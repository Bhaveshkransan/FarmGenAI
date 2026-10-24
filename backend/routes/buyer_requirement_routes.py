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

    # Initialize Phase 1 Buyer Workflow Memory
    try:
        from backend.services.buyer_workflow_service import buyer_workflow_service
        services = data.get("selected_services") or {}
        if data.get("transport_required") or data.get("transportRequired"):
            services["transport"] = True
        if data.get("warehouse_required") or data.get("storageRequired"):
            services["warehouse"] = True
        if data.get("processor_required") or data.get("processorRequired"):
            services["processor"] = True

        await buyer_workflow_service.initialize_workflow(
            requirement_id=req_id,
            buyer_id=req["user_id"],
            crop=req["crop"],
            quantity=qty,
            quality=grade,
            pickup_location=data.get("pickup_location") or "Maharashtra",
            delivery_location=loc,
            delivery_deadline_hours=float(data.get("delivery_days", 7)) * 24.0,
            selected_services=services,
            selected_agents=data.get("selected_agents")
        )
    except Exception:
        pass

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


async def _get_and_authorize_requirement(
    requirement_id: str,
    current_user: dict,
) -> tuple[Optional[dict], Optional[dict]]:
    """
    Validates existence of the requirement / workflow state and ensures the authenticated
    user is the legitimate owner (or admin).
    Returns (req, wf_state).
    Raises:
      404 if requirement / workflow not found
      403 if authenticated user is not the owner (and not admin)
    """
    from backend.services.buyer_workflow_service import buyer_workflow_service

    # 1. Fetch requirement from Database
    buyers = await Database.list_buyers_async()
    req = next(
        (r for r in buyers if (r.get("id") == requirement_id or r.get("requirement_id") == requirement_id)
         and (r.get("kind") == "requirement" or str(r.get("id", "")).startswith("req_"))),
        None
    )

    # 2. Fetch workflow state if available
    state = await buyer_workflow_service.get_workflow_state(requirement_id=requirement_id)

    # 3. If neither exists, requirement not found
    if not req and not state:
        raise HTTPException(status_code=404, detail="Requirement not found")

    # 4. Resolve owner ID
    owner_id = None
    if req and req.get("user_id"):
        owner_id = req.get("user_id")
    elif state and state.get("buyer_id"):
        owner_id = state.get("buyer_id")

    # 5. Check ownership against current user
    user_id = current_user.get("sub") or current_user.get("id")
    role = current_user.get("role")
    if owner_id and owner_id != user_id and role != "admin":
        raise HTTPException(status_code=403, detail="You do not own this requirement")

    return req, state


