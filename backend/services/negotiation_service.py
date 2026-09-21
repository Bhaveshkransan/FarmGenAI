from sqlalchemy.ext.asyncio import AsyncSession
from backend.repositories.user_repository import UserRepository
import logging
import asyncio
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
        if payload.get("buyer_mode"):
            ask = float(payload["min_price"])
            floor = float(payload.get("farmer_floor") or round(ask * 0.75, 2))
            return FarmerAgent(
                name=payload.get("farmer_name", "FarmerAgent"),
                crop=payload["crop"],
                quantity=float(payload["quantity"]),
                min_price=floor,
                initial_price=ask,
                shelf_life=int(payload.get("shelf_life", 3)),
                location=payload.get("location")
            )
        return FarmerAgent(
            name=payload.get("farmer_name", "FarmerAgent"),
            crop=payload["crop"],
            quantity=float(payload["quantity"]),
            min_price=float(payload["min_price"]),
            shelf_life=int(payload.get("shelf_life", 3)),
            location=payload.get("location")
        )

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

        offers = []
        # Use in-memory buyers (seeded by ensure_default_buyers) which have 'name', 'budget', 'target_price' etc.
        buyer_profiles = list(self.db_repo.buyers.values())
        # Fallback: if in-memory is empty, query DB
        if not buyer_profiles:
            db_buyers = await self.db_repo.list_buyers_async()
            # Normalize DB rows to match in-memory schema
            buyer_profiles = [
                {
                    "id": b.get("id"),
                    "name": b.get("buyer_name") or b.get("name") or "Unknown Buyer",
                    "budget": float(b.get("max_price") or b.get("budget") or min_price * quantity * 1.5),
                    "max_quantity": float(b.get("quantity") or quantity),
                    "target_price": float(b.get("max_price") or b.get("target_price") or min_price * 1.2),
                    "location": b.get("location", "Market"),
                    "strategy": b.get("strategy", "standard"),
                }
                for b in db_buyers
            ]
        for profile in buyer_profiles:
            strategy = str(profile.get("strategy") or "").lower()
            if profile.get("kind") == "offer":
                continue

            offered_qty = min(quantity, float(profile.get("max_quantity", quantity)))
            if offered_qty <= 0:
                continue

            budget_limited_price = float(profile.get("budget", 0)) / offered_qty
            
            if "restaurant" in strategy or "premium" in strategy:
                # Premium buyers start slightly higher but still below target
                opening_bid = min(float(profile.get("target_price", min_price)) * 0.85, budget_limited_price)
            else:
                opening_bid = min(float(profile.get("target_price", min_price)) * 0.75, budget_limited_price, (market_price + 3) * 0.75)
                
            offer_price = round(max(1.0, opening_bid), 2)
            distance_penalty = 0 if profile.get("location") == location else 0.2
            
            # User Preference Boost (Stakeholder Requirement C4)
            pref_boost = 15.0 if (buyer_pref in strategy and buyer_pref != "any") else 0.0
            
            # Verification Integrity Boost (Test I2)
            is_verified = bool(profile.get("verified", False))
            verification_weight = 20.0 if is_verified else -10.0
            
            is_viable = offer_price >= min_price
            
            # Weighted Scoring Engine (Personalized for Phase C4 + Phase I)
            if "restaurant" in strategy:
                score = round((offer_price - distance_penalty) * 150 + pref_boost + verification_weight + min(offered_qty, quantity) / 50, 2)
            else:
                score = round((offer_price - distance_penalty) * 100 + pref_boost + verification_weight + min(offered_qty, quantity) / 10, 2)

            # Strategic Labelling (Test E4)
            label = "Market Option"
            if is_viable:
                if score > 150: label = "👑 Best Profit"
                elif distance_penalty == 0: label = "⚡ Fast Handshake"
                elif "restaurant" in strategy: label = "💎 Premium Match"
                elif pref_boost > 0: label = "🎯 Strategic Fit"

            offers.append(
                {
                    "buyer_id": profile.get("id") or profile.get("buyer_id") or profile.get("user_id", "unknown"),
                    "buyer_name": profile.get("name") or profile.get("buyer_name") or profile.get("company", "Unknown Buyer"),
                    "location": profile.get("location", "Market"),
                    "strategy": label,
                    "offered_price": offer_price,
                    "offered_quantity": round(offered_qty, 2),
                    "budget": float(profile.get("budget", 0)),
                    "target_price": float(profile.get("target_price", min_price)),
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
                "status": "ACTIVE"
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
            "selected_buyer": selected_offer,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "transport_plan": None,
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

        # If sync=True is requested, await completion (used for CLI scripts / unit tests)
        if payload.get("sync") is True:
            return await self._run_negotiation_workflow(
                negotiation_id, manager, transporter, payload, scenario, farmer_row, produce_row, selected_offer, market_offers, farmer, live_event_callback
            )

        # Default async execution: dispatch background task and return immediately (50ms response time)
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
            "farmer": farmer_row["name"]
        }

    async def _run_negotiation_workflow(
        self, negotiation_id, manager, transporter, payload, scenario, farmer_row, produce_row, selected_offer, market_offers, farmer, live_event_callback
    ):
        try:
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
            if farmer.location != buyer_loc:
                dist = 180.0
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
                    "message": result.get("summary", "Negotiation completed.")
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
        }

    async def get_negotiation_status(self, negotiation_id: str):
        offers = await self.db_repo.get_offers_for_negotiation_async(negotiation_id)
        if negotiation_id in self.active_negotiations:
            res = dict(self.active_negotiations[negotiation_id])
            if offers:
                res["offers"] = offers
            return res

        row = await self.db_repo.get_negotiation_async(negotiation_id)
        if not row:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Negotiation not found")

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
            "user_id": row.get("user_id"),
            "status": row.get("status", "UNKNOWN"),
            "summary": row.get("summary", ""),
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
        crop = row.get("crop", "Tomato")
        farmer_name = row.get("farmer") or row.get("farmer_name") or "Farmer Ramesh"
        buyer_name = row.get("buyer") or row.get("buyer_name") or "Buyer"

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
        farmer_floor = float(row.get("farmer_floor") or round(min_p * 0.75, 2))
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

    async def run_parallel_procurement(self, negotiation_id: str, payload: dict = None):
        """
        Executes Autonomous Parallel Buying across all 5 Maharashtra candidate suppliers:
        1. Identifies the 5 verified Maharashtra mandi lots for this crop.
        2. Concurrently negotiates concession pricing with each supplier in parallel.
        3. Computes Landed Cost (Base Rate + Freight based on distance + APMC Cess).
        4. Disqualifies rogue quotes that exceed the statutory MSP ceiling.
        5. Auto-selects Rank #1 (Lowest Landed Cost with highest match score).
        6. Updates negotiation record with the auto-selected winning deal.
        """
        row = await self.db_repo.get_negotiation_async(negotiation_id)
        if not row:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Negotiation not found")

        crop = row.get("crop", "Soybean")
        crop_norm = "Soybean"
        for k in STATUTORY_BENCHMARKS:
            if k.lower() in crop.lower():
                crop_norm = k
                break

        bench_info = STATUTORY_BENCHMARKS.get(crop_norm, {"benchmark": 48.92})
        statutory_bench = float(bench_info.get("benchmark", 48.92))
        qty = float((payload and payload.get("quantity")) or row.get("quantity") or 500)
        target_p = float((payload and payload.get("target_price")) or row.get("target_price") or row.get("price") or statutory_bench)
        max_buyer_ceiling = round(max(target_p * 1.35, statutory_bench * 1.40), 2)

        suppliers_pool = MAHARASHTRA_CROP_SUPPLIERS.get(crop_norm, MAHARASHTRA_CROP_SUPPLIERS["Soybean"])

        parallel_results = []
        for idx, cp in enumerate(suppliers_pool):
            # 1. Opening initial ask from supplier lot
            initial_p = round(target_p * (1.08 + idx * 0.02), 2)
            # 2. Parallel simulated concession bargaining (autonomous RL agent concession)
            # Rank 0 (leader) concedes closest to target; others have slight variations
            concession_factor = 0.98 if idx == 0 else (1.01 + idx * 0.015)
            negotiated_p = round(target_p * concession_factor, 2)

            # Check if quote exceeds ceiling
            is_disqualified = negotiated_p > max_buyer_ceiling
            
            # 3. Freight logistics based on highway distance (₹6.50/km flat + handling)
            freight_total = max(650.0, round(cp["dist"] * 6.50 + qty * 0.35, 2))
            freight_per_kg = round(freight_total / max(1.0, qty), 2)
            
            # 4. APMC statutory cess (1% on base purchase value)
            apmc_cess_per_kg = round(negotiated_p * 0.01, 2)
            
            # 5. True Landed Cost per kg
            landed_cost_per_kg = round(negotiated_p + freight_per_kg + apmc_cess_per_kg, 2)
            total_landed_cost = round(landed_cost_per_kg * qty, 2)

            match_score = max(85, cp["match"] - idx * 2)

            parallel_results.append({
                "index": idx,
                "name": cp["name"],
                "location": cp["loc"],
                "distance_km": cp["dist"],
                "initial_ask": initial_p,
                "negotiated_price": negotiated_p,
                "freight_total": freight_total,
                "freight_per_kg": freight_per_kg,
                "apmc_cess_per_kg": apmc_cess_per_kg,
                "landed_cost_per_kg": landed_cost_per_kg,
                "total_landed_cost": total_landed_cost,
                "match_score": match_score,
                "special": cp["special"],
                "is_disqualified": is_disqualified,
                "disqualification_reason": "Exceeds MSP Ceiling" if is_disqualified else None,
                "status": "Disqualified" if is_disqualified else ("Counter-offered" if idx > 0 else "Active (Best Match)"),
                "is_best": False
            })

        # Rank qualified suppliers by lowest landed cost per kg
        qualified = [s for s in parallel_results if not s["is_disqualified"]]
        qualified.sort(key=lambda s: (s["landed_cost_per_kg"], -s["match_score"]))
        
        # Designate #1 winner
        if qualified:
            qualified[0]["is_best"] = True
            qualified[0]["status"] = "🏆 Auto-Selected Best Deal"
            winner = qualified[0]
        else:
            winner = parallel_results[0]
            winner["is_best"] = True

        # Sort all suppliers for display (winner first, then other qualified by landed cost, then disqualified)
        ranked_suppliers = sorted(parallel_results, key=lambda s: (1 if s["is_disqualified"] else 0, s["landed_cost_per_kg"]))
        for rank_idx, s in enumerate(ranked_suppliers, 1):
            s["rank"] = rank_idx

        # Update negotiation in DB with the auto-selected winner
        await self.db_repo.update_negotiation_async(negotiation_id, {
            "farmer_name": winner["name"],
            "farmer": winner["name"],
            "final_price": winner["negotiated_price"],
            "status": "ACTIVE",
            "summary": f"Autonomous Parallel Buying completed across 5 Maharashtra suppliers. Auto-selected #1: {winner['name']} at ₹{winner['negotiated_price']}/kg (Landed: ₹{winner['landed_cost_per_kg']}/kg)."
        })

        # Add parallel summary offer to negotiation history
        parallel_offer = {
            "round": int(row.get("current_round", 1)) + 1,
            "agent": "Autonomous Parallel Buying Engine",
            "price": winner["negotiated_price"],
            "decision": "COUNTER",
            "quantity": qty,
            "message": (
                f"⚡ [Parallel Procurement Completed] Evaluated 5 Maharashtra suppliers in parallel. "
                f"Auto-selected winning supplier: {winner['name']} ({winner['location']}) "
                f"at ₹{winner['negotiated_price']}/kg (Landed Cost: ₹{winner['landed_cost_per_kg']}/kg, {winner['match_score']}% Match)."
            )
        }
        await self.db_repo.append_offer_async(negotiation_id, parallel_offer)

        try:
            from backend.websocket.agent_updates import agent_update_hub as ws_manager
            await ws_manager.broadcast({
                "event": "NEGOTIATION_LOG",
                "negotiation_id": negotiation_id,
                "agent_type": "buyer",
                "message": parallel_offer["message"],
                "offer": winner["negotiated_price"]
            })
            await ws_manager.broadcast({
                "event": "PARALLEL_PROCUREMENT_COMPLETE",
                "negotiation_id": negotiation_id,
                "winner": winner,
                "suppliers": ranked_suppliers
            })
        except Exception:
            pass

        return {
            "success": True,
            "negotiation_id": negotiation_id,
            "crop": crop_norm,
            "quantity": qty,
            "statutory_benchmark": statutory_bench,
            "buyer_ceiling": max_buyer_ceiling,
            "winner": winner,
            "suppliers": ranked_suppliers
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

        crop = row.get("crop", "Soybean")
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
