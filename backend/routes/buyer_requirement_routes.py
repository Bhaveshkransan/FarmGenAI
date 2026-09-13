"""
backend/routes/buyer_requirement_routes.py

Buyer requirement CRUD — buyers post what they need.
FR-4: Buyer Requirement Posting
"""

import uuid
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from backend.services.security import get_current_user
from database.db import Database

router = APIRouter(tags=["Buyer Requirements"])


class BuyerRequirementCreate(BaseModel):
    crop: str = Field(..., example="Cotton")
    quantity: float = Field(..., gt=0, example=1000.0)
    target_price: float = Field(..., gt=0, example=65.0)
    max_price: float = Field(None, example=72.0)
    location: str = Field(..., example="Amravati")
    budget: float = Field(..., gt=0, example=75000.0)
    delivery_days: int = Field(7, ge=1, example=7)
    quality_grade: str = Field("A", example="A")
    notes: str = Field("", example="Prefer certified organic")


class BuyerRequirementUpdate(BaseModel):
    quantity: float = None
    target_price: float = None
    max_price: float = None
    budget: float = None
    status: str = None   # "ACTIVE" | "FULFILLED" | "CANCELLED"
    notes: str = None


@router.get("/")
async def list_requirements(
    crop: str = None,
    location: str = None,
    current_user: dict = Depends(get_current_user),
):
    """Return all active buyer requirements, optionally filtered."""
    buyers = await Database.list_buyers_async()
    reqs = [r for r in buyers if r.get("kind") == "requirement"]
    if crop:
        reqs = [r for r in reqs if r.get("crop", "").lower() == crop.lower()]
    if location:
        reqs = [r for r in reqs if r.get("location", "").lower() == location.lower()]
    active = [r for r in reqs if r.get("status") == "ACTIVE"]
    return {"success": True, "data": active, "count": len(active)}

@router.get("/me")
async def get_my_requirements(current_user: dict = Depends(get_current_user)):
    """Return buyer requirements for the logged in user."""
    buyers = await Database.list_buyers_async()
    my_reqs = [r for r in buyers if r.get("kind") == "requirement" and r.get("user_id") == current_user["sub"]]
    return {"success": True, "data": my_reqs, "count": len(my_reqs)}

@router.get("/{requirement_id}")
async def get_requirement(requirement_id: str, current_user: dict = Depends(get_current_user)):
    """Return a specific buyer requirement."""
    buyers = await Database.list_buyers_async()
    req = next((r for r in buyers if r.get("id") == requirement_id and r.get("kind") == "requirement"), None)
    if not req:
        raise HTTPException(status_code=404, detail="Requirement not found")
    return {"success": True, "data": req}


@router.post("/")
async def create_requirement(
    payload: BuyerRequirementCreate,
    current_user: dict = Depends(get_current_user),
):
    """Post a new buyer requirement."""
    req_id = f"req_{str(uuid.uuid4())[:8]}"
    req = {
        "id": req_id,
        "kind": "requirement",
        "user_id": current_user["sub"],
        "buyer_name": current_user.get("name", "Buyer"),
        "status": "ACTIVE",
        "created_at": datetime.now(timezone.utc).isoformat(),
        **payload.dict(),
    }
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

