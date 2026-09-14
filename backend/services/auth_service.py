from backend.repositories.user_repository import UserRepository
from database.db import Database, DBUser, AsyncSessionLocal
from sqlalchemy import select
from backend.services.security import hash_password, verify_password, create_access_token

async def signup_user(data: dict):
    # ── Robust Email Check ─────────────────────────────
    async def _check_email():
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(DBUser).where(DBUser.email == data["email"]))
            return res.scalars().first() is not None
            
    if await _check_email():
        return {"error": "User with this email already exists"}

    user_id = Database.generate_id("user")
    role = data.get("role", "farmer").lower()

    # Hash password securely using Bcrypt
    hashed_pwd = hash_password(data["password"])

    buyer_persona = data.get("buyer_persona") or "general_buyer"
    business_name = data.get("business_name") or data["name"]
    fssai_license = data.get("fssai_license") or ""
    gstin = data.get("gstin") or ""
    mandi_license = data.get("mandi_license") or ""
    processing_capacity = data.get("processing_capacity") or ""
    procurement_window = data.get("procurement_window") or ""

    user_prefs = {
        "buyer_persona": buyer_persona,
        "business_name": business_name,
        "fssai_license": fssai_license,
        "gstin": gstin,
        "mandi_license": mandi_license,
        "processing_capacity": processing_capacity,
        "procurement_window": procurement_window
    }

    user_record = {
        "user_id": user_id,
        "name": data["name"],
        "email": data["email"],
        "password": hashed_pwd,
        "location": data["location"],
        "language": data.get("language", "English"),
        "role": role,
        "verification_status": "VERIFIED" if (fssai_license or gstin or mandi_license) else "PENDING",
        "preferences": user_prefs,
        "trust_score": 4.5 if (fssai_license or gstin) else 4.0
    }

    # Persist to Core User Table
    await UserRepository.upsert(user_record)

    # ── Role-Specific Initialization ───────────────────
    if role == "farmer":
        await Database.upsert_farmer_async({
            "id": user_id,
            "name": data["name"],
            "location": data["location"],
            "language": user_record["language"]
        })
    elif role == "buyer":
        await Database.upsert_buyer_async({
            "id": user_id,
            "name": data["name"],
            "location": data["location"],
            "budget": 100000, # Default high budget for new buyers
            "max_quantity": 5000,
            "target_price": 20,
            "strategy": buyer_persona,
            "buyer_persona": buyer_persona,
            "business_name": business_name,
            "fssai_license": fssai_license,
            "gstin": gstin,
            "preferences": user_prefs
        })
    
    await Database.add_history_async(user_id, {"type": "ACCOUNT_CREATED", "role": role, "message": f"New {role} account initialized ({buyer_persona})."})

    # Issue access token
    token = create_access_token({"sub": user_id, "role": role})

    return {
        "user_id": user_id,
        "name": user_record["name"],
        "email": user_record["email"],
        "location": user_record["location"],
        "language": user_record["language"],
        "role": role,
        "trust_score": user_record["trust_score"],
        "token": token,
        "buyer_persona": buyer_persona,
        "business_name": business_name,
        "fssai_license": fssai_license,
        "gstin": gstin,
        "preferences": user_prefs,
        "verification_status": user_record["verification_status"],
        "message": "Signup successful"
    }


async def login_user(data: dict):
    # Check Database for most fresh user data
    async def _get_user_db():
        async with AsyncSessionLocal() as session:
            res = await session.execute(select(DBUser).where(DBUser.email == data["email"]))
            return res.scalars().first()

    u = await _get_user_db()
    if u and verify_password(data["password"], u.password):
        token = create_access_token({"sub": u.user_id, "role": u.role})
        prefs = {}
        if u.preferences:
            if isinstance(u.preferences, dict):
                prefs = u.preferences
            elif isinstance(u.preferences, str):
                try:
                    import json
                    prefs = json.loads(u.preferences)
                except Exception:
                    prefs = {}

        return {
            "user_id": u.user_id,
            "name": u.name,
            "email": u.email,
            "location": u.location,
            "language": u.language,
            "role": u.role,
            "trust_score": u.trust_score,
            "token": token,
            "buyer_persona": prefs.get("buyer_persona", "general_buyer"),
            "business_name": prefs.get("business_name", u.name),
            "fssai_license": prefs.get("fssai_license", ""),
            "gstin": prefs.get("gstin", ""),
            "preferences": prefs,
            "verification_status": getattr(u, "verification_status", "PENDING"),
            "message": "Login successful"
        }

    return {"error": "Invalid email or password"}