@router.post("/{requirement_id}/orchestrate")
async def orchestrate_requirement_negotiation(
    requirement_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Triggers autonomous top-5 parallel multi-seller negotiation for an existing buyer requirement.
    """
    req, _ = await _get_and_authorize_requirement(requirement_id, current_user)
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


@router.get("/{requirement_id}/workflow")
async def get_requirement_workflow(
    requirement_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Retrieve the authoritative Buyer workflow memory and valid next actions."""
    from backend.services.buyer_workflow_service import buyer_workflow_service
    req, state = await _get_and_authorize_requirement(requirement_id, current_user)
    if not state:
        # If not initialized, initialize from requirement
        if not req:
            raise HTTPException(status_code=404, detail="Requirement not found")
        state = await buyer_workflow_service.initialize_workflow(
            requirement_id=requirement_id,
            buyer_id=req.get("user_id", current_user.get("sub")),
            crop=req.get("crop", "Produce"),
            quantity=float(req.get("quantity", 500)),
            quality=req.get("quality_grade", "Grade A"),
            delivery_location=req.get("location", "Maharashtra")
        )

    valid_actions = buyer_workflow_service.get_valid_next_actions(state)
    return {
        "success": True,
        "workflow": state,
        "valid_next_actions": valid_actions
    }


@router.post("/{requirement_id}/workflow/step")
async def step_requirement_workflow(
    requirement_id: str,
    payload: dict = None,
    current_user: dict = Depends(get_current_user),
):
    """Executes the deterministic policy step for this requirement workflow."""
    req, state = await _get_and_authorize_requirement(requirement_id, current_user)
    from backend.services.buyer_workflow_service import buyer_workflow_service
    action_override = payload.get("action") if isinstance(payload, dict) else None
    try:
        updated_state = await buyer_workflow_service.step_workflow(
            requirement_id=requirement_id,
            action_override=action_override
        )
        valid_actions = buyer_workflow_service.get_valid_next_actions(updated_state)
        return {
            "success": True,
            "workflow": updated_state,
            "valid_next_actions": valid_actions
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{requirement_id}/workflow/reevaluate")
async def reevaluate_requirement_workflow(
    requirement_id: str,
    payload: dict = None,
    current_user: dict = Depends(get_current_user),
):
    """Re-evaluates requirement workflow state against authoritative deal verification."""
    req, state = await _get_and_authorize_requirement(requirement_id, current_user)
    if not state:
        raise HTTPException(status_code=404, detail="Requirement workflow not found")

    from backend.services.buyer_workflow_service import buyer_workflow_service
    state = await buyer_workflow_service.revalidate_deal_state(state)
    valid_actions = buyer_workflow_service.get_valid_next_actions(state)
    return {
        "success": True,
        "workflow": state,
        "valid_next_actions": valid_actions
    }


@router.post("/{requirement_id}/workflow/agents/select")
async def select_requirement_agents(
    requirement_id: str,
    payload: dict,
    current_user: dict = Depends(get_current_user),
):
    """
    Authoritative endpoint to update selected downstream agents for a requirement workflow.
    Example payload: { "selected_agents": ["TRANSPORT", "WAREHOUSE", "PROCESSOR"] }
    """
    req, state = await _get_and_authorize_requirement(requirement_id, current_user)
    from backend.services.buyer_workflow_service import buyer_workflow_service
    selected_agents = payload.get("selected_agents") or []
    if not isinstance(selected_agents, list):
        raise HTTPException(status_code=400, detail="'selected_agents' must be a list of strings")
    try:
        updated = await buyer_workflow_service.update_selected_agents(requirement_id, selected_agents)
        valid_actions = buyer_workflow_service.get_valid_next_actions(updated)
        return {
            "success": True,
            "workflow": updated,
            "valid_next_actions": valid_actions
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{requirement_id}/workflow/execute")
async def execute_full_requirement_workflow(
    requirement_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Executes the entire multi-agent supply chain pipeline sequentially across all selected agents.
    """
    req, state = await _get_and_authorize_requirement(requirement_id, current_user)
    from backend.services.buyer_workflow_service import buyer_workflow_service
    try:
        updated = await buyer_workflow_service.execute_full_workflow(requirement_id)
        valid_actions = buyer_workflow_service.get_valid_next_actions(updated)
        return {
            "success": True,
            "workflow": updated,
            "valid_next_actions": valid_actions
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/{requirement_id}/workflow/status")
async def get_requirement_workflow_status(
    requirement_id: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Returns current high-level orchestration status, agent completion status, and final plan.
    """
    req, state = await _get_and_authorize_requirement(requirement_id, current_user)
    if not state:
        raise HTTPException(status_code=404, detail="Requirement workflow not found")

    from backend.services.buyer_workflow_service import buyer_workflow_service
    valid_actions = buyer_workflow_service.get_valid_next_actions(state)
    return {
        "success": True,
        "requirement_id": requirement_id,
        "workflow_id": state.get("workflow_id"),
        "workflow_status": state.get("workflow_status"),
        "selected_agents": state.get("selected_agents", []),
        "completed_agents": state.get("completed_agents", []),
        "failed_agents": state.get("failed_agents", []),
        "pending_agents": state.get("pending_agents", []),
        "farmer_deal_valid": bool(state.get("farmer_deal", {}).get("valid")),
        "agent_outcomes": state.get("agent_outcomes", {}),
        "final_plan": state.get("final_plan"),
        "valid_next_actions": valid_actions
    }


@router.get("/{requirement_id}/workflow/agents/{agent}")
async def get_requirement_agent_outcome(
    requirement_id: str,
    agent: str,
    current_user: dict = Depends(get_current_user),
):
    """
    Retrieves the authoritative AgentOutcome envelope for a specific executed agent.
    """
    req, state = await _get_and_authorize_requirement(requirement_id, current_user)
    if not state:
        raise HTTPException(status_code=404, detail="Requirement workflow not found")

    target_agent = agent.strip().upper()
    outcome = state.get("agent_outcomes", {}).get(target_agent)
    if not outcome:
        raise HTTPException(
            status_code=404,
            detail=f"Agent '{target_agent}' outcome not found for requirement '{requirement_id}'. Selected: {state.get('selected_agents')}"
        )

    return {
        "success": True,
        "agent": target_agent,
        "outcome": outcome
    }



