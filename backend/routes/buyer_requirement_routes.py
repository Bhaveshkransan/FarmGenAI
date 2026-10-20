"""
backend/routes/buyer_requirement_routes.py

Buyer requirement CRUD — buyers post what they need.
FR-4: Buyer Requirement Posting
"""

import uuid
import re
from datetime import datetime, timezone
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field, validator
from backend.services.security import get_current_user, get_current_user_optional
from database.db import Database

router = APIRouter(tags=["Buyer Requirements"])

MAHARASHTRA_DISTRICTS_LOWER = [
    "maharashtra", "all maharashtra", "any", "nashik", "pune", "mumbai", "nagpur", "aurangabad",
    "chhatrapati sambhajinagar", "sambhajinagar", "solapur", "kolhapur", "ahmednagar", "satara",
    "sangli", "amravati", "thane", "kalyan", "jalgaon", "latur", "dhule", "nanded", "akola",
    "chandrapur", "parbhani", "buldhana", "yavatmal", "ratnagiri", "sindhudurg", "beed", "jalna",
    "raigad", "palghar", "osmanabad", "dharashiv", "wardha", "bhandara", "gondia", "gadchiroli",
    "hingoli", "washim", "navi mumbai", "panvel", "baramati", "shirur", "manchar", "dindori",
    "lasalgaon", "pimpalgaon", "yeola", "malegaon", "sangamner", "kopargaon", "shrirampur"
]


class BuyerRequirementCreate(BaseModel):
    crop: str = Field(..., example="Wheat")
    quantity: float = Field(..., gt=0, example=1000.0)
    target_price: float = Field(None, example=22.0)
    max_price: float = Field(None, example=26.0)
    location: str = Field(None, example="Pune")
    budget: float = Field(None, example=30000.0)
    delivery_days: int = Field(7, ge=1, example=7)
    quality_grade: str = Field("A", example="A")
    notes: str = Field("", example="Prefer certified organic")
    # Frontend form aliases
    maxBudget: Optional[float] = None
    preferredLocation: Optional[str] = None
    quality: Optional[str] = None
    deliveryDate: Optional[str] = None
    transportRequired: Optional[bool] = None
    storageRequired: Optional[bool] = None

    @validator("crop")
    def validate_crop(cls, v):
        if not v or not str(v).strip():
            raise ValueError("Crop name is required.")
        from shared.crop_catalog import validate_buyer_crop
        try:
            return validate_buyer_crop(str(v).strip())
        except ValueError as e:
            raise ValueError(str(e))

    @validator("location", "preferredLocation", pre=True, always=True)
    def validate_location(cls, v):
        if not v or not str(v).strip():
            return "Maharashtra"
        clean = str(v).strip().lower()
        if clean in ["any", "all", "all maharashtra"]:
            return "All Maharashtra"
        if not any(dist in clean for dist in MAHARASHTRA_DISTRICTS_LOWER):
            raise ValueError(
                f"AgriNegotiator procurement is strictly restricted to Maharashtra mandis & districts. "
                f"'{v}' is outside our operational service area."
            )
        return str(v).strip().title()

    @validator("deliveryDate", pre=True, always=True)
    def validate_delivery_date(cls, v):
        if not v or not str(v).strip():
            return None
        v_clean = str(v).strip()
        try:
            target_d = datetime.strptime(v_clean.split("T")[0], "%Y-%m-%d").date()
            today = datetime.now(timezone.utc).date()
            if target_d < today:
                raise ValueError("Delivery deadline cannot be in the past.")
        except ValueError as err:
            if "past" in str(err):
                raise
            raise ValueError("Invalid delivery deadline date format. Expected YYYY-MM-DD.")
        return v_clean


class BuyerRequirementUpdate(BaseModel):
    quantity: float = None
    target_price: float = None
    max_price: float = None
    budget: float = None
    status: str = None   # "ACTIVE" | "FULFILLED" | "CANCELLED"
    notes: str = None


from shared.crop_catalog import normalize_crop_name
from backend.services.matching_service import match_requirement_to_listings


def crops_match(req_c: str, prod_c: str) -> bool:
    norm_r = normalize_crop_name(req_c)
    norm_p = normalize_crop_name(prod_c)
    if norm_r and norm_p:
        return norm_r == norm_p
    if not norm_r and not norm_p:
        r = (req_c or "").lower().strip()
        p = (prod_c or "").lower().strip()
        return bool(r and p and r == p)
    return False


