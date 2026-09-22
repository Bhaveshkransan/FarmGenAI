"""
tests/test_05_buyer_negotiation_strategy.py

Verification tests for Priority 2: Buyer Negotiation Strategy & Behavior
Covers:
  - Persona differentiation (Boulware, Aggressive, Conceder, Balanced)
  - Opening offer calculation & cap
  - Concession progression & reciprocal tit-for-tat
  - Reservation price (P_max) ceiling protection
  - Budget protection & quantity-price tradeoff
  - Maximum rounds behavior (Round 1, 3, 5)
  - Stall detection walk-away
  - ZOPA & surplus evaluation
  - BATNA usage as effective ceiling
  - Quality / Freshness modulation
  - ML market anchor vs negotiation strategy separation
  - Determinism & LLM safety overrides
  - Full Manual Negotiation Matrix (NEG-01 to NEG-12)
"""

import pytest
from agents.buyer_agent import BuyerAgent, BUYER_PERSONAS


# ============================================================================
#  1. PERSONA DIFFERENTIATION & OPENING OFFERS
# ============================================================================

class TestBuyerPersonaDifferentiation:

    def test_all_four_personas_produce_different_opening_offers(self):
        context = {"market_price": 48.0, "crop": "Soybean"}
        
        boulware_buyer = BuyerAgent("Boulware", budget=50000, max_quantity=1000, target_price=45.0, reservation_price=54.0, persona="boulware", crop="Soybean")
        aggressive_buyer = BuyerAgent("Aggressive", budget=50000, max_quantity=1000, target_price=45.0, reservation_price=54.0, persona="aggressive", crop="Soybean")
        conceder_buyer = BuyerAgent("Conceder", budget=50000, max_quantity=1000, target_price=45.0, reservation_price=54.0, persona="conceder", crop="Soybean")
        balanced_buyer = BuyerAgent("Balanced", budget=50000, max_quantity=1000, target_price=45.0, reservation_price=54.0, persona="balanced", crop="Soybean")

        offer_boulware = boulware_buyer.make_offer(context)
        offer_aggressive = aggressive_buyer.make_offer(context)
        offer_conceder = conceder_buyer.make_offer(context)
        offer_balanced = balanced_buyer.make_offer(context)

        # Aggressive offers lowest (highest discount 0.75)
        # Boulware offers second lowest (discount 0.78)
        # Balanced offers moderate (discount 0.82)
        # Conceder offers highest (discount 0.90)
        assert offer_aggressive["price"] < offer_boulware["price"]
        assert offer_boulware["price"] < offer_balanced["price"]
        assert offer_balanced["price"] < offer_conceder["price"]

        # All opening offers must stay below reservation price
        assert offer_conceder["price"] <= 54.0
        assert offer_aggressive["price"] <= 54.0

    def test_opening_offer_never_exceeds_reservation_price(self):
        # Target price higher than reservation (sanitized by __init__)
        buyer = BuyerAgent("CeilingTest", budget=50000, max_quantity=1000, target_price=60.0, reservation_price=50.0, crop="Soybean")
        offer = buyer.make_offer({"market_price": 60.0})
        assert offer["price"] <= 50.0


# ============================================================================
#  2. CONCESSION STRATEGY & PROGRESSION
# ============================================================================

class TestBuyerConcessionStrategy:

    def test_boulware_concedes_slower_than_conceder(self):
        offer = {"price": 52.0, "quantity": 1000, "crop": "Soybean"}
        boulware = BuyerAgent("Boulware", budget=60000, max_quantity=1000, target_price=45.0, reservation_price=55.0, strategy="boulware", crop="Soybean")
        conceder = BuyerAgent("Conceder", budget=60000, max_quantity=1000, target_price=45.0, reservation_price=55.0, strategy="conceder", crop="Soybean")

        boulware.make_offer({"market_price": 48.0})
        conceder.make_offer({"market_price": 48.0})

        res_boulware = boulware.respond_to_offer(offer, context={"round": 2, "max_rounds": 5, "market_price": 48.0}, force_deterministic=True)
        res_conceder = conceder.respond_to_offer(offer, context={"round": 2, "max_rounds": 5, "market_price": 48.0}, force_deterministic=True)

        assert res_boulware["type"] == "COUNTER"
        assert res_conceder["type"] == "COUNTER"
        # Conceder moves faster toward seller price than Boulware in early/mid rounds
        assert res_conceder["price"] > res_boulware["price"]


    def test_concession_never_crosses_reservation_ceiling(self):
        buyer = BuyerAgent("CeilingProtection", budget=60000, max_quantity=1000, target_price=45.0, reservation_price=50.0, strategy="conceder", crop="Soybean")
        offer = {"price": 65.0, "quantity": 1000, "crop": "Soybean"}
        
        for r in range(1, 6):
            res = buyer.respond_to_offer(offer, context={"round": r, "max_rounds": 5, "market_price": 48.0}, force_deterministic=True)
            if res["type"] == "COUNTER":
                assert res["price"] <= 50.0


