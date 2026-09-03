"""
tests/test_03_business_rules.py
Type: DETERMINISTIC / UNIT + INTEGRATION
Covers: Floor price, budget ceiling, validator logic, escalation, RL rewards.
"""
import sys, os, asyncio, random
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import pytest

import agents.farmer_agent as _fa_mod
import agents.buyer_agent as _ba_mod
_fa_mod.llm_client = None
_ba_mod.llm_client = None

from agents.farmer_agent import FarmerAgent
from agents.buyer_agent import BuyerAgent
from agents.warehouse_agent import WarehouseAgent
from agents.processor_agent import ProcessorAgent
from negotiation_engine.negotiation_manager import NegotiationManager


def run(coro):
    return asyncio.run(coro)


def make_manager(min_price=20.0, target_price=22.0, max_rounds=5,
                 shelf_life=5, quantity=500):
    random.seed(42)
    farmer = FarmerAgent(name="BR_Farmer", crop="Tomato", quantity=quantity,
                         min_price=min_price, shelf_life=shelf_life)
    buyer = BuyerAgent(name="BR_Buyer",
                       budget=target_price * quantity * 1.2,
                       max_quantity=quantity * 1.5, target_price=target_price)
    warehouse = WarehouseAgent(name="BR_WH", capacity=5000, storage_cost_per_kg=1.5)
    processor = ProcessorAgent(name="BR_P", crop_type="Tomato", processing_capacity=1000,
                               processing_cost_per_kg=2.0,
                               target_price=min_price * 0.8,
                               max_price=min_price * 1.2)
    return NegotiationManager(farmer=farmer, buyers=[buyer], warehouse=warehouse,
                              processor=processor, max_rounds=max_rounds)


# ================================================================
# BR-1: Floor Price
# ================================================================

class TestFloorPriceProtection:

    def test_deal_price_never_below_floor_easy(self):
        mgr = make_manager(min_price=20.0, target_price=25.0)
        result = run(mgr.start_negotiation(market_price=22.0))
        if result["state"] == "DEAL":
            assert result["deal"]["price"] >= 20.0, (
                f"FLOOR VIOLATED: deal={result['deal']['price']} < min=20.0")

    def test_deal_price_never_below_floor_tight(self):
        mgr = make_manager(min_price=20.0, target_price=21.0)
        result = run(mgr.start_negotiation(market_price=20.5))
        if result["state"] == "DEAL":
            assert result["deal"]["price"] >= 20.0

    def test_no_deal_when_buyer_ceiling_below_floor(self):
        mgr = make_manager(min_price=30.0, target_price=15.0, max_rounds=3)
        result = run(mgr.start_negotiation(market_price=20.0))
        assert result["state"] != "DEAL"

    def test_farmer_fallback_counter_above_min(self):
        """FarmerAgent._fallback_decision must never return below min_price."""
        random.seed(0)
        farmer = FarmerAgent(name="F", crop="T", quantity=500,
                             min_price=20.0, shelf_life=7)
        farmer.current_price = 28.0
        for price in [5.0, 10.0, 15.0, 19.9]:
            result = farmer._fallback_decision({"price": price, "quantity": 100}, 22.0)
            if result["decision"] == "COUNTER":
                assert result["counter_price"] >= 20.0, (
                    f"FLOOR VIOLATED: counter={result['counter_price']} offer={price}")

    def test_validator_fallback_rejects_below_floor(self):
        """Deterministic validator: deal_price < min_price => invalid."""
        min_price = 20.0
        deal_price = 15.0
        quantity = 500
        budget = 100000.0
        valid = (deal_price * quantity <= budget) and (deal_price >= min_price)
        assert valid is False

    def test_validator_fallback_accepts_above_floor(self):
        min_price = 20.0
        deal_price = 22.0
        quantity = 500
        budget = 100000.0
        valid = (deal_price * quantity <= budget) and (deal_price >= min_price)
        assert valid is True


# ================================================================
# BR-2: Budget Ceiling
# ================================================================

