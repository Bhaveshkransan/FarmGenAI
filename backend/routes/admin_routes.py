"""
backend/routes/admin_routes.py

Admin-only management endpoints.
Covers user verification, audit logs, system flags, and platform governance.
"""

from backend.repositories.user_repository import UserRepository
import logging
from fastapi import APIRouter, Depends, HTTPException
from backend.services.security import get_current_user
from database.db import Database

logger = logging.getLogger("admin_routes")
router = APIRouter(tags=["Admin"])


async def _require_admin(current_user: dict):
    """Dependency: ensures caller is an admin user."""
    role = current_user.get("role", "")
    if role != "admin":
        raise HTTPException(status_code=403, detail="Admin access required.")
    return current_user


# ── User Management ──────────────────────────────────────

@router.get("/users")
async def list_all_users(current_user: dict = Depends(get_current_user)):
    """Return all registered users. Admin only."""
    await _require_admin(current_user)
    from backend.db.session import AsyncSessionLocal
    from backend.db.models.schema import DBUser
    from sqlalchemy import select
    async with AsyncSessionLocal() as session:
        res = await session.execute(select(DBUser).order_by(DBUser.user_id))
        rows = res.scalars().all()
    users = [
        {
            "user_id": u.user_id,
            "name": u.name,
            "email": u.email,
            "role": u.role,
            "location": u.location,
            "verification_status": u.verification_status,
            "trust_score": u.trust_score,
        }
        for u in rows
    ]
    return {"success": True, "data": users, "count": len(users)}


@router.post("/users/{user_id}/verify")
async def admin_verify_user(
    user_id: str,
    verified: bool = True,
    current_user: dict = Depends(get_current_user),
):
    """Verify or revoke a user. Admin only."""
    _require_admin(current_user)
    user = await UserRepository.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user["verified"] = verified
    user["verification_status"] = "VERIFIED" if verified else "REJECTED"
    await UserRepository.upsert(user)
    logger.info(f"Admin {current_user['sub']} set verified={verified} for user {user_id}")
    return {"success": True, "user_id": user_id, "verified": verified}


@router.post("/users/{user_id}/set-role")
async def admin_set_role(
    user_id: str,
    role: str,
    current_user: dict = Depends(get_current_user),
):
    """Change a user's role. Admin only."""
    _require_admin(current_user)
    valid_roles = {"farmer", "buyer", "warehouse", "transporter", "processor", "admin"}
    if role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Invalid role. Must be one of: {valid_roles}")

    user = await UserRepository.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    old_role = user.get("role")
    user["role"] = role
    await UserRepository.upsert(user)
    logger.info(f"Admin {current_user['sub']} changed role for {user_id}: {old_role} → {role}")
    return {"success": True, "user_id": user_id, "old_role": old_role, "new_role": role}


@router.delete("/users/{user_id}")
async def admin_delete_user(user_id: str, current_user: dict = Depends(get_current_user)):
    """Soft-delete a user account. Admin only."""
    _require_admin(current_user)
    user = await UserRepository.get_by_id(user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    user["active"] = False
    user["verification_status"] = "DEACTIVATED"
    await UserRepository.upsert(user)
    logger.info(f"Admin {current_user['sub']} deactivated user {user_id}")
    return {"success": True, "user_id": user_id, "status": "deactivated"}


# ── Negotiation Governance ───────────────────────────────

@router.get("/negotiations")
async def list_all_negotiations(
    status: str = None,
    current_user: dict = Depends(get_current_user),
):
    """List all negotiations across all users. Admin only."""
    _require_admin(current_user)
    negs = list(Database.negotiations.values())
    if status:
        negs = [n for n in negs if str(n.get("status", "")).upper() == status.upper()]
    return {"success": True, "data": negs, "count": len(negs)}


@router.post("/negotiations/{negotiation_id}/cancel")
async def admin_cancel_negotiation(
    negotiation_id: str,
    reason: str = "Admin cancellation",
    current_user: dict = Depends(get_current_user),
):
    """Force-cancel a negotiation. Admin only."""
    _require_admin(current_user)
    neg = await Database.get_negotiation_async(negotiation_id)
    if not neg:
        raise HTTPException(status_code=404, detail="Negotiation not found")

    neg["status"] = "CANCELLED"
    neg["admin_note"] = reason
    await Database.update_negotiation_async(negotiation_id, neg)
    logger.info(f"Admin {current_user['sub']} cancelled negotiation {negotiation_id}")
    return {"success": True, "negotiation_id": negotiation_id, "status": "CANCELLED"}


# ── Audit Logs ────────────────────────────────────────────

@router.get("/audit-logs")
async def get_audit_logs(
    limit: int = 100,
    current_user: dict = Depends(get_current_user),
):
    """Return platform-wide audit log. Admin only."""
    _require_admin(current_user)
    all_history = await Database.get_history_async("all")
    return {
        "success": True,
        "data": all_history[-limit:],
        "count": len(all_history),
    }


# ── Platform Statistics ───────────────────────────────────

@router.get("/platform-stats")
async def admin_platform_stats(current_user: dict = Depends(get_current_user)):
    """High-level platform statistics. Admin only."""
    _require_admin(current_user)
    total_users = len(Database.users)
    total_negs = len(Database.negotiations)
    deals = sum(1 for n in Database.negotiations.values() if n.get("status") == "DEAL")
    return {
        "success": True,
        "data": {
            "total_users": total_users,
            "total_negotiations": total_negs,
            "successful_deals": deals,
            "success_rate": round((deals / total_negs) * 100, 1) if total_negs else 0,
        },
    }

