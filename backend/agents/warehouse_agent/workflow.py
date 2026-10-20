"""
backend/agents/warehouse_agent/workflow.py

Real Warehouse Stakeholder Agent Workflow — Phase 7
--------------------------------------------------
Performs:
1. Warehouse Discovery across Maharashtra APMC godowns and cold chains.
2. Capacity Validation (Metric Tons to kg conversion and threshold check).
3. Crop Compatibility & Storage Constraints (Cold Storage for perishables, Dry Warehouse for grains/oilseeds).
4. Shelf-Life Considerations & Holding Duration estimation.
5. Location & Proximity Matching (District / APMC mandi locality).
6. Deterministic Storage Cost Calculation (price per MT/day -> price per kg/day * duration).
7. Facility Ranking & Selection (multi-criteria scoring: proximity, cost, rating, spare capacity).
8. Durable Space Reservation & Structured Result Generation.
"""

import json
import uuid
import logging
from pathlib import Path
from copy import deepcopy
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

logger = logging.getLogger("WarehouseAgentWorkflow")

DATASET_PATH = Path(__file__).resolve().parent.parent.parent / "dataset" / "warehouses.json"

PERISHABLE_CROPS = {
    "tomato", "strawberry", "grape", "banana", "mango", "pomegranate",
    "orange", "citrus", "vegetables", "chilli", "capsicum"
}

# Fallback warehouse profiles if JSON file is missing or unreadable
FALLBACK_WAREHOUSES = [
    {
        "warehouse_id": "wh_nashik_001",
        "name": "Nashik Valley Agri Cold Storage",
        "district": "Nashik",
        "location": "Pimpalgaon Baswant, Nashik",
        "type": "Cold Storage",
        "capacity_mt": 5000.0,
        "available_capacity_mt": 1200.0,
        "price_per_mt_per_day": 50.00,
        "rating": 4.5,
        "contact_number": "+91-9876543210"
    },
    {
        "warehouse_id": "wh_pune_001",
        "name": "Manchar Vegetable Cold Chain Ltd",
        "district": "Pune",
        "location": "Manchar APMC, Pune",
        "type": "Cold Storage",
        "capacity_mt": 3000.0,
        "available_capacity_mt": 800.0,
        "price_per_mt_per_day": 60.00,
        "rating": 4.6,
        "contact_number": "+91-9876543212"
    },
    {
        "warehouse_id": "wh_pune_002",
        "name": "Pune District Cooperative Dry Godown",
        "district": "Pune",
        "location": "Loni Kalbhor, Pune",
        "type": "Dry Warehouse",
        "capacity_mt": 8000.0,
        "available_capacity_mt": 3200.0,
        "price_per_mt_per_day": 15.00,
        "rating": 4.0,
        "contact_number": "+91-9876543213"
    },
    {
        "warehouse_id": "wh_latur_001",
        "name": "Latur Oilseed Dry Godown Complex",
        "district": "Latur",
        "location": "Latur APMC Industrial Area, Latur",
        "type": "Dry Warehouse",
        "capacity_mt": 12000.0,
        "available_capacity_mt": 6000.0,
        "price_per_mt_per_day": 12.00,
        "rating": 4.3,
        "contact_number": "+91-9876543217"
    },
    {
        "warehouse_id": "wh_ahmednagar_001",
        "name": "Rahuri Grain & Pulses Warehouse",
        "district": "Ahmednagar",
        "location": "Rahuri APMC, Ahmednagar",
        "type": "Dry Warehouse",
        "capacity_mt": 6000.0,
        "available_capacity_mt": 1500.0,
        "price_per_mt_per_day": 18.00,
        "rating": 4.1,
        "contact_number": "+91-9876543214"
    }
]


def load_warehouse_dataset() -> List[Dict[str, Any]]:
    """Loads authoritative warehouses dataset."""
    if DATASET_PATH.exists():
        try:
            with open(DATASET_PATH, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list) and len(data) > 0:
                    return deepcopy(data)
        except Exception as e:
            logger.warning(f"Could not read warehouses.json: {e}. Using fallback.")
    return deepcopy(FALLBACK_WAREHOUSES)