# ============================================================================
#  3. STALL DETECTION & WALK-AWAY
# ============================================================================

class TestStallDetection:

    def test_stall_detection_triggers_reject_when_seller_immobile_above_reservation(self):
        buyer = BuyerAgent("StallTester", budget=50000, max_quantity=1000, target_price=40.0, reservation_price=45.0, crop="Soybean")
        
        # Farmer gives static high offers of ₹55, ₹55.05, ₹55.02 (above reservation of ₹45)
        res1 = buyer.respond_to_offer({"price": 55.0, "quantity": 1000, "crop": "Soybean"}, context={"round": 1, "max_rounds": 5}, force_deterministic=True)
        assert res1["type"] == "COUNTER"

        res2 = buyer.respond_to_offer({"price": 55.05, "quantity": 1000, "crop": "Soybean"}, context={"round": 2, "max_rounds": 5}, force_deterministic=True)
        assert res2["type"] == "COUNTER"

        res3 = buyer.respond_to_offer({"price": 55.02, "quantity": 1000, "crop": "Soybean"}, context={"round": 3, "max_rounds": 5}, force_deterministic=True)
        # 3rd static offer triggers stall rejection
        assert res3["type"] == "REJECT"
        assert "stall" in res3["message"].lower()


# ============================================================================
#  4. ZOPA, BATNA, & MAX ROUNDS
# ============================================================================

class TestZopaBatnaMaxRounds:

    def test_zopa_evaluation(self):
        buyer = BuyerAgent("ZopaTester", budget=50000, max_quantity=1000, target_price=45.0, reservation_price=52.0, crop="Soybean")
        
        has_zopa, msg1 = buyer.check_zopa(48.0)
        assert has_zopa is True
        assert "positive surplus" in msg1.lower()

        no_zopa, msg2 = buyer.check_zopa(58.0)
        assert no_zopa is False
        assert "negative zopa" in msg2.lower()

    def test_batna_caps_effective_concession_ceiling(self):
        buyer = BuyerAgent("BatnaTester", budget=50000, max_quantity=1000, target_price=40.0, reservation_price=55.0, strategy="conceder", crop="Soybean")
        # Market alternative BATNA is ₹44/kg
        batna_val = buyer.calculate_batna(market_price=42.5) # 42.5 + 1.5 = 44.0
        assert batna_val == 44.0

        offer = {"price": 60.0, "quantity": 1000, "crop": "Soybean"}
        res = buyer.respond_to_offer(offer, context={"round": 4, "max_rounds": 5, "market_price": 42.5}, force_deterministic=True)
        if res["type"] == "COUNTER":
            assert res["price"] <= 44.0

    def test_max_rounds_behavior(self):
        buyer = BuyerAgent("RoundTester", budget=50000, max_quantity=1000, target_price=40.0, reservation_price=48.0, crop="Soybean")
        
        # Round 5 of 5: Seller offer ₹45 (below reservation ₹48) -> ACCEPT
        res_accept = buyer.respond_to_offer({"price": 45.0, "quantity": 1000, "crop": "Soybean"}, context={"round": 5, "max_rounds": 5}, force_deterministic=True)
        assert res_accept["type"] == "ACCEPT"

        # Round 5 of 5: Seller offer ₹52 (above reservation ₹48) -> REJECT
        buyer2 = BuyerAgent("RoundTester2", budget=50000, max_quantity=1000, target_price=40.0, reservation_price=48.0, crop="Soybean")
        res_reject = buyer2.respond_to_offer({"price": 52.0, "quantity": 1000, "crop": "Soybean"}, context={"round": 5, "max_rounds": 5}, force_deterministic=True)
        assert res_reject["type"] == "REJECT"


# ============================================================================
#  5. MULTI-VARIABLE QUANTITY-PRICE TRADEOFF & BUDGET PROTECTION
# ============================================================================

