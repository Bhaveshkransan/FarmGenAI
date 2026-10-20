from copy import deepcopy

from database.db import Database


_WAREHOUSE_PROFILES = [
    {
        "id": "wh_nashik_cold",
        "name": "Nashik Cold Storage",
        "location": "Nashik",
        "capacity_kg": 12000.0,
        "base_cost_per_kg_per_day": 1.9,
    },
    {
        "id": "wh_pune_hub",
        "name": "Pune Agro Hub",
        "location": "Pune",
        "capacity_kg": 9500.0,
        "base_cost_per_kg_per_day": 1.6,
    },
    {
        "id": "wh_mumbai_port",
        "name": "Mumbai Port Warehouse",
        "location": "Mumbai",
        "capacity_kg": 18000.0,
        "base_cost_per_kg_per_day": 2.2,
    },
]


async def _get_storage_loads() -> dict:
    loads = {profile["id"]: 0.0 for profile in _WAREHOUSE_PROFILES}
    status_rows = list(Database.negotiations.values())
    storage_rows = [row for row in status_rows if row.get("status") == "ESCALATED_STORAGE"]

    if not storage_rows:
        return loads

    # Spread historical load across warehouses to maintain deterministic
    # utilization without requiring extra DB tables in hackathon mode.
    for index, row in enumerate(storage_rows):
        wh = _WAREHOUSE_PROFILES[index % len(_WAREHOUSE_PROFILES)]
        loads[wh["id"]] += float(row.get("quantity", 0) or 0)

    return loads


async def list_warehouses():
    loads = await _get_storage_loads()
    result = []

    for profile in _WAREHOUSE_PROFILES:
        used = round(loads.get(profile["id"], 0.0), 2)
        available = max(profile["capacity_kg"] - used, 0.0)
        utilization_pct = round((used / profile["capacity_kg"]) * 100, 2) if profile["capacity_kg"] else 0.0

        result.append(
            {
                **deepcopy(profile),
                "used_capacity_kg": used,
                "available_capacity_kg": round(available, 2),
                "utilization_pct": utilization_pct,
            }
        )

    return result


async def assign_storage(produce: dict):
    quantity = float(produce.get("quantity", 0) or 0)
    if quantity <= 0:
        raise ValueError("quantity must be greater than 0")

    location = str(produce.get("location", "")).strip() or "Unknown"
    shelf_life = int(produce.get("shelf_life", 3) or 3)
    crop = str(produce.get("crop", "produce"))

    warehouses = await list_warehouses()
    viable = [w for w in warehouses if w["available_capacity_kg"] >= quantity]
    if not viable:
        raise ValueError("No warehouse has enough available capacity for this quantity")

    def _rank_key(wh):
        location_bonus = 0 if wh["location"].lower() == location.lower() else 1
        urgency_penalty = 0.25 if shelf_life <= 2 else 0
        effective_cost = wh["base_cost_per_kg_per_day"] + urgency_penalty
        return (location_bonus, effective_cost, -wh["available_capacity_kg"])

    selected = sorted(viable, key=_rank_key)[0]
    total_daily_cost = round(quantity * selected["base_cost_per_kg_per_day"], 2)

    return {
        "warehouse_id": selected["id"],
        "warehouse": selected["name"],
        "location": selected["location"],
        "crop": crop,
        "quantity": quantity,
        "cost_per_kg_per_day": selected["base_cost_per_kg_per_day"],
        "total_daily_cost": total_daily_cost,
        "available_capacity_after_assignment": round(selected["available_capacity_kg"] - quantity, 2),
        "recommended_days": max(1, min(7, shelf_life)),
        "status": "ASSIGNED",
    }
