import asyncio
import json
import sys
import os

sys.path.insert(0, ".")

from database.db import AsyncSessionLocal, DBUser, DBBuyer, DBFarmer
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
        from backend.db.models.user import User
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
            
            # Check existing in User (v1_users)
            res_v1 = await session.execute(select(User).where(User.email == u["email"]))
            existing_v1 = res_v1.scalars().first()
            if existing_v1:
                print(f"Updating User (v1): {u['email']}")
                existing_v1.hashed_password = u["password"]
                existing_v1.full_name = u["name"]
                existing_v1.role = u["role"]
                existing_v1.is_active = True
            else:
                print(f"Creating User (v1): {u['email']}")
                new_v1 = User(
                    id=u["user_id"],
                    email=u["email"],
                    hashed_password=u["password"],
                    full_name=u["name"],
                    role=u["role"],
                    is_active=True
                )
                session.add(new_v1)
        
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

        await session.commit()
    print("=== Demo users seeded successfully! ===")

if __name__ == "__main__":
    asyncio.run(seed_users())
