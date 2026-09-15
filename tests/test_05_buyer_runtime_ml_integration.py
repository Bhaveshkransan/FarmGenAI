"""
tests/test_05_buyer_runtime_ml_integration.py
------------------------------------------------------------------------
Test suite validating end-to-end runtime ML execution for BuyerAgent:
  1. All 7 crops auto-resolve real features and execute model.predict() with audit_status == "ML_USED"
  2. Standalone BuyerAgent get_market_valuation() auto-resolves features without manual input
  3. ML prediction anchors initial bid in make_offer()
  4. ML prediction anchors concession in respond_to_offer()
  5. Economic guardrails:
     - Case A: High market price / ask capped at reservation price P_max
     - Case B: Insufficient budget strictly bounded or rejected
     - Case C: Normal valuation within budget
  6. Unsupported crop fallback: audit_status == "FALLBACK_USED"
  7. LangGraph buyer_node: auto-resolves market_features when missing from state and logs ML anchor
  8. Thread safety under concurrent pricing service calls
"""

import math
import pytest
import asyncio
import threading
from agents.buyer_agent import BuyerAgent
from backend.services.buyer_pricing_service import (
    get_buyer_pricing_service,
    BuyerPricePredictionService,
)
from shared.crop_catalog import BUYER_SUPPORTED_CROPS
from backend.agents.graph_orchestrator import buyer_node, NegotiationState


