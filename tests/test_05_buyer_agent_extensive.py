"""
tests/test_05_buyer_agent_extensive.py
------------------------------------------------------------------------
Level 1-25 Test Matrix for Autonomous Buyer Agent Overhaul.
Validates:
  - Multi-attribute utility scoring
  - Budget boundaries & reservation ceilings (P_max)
  - Concession curve progression (Boulware, Linear, Conceder)
  - Spoilage risk exploitation & perishable discount logic
  - Adversarial inputs (NaN, Inf, negative prices, type violations)
  - Monotonicity & hallucination guardrails
"""

import sys
import os
import math
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import agents.base_agent as _base_mod
import agents.buyer_agent as _ba_mod

# Force deterministic mode for tests
_base_mod.llm_client = None
_ba_mod.llm_client = None

from agents.buyer_agent import BuyerAgent

MARKET_CTX = {"market_price": 22.0, "round": 1, "max_rounds": 5}


class TestBuyerAgentExtensive(unittest.TestCase):

    def setUp(self):
        # Standard benchmark buyer: Target ₹20, Ceiling ₹25, Budget ₹20,000, Max 1000kg
        self.buyer = BuyerAgent(
            name="BhaveshProcurement",
            budget=20000.0,
            max_quantity=1000.0,
            target_price=20.0,
            location="Pune",
            reservation_price=25.0,
            strategy="balanced",
            min_shelf_life=3,
        )

    # =========================================================================
    # LEVEL 1: INITIALIZATION & BASELINE OFFERS (B01 - B05)
    # =========================================================================

    def test_B01_initialization(self):
        assert self.buyer.agent_type == "buyer"
        assert self.buyer.budget == 20000.0
        assert self.buyer.max_quantity == 1000.0
        assert self.buyer.target_price == 20.0
        assert self.buyer.reservation_price == 25.0
        assert self.buyer.location == "Pune"
        assert self.buyer.strategy == "balanced"
        assert self.buyer.inventory == 0.0

    def test_B02_default_reservation_price(self):
        b = BuyerAgent("DefaultCeiling", budget=10000, max_quantity=500, target_price=20.0)
        # Default allows up to 20% premium above target
        assert b.reservation_price == 24.0

    def test_B03_custom_reservation_price(self):
        b = BuyerAgent("CustomCeiling", budget=10000, max_quantity=500, target_price=20.0, reservation_price=22.5)
        assert b.reservation_price == 22.5

    def test_B04_initial_make_offer(self):
        offer = self.buyer.make_offer(MARKET_CTX)
        assert "price" in offer and "quantity" in offer and "message" in offer
        # Opening bid should be discounted below target price
        assert offer["price"] < self.buyer.target_price
        assert offer["price"] > 0
        assert 0 < offer["quantity"] <= self.buyer.max_quantity

    def test_B05_accept_at_or_below_target(self):
        resp = self.buyer.respond_to_offer({"price": 20.0, "quantity": 500}, MARKET_CTX, force_deterministic=True)
        assert resp["type"] == "ACCEPT"
        assert resp["price"] == 20.0

    # =========================================================================
    # LEVEL 2: OPERATIONAL MARGINS & CONCESSIONS (B06 - B10)
    # =========================================================================

    def test_B06_accept_within_three_percent_tolerance(self):
        # 20.0 * 1.03 = 20.60
        resp = self.buyer.respond_to_offer({"price": 20.50, "quantity": 500}, MARKET_CTX, force_deterministic=True)
        assert resp["type"] == "ACCEPT"

    def test_B07_counter_above_target_below_reservation(self):
        resp = self.buyer.respond_to_offer({"price": 23.0, "quantity": 500}, MARKET_CTX, force_deterministic=True)
        assert resp["type"] == "COUNTER"
        assert resp["price"] <= self.buyer.reservation_price
        assert resp["price"] < 23.0

    def test_B08_counter_never_exceeds_reservation_ceiling(self):
        for seller_price in [24.0, 24.9, 25.0, 26.0, 28.0]:
            resp = self.buyer.respond_to_offer({"price": seller_price, "quantity": 200}, MARKET_CTX, force_deterministic=True)
            if resp["type"] == "COUNTER":
                assert resp["price"] <= self.buyer.reservation_price, (
                    f"CEILING VIOLATION: counter={resp['price']} > reservation={self.buyer.reservation_price}"
                )

    def test_B09_monotonicity_counter_strictly_below_seller_offer(self):
        for seller_price in [21.0, 22.0, 23.5, 24.8]:
            resp = self.buyer.respond_to_offer({"price": seller_price, "quantity": 300}, MARKET_CTX, force_deterministic=True)
            if resp["type"] == "COUNTER":
                assert resp["price"] < seller_price, "Buyer counter must be strictly below seller ask"

    def test_B10_final_round_resolution_accepts_if_within_reservation(self):
        ctx = {"market_price": 22.0, "round": 5, "max_rounds": 5}
        resp = self.buyer.respond_to_offer({"price": 24.0, "quantity": 400}, ctx, force_deterministic=True)
        assert resp["type"] == "ACCEPT"

    # =========================================================================
    # LEVEL 3: BUDGET CEILINGS & FINANCIAL GUARDRAILS (B11 - B15)
    # =========================================================================

    def test_B11_budget_non_negative_after_accept(self):
        initial = self.buyer.budget
        resp = self.buyer.respond_to_offer({"price": 19.0, "quantity": 800}, MARKET_CTX, force_deterministic=True)
        assert resp["type"] == "ACCEPT"
        assert self.buyer.budget >= 0.0
        assert self.buyer.budget == round(initial - (800 * 19.0), 2)

    def test_B12_inventory_incrementation(self):
        resp = self.buyer.respond_to_offer({"price": 18.0, "quantity": 600}, MARKET_CTX, force_deterministic=True)
        assert resp["type"] == "ACCEPT"
        assert self.buyer.inventory == 600.0

    def test_B13_partial_batch_purchase_capping(self):
        # Buyer with small budget of ₹5,000 offered 500kg at ₹20 = ₹10,000
        poor_buyer = BuyerAgent("BudgetConstrained", budget=5000.0, max_quantity=1000, target_price=20.0)
        resp = poor_buyer.respond_to_offer({"price": 20.0, "quantity": 500}, MARKET_CTX, force_deterministic=True)
        assert resp["type"] == "ACCEPT"
        # Should buy 250kg = ₹5,000, not the full 500kg
        assert resp["quantity"] == 250.0
        assert poor_buyer.budget >= 0.0

    def test_B14_unaffordable_single_unit_rejection(self):
        tiny_buyer = BuyerAgent("Penniless", budget=10.0, max_quantity=100, target_price=20.0)
        resp = tiny_buyer.respond_to_offer({"price": 20.0, "quantity": 50}, MARKET_CTX, force_deterministic=True)
        assert resp["type"] == "REJECT"

    def test_B15_quantity_never_exceeds_max_quantity(self):
        rich_buyer = BuyerAgent("Wealthy", budget=1000000.0, max_quantity=300.0, target_price=20.0)
        resp = rich_buyer.respond_to_offer({"price": 19.0, "quantity": 5000}, MARKET_CTX, force_deterministic=True)
        assert resp["type"] == "ACCEPT"
        assert resp["quantity"] <= 300.0

    # =========================================================================
    # LEVEL 4: FRESHNESS, SPOILAGE & STRATEGY CURVES (B16 - B20)
    # =========================================================================

    def test_B16_rejection_of_spoiled_produce(self):
        resp = self.buyer.respond_to_offer(
            {"price": 15.0, "quantity": 200, "shelf_life": 0}, MARKET_CTX, force_deterministic=True
        )
        assert resp["type"] == "REJECT"
        assert "spoiled" in resp["message"].lower()

    def test_B17_spoilage_discount_counter(self):
        # Shelf life 1 day remaining -> buyer demands discounted price
        resp = self.buyer.respond_to_offer(
            {"price": 22.0, "quantity": 200, "shelf_life": 1}, MARKET_CTX, force_deterministic=True
        )
        assert resp["type"] == "COUNTER"
        assert resp["price"] <= self.buyer.target_price * 0.90

    def test_B18_strategy_concession_curves(self):
        b_boulware = BuyerAgent("Boulware", budget=20000, max_quantity=500, target_price=20.0, strategy="boulware")
        b_conceder = BuyerAgent("Conceder", budget=20000, max_quantity=500, target_price=20.0, strategy="conceder")

        ctx_round_1 = {"market_price": 22.0, "round": 1, "max_rounds": 5}
        resp_boulware = b_boulware.respond_to_offer({"price": 23.0, "quantity": 300}, ctx_round_1, force_deterministic=True)
        resp_conceder = b_conceder.respond_to_offer({"price": 23.0, "quantity": 300}, ctx_round_1, force_deterministic=True)

        assert resp_boulware["type"] == "COUNTER"
        assert resp_conceder["type"] == "COUNTER"
        # Boulware should be firmer (lower counter price) than Conceder in early rounds
        assert resp_boulware["price"] <= resp_conceder["price"]

    def test_B19_multi_attribute_utility_scoring(self):
        # Target price = 20, Reservation = 25
        u_perfect = self.buyer.calculate_utility(price=20.0, quantity=1000.0, shelf_life=10)
        u_compromise = self.buyer.calculate_utility(price=23.0, quantity=1000.0, shelf_life=10)
        u_above_ceiling = self.buyer.calculate_utility(price=26.0, quantity=1000.0, shelf_life=10)
        u_spoiled = self.buyer.calculate_utility(price=18.0, quantity=1000.0, shelf_life=0)

        assert u_perfect == 1.0
        assert 0.0 < u_compromise < 1.0
        assert u_above_ceiling == 0.0
        assert u_spoiled == 0.0

    def test_B20_astronomical_price_rejection(self):
        # Reservation price is 25. An offer of 100 is 4x ceiling -> immediate REJECT
        resp = self.buyer.respond_to_offer({"price": 100.0, "quantity": 500}, MARKET_CTX, force_deterministic=True)
        assert resp["type"] == "REJECT"

    # =========================================================================
    # LEVEL 5: ADVERSARIAL INPUTS & ROBUSTNESS (B21 - B25)
    # =========================================================================

    def test_B21_reject_nan_price(self):
        resp = self.buyer.respond_to_offer({"price": float("nan"), "quantity": 500}, MARKET_CTX, force_deterministic=True)
        assert resp["type"] == "REJECT"

    def test_B22_reject_inf_price(self):
        resp = self.buyer.respond_to_offer({"price": float("inf"), "quantity": 500}, MARKET_CTX, force_deterministic=True)
        assert resp["type"] == "REJECT"

    def test_B23_reject_negative_and_zero_price(self):
        for invalid_price in [-10.0, 0.0]:
            resp = self.buyer.respond_to_offer({"price": invalid_price, "quantity": 500}, MARKET_CTX, force_deterministic=True)
            assert resp["type"] == "REJECT"

    def test_B24_reject_malformed_non_dict_offer(self):
        for malformed in [None, "invalid_string", [10, 20], 42]:
            resp = self.buyer.respond_to_offer(malformed, MARKET_CTX, force_deterministic=True)
            assert resp["type"] == "REJECT"

    def test_B25_reject_missing_fields(self):
        resp_no_price = self.buyer.respond_to_offer({"quantity": 500}, MARKET_CTX, force_deterministic=True)
        resp_no_qty = self.buyer.respond_to_offer({"price": 20.0}, MARKET_CTX, force_deterministic=True)
        assert resp_no_price["type"] == "REJECT"
        assert resp_no_qty["type"] == "REJECT"

    # =========================================================================
    # LEVEL 6: BUYER PERSONAS & DIFFERENTIATED UTILITY (B26 - B28)
    # =========================================================================

    def test_B26_buyer_personas_initialization(self):
        supermarket = BuyerAgent("Supermarket", budget=50000, max_quantity=2000, target_price=20.0, persona="retail_supermarket")
        wholesaler = BuyerAgent("Wholesaler", budget=100000, max_quantity=5000, target_price=18.0, persona="bulk_wholesaler")
        processor = BuyerAgent("Processor", budget=75000, max_quantity=4000, target_price=16.0, persona="food_processor")
        restaurant = BuyerAgent("Kitchen", budget=20000, max_quantity=500, target_price=22.0, persona="restaurant_kitchen")

        assert supermarket.strategy == "boulware"
        assert supermarket.weights["freshness"] == 0.30
        assert wholesaler.strategy == "aggressive"
        assert wholesaler.weights["price"] == 0.75
        assert processor.strategy == "conceder"
        assert processor.weights["quantity"] == 0.35
        assert restaurant.strategy == "balanced"
        assert restaurant.weights["freshness"] == 0.30

    def test_B27_persona_differential_utility(self):
        supermarket = BuyerAgent("Supermarket", budget=50000, max_quantity=1000, target_price=20.0, persona="retail_supermarket")
        processor = BuyerAgent("Processor", budget=50000, max_quantity=1000, target_price=20.0, persona="food_processor")

        # Produce with lower shelf life (2 days)
        u_supermarket = supermarket.calculate_utility(price=20.0, quantity=1000, shelf_life=2)
        u_processor = processor.calculate_utility(price=20.0, quantity=1000, shelf_life=2)

        # Supermarket penalizes decay much more heavily than the processing plant
        assert u_processor > u_supermarket

    def test_B28_custom_fallback_persona(self):
        custom = BuyerAgent("Custom", budget=10000, max_quantity=500, target_price=20.0, persona="unknown_persona")
        assert custom.persona == "custom"
        assert custom.weights["price"] == 0.60

    # =========================================================================
    # LEVEL 7: DYNAMIC BATNA & MANDI PRICE GROUNDING (B29 - B31)
    # =========================================================================

    def test_B29_batna_calculation(self):
        b = BuyerAgent("BATNATest", budget=20000, max_quantity=1000, target_price=20.0, reservation_price=26.0)
        # With market price ₹21.00 and buffer ₹1.50 -> BATNA is 22.50 (< reservation 26.0)
        batna = b.calculate_batna(market_price=21.0, transport_buffer=1.50)
        assert batna == 22.50

        # When market price is higher than reservation price, reservation price dominates
        batna_capped = b.calculate_batna(market_price=30.0, transport_buffer=1.50)
        assert batna_capped == 26.0

        # Without market price, returns reservation price
        assert b.calculate_batna(None) == 26.0

    def test_B30_counter_bounded_by_batna(self):
        # Reservation price is 28, but market price is 20 -> BATNA is 21.50
        b = BuyerAgent("BATNABounded", budget=20000, max_quantity=1000, target_price=18.0, reservation_price=28.0)
        ctx = {"market_price": 20.0, "round": 3, "max_rounds": 5}
        resp = b.respond_to_offer({"price": 25.0, "quantity": 500}, ctx, force_deterministic=True)
        if resp["type"] == "COUNTER":
            batna = b.calculate_batna(20.0)
            assert resp["price"] <= batna

    def test_B31_seller_concession_tracking(self):
        b = BuyerAgent("Tracker", budget=20000, max_quantity=1000, target_price=20.0)
        ctx = {"market_price": 22.0, "round": 1}
        b.respond_to_offer({"price": 24.0, "quantity": 500}, ctx, force_deterministic=True)
        b.respond_to_offer({"price": 23.0, "quantity": 500}, ctx, force_deterministic=True)

        assert len(b.seller_offer_history) == 2
        assert b.seller_offer_history == [24.0, 23.0]

    # =========================================================================
    # LEVEL 8: DIGITAL PURCHASE ORDER (PO) GENERATION (B32 - B35)
    # =========================================================================

    def test_B32_generate_purchase_order_structure(self):
        b = BuyerAgent("CorpProcure", budget=50000, max_quantity=2000, target_price=20.0, persona="retail_supermarket")
        po = b.generate_purchase_order(price=19.50, quantity=1000, seller_name="RameshFarmer", context={"crop": "Onion"})

        assert po["po_number"].startswith("PO-")
        assert po["buyer_name"] == "CorpProcure"
        assert po["buyer_persona"] == "retail_supermarket"
        assert po["seller_name"] == "RameshFarmer"
        assert po["crop"] == "Onion"
        assert po["agreed_price"] == 19.50
        assert po["agreed_quantity"] == 1000
        assert po["total_value"] == 19500.0
        assert po["status"] == "ISSUED"
        assert "timestamp" in po

    def test_B33_po_contract_attached_to_accept_response(self):
        b = BuyerAgent("DealCloser", budget=30000, max_quantity=1000, target_price=22.0)
        resp = b.respond_to_offer(
            {"price": 21.0, "quantity": 500},
            {"market_price": 22.0, "round": 1, "seller_name": "SureshFarmer", "crop": "Soybean"},
            force_deterministic=True,
        )
        assert resp["type"] == "ACCEPT"
        assert "contract" in resp
        contract = resp["contract"]
        assert contract["po_number"].startswith("PO-")
        assert contract["seller_name"] == "SureshFarmer"
        assert contract["crop"] == "Soybean"
        assert contract["agreed_price"] == 21.0
        assert contract["agreed_quantity"] == 500

    def test_B34_contracts_persisted_in_agent_memory(self):
        b = BuyerAgent("AuditAgent", budget=50000, max_quantity=1000, target_price=25.0)
        assert len(b.generated_contracts) == 0
        b.respond_to_offer({"price": 22.0, "quantity": 200}, MARKET_CTX, force_deterministic=True)
        assert len(b.generated_contracts) == 1
        assert b.generated_contracts[0]["total_value"] == 4400.0

    def test_B35_reciprocal_tit_for_tat_stubborn_seller(self):
        b_stubborn = BuyerAgent("FirmBuyer", budget=20000, max_quantity=500, target_price=18.0, reservation_price=25.0)
        # Offer 1: 24.0, Offer 2: 24.0 (Seller conceded 0.0 -> stubborn)
        ctx1 = {"market_price": 20.0, "round": 1, "max_rounds": 5}
        ctx2 = {"market_price": 20.0, "round": 2, "max_rounds": 5}
        resp1 = b_stubborn.respond_to_offer({"price": 24.0, "quantity": 500}, ctx1, force_deterministic=True)
        resp2 = b_stubborn.respond_to_offer({"price": 24.0, "quantity": 500}, ctx2, force_deterministic=True)

        assert resp1["type"] == "COUNTER"
        assert resp2["type"] == "COUNTER"
        # Buyer should barely move or remain restrained in round 2 due to stubborn seller
        assert resp2["price"] <= resp1["price"] + 0.8

    # =========================================================================
    # LEVEL 8: COGNITIVE RESILIENCE & PRIVACY (B36 - B39)
    # =========================================================================

    def test_B36_sanitize_xml_tags(self):
        b = BuyerAgent("XmlBuyer", budget=20000, max_quantity=500, target_price=20.0, reservation_price=24.0)
        parsed = b._sanitize_llm_dict({
            "decision": "COUNTER",
            "counter_price": "21.75",
            "reason": "Offering higher counter due to high quality."
        })
        assert parsed["decision"] == "COUNTER"
        assert parsed["counter_price"] == 21.75

    def test_B37_sanitize_currency_symbols(self):
        b = BuyerAgent("CurrencyBuyer", budget=20000, max_quantity=500, target_price=20.0, reservation_price=24.0)
        parsed = b._sanitize_llm_dict({
            "decision": "counter",
            "counter_price": "₹22.50/kg",
            "reason": "Market average is ₹20."
        })
        assert parsed["decision"] == "COUNTER"
        assert parsed["counter_price"] == 22.50

    def test_B38_sanitize_reservation_price_privacy(self):
        b = BuyerAgent("PrivateBuyer", budget=20000, max_quantity=500, target_price=20.0, reservation_price=24.0)
        parsed = b._sanitize_llm_dict({
            "decision": "COUNTER",
            "counter_price": 22.0,
            "reason": "My maximum ceiling is 24.0, so I counter with 22.0."
        })
        # Ceiling 24.0 should be scrubbed from public explanation
        assert "24.0" not in parsed["reason"]
        assert "[confidential threshold]" in parsed["reason"]


if __name__ == "__main__":
    unittest.main()
