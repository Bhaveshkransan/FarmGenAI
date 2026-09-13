from sqlalchemy.ext.asyncio import AsyncSession
from backend.repositories.user_repository import UserRepository
import asyncio
from agents.buyer_agent import BuyerAgent
from agents.compost_agent import CompostAgent
from agents.farmer_agent import FarmerAgent
from agents.processor_agent import ProcessorAgent
from agents.transporter_agent import TransporterAgent
from agents.warehouse_agent import WarehouseAgent
from agents.restaurant_agent import RestaurantAgent
from database.db import Database
from backend.services.history_service import add_history
from negotiation_engine.negotiation_manager import NegotiationManager
from nodes.node_hub import hub
from datetime import datetime, timezone


DEFAULT_BUYER_PROFILES = [
    {
        "id": "buyer_wholesale_hub",
        "name": "Wholesale Hub",
        "budget": 26000,
        "max_quantity": 1400,
        "target_price": 20,
        "location": "Nashik",
        "strategy": "Bulk purchase for city mandis",
    },
    {
        "id": "buyer_fresh_mart",
        "name": "FreshMart Retail",
        "budget": 21000,
        "max_quantity": 900,
        "target_price": 22,
        "location": "Pune",
        "strategy": "High-quality produce for retail shelves",
    },
    {
        "id": "buyer_food_chain",
        "name": "FoodChain Kitchens",
        "budget": 18500,
        "max_quantity": 700,
        "target_price": 19,
        "location": "Mumbai",
        "strategy": "Stable mid-price demand for kitchens",
    },
    {
        "id": "buyer_export_link",
        "name": "ExportLink Foods",
        "budget": 32000,
        "max_quantity": 1600,
        "target_price": 21,
        "location": "Nagpur",
        "strategy": "Cross-city consolidation buyer",
    },
    {
        "id": "buyer_greenleaf_dining",
        "name": "GreenLeaf Premium Dining",
        "budget": 15000,
        "max_quantity": 50,
        "target_price": 35,
        "location": "Mumbai",
        "strategy": "restaurant",
    },
    {
        "id": "buyer_agro_exports",
        "name": "Agro Global Exports",
        "budget": 45000,
        "max_quantity": 2000,
        "target_price": 24,
        "location": "Thane",
        "strategy": "Premium export grade bulk buyer",
    },
    {
        "id": "buyer_local_mandi_1",
        "name": "Kalyan Regional Mandi",
        "budget": 12000,
        "max_quantity": 500,
        "target_price": 18,
        "location": "Kalyan",
        "strategy": "Local distribution aggregator",
    },
    {
        "id": "buyer_city_fresh",
        "name": "CityFresh Organics",
        "budget": 14000,
        "max_quantity": 400,
        "target_price": 28,
        "location": "Pune",
        "strategy": "premium",
    },
    {
        "id": "buyer_industrial_1",
        "name": "Reliable Food Processing",
        "budget": 50000,
        "max_quantity": 3000,
        "target_price": 17,
        "location": "Aurangabad",
        "strategy": "Industrial volume procurement",
    },
]

DEFAULT_FARMER_LISTINGS = [
    {
        "farmer_name": "Ramesh Patil",
        "crop": "Tomato",
        "quantity": 1200,
        "min_price": 18,
        "shelf_life": 4,
        "location": "Nashik",
        "quality": "A",
        "language": "Marathi",
    },
    {
        "farmer_name": "Sita Deshmukh",
        "crop": "Onion",
        "quantity": 1800,
        "min_price": 15,
        "shelf_life": 6,
        "location": "Pune",
        "quality": "A",
        "language": "Hindi",
    },
    {
        "farmer_name": "Arjun Kale",
        "crop": "Potato",
        "quantity": 2200,
        "min_price": 14,
        "shelf_life": 8,
        "location": "Ahmednagar",
        "quality": "B",
        "language": "Marathi",
    },
    {
        "farmer_name": "Meera Jagtap",
        "crop": "Cabbage",
        "quantity": 900,
        "min_price": 16,
        "shelf_life": 5,
        "location": "Satara",
        "quality": "A",
        "language": "English",
    },
]


