from copy import deepcopy
from sqlalchemy import select
from database.db import AsyncSessionLocal, DBFarmer, DBBuyer, Database

class FarmerRepository:
    @staticmethod
    async def upsert(payload: dict) -> dict:
        p = deepcopy(payload)
        farmer_id = p.get("id") or Database.generate_id("farmer")
        p["id"] = farmer_id
        async with AsyncSessionLocal() as session:
            async with session.begin():
                db_farmer = await session.get(DBFarmer, farmer_id)
                if not db_farmer:
                    db_farmer = DBFarmer(id=farmer_id)
                    session.add(db_farmer)
                if "name" in p: db_farmer.name = p["name"]
                if "location" in p: db_farmer.location = p["location"]
                if "language" in p: db_farmer.language = p["language"]
                if "village" in p: db_farmer.village = p["village"]
                if "taluka" in p: db_farmer.taluka = p["taluka"]
                if "district" in p: db_farmer.district = p["district"]
                if "state" in p: db_farmer.state = p["state"]
                if "contact_number" in p: db_farmer.contact_number = p["contact_number"]
                if "farm_size_acres" in p: db_farmer.farm_size_acres = p["farm_size_acres"]
                if "farming_type" in p: db_farmer.farming_type = p["farming_type"]
                if "preferences" in p: db_farmer.preferences = p["preferences"]
        return p

    @staticmethod
    async def get_by_id(farmer_id: str) -> dict | None:
        async with AsyncSessionLocal() as session:
            db_farmer = await session.get(DBFarmer, farmer_id)
            if not db_farmer:
                return None
            return {
                "id": db_farmer.id,
                "name": db_farmer.name,
                "contact_number": db_farmer.contact_number,
                "location": db_farmer.location,
                "village": db_farmer.village,
                "taluka": db_farmer.taluka,
                "district": db_farmer.district,
                "state": db_farmer.state,
                "language": db_farmer.language,
                "farm_size_acres": db_farmer.farm_size_acres,
                "farming_type": db_farmer.farming_type,
                "preferences": db_farmer.preferences,
            }

    @staticmethod
    async def list_all() -> list:
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(DBFarmer))
            rows = res.scalars().all()
            return [
                {
                    "id": r.id,
                    "name": r.name,
                    "contact_number": r.contact_number,
                    "location": r.location,
                    "village": r.village,
                    "taluka": r.taluka,
                    "district": r.district,
                    "state": r.state,
                    "language": r.language,
                    "farm_size_acres": r.farm_size_acres,
                    "farming_type": r.farming_type,
                    "preferences": r.preferences,
                }
                for r in rows
            ]


class BuyerRepository:
    @staticmethod
    async def upsert(payload: dict) -> dict:
        p = deepcopy(payload)
        buyer_id = p.get("id") or Database.generate_id("buyer")
        p["id"] = buyer_id
        async with AsyncSessionLocal() as session:
            async with session.begin():
                db_buyer = await session.get(DBBuyer, buyer_id)
                if not db_buyer:
                    db_buyer = DBBuyer(id=buyer_id)
                    session.add(db_buyer)
                
                if "user_id" in p: db_buyer.user_id = p["user_id"]
                if "buyer_name" in p: db_buyer.buyer_name = p["buyer_name"]
                if "crop" in p: db_buyer.crop = p["crop"]
                if "min_price" in p: db_buyer.min_price = p["min_price"]
                if "max_price" in p: db_buyer.max_price = p["max_price"]
                if "quantity" in p: db_buyer.quantity = p["quantity"]
                if "location" in p: db_buyer.location = p["location"]
                if "urgency" in p: db_buyer.urgency = p["urgency"]
                if "neg_mode" in p: db_buyer.neg_mode = p["neg_mode"]
                if "strategy" in p: db_buyer.strategy = p["strategy"]
                if "status" in p: db_buyer.status = p["status"]
        return p

    @staticmethod
    async def list_all() -> list:
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(DBBuyer))
            rows = res.scalars().all()
            results = []
            for r in rows:
                results.append({
                    "id": r.id,
                    "user_id": r.user_id,
                    "buyer_name": r.buyer_name,
                    "crop": r.crop,
                    "min_price": r.min_price,
                    "max_price": r.max_price,
                    "quantity": r.quantity,
                    "location": r.location,
                    "urgency": r.urgency,
                    "neg_mode": r.neg_mode,
                    "strategy": r.strategy,
                    "status": r.status
                })
            return results

