"""
backend/routes/profile_routes.py

User profile management endpoints.
FR-1: User Registration & Profile Management
"""

from backend.repositories.user_repository import UserRepository
from fastapi import APIRouter, Depends, HTTPException
from backend.services.security import get_current_user
from backend.schemas.profile_model import UserProfileUpdate, FarmerProfileCreate, BuyerProfileCreate, ProfileResponse
from database.db import Database

router = APIRouter(tags=["Profiles"])

# In-memory extended profile store
_farmer_profiles: dict = {}
_buyer_profiles: dict = {}


@router.get("/me")
async def get_my_profile(current_user: dict = Depends(get_current_user)):
    """Return the authenticated user's full profile."""
    uid = current_user["sub"]
    user = await UserRepository.get_by_id(uid)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return {
        "success": True,
        "data": {
            **user,
            "farmer_profile": _farmer_profiles.get(uid),
            "buyer_profile": _buyer_profiles.get(uid),
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
    """Return another user's public profile."""
    user = await UserRepository.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Return limited public view
    return {
        "success": True,
        "data": {
            "user_id": user_id,
            "name": user.get("name"),
            "role": user.get("role"),
            "location": user.get("location"),
            "trust_score": user.get("trust_score", 4.0),
            "verification_status": user.get("verification_status", "PENDING"),
            "farmer_profile": _farmer_profiles.get(user_id),
            "buyer_profile": _buyer_profiles.get(user_id),
        },
    }


@router.post("/farmer")
async def create_farmer_profile(
    payload: FarmerProfileCreate,
    current_user: dict = Depends(get_current_user),
):
    """Create or update extended farmer profile."""
    uid = current_user["sub"]
    profile = {**payload.dict(), "id": uid, "created_at": __import__("datetime").datetime.utcnow().isoformat()}
    _farmer_profiles[uid] = profile
    # Persist to database
    await Database.upsert_farmer_async(profile)
    return {"success": True, "data": profile}


@router.post("/buyer")
async def create_buyer_profile(
    payload: BuyerProfileCreate,
    current_user: dict = Depends(get_current_user),
):
    """Create or update extended buyer profile."""
    uid = current_user["sub"]
    profile = {**payload.dict(), "id": uid, "created_at": __import__("datetime").datetime.utcnow().isoformat()}
    _buyer_profiles[uid] = profile
    # Persist to database
    await Database.upsert_buyer_async(profile)
    return {"success": True, "data": profile}
