"""
backend/routes/processor_routes.py

Processor / Value-Added Processing endpoints.
FR-11: Industrial Processing Escalation
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from backend.services.security import get_current_user
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


@router.get("/")
@router.get("")
@router.get("/matching")
async def get_processors(
    crop: str = None,
    current_user: dict = Depends(get_current_user),
):
    """List available industrial processors, optionally filtered by crop."""
    processors = await list_processors(crop=crop)
    return {"success": True, "data": processors, "count": len(processors)}


@router.post("/order")
async def submit_order(
    payload: ProcessingOrderRequest,
    current_user: dict = Depends(get_current_user),
):
    """Submit a crop lot to a processor for value-added processing."""
    try:
        order = await submit_processing_order({
            **payload.dict(),
            "farmer_id": current_user["sub"],
        })
        return {"success": True, "data": order}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/order/{order_id}")
async def get_order(order_id: str, current_user: dict = Depends(get_current_user)):
    """Get a specific processing order."""
    try:
        order = await get_processor_order(order_id)
        return {"success": True, "data": order}
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/orders")
async def my_orders(current_user: dict = Depends(get_current_user)):
    """List all processing orders for the authenticated farmer."""
    uid = current_user["sub"]
    orders = await list_processor_orders(farmer_id=uid)
    return {"success": True, "data": orders, "count": len(orders)}

