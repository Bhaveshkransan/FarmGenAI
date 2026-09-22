"""
tests/test_09_buyer_market_context.py
------------------------------------------------------------------------
Comprehensive Test Suite for Priority 5:
Buyer Market Context Integration & Full Decision-Pipeline Verification.

Covers Test Matrix MC-01 through MC-30 and E2E Scenarios 1 through 10:
- MC-01: Current market only
- MC-02: ML forecast only
- MC-03: RAG only
- MC-04: Current market + ML
- MC-05: Current market + RAG
- MC-06: ML + RAG
- MC-07: Current market + ML + RAG (Full context)
- MC-08: All market context unavailable
- MC-09: Current market stale
- MC-10: Current market exact APMC
- MC-11: Current market district fallback
- MC-12: Current market state fallback
- MC-13: Price unit consistency (₹/kg vs ₹/quintal)
- MC-14: ML forecast is not treated as current price
- MC-15: Current price is not treated as forecast
- MC-16: RAG cannot override reservation
- MC-17: Market price cannot override reservation
- MC-18: ML cannot override reservation
- MC-19: Budget remains authoritative
- MC-20: Quantity remains authoritative
- MC-21: Crop isolation remains authoritative
- MC-22: Maximum rounds remain authoritative
- MC-23: Boulware behavior
- MC-24: Aggressive behavior
- MC-25: Conceder behavior
- MC-26: Balanced behavior
- MC-27: Deterministic behavior (no random strategic pricing)
- MC-28: Malformed market context
- MC-29: Missing market data
- MC-30: Full end-to-end Buyer negotiation
"""

import sys
import os
import math
import pytest
from datetime import datetime, timezone
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from agents.buyer_agent import BuyerAgent
from backend.schemas.buyer_market_context import (
    BuyerMarketContext,
    CurrentMarketContext,
    MLForecastContext,
    BuyerRAGContextSummary,
)
from backend.services.buyer_market_context_service import (
    BuyerMarketContextService,
    buyer_market_context_service,
)
from backend.services.buyer_rag_service import BuyerRAGContext


# ─────────────────────────────────────────────────────────────────────────────
# Test Matrix: MC-01 through MC-08 (Combinatorial Context Availability)
# ─────────────────────────────────────────────────────────────────────────────

