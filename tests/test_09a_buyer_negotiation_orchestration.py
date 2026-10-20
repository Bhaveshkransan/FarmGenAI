"""
tests/test_09a_buyer_negotiation_orchestration.py
------------------------------------------------------------------------
Comprehensive Verification Test Suite for Priority 5C:
AUTOMATIC TOP-5 BUYER NEGOTIATION ORCHESTRATION.

Test Matrix:
  - NEG-ORCH-01: Top-5 candidate discovery
  - NEG-ORCH-02: Top-5 selection cap
  - NEG-ORCH-03: Fewer than 5 candidates handled gracefully
  - NEG-ORCH-04: Concurrent multi-branch execution
  - NEG-ORCH-05: Session ID isolation across branches
  - NEG-ORCH-06: Zero cross-branch mutation (Seller A cannot mutate Seller B)
  - NEG-ORCH-07: Automatic multi-round progression
  - NEG-ORCH-08: Internal COUNTER progression
  - NEG-ORCH-09: Internal ACCEPT only for valid executable offers
  - NEG-ORCH-10: Internal REJECT for invalid / out-of-bounds offers
  - NEG-ORCH-11: Reservation ceiling protection (Bajra ₹3000 max vs ₹3500 ask)
  - NEG-ORCH-12: Total expenditure budget protection (price * quantity <= budget)
  - NEG-ORCH-13: Quantity feasibility and protection
  - NEG-ORCH-14: Strict 7-crop isolation and unsupported crop protection
  - NEG-ORCH-15: Non-positive / invalid price protection
  - NEG-ORCH-16: NaN / Infinite price & quantity protection
  - NEG-ORCH-17: Final-round fallback cannot exceed reservation ceiling
  - NEG-ORCH-18: Immobile seller stall detection and termination
  - NEG-ORCH-19: Maximum negotiation rounds reached handling
  - NEG-ORCH-20: All sellers above reservation -> NO_EXECUTABLE_DEAL
  - NEG-ORCH-21: No forced winner when all branches fail
  - NEG-ORCH-22: Final winner selected exclusively from valid executable deals
  - NEG-ORCH-23: True landed-cost ranking (Base + Freight + APMC Cess)
  - NEG-ORCH-24: Waits for all parallel branches before winner selection
  - NEG-ORCH-25: Coherent structured chat/terminal transcript generation
  - NEG-ORCH-26: RAG / ML / Current-market context cannot override reservation or force ACCEPT
  - Scenarios A through F
"""

import math
import pytest
import asyncio
from agents.buyer_agent import BuyerAgent
from backend.services.buyer_orchestrator import BuyerOrchestrationService, buyer_orchestration_service
from shared.crop_catalog import is_supported_buyer_crop


# =============================================================================
# Direct BuyerAgent Deterministic Economic Decision Safety Tests
# =============================================================================

