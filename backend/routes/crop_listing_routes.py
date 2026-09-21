"""
backend/routes/crop_listing_routes.py

Crop listing CRUD — farmers post produce availability.
FR-3: Farmer Crop Listing Management
"""

import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from backend.services.security import get_current_user
from database.db import Database

router = APIRouter(tags=["Crop Listings"])


from backend.schemas.produce_model import CropListingCreate, CropListingUpdate


@router.get("/")
async def list_crop_listings(
    crop: str = None,
    location: str = None,
    current_user: dict = Depends(get_current_user),
):
    """Return all active crop listings, optionally filtered."""
    listings = await Database.list_produce_async()
    if crop:
        listings = [l for l in listings if l.get("crop", "").lower() == crop.lower()]
    if location:
        listings = [l for l in listings if l.get("location", "").lower() == location.lower()]
    return {"success": True, "data": listings, "count": len(listings)}


@router.get("/me")
async def get_my_crop_listings(current_user: dict = Depends(get_current_user)):
    """Return crop listings for the logged in user."""
    listings = await Database.list_produce_async()
    user_sub = current_user.get("sub")
    my_listings = [l for l in listings if l.get("user_id") == user_sub]
    if not my_listings:
        my_listings = listings
    return {"success": True, "data": my_listings, "count": len(my_listings)}



@router.get("/{listing_id}")
async def get_crop_listing(listing_id: str, current_user: dict = Depends(get_current_user)):
    """Return a specific crop listing."""
    listing = await Database.get_produce_async(listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    return {"success": True, "data": listing}


@router.post("/")
async def create_crop_listing(
    payload: CropListingCreate,
    current_user: dict = Depends(get_current_user),
):
    """Create a new crop listing for the authenticated farmer."""
    listing_id = str(uuid.uuid4())[:12]
    listing = {
        "id": listing_id,
        "user_id": current_user["sub"],
        "farmer_name": current_user.get("name", "Farmer"),
        "status": "ACTIVE",
        "created_at": datetime.now(timezone.utc).isoformat(),
        **payload.dict(),
    }
    await Database.upsert_produce_async(listing)
    return {"success": True, "data": listing, "listing_id": listing_id}


@router.patch("/{listing_id}")
async def update_crop_listing(
    listing_id: str,
    payload: CropListingUpdate,
    current_user: dict = Depends(get_current_user),
):
    """Update an existing crop listing. Only the owner can update."""
    listing = await Database.get_produce_async(listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    if listing["user_id"] != current_user["sub"]:
        raise HTTPException(status_code=403, detail="You do not own this listing")

    updates = {k: v for k, v in payload.dict().items() if v is not None}
    listing.update(updates)
    listing["updated_at"] = datetime.now(timezone.utc).isoformat()
    await Database.upsert_produce_async(listing)
    return {"success": True, "data": listing}


@router.delete("/{listing_id}")
async def delete_crop_listing(
    listing_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Delete (expire) a crop listing."""
    listing = await Database.get_produce_async(listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    if listing["user_id"] != current_user["sub"] and current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="You do not own this listing")

    await Database.delete_produce_async(listing_id)
    return {"success": True, "message": "Listing marked as expired."}

