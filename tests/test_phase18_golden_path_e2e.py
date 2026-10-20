"""
tests/test_phase18_golden_path_e2e.py
------------------------------------------------------------------------
Phase 18, 19, 20 Golden Path End-to-End System & Adversarial Certification Suite:

1. BUYER-E2E-SOYBEAN-001:
   Complete Golden Path from Requirement Creation -> Discovery -> Top-5 Ranking ->
   Parallel Multi-Round Negotiation -> Deterministic Deal Evaluation ->
   Automatic Finalization (TXN-MH-2026-..., SHA-256 Contract Hash, History, Inventory Deduction)

2. Adversarial & Edge Cases (Phase 19):
   - NaN, inf, negative price/quantity injection rejection
   - Reservation price hard ceiling enforcement (seller offer > max_price)
   - Crop mismatch prevention (Soybean requirement cannot match Cotton listing)
   - Zero candidate gracefully returning NO_CANDIDATES_FOUND with 0 DB side-effects

3. Concurrency & Multi-Tenant Isolation (Phase 20):
   - Parallel concurrent buyer requirement runs
   - WebSocket session isolation ensuring zero cross-tenant event leakage
"""

import asyncio
import hashlib
import json
import math
import uuid
import pytest
from unittest.mock import AsyncMock

from agents.buyer_agent import BuyerAgent
from backend.services.buyer_orchestrator import BuyerOrchestrationService
from backend.services.buyer_rag_service import buyer_rag_service, BuyerRAGContext
from backend.websocket.agent_updates import AgentUpdateHub
from database.db import Database


