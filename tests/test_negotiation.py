"""Unit tests for NegotiationManager and negotiation flow."""

import unittest

from agents.farmer_agent import FarmerAgent
from agents.buyer_agent import BuyerAgent
from agents.warehouse_agent import WarehouseAgent
from negotiation_engine.negotiation_manager import NegotiationManager


def _make_manager(min_price=18, target_price=16, max_rounds=5):
    farmer = FarmerAgent(
        name="TestFarmer", crop="Tomato", quantity=500,
        min_price=min_price, shelf_life=4
    )
    buyer = BuyerAgent(
        name="TestBuyer", budget=12000, max_quantity=600,
        target_price=target_price
    )
    warehouse = WarehouseAgent(
        name="TestWarehouse", capacity=5000,
        storage_cost_per_kg=1.5, location="Nashik"
    )
    return NegotiationManager(
        farmer=farmer, buyers=[buyer], warehouse=warehouse,
        max_rounds=max_rounds
    )


class TestNegotiationManager(unittest.TestCase):

    def test_negotiation_returns_result_dict(self):
        mgr = _make_manager()
        import asyncio
        result = asyncio.run(mgr.start_negotiation(market_price=18))
        self.assertIsInstance(result, dict)
        self.assertIn("state", result)
        self.assertIn("logs", result)

    def test_negotiation_state_is_valid(self):
        mgr = _make_manager()
        import asyncio
        result = asyncio.run(mgr.start_negotiation(market_price=18))
        valid_states = {"DEAL", "FAILED", "ESCALATED_STORAGE",
                        "ESCALATED_PROCESSING", "ESCALATED_COMPOST"}
        self.assertIn(result["state"], valid_states)

    def test_deal_reached_when_prices_close(self):
        # With small gap (farmer 18 min + 2-3 initial, buyer target 17)
        # the manager should converge within 5 rounds
        import random
        random.seed(42)
        mgr = _make_manager(min_price=16, target_price=18, max_rounds=6)
        import asyncio
        result = asyncio.run(mgr.start_negotiation(market_price=17))
        self.assertEqual(result["state"], "DEAL")

    def test_deal_has_price_and_quantity(self):
        mgr = _make_manager(min_price=16, target_price=18, max_rounds=6)
        import asyncio
        result = asyncio.run(mgr.start_negotiation(market_price=17))
        if result["state"] == "DEAL":
            self.assertTrue(len(result["partnerships"]) >= 1)
            self.assertIn("price", result["partnerships"][0])
            self.assertIn("quantity", result["partnerships"][0])

    def test_logs_contain_round_entries(self):
        mgr = _make_manager()
        import asyncio
        asyncio.run(mgr.start_negotiation(market_price=18))
        self.assertTrue(len(mgr.logs) > 0)

    def test_price_series_populated(self):
        mgr = _make_manager(min_price=18, target_price=20)
        import asyncio
        asyncio.run(mgr.start_negotiation(market_price=18))
        series = mgr.memory.get_price_series()
        self.assertIsInstance(series, list)
        self.assertTrue(len(series) >= 1)

    def test_escalation_when_no_deal(self):
        # Force fail: farmer min far above buyer target
        mgr = _make_manager(min_price=50, target_price=10, max_rounds=2)
        import asyncio
        result = asyncio.run(mgr.start_negotiation(market_price=15))
        self.assertNotEqual(result["state"], "DEAL")


if __name__ == "__main__":
    unittest.main()