class TestMarketContextCombinations:
    """Tests MC-01 through MC-08 covering all combinations of context availability."""

    def test_mc_01_current_market_only(self):
        """MC-01: Verify behavior when ONLY Current Market data is available."""
        ctx = BuyerMarketContext(
            crop="Soybean",
            location="Latur",
            current_market=CurrentMarketContext(
                commodity="Soybean",
                modal_price=48.50,
                min_price=46.00,
                max_price=51.00,
                market="Latur APMC",
                observation_date="2026-09-22",
                freshness="CURRENT",
                match_level="EXACT_APMC",
                is_current=True,
                is_available=True,
            ),
            ml_forecast=MLForecastContext(commodity="Soybean", is_available=False),
            buyer_rag=BuyerRAGContextSummary(is_empty=True, is_available=False),
        )
        assert ctx.has_current_market is True
        assert ctx.has_ml_forecast is False
        assert ctx.has_buyer_rag is False
        assert ctx.is_partial is True
        assert "📍 Current Daily Mandi Price (Observed): ₹48.5/kg" in ctx.to_prompt_text()
        assert "Predicted Next-Period Modal Price (ML Forecast): UNAVAILABLE" in ctx.to_prompt_text()

        # Buyer negotiation remains operational
        buyer = BuyerAgent(name="Buyer1", budget=100000, max_quantity=1000, target_price=45, reservation_price=52, crop="Soybean")
        res = buyer.respond_to_offer({"price": 50.0, "quantity": 100}, context={"buyer_market_context": ctx}, force_deterministic=True)
        assert res["type"] in ["COUNTER", "ACCEPT"]

    def test_mc_02_ml_forecast_only(self):
        """MC-02: Verify behavior when ONLY ML forecast is available."""
        ctx = BuyerMarketContext(
            crop="Cotton",
            location="Jalgaon",
            current_market=CurrentMarketContext(commodity="Cotton", is_available=False),
            ml_forecast=MLForecastContext(
                commodity="Cotton",
                predicted_modal_price=72.00,
                forecast_period="next_period (t+1)",
                model="RidgeRegression",
                audit_status="ML_USED",
                is_ml_prediction=True,
                is_available=True,
            ),
            buyer_rag=BuyerRAGContextSummary(is_empty=True, is_available=False),
        )
        assert ctx.has_current_market is False
        assert ctx.has_ml_forecast is True
        assert ctx.has_buyer_rag is False
        assert ctx.is_partial is True
        assert "🔮 Predicted Next-Period Modal Price (ML Forecast): ₹72.0/kg" in ctx.to_prompt_text()

        buyer = BuyerAgent(name="Buyer2", budget=100000, max_quantity=1000, target_price=68, reservation_price=75, crop="Cotton")
        res = buyer.respond_to_offer({"price": 70.0, "quantity": 100}, context={"buyer_market_context": ctx}, force_deterministic=True)
        assert res["type"] in ["COUNTER", "ACCEPT"]

    def test_mc_03_rag_only(self):
        """MC-03: Verify behavior when ONLY Buyer RAG context is available."""
        ctx = BuyerMarketContext(
            crop="Onion",
            location="Lasalgaon",
            current_market=CurrentMarketContext(commodity="Onion", is_available=False),
            ml_forecast=MLForecastContext(commodity="Onion", is_available=False),
            buyer_rag=BuyerRAGContextSummary(
                quality_context="Requires Grade A red onions with moisture < 12%",
                procurement_context="Standard payment Net-7 upon delivery",
                is_empty=False,
                is_available=True,
            ),
        )
        assert ctx.has_current_market is False
        assert ctx.has_ml_forecast is False
        assert ctx.has_buyer_rag is True
        assert "Quality Specs: Requires Grade A red onions" in ctx.to_prompt_text()

        buyer = BuyerAgent(name="Buyer3", budget=100000, max_quantity=1000, target_price=20, reservation_price=25, crop="Onion")
        res = buyer.respond_to_offer({"price": 22.0, "quantity": 100}, context={"buyer_market_context": ctx}, force_deterministic=True)
        assert res["type"] in ["COUNTER", "ACCEPT"]

    def test_mc_04_current_market_and_ml(self):
        """MC-04: Verify Current Market + ML Forecast without RAG."""
        ctx = BuyerMarketContext(
            crop="Sugarcane",
            current_market=CurrentMarketContext(commodity="Sugarcane", modal_price=3.60, is_available=True),
            ml_forecast=MLForecastContext(commodity="Sugarcane", predicted_modal_price=3.75, is_available=True),
            buyer_rag=BuyerRAGContextSummary(is_empty=True, is_available=False),
        )
        assert ctx.has_current_market is True
        assert ctx.has_ml_forecast is True
        assert ctx.has_buyer_rag is False
        assert ctx.is_partial is True

    def test_mc_05_current_market_and_rag(self):
        """MC-05: Verify Current Market + RAG without ML."""
        ctx = BuyerMarketContext(
            crop="Jowar",
            current_market=CurrentMarketContext(commodity="Jowar", modal_price=34.00, is_available=True),
            ml_forecast=MLForecastContext(commodity="Jowar", is_available=False),
            buyer_rag=BuyerRAGContextSummary(procurement_context="Direct mandi purchase", is_empty=False, is_available=True),
        )
        assert ctx.has_current_market is True
        assert ctx.has_ml_forecast is False
        assert ctx.has_buyer_rag is True
        assert ctx.is_partial is True

    def test_mc_06_ml_and_rag(self):
        """MC-06: Verify ML Forecast + RAG without Current Market."""
        ctx = BuyerMarketContext(
            crop="Bajra",
            current_market=CurrentMarketContext(commodity="Bajra", is_available=False),
            ml_forecast=MLForecastContext(commodity="Bajra", predicted_modal_price=27.00, is_available=True),
            buyer_rag=BuyerRAGContextSummary(quality_context="Nutri-cereal FAQ grade", is_empty=False, is_available=True),
        )
        assert ctx.has_current_market is False
        assert ctx.has_ml_forecast is True
        assert ctx.has_buyer_rag is True
        assert ctx.is_partial is True

    def test_mc_07_full_context_market_ml_rag(self):
        """MC-07: Verify complete composite market context (All 3 domains active)."""
        ctx = BuyerMarketContext(
            crop="Rice",
            location="Gondia",
            current_market=CurrentMarketContext(
                commodity="Rice",
                modal_price=28.00,
                min_price=26.00,
                max_price=30.00,
                market="Gondia APMC",
                observation_date="2026-09-22",
                freshness="CURRENT",
                is_available=True,
                is_current=True,
            ),
            ml_forecast=MLForecastContext(
                commodity="Rice",
                predicted_modal_price=29.50,
                audit_status="ML_USED",
                is_ml_prediction=True,
                is_available=True,
            ),
            buyer_rag=BuyerRAGContextSummary(
                quality_context="Kolam rice broken grains < 5%",
                procurement_context="Bulk mill intake",
                is_empty=False,
                is_available=True,
            ),
        )
        assert ctx.is_complete is True
        assert ctx.has_current_market is True
        assert ctx.has_ml_forecast is True
        assert ctx.has_buyer_rag is True
        p_text = ctx.to_prompt_text()
        assert "📍 Current Daily Mandi Price (Observed): ₹28.0/kg" in p_text
        assert "🔮 Predicted Next-Period Modal Price (ML Forecast): ₹29.5/kg" in p_text
        assert "Kolam rice broken grains < 5%" in p_text

    def test_mc_08_all_context_unavailable(self):
        """MC-08: Verify pure deterministic fallback when all external context fails."""
        ctx = BuyerMarketContext(
            crop="Soybean",
            current_market=CurrentMarketContext(commodity="Soybean", is_available=False),
            ml_forecast=MLForecastContext(commodity="Soybean", is_available=False),
            buyer_rag=BuyerRAGContextSummary(is_empty=True, is_available=False),
        )
        assert ctx.is_empty is True
        buyer = BuyerAgent(name="Buyer8", budget=50000, max_quantity=500, target_price=45, reservation_price=50, crop="Soybean")
        res = buyer.respond_to_offer({"price": 46.0, "quantity": 100}, context={"buyer_market_context": ctx}, force_deterministic=True)
        assert res["type"] in ["ACCEPT", "COUNTER"]


