"""
backend/tests/test_farmer_architecture_rules.py

Targeted Integration Test Suite verifying all 5 Non-Negotiable
Architectural Rules for the Farmer Workflow in AgriNegotiator:

1. Canonical 7-Crop Restriction (Mango/unsupported -> 400)
2. Deterministic Price & Quantity Boundary Validation (<=0 -> 400)
3. Real XGBoost Machine Learning Model Loading & Inference
4. Explicit HOLD Execution Path (Bypasses buyer matching & negotiation)
5. BUYER_ONLY Mode Restriction (Halts before downstream logistics)
6. Resource-Aware Orchestration: Own Transport (Transport agent skipped)
7. Resource-Aware Orchestration: Own Storage (Warehouse agent skipped)
8. Deterministic Floor-Price Guardrail (Deal < min_price -> Hard REJECT)
"""

import asyncio
import requests
try:
    import pytest
except ImportError:
    class DummyPytest:
        class mark:
            @staticmethod
            def asyncio(fn):
                return fn
    pytest = DummyPytest()
from backend.core.constants import validate_crop, CROP_MASTER, SUPPORTED_CROPS
from backend.services.price_prediction_service import predict_price_xgboost
from backend.agents.graph_orchestrator import (
    validator_node, 
    dynamic_routing_node, 
    hold_decision_node,
    route_after_market_intelligence,
    graph_orchestrator
)

BASE_URL = "http://127.0.0.1:8000/api/v1"


def test_rule_1_invalid_crop_rejected_http_400():
    """Verify non-canonical crops (e.g., Mango) are rejected at API boundary."""
    # Unit check
    is_valid, msg = validate_crop("Mango")
    assert not is_valid
    assert "Unsupported crop" in msg

    # HTTP API check
    payload = {
        "crop": "Mango",
        "quantity": 500,
        "min_price": 50.0,
        "farmer_name": "Test Farmer"
    }
    r = requests.post(f"{BASE_URL}/negotiations/", json=payload)
    assert r.status_code == 400, f"Expected 400, got {r.status_code}: {r.text}"
    assert "Unsupported crop: 'Mango'" in r.text
    print("✅ TEST 1 PASSED: Invalid crop 'Mango' rejected with HTTP 400.")


def test_rule_2_valid_canonical_7_crops_accepted():
    """Verify all 7 canonical crops are accepted without error."""
    for crop in SUPPORTED_CROPS:
        is_valid, _ = validate_crop(crop)
        assert is_valid, f"Crop {crop} should be valid in CROP_MASTER"
    print(f"✅ TEST 2 PASSED: All 7 canonical crops ({', '.join(SUPPORTED_CROPS)}) valid.")


def test_rule_3_price_and_quantity_deterministic_validation():
    """Verify quantity <= 0 or min_price <= 0 are rejected with HTTP 400."""
    # Zero quantity
    r1 = requests.post(f"{BASE_URL}/negotiations/", json={"crop": "Soybean", "quantity": 0, "min_price": 45.0})
    assert r1.status_code == 400

    # Zero / negative price
    r2 = requests.post(f"{BASE_URL}/negotiations/", json={"crop": "Soybean", "quantity": 500, "min_price": -10.0})
    assert r2.status_code == 400
    print("✅ TEST 3 PASSED: Zero/negative quantity & price rejected deterministically with HTTP 400.")


def test_rule_4_real_xgboost_model_inference():
    """Verify authoritative XGBoost model loads and projects 7-day forecast."""
    res = predict_price_xgboost("Soybean", "Latur", 48.0, days_ahead=7)
    assert res["model_type"] == "XGBRegressor", f"Expected XGBRegressor, got {res['model_type']}"
    assert res["forecast_price"] > 0
    assert res["direction"] in ["up", "down"]
    print(f"✅ TEST 4 PASSED: Real XGBoost model projected Soybean price to ₹{res['forecast_price']}/kg ({res['direction']}).")


