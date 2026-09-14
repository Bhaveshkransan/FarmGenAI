"""
backend/services/workflow_service.py

Workflow Planning Service — FR-6: Automated Workflow Planning

Determines the optimal supply chain route for a crop listing:
  1. Direct Sale (highest priority)
  2. Cold Storage (medium-term holding)
  3. Processing (value-added fallback)
  4. Composting (last resort / zero-waste)

Business rules per SRS:
- If shelf_life <= 2 AND no viable buyer: escalate to STORAGE or PROCESSING
- If storage cost < 30% of market value: recommend STORAGE
- If processor_offer >= 60% of min_price: recommend PROCESSING
- Otherwise: COMPOST (ecological fallback)
"""

import logging
import uuid
import datetime
from typing import Dict, List
from backend.repositories.database_repo import Database

logger = logging.getLogger("WorkflowService")


async def plan_workflow(listing: Dict, market_price: float = None) -> Dict:
    """
    Determine the recommended supply chain workflow for a crop listing.

    Args:
        listing: crop listing dict (crop, quantity, min_price, spoilage_days, location)
        market_price: optional real-time market price override

    Returns:
        workflow plan with ranked options and recommendation
    """
    quantity = float(listing.get("quantity", 100))
    min_price = float(listing.get("min_price", 10))
    spoilage_days = int(listing.get("spoilage_days") or listing.get("shelf_life") or 7)
    location = listing.get("location", "Market")
    crop = listing.get("crop", "Produce")

    if not market_price:
        market_price = min_price * 1.15

    # ── Calculate option metrics ──────────────────────────
    direct_revenue = market_price * quantity
    direct_net = direct_revenue

    storage_cost_per_day = 1.8  # ₹/kg/day (default)
    storage_days = min(spoilage_days, 7)
    total_storage_cost = storage_cost_per_day * quantity * storage_days
    storage_expected_price = market_price * 1.05  # price recovery after storage
    storage_net = storage_expected_price * quantity - total_storage_cost

    processing_price = market_price * 0.78
    processing_net = processing_price * quantity

    compost_price = 8.0
    compost_net = compost_price * quantity

    # ── Spoilage urgency ──────────────────────────────────
    if spoilage_days <= 1:
        urgency = "CRITICAL"
    elif spoilage_days <= 3:
        urgency = "HIGH"
    elif spoilage_days <= 7:
        urgency = "MEDIUM"
    else:
        urgency = "LOW"

    # ── Build options list ────────────────────────────────
    options: List[Dict] = [
        {
            "type": "direct-sale",
            "label": "Direct Sale",
            "net_revenue": round(direct_net, 2),
            "price_per_kg": round(market_price, 2),
            "viable": True,
            "risk": "Low" if spoilage_days > 3 else "Medium",
            "time_to_cash_days": 1,
            "notes": "Immediate sale at market price.",
        },
        {
            "type": "storage",
            "label": "Cold Storage",
            "net_revenue": round(storage_net, 2),
            "price_per_kg": round(storage_expected_price, 2),
            "storage_cost_total": round(total_storage_cost, 2),
            "storage_days": storage_days,
            "viable": spoilage_days > 2 and total_storage_cost < direct_revenue * 0.3,
            "risk": "Medium",
            "time_to_cash_days": storage_days + 1,
            "notes": f"Store for {storage_days} days to wait for better prices.",
        },
        {
            "type": "processing",
            "label": "Processing / Value-Added",
            "net_revenue": round(processing_net, 2),
            "price_per_kg": round(processing_price, 2),
            "viable": processing_price >= min_price * 0.6,
            "risk": "Low",
            "time_to_cash_days": 2,
            "notes": "Sell to food processor for guaranteed purchase.",
        },
        {
            "type": "compost",
            "label": "Composting (Zero-Waste)",
            "net_revenue": round(compost_net, 2),
            "price_per_kg": compost_price,
            "viable": True,
            "risk": "None",
            "time_to_cash_days": 1,
            "notes": "Eco-friendly fallback recovering some value.",
        },
    ]

    # ── Select best route by net revenue among viable options ──
    viable = [o for o in options if o["viable"]]
    if not viable:
        viable = [options[-1]]  # always use compost as fallback

    # For critical spoilage, penalize storage
    if urgency == "CRITICAL":
        viable = [o for o in viable if o["type"] != "storage"] or viable

    best = max(viable, key=lambda x: x["net_revenue"])

    result = {
        "plan_id": str(uuid.uuid4()),
        "listing_id": listing.get("id"),
        "user_id": listing.get("user_id"),
        "crop": crop,
        "quantity": quantity,
        "location": location,
        "spoilage_urgency": urgency,
        "urgency": urgency,
        "spoilage_days": spoilage_days,
        "market_price": round(market_price, 2),
        "min_price": min_price,
        "options": options,
        "recommended": best,
        "recommendation": best,
        "recommendation_reason": await _build_reason(best, urgency, min_price, market_price),
        "created_at": datetime.datetime.utcnow().isoformat()
    }

    # Persist the plan to database
    try:
        from backend.repositories.database_repo import Database
        await Database.upsert_workflow_plan_async(result["plan_id"], result)
    except Exception as e:
        logger.error(f"Failed to persist workflow plan: {e}")

    return result
async def _build_reason(option: Dict, urgency: str, min_price: float, market_price: float) -> str:
    opt_type = option["type"]
    net = option["net_revenue"]
    if opt_type == "direct-sale":
        return f"Direct sale yields highest net revenue ₹{net:.2f}. Current market price is favorable."
    if opt_type == "storage":
        return f"Storage expected to recover ₹{net:.2f} after {option['storage_days']} days. Spoilage risk is manageable."
    if opt_type == "processing":
        return f"Processing guarantees ₹{option['price_per_kg']}/kg with no spoilage risk. Net ₹{net:.2f}."
    return f"Composting recovers minimal value (₹{net:.2f}) while eliminating waste."