# ─────────────────────────────────────────────────────────────────────────────
# Test Matrix: MC-09 through MC-15 (Location, Freshness, Units & Semantic Integrity)
# ─────────────────────────────────────────────────────────────────────────────

class TestSemanticAndUnitIntegrity:
    """Tests MC-09 through MC-15."""

    def test_mc_09_current_market_stale_flagged(self):
        """MC-09: Verify stale market data is explicitly flagged and never marked fresh."""
        cm = CurrentMarketContext(
            commodity="Onion",
            modal_price=22.0,
            observation_date="2026-08-01",
            freshness="STALE",
            is_current=False,
            is_available=True,
        )
        ctx = BuyerMarketContext(crop="Onion", current_market=cm)
        assert ctx.current_market.is_current is False
        assert ctx.current_market.freshness == "STALE"
        assert "[STALE]" in ctx.to_prompt_text()

    def test_mc_10_location_exact_apmc(self):
        """MC-10: Verify exact APMC match level is preserved in metadata."""
        cm = CurrentMarketContext(
            commodity="Soybean",
            modal_price=50.0,
            market="Latur APMC",
            match_level="EXACT_APMC",
            is_available=True,
        )
        ctx = BuyerMarketContext(crop="Soybean", current_market=cm)
        assert ctx.current_market.match_level == "EXACT_APMC"
        assert "(Location Match: EXACT_APMC)" in ctx.to_prompt_text()

    def test_mc_11_location_district_fallback(self):
        """MC-11: Verify district fallback match level is preserved."""
        cm = CurrentMarketContext(
            commodity="Cotton",
            modal_price=71.0,
            district="Jalgaon",
            match_level="DISTRICT",
            is_available=True,
        )
        ctx = BuyerMarketContext(crop="Cotton", current_market=cm)
        assert ctx.current_market.match_level == "DISTRICT"
        assert "(Location Match: DISTRICT)" in ctx.to_prompt_text()

    def test_mc_12_location_state_fallback(self):
        """MC-12: Verify statewide fallback match level is preserved."""
        cm = CurrentMarketContext(
            commodity="Sugarcane",
            modal_price=3.5,
            state="Maharashtra",
            match_level="STATE",
            is_available=True,
        )
        ctx = BuyerMarketContext(crop="Sugarcane", current_market=cm)
        assert ctx.current_market.match_level == "STATE"
        assert "(Location Match: STATE)" in ctx.to_prompt_text()

    def test_mc_13_price_unit_consistency(self):
        """MC-13: Verify unit validator flags potential unnormalized quintal prices."""
        valid_ctx = BuyerMarketContext(
            crop="Soybean",
            current_market=CurrentMarketContext(commodity="Soybean", modal_price=50.0, is_available=True),
            ml_forecast=MLForecastContext(commodity="Soybean", predicted_modal_price=52.0, is_available=True),
        )
        ok, msg = valid_ctx.validate_units()
        assert ok is True

        # Malformed: unnormalized ₹/quintal price (e.g. 5000 instead of 50.0)
        invalid_ctx = BuyerMarketContext(
            crop="Soybean",
            current_market=CurrentMarketContext(commodity="Soybean", modal_price=5000.0, is_available=True),
        )
        ok, msg = invalid_ctx.validate_units()
        assert ok is False
        assert "unit mismatch" in msg.lower()

    def test_mc_14_ml_forecast_is_not_treated_as_current_price(self):
        """MC-14: Verify ML forecast is strictly stored in ml_forecast and labeled as forecast."""
        ctx = BuyerMarketContext(
            crop="Cotton",
            ml_forecast=MLForecastContext(commodity="Cotton", predicted_modal_price=73.5, is_available=True),
        )
        assert ctx.has_current_market is False
        assert ctx.has_ml_forecast is True
        assert ctx.current_market.modal_price is None
        assert "🔮 Predicted Next-Period Modal Price (ML Forecast): ₹73.5/kg" in ctx.to_prompt_text()

    def test_mc_15_current_price_is_not_treated_as_forecast(self):
        """MC-15: Verify current mandi price is strictly stored in current_market and labeled as observed."""
        ctx = BuyerMarketContext(
            crop="Cotton",
            current_market=CurrentMarketContext(commodity="Cotton", modal_price=71.0, is_available=True),
        )
        assert ctx.has_current_market is True
        assert ctx.has_ml_forecast is False
        assert ctx.ml_forecast.predicted_modal_price is None
        assert "📍 Current Daily Mandi Price (Observed): ₹71.0/kg" in ctx.to_prompt_text()


