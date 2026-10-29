from sqlalchemy.ext.asyncio import AsyncSession
from backend.repositories.user_repository import UserRepository
import logging
import asyncio
import uuid
from datetime import datetime, timezone

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
logger = logging.getLogger("backend.services.negotiation_service")

# ─────────────────────────────────────────────────────────────────────────────
# Statutory Benchmarks (MSP / FRP) for 7 Canonical Maharashtra Crops
# ─────────────────────────────────────────────────────────────────────────────
STATUTORY_BENCHMARKS = {
    "Sugarcane": {"mechanism": "FRP", "benchmark": 3.40, "modal_range": (3.20, 4.20)},
    "Soybean": {"mechanism": "MSP", "benchmark": 48.92, "modal_range": (42.00, 55.00)},
    "Cotton": {"mechanism": "MSP", "benchmark": 71.21, "modal_range": (68.00, 78.00)},
    "Jowar": {"mechanism": "MSP", "benchmark": 33.71, "modal_range": (29.00, 38.00)},
    "Onion": {"mechanism": "MANDI_MODAL", "benchmark": 25.00, "modal_range": (15.00, 26.00)},
    "Bajra": {"mechanism": "MSP", "benchmark": 26.25, "modal_range": (23.00, 30.00)},
    "Rice": {"mechanism": "MSP", "benchmark": 23.00, "modal_range": (22.00, 36.00)},
}