@router.get("")
@router.get("/")
async def list_requirements(
    crop: str = None,
    location: str = None,
    current_user: Optional[dict] = Depends(get_current_user_optional),
):
    """Return all active buyer requirements, optionally filtered."""
    buyers = await Database.list_buyers_async()
    reqs = [
        r for r in buyers 
        if (r.get("kind") == "requirement" or str(r.get("id", "")).startswith("req_"))
        and r.get("crop") and str(r.get("crop")).strip()
        and (r.get("quantity") or 0) > 0
    ]
    if crop:
        reqs = [r for r in reqs if crops_match(crop, str(r.get("crop", "")))]
    if location:
        reqs = [r for r in reqs if str(r.get("location", "")).lower() == location.lower()]
    active = [r for r in reqs if r.get("status") == "ACTIVE"]
    return {"success": True, "data": active, "count": len(active)}

@router.get("/me")
async def get_my_requirements(current_user: dict = Depends(get_current_user)):
    """Return buyer requirements for the logged in user."""
    buyers = await Database.list_buyers_async()
    my_reqs = [
        r for r in buyers 
        if (r.get("kind") == "requirement" or str(r.get("id", "")).startswith("req_"))
        and r.get("user_id") == current_user["sub"]
        and r.get("crop") and str(r.get("crop")).strip()
        and (r.get("quantity") or 0) > 0
    ]
    return {"success": True, "data": my_reqs, "count": len(my_reqs)}

@router.get("/{requirement_id}/matches")
async def get_requirement_matches(
    requirement_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Find matching produce listings for a specific buyer requirement using centralized matching service."""
    buyers = await Database.list_buyers_async()
    req = next((r for r in buyers if (r.get("id") == requirement_id or r.get("requirement_id") == requirement_id) and (r.get("kind") == "requirement" or str(r.get("id", "")).startswith("req_"))), None)
    if not req:
        raise HTTPException(status_code=404, detail="Requirement not found")
    
    user_id = current_user.get("sub") or current_user.get("id")
    role = current_user.get("role")
    if req.get("user_id") and req.get("user_id") != user_id and role != "admin":
        raise HTTPException(status_code=403, detail="You do not own this requirement")

    matches = await match_requirement_to_listings(req)
    return {
        "success": True, 
        "requirement": req, 
        "data": matches, 
        "count": len(matches)
    }


@router.get("/{requirement_id}")
async def get_requirement(requirement_id: str, current_user: dict = Depends(get_current_user)):
    """Return a specific buyer requirement."""
    buyers = await Database.list_buyers_async()
    req = next((r for r in buyers if r.get("id") == requirement_id and (r.get("kind") == "requirement" or str(r.get("id", "")).startswith("req_"))), None)
    if not req:
        raise HTTPException(status_code=404, detail="Requirement not found")
    return {"success": True, "data": req}


@router.post("")
@router.post("/")
async def create_requirement(
    payload: BuyerRequirementCreate,
    current_user: Optional[dict] = Depends(get_current_user_optional),
):
    """Post a new buyer requirement."""
    req_id = f"req_{str(uuid.uuid4())[:8]}"
    data = payload.dict()
    user_info = current_user or {"sub": "buyer_enterprise", "name": "Buyer Enterprise", "role": "buyer"}
    
    # Normalize fields across frontend schemas
    loc = data.get("location") or data.get("preferredLocation") or "Maharashtra"
    max_p = data.get("max_price") or data.get("maxBudget") or 25.0
    target_p = data.get("target_price") or data.get("maxBudget") or max_p
    qty = float(data.get("quantity", 500))
    bgt = data.get("budget") or (qty * float(max_p))
    grade = data.get("quality_grade") or data.get("quality") or "A"
    
    req = {
        "id": req_id,
        "requirement_id": req_id,
        "kind": "requirement",
        "user_id": user_info.get("sub", "buyer_enterprise"),
        "buyer_name": user_info.get("name") or user_info.get("businessName") or "Buyer Enterprise",
        "status": "ACTIVE",
        "crop": data.get("crop", "Produce"),
        "quantity": qty,
        "target_price": float(target_p),
        "max_price": float(max_p),
        "budget": float(bgt),
        "location": loc,
        "quality_grade": grade,
        "quality": grade,
        "created_at": datetime.now(timezone.utc).isoformat(),
        **data,
    }
    req["location"] = loc
    req["target_price"] = float(target_p)
    req["max_price"] = float(max_p)
    req["budget"] = float(bgt)
    req["quality_grade"] = grade

    await Database.upsert_buyer_async(req)
    return {"success": True, "data": req, "requirement_id": req_id}


@router.patch("/{requirement_id}")
async def update_requirement(
    requirement_id: str,
    payload: BuyerRequirementUpdate,
    current_user: dict = Depends(get_current_user),
):
    """Update an existing buyer requirement."""
    buyers = await Database.list_buyers_async()
    req = next((r for r in buyers if r.get("id") == requirement_id and r.get("kind") == "requirement"), None)
    if not req:
        raise HTTPException(status_code=404, detail="Requirement not found")
    if req["user_id"] != current_user["sub"]:
        raise HTTPException(status_code=403, detail="You do not own this requirement")

    updates = {k: v for k, v in payload.dict().items() if v is not None}
    req.update(updates)
    req["updated_at"] = datetime.now(timezone.utc).isoformat()
    await Database.upsert_buyer_async(req)
    return {"success": True, "data": req}


@router.delete("/{requirement_id}")
async def cancel_requirement(
    requirement_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Cancel a buyer requirement."""
    buyers = await Database.list_buyers_async()
    req = next((r for r in buyers if r.get("id") == requirement_id and r.get("kind") == "requirement"), None)
    if not req:
        raise HTTPException(status_code=404, detail="Requirement not found")
    if req["user_id"] != current_user["sub"] and current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="You do not own this requirement")

    req["status"] = "CANCELLED"
    await Database.upsert_buyer_async(req)
    return {"success": True, "message": "Requirement cancelled."}


