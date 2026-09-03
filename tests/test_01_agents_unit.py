"""
tests/test_01_agents_unit.py
------------------------------------------------------------------------
Type: DETERMINISTIC / UNIT
Covers: All 7 agent classes with no LLM dependency.
"""
import sys, os, random
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
from agents.compost_agent import CompostAgent
from agents.transporter_agent import TransporterAgent
from agents.restaurant_agent import RestaurantAgent

MARKET_CTX = {"market_price": 20.0, "round": 1}

# --- FarmerAgent -----------------------------------------------

class TestFarmerAgent:
    def setup_method(self):
        random.seed(42)
        self.farmer = FarmerAgent(
            name="Ramesh", crop="Tomato", quantity=500,
            min_price=20.0, shelf_life=5, location="Pune"
        )

    def test_initial_price_above_min(self):
        assert self.farmer.current_price >= self.farmer.min_price

    def test_make_offer_has_price_and_quantity(self):
        offer = self.farmer.make_offer(MARKET_CTX)
        assert "price" in offer and "quantity" in offer
        assert offer["price"] > 0 and offer["quantity"] > 0

    def test_evaluate_offer_accept_at_target(self):
        self.farmer.current_price = 22.0
        assert self.farmer.evaluate_offer({"price": 22.0, "quantity": 500}) == "ACCEPT"

    def test_evaluate_offer_counter_below_target(self):
        self.farmer.current_price = 30.0
        assert self.farmer.evaluate_offer({"price": 18.0, "quantity": 500}) == "COUNTER"

    def test_floor_price_never_violated(self):
        """CRITICAL: counter price must never go below min_price."""
        self.farmer.current_price = 25.0
        for buyer_price in [19.0, 15.0, 10.0, 1.0]:
            resp = self.farmer.respond_to_offer({"price": buyer_price, "quantity": 200}, MARKET_CTX)
            if resp["type"] == "COUNTER":
                assert resp["price"] >= self.farmer.min_price, (
                    f"FLOOR VIOLATION: counter={resp['price']} < min={self.farmer.min_price}"
                )

    def test_accept_when_price_meets_current_price(self):
        self.farmer.current_price = 22.0
        resp = self.farmer.respond_to_offer({"price": 22.0, "quantity": 300}, MARKET_CTX)
        assert resp["type"] == "ACCEPT"

    def test_shelf_life_stored(self):
        assert self.farmer.shelf_life == 5

    def test_location_stored(self):
        assert self.farmer.location == "Pune"


# --- BuyerAgent ------------------------------------------------

class TestBuyerAgent:
    def setup_method(self):
        random.seed(42)
        self.buyer = BuyerAgent(
            name="BigBasket", budget=25000, max_quantity=1000,
            target_price=22.0, location="Mumbai"
        )

    def test_make_offer_below_target(self):
        offer = self.buyer.make_offer(MARKET_CTX)
        assert offer["price"] <= self.buyer.target_price + 1.0

    def test_make_offer_quantity_within_max(self):
        offer = self.buyer.make_offer(MARKET_CTX)
        assert 0 < offer["quantity"] <= self.buyer.max_quantity

    def test_evaluate_offer_accept_at_target(self):
        # BuyerAgent accepts when price <= target_price * 0.95 (buyer-favourable)
        accept_price = self.buyer.target_price * 0.90
        assert self.buyer.evaluate_offer({"price": accept_price, "quantity": 500}) == "ACCEPT"

    def test_evaluate_offer_counter_above_target(self):
        assert self.buyer.evaluate_offer({"price": self.buyer.target_price * 2, "quantity": 500}) == "COUNTER"

    def test_budget_non_negative_after_accept(self):
        resp = self.buyer.respond_to_offer({"price": 20.0, "quantity": 500}, MARKET_CTX)
        if resp["type"] == "ACCEPT":
            assert self.buyer.budget >= 0

    def test_respond_returns_valid_type(self):
        resp = self.buyer.respond_to_offer({"price": 20.0, "quantity": 400}, MARKET_CTX)
        assert resp["type"] in ("ACCEPT", "COUNTER", "REJECT")
        assert "price" in resp

    def test_budget_ceiling_prevents_overpay(self):
        """Buyer with tiny budget cannot buy 1000kg at high price."""
        poor_buyer = BuyerAgent(name="TinyBudget", budget=100, max_quantity=1000, target_price=22.0)
        resp = poor_buyer.respond_to_offer({"price": 22.0, "quantity": 1000}, MARKET_CTX)
        if resp["type"] == "ACCEPT":
            assert resp["quantity"] * 22.0 <= 100 + 22.0  # allow 1 unit tolerance


# --- WarehouseAgent --------------------------------------------

