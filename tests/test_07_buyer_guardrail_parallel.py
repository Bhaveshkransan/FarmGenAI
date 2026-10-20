import asyncio
from backend.services.negotiation_service import NegotiationService, STATUTORY_BENCHMARKS, MAHARASHTRA_CROP_SUPPLIERS
from database.db import Database


def test_statutory_benchmarks_defined():
    assert len(STATUTORY_BENCHMARKS) == 7
    for crop in ["Soybean", "Cotton", "Jowar", "Onion", "Bajra", "Rice", "Sugarcane"]:
        assert crop in STATUTORY_BENCHMARKS
        assert STATUTORY_BENCHMARKS[crop]["benchmark"] > 0
    assert len(MAHARASHTRA_CROP_SUPPLIERS) == 7
    for crop in MAHARASHTRA_CROP_SUPPLIERS:
        assert len(MAHARASHTRA_CROP_SUPPLIERS[crop]) == 5


def test_buyer_guardrail_blocks_2000_offer():
    async def run():
        service = NegotiationService(None)
        neg_id = Database.generate_id("neg")
        payload = {
            "negotiation_id": neg_id,
            "crop": "Soybean",
            "quantity": 2500,
            "price": 48.92,
            "target_price": 48.92,
            "min_price": 45.0,
            "status": "ACTIVE",
            "farmer_name": "Latur Mandi Farmer",
            "buyer_name": "Test Enterprise"
        }
        await Database.create_negotiation_async(payload)

        # Attempt counter offer of 2000 (exceeds MSP of 48.92)
        res = await service.intervene_deal(neg_id, {"price": 2000.0, "quantity": 2500})
        assert res["status"] == "ACTIVE"
        assert res["final_price"] is None
        assert res["decision"] == "REJECT"
        assert "🛡️ [Buyer Guardrail]" in res["warning"]
    asyncio.run(run())


def test_parallel_procurement_auto_selects_best():
    async def run():
        service = NegotiationService(None)
        neg_id = Database.generate_id("neg")
        payload = {
            "negotiation_id": neg_id,
            "crop": "Soybean",
            "quantity": 5000,
            "price": 48.92,
            "target_price": 48.92,
            "min_price": 45.0,
            "status": "ACTIVE",
            "farmer_name": "Latur Mandi Farmer",
            "buyer_name": "Test Enterprise"
        }
        await Database.create_negotiation_async(payload)

        # Seed real produce listings in Database to be discovered
        for i in range(5):
            await Database.upsert_produce_async({
                "id": f"list_test_soy_{i+1}",
                "farmer_name": f"Latur Farmer {i+1}",
                "crop": "Soybean",
                "quantity": 5000,
                "min_price": 45.0 + i * 0.5,
                "location": "Latur",
                "status": "ACTIVE",
                "shelf_life": 10,
                "quality": "A",
            })

        res = await service.run_parallel_procurement(neg_id, {"quantity": 5000, "target_price": 48.92})
        assert res["success"] is True
        assert len(res["suppliers"]) == 5
        winner = res["winner"]
        assert winner["is_best"] is True
        assert winner["rank"] == 1
        assert winner["landed_cost_per_kg"] > 0
        assert winner["negotiated_price"] <= res["buyer_ceiling"]
    asyncio.run(run())


def test_buyer_guardrail_blocks_sub_floor_offer():
    async def run():
        service = NegotiationService(None)
        neg_id = Database.generate_id("neg")
        payload = {
            "negotiation_id": neg_id,
            "crop": "Soybean",
            "quantity": 2500,
            "price": 48.92,
            "target_price": 48.92,
            "min_price": 45.0,
            "status": "ACTIVE",
            "farmer_name": "Latur Mandi Farmer",
            "buyer_name": "Test Enterprise"
        }
        await Database.create_negotiation_async(payload)

        # Attempt counter offer of 5.0 (below floor of ~17.12 for Soybean)
        res = await service.intervene_deal(neg_id, {"price": 5.0, "quantity": 2500})
        assert res["status"] == "ACTIVE"
        assert res["final_price"] is None
        assert res["decision"] == "REJECT"
        assert "🛡️ [Buyer Guardrail]" in res["warning"]
        assert "floor" in res["warning"].lower()
    asyncio.run(run())


def test_finalize_deal_rejects_invalid_entries_and_guardrail_violations():
    from backend.routes.negotiation_routes import accept_deal
    from fastapi import HTTPException
    import pytest

    async def run():
        neg_id = Database.generate_id("neg")
        payload = {
            "negotiation_id": neg_id,
            "crop": "Soybean",
            "quantity": 2500,
            "price": 48.92,
            "target_price": 48.92,
            "min_price": 45.0,
            "status": "ACTIVE",
            "farmer_name": "Latur Mandi Farmer",
            "buyer_name": "Test Enterprise"
        }
        await Database.create_negotiation_async(payload)

        # 1. Price ceiling violation (2000.0) -> strictly rejected
        with pytest.raises(HTTPException) as exc_info:
            await accept_deal(neg_id, {"price": 2000.0, "quantity": 2500, "crop": "Soybean"})
        assert exc_info.value.status_code == 400
        assert "exceeds statutory ceiling" in exc_info.value.detail

        # 2. Price floor violation (2.0) -> strictly rejected
        with pytest.raises(HTTPException) as exc_info:
            await accept_deal(neg_id, {"price": 2.0, "quantity": 2500, "crop": "Soybean"})
        assert exc_info.value.status_code == 400
        assert "below the statutory APMC floor threshold" in exc_info.value.detail

        # 3. Invalid volume (<= 0) -> strictly rejected
        with pytest.raises(HTTPException) as exc_info:
            await accept_deal(neg_id, {"price": 47.5, "quantity": -500, "crop": "Soybean"})
        assert exc_info.value.status_code == 400
        assert "strictly positive" in exc_info.value.detail

        # 4. Valid deal details -> accepted & smart contract signed
        res = await accept_deal(neg_id, {
            "price": 47.5,
            "quantity": 2500,
            "crop": "Soybean",
            "farmer": "Latur Farmers Cooperative",
            "buyer": "Enterprise Agro Ltd"
        })
        assert res["status"] == "success"
        assert "TXN-MH-2026-" in res["transaction_id"]
        assert res["contract_hash"].startswith("0x")
        assert res["contract"]["final_price"] == 47.5
        assert res["contract"]["quantity"] == 2500
        assert res["contract"]["apmc_cess"] == round(47.5 * 2500 * 0.01, 2)
    asyncio.run(run())

