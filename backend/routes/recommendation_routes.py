"""
backend/routes/recommendation_routes.py

AI-powered recommendations for farmers and buyers.
Surfaces the best supply chain path and market opportunities.
"""

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from backend.services.security import get_current_user
from database.db import Database
from llm.llm_client import client as llm_client

router = APIRouter(tags=["Recommendations"])


class RecommendationRequest(BaseModel):
    crop: str = "Soybean"
    quantity: float = 1000.0
    min_price: float = 65.0
    location: str = "Latur"
    spoilage_days: int = 180
    market_price: float = 72.0


@router.post("/generate")
async def generate_recommendation(
    req: RecommendationRequest,
    current_user: dict = Depends(get_current_user),
):
    """
    Generate an AI-powered supply chain recommendation for a farmer's produce.
    Falls back to deterministic logic if LLM is unavailable.
    """
    storage_cost = round(1.8 * req.quantity * req.spoilage_days, 2)
    processor_offer = round(req.market_price * 0.8, 2)

    # Score each option
    direct_score = req.market_price * req.quantity
    storage_score = (req.market_price * 1.05) * req.quantity - storage_cost
    process_score = processor_offer * req.quantity

    options = [
        {"type": "Direct Sale", "net_revenue": round(direct_score, 2), "risk": "Low"},
        {"type": "Cold Storage", "net_revenue": round(storage_score, 2), "risk": "Medium"},
        {"type": "Processing", "net_revenue": round(process_score, 2), "risk": "Low"},
    ]
    best = max(options, key=lambda o: o["net_revenue"])

    # Try LLM explanation
    explanation = llm_client.explain_scenarios(
        [
            {"scenario_type": o["type"].lower().replace(" ", "-"), "final_price": req.market_price,
             "score": o["net_revenue"], "status": "PROJECTED"}
            for o in options
        ],
        best["type"].lower().replace(" ", "-"),
    )

    return {
        "success": True,
        "data": {
            "crop": req.crop,
            "location": req.location,
            "options": options,
            "recommended": best,
            "explanation": explanation,
        },
    }


@router.get("/history/{user_id}")
async def user_recommendations(
    user_id: str,
    current_user: dict = Depends(get_current_user),
):
    """Return previous negotiation outcomes to infer recommendations."""
    records = await Database.get_history_async(user_id)
    deals = [r for r in records if r.get("status") == "DEAL"]
    return {
        "success": True,
        "data": {
            "user_id": user_id,
            "total_negotiations": len(records),
            "successful_deals": len(deals),
            "history": records[-10:],
        },
    }

