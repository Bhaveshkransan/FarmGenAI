"""
tests/test_buyer_adversarial_pmax_budget.py
------------------------------------------------------------------------
Comprehensive adversarial and security tests for BuyerAgent & BuyerOrchestrator:
1. Absolute P_max validation with adversarial inputs (NaN, Inf, negatives, strings, nulls).
2. Absolute LLM override protection (deterministic business rules always override LLM proposals).
3. Cross-branch concurrent budget locking (Committed + Pending <= Budget).
4. Strict quantity allocation lifecycle (requested, allocated, remaining, min_purchase).
5. Listing freshness & revalidation before deal award.
6. Deterministic contract hashing and idempotency key generation.
"""

import math
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

from agents.buyer_agent import BuyerAgent
from backend.services.buyer_orchestrator import (
    BuyerOrchestrationService,
    BudgetReservationTracker,
)
from database.db import Database


class TestBuyerAdversarialPmax:
    """Test Suite 1: Absolute P_max & Adversarial Input Handling"""

    def test_adversarial_nan_price_rejected(self):
        buyer = BuyerAgent(
            name="Adversarial Tester",
            budget=100000.0,
            max_quantity=1000.0,
            target_price=45.0,
            reservation_price=50.0,
            crop="Soybean"
        )
        offer = {"price": float("nan"), "quantity": 500.0, "crop": "Soybean"}
        res = buyer.respond_to_offer(offer, force_deterministic=True)
        assert res["type"] == "REJECT"

    def test_adversarial_inf_price_rejected(self):
        buyer = BuyerAgent(
            name="Adversarial Tester",
            budget=100000.0,
            max_quantity=1000.0,
            target_price=45.0,
            reservation_price=50.0,
            crop="Soybean"
        )
        offer = {"price": float("inf"), "quantity": 500.0, "crop": "Soybean"}
        res = buyer.respond_to_offer(offer, force_deterministic=True)
        assert res["type"] == "REJECT"

    def test_adversarial_negative_price_rejected(self):
        buyer = BuyerAgent(
            name="Adversarial Tester",
            budget=100000.0,
            max_quantity=1000.0,
            target_price=45.0,
            reservation_price=50.0,
            crop="Soybean"
        )
        offer = {"price": -25.0, "quantity": 500.0, "crop": "Soybean"}
        res = buyer.respond_to_offer(offer, force_deterministic=True)
        assert res["type"] == "REJECT"

    def test_adversarial_string_nan_rejected(self):
        buyer = BuyerAgent(
            name="Adversarial Tester",
            budget=100000.0,
            max_quantity=1000.0,
            target_price=45.0,
            reservation_price=50.0,
            crop="Soybean"
        )
        offer = {"price": "NaN", "quantity": 500.0, "crop": "Soybean"}
        res = buyer.respond_to_offer(offer, force_deterministic=True)
        assert res["type"] == "REJECT"

    def test_adversarial_non_numeric_string_rejected(self):
        buyer = BuyerAgent(
            name="Adversarial Tester",
            budget=100000.0,
            max_quantity=1000.0,
            target_price=45.0,
            reservation_price=50.0,
            crop="Soybean"
        )
        offer = {"price": "free_produce", "quantity": 500.0, "crop": "Soybean"}
        res = buyer.respond_to_offer(offer, force_deterministic=True)
        assert res["type"] == "REJECT"

    def test_adversarial_zero_and_negative_quantity_rejected(self):
        buyer = BuyerAgent(
            name="Adversarial Tester",
            budget=100000.0,
            max_quantity=1000.0,
            target_price=45.0,
            reservation_price=50.0,
            crop="Soybean"
        )
        res_zero = buyer.respond_to_offer({"price": 45.0, "quantity": 0.0, "crop": "Soybean"}, force_deterministic=True)
        assert res_zero["type"] == "REJECT"

        res_neg = buyer.respond_to_offer({"price": 45.0, "quantity": -50.0, "crop": "Soybean"}, force_deterministic=True)
        assert res_neg["type"] == "REJECT"

    def test_spoiled_crop_rejected(self):
        buyer = BuyerAgent(
            name="Adversarial Tester",
            budget=100000.0,
            max_quantity=1000.0,
            target_price=45.0,
            reservation_price=50.0,
            crop="Soybean"
        )
        offer = {"price": 45.0, "quantity": 500.0, "crop": "Soybean", "shelf_life": 0}
        res = buyer.respond_to_offer(offer, force_deterministic=True)
        assert res["type"] == "REJECT"