class NegotiationService:
    def __init__(self, db):
        self.db = db
        self.db_repo = Database(db)
        self.active_negotiations = {}

    async def ensure_default_buyers(self):
        for buyer in DEFAULT_BUYER_PROFILES:
            await self.db_repo.upsert_buyer_async(buyer)

    async def ensure_default_farmers_and_produce(self):
        existing = await self.db_repo.list_produce_async()
        if existing:
            return

        for listing in DEFAULT_FARMER_LISTINGS:
            farmer = await self.db_repo.upsert_farmer_async(
                {
                    "name": listing["farmer_name"],
                    "location": listing["location"],
                    "language": listing["language"],
                }
            )
            await self.db_repo.upsert_produce_async(
                {
                    "farmer_id": farmer["id"],
                    "crop": listing["crop"],
                    "quantity": listing["quantity"],
                    "min_price": listing["min_price"],
                    "shelf_life": listing["shelf_life"],
                    "quality": listing["quality"],
                    "location": listing["location"],
                    "language": listing["language"],
                    "status": "LISTED",
                }
            )

    async def _build_farmer(self, payload: dict):
        storage_info = payload.get("storage_info") or {}
        processing_info = payload.get("processing_info") or {}
        
        return FarmerAgent(
            name=payload.get("farmer_name", "FarmerAgent"),
            crop=payload["crop"],
            quantity=float(payload["quantity"]),
            min_price=float(payload["min_price"]),
            shelf_life=int(payload.get("shelf_life", 3)),
            location=payload.get("location"),
            min_sale_quantity=float(payload.get("min_sale_quantity", 100)),
            initial_price=float(payload.get("expected_price", float(payload["min_price"]) * 1.2)),
            has_storage_option=payload.get("storage_available", bool(storage_info.get("available", True) if storage_info else False)),
            has_processor_option=payload.get("processing_available", bool(processing_info.get("available", True) if processing_info else False)),
        )

    async def _build_buyer(self, buyer_profile: dict):
        strategy = buyer_profile.get("strategy", "").lower()
        if "restaurant" in strategy or "premium" in strategy:
            return RestaurantAgent(
                name=buyer_profile["name"],
                budget=float(buyer_profile["budget"]),
                max_quantity=int(buyer_profile["max_quantity"]),
                target_price=float(buyer_profile["target_price"]),
                location=buyer_profile.get("location", "Market"),
                min_shelf_life=3,
                premium_ratio=1.2
            )
        
        return BuyerAgent(
            name=buyer_profile["name"],
            budget=float(buyer_profile["budget"]),
            max_quantity=int(buyer_profile["max_quantity"]),
            target_price=float(buyer_profile["target_price"]),
            location=buyer_profile.get("location", "Market")
        )

    async def _build_support_agents(self, payload: dict):
        warehouse = WarehouseAgent(
            name="WarehouseAgent",
            capacity=int(payload.get("warehouse_capacity", 5000)),
            storage_cost_per_kg=float(payload.get("storage_cost_per_kg", 1.8)),
            location=payload.get("location", "Nashik")
        )
        processor = ProcessorAgent(
            name="ProcessorAgent",
            crop_type=payload["crop"],
            processing_capacity=int(payload.get("processor_capacity", payload["quantity"])),
            processing_cost_per_kg=float(payload.get("processing_cost_per_kg", 2.0)),
            target_price=float(payload.get("processor_target_price", payload["min_price"] - 1)),
            max_price=float(payload.get("processor_max_price", payload["min_price"] + 2))
        )
        compost = CompostAgent(name="CompostAgent", base_price=float(payload.get("compost_price", 8)))
        transporter = TransporterAgent(
            name="TransporterAgent",
            vehicle_capacity=int(payload.get("transporter_capacity", payload["quantity"])),
            cost_per_km_per_kg=float(payload.get("transport_cost_per_km_per_kg", 0.03)),
            base_fee=float(payload.get("transport_base_fee", 450))
        )
        return warehouse, processor, compost, transporter

    async def _generate_market_offers(self, payload: dict):
        await self.ensure_default_buyers()
        from backend.services.matching_service import match_listing_to_buyers
        
        # Prepare the listing payload to match what match_listing_to_buyers expects
        listing = {
            "user_id": payload.get("user_id"),
            "crop": payload["crop"],
            "quantity": payload["quantity"],
            "min_price": payload["min_price"],
            "market_price": payload.get("market_price", float(payload["min_price"]) + 1),
            "location": payload.get("location", "Unknown")
        }
        
        offers = await match_listing_to_buyers(listing)
        return offers

    async def start_negotiation(
        self,
        payload: dict,
        scenario: str = "direct-sale",
        pre_id: str = None,
        live_event_callback=None,
    ):
        buyer_mode = bool(payload.get("buyer_mode"))
        if buyer_mode:
            target = float(payload.get("buyer_target_price", payload.get("min_price", 18) + 1))
            quantity = float(payload.get("buyer_max_quantity", payload.get("quantity", 0)))
            budget = float(payload.get("buyer_budget", max(quantity, 1.0) * max(target, 1.0) * 1.2))
            selected_offer = {
                "buyer_id": payload.get("user_id") or "buyer_manual",
                "buyer_name": payload.get("buyer_name", "Buyer"),
                "location": payload.get("buyer_location", payload.get("location", "Market")),
                "strategy": payload.get("buyer_strategy", "Buyer initiated direct negotiation"),
                "offered_price": round(target, 2),
                "offered_quantity": round(quantity, 2),
                "budget": round(budget, 2),
                "target_price": round(target, 2),
                "status": "VIABLE",
                "score": 1000,
            }
            market_offers = [selected_offer]
        else:
            # Multi-buyer discovery
            market_offers = await self._generate_market_offers(payload)
        
        all_buyers = []
        for off in market_offers[:6]:  # Test with up to 6 top buyers
            buyer = await self._build_buyer({
                "name": off["buyer_name"],
                "budget": off["budget"],
                "max_quantity": off["offered_quantity"],
                "target_price": off["target_price"],
                "location": off["location"],
                "strategy": off.get("strategy", "")
            })
            all_buyers.append(buyer)
        
        selected_offer = market_offers[0] if market_offers else None
        
        farmer = await self._build_farmer(payload)
        warehouse, processor, compost, transporter = await self._build_support_agents(payload)
        
        manager = NegotiationManager(
            farmer=farmer,
            buyers=all_buyers,
            warehouse=warehouse,
            processor=processor,
            compost=compost,
            max_rounds=int(payload.get("max_rounds", 8)),
            live_event_callback=live_event_callback,
        )

        result = await manager.start_negotiation(
            market_price=float(payload.get("market_price", payload["min_price"] + 1)),
            scenario=scenario
        )

        # Injects transport calculations into the logs if a deal was reached
        if result["state"] in ("DEAL", "ESCALATED_STORAGE", "ESCALATED_PROCESSING"):
             dist = 45 # baseline km
             cost = transporter.calculate_transport_cost(payload["quantity"], dist)
             manager.logs.append(f"🚛 Logistics: {transporter.name} calculated ₹{cost:.2f} for {dist}km transit.")
             manager.logs.append(f"📜 Finalizing supply chain record for audit...")

        screening_logs = [
            f"Marketplace scan: {len(market_offers)} buyers evaluated for {payload['crop']}.",
        ]
        screening_logs.extend(
            f"🔍 {offer['buyer_name']}: bid ₹{offer['offered_price']}/kg for {offer['offered_quantity']}kg ({offer['status']})"
            for offer in market_offers
        )
        manager.logs = screening_logs + manager.logs

        farmer_row = await self.db_repo.upsert_farmer_async(
            {
                "name": payload.get("farmer_name", "Unknown Farmer"),
                "location": payload.get("location", "Unknown"),
                "language": payload.get("language", "English")
            }
        )
        produce_row = await self.db_repo.upsert_produce_async(
            {
                "farmer_name": farmer_row["name"],
                "crop": payload["crop"],
                "quantity": payload["quantity"],
                "min_price": payload["min_price"],
                "shelf_life": payload.get("shelf_life", 3),
                "quality": payload.get("quality", "A"),
                "location": payload.get("location", "Unknown"),
                "language": payload.get("language", "English"),
                "status": result["state"]
            }
        )

        # Identify all agents that participated in this negotiation
        agents_involved = [farmer_row["name"]]
        if selected_offer:
            agents_involved.append(selected_offer["buyer_name"])
        if result["state"] in ("ESCALATED_STORAGE",):
            agents_involved.append("WarehouseAgent")
        elif result["state"] in ("ESCALATED_PROCESSING",):
            agents_involved.append("ProcessorAgent")
        elif result["state"] in ("ESCALATED_COMPOST",):
            agents_involved.append("CompostAgent")

        buyer_loc = selected_offer.get("location", "Market") if selected_offer else all_buyers[0].location
        if farmer.location != buyer_loc:
            # Maharashtra-focused smart distance mock
            mh_cities = ["Mumbai", "Pune", "Nashik", "Nagpur", "Satara", "Kolhapur", "Solapur"]
            if farmer.location in mh_cities and buyer_loc in mh_cities:
                dist = 180.0  # Regional Maharashtra distance
            elif farmer.location == buyer_loc:
                dist = 45.0   # Local district 
            else:
                dist = 950.0  # Interstate distance
            
            cost = transporter.calculate_transport_cost(payload["quantity"], dist)
            transport_plan = {
                "agent": transporter.name,
                "cost": cost,
                "distance": dist,
                "capacity": transporter.vehicle_capacity
            }
        else:
            transport_plan = {
                "agent": transporter.name,
                "base_fee": transporter.base_fee,
                "capacity": transporter.vehicle_capacity,
            }

        negotiation_payload = {
            "user_id": payload.get("user_id"),
            "status": result["state"],
            "summary": result["summary"],
            "scenario": scenario,
            "produce_id": produce_row["id"],
            "farmer_id": farmer_row["id"],
            "farmer": farmer_row["name"],
            "crop": payload["crop"],
            "quantity": float(payload["quantity"]),
            "final_price": result["deal"].get("price") if result.get("deal") else None,
            "agents_involved": agents_involved,
            "next_action": result.get("next_action"),
            "market_offers": market_offers,
            "selected_buyer": selected_offer,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "transport_plan": transport_plan,
        }
        if pre_id:
            negotiation_payload["negotiation_id"] = pre_id
        negotiation_row = await self.db_repo.create_negotiation_async(negotiation_payload)

        for idx, event in enumerate(manager.memory.get_offers(), start=1):
            offer = event["offer"]
            agent_name = event["agent"]
            if event["agent"] == "Buyer" and selected_offer:
                agent_name = selected_offer["buyer_name"]
            elif event["agent"] == "Farmer":
                agent_name = farmer_row["name"]

            await self.db_repo.append_offer_async(
                negotiation_row["negotiation_id"],
                {
                    "round": idx,
                    "agent": agent_name,
                    "price": offer.get("price", 0),
                    "decision": offer.get("type", "OFFER"),
                    "quantity": offer.get("quantity", 0),
                    "message": offer.get("message", "")
                }
            )

        if result.get("deal"):
            contract_data = {
                "negotiation_id": negotiation_row["negotiation_id"],
                "scenario": scenario,
                "price": result["deal"].get("price", 0),
                "quantity": result["deal"].get("quantity", 0),
                "state": result["state"],
                "farmer_id": farmer_row["name"],
                "peer_node": selected_offer.get("buyer_name", "Wholesale Buyer") if selected_offer else "Wholesale Buyer",
                "crop": payload["crop"]
            }
            await self.db_repo.create_contract_async(contract_data)
            # RECORD TO P2P LEDGER (Phase F)
            hub.record_signed_deal(contract_data)

        status_payload = await self._build_status_payload(negotiation_row["negotiation_id"], manager, result)
        self.active_negotiations[negotiation_row["negotiation_id"]] = status_payload

        # Persist to shared history so all users can see past negotiations
        await add_history("all", {
            "negotiation_id": negotiation_row["negotiation_id"],
            "user_id": payload.get("user_id"),
            "farmer": farmer_row["name"],
            "crop": payload["crop"],
            "quantity": float(payload["quantity"]),
            "status": result["state"],
            "final_price": result["deal"].get("price") if result.get("deal") else None,
            "summary": result["summary"],
            "selected_buyer": selected_offer.get("buyer_name") if selected_offer else None,
            "created_at": negotiation_row.get("created_at", ""),
            "logs": manager.logs[:30],
        })

        # Notify UI via thread-safe callback
        if live_event_callback:
            live_event_callback({
                "type": "scenario_ready",
                "data": {
                    "negotiation_id": negotiation_row["negotiation_id"],
                    "farmer": farmer_row["name"],
                    "crop": payload["crop"],
                    "status": result["state"]
                }
            })

        return status_payload

    async def _build_status_payload(self, negotiation_id: str, manager: NegotiationManager, result: dict):
        row = self.db_repo.negotiations.get(negotiation_id, {})
        offers = await self.db_repo.get_offers_for_negotiation_async(negotiation_id)
        return {
            "negotiation_id": negotiation_id,
            "status": result["state"],
            "summary": result["summary"],
            "final_price": result["deal"].get("price") if result.get("deal") else None,
            "farmer": row.get("farmer"),
            "crop": row.get("crop"),
            "quantity": row.get("quantity"),
            "agents_involved": row.get("agents_involved", []),
            "offers": offers,
            "logs": manager.logs,
            "events": manager.memory.get_events(),
            "price_series": manager.memory.get_price_series(),
            "next_action": result.get("next_action"),
            "deal": result.get("deal"),
            "market_offers": row.get("market_offers", []),
            "selected_buyer": row.get("selected_buyer"),
            "transport_plan": row.get("transport_plan"),
        }

    async def get_negotiation_status(self, negotiation_id: str):
        if negotiation_id in self.active_negotiations:
            return self.active_negotiations[negotiation_id]

        row = await self.db_repo.get_negotiation_async(negotiation_id)
        if not row:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Negotiation not found")

        offers = await self.db_repo.get_offers_for_negotiation_async(negotiation_id)
        return {
            "negotiation_id": negotiation_id,
            "user_id": row.get("user_id"),
            "status": row.get("status", "UNKNOWN"),
            "summary": row.get("summary", ""),
            "farmer": row.get("farmer"),
            "crop": row.get("crop"),
            "quantity": row.get("quantity"),
            "agents_involved": row.get("agents_involved", []),
            "offers": offers,
            "next_action": row.get("next_action"),
            "final_price": row.get("final_price") or next((c.get("price") for c in self.db_repo.contracts.values() if c.get("negotiation_id") == negotiation_id), None),
            "market_offers": row.get("market_offers", []),
            "selected_buyer": row.get("selected_buyer"),
            "transport_plan": row.get("transport_plan"),
        }

    async def list_agents(self):
        return [
            {"role": "Farmer", "capability": "Sell produce"},
            {"role": "Buyer", "capability": "Purchase produce in bulk"},
            {"role": "Restaurant", "capability": "Procure premium fresh produce"},
            {"role": "Warehouse", "capability": "Store produce"},
            {"role": "Transporter", "capability": "Move goods"},
            {"role": "Processor", "capability": "Buy for processing"},
            {"role": "Compost", "capability": "Fallback spoilage channel"},
        ]