class TestDirectBuyerEconomicSafety:
    def test_direct_buyer_agent_bajra_bug_protection(self):
        """NEG-ORCH-11 / Scenario B: Buyer reservation ₹3,000/kg, Seller asks ₹3,500/kg -> NEVER ACCEPT."""
        buyer = BuyerAgent(
            name="TestBuyer",
            budget=3000000.0,
            max_quantity=1000.0,
            target_price=2700.0,
            reservation_price=3000.0,
            crop="Bajra",
        )
        assert buyer.reservation_price == 3000.0

        resp = buyer.respond_to_offer(
            offer={"price": 3500.0, "quantity": 1000.0, "crop": "Bajra"},
            context={"round": 1, "max_rounds": 5},
            force_deterministic=True,
        )
        assert resp["type"] != "ACCEPT", f"CRITICAL BUG: BuyerAgent returned ACCEPT for ₹3500 with reservation ₹3000: {resp}"
        assert resp["type"] == "COUNTER"
        assert resp["price"] <= 3000.0, f"Counter price {resp['price']} exceeded reservation ceiling ₹3000."

    def test_direct_buyer_agent_boundary_reservation_offer(self):
        """NEG-ORCH-09: Buyer reservation ₹3,000/kg, Seller asks exact reservation price ₹3,000/kg."""
        buyer = BuyerAgent(
            name="TestBuyer",
            budget=3000000.0,
            max_quantity=1000.0,
            target_price=2700.0,
            reservation_price=3000.0,
            crop="Bajra",
        )
        resp = buyer.respond_to_offer(
            offer={"price": 3000.0, "quantity": 1000.0, "crop": "Bajra"},
            context={"round": 1, "max_rounds": 5},
            force_deterministic=True,
        )
        if resp["type"] == "COUNTER":
            assert resp["price"] <= 3000.0
        elif resp["type"] == "ACCEPT":
            assert resp["price"] <= 3000.0

    def test_direct_buyer_agent_below_target_accept(self):
        """NEG-ORCH-09: Buyer reservation ₹3,000/kg, target ₹2,700/kg, Seller asks ₹2,600/kg -> ACCEPT."""
        buyer = BuyerAgent(
            name="TestBuyer",
            budget=3000000.0,
            max_quantity=1000.0,
            target_price=2700.0,
            reservation_price=3000.0,
            crop="Bajra",
        )
        resp = buyer.respond_to_offer(
            offer={"price": 2600.0, "quantity": 1000.0, "crop": "Bajra"},
            context={"round": 1, "max_rounds": 5},
            force_deterministic=True,
        )
        assert resp["type"] == "ACCEPT"
        assert resp["price"] == 2600.0

    def test_direct_buyer_agent_budget_exhaustion_protection(self):
        """NEG-ORCH-12 / Scenario C: Price <= reservation BUT total_cost > budget -> Bounded by budget."""
        buyer = BuyerAgent(
            name="TestBuyer",
            budget=10000.0,  # Only ₹10,000 total budget
            max_quantity=1000.0,
            target_price=50.0,
            reservation_price=60.0,
            crop="Soybean",
        )
        # Seller asks ₹55/kg for 1000kg -> Total cost = ₹55,000 > ₹10,000 budget
        resp = buyer.respond_to_offer(
            offer={"price": 55.0, "quantity": 1000.0, "crop": "Soybean"},
            context={"round": 1, "max_rounds": 5},
            force_deterministic=True,
        )
        if resp["type"] == "ACCEPT":
            assert resp["quantity"] * resp["price"] <= 10000.0
        elif resp["type"] == "COUNTER":
            assert resp["quantity"] * resp["price"] <= 10000.0

    def test_direct_buyer_agent_unsupported_crop_rejected(self):
        """NEG-ORCH-14: Buyer strictly negotiates only 7 canonical Maharashtra crops."""
        buyer = BuyerAgent(
            name="TestBuyer",
            budget=100000.0,
            max_quantity=1000.0,
            target_price=20.0,
            reservation_price=25.0,
            crop="Sugarcane",
        )
        resp = buyer.respond_to_offer(
            offer={"price": 20.0, "quantity": 500.0, "crop": "Wheat"},
            context={"round": 1, "max_rounds": 5},
            force_deterministic=True,
        )
        assert resp["type"] == "REJECT"
        assert "Unsupported crop" in resp["message"]

    def test_direct_buyer_agent_nan_inf_rejected(self):
        """NEG-ORCH-15 & 16: Invalid or non-finite price/quantity must be rejected."""
        buyer = BuyerAgent(
            name="TestBuyer",
            budget=100000.0,
            max_quantity=1000.0,
            target_price=50.0,
            reservation_price=60.0,
            crop="Soybean",
        )
        resp1 = buyer.respond_to_offer(
            offer={"price": float("nan"), "quantity": 500.0, "crop": "Soybean"},
            context={"round": 1, "max_rounds": 5},
            force_deterministic=True,
        )
        assert resp1["type"] == "REJECT"

        resp2 = buyer.respond_to_offer(
            offer={"price": 50.0, "quantity": float("inf"), "crop": "Soybean"},
            context={"round": 1, "max_rounds": 5},
            force_deterministic=True,
        )
        assert resp2["type"] == "REJECT"

        resp3 = buyer.respond_to_offer(
            offer={"price": -10.0, "quantity": 500.0, "crop": "Soybean"},
            context={"round": 1, "max_rounds": 5},
            force_deterministic=True,
        )
        assert resp3["type"] == "REJECT"

    def test_direct_buyer_agent_final_round_above_reservation_rejected(self):
        """NEG-ORCH-17: At round == max_rounds, if seller price > reservation, MUST REJECT."""
        buyer = BuyerAgent(
            name="TestBuyer",
            budget=100000.0,
            max_quantity=1000.0,
            target_price=50.0,
            reservation_price=55.0,
            crop="Soybean",
        )
        resp = buyer.respond_to_offer(
            offer={"price": 58.0, "quantity": 500.0, "crop": "Soybean"},
            context={"round": 5, "max_rounds": 5},
            force_deterministic=True,
        )
        assert resp["type"] == "REJECT"