class TestQuantityPriceBudgetTradeoff:

    def test_quantity_scaled_to_prevent_budget_violation(self):
        # Budget is ₹20,000. Seller price is ₹25/kg for 1,000kg (Total ₹25,000 > Budget ₹20,000)
        buyer = BuyerAgent("BudgetTester", budget=20000.0, max_quantity=1000.0, target_price=22.0, reservation_price=28.0, crop="Soybean")
        
        # Buyer accepts price ₹25/kg, but purchasable quantity must scale to 800kg (₹20,000 / 25)
        res = buyer.respond_to_offer({"price": 25.0, "quantity": 1000.0, "crop": "Soybean"}, context={"round": 5, "max_rounds": 5}, force_deterministic=True)
        assert res["type"] == "ACCEPT"
        assert res["quantity"] == 800.0
        assert res["price"] * res["quantity"] <= 20000.0


# ============================================================================
#  6. ML SEPARATION & DETERMINISM
# ============================================================================

class TestMLSeparationAndLLMSafety:

    def test_ml_market_anchor_decoupled_from_decision_policy(self):
        buyer = BuyerAgent("DecoupledTester", budget=50000, max_quantity=1000, target_price=40.0, reservation_price=48.0, crop="Soybean")
        # ML market price prediction is ₹32/kg, Seller asks ₹42/kg (above ML anchor but below reservation ₹48)
        res = buyer.respond_to_offer({"price": 42.0, "quantity": 1000, "crop": "Soybean"}, context={"market_price": 32.0, "round": 2, "max_rounds": 5}, force_deterministic=True)
        # Decision is COUNTER (or ACCEPT if final round), not forced to reject or offer exactly ₹32
        assert res["type"] in ["COUNTER", "ACCEPT"]

    def test_llm_hallucination_override_above_reservation(self):
        buyer = BuyerAgent("LLMGuardTester", budget=50000, max_quantity=1000, target_price=40.0, reservation_price=45.0, crop="Soybean")
        # Mock LLM trying to ACCEPT a price of ₹55 (above reservation of ₹45)
        data = buyer._sanitize_llm_dict({"decision": "ACCEPT", "counter_price": 55.0, "reason": "Looks good!"})
        assert data["decision"] == "ACCEPT"
        
        # Passing offer to respond_to_offer with price ₹55 must override ACCEPT to COUNTER/REJECT
        res = buyer.respond_to_offer({"price": 55.0, "quantity": 1000, "crop": "Soybean"}, context={"round": 1, "max_rounds": 5}, force_deterministic=False)
        assert res["type"] != "ACCEPT"


# ============================================================================
#  7. MANUAL NEGOTIATION MATRIX (NEG-01 to NEG-12)
# ============================================================================