# 5 Verified Maharashtra APMC Mandi / Co-operative Suppliers per crop
MAHARASHTRA_CROP_SUPPLIERS = {
    "Onion": [
        {"name": "Lasalgaon Kanda Apex FPO", "loc": "Nashik, Maharashtra", "dist": 105, "match": 97, "special": "APMC Red Onion Direct"},
        {"name": "Pimpalgaon Baswant Onion Farmers Co-op", "loc": "Nashik, Maharashtra", "dist": 120, "match": 95, "special": "Sorted Mesh Lots"},
        {"name": "Dindori Red Onion Consortium", "loc": "Nashik, Maharashtra", "dist": 135, "match": 93, "special": "Cleaned Lot Standard"},
        {"name": "Junnar Agri Producer Company", "loc": "Pune, Maharashtra", "dist": 65, "match": 91, "special": "Rapid Dispatch"},
        {"name": "Ahmednagar Kanda & Agro Producers Union", "loc": "Ahmednagar, Maharashtra", "dist": 160, "match": 89, "special": "Bulk Warehouse Lot"},
    ],
    "Soybean": [
        {"name": "Latur Solvent & Oilseeds Farmers FPO", "loc": "Latur, Maharashtra", "dist": 220, "match": 96, "special": "18.5% Oil Content"},
        {"name": "Nanded Krishi Vikas Agro Consortium", "loc": "Nanded, Maharashtra", "dist": 280, "match": 94, "special": "Moisture < 10%"},
        {"name": "Barshi Soybean Producers Union", "loc": "Solapur, Maharashtra", "dist": 180, "match": 93, "special": "Certified Commercial Lot"},
        {"name": "Hingoli Green Oilseeds Cluster", "loc": "Hingoli, Maharashtra", "dist": 310, "match": 90, "special": "Bulk Hopper Delivery"},
        {"name": "Amravati Krishi Sahakari Sanstha", "loc": "Amravati, Maharashtra", "dist": 390, "match": 88, "special": "Solvent Grade Lot"},
    ],
    "Cotton": [
        {"name": "Vidarbha White Gold Farmers Producer Co.", "loc": "Wardha, Maharashtra", "dist": 310, "match": 97, "special": "29mm Staple Length"},
        {"name": "Akola Cotton Growers Association", "loc": "Akola, Maharashtra", "dist": 280, "match": 95, "special": "Micronaire 4.0"},
        {"name": "Yavatmal Kapas Utpadak Sahakari Sangh", "loc": "Yavatmal, Maharashtra", "dist": 340, "match": 93, "special": "Moisture < 8%"},
        {"name": "Jalgaon Cotton Ginning Farmer Pool", "loc": "Jalgaon, Maharashtra", "dist": 240, "match": 91, "special": "Direct Ginning Pass"},
        {"name": "Chhatrapati Sambhajinagar Agri Consortium", "loc": "Aurangabad, Maharashtra", "dist": 195, "match": 89, "special": "Clean Lint Baleable"},
    ],
    "Sugarcane": [
        {"name": "Kolhapur Panchganga Cane Growers Co-op", "loc": "Kolhapur, Maharashtra", "dist": 210, "match": 97, "special": "High Sucrose 12.5% Brix"},
        {"name": "Sangli Krishna Valley Sugar Belt FPO", "loc": "Sangli, Maharashtra", "dist": 190, "match": 95, "special": "Fresh Harvest Lot"},
        {"name": "Baramati Cane Producers Society", "loc": "Pune, Maharashtra", "dist": 75, "match": 93, "special": "Express Gate Transit"},
        {"name": "Satara Cane & Bio-Agro Producers Group", "loc": "Satara, Maharashtra", "dist": 115, "match": 90, "special": "FRP Direct Compliant"},
        {"name": "Ahmednagar Sugar Cane Cooperative", "loc": "Ahmednagar, Maharashtra", "dist": 150, "match": 88, "special": "Bulk Crusher Ready"},
    ],
    "Rice": [
        {"name": "Indrayani Fragrant Rice Producers FPO", "loc": "Maval, Pune, Maharashtra", "dist": 45, "match": 97, "special": "Indrayani Aromatic Grade"},
        {"name": "Gondia Paddy Farmers Cooperative", "loc": "Gondia, Maharashtra", "dist": 480, "match": 94, "special": "Long Grain Paddy"},
        {"name": "Bhandara Kolam Rice Producer Group", "loc": "Bhandara, Maharashtra", "dist": 450, "match": 92, "special": "Milling Ready <12% Moist"},
        {"name": "Raigad Wada Kolam Farmers Union", "loc": "Raigad, Maharashtra", "dist": 110, "match": 90, "special": "GI Tagged Wada Kolam"},
        {"name": "Kolhapur Basmati & Brown Rice Cluster", "loc": "Kolhapur, Maharashtra", "dist": 225, "match": 88, "special": "Premium Head Rice"},
    ],
    "Jowar": [
        {"name": "Solapur Maldandi Jowar Growers Society", "loc": "Solapur, Maharashtra", "dist": 205, "match": 97, "special": "Maldandi M-35-1 Pure"},
        {"name": "Dharashiv Millets & Sorghum Producer Co.", "loc": "Osmanabad, Maharashtra", "dist": 240, "match": 95, "special": "Nutri-Cereal Certified"},
        {"name": "Ahmednagar Dryland Jowar Collective", "loc": "Ahmednagar, Maharashtra", "dist": 140, "match": 92, "special": "Machine Cleaned White"},
        {"name": "Beed Marathwada Agri Farmers Union", "loc": "Beed, Maharashtra", "dist": 220, "match": 90, "special": "Sun-Dried Commercial"},
        {"name": "Sangli Nutri-Cereal FPO", "loc": "Sangli, Maharashtra", "dist": 195, "match": 88, "special": "Flour Milling Lot"},
    ],
    "Bajra": [
        {"name": "Dhule Pearl Millet Farmers Federation", "loc": "Dhule, Maharashtra", "dist": 260, "match": 96, "special": "ICTP-8203 Bold Grain"},
        {"name": "Nashik Nutri-Cereal Consortium", "loc": "Malegaon, Nashik, Maharashtra", "dist": 160, "match": 94, "special": "Graded Uniform Kernel"},
        {"name": "Sangamner Bajra Utpadak Sangh", "loc": "Ahmednagar, Maharashtra", "dist": 130, "match": 92, "special": "Cleaned Seed Grade"},
        {"name": "Jalgaon Bajra Producer Company", "loc": "Jalgaon, Maharashtra", "dist": 230, "match": 90, "special": "Low Moisture < 11%"},
        {"name": "Solapur Bajra & Millets Cooperative", "loc": "Solapur, Maharashtra", "dist": 210, "match": 88, "special": "Direct Mandi Inflow"},
    ],
}


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
    def __init__(self, db=None):
        self.db = db
        try:
            self.db_repo = Database(db)
        except TypeError:
            self.db_repo = Database
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
        farmer = FarmerAgent()
        
        if payload.get("buyer_mode"):
            ask = float(payload["min_price"])
            floor = float(payload.get("farmer_floor") or round(ask * 0.75, 2))
            farmer.name = payload.get("farmer_name", "FarmerAgent")
            farmer.crop = payload["crop"]
            farmer.quantity = float(payload["quantity"])
            farmer.min_price = floor
            farmer.initial_price = ask
            farmer.shelf_life = int(payload.get("shelf_life", 3))
            farmer.location = payload.get("location")
            return farmer
            
        farmer.name = payload.get("farmer_name", "FarmerAgent")
        farmer.crop = payload["crop"]
        farmer.quantity = float(payload["quantity"])
        farmer.min_price = float(payload["min_price"])
        farmer.shelf_life = int(payload.get("shelf_life", 3))
        farmer.location = payload.get("location")
        return farmer

    async def _build_buyer(self, buyer_profile: dict):
        strategy = str(buyer_profile.get("strategy") or "").lower()
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
        # 1. Query the 8-Factor NRV Matching Engine first for real live buyer requirements
        from backend.services.matching_service import match_listing_to_buyers
        try:
            matched_offers = await match_listing_to_buyers(payload)
            if matched_offers and len(matched_offers) > 0:
                return matched_offers[:5]
        except Exception as e:
            logger.warning(f"Error querying matching engine for market offers: {e}")

        await self.ensure_default_buyers()

        quantity = max(float(payload["quantity"]), 1)
        min_price = float(payload["min_price"])
        market_price = float(payload.get("market_price", min_price + 1))
        location = payload.get("location", "Unknown")

        # ── Fetch Farmer Strategic Context ───────────────────
        user_id = payload.get("user_id")
        user = await UserRepository.get_by_id(user_id) or {}
        # Preferences stored during Phase A onboarding
        farmer_prefs = user.get("preferences", {})
        buyer_pref = str(farmer_prefs.get("buyer_preference", "any")).lower()

        crop = payload.get("crop", "")
        db_buyers = await self.db_repo.list_buyers_async()
        from backend.services.matching_service import crops_match

        # Filter to real buyers from DB that match this crop (or general commodity buyers)
        matching_db_buyers = [
            b for b in db_buyers
            if not b.get("crop") or b.get("crop") in ("ALL", "*", "any") or crops_match(b.get("crop"), crop)
        ]

        buyer_profiles = [
            {
                "id": b.get("id"),
                "name": b.get("buyer_name") or b.get("name") or "Unknown Buyer",
                "budget": float((b.get("max_price") or b.get("target_price") or min_price * 1.2) * quantity * 1.2),
                "max_quantity": float(b.get("quantity") or quantity),
                "target_price": float(b.get("max_price") or b.get("target_price") or min_price * 1.2),
                "location": b.get("location", "Market"),
                "strategy": b.get("strategy", "standard"),
                "crop": b.get("crop"),
                "verified": bool(b.get("verified", True))
            }
            for b in matching_db_buyers
        ]

        if not buyer_profiles:
            # Check requirements table for requirements matching this crop
            from backend.services.matching_service import match_listing_to_buyers
            real_matches = await match_listing_to_buyers(payload)
            if real_matches:
                return real_matches
            # Truly NO buyers matching this crop exist in the database! Return empty list
            return []

        offers = []
        for profile in buyer_profiles:
            strategy = str(profile.get("strategy") or "").lower()
            if profile.get("kind") == "offer":
                continue

            offered_qty = min(quantity, float(profile.get("max_quantity", quantity)))
            if offered_qty <= 0:
                continue

            budget_limited_price = float(profile.get("budget", 0)) / max(offered_qty, 1)
            target_p = float(profile.get("target_price", min_price))

            if "restaurant" in strategy or "premium" in strategy:
                opening_bid = min(target_p * 0.95, budget_limited_price)
            else:
                base_offer = max(target_p * 0.92, min_price if target_p >= min_price else target_p * 0.88)
                opening_bid = min(target_p, budget_limited_price, max(base_offer, 1.0))

            offer_price = round(max(1.0, opening_bid), 2)
            distance_penalty = 0 if profile.get("location") == location else 0.2

            # User Preference Boost (Stakeholder Requirement C4)
            pref_boost = 15.0 if (buyer_pref in strategy and buyer_pref != "any") else 0.0

            # Verification Integrity Boost
            is_verified = bool(profile.get("verified", False))
            verification_weight = 20.0 if is_verified else -10.0

            is_viable = offer_price >= min_price

            # Real match score
            score = round(min(98.0, max(75.0, 95.0 - (distance_penalty * 20.0) + (pref_boost / 3.0))), 1)

            label = "Market Option"
            if is_viable:
                if score > 90: label = "👑 Best Profit"
                elif distance_penalty == 0: label = "⚡ Fast Handshake"
                elif "restaurant" in strategy: label = "💎 Premium Match"
                elif pref_boost > 0: label = "🎯 Strategic Fit"

            offers.append(
                {
                    "buyer_id": profile.get("id") or profile.get("buyer_id") or "unknown",
                    "buyer_name": profile.get("name") or "Unknown Buyer",
                    "location": profile.get("location", "Market"),
                    "strategy": label,
                    "offered_price": offer_price,
                    "offered_quantity": round(offered_qty, 2),
                    "budget": float(profile.get("budget", 0)),
                    "target_price": target_p,
                    "status": "VIABLE" if is_viable else "BELOW_MIN_PRICE",
                    "score": score,
                }
            )

        offers.sort(key=lambda item: (item["status"] == "VIABLE", item["score"], item["offered_price"]), reverse=True)
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
            target = float(payload.get("buyer_target_price") or (float(payload.get("min_price", 18)) + 1))
            quantity = float(payload.get("buyer_max_quantity") or payload.get("quantity", 0))
            budget = float(payload.get("buyer_budget") or (max(quantity, 1.0) * max(target, 1.0) * 1.2))
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
            max_rounds=int(payload.get("max_rounds", 3)),
            live_event_callback=live_event_callback,
        )

        farmer_name_val = payload.get("farmer_name")
        if not farmer_name_val or farmer_name_val in ["Unknown Farmer", "FarmerAgent"]:
            if payload.get("buyer_mode"):
                farmer_name_val = "Maharashtra Farmer Network"
            else:
                farmer_name_val = "Unknown Farmer"

        farmer_row = await self.db_repo.upsert_farmer_async(
            {
                "name": farmer_name_val,
                "location": payload.get("location", "Unknown"),
                "language": payload.get("language", "English")
            }
        )
        incoming_listing_id = payload.get("listing_id")
        produce_row = None
        if incoming_listing_id:
            produce_row = await self.db_repo.get_produce_async(incoming_listing_id)
            if produce_row:
                produce_row["status"] = "NEGOTIATING"
                await self.db_repo.upsert_produce_async(produce_row)

        if not produce_row:
            produce_row = await self.db_repo.upsert_produce_async(
                {
                    "farmer_name": farmer_row["name"],
                    "crop": payload["crop"],
                    "quantity": float(payload["quantity"]),
                    "min_price": float(payload["min_price"]),
                    "shelf_life": payload.get("shelf_life", 3),
                    "quality": payload.get("quality", "A"),
                    "location": payload.get("location", "Unknown"),
                    "language": payload.get("language", "English"),
                    "status": "NEGOTIATING"
                }
            )

        negotiation_id = pre_id or self.db_repo.generate_id("neg")
        initial_price = float(payload.get("buyer_target_price") or payload.get("min_price", 18))
        if payload.get("buyer_mode"):
            buyer_display_name = payload.get("buyer_name") or "Buyer Enterprise"
            farmer_display_name = farmer_name_val
        else:
            buyer_display_name = (selected_offer.get("buyer_name") if selected_offer else None) or payload.get("buyer_name") or "Buyer Agent"
            farmer_display_name = farmer_row["name"]

        if not buyer_display_name.strip():
            buyer_display_name = "Buyer Agent"

        min_p = float(payload.get("min_price", 18.0))
        mkt_p = float(payload.get("market_price", min_p + 2.0))
        tgt_p = float(payload.get("buyer_target_price") or payload.get("target_price", initial_price))

        negotiation_payload = {
            "id": negotiation_id,
            "negotiation_id": negotiation_id,
            "requirement_id": payload.get("requirement_id"),
            "listing_id": incoming_listing_id or produce_row.get("id"),
            "user_id": payload.get("user_id"),
            "status": "ACTIVE",
            "summary": f"Negotiating {payload['quantity']}kg {payload['crop']} between {farmer_display_name} and {buyer_display_name}.",
            "scenario": scenario,
            "produce_id": produce_row["id"],
            "farmer_id": farmer_row["id"],
            "farmer": farmer_display_name,
            "farmer_name": farmer_display_name,
            "buyer": buyer_display_name,
            "buyer_name": buyer_display_name,
            "crop": payload["crop"],
            "quantity": float(payload["quantity"]),
            "min_price": min_p,
            "market_price": mkt_p,
            "target_price": tgt_p,
            "final_price": None,
            "agents_involved": [farmer_display_name, buyer_display_name],
            "next_action": "Autonomous multi-round negotiation active",
            "market_offers": market_offers,
            "active_buyers": market_offers[:3],
            "selected_buyer": selected_offer,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "transport_plan": None,
            "workflow_mode": payload.get("workflow_mode", "FULL_SUPPLY_CHAIN"),
            "selected_services": payload.get("selected_services") or {},
            "district": payload.get("district"),
            "location": payload.get("location") or payload.get("buyer_location"),
            "buyer_location": payload.get("buyer_location") or payload.get("location"),
            "permitted_agents": payload.get("permitted_agents", ["buyer_agent", "dynamic_routing_agent"]),
            "has_transport": bool(payload.get("has_transport", False)),
            "has_storage": bool(payload.get("has_storage", False)),
            "requires_processing": bool(payload.get("requires_processing", False)),
            "sell_hold_decision": payload.get("sell_hold_decision"),
        }
        initial_offers = [
            {
                "round": 1,
                "agent": buyer_display_name,
                "price": initial_price,
                "decision": "OFFER",
                "quantity": float(payload.get("quantity", 500)),
                "message": f"Opening procurement offer: ₹{initial_price}/kg for {payload['quantity']}kg"
            }
        ]
        negotiation_payload["offers"] = initial_offers
        await self.db_repo.create_negotiation_async(negotiation_payload)
        self.active_negotiations[negotiation_id] = negotiation_payload

        # Initial opening offer
        await self.db_repo.append_offer_async(
            negotiation_id,
            initial_offers[0]
        )

        # Check if distributed worker execution is active or requested
        use_worker = bool(payload.get("use_worker") or payload.get("dispatch_mode") == "worker")
        active_worker_detected = False
        stream_job_id = None

        try:
            from backend.core.redis import redis_manager
            if redis_manager.client:
                active_worker_detected = await redis_manager.has_active_stream_workers()
                stream_job_id = await redis_manager.enqueue_negotiation_job(negotiation_id, payload)
                if stream_job_id:
                    negotiation_payload["stream_job_id"] = stream_job_id
                    negotiation_payload["dispatched_to_stream"] = True
                    await self.db_repo.update_negotiation_async(negotiation_id, {"stream_job_id": stream_job_id})
        except Exception as e:
            logger.warning(f"Redis stream dispatch note for {negotiation_id}: {e}")

        # If sync=True is requested, await completion (used for CLI scripts / unit tests)
        if payload.get("sync") is True:
            return await self._run_negotiation_workflow(
                negotiation_id, manager, transporter, payload, scenario, farmer_row, produce_row, selected_offer, market_offers, farmer, live_event_callback
            )

        # Execution routing:
        # If an active worker is detected or use_worker was requested and job was enqueued,
        # let agent_worker.py process the job.
        # Otherwise, run in-process background task via asyncio.create_task.
        if (active_worker_detected or use_worker) and stream_job_id:
            logger.info(f"⚡ Negotiation {negotiation_id} assigned to distributed agent_worker via stream job {stream_job_id}.")
        else:
            asyncio.create_task(self._run_negotiation_workflow(
                negotiation_id, manager, transporter, payload, scenario, farmer_row, produce_row, selected_offer, market_offers, farmer, live_event_callback
            ))

        return {
            "negotiation_id": negotiation_id,
            "status": "ACTIVE",
            "offers": [
                {
                    "round": 1,
                    "agent": buyer_display_name,
                    "price": initial_price,
                    "decision": "OFFER"
                }
            ],
            "summary": negotiation_payload["summary"],
            "crop": payload["crop"],
            "quantity": float(payload["quantity"]),
            "farmer": farmer_row["name"],
            "stream_job_id": stream_job_id,
            "dispatched_to_stream": bool(stream_job_id),
            "execution_mode": "worker" if ((active_worker_detected or use_worker) and stream_job_id) else "in_process"
        }

    async def _run_negotiation_workflow(
        self, negotiation_id, manager, transporter, payload, scenario, farmer_row, produce_row, selected_offer, market_offers, farmer, live_event_callback
    ):
        try:
            result = await manager.start_negotiation(
                market_price=float(payload.get("market_price", payload["min_price"] + 1)),
                scenario=scenario,
                stakeholder_role=payload.get("stakeholder_role", "FARMER"),
                workflow_mode=payload.get("workflow_mode", "FULL_SUPPLY_CHAIN")
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

            buyer_loc = selected_offer.get("location", "Market") if selected_offer else "Market"
            qty_val = float(payload.get("quantity", 2500))
            norm_crop = payload.get("crop", "Produce")
            is_reefer = norm_crop.lower() in {"tomato", "strawberry", "grape", "banana", "mango"} or "onion" in norm_crop.lower()

            try:
                from backend.services.vehicle_service import filter_suitable_vehicles
                from backend.services.routing_service import calculate_transport_route
                from backend.services.transport_cost_service import calculate_transportation_cost
                
                route_res = calculate_transport_route(farmer.location, buyer_loc)
                dist = float(route_res.get("distance_km", 250.0))
                dur_h = float(route_res.get("estimated_duration_hours", 4.0))
                
                veh_filter = await filter_suitable_vehicles(
                    quantity_kg=qty_val,
                    refrigerated_required=is_reefer
                )
                best_v = veh_filter.get("best_vehicle")
                if not best_v and veh_filter.get("candidates"):
                    best_v = veh_filter["candidates"][0]
                
                if best_v:
                    cost_res = await calculate_transportation_cost(
                        vehicle=best_v,
                        distance_km=dist,
                        estimated_duration_hours=dur_h,
                        deadhead_km=float(route_res.get("deadhead_km", 0.0)),
                        is_perishable=is_reefer
                    )
                    cost = round(float(cost_res.get("agreed_price") or cost_res.get("minimum_acceptable_price") or cost_res.get("initial_quote") or (dist * 28.0)))
                    transport_plan = {
                        "agent": best_v["vehicle_name"],
                        "vehicle_name": best_v["vehicle_name"],
                        "vehicle_type": best_v["vehicle_type"],
                        "vehicle_id": best_v.get("vehicle_id"),
                        "cost": cost,
                        "agreed_freight": cost,
                        "distance": dist,
                        "distance_km": dist,
                        "estimated_duration_hours": dur_h,
                        "capacity": best_v["capacity_kg"],
                        "capacity_kg": best_v["capacity_kg"],
                        "fuel_type": best_v.get("fuel_type", "Diesel"),
                        "refrigerated": best_v.get("refrigerated", False),
                        "cost_breakdown": cost_res.get("cost_breakdown", {}),
                        "origin": farmer.location,
                        "destination": buyer_loc,
                        "routing_source": route_res.get("routing_source", "OSRM Live Routing Engine")
                    }
                else:
                    transport_plan = {
                        "status": "INFEASIBLE",
                        "message": f"No vehicle available matching {qty_val:,.0f}kg payload capacity.",
                        "rejected_vehicles": veh_filter.get("rejected_vehicles", []),
                        "origin": farmer.location,
                        "destination": buyer_loc
                    }
            except Exception as tp_err:
                from backend.services.matching_service import get_distance_km_sync
                dist = get_distance_km_sync(farmer.location, buyer_loc) or 250.0
                rate = 32.0 if is_reefer else 24.0
                cost = round(dist * rate)
                transport_plan = {
                    "agent": "Assigned Carrier",
                    "vehicle_name": "Agro Haulage Carrier",
                    "vehicle_type": "Medium Commercial Truck",
                    "cost": cost,
                    "agreed_freight": cost,
                    "distance": dist,
                    "distance_km": dist,
                    "capacity": max(qty_val, 5000),
                    "origin": farmer.location,
                    "destination": buyer_loc,
                }

            for idx, event in enumerate(manager.memory.get_offers(), start=2):
                offer = event["offer"]
                agent_name = event["agent"]
                if event["agent"] == "Buyer" and selected_offer:
                    agent_name = selected_offer["buyer_name"]
                elif event["agent"] == "Farmer":
                    agent_name = farmer_row["name"]

                await self.db_repo.append_offer_async(
                    negotiation_id,
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
                    "negotiation_id": negotiation_id,
                    "scenario": scenario,
                    "price": result["deal"].get("price", 0),
                    "quantity": result["deal"].get("quantity", 0),
                    "state": result["state"],
                    "farmer_id": farmer_row["name"],
                    "peer_node": selected_offer.get("buyer_name", "Wholesale Buyer") if selected_offer else "Wholesale Buyer",
                    "crop": payload["crop"]
                }
                await self.db_repo.create_contract_async(contract_data)
                hub.record_signed_deal(contract_data)

            # Update negotiation record with final result
            buyer_display_name = (selected_offer.get("buyer_name") if selected_offer else None) or payload.get("buyer_name") or "Buyer Agent"
            min_p = float(payload.get("min_price", 18.0))
            mkt_p = float(payload.get("market_price", min_p + 2.0))
            tgt_p = float(payload.get("buyer_target_price") or payload.get("target_price", min_p))

            updated_payload = {
                "id": negotiation_id,
                "negotiation_id": negotiation_id,
                "user_id": payload.get("user_id"),
                "status": result["state"],
                "summary": result["summary"],
                "scenario": scenario,
                "produce_id": produce_row["id"],
                "farmer_id": farmer_row["id"],
                "farmer": farmer_row["name"],
                "farmer_name": farmer_row["name"],
                "buyer": buyer_display_name,
                "buyer_name": buyer_display_name,
                "crop": payload["crop"],
                "quantity": float(payload["quantity"]),
                "min_price": min_p,
                "market_price": mkt_p,
                "target_price": tgt_p,
                "final_price": result["deal"].get("price") if result.get("deal") else None,
                "agents_involved": agents_involved,
                "next_action": result.get("next_action"),
                "market_offers": market_offers,
                "selected_buyer": selected_offer,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "transport_plan": transport_plan,
                "recommendation": result.get("recommendation"),
                "reflection": result.get("reflection"),
            }
            await self.db_repo.create_negotiation_async(updated_payload)

            status_payload = await self._build_status_payload(negotiation_id, manager, result)
            self.active_negotiations[negotiation_id] = status_payload

            # Persist to shared history so all users can see past negotiations
            await add_history("all", {
                "negotiation_id": negotiation_id,
                "user_id": payload.get("user_id"),
                "farmer": farmer_row["name"],
                "crop": payload["crop"],
                "quantity": float(payload["quantity"]),
                "status": result["state"],
                "final_price": result["deal"].get("price") if result.get("deal") else None,
                "summary": result["summary"],
                "selected_buyer": selected_offer.get("buyer_name") if selected_offer else None,
                "created_at": updated_payload.get("created_at", ""),
                "logs": manager.logs[:30],
            })

            # Broadcast via WebSocket
            try:
                from backend.websocket.agent_updates import agent_update_hub
                await agent_update_hub.broadcast({
                    "event": "NEGOTIATION_FINISHED",
                    "negotiation_id": negotiation_id,
                    "status": result["state"],
                    "final_price": result["deal"].get("price") if result.get("deal") else None,
                    "message": result.get("summary", "Negotiation completed."),
                    "recommendation": result.get("recommendation"),
                    "reflection": result.get("reflection"),
                })
            except Exception:
                pass

            if live_event_callback:
                live_event_callback({
                    "type": "scenario_ready",
                    "data": {
                        "negotiation_id": negotiation_id,
                        "farmer": farmer_row["name"],
                        "crop": payload["crop"],
                        "status": result["state"]
                    }
                })

            return status_payload
        except Exception as e:
            logger.error(f"Negotiation workflow error for {negotiation_id}: {e}", exc_info=True)
            await self.db_repo.create_negotiation_async({
                "negotiation_id": negotiation_id,
                "status": "FAILED",
                "summary": f"Negotiation execution encountered an issue: {str(e)}"
            })
            return {"negotiation_id": negotiation_id, "status": "FAILED", "summary": str(e)}

    async def _build_status_payload(self, negotiation_id: str, manager: NegotiationManager, result: dict):
        row = self.db_repo.negotiations.get(negotiation_id, {})
        offers = await self.db_repo.get_offers_for_negotiation_async(negotiation_id)
        selected_b = row.get("selected_buyer") or {}
        buyer_name = (selected_b.get("buyer_name") if isinstance(selected_b, dict) else None) or row.get("buyer") or row.get("buyer_name") or "Buyer Agent"
        farmer_name = row.get("farmer") or row.get("farmer_name") or "Farmer Agent"
        min_p = float(row.get("min_price") or 18.0)
        mkt_p = float(row.get("market_price") or (min_p + 2.0))
        tgt_p = float(row.get("target_price") or ((selected_b.get("target_price") or selected_b.get("offered_price")) if isinstance(selected_b, dict) else None) or min_p)

        return {
            "id": negotiation_id,
            "negotiation_id": negotiation_id,
            "status": result["state"],
            "summary": result["summary"],
            "final_price": result["deal"].get("price") if result.get("deal") else None,
            "farmer": farmer_name,
            "farmer_name": farmer_name,
            "buyer": buyer_name,
            "buyer_name": buyer_name,
            "crop": row.get("crop", "Tomato"),
            "quantity": float(row.get("quantity", 500)),
            "market_price": mkt_p,
            "min_price": min_p,
            "target_price": tgt_p,
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
            "recommendation": result.get("recommendation") or row.get("recommendation"),
            "reflection": result.get("reflection") or row.get("reflection"),
        }

    async def get_negotiation_status(self, negotiation_id: str):
        if not negotiation_id or negotiation_id in ("undefined", "null"):
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Invalid negotiation id")

        # 1. Check in memory active negotiations with exact id or alternate prefix
        target_id = negotiation_id
        if target_id in self.active_negotiations:
            res = dict(self.active_negotiations[target_id])
            offers = await self.db_repo.get_offers_for_negotiation_async(target_id)
            if offers:
                res["offers"] = offers
            db_row = await self.db_repo.get_negotiation_async(target_id)
            if db_row:
                for k in ("warehouse_plan", "processor_plan", "end_to_end_deal", "contract_hash", "transport_plan", "final_price", "status"):
                    if db_row.get(k) and not res.get(k):
                        res[k] = db_row[k]
            return res

        alt_id = f"neg_{negotiation_id}" if not negotiation_id.startswith("neg_") else negotiation_id[4:]
        if alt_id in self.active_negotiations:
            res = dict(self.active_negotiations[alt_id])
            offers = await self.db_repo.get_offers_for_negotiation_async(alt_id)
            if offers:
                res["offers"] = offers
            db_row = await self.db_repo.get_negotiation_async(alt_id)
            if db_row:
                for k in ("warehouse_plan", "processor_plan", "end_to_end_deal", "contract_hash", "transport_plan", "final_price", "status"):
                    if db_row.get(k) and not res.get(k):
                        res[k] = db_row[k]
            return res

        # 2. Check in database with exact id, then alternate prefix
        row = await self.db_repo.get_negotiation_async(target_id)
        if not row:
            row = await self.db_repo.get_negotiation_async(alt_id)
            if row:
                target_id = alt_id

        if not row:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Negotiation not found")

        negotiation_id = target_id
        offers = await self.db_repo.get_offers_for_negotiation_async(negotiation_id)
        selected_b = row.get("selected_buyer") or {}
        buyer_name = (selected_b.get("buyer_name") if isinstance(selected_b, dict) else None) or row.get("buyer") or row.get("buyer_name") or "Buyer Agent"
        farmer_name = row.get("farmer") or row.get("farmer_name") or "Farmer Agent"
        min_p = float(row.get("min_price") or 18.0)
        mkt_p = float(row.get("market_price") or (min_p + 2.0))
        tgt_p = float(row.get("target_price") or ((selected_b.get("target_price") or selected_b.get("offered_price")) if isinstance(selected_b, dict) else None) or min_p)

        # Baseline dictionary loaded from PostgreSQL
        res = {
            "id": negotiation_id,
            "negotiation_id": negotiation_id,
            "user_id": row.get("user_id"),
            "status": row.get("status", "UNKNOWN"),
            "summary": row.get("summary", ""),
            "farmer": farmer_name,
            "farmer_name": farmer_name,
            "buyer": buyer_name,
            "buyer_name": buyer_name,
            "crop": row.get("crop") or "Soybean",
            "quantity": float(row.get("quantity") or 500.0),
            "market_price": mkt_p,
            "min_price": min_p,
            "target_price": tgt_p,
            "agents_involved": row.get("agents_involved", []),
            "offers": offers or [],
            "next_action": row.get("next_action"),
            "final_price": row.get("final_price"),
            "market_offers": row.get("market_offers", []),
            "active_buyers": row.get("active_buyers", row.get("market_offers", [])[:3]),
            "selected_buyer": selected_b,
            "transport_plan": row.get("transport_plan"),
            "warehouse_plan": row.get("warehouse_plan"),
            "processor_plan": row.get("processor_plan"),
            "end_to_end_deal": row.get("end_to_end_deal"),
            "workflow_mode": row.get("workflow_mode") or (selected_b.get("workflow_mode") if isinstance(selected_b, dict) else None) or "FULL_SUPPLY_CHAIN",
            "permitted_agents": row.get("permitted_agents"),
            "selected_services": row.get("selected_services") or (selected_b.get("selected_services") if isinstance(selected_b, dict) else {}),
            "district": row.get("district") or (selected_b.get("district") if isinstance(selected_b, dict) else None),
            "location": row.get("location") or (selected_b.get("location") if isinstance(selected_b, dict) else None),
            "buyer_location": row.get("buyer_location") or (selected_b.get("buyer_location") if isinstance(selected_b, dict) else None) or row.get("location"),
            "parallel_branches": self.active_negotiations.get(negotiation_id, {}).get("parallel_branches") or row.get("market_offers") or [],
            "logs": row.get("logs", []),
            "contract_hash": row.get("contract_hash"),
        }

        # Merge active memory state if present without overwriting database truth
        if negotiation_id in self.active_negotiations:
            active = self.active_negotiations[negotiation_id]
            for k, v in active.items():
                if v is not None:
                    res[k] = v

        return res

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

    async def intervene_deal(self, negotiation_id: str, payload: dict):
        """
        Processes a human buyer's manual counter offer:
        1. Records the buyer counter-offer in DB and memory.
        2. Evaluates the offer against the Farmer Agent.
        3. Records the farmer's response (ACCEPT, REJECT, or COUNTER) in DB and memory.
        4. Broadcasts both offers over WebSockets.
        5. Updates negotiation status (DEAL, REJECT, or ACTIVE).
        """
        row = await self.db_repo.get_negotiation_async(negotiation_id)
        if not row:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Negotiation not found")

        offers = await self.db_repo.get_offers_for_negotiation_async(negotiation_id)
        current_round = max([o.get("round", 1) for o in offers], default=1)
        next_round = current_round + 1

        # Parse price from payload or extract from instruction/message
        raw_price = payload.get("price") if payload.get("price") is not None else payload.get("override_price")
        new_price = float(raw_price) if raw_price is not None and str(raw_price).strip() != "" else 0.0
        
        user_msg = (payload.get("message") or payload.get("instruction") or "").strip()
        if new_price <= 0 and user_msg:
            import re
            m = re.search(r"(?:₹|\b)(\d+(?:\.\d+)?)", user_msg)
            if m:
                try:
                    new_price = float(m.group(1))
                except (ValueError, TypeError):
                    pass

        if new_price <= 0:
            if offers:
                p_list = [float(o.get("price")) for o in reversed(offers) if o.get("price")]
                new_price = p_list[0] if p_list else float(row.get("price") or row.get("target_price") or 45.0)
            else:
                new_price = float(row.get("price") or row.get("target_price") or 45.0)

        qty = float(payload.get("quantity") or row.get("quantity") or 500)
        crop_val = (payload and payload.get("crop")) or (row and row.get("crop")) or "Tomato"
        crop = str(crop_val).strip() if crop_val else "Tomato"
        farmer_name = (row and (row.get("farmer") or row.get("farmer_name"))) or "Farmer Ramesh"
        buyer_name = (row and (row.get("buyer") or row.get("buyer_name"))) or "Buyer"

        # Statutory Benchmark & Buyer Reservation Guardrail
        crop_norm = crop
        for k in STATUTORY_BENCHMARKS:
            if k.lower() in crop.lower():
                crop_norm = k
                break
        bench_info = STATUTORY_BENCHMARKS.get(crop_norm, {"benchmark": 50.0})
        statutory_bench = float(bench_info.get("benchmark", 50.0))
        target_p = float(row.get("target_price") or row.get("price") or statutory_bench)
        # Price ceiling & floor thresholds
        max_buyer_ceiling = round(max(target_p * 1.35, statutory_bench * 1.40), 2)
        min_floor_price = round(statutory_bench * 0.35, 2)

        # Formulate descriptive message
        formatted_msg = user_msg if user_msg else f"Buyer counter offer: ₹{new_price}/kg for {qty:,.0f}kg"

        # 1. Record Buyer Counter Offer
        buyer_offer = {
            "round": next_round,
            "agent": f"{buyer_name} (You)",
            "price": new_price,
            "decision": "COUNTER",
            "quantity": qty,
            "message": formatted_msg
        }
        await self.db_repo.append_offer_async(negotiation_id, buyer_offer)

        # 🛡️ BUYER GUARDRAIL INTERCEPTION: Prevent accepting or finalizing deals above ceiling (e.g. ₹2000) or below floor
        if new_price > max_buyer_ceiling:
            guardrail_msg = (
                f"🛡️ [Buyer Guardrail] Offer ₹{new_price:,.2f}/kg rejected: Exceeds buyer reservation "
                f"ceiling (₹{max_buyer_ceiling:,.2f}/kg) and statutory MSP benchmark (₹{statutory_bench:,.2f}/kg for {crop_norm}). "
                f"Deals above ceiling are strictly blocked."
            )
            farmer_round = next_round + 1
            guardrail_offer = {
                "round": farmer_round,
                "agent": "Buyer Guardrail System",
                "price": max_buyer_ceiling,
                "decision": "REJECT",
                "quantity": qty,
                "message": guardrail_msg
            }
            await self.db_repo.append_offer_async(negotiation_id, guardrail_offer)
            await self.db_repo.update_negotiation_async(negotiation_id, {
                "status": "ACTIVE",
                "final_price": None,
                "current_round": farmer_round
            })
            try:
                from backend.websocket.agent_updates import agent_update_hub as ws_manager
                await ws_manager.broadcast({
                    "event": "NEGOTIATION_LOG",
                    "negotiation_id": negotiation_id,
                    "agent_type": "buyer",
                    "message": guardrail_msg,
                    "offer": max_buyer_ceiling,
                    "status": "ACTIVE"
                })
            except Exception:
                pass

            all_offers = await self.db_repo.get_offers_for_negotiation_async(negotiation_id)
            return {
                "status": "ACTIVE",
                "final_price": None,
                "decision": "REJECT",
                "buyer_offer": buyer_offer,
                "farmer_response": guardrail_offer,
                "offers": all_offers,
                "warning": guardrail_msg
            }

        if new_price < min_floor_price or new_price <= 0:
            guardrail_msg = (
                f"🛡️ [Buyer Guardrail] Offer ₹{new_price:,.2f}/kg rejected: Below statutory APMC floor "
                f"threshold (₹{min_floor_price:,.2f}/kg for {crop_norm}). "
                f"Absurd or predatory low pricing is strictly blocked."
            )
            farmer_round = next_round + 1
            guardrail_offer = {
                "round": farmer_round,
                "agent": "Buyer Guardrail System",
                "price": statutory_bench,
                "decision": "REJECT",
                "quantity": qty,
                "message": guardrail_msg
            }
            await self.db_repo.append_offer_async(negotiation_id, guardrail_offer)
            await self.db_repo.update_negotiation_async(negotiation_id, {
                "status": "ACTIVE",
                "final_price": None,
                "current_round": farmer_round
            })
            try:
                from backend.websocket.agent_updates import agent_update_hub as ws_manager
                await ws_manager.broadcast({
                    "event": "NEGOTIATION_LOG",
                    "negotiation_id": negotiation_id,
                    "agent_type": "buyer",
                    "message": guardrail_msg,
                    "offer": statutory_bench,
                    "status": "ACTIVE"
                })
            except Exception:
                pass

            all_offers = await self.db_repo.get_offers_for_negotiation_async(negotiation_id)
            return {
                "status": "ACTIVE",
                "final_price": None,
                "decision": "REJECT",
                "buyer_offer": buyer_offer,
                "farmer_response": guardrail_offer,
                "offers": all_offers,
                "warning": guardrail_msg
            }

        # 2. Instantiate FarmerAgent to evaluate the counter offer
        min_p = float(row.get("min_price") or 18.0)
        farmer_floor = float(row.get("farmer_floor") or min_p)
        farmer = FarmerAgent(
            name=farmer_name,
            crop=crop,
            quantity=qty,
            min_price=farmer_floor,
            initial_price=min_p,
            shelf_life=int(row.get("shelf_life", 4)),
            location=row.get("location")
        )

        market_p = float(row.get("market_price", min_p + 2.0))
        offer_payload = {"price": new_price, "quantity": qty}
        context_payload = {"market_price": market_p, "round": next_round}

        farmer_resp = farmer.respond_to_offer(offer_payload, context=context_payload, force_deterministic=True)
        decision_type = farmer_resp.get("type", "COUNTER")
        counter_price = farmer_resp.get("price", new_price)
        farmer_msg = farmer_resp.get("message", "")
        if not farmer_msg:
            if decision_type == "ACCEPT":
                farmer_msg = f"Deal Accepted! We agree to ₹{new_price}/kg for {qty:,.0f} kg of {crop}."
            elif decision_type == "REJECT":
                farmer_msg = f"We cannot accept ₹{new_price}/kg as it is below our reserve price of ₹{farmer_floor}/kg."
            else:
                farmer_msg = f"We counter at ₹{counter_price}/kg considering current mandi rates and quality."

        farmer_round = next_round + 1
        farmer_offer = {
            "round": farmer_round,
            "agent": farmer_name,
            "price": counter_price,
            "decision": decision_type,
            "quantity": qty,
            "message": farmer_msg
        }
        await self.db_repo.append_offer_async(negotiation_id, farmer_offer)

        new_status = "ACTIVE"
        final_price = None
        if decision_type == "ACCEPT" and new_price <= max_buyer_ceiling:
            new_status = "DEAL"
            final_price = new_price
            contract_data = {
                "negotiation_id": negotiation_id,
                "scenario": row.get("scenario", "direct-sale"),
                "price": final_price,
                "quantity": qty,
                "state": "DEAL",
                "farmer_id": farmer_name,
                "peer_node": buyer_name,
                "crop": crop
            }
            await self.db_repo.create_contract_async(contract_data)
            hub.record_signed_deal(contract_data)
        elif decision_type == "REJECT":
            new_status = "REJECT"

        update_payload = {
            "status": new_status,
            "final_price": final_price,
            "current_round": farmer_round
        }
        await self.db_repo.update_negotiation_async(negotiation_id, update_payload)

        try:
            from backend.websocket.agent_updates import agent_update_hub as ws_manager
            await ws_manager.broadcast({
                "event": "NEGOTIATION_LOG",
                "negotiation_id": negotiation_id,
                "agent_type": "buyer",
                "message": buyer_offer["message"],
                "offer": new_price
            })
            await ws_manager.broadcast({
                "event": "NEGOTIATION_LOG",
                "negotiation_id": negotiation_id,
                "agent_type": "farmer",
                "message": farmer_offer["message"],
                "offer": counter_price,
                "status": new_status
            })
            if new_status == "DEAL":
                await ws_manager.broadcast({
                    "event": "NEGOTIATION_FINISHED",
                    "negotiation_id": negotiation_id,
                    "status": "DEAL",
                    "final_price": final_price
                })
        except Exception as ws_err:
            logger.warning(f"WebSocket broadcast error: {ws_err}")

        all_offers = await self.db_repo.get_offers_for_negotiation_async(negotiation_id)
        return {
            "status": new_status,
            "final_price": final_price,
            "decision": decision_type,
            "buyer_offer": buyer_offer,
            "farmer_response": farmer_offer,
            "offers": all_offers
        }

    async def get_parallel_branches(self, negotiation_id: str):
        if not negotiation_id.startswith("neg_"):
            negotiation_id = f"neg_{negotiation_id}"
        # 1. From active in-memory state
        if negotiation_id in self.active_negotiations:
            branches = self.active_negotiations[negotiation_id].get("parallel_branches")
            if branches and isinstance(branches, list) and len(branches) > 0 and "chat_messages" in branches[0]:
                return branches[:5]
        # 2. From database market_offers
        try:
            row = await self.db_repo.get_negotiation_async(negotiation_id)
            if row and row.get("market_offers"):
                offers = row.get("market_offers")
                if offers and isinstance(offers, list) and len(offers) > 0 and "chat_messages" in offers[0]:
                    return offers[:5]
        except Exception:
            pass
        # 3. Dynamic run if not already present
        res = await self.run_parallel_procurement(negotiation_id)
        return (res.get("suppliers", []))[:5]

    async def run_parallel_procurement(self, negotiation_id: str, payload: dict = None):
        """
        Executes Autonomous Parallel Buying across top candidate Maharashtra suppliers:
        1. Invokes BuyerOrchestrationService to run isolated concurrent multi-round negotiations.
        2. Applies strict reservation ceiling, budget, and quantity validations.
        3. Ranks valid executable deals by true landed cost (Base + Distance Freight + APMC Cess).
        4. Enforces no-forced-winner policy: returns status="NO_EXECUTABLE_DEAL" if no deal qualifies.
        5. Updates negotiation record and broadcasts real-time results.
        """
        row = await self.db_repo.get_negotiation_async(negotiation_id)
        if not row:
            row = Database.negotiations.get(negotiation_id)
            if not row:
                auto_crop = (payload and payload.get("crop")) or "Soybean"
                auto_qty = float((payload and payload.get("quantity")) or 500)
                auto_target = float((payload and payload.get("target_price")) or 48.0)
                auto_loc = (payload and payload.get("location")) or "Maharashtra"
                row = {
                    "id": negotiation_id,
                    "negotiation_id": negotiation_id,
                    "crop": auto_crop,
                    "quantity": auto_qty,
                    "target_price": auto_target,
                    "min_price": round(auto_target * 0.9, 2),
                    "max_price": round(auto_target * 1.2, 2),
                    "price": auto_target,
                    "location": auto_loc,
                    "buyer": (payload and payload.get("buyer_name")) or "Buyer Agent",
                    "farmer": "Regional APMC Producer",
                    "status": "ACTIVE",
                    "current_round": 1,
                    "offers": [],
                    "workflow_mode": (payload and payload.get("workflow_mode")) or "FULL_SUPPLY_CHAIN"
                }
                Database.negotiations[negotiation_id] = row
                try:
                    await self.db_repo.upsert_negotiation_async(row)
                except Exception:
                    pass

        crop_val = (payload and payload.get("crop")) or (row and row.get("crop")) or "Soybean"
        crop = str(crop_val).strip() if crop_val else "Soybean"
        crop_norm = "Soybean"
        for k in STATUTORY_BENCHMARKS:
            if k.lower() in crop.lower():
                crop_norm = k
                break

        bench_info = STATUTORY_BENCHMARKS.get(crop_norm, {"benchmark": 48.92})
        statutory_bench = float(bench_info.get("benchmark", 48.92))
        qty = float((payload and payload.get("quantity")) or (row and row.get("quantity")) or 500)
        target_p = float((payload and payload.get("target_price")) or (row and (row.get("target_price") or row.get("price"))) or statutory_bench)
        reservation_p = float((payload and (payload.get("max_price") or payload.get("reservation_price"))) or (row and row.get("max_price")) or round(target_p * 1.20, 2))
        budget = float((payload and payload.get("budget")) or (row and row.get("budget")) or (qty * reservation_p))

        requirement_dict = {
            "crop": crop_norm,
            "quantity": qty,
            "target_price": target_p,
            "max_price": reservation_p,
            "reservation_price": reservation_p,
            "budget": budget,
            "location": (row and row.get("location")) or "Maharashtra",
            "buyer_name": (row and (row.get("buyer") or row.get("buyer_name"))) or "Buyer Agent",
            "persona": (payload and payload.get("persona")) or "bulk_wholesaler",
            "strategy": (payload and payload.get("strategy")) or "balanced",
            "sellers": payload.get("sellers") if payload else None,
        }

        # Determine workflow mode and permitted agents
        workflow_mode_raw = (payload and payload.get("workflow_mode")) or (row and row.get("workflow_mode")) or "FULL_SUPPLY_CHAIN"
        if str(workflow_mode_raw).upper() in ("BUYER_ONLY", "SINGLE", "SINGLE_AGENT"):
            workflow_mode = "SINGLE_AGENT"
            permitted_agents = ["BUYER"]
            need_transport = False
            need_storage = False
            allow_processing = False
        else:
            workflow_mode = "FULL_SUPPLY_CHAIN"
            permitted_agents = (payload and payload.get("permitted_agents")) or (row and row.get("permitted_agents")) or [
                "BUYER", "TRANSPORT", "WAREHOUSE", "PROCESSOR"
            ]
            permitted_agents = [str(a).upper() for a in permitted_agents]
            
            # Dynamic downstream needs check
            need_transport = bool(
                payload.get("need_transport", payload.get("req_transport", row.get("need_transport", row.get("req_transport", True))))
            ) and ("TRANSPORT" in permitted_agents)
            need_storage = bool(
                payload.get("need_storage", payload.get("need_warehouse", payload.get("req_warehouse", row.get("need_storage", row.get("need_warehouse", True)))))
            ) and ("WAREHOUSE" in permitted_agents)
            allow_processing = bool(
                payload.get("allow_processing", payload.get("need_processor", payload.get("req_processor", row.get("allow_processing", row.get("need_processor", True)))))
            ) and ("PROCESSOR" in permitted_agents)

            # Check if farmer owns transport or storage
            if payload.get("has_transport") or (row and row.get("has_transport")):
                need_transport = False
            if payload.get("has_storage") or (row and row.get("has_storage")):
                need_storage = False

        holding_days = int((payload and (payload.get("holding_days") or payload.get("shelf_life"))) or (row and (row.get("holding_days") or row.get("shelf_life"))) or 7)

        initial_graph_state = {
            "trace_id": f"trace-{uuid.uuid4().hex[:8]}",
            "negotiation_id": negotiation_id,
            "crop": crop_norm,
            "quantity": qty,
            "target_price": target_p,
            "reservation_price": reservation_p,
            "budget": budget,
            "location": (row and row.get("location")) or "Maharashtra",
            "buyer_name": (row and (row.get("buyer") or row.get("buyer_name"))) or "Buyer Agent",
            "persona": (payload and payload.get("persona")) or "bulk_wholesaler",
            "strategy": (payload and payload.get("strategy")) or "balanced",
            "workflow_mode": workflow_mode,
            "permitted_agents": permitted_agents,
            "need_transport": need_transport,
            "need_storage": need_storage,
            "allow_processing": allow_processing,
            "holding_days": holding_days,
            "sellers": payload.get("sellers") if payload else None,
            "max_rounds": int((payload and payload.get("max_rounds")) or 5),
            "logs": [],
            "emitted_events": [],
        }

        # Invoke compiled LangGraph Buyer Graph Orchestrator
        from backend.agents.buyer_graph import buyer_graph_orchestrator
        orch_res = await buyer_graph_orchestrator.ainvoke(initial_graph_state)

        winner = orch_res.get("winner")
        if winner:
            winner["is_best"] = True
            winner["rank"] = 1
            if "negotiated_price" not in winner:
                winner["negotiated_price"] = winner.get("final_price")
        winner_status = orch_res.get("status", "NO_EXECUTABLE_DEAL")
        negotiations = orch_res.get("negotiations", [])
        executable_deals = orch_res.get("executable_deals", [])
        chat_transcript = orch_res.get("chat_transcript", "")
        transport_assignment = orch_res.get("transport_assignment")
        warehouse_assignment = orch_res.get("warehouse_assignment")
        processor_assignment = orch_res.get("processor_assignment")
        end_to_end_deal = orch_res.get("end_to_end_deal")

        # Format suppliers list for frontend dashboard compatibility
        ranked_suppliers = []
        for rank_idx, neg in enumerate(negotiations, 1):
            ranked_suppliers.append({
                "rank": rank_idx,
                "index": rank_idx - 1,
                "name": neg["seller_name"],
                "location": neg["location"],
                "distance_km": neg["distance_km"],
                "initial_ask": neg["initial_ask"],
                "negotiated_price": neg["final_price"] if neg["final_price"] is not None else neg["initial_ask"],
                "freight_total": neg["freight_total"],
                "freight_per_kg": neg["freight_per_kg"],
                "apmc_cess_per_kg": neg["apmc_cess_per_kg"],
                "landed_cost_per_kg": neg["landed_cost_per_kg"],
                "total_landed_cost": neg["total_landed_cost"],
                "match_score": neg["match_score"],
                "special": f"Rounds: {neg['rounds_count']} | Status: {neg['status']}",
                                "is_disqualified": not neg["is_valid_deal"],
                "disqualification_reason": neg.get("rejection_reason"),
                "status": "🏆 Auto-Selected Best Deal" if (winner and neg.get("session_id") == winner.get("session_id")) else neg["status"],
                "is_best": bool(winner and neg.get("session_id") == winner.get("session_id")),
                "session_id": neg.get("session_id"),
                "seller_id": neg.get("seller_id"),
                "branch_index": neg.get("branch_index", rank_idx - 1),
                "chat_messages": neg.get("chat_messages", []),
                "rounds": neg.get("rounds", []),
                "messages": neg.get("messages", []),
                "contract": neg.get("contract"),
            })

        # Update negotiation record in Database
        if winner:
            db_status = "DEAL"
            final_p = winner["final_price"]
            summary_text = (
                f"Autonomous Parallel Buying completed across {len(negotiations)} suppliers. "
                f"Auto-selected #1: {winner['seller_name']} at ₹{winner['final_price']}/kg "
                f"(Landed: ₹{winner['landed_cost_per_kg']}/kg)."
            )
        else:
            db_status = "NO_EXECUTABLE_DEAL"
            final_p = None
            summary_text = (
                f"Autonomous Parallel Buying completed across {len(negotiations)} suppliers. "
                f"No executable deal found meeting reservation ceiling (₹{reservation_p:.2f}/kg) or budget."
            )

        self.active_negotiations.setdefault(negotiation_id, {})["parallel_branches"] = ranked_suppliers
        self.active_negotiations[negotiation_id]["parallel_results"] = negotiations
        update_payload = {
            "crop": crop_norm,
            "quantity": qty,
            "farmer_name": winner["seller_name"] if winner else "No Deal",
            "farmer": winner["seller_name"] if winner else "No Deal",
            "final_price": final_p,
            "status": db_status,
            "summary": summary_text,
            "transport_plan": transport_assignment,
            "warehouse_plan": warehouse_assignment,
            "processor_plan": processor_assignment,
            "end_to_end_deal": end_to_end_deal,
            "logs": orch_res.get("logs", []),
            "contract_hash": end_to_end_deal.get("contract_hash") if end_to_end_deal else None,
            "market_offers": ranked_suppliers,
        }
        await self.db_repo.update_negotiation_async(negotiation_id, update_payload)
        if negotiation_id in self.active_negotiations:
            self.active_negotiations[negotiation_id].update(update_payload)
        alt_id = f"neg_{negotiation_id}" if not negotiation_id.startswith("neg_") else negotiation_id[4:]
        if alt_id in self.active_negotiations:
            self.active_negotiations[alt_id].update(update_payload)

        # Record parallel summary offer
        parallel_offer = {
            "round": int(row.get("current_round", 1)) + 1,
            "agent": "Autonomous Parallel Buying Engine",
            "price": final_p if final_p is not None else 0.0,
            "decision": "ACCEPT" if winner else "REJECT",
            "quantity": qty,
            "message": summary_text,
        }
        await self.db_repo.append_offer_async(negotiation_id, parallel_offer)

        try:
            from backend.websocket.agent_updates import agent_update_hub as ws_manager
            await ws_manager.broadcast({
                "event": "NEGOTIATION_LOG",
                "negotiation_id": negotiation_id,
                "agent_type": "buyer",
                "message": summary_text,
                "offer": final_p or 0.0,
            })
            await ws_manager.broadcast({
                "event": "PARALLEL_PROCUREMENT_COMPLETE",
                "negotiation_id": negotiation_id,
                "winner": winner,
                "suppliers": ranked_suppliers,
                "status": winner_status,
                "chat_transcript": chat_transcript,
                "transport_assignment": transport_assignment,
                "warehouse_assignment": warehouse_assignment,
                "processor_assignment": processor_assignment,
                "end_to_end_deal": end_to_end_deal,
            })
        except Exception as ws_err:
            logger.warning(f"WebSocket broadcast error in parallel procurement: {ws_err}")

        return {
            "success": True,
            "negotiation_id": negotiation_id,
            "buyer_ceiling": reservation_p,
            "status": winner_status,
            "winner": winner,
            "requested_quantity": orch_res.get("requested_quantity", qty),
            "allocated_quantity": orch_res.get("allocated_quantity", float(winner["executable_quantity"]) if winner else 0.0),
            "remaining_quantity": orch_res.get("remaining_quantity", 0.0 if winner else qty),
            "min_purchase_quantity": orch_res.get("min_purchase_quantity", 0.0),
            "candidate_count": len(negotiations),
            "suppliers": ranked_suppliers,
            "negotiations": negotiations,
            "executable_deals": executable_deals,
            "chat_transcript": chat_transcript,
            "transport_assignment": transport_assignment,
            "warehouse_assignment": warehouse_assignment,
            "processor_assignment": processor_assignment,
            "end_to_end_deal": end_to_end_deal,
            "logs": orch_res.get("logs", []),
        }

    async def autonomous_step(self, negotiation_id: str):
        """
        Buyer Agent analyzes latest farmer ask, calculates optimal strategic counter,
        and exchanges offers autonomously without requiring human typing.
        Guarded by statutory MSP ceiling.
        """
        row = await self.db_repo.get_negotiation_async(negotiation_id)
        if not row:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Negotiation not found")

        crop_val = (row and row.get("crop")) or "Soybean"
        crop = str(crop_val).strip() if crop_val else "Soybean"
        crop_norm = "Soybean"
        for k in STATUTORY_BENCHMARKS:
            if k.lower() in crop.lower():
                crop_norm = k
                break
        bench_info = STATUTORY_BENCHMARKS.get(crop_norm, {"benchmark": 48.92})
        statutory_bench = float(bench_info.get("benchmark", 48.92))

        offers = await self.db_repo.get_offers_for_negotiation_async(negotiation_id)
        farmer_offers = [o for o in offers if not ("buyer" in str(o.get("agent", "")).lower() or "human" in str(o.get("agent", "")).lower())]
        latest_farmer_ask = farmer_offers[-1]["price"] if farmer_offers else float(row.get("min_price", 18))
        
        target_price = float(row.get("target_price") or row.get("buyer_target_price") or statutory_bench)
        max_buyer_ceiling = round(max(target_price * 1.35, statutory_bench * 1.40), 2)

        buyer_offers = [o for o in offers if ("buyer" in str(o.get("agent", "")).lower() or "human" in str(o.get("agent", "")).lower())]
        latest_buyer_bid = buyer_offers[-1]["price"] if buyer_offers else target_price
        
        gap = latest_farmer_ask - latest_buyer_bid
        if gap <= 0.4 and latest_farmer_ask <= max_buyer_ceiling:
            return await self.intervene_deal(negotiation_id, {"price": latest_farmer_ask, "quantity": row.get("quantity", 500)})
        
        step = round(max(0.25, gap * 0.35), 2)
        new_buyer_price = round(min(latest_farmer_ask, latest_buyer_bid + step), 2)
        new_buyer_price = min(new_buyer_price, max_buyer_ceiling)
        return await self.intervene_deal(negotiation_id, {"price": new_buyer_price, "quantity": row.get("quantity", 500)})




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