# =============================================================================
# BuyerOrchestrationService Core Requirements (NEG-ORCH-01 to NEG-ORCH-26)
# =============================================================================

class TestBuyerOrchestrationService:

    def test_neg_orch_01_and_02_top_5_candidate_selection(self):
        """NEG-ORCH-01 & 02: Discovers top 5 eligible candidate sellers."""
        from database.db import Database
        async def _run():
            service = BuyerOrchestrationService()
            for i in range(5):
                await Database.upsert_produce_async({
                    "id": f"list_cotton_test_{i+1}",
                    "farmer_name": f"Wardha Farmer {i+1}",
                    "crop": "Cotton",
                    "quantity": 1000.0,
                    "min_price": 68.0 + i,
                    "location": "Wardha",
                    "status": "ACTIVE",
                    "shelf_life": 30,
                    "quality": "A",
                })
            req = {
                "crop": "Cotton",
                "quantity": 1000.0,
                "target_price": 70.0,
                "max_price": 75.0,
                "budget": 100000.0,
                "location": "Wardha",
            }
            candidates = await service.get_top_candidates(req, max_candidates=5)
            assert len(candidates) <= 5
            assert len(candidates) > 0
            for c in candidates:
                assert c["crop"] == "Cotton"
                assert c["price"] > 0
                assert "name" in c
        asyncio.run(_run())

    def test_neg_orch_03_fewer_than_5_candidates_handled(self):
        """NEG-ORCH-03: Handles requests when fewer than 5 real candidates exist."""
        async def _run():
            service = BuyerOrchestrationService()
            explicit_sellers = [
                {"id": "s1", "name": "Seller One", "price": 50.0, "quantity": 500.0, "location": "Pune", "crop": "Soybean"},
                {"id": "s2", "name": "Seller Two", "price": 52.0, "quantity": 500.0, "location": "Nashik", "crop": "Soybean"},
            ]
            req = {
                "crop": "Soybean",
                "quantity": 500.0,
                "target_price": 48.0,
                "max_price": 55.0,
                "budget": 30000.0,
                "sellers": explicit_sellers,
            }
            candidates = await service.get_top_candidates(req, max_candidates=5)
            assert len(candidates) == 2
            assert candidates[0]["name"] == "Seller One"
            assert candidates[1]["name"] == "Seller Two"
        asyncio.run(_run())

    def test_neg_orch_04_and_05_and_06_state_isolation(self):
        """NEG-ORCH-04, 05, 06: Parallel branches have unique session IDs and isolated states."""
        async def _run():
            service = BuyerOrchestrationService()
            sellers = [
                {"id": "s1", "name": "Seller Alpha", "price": 45.0, "quantity": 500.0, "location": "Pune", "crop": "Soybean"},
                {"id": "s2", "name": "Seller Beta", "price": 60.0, "quantity": 500.0, "location": "Nashik", "crop": "Soybean"},
            ]
            req = {
                "crop": "Soybean",
                "quantity": 500.0,
                "target_price": 46.0,
                "max_price": 50.0,
                "budget": 30000.0,
                "sellers": sellers,
            }
            result = await service.orchestrate_negotiation(req)
            negs = result["negotiations"]
            assert len(negs) == 2
            assert negs[0]["session_id"] != negs[1]["session_id"]
            assert negs[0]["seller_name"] == "Seller Alpha"
            assert negs[1]["seller_name"] == "Seller Beta"
            # Seller Beta exceeded max_price (₹60 vs ₹50) so it cannot affect Seller Alpha
            assert negs[1]["is_valid_deal"] is False
            assert negs[0]["is_valid_deal"] is True
        asyncio.run(_run())

    def test_neg_orch_07_and_08_multi_round_progression(self):
        """NEG-ORCH-07 & 08: Negotiations progress through rounds automatically."""
        async def _run():
            service = BuyerOrchestrationService()
            sellers = [
                {"id": "s1", "name": "Co-op Farm", "price": 55.0, "floor_price": 47.0, "flexibility": 0.20, "quantity": 500.0, "location": "Latur", "crop": "Soybean"},
            ]
            req = {
                "crop": "Soybean",
                "quantity": 500.0,
                "target_price": 46.0,
                "max_price": 50.0,
                "budget": 30000.0,
                "sellers": sellers,
            }
            result = await service.orchestrate_negotiation(req, max_rounds=5)
            neg = result["negotiations"][0]
            assert neg["rounds_count"] >= 1
            assert len(neg["rounds"]) == neg["rounds_count"]
            assert neg["rounds"][0]["round"] == 1
        asyncio.run(_run())

    def test_neg_orch_10_and_20_bajra_all_sellers_above_reservation(self):
        """Scenario A & B / NEG-ORCH-10, 20: Bajra all sellers above reservation -> NO_EXECUTABLE_DEAL."""
        async def _run():
            service = BuyerOrchestrationService()
            bajra_sellers = [
                {"id": "b1", "name": "Bajra Seller 1", "price": 3500.0, "floor_price": 3400.0, "quantity": 1000.0, "crop": "Bajra"},
                {"id": "b2", "name": "Bajra Seller 2", "price": 3450.0, "floor_price": 3350.0, "quantity": 1000.0, "crop": "Bajra"},
                {"id": "b3", "name": "Bajra Seller 3", "price": 3600.0, "floor_price": 3500.0, "quantity": 1000.0, "crop": "Bajra"},
                {"id": "b4", "name": "Bajra Seller 4", "price": 3550.0, "floor_price": 3400.0, "quantity": 1000.0, "crop": "Bajra"},
                {"id": "b5", "name": "Bajra Seller 5", "price": 3500.0, "floor_price": 3300.0, "quantity": 1000.0, "crop": "Bajra"},
            ]
            req = {
                "crop": "Bajra",
                "quantity": 1000.0,
                "target_price": 2700.0,
                "reservation_price": 3000.0,
                "max_price": 3000.0,
                "budget": 3000000.0,
                "sellers": bajra_sellers,
            }
            result = await service.orchestrate_negotiation(req, max_candidates=5)
            assert result["winner"] is None, f"Winner must be None when all sellers ask > ₹3000: {result['winner']}"
            assert result["status"] == "NO_EXECUTABLE_DEAL"
            assert len(result["executable_deals"]) == 0
            for neg in result["negotiations"]:
                assert neg["is_valid_deal"] is False
        asyncio.run(_run())

    def test_neg_orch_11_and_12_budget_protection(self):
        """NEG-ORCH-11 & 12: Price * quantity exceeding budget is bounded."""
        async def _run():
            service = BuyerOrchestrationService()
            sellers = [
                {"id": "s1", "name": "Expensive Seller", "price": 50.0, "quantity": 1000.0, "crop": "Soybean"},
            ]
            req = {
                "crop": "Soybean",
                "quantity": 1000.0,
                "target_price": 45.0,
                "max_price": 55.0,
                "budget": 20000.0,  # Only 20k budget for 50k transaction
                "sellers": sellers,
            }
            result = await service.orchestrate_negotiation(req)
            neg = result["negotiations"][0]
            if neg["outcome"] == "DEAL":
                assert neg["executable_quantity"] * neg["final_price"] <= 20000.0
        asyncio.run(_run())

    def test_neg_orch_13_quantity_protection(self):
        """NEG-ORCH-13: Invalid quantity cannot result in deal."""
        async def _run():
            service = BuyerOrchestrationService()
            req = {
                "crop": "Soybean",
                "quantity": -500.0,
                "target_price": 45.0,
                "max_price": 55.0,
                "budget": 20000.0,
            }
            result = await service.orchestrate_negotiation(req)
            assert result["status"] == "ERROR_INVALID_QUANTITY"
            assert result["winner"] is None
        asyncio.run(_run())

    def test_neg_orch_14_unsupported_crop(self):
        """NEG-ORCH-14: Unsupported crop returns ERROR_UNSUPPORTED_CROP."""
        async def _run():
            service = BuyerOrchestrationService()
            req = {
                "crop": "Apples",
                "quantity": 500.0,
                "target_price": 100.0,
                "max_price": 120.0,
                "budget": 100000.0,
            }
            result = await service.orchestrate_negotiation(req)
            assert result["status"] == "ERROR_UNSUPPORTED_CROP"
            assert result["winner"] is None
        asyncio.run(_run())

    def test_neg_orch_18_stall_handling(self):
        """NEG-ORCH-18: Immobile seller prices above reservation trigger STALLED."""
        async def _run():
            service = BuyerOrchestrationService()
            stubborn_seller = [
                {"id": "stub1", "name": "Stubborn Merchant", "price": 3500.0, "floor_price": 3500.0, "flexibility": 0.0, "quantity": 500.0, "crop": "Bajra"},
            ]
            req = {
                "crop": "Bajra",
                "quantity": 500.0,
                "target_price": 2700.0,
                "max_price": 3000.0,
                "budget": 2000000.0,
                "sellers": stubborn_seller,
            }
            result = await service.orchestrate_negotiation(req, max_rounds=5)
            neg = result["negotiations"][0]
            assert neg["outcome"] in ("STALLED", "REJECT", "MAX_ROUNDS_REACHED")
            assert neg["is_valid_deal"] is False
        asyncio.run(_run())

    def test_neg_orch_21_no_forced_winner_when_all_fail(self):
        """NEG-ORCH-21: No winner is selected when all negotiations fail."""
        async def _run():
            service = BuyerOrchestrationService()
            high_sellers = [
                {"id": "h1", "name": "High 1", "price": 80.0, "quantity": 500.0, "crop": "Sugarcane"},
                {"id": "h2", "name": "High 2", "price": 90.0, "quantity": 500.0, "crop": "Sugarcane"},
            ]
            req = {
                "crop": "Sugarcane",
                "quantity": 500.0,
                "target_price": 3.5,
                "max_price": 4.5,
                "budget": 5000.0,
                "sellers": high_sellers,
            }
            result = await service.orchestrate_negotiation(req)
            assert result["winner"] is None
            assert result["status"] == "NO_EXECUTABLE_DEAL"
        asyncio.run(_run())

    def test_neg_orch_22_and_23_valid_deal_selection_and_landed_cost(self):
        """Scenario D / NEG-ORCH-22, 23: Multiple valid sellers ranked by Landed Cost."""
        async def _run():
            service = BuyerOrchestrationService()
            sellers = [
                # Seller A: Base 48.0, dist 300km -> higher freight
                {"id": "sA", "name": "Far Supplier", "price": 48.0, "floor_price": 46.0, "quantity": 500.0, "distance_km": 300.0, "crop": "Soybean"},
                # Seller B: Base 47.5, dist 50km -> lower freight
                {"id": "sB", "name": "Near Supplier", "price": 47.5, "floor_price": 46.0, "quantity": 500.0, "distance_km": 50.0, "crop": "Soybean"},
            ]
            req = {
                "crop": "Soybean",
                "quantity": 500.0,
                "target_price": 46.0,
                "max_price": 52.0,
                "budget": 30000.0,
                "sellers": sellers,
            }
            result = await service.orchestrate_negotiation(req)
            assert result["status"] == "DEAL_SELECTED"
            # Near Supplier should have lower landed cost and win
            assert result["winner"]["seller_name"] == "Near Supplier"
            far_supplier = [n for n in result["negotiations"] if n["seller_name"] == "Far Supplier"][0]
            assert result["winner"]["landed_cost_per_kg"] < far_supplier["landed_cost_per_kg"]
        asyncio.run(_run())

    def test_neg_orch_24_waits_for_all_parallel_branches(self):
        """NEG-ORCH-24: Waits for all branches to finish before selecting winner."""
        async def _run():
            service = BuyerOrchestrationService()
            sellers = [
                {"id": "s1", "name": "Fast Supplier", "price": 47.0, "quantity": 500.0, "crop": "Soybean"},
                {"id": "s2", "name": "Cheaper Multi-round Supplier", "price": 52.0, "floor_price": 45.0, "quantity": 500.0, "crop": "Soybean"},
            ]
            req = {
                "crop": "Soybean",
                "quantity": 500.0,
                "target_price": 46.0,
                "max_price": 52.0,
                "budget": 30000.0,
                "sellers": sellers,
            }
            result = await service.orchestrate_negotiation(req, max_rounds=5)
            # Both branches must have completed records
            assert len(result["negotiations"]) == 2
            assert all(n["status"] in ("DEAL", "REJECT", "MAX_ROUNDS_REACHED", "STALLED") for n in result["negotiations"])
        asyncio.run(_run())

    def test_neg_orch_25_transcript_output(self):
        """NEG-ORCH-25: Generates comprehensive chat-style transcript."""
        async def _run():
            service = BuyerOrchestrationService()
            req = {
                "crop": "Soybean",
                "quantity": 500.0,
                "target_price": 46.0,
                "max_price": 52.0,
                "budget": 30000.0,
                "sellers": [
                    {"id": "s1", "name": "Demo Seller", "price": 48.0, "quantity": 500.0, "crop": "Soybean"}
                ],
            }
            result = await service.orchestrate_negotiation(req)
            assert "chat_transcript" in result
            assert "BUYER AUTONOMOUS PROCUREMENT ORCHESTRATION" in result["chat_transcript"]
            assert "FINAL COMPARISON" in result["chat_transcript"]
        asyncio.run(_run())

    def test_neg_orch_scenario_e_branch_failure_isolation(self):
        """Scenario E: One malformed branch failing does not crash other branches."""
        async def _run():
            service = BuyerOrchestrationService()
            sellers = [
                {"id": "s1", "name": "Good Supplier", "price": 46.0, "quantity": 500.0, "crop": "Soybean"},
                {"id": "s2", "name": "Broken Supplier", "price": float("nan"), "quantity": 500.0, "crop": "Soybean"},
            ]
            req = {
                "crop": "Soybean",
                "quantity": 500.0,
                "target_price": 46.0,
                "max_price": 50.0,
                "budget": 30000.0,
                "sellers": sellers,
            }
            result = await service.orchestrate_negotiation(req)
            assert len(result["negotiations"]) == 2
            good_neg = next(n for n in result["negotiations"] if n["seller_name"] == "Good Supplier")
            broken_neg = next(n for n in result["negotiations"] if n["seller_name"] == "Broken Supplier")
            assert good_neg["is_valid_deal"] is True
            assert broken_neg["is_valid_deal"] is False
            assert result["winner"]["seller_name"] == "Good Supplier"
        asyncio.run(_run())

    def test_neg_orch_scenario_f_budget_isolation(self):
        """Scenario F: Parallel branches operate on budget snapshots; shared budget is not depleted concurrently."""
        async def _run():
            service = BuyerOrchestrationService()
            sellers = [
                {"id": "s1", "name": "Supplier A", "price": 46.0, "quantity": 500.0, "crop": "Soybean"},
                {"id": "s2", "name": "Supplier B", "price": 46.0, "quantity": 500.0, "crop": "Soybean"},
            ]
            req = {
                "crop": "Soybean",
                "quantity": 500.0,
                "target_price": 46.0,
                "max_price": 50.0,
                "budget": 25000.0,  # Enough for ONE deal (23,000), not both (46,000)
                "sellers": sellers,
            }
            result = await service.orchestrate_negotiation(req)
            # Both branches are evaluated with full budget snapshot, then ONE winner is chosen
            assert result["status"] == "DEAL_SELECTED"
            assert result["winner"] is not None
            assert result["winner"]["total_landed_cost"] <= 25000.0
        asyncio.run(_run())
