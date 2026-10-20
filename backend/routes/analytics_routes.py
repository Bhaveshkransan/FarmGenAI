"""
backend/routes/analytics_routes.py

Dashboard analytics and reporting API endpoints.
"""

from fastapi import APIRouter, Depends
from backend.repositories.user_repository import UserRepository
from backend.services.security import get_current_user, get_current_user_optional
from database.db import Database

router = APIRouter(tags=["Analytics"])


from backend.db.models.schema import DBNegotiation, DBUser
from backend.db.session import AsyncSessionLocal
from sqlalchemy import select

@router.get("/stats")
async def platform_stats(current_user: dict = Depends(get_current_user_optional)):
    """Return aggregated platform statistics for the dashboard."""
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(DBNegotiation))
        all_negs = [row.__dict__ for row in res.scalars().all()]

    total = len(all_negs)
    deals = [n for n in all_negs if n.get("status") == "DEAL"]
    storage = [n for n in all_negs if "STORAGE" in str(n.get("status", ""))]
    processing = [n for n in all_negs if "PROCESSING" in str(n.get("status", ""))]
    compost = [n for n in all_negs if "COMPOST" in str(n.get("status", ""))]
    failed = [n for n in all_negs if n.get("status") in ("FAILED", "REJECT")]

    prices = [n.get("final_price") for n in deals if n.get("final_price")]
    avg_price = round(sum(prices) / len(prices), 2) if prices else 0.0

    success_rate = round((len(deals) / total) * 100, 1) if total > 0 else 0.0

    # Crop distribution
    crop_counts: dict = {}
    for n in all_negs:
        crop = n.get("crop", "Unknown")
        crop_counts[crop] = crop_counts.get(crop, 0) + 1

    return {
        "success": True,
        "data": {
            "total_negotiations": total,
            "successful_deals": len(deals),
            "escalated_storage": len(storage),
            "escalated_processing": len(processing),
            "escalated_compost": len(compost),
            "failed_negotiations": len(failed),
            "success_rate_percent": success_rate,
            "average_deal_price": avg_price,
            "crop_distribution": crop_counts,
        },
    }


@router.get("/history")
async def negotiation_history(
    user_id: str = None,
    current_user: dict = Depends(get_current_user),
):
    """Return negotiation history for the authenticated user or all users."""
    uid = user_id or current_user["sub"]
    records = await Database.get_history_async(uid)
    return {"success": True, "data": records}


@router.get("/leaderboard")
async def trust_leaderboard(current_user: dict = Depends(get_current_user)):
    """Return top-10 users ranked by trust score."""
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(DBUser))
        all_users = [row.__dict__ for row in res.scalars().all()]
        
    ranked = sorted(all_users, key=lambda u: u.get("trust_score", 0), reverse=True)[:10]
    return {
        "success": True,
        "data": [
            {
                "user_id": u["user_id"],
                "name": u.get("name"),
                "role": u.get("role"),
                "trust_score": u.get("trust_score"),
            }
            for u in ranked
        ],
    }

