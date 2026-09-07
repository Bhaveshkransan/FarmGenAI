
import json
from copy import deepcopy
from uuid import uuid4
import asyncio
from sqlalchemy import select

from backend.db.session import AsyncSessionLocal, engine, Base, _run_async
from backend.db.models.schema import *

class Database:
    @classmethod
    def __init__(cls, session):
        session = session

    users: dict = {}
    farmers: dict = {}
    buyers: dict = {}
    produce: dict = {}
    negotiations: dict = {}
    offers: dict = {}
    contracts: dict = {}
    history: dict = {}

    @staticmethod
    def generate_id(prefix: str) -> str:
        return f"{prefix}_{uuid4().hex[:8]}"
    @classmethod
    async def reset(cls):
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.drop_all)
            await conn.run_sync(Base.metadata.create_all)
        Database.users.clear()
        Database.farmers.clear()
        Database.buyers.clear()
        Database.produce.clear()
        Database.negotiations.clear()
        Database.offers.clear()
        Database.contracts.clear()
        Database.history.clear()
    @classmethod
    async def upsert_farmer_async(cls, payload: dict) -> dict:
        p = deepcopy(payload)
        farmer_id = p.get("id") or Database.generate_id("farmer")
        p["id"] = farmer_id
        async with AsyncSessionLocal() as session:
            db_farmer = await session.get(DBFarmer, farmer_id)
            if not db_farmer:
                db_farmer = DBFarmer(id=farmer_id)
                session.add(db_farmer)
            db_farmer.name = p.get("name")
            db_farmer.contact_number = p.get("contact_number")
            db_farmer.location = p.get("location")
            db_farmer.village = p.get("village")
            db_farmer.taluka = p.get("taluka")
            db_farmer.district = p.get("district")
            db_farmer.state = p.get("state")
            db_farmer.latitude = p.get("latitude")
            db_farmer.longitude = p.get("longitude")
            db_farmer.language = p.get("language")
            db_farmer.farm_size_acres = p.get("farm_size_acres")
            db_farmer.farming_type = p.get("farming_type")
            db_farmer.preferences = p.get("preferences")
            await session.commit()
        Database.farmers[farmer_id] = p
        return p
    @classmethod
    async def upsert_buyer_async(cls, payload: dict) -> dict:
        p = deepcopy(payload)
        buyer_id = p.get("id") or Database.generate_id("buyer")
        p["id"] = buyer_id
        async with AsyncSessionLocal() as session:
            async with AsyncSessionLocal() as session:
                db_buyer = await session.get(DBBuyer, buyer_id)
                if not db_buyer:
                    db_buyer = DBBuyer(id=buyer_id)
                    session.add(db_buyer)
                
                db_buyer.user_id = p.get("user_id")
                db_buyer.buyer_name = p.get("buyer_name")
                db_buyer.crop = p.get("crop")
                db_buyer.min_price = p.get("min_price")
                db_buyer.max_price = p.get("max_price")
                db_buyer.quantity = p.get("quantity")
                db_buyer.location = p.get("location")
                db_buyer.urgency = p.get("urgency")
                db_buyer.neg_mode = p.get("neg_mode")
                db_buyer.strategy = p.get("strategy")
                db_buyer.status = p.get("status")
        Database.buyers[buyer_id] = p
        return p
    @classmethod
    async def list_buyers_async(cls) -> list:
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
        Database.buyers = {b["id"]: b for b in results}
        return results
    @classmethod
    async def upsert_produce_async(cls, payload: dict) -> dict:
        p = deepcopy(payload)
        produce_id = p.get("id") or Database.generate_id("produce")
        p["id"] = produce_id
        async with AsyncSessionLocal() as session:
            db_produce = await session.get(DBProduce, produce_id)
            if not db_produce:
                db_produce = DBProduce(id=produce_id)
                session.add(db_produce)
            
            db_produce.user_id = p.get("user_id")
            db_produce.farmer_name = p.get("farmer_name")
            db_produce.crop = p.get("crop")
            db_produce.crop_category = p.get("crop_category")
            db_produce.variety = p.get("variety")
            db_produce.grade = p.get("grade")
            db_produce.quantity = p.get("quantity")
            db_produce.unit = p.get("unit", "kg")
            db_produce.min_sale_quantity = p.get("min_sale_quantity")
            db_produce.expected_price = p.get("expected_price")
            db_produce.min_price = p.get("min_price")
            db_produce.price_unit = p.get("price_unit", "per_kg")
            db_produce.quality_info = p.get("quality_info")
            db_produce.harvest_date = p.get("harvest_date")
            db_produce.availability_date = p.get("availability_date")
            db_produce.preferred_selling_date = p.get("preferred_selling_date")
            db_produce.shelf_life = p.get("shelf_life")
            db_produce.location = p.get("location")
            db_produce.latitude = p.get("latitude")
            db_produce.longitude = p.get("longitude")
            db_produce.storage_info = p.get("storage_info")
            db_produce.processing_info = p.get("processing_info")
            db_produce.transport_reqs = p.get("transport_reqs")
            db_produce.selected_services = p.get("selected_services")
            db_produce.images = p.get("images")
            db_produce.description = p.get("description")
            db_produce.language = p.get("language")
            db_produce.status = p.get("status", "ACTIVE")
            await session.commit()
        Database.produce[produce_id] = p
        return p
    @classmethod
    async def list_produce_async(cls) -> list:
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(DBProduce))
            rows = res.scalars().all()
            results = []
            for r in rows:
                results.append({
                    "id": r.id,
                    "user_id": r.user_id,
                    "farmer_name": r.farmer_name,
                    "crop": r.crop,
                    "crop_category": r.crop_category,
                    "variety": r.variety,
                    "grade": r.grade,
                    "quantity": r.quantity,
                    "unit": r.unit,
                    "min_sale_quantity": r.min_sale_quantity,
                    "expected_price": r.expected_price,
                    "min_price": r.min_price,
                    "price_unit": r.price_unit,
                    "quality_info": r.quality_info,
                    "harvest_date": r.harvest_date,
                    "availability_date": r.availability_date,
                    "preferred_selling_date": r.preferred_selling_date,
                    "shelf_life": r.shelf_life,
                    "location": r.location,
                    "latitude": r.latitude,
                    "longitude": r.longitude,
                    "storage_info": r.storage_info,
                    "processing_info": r.processing_info,
                    "transport_reqs": r.transport_reqs,
                    "selected_services": r.selected_services,
                    "images": r.images,
                    "description": r.description,
                    "language": r.language,
                    "status": r.status
                })
        Database.produce = {p["id"]: p for p in results}
        return results
    @classmethod
    async def get_produce_async(cls, produce_id: str) -> dict | None:
        async with AsyncSessionLocal() as session:
            db_produce = await session.get(DBProduce, produce_id)
            if db_produce:
                return {
                    "id": db_produce.id,
                    "user_id": db_produce.user_id,
                    "farmer_name": db_produce.farmer_name,
                    "crop": db_produce.crop,
                    "crop_category": db_produce.crop_category,
                    "variety": db_produce.variety,
                    "grade": db_produce.grade,
                    "quantity": db_produce.quantity,
                    "unit": db_produce.unit,
                    "min_sale_quantity": db_produce.min_sale_quantity,
                    "expected_price": db_produce.expected_price,
                    "min_price": db_produce.min_price,
                    "price_unit": db_produce.price_unit,
                    "quality_info": db_produce.quality_info,
                    "harvest_date": db_produce.harvest_date,
                    "availability_date": db_produce.availability_date,
                    "preferred_selling_date": db_produce.preferred_selling_date,
                    "shelf_life": db_produce.shelf_life,
                    "location": db_produce.location,
                    "latitude": db_produce.latitude,
                    "longitude": db_produce.longitude,
                    "storage_info": db_produce.storage_info,
                    "processing_info": db_produce.processing_info,
                    "transport_reqs": db_produce.transport_reqs,
                    "selected_services": db_produce.selected_services,
                    "images": db_produce.images,
                    "description": db_produce.description,
                    "language": db_produce.language,
                    "status": db_produce.status
                }
            return None
    @classmethod
    async def delete_produce_async(cls, produce_id: str):
        async with AsyncSessionLocal() as session:
            async with AsyncSessionLocal() as session:
                db_produce = await session.get(DBProduce, produce_id)
                if db_produce:
                    db_produce.status = "EXPIRED"
        if produce_id in Database.produce:
            Database.produce[produce_id]["status"] = "EXPIRED"
    @classmethod
    async def create_booking_async(cls, booking: dict):
        async with AsyncSessionLocal() as session:
            async with AsyncSessionLocal() as session:
                db_booking = DBBooking(
                    booking_id=booking["booking_id"],
                    negotiation_id=booking.get("negotiation_id"),
                    crop=booking.get("crop"),
                    origin_location=booking.get("origin_location"),
                    destination_location=booking.get("destination_location"),
                    booked_by=booking.get("booked_by"),
                    status=booking.get("status"),
                    vehicle_id=booking.get("vehicle_id"),
                    truck=booking.get("truck"),
                    capacity_kg=booking.get("capacity_kg"),
                    quantity=booking.get("quantity"),
                    distance_km=booking.get("distance_km"),
                    pickup_time=booking.get("pickup_time"),
                    estimated_transit_hours=booking.get("estimated_transit_hours"),
                    estimated_cost=booking.get("estimated_cost"),
                    created_at=booking.get("created_at")
                )
                session.add(db_booking)
    @classmethod
    async def get_booking_async(cls, booking_id: str) -> dict | None:
        async with AsyncSessionLocal() as session:
            db_booking = await session.get(DBBooking, booking_id)
            if db_booking:
                return {
                    "booking_id": db_booking.booking_id,
                    "negotiation_id": db_booking.negotiation_id,
                    "crop": db_booking.crop,
                    "origin_location": db_booking.origin_location,
                    "destination_location": db_booking.destination_location,
                    "booked_by": db_booking.booked_by,
                    "status": db_booking.status,
                    "vehicle_id": db_booking.vehicle_id,
                    "truck": db_booking.truck,
                    "capacity_kg": db_booking.capacity_kg,
                    "quantity": db_booking.quantity,
                    "distance_km": db_booking.distance_km,
                    "pickup_time": db_booking.pickup_time,
                    "estimated_transit_hours": db_booking.estimated_transit_hours,
                    "estimated_cost": db_booking.estimated_cost,
                    "created_at": db_booking.created_at,
                    "updated_at": db_booking.updated_at
                }
            return None
    @classmethod
    async def list_bookings_async(cls) -> list:
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(DBBooking))
            rows = res.scalars().all()
            return [{
                "booking_id": r.booking_id,
                "negotiation_id": r.negotiation_id,
                "crop": r.crop,
                "origin_location": r.origin_location,
                "destination_location": r.destination_location,
                "booked_by": r.booked_by,
                "status": r.status,
                "vehicle_id": r.vehicle_id,
                "truck": r.truck,
                "capacity_kg": r.capacity_kg,
                "quantity": r.quantity,
                "distance_km": r.distance_km,
                "pickup_time": r.pickup_time,
                "estimated_transit_hours": r.estimated_transit_hours,
                "estimated_cost": r.estimated_cost,
                "created_at": r.created_at,
                "updated_at": r.updated_at
            } for r in rows]
    @classmethod
    async def update_booking_async(cls, booking_id: str, payload: dict):
        async with AsyncSessionLocal() as session:
            async with AsyncSessionLocal() as session:
                db_booking = await session.get(DBBooking, booking_id)
                if db_booking:
                    if "status" in payload: db_booking.status = payload["status"]
                    if "updated_at" in payload: db_booking.updated_at = payload["updated_at"]
    @classmethod
    async def create_negotiation_async(cls, payload: dict) -> dict:
        p = deepcopy(payload)
        neg_id = p.get("negotiation_id") or Database.generate_id("neg")
        p["negotiation_id"] = neg_id
        async with AsyncSessionLocal() as session:
            async with AsyncSessionLocal() as session:
                db_neg = await session.get(DBNegotiation, neg_id)
                if not db_neg:
                    db_neg = DBNegotiation(negotiation_id=neg_id)
                    session.add(db_neg)
                db_neg.crop = p.get("crop")
                db_neg.quantity = p.get("quantity")
                db_neg.farmer_id = p.get("farmer_id")
                db_neg.buyer_id = p.get("buyer_id")
                db_neg.user_id = p.get("user_id")
                db_neg.farmer_name = p.get("farmer_name")
                db_neg.status = p.get("status")
                db_neg.current_round = p.get("current_round", 0)
                db_neg.summary = p.get("summary")
                db_neg.final_price = p.get("final_price")
                tp = p.get("transport_plan")
                if isinstance(tp, dict):
                    import json
                    tp = json.dumps(tp)
                db_neg.transport_plan = tp
                db_neg.peer_node = p.get("peer_node")
                db_neg.logs = p.get("logs", [])
                db_neg.market_offers = p.get("market_offers", [])
                db_neg.selected_buyer = p.get("selected_buyer", {})
                db_neg.signatures = p.get("signatures", {})
        Database.negotiations[neg_id] = p
        return p
    @classmethod
    async def get_negotiation_async(cls, neg_id: str) -> dict:
        async with AsyncSessionLocal() as session:
            db_neg = await session.get(DBNegotiation, neg_id)
            if db_neg:
                return {
                    "negotiation_id": db_neg.negotiation_id,
                    "crop": db_neg.crop,
                    "quantity": db_neg.quantity,
                    "farmer_id": db_neg.farmer_id,
                    "buyer_id": db_neg.buyer_id,
                    "user_id": db_neg.user_id,
                    "farmer_name": db_neg.farmer_name,
                    "status": db_neg.status,
                    "current_round": db_neg.current_round,
                    "summary": db_neg.summary,
                    "final_price": db_neg.final_price,
                    "transport_plan": db_neg.transport_plan,
                    "peer_node": db_neg.peer_node,
                    "logs": db_neg.logs or [],
                    "market_offers": db_neg.market_offers or [],
                    "selected_buyer": db_neg.selected_buyer or {},
                    "signatures": db_neg.signatures or {}
                }
            return None
    @classmethod
    async def update_negotiation_async(cls, neg_id: str, payload: dict):
        payload["negotiation_id"] = neg_id
        async with AsyncSessionLocal() as session:
            async with AsyncSessionLocal() as session:
                db_neg = await session.get(DBNegotiation, neg_id)
                if not db_neg:
                    db_neg = DBNegotiation(negotiation_id=neg_id)
                    session.add(db_neg)
                if "crop" in payload: db_neg.crop = payload["crop"]
                if "quantity" in payload: db_neg.quantity = payload["quantity"]
                if "farmer_id" in payload: db_neg.farmer_id = payload["farmer_id"]
                if "buyer_id" in payload: db_neg.buyer_id = payload["buyer_id"]
                if "user_id" in payload: db_neg.user_id = payload["user_id"]
                if "farmer_name" in payload: db_neg.farmer_name = payload["farmer_name"]
                if "status" in payload: db_neg.status = payload["status"]
                if "current_round" in payload: db_neg.current_round = payload["current_round"]
                if "summary" in payload: db_neg.summary = payload["summary"]
                if "final_price" in payload: db_neg.final_price = payload["final_price"]
                if "transport_plan" in payload: db_neg.transport_plan = payload["transport_plan"]
                if "peer_node" in payload: db_neg.peer_node = payload["peer_node"]
                if "logs" in payload: db_neg.logs = payload["logs"]
                if "market_offers" in payload: db_neg.market_offers = payload["market_offers"]
                if "selected_buyer" in payload: db_neg.selected_buyer = payload["selected_buyer"]
                if "signatures" in payload: db_neg.signatures = payload["signatures"]
        Database.negotiations[neg_id] = payload
    @classmethod
    async def append_offer_async(cls, negotiation_id: str, payload: dict) -> dict:
        p = deepcopy(payload)
        p["id"] = Database.generate_id("offer")
        p["negotiation_id"] = negotiation_id
        async with AsyncSessionLocal() as session:
            async with AsyncSessionLocal() as session:
                db_offer = DBOffer(
                    id=p["id"],
                    negotiation_id=negotiation_id,
                    round_num=p.get("round", 0),
                    sender=p.get("sender"),
                    price=p.get("price"),
                    quantity=p.get("quantity"),
                    message=p.get("message")
                )
                session.add(db_offer)
        Database.offers[p["id"]] = p
        return p
    @classmethod
    async def get_offers_for_negotiation_async(cls, negotiation_id: str) -> list:
        async with AsyncSessionLocal() as session:
            res = await session.execute(
                select(DBOffer)
                .where(DBOffer.negotiation_id == negotiation_id)
                .order_by(DBOffer.round_num)
            )
            rows = res.scalars().all()
            return [{
                "id": r.id,
                "negotiation_id": r.negotiation_id,
                "round": r.round_num,
                "sender": r.sender,
                "price": r.price,
                "quantity": r.quantity,
                "message": r.message
            } for r in rows]
    @classmethod
    async def create_contract_async(cls, payload: dict) -> dict:
        p = deepcopy(payload)
        p["id"] = Database.generate_id("contract")
        async with AsyncSessionLocal() as session:
            async with AsyncSessionLocal() as session:
                db_contract = DBContract(
                    id=p["id"],
                    negotiation_id=p.get("negotiation_id"),
                    farmer_id=p.get("farmer_id"),
                    buyer_id=p.get("buyer_id"),
                    crop=p.get("crop"),
                    quantity=p.get("quantity"),
                    final_price=p.get("final_price"),
                    status=p.get("status")
                )
                session.add(db_contract)
        Database.contracts[p["id"]] = p
        return p
    @classmethod
    async def add_history_async(cls, user_id: str, entry: dict):
        record_id = Database.generate_id("hist")
        entry = deepcopy(entry)
        entry["user_id"] = user_id
        async with AsyncSessionLocal() as session:
            async with AsyncSessionLocal() as session:
                db_history = DBHistory(
                    id=record_id,
                    user_id=user_id,
                    negotiation_id=entry.get("negotiation_id"),
                    crop=entry.get("crop"),
                    quantity=entry.get("quantity"),
                    status=entry.get("status"),
                    final_price=entry.get("final_price"),
                    summary=entry.get("summary"),
                    market_price=entry.get("market_price"),
                    negotiation_rounds=entry.get("negotiation_rounds"),
                    successful=entry.get("successful"),
                    failure_reason=entry.get("failure_reason"),
                    farmer_strategy=entry.get("farmer_strategy"),
                    farmer_reward=entry.get("farmer_reward"),
                    buyer_strategy=entry.get("buyer_strategy"),
                    buyer_reward=entry.get("buyer_reward"),
                    warehouse_strategy=entry.get("warehouse_strategy"),
                    warehouse_reward=entry.get("warehouse_reward"),
                    transport_strategy=entry.get("transport_strategy"),
                    transport_reward=entry.get("transport_reward"),
                    processor_strategy=entry.get("processor_strategy"),
                    processor_reward=entry.get("processor_reward"),
                    compost_strategy=entry.get("compost_strategy"),
                    compost_reward=entry.get("compost_reward")
                )
                session.add(db_history)
        if user_id not in Database.history:
            Database.history[user_id] = []
        Database.history[user_id].append(entry)
    @classmethod

    def get_history(cls, user_id: str = "all") -> list:
        async def _get():
            async with AsyncSessionLocal() as session:
                if user_id == "all":
                    res = await session.execute(select(DBHistory).order_by(DBHistory.id.desc()).limit(50))
                else:
                    res = await session.execute(select(DBHistory).where(DBHistory.user_id == user_id).order_by(DBHistory.id.desc()))
                rows = res.scalars().all()
                return [json.loads(r.data) if r.data else {
                    "negotiation_id": r.negotiation_id,
                    "crop": r.crop,
                    "quantity": r.quantity,
                    "status": r.status,
                    "final_price": r.final_price,
                    "summary": r.summary,
                    "farmer_strategy": r.farmer_strategy,
                    "farmer_reward": r.farmer_reward,
                    "buyer_strategy": r.buyer_strategy,
                    "buyer_reward": r.buyer_reward,
                    "warehouse_strategy": r.warehouse_strategy,
                    "warehouse_reward": r.warehouse_reward,
                    "transport_strategy": r.transport_strategy,
                    "transport_reward": r.transport_reward,
                    "processor_strategy": r.processor_strategy,
                    "processor_reward": r.processor_reward,
                    "compost_strategy": r.compost_strategy,
                    "compost_reward": r.compost_reward
                } for r in rows]
        return _run_async(_get())
    @classmethod
    async def get_history_async(cls, user_id: str = "all") -> list:
        async with AsyncSessionLocal() as session:
            if user_id == "all":
                res = await session.execute(select(DBHistory).order_by(DBHistory.id.desc()).limit(50))
            else:
                res = await session.execute(select(DBHistory).where(DBHistory.user_id == user_id).order_by(DBHistory.id.desc()))
            rows = res.scalars().all()
            results = []
            for r in rows:
                results.append({
                    "negotiation_id": r.negotiation_id,
                    "crop": r.crop,
                    "quantity": r.quantity,
                    "status": r.status,
                    "final_price": r.final_price,
                    "summary": r.summary,
                    "farmer_strategy": r.farmer_strategy,
                    "farmer_reward": r.farmer_reward,
                    "buyer_strategy": r.buyer_strategy,
                    "buyer_reward": r.buyer_reward,
                    "warehouse_strategy": r.warehouse_strategy,
                    "warehouse_reward": r.warehouse_reward,
                    "transport_strategy": r.transport_strategy,
                    "transport_reward": r.transport_reward,
                    "processor_strategy": r.processor_strategy,
                    "processor_reward": r.processor_reward,
                    "compost_strategy": r.compost_strategy,
                    "compost_reward": r.compost_reward
                })
            return results
    @classmethod
    def get_msp_price(cls, crop: str) -> float | None:
        async def _get():
            async with AsyncSessionLocal() as session:
                stmt = select(DBMspPrice).where(DBMspPrice.crop.ilike(crop))
                res = await session.execute(stmt)
                row = res.scalars().first()
                return row.msp_price_per_quintal if row else None
        try:
            return _run_async(_get())
        except Exception as e:
            print("MSP PRICE EXCEPTION:", e)
            return None
    @classmethod
    def get_market_mappings(cls, district: str) -> list:
        async def _get():
            async with AsyncSessionLocal() as session:
                stmt = select(DBMarketMapping).where(DBMarketMapping.district.ilike(district))
                res = await session.execute(stmt)
                rows = res.scalars().all()
                return [{"district": r.district, "market_name": r.market_name, "state": r.state} for r in rows]
        try:
            return _run_async(_get())
        except Exception:
            return []
    @classmethod
    def get_crop_quality_reference(cls, crop: str) -> list:
        async def _get():
            async with AsyncSessionLocal() as session:
                stmt = select(DBCropQualityReference).where(DBCropQualityReference.crop.ilike(crop))
                res = await session.execute(stmt)
                rows = res.scalars().all()
                return [{
                    "crop": r.crop,
                    "variety": r.variety,
                    "grade": r.grade,
                    "min_size_mm": r.min_size_mm,
                    "max_moisture_pct": r.max_moisture_pct,
                    "color_standards": r.color_standards,
                    "skin_firmness": r.skin_firmness,
                    "common_defects_allowed": r.common_defects_allowed
                } for r in rows]
        try:
            return _run_async(_get())
        except Exception:
            return []
    @classmethod
    def get_seasonal_calendar(cls) -> list:
        async def _get():
            async with AsyncSessionLocal() as session:
                stmt = select(DBSeasonalCalendar)
                res = await session.execute(stmt)
                rows = res.scalars().all()
                return [{
                    "season_id": r.season_id,
                    "event_name": r.event_name,
                    "month_range": r.month_range,
                    "affected_crops": r.affected_crops,
                    "price_impact_trend": r.price_impact_trend,
                    "market_behavior_description": r.market_behavior_description
                } for r in rows]
        try:
            return _run_async(_get())
        except Exception:
            return []
    @classmethod
    def get_trust_score(cls, user_id: str) -> dict | None:
        async def _get():
            async with AsyncSessionLocal() as session:
                stmt = select(DBTrustScore).where(DBTrustScore.user_id == user_id)
                res = await session.execute(stmt)
                r = res.scalars().first()
                if not r:
                    return None
                return {
                    "user_id": r.user_id,
                    "trust_score_final": r.trust_score_final
                }
        try:
            return _run_async(_get())
        except Exception:
            return None
    @classmethod

    def get_warehouse_list(cls, district: str) -> list:
        async def _get():
            async with AsyncSessionLocal() as session:
                stmt = select(DBWarehouse).where(DBWarehouse.district.ilike(district))
                res = await session.execute(stmt)
                rows = res.scalars().all()
                return [{
                    "warehouse_id": r.warehouse_id,
                    "name": r.name,
                    "district": r.district,
                    "location": r.location,
                    "type": r.type,
                    "capacity_mt": r.capacity_mt,
                    "available_capacity_mt": r.available_capacity_mt,
                    "price_per_mt_per_day": r.price_per_mt_per_day,
                    "rating": r.rating,
                    "contact_number": r.contact_number
                } for r in rows]
        try:
            return _run_async(_get())
        except Exception:
            return []
    @classmethod

    def get_transporter_list(cls, current_location: str) -> list:
        async def _get():
            async with AsyncSessionLocal() as session:
                stmt = select(DBTransporter).where(DBTransporter.current_location.ilike(current_location))
                res = await session.execute(stmt)
                rows = res.scalars().all()
                return [{
                    "transporter_id": r.transporter_id,
                    "provider_name": r.provider_name,
                    "vehicle_type": r.vehicle_type,
                    "capacity_mt": r.capacity_mt,
                    "rate_per_km": r.rate_per_km,
                    "base_fare": r.base_fare,
                    "rating": r.rating,
                    "contact_number": r.contact_number,
                    "current_location": r.current_location
                } for r in rows]
        try:
            return _run_async(_get())
        except Exception:
            return []