# ─────────────────────────────────────────────────────────────────────────────
# Test Matrix: MC-16 through MC-22 (Hard Economic Invariance)
# ─────────────────────────────────────────────────────────────────────────────

class TestEconomicInvariance:
    """Tests MC-16 through MC-22: Guardrails MUST remain strictly authoritative."""

    def test_mc_16_rag_cannot_override_reservation(self):
        """MC-16: High-praise RAG text cannot authorize offer acceptance above reservation price."""
        buyer = BuyerAgent(name="Buyer16", budget=100000, max_quantity=1000, target_price=40, reservation_price=45, crop="Soybean")
        rag_ctx = BuyerRAGContextSummary(
            quality_context="Extremely premium organic export-quality crop worth 2x standard price!",
            is_empty=False,
            is_available=True,
        )
        ctx = BuyerMarketContext(crop="Soybean", buyer_rag=rag_ctx)

        # Offer is ₹48 (above reservation price ₹45)
        res = buyer.respond_to_offer({"price": 48.0, "quantity": 100}, context={"buyer_market_context": ctx}, force_deterministic=True)
        assert res["type"] in ["COUNTER", "REJECT"]
        if res["type"] == "COUNTER":
            assert res["price"] <= 45.0

    def test_mc_17_market_price_cannot_override_reservation(self):
        """MC-17: High observed mandi price cannot authorize acceptance above reservation price."""
        buyer = BuyerAgent(name="Buyer17", budget=100000, max_quantity=1000, target_price=40, reservation_price=45, crop="Soybean")
        mandi_ctx = CurrentMarketContext(commodity="Soybean", modal_price=70.0, is_available=True)
        ctx = BuyerMarketContext(crop="Soybean", current_market=mandi_ctx)

        # Seller asks ₹48 (below mandi ₹70, but above reservation ₹45)
        res = buyer.respond_to_offer({"price": 48.0, "quantity": 100}, context={"buyer_market_context": ctx}, force_deterministic=True)
        assert res["type"] in ["COUNTER", "REJECT"]
        if res["type"] == "COUNTER":
            assert res["price"] <= 45.0

    def test_mc_18_ml_cannot_override_reservation(self):
        """MC-18: High ML prediction cannot authorize acceptance above reservation price."""
        buyer = BuyerAgent(name="Buyer18", budget=100000, max_quantity=1000, target_price=40, reservation_price=45, crop="Soybean")
        ml_ctx = MLForecastContext(commodity="Soybean", predicted_modal_price=80.0, is_available=True)
        ctx = BuyerMarketContext(crop="Soybean", ml_forecast=ml_ctx)

        # Seller asks ₹50
        res = buyer.respond_to_offer({"price": 50.0, "quantity": 100}, context={"buyer_market_context": ctx}, force_deterministic=True)
        assert res["type"] in ["COUNTER", "REJECT"]
        if res["type"] == "COUNTER":
            assert res["price"] <= 45.0

    def test_mc_19_budget_remains_authoritative(self):
        """MC-19: Buyer cannot accept or counter with total value exceeding budget."""
        buyer = BuyerAgent(name="Buyer19", budget=1000, max_quantity=100, target_price=20, reservation_price=25, crop="Onion")
        # Ask for ₹22 for 100kg = ₹2200 (exceeds budget ₹1000)
        res = buyer.respond_to_offer({"price": 22.0, "quantity": 100}, context={"round": 1}, force_deterministic=True)
        if res["type"] == "ACCEPT":
            assert res["quantity"] * 22.0 <= 1000.0
        elif res["type"] == "COUNTER":
            assert res["price"] * res["quantity"] <= 1000.0

    def test_mc_20_quantity_remains_authoritative(self):
        """MC-20: Buyer cannot purchase more than max_quantity."""
        buyer = BuyerAgent(name="Buyer20", budget=500000, max_quantity=200, target_price=20, reservation_price=25, crop="Onion")
        # Seller offers 1000kg at ₹18 (within target)
        res = buyer.respond_to_offer({"price": 18.0, "quantity": 1000}, context={"round": 1}, force_deterministic=True)
        assert res["type"] == "ACCEPT"
        assert res["quantity"] <= 200.0

    def test_mc_21_crop_isolation_remains_authoritative(self):
        """MC-21: Unsupported crop must be immediately rejected."""
        buyer = BuyerAgent(name="Buyer21", budget=100000, max_quantity=500, target_price=50, reservation_price=60, crop="Soybean")
        res = buyer.respond_to_offer({"crop": "Cardamom", "price": 40.0, "quantity": 50}, force_deterministic=True)
        assert res["type"] == "REJECT"
        assert "unsupported crop" in res["message"].lower()

    def test_mc_22_maximum_rounds_remains_authoritative(self):
        """MC-22: Final round resolution must either accept within reservation or reject."""
        buyer = BuyerAgent(name="Buyer22", budget=100000, max_quantity=500, target_price=40, reservation_price=45, crop="Soybean")
        # In final round 5 of 5:
        # If offer is <= reservation price (₹44), accept
        res_accept = buyer.respond_to_offer({"price": 44.0, "quantity": 100}, context={"round": 5, "max_rounds": 5}, force_deterministic=True)
        assert res_accept["type"] == "ACCEPT"

        # If offer is > reservation price (₹46), reject
        res_reject = buyer.respond_to_offer({"price": 46.0, "quantity": 100}, context={"round": 5, "max_rounds": 5}, force_deterministic=True)
        assert res_reject["type"] == "REJECT"