@pytest.mark.asyncio
async def test_rule_5_hold_execution_path_bypasses_buyer_matching():
    """Verify HOLD decision routes to hold_decision_node and bypasses buyer matching."""
    state = {
        "crop": "Soybean",
        "quantity": 500,
        "min_price": 45.0,
        "market_price": 48.0,
        "sell_hold_decision": "HOLD",
        "sell_hold_reasoning": "Anticipating wholesale price surge.",
        "logs": []
    }
    next_node = await route_after_market_intelligence(state)
    assert next_node == "hold_decision_node", f"Expected hold_decision_node, got {next_node}"

    # Execute hold_decision_node
    result = await hold_decision_node(state)
    assert result["status"] == "HOLD"
    assert result["deal"]["type"] == "HOLD"
    assert any("HOLD Execution Path Activated" in log for log in result["logs"])
    print("✅ TEST 5 PASSED: HOLD decision routes to hold_decision_node, bypassing buyer matching.")


@pytest.mark.asyncio
async def test_rule_6_buyer_only_mode_halts_before_logistics():
    """Verify BUYER_ONLY mode halts at deal agreement without downstream logistics."""
    state = {
        "status": "DEAL",
        "deal": {"type": "DIRECT", "price": 50.0},
        "workflow_mode": "BUYER_ONLY",
        "permitted_agents": ["buyer_agent"],
        "logs": [],
        "quantity": 500,
        "location": "Nashik",
        "selected_buyer": {"name": "Test Buyer", "location": "Pune"}
    }
    result = await dynamic_routing_node(state)
    assert "transport_plan" not in result.get("deal", {})
    assert any("Scope is BUYER_ONLY" in log for log in result["logs"])
    print("✅ TEST 6 PASSED: BUYER_ONLY mode terminates at deal agreement without executing logistics.")


@pytest.mark.asyncio
async def test_rule_7_own_transport_resource_skips_transport_procurement():
    """Verify farmer with existing transport does not trigger transport agent bidding."""
    state = {
        "status": "DEAL",
        "deal": {"type": "DIRECT", "price": 50.0},
        "workflow_mode": "FULL_SUPPLY_CHAIN",
        "permitted_agents": ["buyer_agent", "dynamic_routing_agent"],
        "has_transport": True,
        "has_storage": False,
        "logs": [],
        "quantity": 500,
        "location": "Nashik",
        "selected_buyer": {"name": "Test Buyer", "location": "Pune"}
    }
    result = await dynamic_routing_node(state)
    assert result["deal"]["transport_plan"]["type"] == "SELF_TRANSPORT"
    assert any("Farmer possesses own transport" in log for log in result["logs"])
    print("✅ TEST 7 PASSED: Own transport recognized; third-party transport procurement skipped.")


@pytest.mark.asyncio
async def test_rule_8_own_storage_resource_skips_warehouse_procurement():
    """Verify farmer with existing storage does not trigger warehouse procurement."""
    state = {
        "status": "DEAL",
        "deal": {"type": "DIRECT", "price": 50.0},
        "workflow_mode": "FULL_SUPPLY_CHAIN",
        "permitted_agents": ["buyer_agent", "dynamic_routing_agent"],
        "has_transport": True,
        "has_storage": True,
        "spoilage_days": 3,  # Perishable, but farmer has storage!
        "logs": [],
        "quantity": 500,
        "location": "Nashik",
        "selected_buyer": {"name": "Test Buyer", "location": "Pune"}
    }
    result = await dynamic_routing_node(state)
    assert "warehouse_option" not in result["deal"]
    assert any("Farmer possesses own storage facility" in log for log in result["logs"])
    print("✅ TEST 8 PASSED: Own storage recognized; warehouse procurement skipped.")