class TestGoldenPathBuyerE2ESoybean001:
    """Phase 18: Full Golden Path System Test BUYER-E2E-SOYBEAN-001."""

    def test_golden_path_buyer_e2e_soybean_001(self):
        async def _run():
            # 1. Reset Database & Seed Real Produce Listings
            await Database.reset()

            seller_1 = {
                "id": "seller_latur_001",
                "farmer_name": "Ramesh Patil",
                "crop": "Soybean",
                "quantity": 1200.0,
                "min_price": 50.0,
                "expected_price": 56.0,
                "location": "Latur",
                "quality": "A",
                "shelf_life": 180,
            }
            seller_2 = {
                "id": "seller_osmanabad_002",
                "farmer_name": "Suresh Deshmukh",
                "crop": "Soybean",
                "quantity": 800.0,
                "min_price": 52.0,
                "expected_price": 57.0,
                "location": "Osmanabad",
                "quality": "A",
                "shelf_life": 150,
            }
            seller_3 = {
                "id": "seller_nagpur_003",
                "farmer_name": "Vikas Shinde",
                "crop": "Soybean",
                "quantity": 2000.0,
                "min_price": 62.0,  # Above reservation price of 58
                "expected_price": 65.0,
                "location": "Nagpur",
                "quality": "B",
                "shelf_life": 120,
            }
            # Ineligible crop (Cotton)
            seller_4 = {
                "id": "seller_akola_004",
                "farmer_name": "Anil Rathod",
                "crop": "Cotton",
                "quantity": 1500.0,
                "min_price": 60.0,
                "expected_price": 70.0,
                "location": "Akola",
                "quality": "A",
                "shelf_life": 90,
            }

            await Database.upsert_produce_async(seller_1)
            await Database.upsert_produce_async(seller_2)
            await Database.upsert_produce_async(seller_3)
            await Database.upsert_produce_async(seller_4)

            # 2. Buyer Profile & Requirement Creation
            buyer_req = {
                "requirement_id": "REQ-SOYBEAN-001",
                "buyer_id": "BUYER-CORP-MAHA-01",
                "buyer_name": "MahaAgro Processors Ltd",
                "crop": "Soybean",
                "quantity": 1000.0,
                "target_quantity": 1000.0,
                "target_price": 52.0,
                "max_price": 58.0,
                "budget": 75000.0,
                "location": "Latur",
                "quality_tier": "A",
                "urgency": "NORMAL",
                "risk_appetite": "Moderate",
            }

            # 3. Candidate Discovery & Top-5 Deterministic Ranking
            orchestrator = BuyerOrchestrationService()
            candidates = await orchestrator.get_top_candidates(buyer_req)

            # Verify discovery & filtering
            assert len(candidates) >= 2
            seller_ids = [c["id"] for c in candidates]
            assert "seller_latur_001" in seller_ids
            assert "seller_osmanabad_002" in seller_ids
            assert "seller_akola_004" not in seller_ids  # Cotton filtered out

            # Verify ranking: closest/best match is first
            assert candidates[0]["id"] == "seller_latur_001"
            assert candidates[0]["location"] == "Latur"

            # 4. Parallel Multi-Round Negotiation Execution via orchestrate_negotiation
            result = await orchestrator.orchestrate_negotiation(
                requirement=buyer_req,
                max_candidates=5,
                max_rounds=4,
            )

            # 5. Deterministic Deal Evaluation Verification
            assert result["status"] == "DEAL_SELECTED"
            winner = result["winner"]
            assert winner is not None
            assert winner["seller_id"] == "seller_latur_001"
            assert winner["final_price"] <= 58.0  # Must be strictly within reservation ceiling
            assert winner["final_price"] >= 50.0  # Must satisfy seller minimum

            # 6. Automatic Finalization Verification
            assert winner["transaction_id"].startswith("TXN-MH-2026-")
            assert winner["contract_hash"].startswith("0x")
            assert len(winner["contract_hash"]) == 66  # "0x" + 64 hex chars

            # Verify History Record in DB
            history = await Database.get_history_async(buyer_req["buyer_id"])
            assert len(history) >= 1
            saved_tx = next((h for h in history if h.get("transaction_id") == winner["transaction_id"]), None)
            assert saved_tx is not None
            assert saved_tx["crop"] == "Soybean"
            assert saved_tx["final_price"] == winner["final_price"]

            # Verify Produce Inventory Deduction
            all_produce = await Database.list_produce_async()
            updated_seller_1 = next((p for p in all_produce if p["id"] == "seller_latur_001"), None)
            assert updated_seller_1 is not None
            assert updated_seller_1["quantity"] < 1200.0

        asyncio.run(_run())


class TestAdversarialAndEdgeCases:
    """Phase 19: Adversarial & Edge-Case Validation Matrix."""

    def test_reservation_ceiling_strictly_enforced_against_adversarial_prices(self):
        buyer = BuyerAgent(
            name="Strict Buyer",
            budget=100000.0,
            max_quantity=1000.0,
            target_price=50.0,
            reservation_price=58.0,
            crop="Soybean",
        )
        # Adversarial high offers
        for adversarial_price in [58.01, 60.0, 100.0, 999999.0]:
            offer = {"price": adversarial_price, "quantity": 1000.0, "crop": "Soybean"}
            context = {"round": 4, "max_rounds": 4, "market_price": 55.0}
            resp = buyer.respond_to_offer(offer, context, force_deterministic=True)
            assert resp["type"] != "ACCEPT", f"Adversarial price {adversarial_price} was accepted!"

    def test_adversarial_nan_and_negative_inputs(self):
        buyer = BuyerAgent(
            name="Strict Buyer",
            budget=100000.0,
            max_quantity=1000.0,
            target_price=50.0,
            reservation_price=58.0,
            crop="Soybean",
        )
        for invalid_price in [-10.0, -0.01, float("nan"), float("inf")]:
            offer = {"price": invalid_price, "quantity": 1000.0, "crop": "Soybean"}
            context = {"round": 1, "max_rounds": 4, "market_price": 55.0}
            resp = buyer.respond_to_offer(offer, context, force_deterministic=True)
            assert resp["type"] == "REJECT"

    def test_zero_candidates_found_yields_no_side_effects(self):
        async def _run():
            await Database.reset()
            orchestrator = BuyerOrchestrationService()
            req = {
                "requirement_id": "REQ-EMPTY-001",
                "buyer_id": "BUYER-001",
                "crop": "Cardamom",  # Unsupported / No sellers in DB
                "quantity": 500.0,
                "target_quantity": 500.0,
                "target_price": 1000.0,
                "max_price": 1200.0,
                "budget": 600000.0,
            }
            candidates = await orchestrator.get_top_candidates(req)
            assert len(candidates) == 0

            result = await orchestrator.orchestrate_negotiation(req)
            assert result["winner"] is None
            assert len(result.get("executable_deals", [])) == 0
            history = await Database.get_history_async("BUYER-001")
            assert len(history) == 0
        asyncio.run(_run())