# ─────────────────────────────────────────────────────────────────────────────
# Test Matrix: MC-23 through MC-27 (Persona Concession & Determinism)
# ─────────────────────────────────────────────────────────────────────────────

class TestPersonaAndDeterminism:
    """Tests MC-23 through MC-27."""

    def test_mc_23_boulware_behavior(self):
        """MC-23: Boulware concedes slowly in early rounds."""
        buyer = BuyerAgent(name="BoulwareBuyer", budget=100000, max_quantity=500, target_price=40, reservation_price=50, strategy="boulware", crop="Soybean")
        res_r1 = buyer.respond_to_offer({"price": 48.0, "quantity": 100}, context={"round": 1, "max_rounds": 5, "market_price": 45.0}, force_deterministic=True)
        assert res_r1["type"] == "COUNTER"
        # Opening bid is 32.0; Boulware concession is minimal in round 1
        assert res_r1["price"] < 35.0

    def test_mc_24_aggressive_behavior(self):
        """MC-24: Aggressive buyer makes minimal concession."""
        buyer = BuyerAgent(name="AggressiveBuyer", budget=100000, max_quantity=500, target_price=40, reservation_price=50, strategy="aggressive", crop="Soybean")
        res_r1 = buyer.respond_to_offer({"price": 48.0, "quantity": 100}, context={"round": 1, "max_rounds": 5, "market_price": 45.0}, force_deterministic=True)
        assert res_r1["type"] == "COUNTER"
        assert res_r1["price"] <= 33.0

    def test_mc_25_conceder_behavior(self):
        """MC-25: Conceder buyer concedes more quickly in early rounds."""
        buyer = BuyerAgent(name="ConcederBuyer", budget=100000, max_quantity=500, target_price=40, reservation_price=50, strategy="conceder", crop="Soybean")
        res_r1 = buyer.respond_to_offer({"price": 48.0, "quantity": 100}, context={"round": 1, "max_rounds": 5, "market_price": 45.0}, force_deterministic=True)
        assert res_r1["type"] == "COUNTER"
        # Conceder produces faster movement than Aggressive / Balanced
        assert res_r1["price"] >= 35.0

    def test_mc_26_balanced_behavior(self):
        """MC-26: Balanced buyer concessions are linear and bounded."""
        buyer = BuyerAgent(name="BalancedBuyer", budget=100000, max_quantity=500, target_price=40, reservation_price=50, strategy="balanced", crop="Soybean")
        res_r1 = buyer.respond_to_offer({"price": 48.0, "quantity": 100}, context={"round": 1, "max_rounds": 5, "market_price": 45.0}, force_deterministic=True)
        assert res_r1["type"] == "COUNTER"
        assert res_r1["price"] >= 33.0

    def test_mc_27_deterministic_behavior(self):
        """MC-27: Identical inputs yield identical decisions without random drift."""
        b1 = BuyerAgent(name="B1", budget=100000, max_quantity=500, target_price=40, reservation_price=50, strategy="balanced", crop="Soybean")
        b2 = BuyerAgent(name="B2", budget=100000, max_quantity=500, target_price=40, reservation_price=50, strategy="balanced", crop="Soybean")

        r1 = b1.respond_to_offer({"price": 46.0, "quantity": 100}, context={"round": 2, "max_rounds": 5}, force_deterministic=True)
        r2 = b2.respond_to_offer({"price": 46.0, "quantity": 100}, context={"round": 2, "max_rounds": 5}, force_deterministic=True)
        assert r1["type"] == r2["type"]
        assert r1["price"] == r2["price"]


