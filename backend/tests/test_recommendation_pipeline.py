"""
backend/tests/test_recommendation_pipeline.py

Comprehensive tests for the FarmGenAI Recommendation System:
1. LLM JSON parsing in _generate_recommendation
2. Deterministic fallback coverage for DEAL, PROCESSING, STORAGE, HOLD, COMPOST
3. RECOMMENDATION_PROMPT parameter completeness
4. Recommendation routes (/recommendations/generate) logic
5. NegotiationStatusResponse schema includes recommendation & reflection
6. NegotiationManager propagates recommendation to downstream consumers
"""

import pytest
import asyncio
from unittest.mock import patch, MagicMock

from backend.agents.graph_orchestrator import _generate_recommendation
from backend.agents.prompts import RECOMMENDATION_PROMPT
from backend.schemas.negotiation_model import NegotiationStatusResponse


@pytest.fixture
def base_state():
    return {
        "crop": "Soybean",
        "quantity": 1000.0,
        "min_price": 45.0,
        "market_price": 50.0,
        "spoilage_days": 14,
        "status": "ACTIVE",
        "latest_buyer_offer": 48.0,
        "location": "Latur",
    }


# Test 1: LLM returns valid JSON {"message": "..."}
@pytest.mark.asyncio
async def test_rec_llm_json_parsed_correctly(base_state):
    llm_json = '{"message": "Negotiation reached a strong rate of ₹48/kg for Soybean. Confirm delivery schedule."}'
    with patch("backend.agents.graph_orchestrator.llm_client.generate", return_value=llm_json):
        rec = await _generate_recommendation(base_state, {"type": "DIRECT", "price": 48.0})
        assert "Negotiation reached a strong rate" in rec
        assert "Soybean" in rec


# Test 2: LLM returns plain text (fallback gracefully handled)
@pytest.mark.asyncio
async def test_rec_llm_plain_text_handled(base_state):
    plain_text = "Recommend selling at ₹48/kg immediately to secure buyer commitment."
    with patch("backend.agents.graph_orchestrator.llm_client.generate", return_value=plain_text):
        rec = await _generate_recommendation(base_state, {"type": "DIRECT", "price": 48.0})
        assert "Recommend selling at ₹48/kg" in rec


# Test 3: LLM failure fallback for DEAL
@pytest.mark.asyncio
async def test_rec_fallback_deal(base_state):
    base_state["status"] = "DEAL"
    base_state["latest_buyer_offer"] = 49.0
    with patch("backend.agents.graph_orchestrator.llm_client.generate", side_effect=Exception("API down")):
        rec = await _generate_recommendation(base_state, {"type": "DIRECT", "price": 49.0})
        assert "Direct sale at ₹49.0/kg is the optimal outcome" in rec
        assert "Soybean" in rec
        assert "invoicing" in rec


# Test 4: LLM failure fallback for PROCESSING
@pytest.mark.asyncio
async def test_rec_fallback_processing(base_state):
    base_state["status"] = "ESCALATED_PROCESSING"
    with patch("backend.agents.graph_orchestrator.llm_client.generate", side_effect=Exception("API down")):
        rec = await _generate_recommendation(base_state, {"type": "PROCESSING", "price": 40.0})
        assert "Processing route activated" in rec
        assert "₹40.0/kg" in rec
        assert "FPO" in rec


# Test 5: LLM failure fallback for STORAGE
@pytest.mark.asyncio
async def test_rec_fallback_storage(base_state):
    base_state["status"] = "ESCALATED_STORAGE"
    deal = {"type": "STORAGE", "storage_cost": 25200.0}
    with patch("backend.agents.graph_orchestrator.llm_client.generate", side_effect=Exception("API down")):
        rec = await _generate_recommendation(base_state, deal)
        assert "Cold storage recommended" in rec
        assert "14 days" in rec


# Test 6: LLM failure fallback for HOLD
@pytest.mark.asyncio
async def test_rec_fallback_hold(base_state):
    base_state["status"] = "HOLD"
    with patch("backend.agents.graph_orchestrator.llm_client.generate", side_effect=Exception("API down")):
        rec = await _generate_recommendation(base_state, {"type": "HOLD"})
        assert "HOLD directive active" in rec
        assert "XGBoost forecast" in rec
        assert "7 days" in rec


# Test 7: LLM failure fallback for COMPOST / Spoilage critical
@pytest.mark.asyncio
async def test_rec_fallback_compost(base_state):
    base_state["status"] = "FAILED"
    base_state["spoilage_days"] = 1  # critical
    with patch("backend.agents.graph_orchestrator.llm_client.generate", side_effect=Exception("API down")):
        rec = await _generate_recommendation(base_state, None)
        assert "processor salvage or compost" in rec
        assert "Soybean" in rec


# Test 8: RECOMMENDATION_PROMPT parameter formatting
def test_recommendation_prompt_variables():
    rendered = RECOMMENDATION_PROMPT.format(
        crop="Cotton",
        quantity=500.0,
        farmer_min_price=70.0,
        direct_sale_result="Status=DEAL, Price=₹72/kg",
        storage_cost=1500.0,
        storage_days=30,
        processor_offer=56.0,
        market_price=71.0,
    )
    assert "Cotton" in rendered
    assert "₹70.0/kg" in rendered
    assert "₹71.0/kg" in rendered
    assert "Output JSON:" in rendered


# Test 9: NegotiationStatusResponse schema includes recommendation & reflection
def test_negotiation_status_response_schema():
    payload = {
        "negotiation_id": "neg_test_123",
        "status": "DEAL",
        "offers": [],
        "summary": "Deal completed.",
        "final_price": 52.0,
        "recommendation": "Direct sale is recommended.",
        "reflection": "Both parties aligned on market rate.",
    }
    obj = NegotiationStatusResponse(**payload)
    assert obj.recommendation == "Direct sale is recommended."
    assert obj.reflection == "Both parties aligned on market rate."


# Test 10: Recommendation route business logic calculation
@pytest.mark.asyncio
async def test_recommendation_routes_calculation():
    from backend.routes.recommendation_routes import RecommendationRequest, generate_recommendation
    
    req = RecommendationRequest(
        crop="Soybean",
        quantity=1000.0,
        min_price=45.0,
        location="Latur",
        spoilage_days=30,
        market_price=50.0
    )
    
    mock_user = {"id": "farmer_1", "role": "FARMER"}
    with patch("backend.routes.recommendation_routes.llm_client.explain_scenarios", return_value="Direct sale maximizes net returns."):
        result = await generate_recommendation(req, current_user=mock_user)
        assert result["success"] is True
        assert result["data"]["crop"] == "Soybean"
        assert len(result["data"]["options"]) == 3
        # Direct sale net revenue = 50 * 1000 = 50000
        direct_opt = next(o for o in result["data"]["options"] if o["type"] == "Direct Sale")
        assert direct_opt["net_revenue"] == 50000.0