async def run_warehouse_workflow(input_request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Real Warehouse Agent Execution Entrypoint.
    
    Accepts:
    {
        "requirement_id": "req_123",
        "workflow_id": "wf_123",
        "farmer_deal_id": "deal_456",
        "crop": "Soybean",
        "quantity_kg": 5000.0,
        "location": "Pune",
        "pickup_location": "Nashik",
        "delivery_location": "Pune",
        "holding_days": 7,
        "refrigerated_required": False
    }
    
    Returns structured AgentOutcome-compatible dictionary.
    """
    exec_id = f"WH-EXEC-{uuid.uuid4().hex[:8]}"
    started_at = datetime.now(timezone.utc).isoformat()

    req_id = input_request.get("requirement_id") or f"req_{uuid.uuid4().hex[:6]}"
    wf_id = input_request.get("workflow_id")
    deal_id = input_request.get("farmer_deal_id")
    crop = str(input_request.get("crop") or "Produce").strip()
    qty_kg = float(input_request.get("quantity_kg") or input_request.get("quantity") or 1000.0)
    qty_mt = qty_kg / 1000.0

    target_loc = str(
        input_request.get("delivery_location")
        or input_request.get("location")
        or input_request.get("pickup_location")
        or "Maharashtra"
    ).strip()

    holding_days = int(input_request.get("holding_days") or input_request.get("shelf_life_days") or 7)
    holding_days = max(1, min(60, holding_days))

    # Auto-detect cold storage requirement
    explicit_ref = input_request.get("refrigerated_required")
    if explicit_ref is not None:
        refrigerated_required = bool(explicit_ref)
    else:
        refrigerated_required = crop.lower() in PERISHABLE_CROPS

    logger.info(
        f"[WAREHOUSE_AGENT] Execution {exec_id} started for {qty_kg}kg {crop} in {target_loc} "
        f"(Cold Storage: {refrigerated_required}, Holding Days: {holding_days})"
    )

    # 1. Discover all warehouses
    all_warehouses = load_warehouse_dataset()
    evaluated_candidates = []
    viable_candidates = []
    warnings = []

    for wh in all_warehouses:
        w_type = wh.get("type", "Dry Warehouse")
        w_avail_mt = float(wh.get("available_capacity_mt", 0.0))
        w_avail_kg = w_avail_mt * 1000.0
        w_district = wh.get("district", "Maharashtra")
        w_price_mt_day = float(wh.get("price_per_mt_per_day", 25.0))
        w_rating = float(wh.get("rating", 4.0))

        # Check type compatibility
        type_compatible = True
        if refrigerated_required and "cold" not in w_type.lower():
            type_compatible = False

        # Check capacity
        has_capacity = w_avail_kg >= qty_kg

        # Proximity score (0 if exact district match, 1 if general Maharashtra)
        loc_lower = target_loc.lower()
        is_district_match = (
            w_district.lower() in loc_lower or
            wh.get("location", "").lower() in loc_lower or
            any(w_district.lower() == part.strip() for part in loc_lower.split(","))
        )

        cand_info = {
            "warehouse_id": wh.get("warehouse_id"),
            "name": wh.get("name"),
            "district": w_district,
            "location": wh.get("location"),
            "type": w_type,
            "available_capacity_kg": w_avail_kg,
            "available_capacity_mt": w_avail_mt,
            "price_per_mt_per_day": w_price_mt_day,
            "cost_per_kg_per_day": round(w_price_mt_day / 1000.0, 4),
            "rating": w_rating,
            "type_compatible": type_compatible,
            "has_capacity": has_capacity,
            "is_district_match": is_district_match
        }
        evaluated_candidates.append(cand_info)

        if type_compatible and has_capacity:
            viable_candidates.append(cand_info)

    # 2. Infeasibility Check
    if not viable_candidates:
        err_msg = (
            f"No viable warehouse found with sufficient available capacity ({qty_kg}kg) "
            f"for {crop} (Requires Cold Storage: {refrigerated_required}) in Maharashtra."
        )
        logger.warning(f"[WAREHOUSE_AGENT] {err_msg}")
        completed_at = datetime.now(timezone.utc).isoformat()
        return {
            "agent": "WAREHOUSE",
            "execution_id": exec_id,
            "status": "FAILED",
            "requirement_id": req_id,
            "workflow_id": wf_id,
            "started_at": started_at,
            "completed_at": completed_at,
            "decision": "INFEASIBLE",
            "decision_reason": err_msg,
            "cost": 0.0,
            "candidates": evaluated_candidates,
            "selected_option": None,
            "constraints_checked": {
                "quantity_kg": qty_kg,
                "refrigerated_required": refrigerated_required,
                "holding_days": holding_days,
                "target_location": target_loc,
                "capacity_sufficient": False
            },
            "warnings": warnings,
            "error": err_msg,
            "retryable": True,
            "result": {
                "error": err_msg,
                "route": "/dashboard/warehouse",
                "handoff_ready": False
            }
        }

    # 3. Multi-Criteria Ranking
    # Best candidate: District match first (0 vs 1), then lowest cost per kg, then higher rating, then higher available capacity
    def _rank_key(c):
        dist_penalty = 0 if c["is_district_match"] else 1
        cost = c["cost_per_kg_per_day"]
        rating_bonus = -c["rating"]
        spare_capacity = -c["available_capacity_kg"]
        return (dist_penalty, cost, rating_bonus, spare_capacity)

    viable_candidates.sort(key=_rank_key)
    selected = viable_candidates[0]

    if not selected["is_district_match"]:
        warnings.append(
            f"No warehouse in immediate district '{target_loc}' had sufficient capacity; "
            f"allocated in neighboring district '{selected['district']}'."
        )

    # 4. Storage Cost Calculations
    cost_per_kg_day = selected["cost_per_kg_per_day"]
    daily_cost = round(qty_kg * cost_per_kg_day, 2)
    total_holding_cost = round(daily_cost * holding_days, 2)
    reservation_id = f"WH-RES-{req_id[-6:] if len(req_id) >= 6 else req_id}-{uuid.uuid4().hex[:4].upper()}"

    selected_option = {
        "warehouse_id": selected["warehouse_id"],
        "name": selected["name"],
        "district": selected["district"],
        "location": selected["location"],
        "type": selected["type"],
        "price_per_mt_per_day": selected["price_per_mt_per_day"],
        "cost_per_kg_per_day": cost_per_kg_day,
        "total_daily_cost": daily_cost,
        "total_holding_cost": total_holding_cost,
        "holding_days": holding_days,
        "reservation_id": reservation_id,
        "allocated_quantity_kg": qty_kg,
        "allocated_capacity_mt": qty_mt,
        "remaining_capacity_mt": round(selected["available_capacity_mt"] - qty_mt, 2),
        "rating": selected["rating"]
    }

    decision_reason = (
        f"Allocated {qty_kg}kg at {selected['name']} ({selected['location']}, {selected['district']}) "
        f"for {holding_days} days. Daily holding rate: ₹{cost_per_kg_day:.3f}/kg/day (Total: ₹{total_holding_cost:,.2f})."
    )

    logger.info(f"[WAREHOUSE_AGENT] Execution {exec_id} completed successfully: {decision_reason}")
    completed_at = datetime.now(timezone.utc).isoformat()

    return {
        "agent": "WAREHOUSE",
        "execution_id": exec_id,
        "status": "COMPLETED",
        "requirement_id": req_id,
        "workflow_id": wf_id,
        "started_at": started_at,
        "completed_at": completed_at,
        "decision": "CONFIRMED",
        "decision_reason": decision_reason,
        "cost": total_holding_cost,
        "candidates": evaluated_candidates,
        "selected_option": selected_option,
        "constraints_checked": {
            "quantity_kg": qty_kg,
            "refrigerated_required": refrigerated_required,
            "holding_days": holding_days,
            "target_location": target_loc,
            "facility_type": selected["type"],
            "capacity_sufficient": True
        },
        "warnings": warnings,
        "error": None,
        "retryable": False,
        "result": {
            **selected_option,
            "route": "/dashboard/warehouse",
            "handoff_ready": True,
            "completed": True
        }
    }
