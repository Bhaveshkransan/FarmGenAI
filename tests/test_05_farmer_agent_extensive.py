"""
tests/test_05_farmer_agent_extensive.py
------------------------------------------------------------------------
Level 1-15 Test Matrix for Farmer Agent Overhaul.
Validates multi-variable logic, hallucination protection, adversarial inputs, and edge cases.
"""
import sys, os, math
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import pytest

import agents.farmer_agent as _fa_mod
# Force deterministic mode for tests
_fa_mod.llm_client = None

from agents.farmer_agent import FarmerAgent

MARKET_CTX = {"market_price": 20.0, "round": 1}

class TestFarmerAgentExtensive:

    def setup_method(self):
        # Base setup: F01 Initialization check
        self.farmer = FarmerAgent(
            name="Ritik",
            crop="Tomato",
            quantity=1000,
            min_price=20.0,
            shelf_life=5,
            location="Nashik",
            min_sale_quantity=100,
            initial_price=30.0 # Deterministic
        )

    # ==========================================
    # LEVEL 1: BASIC TESTS (F01 - F06)
    # ==========================================
    def test_F01_initialization(self):
        assert self.farmer.agent_type == "farmer"
        assert self.farmer.crop == "Tomato"
        assert self.farmer.quantity == 1000
        assert self.farmer.min_price == 20.0
        assert self.farmer.shelf_life == 5
        assert self.farmer.location == "Nashik"
        assert self.farmer.current_price == 30.0

    def test_F02_initial_offer(self):
        offer = self.farmer.make_offer()
        assert offer["price"] == 30.0
        assert offer["quantity"] == 1000

    def test_F03_offer_exactly_at_target(self):
        resp = self.farmer.respond_to_offer({"price": 30.0, "quantity": 500}, MARKET_CTX, force_deterministic=True)
        assert resp["type"] == "ACCEPT"

    def test_F04_offer_slightly_below_target(self):
        # Target = 30. 29.50 is 98.33%, which is >= 98%
        resp = self.farmer.respond_to_offer({"price": 29.50, "quantity": 500}, MARKET_CTX, force_deterministic=True)
        assert resp["type"] == "ACCEPT"

    def test_F05_offer_below_threshold(self):
        # Target = 30. 25 is < 98%, but >= min_price (20)
        resp = self.farmer.respond_to_offer({"price": 25.0, "quantity": 500}, MARKET_CTX, force_deterministic=True)
        assert resp["type"] == "COUNTER"

    def test_F06_extremely_low_offer(self):
        # Offer 15 is < min_price (20)
        resp = self.farmer.respond_to_offer({"price": 15.0, "quantity": 500}, MARKET_CTX, force_deterministic=True)
        assert resp["type"] == "REJECT"

    # ==========================================
    # LEVEL 2: QUANTITY TESTS (F07 - F11)
    # ==========================================
    def test_F07_partial_quantity(self):
        resp = self.farmer.respond_to_offer({"price": 30.0, "quantity": 500}, MARKET_CTX, force_deterministic=True)
        assert resp["type"] == "ACCEPT"
        assert resp["quantity"] == 500
        assert self.farmer.quantity == 500 # Ensure state updated

    def test_F08_quantity_exceeds_available(self):
        resp = self.farmer.respond_to_offer({"price": 30.0, "quantity": 1500}, MARKET_CTX, force_deterministic=True)
        assert resp["type"] == "COUNTER"
        assert resp["quantity"] == 1000 # Counters with max available

    def test_F09_offer_quantity_zero(self):
        resp = self.farmer.respond_to_offer({"price": 30.0, "quantity": 0}, MARKET_CTX, force_deterministic=True)
        assert resp["type"] == "REJECT"

    def test_F10_offer_quantity_negative(self):
        resp = self.farmer.respond_to_offer({"price": 30.0, "quantity": -100}, MARKET_CTX, force_deterministic=True)
        assert resp["type"] == "REJECT"

    def test_F11_below_minimum_sale_quantity(self):
        resp = self.farmer.respond_to_offer({"price": 30.0, "quantity": 50}, MARKET_CTX, force_deterministic=True)
        assert resp["type"] == "REJECT"

    # ==========================================
    # LEVEL 3: SPOILAGE INTELLIGENCE (F12 - F15)
    # ==========================================
    def test_F12_long_shelf_life_rejects_lowball(self):
        self.farmer.shelf_life = 30
        resp = self.farmer.respond_to_offer({"price": 18.0, "quantity": 500}, MARKET_CTX, force_deterministic=True)
        assert resp["type"] == "REJECT" # Should store/hold out

    def test_F14_critical_shelf_life_accepts_discount(self):
        self.farmer.shelf_life = 1
        # Target 30, Min 20, Offer 18. With 1 day left, 18 is >= 20*0.8 (16)
        resp = self.farmer.respond_to_offer({"price": 18.0, "quantity": 500}, MARKET_CTX, force_deterministic=True)
        assert resp["type"] == "ACCEPT"

    def test_F15_already_spoiled(self):
        self.farmer.shelf_life = 0
        resp = self.farmer.respond_to_offer({"price": 30.0, "quantity": 500}, MARKET_CTX, force_deterministic=True)
        assert resp["type"] == "REJECT"

    # ==========================================
    # LEVEL 4 & 5: STORAGE / PROCESSOR INTELLIGENCE
    # ==========================================
    def test_storage_fallback_rejection(self):
        self.farmer.shelf_life = 10
        self.farmer.has_storage_option = True
        resp = self.farmer.respond_to_offer({"price": 18.0, "quantity": 500}, MARKET_CTX, force_deterministic=True)
        assert resp["type"] == "REJECT"
        assert "store the crop" in resp["message"].lower()

    def test_processor_salvage_rejection(self):
        self.farmer.shelf_life = 1
        self.farmer.has_processor_option = True
        # Min 20, processor salvage = 20*0.7 = 14. Offer 12 should be rejected.
        resp = self.farmer.respond_to_offer({"price": 12.0, "quantity": 500}, MARKET_CTX, force_deterministic=True)
        assert resp["type"] == "REJECT"
        assert "salvage value" in resp["message"].lower()

    # ==========================================
    # LEVEL 7: ADVERSARIAL TESTS
    # ==========================================
    def test_adversarial_missing_keys(self):
        assert self.farmer.respond_to_offer({}, MARKET_CTX, force_deterministic=True)["type"] == "REJECT"
        
    def test_adversarial_null_price(self):
        assert self.farmer.respond_to_offer({"price": None, "quantity": 500}, MARKET_CTX, force_deterministic=True)["type"] == "REJECT"
        
    def test_adversarial_string_price(self):
        assert self.farmer.respond_to_offer({"price": "₹100", "quantity": 500}, MARKET_CTX, force_deterministic=True)["type"] == "REJECT"
        
    def test_adversarial_negative_price(self):
        assert self.farmer.respond_to_offer({"price": -500, "quantity": 500}, MARKET_CTX, force_deterministic=True)["type"] == "REJECT"
        
    def test_adversarial_nan_infinity(self):
        assert self.farmer.respond_to_offer({"price": float("nan"), "quantity": 500}, MARKET_CTX, force_deterministic=True)["type"] == "REJECT"
        assert self.farmer.respond_to_offer({"price": float("inf"), "quantity": 500}, MARKET_CTX, force_deterministic=True)["type"] == "REJECT"

    # ==========================================
    # LEVEL 8 & 9: LLM HALLUCINATION PROTECTION
    # ==========================================
    def test_llm_hallucination_accept_below_min(self, monkeypatch):
        # Force LLM to blindly accept an absurdly low offer
        def mock_think(*args, **kwargs):
            return {"decision": "ACCEPT", "counter_price": 5.0, "reason": "Hallucinated reason"}
        monkeypatch.setattr(self.farmer, "think", mock_think)
        
        # Enable LLM client flag
        _fa_mod.llm_client = True 
        
        self.farmer.shelf_life = 10 # Not desperate
        resp = self.farmer.respond_to_offer({"price": 5.0, "quantity": 500}, MARKET_CTX, force_deterministic=False)
        
        # The business layer should override the ACCEPT and turn it into a COUNTER
        # because 5.0 is < min_price (20) and not desperate
        assert resp["type"] == "COUNTER"
        assert resp["price"] >= 20.0
        assert "override" in resp["message"].lower()

    def test_llm_hallucination_counter_lower_than_offer(self, monkeypatch):
        # Force LLM to counter with an absurdly low price
        def mock_think(*args, **kwargs):
            return {"decision": "COUNTER", "counter_price": -50.0, "reason": "Hallucinated logic"}
        monkeypatch.setattr(self.farmer, "think", mock_think)
        
        _fa_mod.llm_client = True 
        
        resp = self.farmer.respond_to_offer({"price": 10.0, "quantity": 500}, MARKET_CTX, force_deterministic=False)
        assert resp["type"] == "REJECT" # Business layer failsafe rejects low offers
