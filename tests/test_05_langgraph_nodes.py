"""
tests/test_05_langgraph_nodes.py
Type: INTEGRATION (real LangGraph, no mocks for node logic)
Covers: Individual LangGraph node function outputs.
"""
import sys, os, asyncio
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import pytest

from backend.agents.graph_orchestrator import (
    planner_node, market_intelligence_node, matching_engine_node,
    farmer_node, buyer_node, rank_responses_node, validator_node,
    calculate_supply_chain_rewards,
)


def run(coro):
    return asyncio.run(coro)


BASE = {
    "crop": "Tomato", "quantity": 500.0, "min_price": 20.0,
    "target_price": 24.0, "spoilage_days": 5, "location": "Pune",
    "market_price": 22.0, "round": 0, "max_rounds": 6, "history": [],
    "buyer_profile": None, "logs": [], "status": "ACTIVE",
    "proposed_scenario": "direct-sale", "next_action": "",
    "deal": None, "plan": None, "reflection": None,
    "selected_buyer": None, "market_offers": [],
    "user_id": None, "active_buyers": [], "current_offers": [],
    "best_current_offer": None, "latest_farmer_ask": None,
    "latest_buyer_offer": None, "rag_context": None,
    "market_intelligence": None, "recommendation": None,
    "buyers_list": [
        {"id": "b1", "name": "NodeTestBuyer", "target_price": 22.0,
         "budget": 15000.0, "max_quantity": 600.0,
         "location": "Mumbai", "strategy": "bulk"}
    ],
}


class TestPlannerNode:
    def test_returns_plan(self):
        result = run(planner_node(dict(BASE)))
        assert "plan" in result
        assert "logs" in result
        assert result["status"] == "ACTIVE"

    def test_logs_planner_entry(self):
        result = run(planner_node(dict(BASE)))
        assert any("Planner" in log for log in result["logs"])

    def test_rag_context_is_string(self):
        result = run(planner_node(dict(BASE)))
        assert isinstance(result.get("rag_context"), str)


class TestMarketIntelligenceNode:
    def setup_method(self):
        self.state = dict(BASE)
        self.state["rag_context"] = "Test RAG context."

    def test_returns_analysis(self):
        result = run(market_intelligence_node(self.state))
        assert "market_intelligence" in result
        assert "logs" in result

    def test_log_has_entry(self):
        result = run(market_intelligence_node(self.state))
        assert any("Market Intelligence" in log for log in result["logs"])

    def test_analysis_is_non_empty_string(self):
        result = run(market_intelligence_node(self.state))
        assert isinstance(result["market_intelligence"], str)
        assert len(result["market_intelligence"]) > 0


class TestMatchingEngineNode:
    def test_returns_active_buyers(self):
        result = run(matching_engine_node(dict(BASE)))
        assert "active_buyers" in result
        assert len(result["active_buyers"]) >= 1

    def test_returns_current_offers(self):
        result = run(matching_engine_node(dict(BASE)))
        assert "current_offers" in result

    def test_returns_market_offers(self):
        result = run(matching_engine_node(dict(BASE)))
        assert "market_offers" in result

    def test_first_buyer_has_id_or_name(self):
        result = run(matching_engine_node(dict(BASE)))
        buyer = result["active_buyers"][0]
        assert "id" in buyer or "name" in buyer

    def test_log_has_matching_entry(self):
        result = run(matching_engine_node(dict(BASE)))
        assert any("Matching Engine" in log for log in result["logs"])

    def test_empty_buyers_creates_default(self):
        state = dict(BASE)
        state["buyers_list"] = []
        result = run(matching_engine_node(state))
        assert len(result["active_buyers"]) >= 1


class TestFarmerNode:
    def setup_method(self):
        self.state = dict(BASE)
        self.state.update({
            "active_buyers": [{"id": "b1", "name": "B1", "target_price": 22.0,
                               "budget": 15000.0, "max_quantity": 600.0,
                               "location": "Mumbai", "strategy": "bulk"}],
            "latest_buyer_offer": 18.0,
            "latest_farmer_ask": 24.0,
            "selected_buyer": {"id": "b1", "name": "B1"},
        })

    def test_returns_state_update(self):
        result = run(farmer_node(self.state))
        assert "logs" in result and "round" in result

    def test_logs_farmer_entry(self):
        result = run(farmer_node(self.state))
        assert any("Farmer" in log for log in result["logs"])

    def test_status_is_valid(self):
        result = run(farmer_node(self.state))
        if "status" in result:
            assert result["status"] in ("DEAL", "REJECT", "ACTIVE")

    def test_counter_above_min_price(self):
        """CRITICAL: farmer_node counter must be >= min_price=20.0."""
        state = dict(self.state)
        state["latest_buyer_offer"] = 5.0   # way below floor
        result = run(farmer_node(state))
        ask = result.get("latest_farmer_ask")
        status = result.get("status")
        if ask and status not in ("DEAL", "REJECT"):
            assert ask >= 20.0, f"FLOOR VIOLATED in farmer_node: ask={ask}"