async def end_negotiation(payload: dict, db: AsyncSession = None):
    # Backward compatibility stub
    service_instance = NegotiationService(db)
    return await service_instance.end_negotiation(
        payload["negotiation_id"], payload["action"], payload.get("final_price")
    )

# Global singleton for startup tasks and tests
service = NegotiationService(None)


async def start_negotiation(payload: dict, scenario: str = "direct-sale", db=None):
    return await NegotiationService(db).start_negotiation(payload, scenario=scenario)


async def get_negotiation_status(negotiation_id: str, db=None):
    return await NegotiationService(db).get_negotiation_status(negotiation_id)


async def list_agents(db=None):
    return await NegotiationService(db).list_agents()


async def list_farmers(db=None):
    return list(Database(db).farmers.values())


async def list_negotiations(db=None):
    negs = list(Database(db).negotiations.values())
    negs.reverse()
    return negs[:50]


async def list_buyers(db=None):
    service = NegotiationService(db)
    await service.ensure_default_buyers()
    return await Database(db).list_buyers_async()


async def list_buyer_offers(user_id: str | None = None, db=None):
    offers = [row for row in await Database.list_buyers_async() if row.get("kind") == "offer"]
    if user_id:
        offers = [row for row in offers if row.get("user_id") == user_id]
    offers.sort(key=lambda row: row.get("created_at", ""), reverse=True)
    return offers


async def create_buyer_offer(payload: dict, db=None):
    price = float(payload.get("max_price", 0))
    record = {
        "id": Database(db).generate_id("buyer_offer"),
        "kind": "offer",
        "user_id": payload.get("user_id"),
        "buyer_name": payload.get("buyer_name", "Buyer"),
        "name": payload.get("buyer_name", "Buyer"),
        "crop": payload["crop"],
        "min_price": float(payload.get("min_price", 0)),
        "max_price": price,
        "offered_price": price,
        "quantity": float(payload["quantity"]),
        "max_quantity": float(payload["quantity"]),
        "target_price": price,
        "budget": price * float(payload["quantity"]),
        "location": payload.get("location", "Unknown"),
        "strategy": payload.get("strategy", "Direct procurement offer"),
        "status": "VIABLE",
        "created_at": "2026-04-06T12:00:00Z"
    }
    await Database(db).upsert_buyer_async(record)
    return record


async def list_produce(db=None):
    service = NegotiationService(db)
    await service.ensure_default_farmers_and_produce()
    return await Database(db).list_produce_async()



service = NegotiationService(None)