class TestBuyerRuntimeMLIntegration:
    """Rigorous end-to-end verification of runtime ML prediction flow."""

    def test_01_all_seven_crops_auto_resolve_and_predict(self):
        """Verify all 7 crops auto-resolve real features from APMC dataset and run ML predict."""
        service = get_buyer_pricing_service()
        assert service is not None

        for crop in list(BUYER_SUPPORTED_CROPS.keys()):
            pred_res = service.predict_modal_price(crop)
            assert pred_res["audit_status"] == "ML_USED"
            assert pred_res["is_ml_prediction"] is True
            assert pred_res["crop"] == crop
            assert pred_res["predicted_modal_price"] > 0
            assert pred_res["feature_source"]["is_real_data"] is True
            assert "apmc" in pred_res["feature_source"]
            assert len(pred_res["features_used"]) == 12

    def test_02_buyer_agent_standalone_valuation_auto_resolves(self):
        """Verify BuyerAgent.get_market_valuation() auto-resolves without context features."""
        buyer = BuyerAgent(
            name="ValuationTester",
            budget=100000.0,
            max_quantity=1000.0,
            target_price=30.0,
            reservation_price=40.0,
            crop="Soybean",
            location="Latur"
        )
        val = buyer.get_market_valuation("Soybean", "Latur")
        assert val > 0
        pred = buyer.last_ml_prediction
        assert pred is not None
        assert pred["audit_status"] == "ML_USED"
        assert pred["is_ml_prediction"] is True
        assert pred["predicted_modal_price"] == val
        assert "Latur" in pred["feature_source"]["match_level"]

    def test_03_make_offer_anchored_by_ml_prediction(self):
        """Verify make_offer() invokes ML prediction and uses it to anchor opening bid."""
        buyer = BuyerAgent(
            name="OpeningBidTester",
            budget=50000.0,
            max_quantity=500.0,
            target_price=45.0,
            reservation_price=55.0,
            crop="Cotton",
            location="Nagpur"
        )
        offer = buyer.make_offer()
        assert offer["price"] > 0
        assert offer["quantity"] > 0
        pred = buyer.last_ml_prediction
        assert pred is not None
        assert pred["audit_status"] == "ML_USED"
        assert pred["crop"] == "Cotton"

    def test_04_respond_to_offer_anchored_by_ml(self):
        """Verify respond_to_offer() executes ML model and anchors concession."""
        buyer = BuyerAgent(
            name="ConcessionTester",
            budget=100000.0,
            max_quantity=500.0,
            target_price=28.0,
            reservation_price=35.0,
            crop="Soybean",
            location="Latur"
        )
        resp = buyer.respond_to_offer({"price": 42.0, "quantity": 500.0, "crop": "Soybean"})
        assert resp["type"] in ["COUNTER", "REJECT"]
        pred = buyer.last_ml_prediction
        assert pred is not None
        assert pred["audit_status"] == "ML_USED"
        assert resp["price"] <= buyer.reservation_price

    def test_05_economic_guardrail_case_a_reservation_ceiling(self):
        """Case A: When seller ask and ML price are high, counter is strictly capped at P_max."""
        buyer = BuyerAgent(
            name="CeilingTester",
            budget=100000.0,
            max_quantity=500.0,
            target_price=22.0,
            reservation_price=26.0,
            crop="Soybean",
            location="Latur"
        )
        resp = buyer.respond_to_offer({"price": 60.0, "quantity": 500.0, "crop": "Soybean"})
        if resp["type"] == "COUNTER":
            assert resp["price"] <= buyer.reservation_price
        else:
            assert resp["type"] == "REJECT"

    def test_06_economic_guardrail_case_b_budget_protection(self):
        """Case B: When budget is tightly constrained, order cost never exceeds budget."""
        buyer = BuyerAgent(
            name="BudgetTester",
            budget=300.0,
            max_quantity=100.0,
            target_price=12.0,
            reservation_price=15.0,
            crop="Bajra",
            location="Pune"
        )
        resp = buyer.respond_to_offer({"price": 14.0, "quantity": 100.0, "crop": "Bajra"})
        if resp["type"] in ["ACCEPT", "COUNTER"]:
            total_commitment = resp["price"] * resp["quantity"]
            assert total_commitment <= buyer.budget
        else:
            assert resp["type"] == "REJECT"

    def test_07_economic_guardrail_case_c_normal_anchored_bid(self):
        """Case C: Realistic market conditions anchor reasonable counter-offer."""
        buyer = BuyerAgent(
            name="NormalBidTester",
            budget=50000.0,
            max_quantity=500.0,
            target_price=30.0,
            reservation_price=36.0,
            crop="Soybean",
            location="Latur"
        )
        resp = buyer.respond_to_offer({"price": 34.0, "quantity": 500.0, "crop": "Soybean"})
        assert resp["type"] in ["ACCEPT", "COUNTER"]
        assert resp["price"] <= buyer.reservation_price
        assert resp["price"] * resp["quantity"] <= buyer.budget

    def test_08_unsupported_crop_fallback_audit_status(self):
        """Verify unsupported crop cleanly falls back with audit_status == 'FALLBACK_USED'."""
        buyer = BuyerAgent(
            name="FallbackTester",
            budget=50000.0,
            max_quantity=100.0,
            target_price=50.0
        )
        val = buyer.get_market_valuation("Mango", context={"market_price": 55.0})
        assert val == 55.0
        pred = buyer.last_ml_prediction
        assert pred is not None
        assert pred["audit_status"] == "FALLBACK_USED"
        assert pred["is_ml_prediction"] is False

    def test_09_thread_safe_pricing_service(self):
        """Verify thread-safety: concurrent predictions execute without race conditions."""
        service = get_buyer_pricing_service()
        results = []
        errors = []

        def worker(crop):
            try:
                res = service.predict_modal_price(crop)
                results.append(res)
            except Exception as e:
                errors.append(e)

        crop_list = list(BUYER_SUPPORTED_CROPS.keys()) * 3  # 21 concurrent requests
        threads = [
            threading.Thread(target=worker, args=(crop,))
            for crop in crop_list
        ]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert len(errors) == 0, f"Thread errors encountered: {errors}"
        assert len(results) == 21
        assert all(r["audit_status"] == "ML_USED" for r in results)

    def test_10_langgraph_buyer_node_auto_resolves_and_logs(self):
        """Verify LangGraph buyer_node auto-resolves features, updates state, and logs ML anchor."""
        state: NegotiationState = {
            "crop": "Soybean",
            "quantity": 500.0,
            "min_price": 25.0,
            "target_price": 32.0,
            "spoilage_days": 15,
            "location": "Latur",
            "market_price": 30.0,
            "round": 1,
            "max_rounds": 5,
            "history": [],
            "buyer_profile": {
                "name": "AgriCorp Latur",
                "budget": 50000.0,
                "max_quantity": 500.0,
                "target_price": 32.0,
                "location": "Latur",
                "strategy": "balanced"
            },
            "logs": [],
            "status": "ACTIVE",
            "proposed_scenario": "",
            "next_action": "",
            "deal": None,
            "plan": None,
            "reflection": None,
            "selected_buyer": None,
            "market_offers": [],
            "user_id": None,
            "active_buyers": [],
            "current_offers": [],
            "best_current_offer": None,
            "latest_farmer_ask": 44.0,
            "latest_buyer_offer": None,
            "buyers_list": [],
            "rag_context": None,
            "market_intelligence": None,
            "recommendation": None,
            "farmer_agent_obj": None,
            "buyer_agent_objs": None,
            "market_features": None,  # Omitted: must be dynamically resolved
        }

        result = asyncio.run(buyer_node(state))
        assert "market_features" in result
        assert result["market_features"] is not None
        assert "modal_price_kg" in result["market_features"]
        assert len(result["buyer_agent_objs"]) > 0
        b_agent = result["buyer_agent_objs"][0]
        assert b_agent.last_ml_prediction is not None
        assert b_agent.last_ml_prediction["audit_status"] == "ML_USED"
        assert any("ML Market Anchor" in log for log in result["logs"])