@pytest.mark.asyncio
async def test_rule_9_deterministic_floor_price_guardrail_overrides_llm():
    """Verify validator_node deterministically rejects offer below min_price."""
    state = {
        "crop": "Soybean",
        "quantity": 500,
        "min_price": 45.0,
        "latest_buyer_offer": 35.0,  # Below floor ₹45!
        "latest_farmer_ask": 48.0,
        "selected_buyer": {"name": "Predatory Buyer", "budget": 100000},
        "logs": []
    }
    result = await validator_node(state)
    assert result["status"] == "REJECT"
    assert any("Deal price ₹35.0/kg is below farmer floor price ₹45.0/kg" in log for log in result["logs"])
    print("✅ TEST 9 PASSED: Below-floor offer (₹35 < ₹45) deterministically rejected.")


@pytest.mark.asyncio
async def test_rule_10_lack_of_storage_with_holding_duration_triggers_warehouse():
    """Verify that lacking storage with required holding duration activates warehouse procurement, even if shelf-life > 5."""
    state = {
        "status": "DEAL",
        "deal": {"type": "DIRECT", "price": 50.0},
        "workflow_mode": "FULL_SUPPLY_CHAIN",
        "permitted_agents": ["buyer_agent", "dynamic_routing_agent", "warehouse_agent"],
        "has_transport": True,
        "has_storage": False,     # Farmer has NO storage
        "holding_days": 4,         # Farmer must hold for 4 days before buyer pickup
        "spoilage_days": 14,       # Shelf life is 14 days (> 5), but storage is STILL required!
        "logs": [],
        "quantity": 500,
        "location": "Nashik",
        "selected_buyer": {"name": "Test Buyer", "location": "Pune"}
    }
    result = await dynamic_routing_node(state)
    assert "warehouse_option" in result["deal"], "Warehouse procurement should activate when farmer lacks storage and needs holding duration"
    assert any("Warehouse" in log for log in result["logs"])
    print("✅ TEST 10 PASSED: Lacking storage + holding duration triggers warehouse procurement (independent of shelf-life).")


@pytest.mark.asyncio
async def test_rule_11_requires_processing_activates_processor_quotes():
    """Verify that requiring processing activates processor quotes in dynamic routing."""
    state = {
        "status": "DEAL",
        "deal": {"type": "DIRECT", "price": 50.0},
        "workflow_mode": "FULL_SUPPLY_CHAIN",
        "permitted_agents": ["buyer_agent", "dynamic_routing_agent", "processor_agent"],
        "has_transport": True,
        "has_storage": True,
        "requires_processing": True,
        "spoilage_days": 10,
        "logs": [],
        "quantity": 1000,
        "location": "Nashik",
        "selected_buyer": {"name": "Test Buyer", "location": "Pune"}
    }
    result = await dynamic_routing_node(state)
    assert "processor_option" in result["deal"], "Processor option should be procured when requires_processing is True"
    assert any("Processor" in log for log in result["logs"])
    print("✅ TEST 11 PASSED: requires_processing triggers value-add processor quotes.")


if __name__ == "__main__":
    print("\n🚀 RUNNING TARGETED INTEGRATION TEST SUITE FOR FARMER ARCHITECTURE RULES...\n")
    test_rule_1_invalid_crop_rejected_http_400()
    test_rule_2_valid_canonical_7_crops_accepted()
    test_rule_3_price_and_quantity_deterministic_validation()
    test_rule_4_real_xgboost_model_inference()
    asyncio.run(test_rule_5_hold_execution_path_bypasses_buyer_matching())
    asyncio.run(test_rule_6_buyer_only_mode_halts_before_logistics())
    asyncio.run(test_rule_7_own_transport_resource_skips_transport_procurement())
    asyncio.run(test_rule_8_own_storage_resource_skips_warehouse_procurement())
    asyncio.run(test_rule_9_deterministic_floor_price_guardrail_overrides_llm())
    asyncio.run(test_rule_10_lack_of_storage_with_holding_duration_triggers_warehouse())
    asyncio.run(test_rule_11_requires_processing_activates_processor_quotes())
    print("\n🎉 ALL 11 ARCHITECTURAL INTEGRATION TESTS PASSED CLEANLY! 100% SUCCESS.\n")

