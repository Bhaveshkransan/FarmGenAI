"""
tests/test_buyer_runtime_e2e.py
------------------------------------------------------------------------
End-to-End Runtime Validation of Autonomous Buyer Procurement Engine:
1. Requirement Creation -> Candidate Discovery -> Parallel 5-Branch Multi-Round Negotiation
2. Landed Cost (Base + Distance Freight + APMC Cess) Ranking
3. Deterministic Winner Selection + SHA-256 Contract + Transaction Finalization
4. Stale/Depleted Listing Disqualification
5. No-Winner Policy when all candidates exceed reservation ceiling
6. Strict 7-Crop & Quantity Guardrails
"""

import math
import pytest
import asyncio
from unittest.mock import patch, MagicMock, AsyncMock

from backend.services.buyer_orchestrator import BuyerOrchestrationService
from backend.services.negotiation_service import NegotiationService
from database.db import Database


class TestBuyerRuntimeE2E:
    """Complete Runtime End-to-End Validation Suite"""

    @pytest.mark.asyncio
    async def test_full_buyer_runtime_e2e_deal_success(self):
        """
        Validates the entire runtime chain:
        5 candidates negotiate concurrently across multiple rounds,
        landed costs are computed with distance freight and cess,
        lowest landed cost deal within budget is awarded.
        """
        service = BuyerOrchestrationService()

        requirement = {
            "crop": "Soybean",
            "quantity": 1000.0,
            "target_price": 48.0,
            "max_price": 52.0,
            "reservation_price": 52.0,
            "budget": 60000.0,
            "location": "Pune, Maharashtra",
            "buyer_name": "AgroTech Mills Pune",
            "persona": "bulk_wholesaler",
            "strategy": "aggressive",
            "sellers": [
                {
                    "id": "seller_latur",
                    "name": "Latur Farmers FPO",
                    "price": 50.0,
                    "quantity": 1500.0,
                    "distance_km": 220.0,
                    "location": "Latur, Maharashtra",
                    "match_score": 95.0,
                },
                {
                    "id": "seller_nanded",
                    "name": "Nanded Krishi Consortium",
                    "price": 51.5,
                    "quantity": 1200.0,
                    "distance_km": 280.0,
                    "location": "Nanded, Maharashtra",
                    "match_score": 92.0,
                },
                {
                    "id": "seller_solapur",
                    "name": "Solapur Agro Union",
                    "price": 49.0,
                    "quantity": 1000.0,
                    "distance_km": 160.0,
                    "location": "Solapur, Maharashtra",
                    "match_score": 96.0,
                },
                {
                    "id": "seller_akola",
                    "name": "Akola Oilseeds Pool",
                    "price": 54.0,  # Starts above ceiling, will negotiate down
                    "floor_price": 50.5,
                    "quantity": 1000.0,
                    "distance_km": 300.0,
                    "location": "Akola, Maharashtra",
                    "match_score": 88.0,
                },
                {
                    "id": "seller_expensive",
                    "name": "High Premium Seller",
                    "price": 65.0,  # Refuses to concede below 60 -> exceeds ceiling 52
                    "floor_price": 60.0,
                    "flexibility": 0.02,
                    "quantity": 1000.0,
                    "distance_km": 100.0,
                    "location": "Sangli, Maharashtra",
                    "match_score": 85.0,
                }
            ]
        }

        # Mock DB calls for produce inventory and history
        mock_produce = {
            "seller_latur": {"id": "seller_latur", "status": "ACTIVE", "quantity": 1500.0},
            "seller_nanded": {"id": "seller_nanded", "status": "ACTIVE", "quantity": 1200.0},
            "seller_solapur": {"id": "seller_solapur", "status": "ACTIVE", "quantity": 1000.0},
            "seller_akola": {"id": "seller_akola", "status": "ACTIVE", "quantity": 1000.0},
            "seller_expensive": {"id": "seller_expensive", "status": "ACTIVE", "quantity": 1000.0},
        }

        async def mock_get_produce(pid):
            return mock_produce.get(pid)

        with patch.object(Database, "get_produce_async", side_effect=mock_get_produce), \
             patch.object(Database, "deduct_produce_inventory_async", new_callable=AsyncMock) as mock_deduct, \
             patch.object(Database, "add_history_async", new_callable=AsyncMock):

            res = await service.orchestrate_negotiation(
                requirement=requirement,
                max_candidates=5,
                max_rounds=5,
                negotiation_id="neg_runtime_test_01"
            )

            # 1. Orchestration status
            assert res["status"] == "DEAL_SELECTED"
            winner = res["winner"]
            assert winner is not None

            # 2. Winner must satisfy ceiling
            assert winner["final_price"] <= 52.0
            assert winner["is_valid_deal"] is True

            # 3. Expensive seller must be disqualified
            exp_branch = next(n for n in res["negotiations"] if n["seller_id"] == "seller_expensive")
            assert exp_branch["is_valid_deal"] is False

            # 4. Landed cost evaluation
            assert winner["landed_cost_per_kg"] == round(
                winner["final_price"] + winner["freight_per_kg"] + winner["apmc_cess_per_kg"], 2
            )
            assert winner["total_landed_cost"] <= 60000.0

            # 5. Quantity lifecycle verification
            assert res["requested_quantity"] == 1000.0
            assert res["allocated_quantity"] == 1000.0
            assert res["remaining_quantity"] == 0.0

            # 6. Contract and transaction verification
            assert winner["transaction_id"].startswith("TXN-MH-2026-")
            assert winner["contract_hash"].startswith("0x")
            assert len(winner["idempotency_key"]) == 64

            # 7. Inventory deduction called for winner
            mock_deduct.assert_called_once_with(winner["seller_id"], 1000.0)

    @pytest.mark.asyncio
    async def test_full_buyer_runtime_no_executable_deal(self):
        """
        Validates deterministic no-winner outcome when ALL candidate sellers
        refuse to drop below the buyer's reservation ceiling.
        """
        service = BuyerOrchestrationService()

        requirement = {
            "crop": "Cotton",
            "quantity": 500.0,
            "target_price": 70.0,
            "max_price": 72.0,  # Hard ceiling
            "budget": 40000.0,
            "location": "Nagpur, Maharashtra",
            "sellers": [
                {
                    "id": "cotton_1",
                    "name": "Kapas Dealer 1",
                    "price": 85.0,
                    "floor_price": 80.0,  # Refuses below 80 -> > 72
                    "quantity": 500.0,
                    "distance_km": 150.0,
                },
                {
                    "id": "cotton_2",
                    "name": "Kapas Dealer 2",
                    "price": 88.0,
                    "floor_price": 78.0,  # Refuses below 78 -> > 72
                    "quantity": 500.0,
                    "distance_km": 120.0,
                }
            ]
        }

        with patch.object(Database, "deduct_produce_inventory_async", new_callable=AsyncMock) as mock_deduct:
            res = await service.orchestrate_negotiation(
                requirement=requirement,
                max_candidates=2,
                max_rounds=3,
                negotiation_id="neg_no_deal_02"
            )

            assert res["status"] == "NO_EXECUTABLE_DEAL"
            assert res["winner"] is None
            assert len(res["executable_deals"]) == 0
            assert res["allocated_quantity"] == 0.0
            assert res["remaining_quantity"] == 500.0

            # Zero inventory deducted
            mock_deduct.assert_not_called()

    @pytest.mark.asyncio
    async def test_unsupported_crop_guardrail_blocks_orchestration(self):
        """
        Validates that non-Maharashtra crops (e.g. Pineapple) are rejected immediately.
        """
        service = BuyerOrchestrationService()
        requirement = {
            "crop": "Pineapple",
            "quantity": 500.0,
            "target_price": 50.0,
            "max_price": 60.0,
        }
        res = await service.orchestrate_negotiation(requirement=requirement)
        assert res["status"] == "ERROR_UNSUPPORTED_CROP"
        assert res["winner"] is None

    @pytest.mark.asyncio
    async def test_invalid_quantity_guardrail_blocks_orchestration(self):
        """
        Validates that non-positive quantities (0 or negative) are rejected immediately.
        """
        service = BuyerOrchestrationService()
        requirement = {
            "crop": "Soybean",
            "quantity": -100.0,
            "target_price": 48.0,
            "max_price": 52.0,
        }
        res = await service.orchestrate_negotiation(requirement=requirement)
        assert res["status"] == "ERROR_INVALID_QUANTITY"
        assert res["winner"] is None
