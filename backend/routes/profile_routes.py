"""
backend/routes/profile_routes.py

User profile management endpoints.
FR-1: User Registration & Profile Management

Extended farmer/buyer profiles are now persisted to PostgreSQL via
Database.upsert_farmer_async() and Database.upsert_buyer_async(),
and loaded from DB on GET requests — not from in-memory dicts.
"""

from backend.repositories.user_repository import UserRepository
from fastapi import APIRouter, Depends, HTTPException
from backend.services.security import get_current_user
from backend.schemas.profile_model import UserProfileUpdate, FarmerProfileCreate, BuyerProfileCreate, ProfileResponse
from database.db import Database
from backend.db.session import AsyncSessionLocal
from backend.db.models.schema import DBFarmer, DBBuyer
from sqlalchemy import select

router = APIRouter(tags=["Profiles"])


async def _get_farmer_profile(user_id: str) -> dict | None:
    """Load farmer extended profile from PostgreSQL by user_id (id field)."""
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(DBFarmer).where(DBFarmer.id == user_id))
        row = res.scalars().first()
        if not row:
            return None
        return {
            "id": row.id,
            "name": row.name,
            "contact_number": row.contact_number,
            "location": row.location,
            "village": row.village,
            "taluka": row.taluka,
            "district": row.district,
            "state": row.state,
            "latitude": row.latitude,
            "longitude": row.longitude,
            "language": row.language,
            "farm_size_acres": row.farm_size_acres,
            "farming_type": row.farming_type,
            "preferences": row.preferences,
        }


async def _get_buyer_profile(user_id: str) -> dict | None:
    """Load buyer extended profile from PostgreSQL by user_id."""
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(DBBuyer).where(DBBuyer.user_id == user_id))
        row = res.scalars().first()
        if not row:
            return None
        return {
            "id": row.id,
            "user_id": row.user_id,
            "buyer_name": row.buyer_name,
            "crop": row.crop,
            "min_price": row.min_price,
            "max_price": row.max_price,
            "quantity": row.quantity,
            "location": row.location,
            "urgency": row.urgency,
            "neg_mode": row.neg_mode,
            "strategy": row.strategy,
        }


@router.get("/me")
async def get_my_profile(current_user: dict = Depends(get_current_user)):
    """Return the authenticated user's full profile from PostgreSQL."""
    uid = current_user["sub"]
    user = await UserRepository.get_by_id(uid)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    farmer_profile = await _get_farmer_profile(uid)
    buyer_profile = await _get_buyer_profile(uid)

    return {
        "success": True,
        "data": {
            **user,
            "farmer_profile": farmer_profile,
            "buyer_profile": buyer_profile,
        },
    }


@router.patch("/me")
async def update_my_profile(
    payload: UserProfileUpdate,
    current_user: dict = Depends(get_current_user),
):
    """Update the authenticated user's profile fields."""
    uid = current_user["sub"]
    user = await UserRepository.get_by_id(uid)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    updates = {k: v for k, v in payload.dict().items() if v is not None}
    user.update(updates)
    await UserRepository.upsert(user)

    return {"success": True, "message": "Profile updated.", "data": user}


@router.get("/{user_id}")
async def get_user_profile(user_id: str, current_user: dict = Depends(get_current_user)):
    """Return another user's public profile from PostgreSQL."""
    user = await UserRepository.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    farmer_profile = await _get_farmer_profile(user_id)
    buyer_profile = await _get_buyer_profile(user_id)

    return {
        "success": True,
        "data": {
            "user_id": user_id,
            "name": user.get("name"),
            "role": user.get("role"),
            "location": user.get("location"),
            "trust_score": user.get("trust_score", 4.0),
            "verification_status": user.get("verification_status", "PENDING"),
            "farmer_profile": farmer_profile,
            "buyer_profile": buyer_profile,
        },
    }


@router.post("/farmer")
async def create_farmer_profile(
    payload: FarmerProfileCreate,
    current_user: dict = Depends(get_current_user),
):
    """Create or update extended farmer profile — persisted to PostgreSQL."""
    uid = current_user["sub"]
    import datetime
    profile = {
        **payload.dict(),
        "id": uid,
        "created_at": datetime.datetime.utcnow().isoformat()
    }
    # Persist to PostgreSQL
    await Database.upsert_farmer_async(profile)
    return {"success": True, "data": profile}


@router.post("/buyer")
async def create_buyer_profile(
    payload: BuyerProfileCreate,
    current_user: dict = Depends(get_current_user),
):
    """Create or update extended buyer profile — persisted to PostgreSQL."""
    uid = current_user["sub"]
    import datetime
    profile = {
        **payload.dict(),
        "id": uid,
        "user_id": uid,
        "created_at": datetime.datetime.utcnow().isoformat()
    }
    # Persist to PostgreSQL
    await Database.upsert_buyer_async(profile)
    return {"success": True, "data": profile}
