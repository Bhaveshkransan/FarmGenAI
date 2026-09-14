"""
tests/test_05_buyer_profile_economic_state.py
------------------------------------------------------------------------
Verification Suite for Phase 2: Buyer Profile, Economic State, Budget Guardrails & BATNA.

Tests:
  - Four canonical Buyer Personas (retail_supermarket, bulk_wholesaler, food_processor, restaurant_kitchen)
  - Persona preference weighting (price, quantity, freshness, quality)
  - Multi-attribute utility scoring with quality grade modulation
  - Resolution of Quantity Under-Budget Bug (zero units affordable must trigger REJECT, never clamped to 1)
  - True BATNA vs Market-Reference Heuristic distinction
  - ZOPA validation without inventing seller reservation prices
  - Target price and reservation ceiling (P_max) economic invariants
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agents.buyer_agent import BuyerAgent, BUYER_PERSONAS

# Force deterministic testing
import agents.buyer_agent as _ba_mod
_ba_mod.llm_client = None


class TestBuyerProfileEconomicState(unittest.TestCase):

    # =========================================================================
    # 1. BUYER PERSONAS INITIALIZATION & CONFIGURATION
    # =========================================================================

    def test_all_four_buyer_personas_registered(self):
        expected_personas = ["retail_supermarket", "bulk_wholesaler", "food_processor", "restaurant_kitchen"]
        for p in expected_personas:
            self.assertIn(p, BUYER_PERSONAS)
            self.assertIn("weights", BUYER_PERSONAS[p])
            self.assertIn("strategy", BUYER_PERSONAS[p])
            self.assertIn("min_shelf_life", BUYER_PERSONAS[p])

    def test_persona_profiles_behavioral_differentiation(self):
        supermarket = BuyerAgent("Supermarket", budget=50000, max_quantity=2000, target_price=20.0, persona="retail_supermarket")
        wholesaler = BuyerAgent("Wholesaler", budget=100000, max_quantity=5000, target_price=18.0, persona="bulk_wholesaler")
        processor = BuyerAgent("Processor", budget=75000, max_quantity=4000, target_price=16.0, persona="food_processor")
        restaurant = BuyerAgent("Kitchen", budget=20000, max_quantity=500, target_price=22.0, persona="restaurant_kitchen")

        # Wholesaler prioritizes price discounts above all
        self.assertGreater(wholesaler.weights["price"], 0.70)
        self.assertEqual(wholesaler.strategy, "aggressive")

        # Food processor accepts short shelf-life and prioritizes volume
        self.assertEqual(processor.min_shelf_life, 1)
        self.assertGreater(processor.weights["quantity"], 0.30)
        self.assertEqual(processor.strategy, "conceder")

        # Retail supermarket requires longer shelf life
        self.assertEqual(supermarket.min_shelf_life, 4)
        self.assertEqual(supermarket.strategy, "boulware")

        # Restaurant requires balanced freshness and steady batches
        self.assertEqual(restaurant.weights["freshness"], 0.30)
        self.assertEqual(restaurant.strategy, "balanced")

    # =========================================================================
    # 2. MULTI-ATTRIBUTE UTILITY & QUALITY GRADE MODULATION
    # =========================================================================

    def test_utility_scoring_with_quality_grade(self):
        supermarket = BuyerAgent("Supermarket", budget=50000, max_quantity=1000, target_price=20.0, persona="retail_supermarket")
        processor = BuyerAgent("Processor", budget=50000, max_quantity=1000, target_price=20.0, persona="food_processor")

        # Grade A produce gets maximum quality multiplier
        u_sup_grade_a = supermarket.calculate_utility(price=20.0, quantity=1000, shelf_life=5, quality_grade="A")
        u_sup_grade_c = supermarket.calculate_utility(price=20.0, quantity=1000, shelf_life=5, quality_grade="C")

        # Supermarket heavily penalizes Grade C produce
        self.assertGreater(u_sup_grade_a, u_sup_grade_c)
        self.assertLess(u_sup_grade_c, 0.70)

        # Processor accepts Grade C for pulp/crushing with much higher utility than retail
        u_proc_grade_c = processor.calculate_utility(price=20.0, quantity=1000, shelf_life=5, quality_grade="C")
        self.assertGreater(u_proc_grade_c, u_sup_grade_c)

    # =========================================================================
    # 3. QUANTITY UNDER-BUDGET BUG RESOLUTION (INSTRUCTION 25)
    # =========================================================================

    def test_make_offer_zero_affordable_quantity_triggers_reject(self):
        # Buyer with budget ₹10 cannot even afford 1 unit of a ₹20 produce
        poor_buyer = BuyerAgent("PennilessBuyer", budget=10.0, max_quantity=100, target_price=20.0)
        offer = poor_buyer.make_offer({"market_price": 25.0})

        # MUST NOT force quantity to 1.0!
        self.assertEqual(offer.get("quantity"), 0.0)
        self.assertEqual(offer.get("price"), 0.0)
        self.assertEqual(offer.get("type"), "REJECT")
        self.assertEqual(offer.get("error"), "INSUFFICIENT_BUDGET")

    def test_counter_zero_affordable_quantity_triggers_reject(self):
        # Buyer with budget ₹15 offered produce at ₹25 with counter price > ₹15
        tight_buyer = BuyerAgent("TightBudget", budget=15.0, max_quantity=100, target_price=18.0, reservation_price=25.0)
        # Force a counter scenario
        resp = tight_buyer.respond_to_offer(
            {"price": 22.0, "quantity": 10},
            {"market_price": 22.0, "round": 1, "max_rounds": 5},
            force_deterministic=True
        )
        # Because affordable_qty = floor(15 / counter_price) = 0, agent must REJECT, NOT force 1.0
        self.assertEqual(resp["type"], "REJECT")
        self.assertIn("budget", resp["message"].lower())

    def test_accept_zero_affordable_quantity_triggers_reject(self):
        broke_buyer = BuyerAgent("BrokeBuyer", budget=5.0, max_quantity=100, target_price=20.0)
        resp = broke_buyer.respond_to_offer(
            {"price": 18.0, "quantity": 10},
            {"market_price": 20.0, "round": 1},
            force_deterministic=True
        )
        # 18.0 is <= target, but budget is ₹5. Cannot purchase even 1 unit.
        self.assertEqual(resp["type"], "REJECT")
        self.assertIn("budget", resp["message"].lower())

    # =========================================================================
    # 4. TRUE BATNA VS MARKET-REFERENCE HEURISTIC (INSTRUCTION 26)
    # =========================================================================

    def test_true_batna_with_alternative_supplier_quotes(self):
        buyer = BuyerAgent("CorpProcure", budget=50000, max_quantity=1000, target_price=20.0, reservation_price=28.0)
        alt_quotes = [
            {"supplier": "Mandi Vendor A", "price": 23.50},
            {"supplier": "Mandi Vendor B", "price": 22.00},
            {"supplier": "Mandi Vendor C", "price": 24.00},
        ]
        batna = buyer.calculate_batna(market_price=21.0, alternative_offers=alt_quotes)
        # True BATNA is the best outside alternative = ₹22.00
        self.assertEqual(batna, 22.00)
        self.assertEqual(buyer.get_batna_source_type(alt_quotes), "TRUE_ALTERNATIVE_SUPPLIER")

    def test_batna_fallback_designated_as_market_reference_heuristic(self):
        buyer = BuyerAgent("CorpProcure", budget=50000, max_quantity=1000, target_price=20.0, reservation_price=26.0)
        # Without alternative quotes, uses market_price + transport buffer
        batna = buyer.calculate_batna(market_price=21.0, transport_buffer=1.50)
        self.assertEqual(batna, 22.50)
        self.assertEqual(buyer.get_batna_source_type(), "MARKET_REFERENCE_HEURISTIC")

    # =========================================================================
    # 5. ZOPA CALCULATION WITHOUT FABRICATING SELLER MINIMUM (INSTRUCTION 27)
    # =========================================================================

    def test_zopa_positive_overlap(self):
        buyer = BuyerAgent("ZOPABuyer", budget=50000, max_quantity=1000, target_price=20.0, reservation_price=25.0)
        has_zopa, reason = buyer.check_zopa(seller_min_price=22.0)
        self.assertTrue(has_zopa)
        self.assertIn("surplus band of ₹3.0/kg", reason)

    def test_zopa_negative_overlap(self):
        buyer = BuyerAgent("ZOPABuyer", budget=50000, max_quantity=1000, target_price=20.0, reservation_price=25.0)
        has_zopa, reason = buyer.check_zopa(seller_min_price=28.0)
        self.assertFalse(has_zopa)
        self.assertIn("Negative ZOPA", reason)

    def test_zopa_unknown_when_seller_min_not_provided(self):
        buyer = BuyerAgent("ZOPABuyer", budget=50000, max_quantity=1000, target_price=20.0, reservation_price=25.0)
        has_zopa, reason = buyer.check_zopa(seller_min_price=None)
        self.assertTrue(has_zopa)
        self.assertIn("ZOPA status unknown", reason)

    # =========================================================================
    # 6. ECONOMIC INVARIANTS & RESERVATION CEILING
    # =========================================================================

    def test_reservation_ceiling_always_greater_than_or_equal_to_target(self):
        # Even if someone erroneously passes reservation < target, it clamps
        b = BuyerAgent("ClampedBuyer", budget=20000, max_quantity=500, target_price=25.0, reservation_price=20.0)
        self.assertEqual(b.reservation_price, 25.0)
        self.assertGreaterEqual(b.reservation_price, b.target_price)


if __name__ == "__main__":
    unittest.main()