class TestConcurrencyAndSessionIsolation:
    """Phase 20: Concurrency & WebSocket Session Isolation."""

    def test_parallel_independent_buyer_runs_do_not_interfere(self):
        async def _run():
            await Database.reset()
            await Database.upsert_produce_async({
                "id": "seller_onion_01",
                "farmer_name": "Kisan 1",
                "crop": "Onion",
                "quantity": 5000.0,
                "min_price": 20.0,
                "expected_price": 25.0,
                "location": "Nashik",
                "quality": "A",
                "shelf_life": 30,
            })
            await Database.upsert_produce_async({
                "id": "seller_bajra_01",
                "farmer_name": "Kisan 2",
                "crop": "Bajra",
                "quantity": 5000.0,
                "min_price": 30.0,
                "expected_price": 35.0,
                "location": "Pune",
                "quality": "A",
                "shelf_life": 365,
            })

            orchestrator = BuyerOrchestrationService()

            req_onion = {
                "requirement_id": "REQ-CONC-ONION",
                "buyer_id": "BUYER-A",
                "crop": "Onion",
                "quantity": 1000.0,
                "target_quantity": 1000.0,
                "target_price": 22.0,
                "max_price": 26.0,
                "budget": 30000.0,
                "location": "Nashik",
            }
            req_bajra = {
                "requirement_id": "REQ-CONC-BAJRA",
                "buyer_id": "BUYER-B",
                "crop": "Bajra",
                "quantity": 1000.0,
                "target_quantity": 1000.0,
                "target_price": 32.0,
                "max_price": 36.0,
                "budget": 40000.0,
                "location": "Pune",
            }

            # Run concurrently
            task_a = orchestrator.orchestrate_negotiation(req_onion, max_rounds=3)
            task_b = orchestrator.orchestrate_negotiation(req_bajra, max_rounds=3)

            res_a, res_b = await asyncio.gather(task_a, task_b)

            assert res_a["winner"] is not None
            assert res_a["winner"]["crop"] == "Onion"
            assert res_b["winner"] is not None
            assert res_b["winner"]["crop"] == "Bajra"
        asyncio.run(_run())

    def test_websocket_channel_isolation(self):
        async def _run():
            hub = AgentUpdateHub()
            ws_a = AsyncMock()
            ws_b = AsyncMock()

            neg_a = f"neg_{uuid.uuid4().hex[:8]}"
            neg_b = f"neg_{uuid.uuid4().hex[:8]}"

            hub.subscribe(ws_a, neg_a)
            hub.subscribe(ws_b, neg_b)

            # Broadcast event to neg_a only
            payload_a = {"negotiation_id": neg_a, "event": "PRICE_UPDATE", "price": 54.0}
            await hub.broadcast(payload_a)

            # ws_a must receive payload_a
            assert ws_a.send_json.await_count == 1
            assert ws_a.send_json.call_args[0][0]["price"] == 54.0

            # ws_b must NOT receive anything
            assert ws_b.send_json.await_count == 0
        asyncio.run(_run())
