"""
backend/routes/processor_routes.py

Processor / Value-Added Processing endpoints.
FR-11: Industrial Processing Escalation
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from backend.services.security import get_current_user_optional
from backend.services.processor_service import (
    list_processors, submit_processing_order, get_processor_order, list_processor_orders
)

router = APIRouter(tags=["Processor"])


class ProcessingOrderRequest(BaseModel):
    negotiation_id: Optional[str] = None
    processor_id: str
    crop: str
    quantity: float = Field(..., gt=0)
    notes: Optional[str] = None
    farmer_id: Optional[str] = None


@router.get("")
@router.get("/")
async def get_processors(
    crop: str = None,
    current_user: dict = Depends(get_current_user_optional),
):
    """List available industrial processors, optionally filtered by crop."""
    processors = await list_processors(crop=crop)
    return {"success": True, "data": processors, "count": len(processors)}


@router.post("/order")
async def submit_order(
    payload: ProcessingOrderRequest,
    current_user: dict = Depends(get_current_user_optional),
):
    """Submit a crop lot to a processor for value-added processing."""
    try:
        user_sub = current_user.get("sub") if current_user else (payload.farmer_id or "usr_buyer_demo")
        order = await submit_processing_order({
            **payload.dict(),
            "farmer_id": user_sub,
        })
        return {"success": True, "data": order, "status": order.get("status", "SUBMITTED"), "order_id": order.get("order_id"), "total_payment": order.get("total_payment")}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/order/{order_id}")
async def get_order(order_id: str, current_user: dict = Depends(get_current_user_optional)):
    """Get a specific processing order."""
    try:
        order = await get_processor_order(order_id)
        return {"success": True, "data": order}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/orders")
async def my_orders(current_user: dict = Depends(get_current_user_optional)):
    """List all processing orders for the authenticated farmer."""
    uid = current_user.get("sub") if current_user else "usr_buyer_demo"
    orders = await list_processor_orders(farmer_id=uid)
    return {"success": True, "data": orders, "count": len(orders)}
