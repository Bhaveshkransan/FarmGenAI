import asyncio
import json
import sys
import os

sys.path.insert(0, ".")

from database.db import AsyncSessionLocal, DBUser, DBBuyer, DBFarmer, DBProduce, DBNegotiation
from backend.core.security import hash_password
from sqlalchemy import select

DEMO_USERS = [
    {
        "user_id": "usr_buyer_demo",
        "name": "AgroCorp Procurement Director",
        "email": "buyer@agrinegotiator.com",
        "password": hash_password("password123"),
        "location": "Pune / Nashik, Maharashtra",
        "language": "English",
        "role": "buyer",
        "verification_status": "VERIFIED",
        "trust_score": 4.85,
        "preferences": json.dumps({
            "buyer_persona": "food_processing",
            "business_name": "AgroCorp Food Processing Ltd",
            "fssai_license": "FSSAI-12345678901234",
            "gstin": "27AABCU9603R1ZM",
            "mandi_license": "PUN-APMC-9941",
            "processing_capacity": "50 MT/day",
            "procurement_window": "Immediate (Next 7 Days)"
        })
    },
    {
        "user_id": "usr_farmer_demo",
        "name": "Ramesh Patil",
        "email": "farmer@agrinegotiator.com",
        "password": hash_password("password123"),
        "location": "Lasalgaon Mandi, Nashik, Maharashtra",
        "language": "Marathi",
        "role": "farmer",
        "verification_status": "VERIFIED",
        "trust_score": 4.90,
        "preferences": json.dumps({
            "farm_name": "Patil Organics",
            "primary_crop": "Soybean",
            "mandi_location": "Lasalgaon APMC"
        })
    },
    {
        "user_id": "usr_admin_demo",
        "name": "System Administrator",
        "email": "admin@agrinegotiator.com",
        "password": hash_password("password123"),
        "location": "Mumbai, Maharashtra",
        "language": "English",
        "role": "admin",
        "verification_status": "VERIFIED",
        "trust_score": 5.0,
        "preferences": json.dumps({
            "dashboard_view": "ai-ops"
        })
    },
    {
        "user_id": "usr_transport_demo",
        "name": "Maharashtra Express Logistics Fleet",
        "email": "transport@agrinegotiator.com",
        "password": hash_password("password123"),
        "location": "Nashik / Mumbai Corridor, Maharashtra",
        "language": "English",
        "role": "transport",
        "verification_status": "VERIFIED",
        "trust_score": 4.92,
        "preferences": json.dumps({
            "fleet_size": 24,
            "reefer_available": True,
            "base_terminal": "Nashik APMC Logistics Hub"
        })
    },
    {
        "user_id": "usr_warehouse_demo",
        "name": "MahaWarehouse Storage Hub",
        "email": "warehouse@agrinegotiator.com",
        "password": hash_password("password123"),
        "location": "Lasalgaon, Nashik, Maharashtra",
        "language": "English",
        "role": "warehouse",
        "verification_status": "VERIFIED",
        "trust_score": 4.88,
        "preferences": json.dumps({
            "capacity_mt": 10000,
            "cold_storage": True
        })
    },
    {
        "user_id": "usr_processor_demo",
        "name": "Sahyadri Agro Milling & Processing",
        "email": "processor@agrinegotiator.com",
        "password": hash_password("password123"),
        "location": "Pune MIDC, Maharashtra",
        "language": "English",
        "role": "processor",
        "verification_status": "VERIFIED",
        "trust_score": 4.95,
        "preferences": json.dumps({
            "daily_milling_capacity_mt": 120
        })
    }
]

