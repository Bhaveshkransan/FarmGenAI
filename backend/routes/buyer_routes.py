from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from backend.api.v1.dependencies import get_db
from backend.services.negotiation_service import create_buyer_offer, list_buyer_offers, list_buyers
from ..schemas.buyer_model import BuyerOfferCreate
from backend.core.security import get_current_user, require_role
from backend.services.buyer_market_service import get_buyer_market_service

router = APIRouter()

@router.get("/")
async def get_buyers(
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db)
):
    return {"buyers": await list_buyers(db=db)}


@router.get("/offers")
async def get_buyer_offers(
    user_id: str | None = None,
    current_user: dict = Depends(require_role("buyer", "admin")),
    db: AsyncSession = Depends(get_db)
):
    return {"offers": await list_buyer_offers(user_id=user_id, db=db)}


@router.post("/offers")
async def add_buyer_offer(
    payload: BuyerOfferCreate,
    current_user: dict = Depends(require_role("buyer", "admin")),
    db: AsyncSession = Depends(get_db)
):
    data = payload.model_dump()
    data["user_id"] = current_user["sub"]
    return await create_buyer_offer(data, db=db)


@router.get("/mandi-comparison")
async def get_mandi_comparison(
    crop: str = Query("Soybean", description="Crop name among the 7 canonical Maharashtra crops"),
    buyer_location: str = Query("Pune", description="Buyer location / processing center")
):
    """
    Returns real APMC Mandi price & inbound logistics comparison (MandiMitra for Buyers).
    """
    svc = get_buyer_market_service()
    return svc.get_mandi_comparison(crop=crop, buyer_location=buyer_location)


@router.get("/price-forecast")
async def get_price_forecast(
    crop: str = Query("Soybean", description="Crop name among the 7 canonical Maharashtra crops"),
    location: str = Query("Pune", description="Target location / APMC")
):
    """
    Returns 7-day ML wholesale price forecast, trend metrics, and strategic buyer advice.
    """
    svc = get_buyer_market_service()
    return svc.get_price_forecast(crop=crop, location=location)


@router.get("/crop-summary")
async def get_crop_summary():
    """
    Returns overview of all 7 canonical crops with live wholesale prices and ML forecast trends.
    """
    svc = get_buyer_market_service()
    return {"crops": svc.get_crop_summary()}