class TestBuyerNode:
    def setup_method(self):
        self.state = dict(BASE)
        self.state.update({
            "active_buyers": [{"id": "b1", "name": "TestBuyer", "target_price": 22.0,
                               "budget": 15000.0, "max_quantity": 600.0,
                               "location": "Mumbai", "strategy": "bulk"}],
            "latest_farmer_ask": 23.0,
            "round": 1, "history": [],
        })

    def test_returns_offers(self):
        result = run(buyer_node(self.state))
        assert "current_offers" in result
        assert len(result["current_offers"]) >= 1

    def test_logs_pool_entry(self):
        result = run(buyer_node(self.state))
        assert any("Buyers Pool" in log for log in result["logs"])

    def test_offer_has_required_keys(self):
        result = run(buyer_node(self.state))
        for offer in result["current_offers"]:
            assert "buyer_name" in offer
            assert "price" in offer
            assert "status" in offer


class TestRankResponsesNode:
    def test_accept_wins_over_counter(self):
        state = dict(BASE)
        state["current_offers"] = [
            {"buyer_id": "b1", "buyer_name": "B1", "price": 22.0, "status": "ACCEPT"},
            {"buyer_id": "b2", "buyer_name": "B2", "price": 20.0, "status": "COUNTER"},
        ]
        state["active_buyers"] = [{"id": "b1", "name": "B1", "target_price": 22.0}]
        result = run(rank_responses_node(state))
        assert result["status"] == "DEAL"

    def test_best_counter_selected(self):
        state = dict(BASE)
        state["current_offers"] = [
            {"buyer_id": "b1", "buyer_name": "B1", "price": 19.0, "status": "COUNTER"},
            {"buyer_id": "b2", "buyer_name": "B2", "price": 21.0, "status": "COUNTER"},
        ]
        state["active_buyers"] = []
        result = run(rank_responses_node(state))
        assert result["status"] == "ACTIVE"
        assert result["latest_buyer_offer"] == 21.0

    def test_all_reject_returns_reject(self):
        state = dict(BASE)
        state["current_offers"] = [
            {"buyer_id": "b1", "buyer_name": "B1", "price": 10.0, "status": "REJECT"}
        ]
        state["active_buyers"] = []
        result = run(rank_responses_node(state))
        assert result["status"] == "REJECT"

    def test_empty_offers_returns_reject(self):
        state = dict(BASE)
        state["current_offers"] = []
        state["active_buyers"] = []
        result = run(rank_responses_node(state))
        assert result["status"] == "REJECT"


class TestValidatorNode:
    def test_produces_status(self):
        state = dict(BASE)
        state.update({
            "status": "DEAL", "latest_buyer_offer": 22.0,
            "latest_farmer_ask": 22.0,
            "selected_buyer": {"id": "b1", "name": "B1", "budget": 15000.0},
        })
        result = run(validator_node(state))
        assert result["status"] in ("DEAL", "REJECT")

    def test_logs_validator_entry(self):
        state = dict(BASE)
        state.update({
            "status": "DEAL", "latest_buyer_offer": 22.0,
            "latest_farmer_ask": 22.0,
            "selected_buyer": {"budget": 15000.0},
        })
        result = run(validator_node(state))
        assert any("Validator" in log for log in result["logs"])


class TestRewardFunction:
    def test_deal_positive_farmer(self):
        r = calculate_supply_chain_rewards({"status": "DEAL", "round": 1, "deal": {}})
        assert r["farmer"] > 0

    def test_reject_negative_farmer(self):
        r = calculate_supply_chain_rewards({"status": "REJECT", "round": 1, "deal": None})
        assert r["farmer"] < 0

    def test_processing_rewards_processor(self):
        r = calculate_supply_chain_rewards({"status": "ESCALATED_PROCESSING",
                                            "round": 1, "deal": None})
        assert r["processor"] > 0

    def test_time_penalty_grows(self):
        r1 = calculate_supply_chain_rewards({"status": "DEAL", "round": 1, "deal": {}})
        r5 = calculate_supply_chain_rewards({"status": "DEAL", "round": 5, "deal": {}})
        assert r1["farmer"] > r5["farmer"]


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