@router.post("/{requirement_id}/orchestrate")
async def orchestrate_requirement_negotiation(
    requirement_id: str,
    current_user: Optional[dict] = Depends(get_current_user_optional),
):
    """
    Triggers autonomous top-5 parallel multi-seller negotiation for an existing buyer requirement.
    """
    buyers = await Database.list_buyers_async()
    req = next((r for r in buyers if (r.get("id") == requirement_id or r.get("requirement_id") == requirement_id) and (r.get("kind") == "requirement" or str(r.get("id", "")).startswith("req_"))), None)
    if not req:
        raise HTTPException(status_code=404, detail="Requirement not found")

    from backend.services.buyer_orchestrator import buyer_orchestration_service
    result = await buyer_orchestration_service.orchestrate_negotiation(req)
    return {"success": True, **result}


@router.post("/orchestrate")
async def orchestrate_ad_hoc_negotiation(
    payload: BuyerRequirementCreate,
    current_user: Optional[dict] = Depends(get_current_user_optional),
):
    """
    Executes autonomous top-5 parallel multi-seller negotiation directly for an ad-hoc requirement payload.
    """
    data = payload.dict()
    user_info = current_user or {"sub": "buyer_enterprise", "name": "Buyer Enterprise", "role": "buyer"}
    loc = data.get("location") or data.get("preferredLocation") or "Maharashtra"
    max_p = data.get("max_price") or data.get("maxBudget") or 25.0
    target_p = data.get("target_price") or data.get("maxBudget") or max_p
    qty = float(data.get("quantity", 500))
    bgt = data.get("budget") or (qty * float(max_p))

    req_dict = {
        "crop": data.get("crop", "Soybean"),
        "quantity": qty,
        "target_price": float(target_p),
        "max_price": float(max_p),
        "reservation_price": float(max_p),
        "budget": float(bgt),
        "location": loc,
        "buyer_name": user_info.get("name") or "Buyer Enterprise",
        "user_id": user_info.get("sub", "buyer_enterprise"),
        "persona": data.get("notes") or "bulk_wholesaler",
        "strategy": "balanced",
    }

    from backend.services.buyer_orchestrator import buyer_orchestration_service
    result = await buyer_orchestration_service.orchestrate_negotiation(req_dict)
    return {"success": True, **result}