async def seed_users():
    print("=== Seeding Authenticated Demo Users ===")
    async with AsyncSessionLocal() as session:
        for u in DEMO_USERS:
            # Check existing in DBUser
            res = await session.execute(select(DBUser).where(DBUser.email == u["email"]))
            existing = res.scalars().first()
            if existing:
                print(f"Updating DBUser: {u['email']}")
                for k, v in u.items():
                    setattr(existing, k, v)
            else:
                print(f"Creating DBUser: {u['email']}")
                new_user = DBUser(**u)
                session.add(new_user)
        
        # Also ensure buyer entry exists in DBBuyer
        buyer_res = await session.execute(select(DBBuyer).where(DBBuyer.user_id == "usr_buyer_demo"))
        if not buyer_res.scalars().first():
            print("Creating DBBuyer record for usr_buyer_demo")
            db_buyer = DBBuyer(
                id="buy_agrocorp_demo",
                user_id="usr_buyer_demo",
                buyer_name="AgroCorp Food Processing Ltd",
                crop="Soybean",
                min_price=46.0,
                max_price=53.0,
                quantity=5000.0,
                location="Pune / Nashik, Maharashtra",
                urgency="HIGH",
                neg_mode="BALANCED",
                strategy="food_processing",
                status="ACTIVE"
            )
            session.add(db_buyer)

        
        # Ensure DBFarmer entry exists for usr_farmer_demo
        farmer_res = await session.execute(select(DBFarmer).where(DBFarmer.id == "usr_farmer_demo"))
        existing_farmer = farmer_res.scalars().first()
        if not existing_farmer:
            print("Creating DBFarmer record for usr_farmer_demo")
            db_farmer = DBFarmer(
                id="usr_farmer_demo",
                name="Ramesh Patil",
                contact_number="+91 98220 12345",
                location="Lasalgaon Mandi, Nashik, Maharashtra",
                village="Lasalgaon",
                taluka="Niphad",
                district="Nashik",
                state="Maharashtra",
                latitude=20.1478,
                longitude=74.2255,
                language="Marathi",
                farm_size_acres=12.5,
                farming_type="Conventional / Integrated",
                preferences={"primary_crop": "Soybean", "mandi_location": "Lasalgaon APMC"}
            )
            session.add(db_farmer)

        # Seed sample active crop listings for Ramesh Patil (usr_farmer_demo)
        FARMER_DEMO_PRODUCE = [
            {
                "id": "prod_farmer_demo_soybean_01",
                "trace_id": "TRC-LST-SOY-DEMO",
                "workflow_mode": "FULL_SUPPLY_CHAIN",
                "user_id": "usr_farmer_demo",
                "farmer_name": "Ramesh Patil",
                "crop": "Soybean",
                "crop_category": "Oilseeds",
                "variety": "JS 335",
                "grade": "A",
                "quantity": 5000.0,
                "unit": "kg",
                "min_sale_quantity": 500.0,
                "expected_price": 58.0,
                "min_price": 52.0,
                "price_unit": "per_kg",
                "harvest_date": "2026-10-10",
                "availability_date": "2026-10-15",
                "preferred_selling_date": "2026-10-25",
                "shelf_life": 180,
                "location": "Lasalgaon Mandi, Nashik, Maharashtra",
                "latitude": 20.1478,
                "longitude": 74.2255,
                "status": "ACTIVE",
                "selected_services": ["TRANSPORT", "WAREHOUSE"]
            },
            {
                "id": "prod_farmer_demo_onion_02",
                "trace_id": "TRC-LST-ONION-DEMO",
                "workflow_mode": "FULL_SUPPLY_CHAIN",
                "user_id": "usr_farmer_demo",
                "farmer_name": "Ramesh Patil",
                "crop": "Onion",
                "crop_category": "Vegetables",
                "variety": "Garwa Red",
                "grade": "A",
                "quantity": 4000.0,
                "unit": "kg",
                "min_sale_quantity": 500.0,
                "expected_price": 28.5,
                "min_price": 24.0,
                "price_unit": "per_kg",
                "harvest_date": "2026-10-12",
                "availability_date": "2026-10-16",
                "preferred_selling_date": "2026-10-26",
                "shelf_life": 45,
                "location": "Lasalgaon Mandi, Nashik, Maharashtra",
                "latitude": 20.1478,
                "longitude": 74.2255,
                "status": "ACTIVE",
                "selected_services": ["TRANSPORT", "WAREHOUSE"]
            },
            {
                "id": "prod_farmer_demo_cotton_03",
                "trace_id": "TRC-LST-COT-DEMO",
                "workflow_mode": "FULL_SUPPLY_CHAIN",
                "user_id": "usr_farmer_demo",
                "farmer_name": "Ramesh Patil",
                "crop": "Cotton",
                "crop_category": "Fibre",
                "variety": "Bunny BT",
                "grade": "A",
                "quantity": 6000.0,
                "unit": "kg",
                "min_sale_quantity": 1000.0,
                "expected_price": 72.0,
                "min_price": 66.0,
                "price_unit": "per_kg",
                "harvest_date": "2026-10-05",
                "availability_date": "2026-10-10",
                "preferred_selling_date": "2026-10-28",
                "shelf_life": 365,
                "location": "Jalgaon APMC, Maharashtra",
                "latitude": 21.0077,
                "longitude": 75.5626,
                "status": "ACTIVE",
                "selected_services": ["TRANSPORT", "WAREHOUSE", "PROCESSOR"]
            },
            {
                "id": "prod_farmer_demo_bajra_04",
                "trace_id": "TRC-LST-BAJ-DEMO",
                "workflow_mode": "FULL_SUPPLY_CHAIN",
                "user_id": "usr_farmer_demo",
                "farmer_name": "Ramesh Patil",
                "crop": "Bajra",
                "crop_category": "Cereals",
                "variety": "ICTP 8203",
                "grade": "A",
                "quantity": 3500.0,
                "unit": "kg",
                "min_sale_quantity": 500.0,
                "expected_price": 26.0,
                "min_price": 22.5,
                "price_unit": "per_kg",
                "harvest_date": "2026-10-08",
                "availability_date": "2026-10-14",
                "preferred_selling_date": "2026-10-27",
                "shelf_life": 120,
                "location": "Malegaon APMC, Nashik, Maharashtra",
                "latitude": 20.5539,
                "longitude": 74.5244,
                "status": "ACTIVE",
                "selected_services": ["TRANSPORT"]
            }
        ]

        for p in FARMER_DEMO_PRODUCE:
            res_p = await session.execute(select(DBProduce).where(DBProduce.id == p["id"]))
            existing_p = res_p.scalars().first()
            if existing_p:
                for k, v in p.items():
                    setattr(existing_p, k, v)
            else:
                session.add(DBProduce(**p))
        print("Seeded 4 active crop listings for Ramesh Patil (usr_farmer_demo)")

        # Link negotiations to usr_farmer_demo
        FARMER_NEGS = ["synth_neg_001", "synth_neg_004", "synth_neg_008", "synth_neg_009"]
        for neg_id in FARMER_NEGS:
            res_n = await session.execute(select(DBNegotiation).where(DBNegotiation.negotiation_id == neg_id))
            neg = res_n.scalars().first()
            if neg:
                neg.farmer_id = "usr_farmer_demo"
                neg.farmer_name = "Ramesh Patil"
        print("Linked active demo negotiations to Ramesh Patil (usr_farmer_demo)")

        await session.commit()
    print("=== Demo users seeded successfully! ===")

if __name__ == "__main__":
    asyncio.run(seed_users())