# ─────────────────────────────────────────────────────────────────────────────
# Test Matrix: MC-28 through MC-30 (Adversarial, Fallbacks & Full E2E Flow)
# ─────────────────────────────────────────────────────────────────────────────

class TestAdversarialAndEndToEnd:
    """Tests MC-28 through MC-30."""

    def test_mc_28_malformed_market_context(self):
        """MC-28: Malformed context (NaN, negative prices) handled safely without crash."""
        buyer = BuyerAgent(name="Buyer28", budget=100000, max_quantity=500, target_price=40, reservation_price=50, crop="Soybean")
        malformed_ctx = {
            "current_mandi_data": {"modal_price_kg": float("nan")},
            "market_features": {"modal_price_kg": -100.0},
        }
        res = buyer.respond_to_offer({"price": 45.0, "quantity": 100}, context=malformed_ctx, force_deterministic=True)
        assert res["type"] in ["ACCEPT", "COUNTER", "REJECT"]

    def test_mc_29_missing_market_data(self):
        """MC-29: Missing context keys gracefully default without throwing exceptions."""
        buyer = BuyerAgent(name="Buyer29", budget=100000, max_quantity=500, target_price=40, reservation_price=50, crop="Soybean")
        res = buyer.respond_to_offer({"price": 42.0, "quantity": 100}, context=None, force_deterministic=True)
        assert res["type"] in ["ACCEPT", "COUNTER"]

    def test_mc_30_full_end_to_end_buyer_negotiation(self):
        """MC-30: Complete multi-round negotiation flow from round 1 to agreement."""
        buyer = BuyerAgent(
            name="RetailProcurement",
            budget=200000,
            max_quantity=1000,
            target_price=42.0,
            reservation_price=48.0,
            persona="retail_supermarket",
            crop="Soybean",
            location="Latur"
        )
        ctx = buyer_market_context_service.build_market_context("Soybean", "Latur", "retail_supermarket")
        assert ctx.crop == "Soybean"

        # Round 1: Farmer asks ₹55 (Above reservation ₹48) -> Buyer Counters
        r1 = buyer.respond_to_offer({"price": 55.0, "quantity": 500}, context={"round": 1, "max_rounds": 5, "buyer_market_context": ctx}, force_deterministic=True)
        assert r1["type"] == "COUNTER"
        assert r1["price"] <= 48.0

        # Round 2: Farmer concessions to ₹50 -> Buyer Counters higher
        r2 = buyer.respond_to_offer({"price": 50.0, "quantity": 500}, context={"round": 2, "max_rounds": 5, "buyer_market_context": ctx}, force_deterministic=True)
        assert r2["type"] == "COUNTER"
        assert r2["price"] >= r1["price"]
        assert r2["price"] <= 48.0

        # Round 3: Farmer concessions to ₹46 (Within reservation) -> Buyer Accepts or Counters close
        r3 = buyer.respond_to_offer({"price": 46.0, "quantity": 500}, context={"round": 3, "max_rounds": 5, "buyer_market_context": ctx}, force_deterministic=True)
        assert r3["type"] in ["COUNTER", "ACCEPT"]

        # Final Round 5: Farmer concessions to ₹44 -> Buyer Accepts
        r5 = buyer.respond_to_offer({"price": 44.0, "quantity": 500}, context={"round": 5, "max_rounds": 5, "buyer_market_context": ctx}, force_deterministic=True)
        assert r5["type"] == "ACCEPT"
        assert r5["price"] == 44.0
        assert r5["quantity"] == 500
        assert "contract" in r5
        assert r5["contract"]["po_number"].startswith("PO-")