class TestBuyerLLMOverrideProtection:
    """Test Suite 2: Absolute LLM Override Protection"""

    def test_llm_hallucination_accept_above_pmax_overridden(self):
        """When LLM hallucinates ACCEPT at ₹70/kg with P_max=50, deterministic rules MUST override."""
        buyer = BuyerAgent(
            name="LLM Test Buyer",
            budget=100000.0,
            max_quantity=1000.0,
            target_price=45.0,
            reservation_price=50.0,
            crop="Soybean"
        )
        offer = {"price": 70.0, "quantity": 500.0, "crop": "Soybean"}
        context = {"round": 5, "max_rounds": 5}

        # Mock LLM returning ACCEPT at 70
        with patch.object(buyer, "think", return_value={"decision": "ACCEPT", "counter_price": 70.0, "reason": "Looks good"}):
            res = buyer.respond_to_offer(offer, context=context, force_deterministic=False)
            # In round 5 (final), cannot accept > P_max -> must REJECT
            assert res["type"] == "REJECT"
            assert "exceeds" in res["message"].lower() or "violates" in res["message"].lower()

    def test_llm_hallucination_counter_above_pmax_clamped(self):
        """When LLM proposes counter of ₹58/kg with P_max=50, counter price must not exceed P_max."""
        buyer = BuyerAgent(
            name="LLM Test Buyer",
            budget=100000.0,
            max_quantity=1000.0,
            target_price=45.0,
            reservation_price=50.0,
            crop="Soybean"
        )
        offer = {"price": 60.0, "quantity": 500.0, "crop": "Soybean"}
        context = {"round": 2, "max_rounds": 5}

        with patch.object(buyer, "think", return_value={"decision": "COUNTER", "counter_price": 58.0, "reason": "Countering"}):
            res = buyer.respond_to_offer(offer, context=context, force_deterministic=False)
            assert res["type"] == "COUNTER"
            assert res["price"] <= 50.0

    def test_llm_invalid_counter_price_triggers_safe_fallback(self):
        """When LLM returns NaN or negative counter price, safe fallback is used."""
        buyer = BuyerAgent(
            name="LLM Test Buyer",
            budget=100000.0,
            max_quantity=1000.0,
            target_price=45.0,
            reservation_price=50.0,
            crop="Soybean"
        )
        offer = {"price": 52.0, "quantity": 500.0, "crop": "Soybean"}
        context = {"round": 1, "max_rounds": 5}

        with patch.object(buyer, "think", return_value={"decision": "COUNTER", "counter_price": float("nan"), "reason": "Bad"}):
            res = buyer.respond_to_offer(offer, context=context, force_deterministic=False)
            assert res["type"] == "COUNTER"
            assert not math.isnan(res["price"])
            assert res["price"] <= 50.0


class TestBudgetReservationTracker:
    """Test Suite 3: Cross-Branch Concurrent Budget Locking"""

    @pytest.mark.asyncio
    async def test_concurrent_budget_locking_prevents_overcommit(self):
        tracker = BudgetReservationTracker(total_budget=50000.0)

        # Branch 0 reserves 25,000
        res0 = await tracker.reserve(branch_idx=0, amount=25000.0)
        assert res0 is True

        # Branch 1 reserves 20,000 -> Total pending = 45,000 <= 50,000
        res1 = await tracker.reserve(branch_idx=1, amount=20000.0)
        assert res1 is True

        # Branch 2 attempts to reserve 10,000 -> 45,000 + 10,000 = 55,000 > 50,000 -> MUST FAIL
        res2 = await tracker.reserve(branch_idx=2, amount=10000.0)
        assert res2 is False

        # Branch 1 releases its reservation (e.g. stalled or rejected)
        await tracker.release(branch_idx=1)

        # Now Branch 2 can successfully reserve 10,000
        res2_retry = await tracker.reserve(branch_idx=2, amount=10000.0)
        assert res2_retry is True

        # Branch 0 confirms deal -> commit 25,000
        commit_res = await tracker.commit(branch_idx=0, amount=25000.0)
        assert commit_res is True
        assert tracker.committed_budget == 25000.0