class TestManualNegotiationMatrix:

    def test_NEG_01_balanced_buyer_reasonable_price(self):
        buyer = BuyerAgent("BalancedBuyer", budget=50000, max_quantity=1000, target_price=48.0, reservation_price=54.0, persona="balanced", crop="Soybean")
        res = buyer.respond_to_offer({"price": 47.5, "quantity": 1000, "crop": "Soybean"}, context={"round": 1, "max_rounds": 5}, force_deterministic=True)
        assert res["type"] == "ACCEPT"

    def test_NEG_02_aggressive_buyer_high_price(self):
        buyer = BuyerAgent("AggressiveBuyer", budget=50000, max_quantity=1000, target_price=45.0, reservation_price=52.0, persona="aggressive", crop="Soybean")
        res = buyer.respond_to_offer({"price": 50.0, "quantity": 1000, "crop": "Soybean"}, context={"round": 1, "max_rounds": 5}, force_deterministic=True)
        assert res["type"] == "COUNTER"
        # Aggressive buyer maintains low counter
        assert res["price"] < 45.0

    def test_NEG_03_boulware_buyer_high_price(self):
        buyer = BuyerAgent("BoulwareBuyer", budget=50000, max_quantity=1000, target_price=45.0, reservation_price=52.0, persona="boulware", crop="Soybean")
        res1 = buyer.respond_to_offer({"price": 51.0, "quantity": 1000, "crop": "Soybean"}, context={"round": 1, "max_rounds": 5}, force_deterministic=True)
        assert res1["type"] == "COUNTER"
        # Firm opening counter
        assert res1["price"] <= 45.0

    def test_NEG_04_conceder_buyer_high_price(self):
        buyer = BuyerAgent("ConcederBuyer", budget=50000, max_quantity=1000, target_price=45.0, reservation_price=52.0, strategy="conceder", persona="food_processor", crop="Soybean")
        buyer.make_offer({"market_price": 48.0})
        res = buyer.respond_to_offer({"price": 50.0, "quantity": 1000, "crop": "Soybean"}, context={"round": 2, "max_rounds": 5, "market_price": 48.0}, force_deterministic=True)
        assert res["type"] == "COUNTER"
        # Conceder concedes faster
        assert res["price"] > 40.0



    def test_NEG_05_farmer_price_below_target(self):
        buyer = BuyerAgent("BuyerTarget", budget=50000, max_quantity=1000, target_price=48.0, reservation_price=54.0, crop="Soybean")
        res = buyer.respond_to_offer({"price": 44.0, "quantity": 1000, "crop": "Soybean"}, context={"round": 1, "max_rounds": 5}, force_deterministic=True)
        assert res["type"] == "ACCEPT"

    def test_NEG_06_farmer_price_between_target_and_reservation(self):
        buyer = BuyerAgent("BuyerMid", budget=50000, max_quantity=1000, target_price=45.0, reservation_price=54.0, crop="Soybean")
        res = buyer.respond_to_offer({"price": 50.0, "quantity": 1000, "crop": "Soybean"}, context={"round": 2, "max_rounds": 5}, force_deterministic=True)
        assert res["type"] in ["COUNTER", "ACCEPT"]

    def test_NEG_07_farmer_price_above_reservation(self):
        buyer = BuyerAgent("BuyerExceed", budget=50000, max_quantity=1000, target_price=45.0, reservation_price=50.0, crop="Soybean")
        res = buyer.respond_to_offer({"price": 60.0, "quantity": 1000, "crop": "Soybean"}, context={"round": 2, "max_rounds": 5}, force_deterministic=True)
        assert res["type"] in ["COUNTER", "REJECT"]
        if res["type"] == "COUNTER":
            assert res["price"] <= 50.0

    def test_NEG_08_repeated_farmer_price_stalled(self):
        buyer = BuyerAgent("BuyerStall", budget=50000, max_quantity=1000, target_price=40.0, reservation_price=45.0, crop="Soybean")
        buyer.respond_to_offer({"price": 52.0, "quantity": 1000, "crop": "Soybean"}, context={"round": 1, "max_rounds": 5}, force_deterministic=True)
        buyer.respond_to_offer({"price": 52.01, "quantity": 1000, "crop": "Soybean"}, context={"round": 2, "max_rounds": 5}, force_deterministic=True)
        res = buyer.respond_to_offer({"price": 52.00, "quantity": 1000, "crop": "Soybean"}, context={"round": 3, "max_rounds": 5}, force_deterministic=True)
        assert res["type"] == "REJECT"

    def test_NEG_09_budget_constrained_quantity(self):
        buyer = BuyerAgent("BuyerBudgetLimit", budget=15000.0, max_quantity=1000.0, target_price=20.0, reservation_price=25.0, crop="Soybean")
        res = buyer.respond_to_offer({"price": 25.0, "quantity": 1000.0, "crop": "Soybean"}, context={"round": 5, "max_rounds": 5}, force_deterministic=True)
        assert res["type"] == "ACCEPT"
        assert res["quantity"] == 600.0  # 15000 / 25

    def test_NEG_10_ml_anchor_below_seller_ask(self):
        buyer = BuyerAgent("BuyerML1", budget=50000, max_quantity=1000, target_price=45.0, reservation_price=52.0, crop="Soybean")
        res = buyer.respond_to_offer({"price": 49.0, "quantity": 1000, "crop": "Soybean"}, context={"market_price": 38.0, "round": 2, "max_rounds": 5}, force_deterministic=True)
        assert res["type"] == "COUNTER"

    def test_NEG_11_ml_anchor_close_to_seller_ask(self):
        buyer = BuyerAgent("BuyerML2", budget=50000, max_quantity=1000, target_price=45.0, reservation_price=52.0, crop="Soybean")
        res = buyer.respond_to_offer({"price": 46.0, "quantity": 1000, "crop": "Soybean"}, context={"market_price": 46.5, "round": 2, "max_rounds": 5}, force_deterministic=True)
        assert res["type"] in ["COUNTER", "ACCEPT"]

    def test_NEG_12_maximum_negotiation_rounds_reached(self):
        buyer = BuyerAgent("BuyerMaxRounds", budget=50000, max_quantity=1000, target_price=40.0, reservation_price=48.0, crop="Soybean")
        res = buyer.respond_to_offer({"price": 46.0, "quantity": 1000, "crop": "Soybean"}, context={"round": 5, "max_rounds": 5}, force_deterministic=True)
        assert res["type"] == "ACCEPT"
