"""
backend/routes/crop_listing_routes.py

Crop listing CRUD — farmers post produce availability.
FR-3: Farmer Crop Listing Management
"""

import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from backend.services.security import get_current_user, get_current_user_optional
from database.db import Database
from backend.core.constants import validate_crop

router = APIRouter(tags=["Crop Listings"])


from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field, root_validator

class CropListingCreate(BaseModel):
    crop: str = Field(..., example="Tomato")
    crop_category: Optional[str] = Field(None, example="Vegetables")
    variety: str = Field(..., example="Nashik Red")
    grade: str = Field(..., example="A")
    quantity: float = Field(..., gt=0, example=500.0)
    unit: str = Field("kg", example="kg")
    min_sale_quantity: float = Field(..., gt=0, example=50.0)
    expected_price: float = Field(..., gt=0, example=20.0)
    min_price: float = Field(..., gt=0, example=18.0)
    price_unit: str = Field("per_kg", example="per_kg")
    quality_info: Optional[Dict[str, Any]] = None
    harvest_date: Optional[str] = None
    availability_date: Optional[str] = None
    preferred_selling_date: Optional[str] = None
    shelf_life: int = Field(..., ge=1, example=7)
    location: str = Field(..., example="Nashik")
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    storage_info: Optional[Dict[str, Any]] = None
    processing_info: Optional[Dict[str, Any]] = None
    transport_reqs: Optional[Dict[str, Any]] = None
    selected_services: Optional[Dict[str, Any]] = None
    images: Optional[List[str]] = None
    description: str = Field("", example="Organic grade A")

    @root_validator(pre=False, skip_on_failure=True)
    def validate_logic(cls, values):
        qty = values.get('quantity')
        min_qty = values.get('min_sale_quantity')
        if qty is not None and min_qty is not None and min_qty > qty:
            raise ValueError('minimum_sale_quantity cannot be greater than available quantity')
        
        min_p = values.get('min_price')
        exp_p = values.get('expected_price')
        if min_p is not None and exp_p is not None and min_p > exp_p:
            raise ValueError('minimum price cannot be greater than expected price')
            
        crop = values.get('crop')
        if crop:
            is_valid, msg = validate_crop(crop)
            if not is_valid:
                raise ValueError(msg)
        
        return values

class CropListingUpdate(BaseModel):
    quantity: float = None
    min_sale_quantity: float = None
    expected_price: float = None
    min_price: float = None
    quality_info: Optional[Dict[str, Any]] = None
    harvest_date: Optional[str] = None
    availability_date: Optional[str] = None
    preferred_selling_date: Optional[str] = None
    shelf_life: int = None
    location: str = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    storage_info: Optional[Dict[str, Any]] = None
    processing_info: Optional[Dict[str, Any]] = None
    transport_reqs: Optional[Dict[str, Any]] = None
    selected_services: Optional[Dict[str, Any]] = None
    images: Optional[List[str]] = None
    description: str = None
    status: str = None  # "ACTIVE" | "SOLD" | "EXPIRED"

    @root_validator(pre=False, skip_on_failure=True)
    def validate_logic(cls, values):
        qty = values.get('quantity')
        min_qty = values.get('min_sale_quantity')
        if qty is not None and min_qty is not None and min_qty > qty:
            raise ValueError('minimum_sale_quantity cannot be greater than available quantity')
        
        min_p = values.get('min_price')
        exp_p = values.get('expected_price')
        if min_p is not None and exp_p is not None and min_p > exp_p:
            raise ValueError('minimum price cannot be greater than expected price')
        
        return values


@router.get("")
@router.get("/")
async def list_crop_listings(
    crop: str = None,
    location: str = None,
    current_user: Optional[dict] = Depends(get_current_user_optional),
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
    my_listings = [l for l in listings if l.get("user_id") == current_user["sub"]]
    return {"success": True, "data": my_listings, "count": len(my_listings)}


@router.get("/{listing_id}")
async def get_crop_listing(listing_id: str, current_user: dict = Depends(get_current_user)):
    """Return a specific crop listing."""
    listing = await Database.get_produce_async(listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
    return {"success": True, "data": listing}


@router.post("")
@router.post("/")
async def create_crop_listing(
    payload: CropListingCreate,
    current_user: dict = Depends(get_current_user),
):
    """Create a new crop listing for the authenticated farmer."""
    listing_id = str(uuid.uuid4())[:12]
    trace_id = f"TRC-LST-{listing_id}"
    listing = {
        "id": listing_id,
        "trace_id": trace_id,
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
    if listing.get("user_id") and listing.get("user_id") != current_user["sub"] and current_user.get("role") != "admin":
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