class TestQuantityLifecycleAndFreshness:
    """Test Suite 4: Strict Quantity Lifecycle & Listing Freshness"""

    @pytest.mark.asyncio
    async def test_min_batch_size_disqualifies_underweight_lots(self):
        service = BuyerOrchestrationService()
        requirement = {
            "crop": "Soybean",
            "quantity": 5000.0,
            "min_batch_size": 1000.0,  # Minimum 1,000 kg required per lot
            "target_price": 48.0,
            "max_price": 52.0,
            "budget": 260000.0,
            "sellers": [
                {
                    "id": "lot_micro_1",
                    "name": "Micro Farmer 1",
                    "quantity": 400.0,  # Only 400kg -> below min_batch 1000kg
                    "price": 47.0,
                    "distance_km": 50.0,
                    "location": "Pune, Maharashtra"
                }
            ]
        }
        res = await service.orchestrate_negotiation(requirement=requirement, max_candidates=1, max_rounds=2)
        assert res["status"] == "NO_EXECUTABLE_DEAL"
        assert res["winner"] is None
        assert "below minimum batch" in res["negotiations"][0]["rejection_reason"].lower()

    @pytest.mark.asyncio
    async def test_listing_freshness_revalidation_disqualifies_sold_listing(self):
        service = BuyerOrchestrationService()
        requirement = {
            "crop": "Soybean",
            "quantity": 500.0,
            "target_price": 48.0,
            "max_price": 52.0,
            "budget": 30000.0,
            "sellers": [
                {
                    "id": "stale_listing_123",
                    "name": "Stale Producer",
                    "quantity": 500.0,
                    "price": 47.0,
                    "distance_km": 80.0,
                    "location": "Latur, Maharashtra"
                }
            ]
        }

        # Mock DB returning that this listing was already SOLD in concurrent race
        with patch.object(
            Database,
            "get_produce_async",
            new_callable=AsyncMock,
            return_value={"id": "stale_listing_123", "status": "SOLD", "quantity": 0.0}
        ):
            res = await service.orchestrate_negotiation(requirement=requirement, max_candidates=1, max_rounds=2)
            assert res["status"] == "NO_EXECUTABLE_DEAL"
            assert res["winner"] is None

    @pytest.mark.asyncio
    async def test_quantity_lifecycle_and_idempotency_tracked_on_winner(self):
        service = BuyerOrchestrationService()
        requirement = {
            "crop": "Soybean",
            "quantity": 500.0,
            "target_price": 48.0,
            "max_price": 52.0,
            "budget": 30000.0,
            "sellers": [
                {
                    "id": "valid_fresh_seller",
                    "name": "Latur Solvent Co-op",
                    "quantity": 500.0,
                    "price": 49.0,
                    "distance_km": 120.0,
                    "location": "Latur, Maharashtra"
                }
            ]
        }

        with patch.object(
            Database,
            "get_produce_async",
            new_callable=AsyncMock,
            return_value={"id": "valid_fresh_seller", "status": "ACTIVE", "quantity": 500.0}
        ), patch.object(
            Database,
            "deduct_produce_inventory_async",
            new_callable=AsyncMock,
            return_value={"id": "valid_fresh_seller", "status": "SOLD", "quantity": 0.0}
        ):
            res = await service.orchestrate_negotiation(requirement=requirement, max_candidates=1, max_rounds=3)
            assert res["status"] == "DEAL_SELECTED"
            winner = res["winner"]
            assert winner is not None

            # Verify quantity lifecycle
            assert res["requested_quantity"] == 500.0
            assert res["allocated_quantity"] == 500.0
            assert res["remaining_quantity"] == 0.0

            # Verify idempotency key and contract hash
            assert "idempotency_key" in winner
            assert len(winner["idempotency_key"]) == 64
            assert "contract_hash" in winner
            assert winner["contract_hash"].startswith("0x")
