"""
backend/routes/matching_routes.py

Matching Engine API endpoints.
FR-5: AI-Powered Farmer-Buyer Matching
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from backend.services.security import get_current_user
from backend.services.matching_service import match_listing_to_buyers, match_requirement_to_listings

router = APIRouter(tags=["Matching"])


class MatchListingRequest(BaseModel):
    listing_id: str = None
    crop: str
    quantity: float = Field(..., gt=0)
    min_price: float = Field(..., gt=0)
    location: str
    spoilage_days: int = Field(7, ge=1)
    quality: str = "A"


class MatchRequirementRequest(BaseModel):
    requirement_id: str | None = None
    crop: str | None = None
    quantity: float | None = Field(None, gt=0)
    target_price: float | None = Field(None, gt=0)
    max_price: float | None = None
    budget: float | None = Field(None, gt=0)
    location: str | None = None


@router.post("/listing-to-buyers")
async def match_listing(
    payload: MatchListingRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Find and rank all buyer requirements compatible with a crop listing.
    Returns scored matches sorted by compatibility.
    """
    listing = payload.dict()
    matches = await match_listing_to_buyers(listing)

    return {
        "success": True,
        "crop": payload.crop,
        "listing_location": payload.location,
        "total_matches": len(matches),
        "grade_a_matches": len([m for m in matches if m["match_grade"] == "A"]),
        "data": matches,
    }


@router.post("/requirement-to-listings")
async def match_requirement(
    payload: MatchRequirementRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Find and rank all crop listings that satisfy a buyer requirement.
    Uses stored PostgreSQL requirement record when requirement_id is provided.
    """
    from database.db import Database
    if payload.requirement_id:
        buyers = await Database.list_buyers_async()
        req = next((r for r in buyers if (r.get("id") == payload.requirement_id or r.get("requirement_id") == payload.requirement_id) and (r.get("kind") == "requirement" or str(r.get("id", "")).startswith("req_"))), None)
        if not req:
            raise HTTPException(status_code=404, detail=f"Requirement '{payload.requirement_id}' not found")
        
        user_id = current_user.get("sub") or current_user.get("id")
        role = current_user.get("role")
        if req.get("user_id") and req.get("user_id") != user_id and role != "admin":
            raise HTTPException(status_code=403, detail="You do not own this requirement")
            
        requirement = req
    else:
        if not payload.crop or not payload.quantity or not payload.target_price:
            raise HTTPException(status_code=422, detail="Missing required procurement parameters (crop, quantity, target_price).")
        requirement = payload.dict()

    matches = await match_requirement_to_listings(requirement)

    return {
        "success": True,
        "crop": requirement.get("crop"),
        "buyer_location": requirement.get("location", ""),
        "total_matches": len(matches),
        "grade_a_matches": len([m for m in matches if m.get("match_grade") == "A"]),
        "data": matches,
    }



@router.get("/auto/{listing_id}")
async def auto_match(
    listing_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Automatically match a saved crop listing to buyers using its stored data.
    """
    from database.db import Database
    listing = Database.produce.get(listing_id)
    if not listing:
        # Try listing from produce table
        produce = await Database.list_produce_async()
        listing = next((p for p in produce if p.get("id") == listing_id), None)

    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")

    matches = await match_listing_to_buyers(listing)
    return {
        "success": True,
        "listing_id": listing_id,
        "crop": listing.get("crop"),
        "total_matches": len(matches),
        "data": matches,
    }