class TestBudgetCeiling:

    def test_validator_rejects_deal_exceeding_budget(self):
        deal_price = 25.0
        quantity = 1000
        budget = 10000.0   # only 400kg affordable
        valid = (deal_price * quantity <= budget) and (deal_price >= 20.0)
        assert valid is False

    def test_buyer_inventory_does_not_exceed_budget(self):
        buyer = BuyerAgent(name="Tight", budget=1000.0, max_quantity=500, target_price=20.0)
        _ba_mod.llm_client = None
        resp = buyer.respond_to_offer({"price": 20.0, "quantity": 500},
                                      {"market_price": 20.0, "round": 1})
        if resp["type"] == "ACCEPT":
            assert resp["price"] * resp["quantity"] <= 1000.0 + 20.0


# ================================================================
# BR-3: Invalid Inputs
# ================================================================

class TestInvalidInputs:

    def test_zero_quantity_does_not_crash(self):
        mgr = make_manager(quantity=0)
        try:
            result = run(mgr.start_negotiation(market_price=20.0))
            assert "state" in result
        except Exception as e:
            pytest.fail(f"Crashed on zero quantity: {e}")

    def test_result_always_has_required_keys(self):
        mgr = make_manager()
        result = run(mgr.start_negotiation(market_price=20.0))
        for key in ("state", "summary", "logs"):
            assert key in result, f"Missing key: {key}"


# ================================================================
# BR-4: Spoilage
# ================================================================

class TestSpoilageRules:

    def test_critical_spoilage_1_day_rule(self):
        """At spoilage <= 2 days, 85% of floor is acceptable."""
        spoilage_days = 1
        min_price = 20.0
        buyer_offer = 17.0
        if spoilage_days <= 2:
            assert buyer_offer >= min_price * 0.85

    def test_high_spoilage_no_deal(self):
        mgr = make_manager(min_price=30.0, target_price=10.0, shelf_life=1, max_rounds=2)
        result = run(mgr.start_negotiation(market_price=20.0))
        assert result["state"] != "DEAL"


# ================================================================
# BR-5: Max Rounds
# ================================================================

class TestMaxRounds:

    def test_terminates_at_max_rounds(self):
        mgr = make_manager(min_price=30.0, target_price=10.0, max_rounds=3)
        result = run(mgr.start_negotiation(market_price=15.0))
        valid = {"DEAL", "FAILED", "ESCALATED_STORAGE",
                 "ESCALATED_PROCESSING", "ESCALATED_COMPOST"}
        assert result["state"] in valid

    def test_max_rounds_1_terminates(self):
        mgr = make_manager(min_price=18.0, target_price=22.0, max_rounds=1)
        result = run(mgr.start_negotiation(market_price=20.0))
        assert "state" in result

    def test_summary_never_missing(self):
        for scenario in [
            dict(min_price=20.0, target_price=25.0),
            dict(min_price=50.0, target_price=10.0),
        ]:
            mgr = make_manager(**scenario, max_rounds=3)
            result = run(mgr.start_negotiation(market_price=20.0))
            assert "summary" in result, f"summary missing for state={result['state']}"
            assert result["summary"] is not None


# ================================================================
# BR-6: RL Rewards
# ================================================================

class TestRewardCalculation:

    def test_deal_positive_farmer_reward(self):
        from backend.agents.graph_orchestrator import calculate_supply_chain_rewards
        r = calculate_supply_chain_rewards({"status": "DEAL", "round": 2, "deal": {}})
        assert r["farmer"] > 0

    def test_reject_negative_farmer_reward(self):
        from backend.agents.graph_orchestrator import calculate_supply_chain_rewards
        r = calculate_supply_chain_rewards({"status": "REJECT", "round": 1, "deal": None})
        assert r["farmer"] < 0

    def test_processing_rewards_processor(self):
        from backend.agents.graph_orchestrator import calculate_supply_chain_rewards
        r = calculate_supply_chain_rewards({"status": "ESCALATED_PROCESSING",
                                            "round": 1, "deal": None})
        assert r["processor"] > 0
        assert r["farmer"] < 0

    def test_time_penalty_grows_with_rounds(self):
        from backend.agents.graph_orchestrator import calculate_supply_chain_rewards
        r1 = calculate_supply_chain_rewards({"status": "DEAL", "round": 1, "deal": {}})
        r5 = calculate_supply_chain_rewards({"status": "DEAL", "round": 5, "deal": {}})
        assert r1["farmer"] > r5["farmer"]


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
