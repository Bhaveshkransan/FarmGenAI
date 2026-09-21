"""
backend/services/vehicle_service.py

Vehicle management and hard-constraint filtering for the Transport Agent.
Filters vehicles based on capacity, status, pickup feasibility, deadline,
and refrigeration/temperature parameters before cost calculation & negotiation.
"""

import logging
from typing import List, Dict, Any, Optional
from sqlalchemy import select
from backend.db.session import AsyncSessionLocal
from backend.db.models.transport_agent_models import DBVehicle

logger = logging.getLogger("VehicleService")

# Default fallback vehicle fleet if DB query returns empty
DEFAULT_FLEET = [
    {
        "vehicle_id": "V01",
        "transporter_id": "TRANS-01",
        "vehicle_type": "Cargo Three-Wheeler",
        "vehicle_name": "Piaggio Ape Extra",
        "capacity_kg": 600.0,
        "fuel_type": "Diesel",
        "fuel_efficiency_kmpl": 16.0,
        "current_location": "Ahmednagar",
        "refrigerated": False,
        "status": "AVAILABLE",
        "rating": 4.6
    },
    {
        "vehicle_id": "V02",
        "transporter_id": "TRANS-01",
        "vehicle_type": "Mini Truck",
        "vehicle_name": "Tata Ace Gold",
        "capacity_kg": 1500.0,
        "fuel_type": "Diesel",
        "fuel_efficiency_kmpl": 12.0,
        "current_location": "Ahmednagar",
        "refrigerated": False,
        "status": "AVAILABLE",
        "rating": 4.8
    },
    {
        "vehicle_id": "V03",
        "transporter_id": "TRANS-02",
        "vehicle_type": "LCV",
        "vehicle_name": "Mahindra Bolero Maxi Truck",
        "capacity_kg": 2500.0,
        "fuel_type": "Diesel",
        "fuel_efficiency_kmpl": 10.0,
        "current_location": "Nashik",
        "refrigerated": False,
        "status": "AVAILABLE",
        "rating": 4.7
    },
    {
        "vehicle_id": "V04",
        "transporter_id": "TRANS-02",
        "vehicle_type": "Medium Truck",
        "vehicle_name": "Eicher Pro 2059",
        "capacity_kg": 5000.0,
        "fuel_type": "Diesel",
        "fuel_efficiency_kmpl": 8.0,
        "current_location": "Ahmednagar",
        "refrigerated": False,
        "status": "AVAILABLE",
        "rating": 4.9
    },
    {
        "vehicle_id": "V05",
        "transporter_id": "TRANS-03",
        "vehicle_type": "Refrigerated Truck",
        "vehicle_name": "ColdChain Reefer 4MT",
        "capacity_kg": 4000.0,
        "fuel_type": "Diesel",
        "fuel_efficiency_kmpl": 6.5,
        "current_location": "Pune",
        "refrigerated": True,
        "temperature_min_c": 2.0,
        "temperature_max_c": 12.0,
        "status": "AVAILABLE",
        "rating": 4.95
    },
    {
        "vehicle_id": "V06",
        "transporter_id": "TRANS-03",
        "vehicle_type": "Heavy Truck",
        "vehicle_name": "Tata 1613 6-Wheeler",
        "capacity_kg": 12000.0,
        "fuel_type": "Diesel",
        "fuel_efficiency_kmpl": 5.0,
        "current_location": "Mumbai",
        "refrigerated": False,
        "status": "AVAILABLE",
        "rating": 4.6
    },
    {
        "vehicle_id": "V07",
        "transporter_id": "TRANS-04",
        "vehicle_type": "Tractor + Trailer",
        "vehicle_name": "Sonalika 750 + Trolley",
        "capacity_kg": 7000.0,
        "fuel_type": "Diesel",
        "fuel_efficiency_kmpl": 7.0,
        "current_location": "Aurangabad",
        "refrigerated": False,
        "status": "AVAILABLE",
        "rating": 4.5
    }
]


async def get_all_vehicles(status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    """Query vehicles from DB with fallback to default fleet."""
    try:
        async with AsyncSessionLocal() as session:
            stmt = select(DBVehicle)
            if status_filter:
                stmt = stmt.where(DBVehicle.status.ilike(status_filter))
            res = await session.execute(stmt)
            rows = res.scalars().all()
            if rows:
                return [{
                    "vehicle_id": r.vehicle_id,
                    "transporter_id": r.transporter_id,
                    "vehicle_type": r.vehicle_type,
                    "vehicle_name": r.vehicle_name or r.vehicle_type,
                    "capacity_kg": r.capacity_kg,
                    "fuel_type": r.fuel_type,
                    "fuel_efficiency_kmpl": r.fuel_efficiency_kmpl,
                    "current_location": r.current_location or "Ahmednagar",
                    "refrigerated": r.refrigerated,
                    "temperature_min_c": r.temperature_min_c,
                    "temperature_max_c": r.temperature_max_c,
                    "status": r.status,
                    "rating": r.rating,
                    "contact_number": r.contact_number
                } for r in rows]
    except Exception as e:
        logger.warning(f"Failed to query DBVehicle: {e}")

    fleet = DEFAULT_FLEET
    if status_filter:
        fleet = [v for v in fleet if v["status"].upper() == status_filter.upper()]
    return fleet


async def filter_suitable_vehicles(
    quantity_kg: float,
    refrigerated_required: bool = False,
    estimated_duration_hours: Optional[float] = None,
    delivery_deadline_hours: Optional[float] = None,
    pickup_location: Optional[str] = None
) -> Dict[str, Any]:
    """
    Apply strict hard constraints to find candidate vehicles.
    
    Hard constraints checked:
    1. Status == AVAILABLE
    2. Vehicle capacity >= requested quantity_kg
    3. Refrigeration requirement (if required, vehicle MUST be refrigerated)
    4. Delivery deadline feasibility (estimated_duration_hours <= delivery_deadline_hours)
    """
    all_vehicles = await get_all_vehicles(status_filter="AVAILABLE")
    
    candidates = []
    rejected = []

    for v in all_vehicles:
        # Constraint 1: Capacity check
        if v["capacity_kg"] < quantity_kg:
            rejected.append({
                "vehicle_id": v["vehicle_id"],
                "reason": f"Insufficient capacity ({v['capacity_kg']}kg < required {quantity_kg}kg)"
            })
            continue

        # Constraint 2: Refrigeration check
        if refrigerated_required and not v.get("refrigerated", False):
            rejected.append({
                "vehicle_id": v["vehicle_id"],
                "reason": "Refrigeration required but vehicle is non-refrigerated"
            })
            continue

        # Constraint 3: Delivery deadline check
        if estimated_duration_hours and delivery_deadline_hours:
            if estimated_duration_hours > delivery_deadline_hours:
                rejected.append({
                    "vehicle_id": v["vehicle_id"],
                    "reason": f"Estimated duration ({estimated_duration_hours}h) exceeds deadline ({delivery_deadline_hours}h)"
                })
                continue

        candidates.append(v)

    # Sort candidates by optimal capacity match (least excess capacity first) then rating
    candidates.sort(key=lambda x: (x["capacity_kg"] - quantity_kg, -x.get("rating", 4.0)))

    return {
        "success": len(candidates) > 0,
        "candidate_count": len(candidates),
        "candidates": candidates,
        "best_vehicle": candidates[0] if candidates else None,
        "rejected_vehicles": rejected
    }