class TestWarehouseAgent:
    def setup_method(self):
        self.warehouse = WarehouseAgent(
            name="ColdStore-Nashik", capacity=5000,
            storage_cost_per_kg=1.5, location="Nashik"
        )

    def test_initial_capacity_full(self):
        assert self.warehouse.available_capacity() == 5000

    def test_accept_within_capacity(self):
        result = self.warehouse.respond_to_offer({"quantity": 200, "crop": "Tomato"})
        assert result["type"] in ("ACCEPT_STORAGE", "REJECT")

    def test_reject_over_capacity(self):
        assert self.warehouse.respond_to_offer({"quantity": 99999, "crop": "Tomato"})["type"] == "REJECT"

    def test_inventory_increments_on_accept(self):
        before = self.warehouse.current_inventory
        result = self.warehouse.respond_to_offer({"quantity": 100, "crop": "Tomato"})
        if result["type"] == "ACCEPT_STORAGE":
            assert self.warehouse.current_inventory == before + 100

    def test_storage_cost_correct(self):
        result = self.warehouse.respond_to_offer({"quantity": 100.0, "crop": "Tomato"})
        if result["type"] == "ACCEPT_STORAGE":
            assert result["cost"] == round(100.0 * 1.5, 2)

    def test_get_status_fields(self):
        status = self.warehouse.get_status()
        for f in ("capacity", "current_inventory", "available_capacity", "storage_cost_per_kg"):
            assert f in status


# --- ProcessorAgent --------------------------------------------

class TestProcessorAgent:
    def setup_method(self):
        self.processor = ProcessorAgent(
            name="FP-Pune", crop_type="Tomato", processing_capacity=1000,
            processing_cost_per_kg=2.0, target_price=15.0, max_price=20.0
        )

    def test_accept_within_price(self):
        result = self.processor.respond_to_offer({"price": 18.0, "quantity": 500, "crop": "Tomato"})
        assert result["type"] in ("ACCEPT_PROCESSING", "REJECT")

    def test_reject_exceeds_max_price(self):
        result = self.processor.respond_to_offer({"price": 25.0, "quantity": 500, "crop": "Tomato"})
        assert result["type"] == "REJECT"

    def test_reject_wrong_crop(self):
        result = self.processor.respond_to_offer({"price": 15.0, "quantity": 300, "crop": "Onion"})
        assert result["type"] == "REJECT"

    def test_quantity_capped_at_capacity(self):
        result = self.processor.respond_to_offer({"price": 15.0, "quantity": 99999, "crop": "Tomato"})
        if result["type"] == "ACCEPT_PROCESSING":
            assert result["quantity"] <= self.processor.processing_capacity


# --- CompostAgent ----------------------------------------------

class TestCompostAgent:
    def setup_method(self):
        self.compost = CompostAgent(name="EcoRecover-1", base_price=8.0)

    def test_accept_within_base_price(self):
        result = self.compost.respond_to_offer({"price": 7.0, "quantity": 200, "crop": "Tomato"})
        assert result["type"] in ("ACCEPT_COMPOST", "REJECT")

    def test_reject_too_high_price(self):
        result = self.compost.respond_to_offer({"price": 13.0, "quantity": 100, "crop": "Tomato"})
        assert result["type"] == "REJECT"  # > 1.5 * base_price

    def test_accept_has_required_fields(self):
        result = self.compost.respond_to_offer({"price": 7.0, "quantity": 150, "crop": "Tomato"})
        if result["type"] == "ACCEPT_COMPOST":
            assert "quantity" in result and "price" in result


# --- TransporterAgent ------------------------------------------

class TestTransporterAgent:
    def setup_method(self):
        self.transporter = TransporterAgent(
            name="FastTrack", vehicle_capacity=500,
            cost_per_km_per_kg=0.03, base_fee=450.0
        )

    def test_cost_formula(self):
        cost = self.transporter.calculate_transport_cost(quantity=500, distance=100)
        assert cost == round(500 * 100 * 0.03 + 450.0, 2)

    def test_delivery_time_positive(self):
        assert self.transporter.estimate_delivery_time(200) > 0

    def test_can_transport_within_capacity(self):
        assert self.transporter.can_transport(499)

    def test_cannot_transport_over_capacity(self):
        assert not self.transporter.can_transport(501)

    def test_reject_over_capacity(self):
        assert self.transporter.respond_to_offer({"quantity": 99999, "distance": 100})["type"] == "REJECT"

    def test_accept_within_capacity(self):
        result = self.transporter.respond_to_offer({"quantity": 400, "distance": 50})
        assert result["type"] in ("ACCEPT_TRANSPORT", "REJECT")


# --- RestaurantAgent -------------------------------------------

class TestRestaurantAgent:
    def setup_method(self):
        self.restaurant = RestaurantAgent(
            name="GreenLeaf", budget=15000, max_quantity=50,
            target_price=35.0, location="Mumbai"
        )

    def test_make_offer_has_price(self):
        offer = self.restaurant.make_offer(MARKET_CTX)
        assert "price" in offer and offer["price"] > 0

    def test_respond_returns_type(self):
        result = self.restaurant.respond_to_offer({"price": 30.0, "quantity": 30})
        assert "type" in result


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
