"""
backend/services/dashboard_service.py

Dashboard Statistics Service — FR-13: Analytics & Dashboard

Aggregates real-time platform metrics for admin and user dashboards.
All data is sourced from PostgreSQL via SQLAlchemy — no in-memory dicts.
"""

from backend.repositories.user_repository import UserRepository
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, List
from backend.db.session import AsyncSessionLocal
from backend.db.models.schema import DBNegotiation, DBUser, DBHistory
from sqlalchemy import select, func

logger = logging.getLogger("DashboardService")


async def get_platform_summary() -> Dict[str, Any]:
    """
    Aggregate-level platform statistics (admin view).
    Reads directly from PostgreSQL — accurate after any server restart.
    """
    async with AsyncSessionLocal() as session:
        # ── Fetch all negotiations ─────────────────────────
        res = await session.execute(select(DBNegotiation))
        all_negs = [r.__dict__ for r in res.scalars().all()]

        # ── Fetch all users ────────────────────────────────
        res_u = await session.execute(select(DBUser))
        all_users = [u.__dict__ for u in res_u.scalars().all()]

    total_negs = len(all_negs)
    deals = [n for n in all_negs if n.get("status") == "DEAL"]
    storage_escalations = [n for n in all_negs if "STORAGE" in str(n.get("status", ""))]
    processing_escalations = [n for n in all_negs if "PROCESSING" in str(n.get("status", ""))]
    compost_escalations = [n for n in all_negs if "COMPOST" in str(n.get("status", ""))]
    failed = [n for n in all_negs if n.get("status") in ("FAILED", "REJECT", "CANCELLED", "NO_DEAL")]

    # Price analytics
    prices = [float(n.get("final_price") or 0) for n in deals if n.get("final_price")]
    avg_price = round(sum(prices) / len(prices), 2) if prices else 0.0
    max_price = round(max(prices), 2) if prices else 0.0
    min_deal_price = round(min(prices), 2) if prices else 0.0

    # Quantity & GMV
    quantities = [float(n.get("quantity") or 0) for n in deals if n.get("quantity")]
    total_volume_kg = round(sum(quantities), 2)
    gmv_values = [
        float(n.get("final_price") or 0) * float(n.get("quantity") or 0)
        for n in deals
        if n.get("final_price") and n.get("quantity")
    ]
    total_gmv = round(sum(gmv_values), 2)

    # User metrics
    total_users = len(all_users)
    farmers = [u for u in all_users if u.get("role") == "farmer"]
    buyers = [u for u in all_users if u.get("role") == "buyer"]
    verified = [u for u in all_users if u.get("verification_status") == "VERIFIED"]

    # Crop distribution
    crop_counts: Dict[str, int] = {}
    for n in all_negs:
        crop = n.get("crop", "Unknown") or "Unknown"
        crop_counts[crop] = crop_counts.get(crop, 0) + 1

    # Location distribution (from negotiations, since users don't always have location)
    location_counts: Dict[str, int] = {}
    for u in all_users:
        loc = u.get("location", "Unknown") or "Unknown"
        location_counts[loc] = location_counts.get(loc, 0) + 1

    return {
        "negotiations": {
            "total": total_negs,
            "deals": len(deals),
            "storage_escalations": len(storage_escalations),
            "processing_escalations": len(processing_escalations),
            "compost_escalations": len(compost_escalations),
            "failed": len(failed),
            "success_rate_pct": round((len(deals) / total_negs) * 100, 1) if total_negs else 0.0,
        },
        "pricing": {
            "average_deal_price": avg_price,
            "max_deal_price": max_price,
            "min_deal_price": min_deal_price,
        },
        "volume": {
            "total_traded_kg": total_volume_kg,
            "total_gmv": total_gmv,
        },
        "users": {
            "total": total_users,
            "farmers": len(farmers),
            "buyers": len(buyers),
            "verified": len(verified),
        },
        "distributions": {
            "crops": dict(sorted(crop_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
            "locations": dict(sorted(location_counts.items(), key=lambda x: x[1], reverse=True)[:10]),
        },
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }


async def get_farmer_dashboard(user_id: str) -> Dict[str, Any]:
    """Per-farmer dashboard view — queries PostgreSQL directly."""
    async with AsyncSessionLocal() as session:
        res = await session.execute(
            select(DBNegotiation).where(DBNegotiation.user_id == user_id)
        )
        my_negs = [n.__dict__ for n in res.scalars().all()]

        res_h = await session.execute(
            select(DBHistory).where(DBHistory.user_id == user_id).order_by(DBHistory.id.desc()).limit(5)
        )
        recent_rows = res_h.scalars().all()

    deals = [n for n in my_negs if n.get("status") == "DEAL"]
    prices = [float(n.get("final_price") or 0) for n in deals if n.get("final_price")]
    avg_price = round(sum(prices) / len(prices), 2) if prices else 0.0
    earnings_values = [
        float(n.get("final_price") or 0) * float(n.get("quantity") or 0)
        for n in deals if n.get("final_price") and n.get("quantity")
    ]
    total_earnings = round(sum(earnings_values), 2)

    recent_activity = [
        {
            "negotiation_id": r.negotiation_id,
            "crop": r.crop,
            "quantity": r.quantity,
            "status": r.status,
            "final_price": r.final_price,
            "summary": r.summary,
        }
        for r in recent_rows
    ]

    user = await UserRepository.get_by_id(user_id) or {}

    return {
        "user": {
            "user_id": user_id,
            "name": user.get("name"),
            "trust_score": user.get("trust_score", 4.0),
            "verification_status": user.get("verification_status", "PENDING"),
        },
        "negotiations": {
            "total": len(my_negs),
            "successful": len(deals),
            "pending": len([n for n in my_negs if n.get("status") in ("RUNNING", "ACTIVE", "IN_PROGRESS")]),
            "failed": len([n for n in my_negs if n.get("status") in ("FAILED", "REJECT", "NO_DEAL")]),
        },
        "earnings": {
            "total": total_earnings,
            "average_price": avg_price,
        },
        "recent_activity": recent_activity,
    }


async def get_buyer_dashboard(user_id: str) -> Dict[str, Any]:
    """Per-buyer dashboard view — queries PostgreSQL directly."""
    async with AsyncSessionLocal() as session:
        res_h = await session.execute(
            select(DBHistory).where(DBHistory.user_id == user_id).order_by(DBHistory.id.desc())
        )
        history_rows = res_h.scalars().all()

    history = [
        {
            "negotiation_id": r.negotiation_id,
            "crop": r.crop,
            "quantity": r.quantity,
            "status": r.status,
            "final_price": r.final_price,
            "summary": r.summary,
        }
        for r in history_rows
    ]
    deal_history = [h for h in history if h.get("status") == "DEAL"]

    purchased_kg = sum(float(h.get("quantity") or 0) for h in deal_history)
    spent = sum(
        float(h.get("final_price") or 0) * float(h.get("quantity") or 0)
        for h in deal_history
        if h.get("final_price") and h.get("quantity")
    )

    user = await UserRepository.get_by_id(user_id) or {}

    return {
        "user": {
            "user_id": user_id,
            "name": user.get("name"),
            "trust_score": user.get("trust_score", 4.0),
        },
        "purchases": {
            "total_deals": len(deal_history),
            "total_kg_purchased": round(purchased_kg, 2),
            "total_spent": round(spent, 2),
        },
        "recent_activity": history[:5],
    }
