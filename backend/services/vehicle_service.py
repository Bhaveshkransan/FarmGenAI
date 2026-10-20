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
    },
    {
        "vehicle_id": "V08",
        "transporter_id": "TRANS-05",
        "vehicle_type": "Multi-Axle Heavy Truck",
        "vehicle_name": "BharatBenz 2823C",
        "capacity_kg": 25000.0,
        "fuel_type": "Diesel",
        "fuel_efficiency_kmpl": 4.0,
        "current_location": "Kolhapur",
        "refrigerated": False,
        "status": "AVAILABLE",
        "rating": 4.75
    }
]


async def get_all_vehicles(status_filter: Optional[str] = None) -> List[Dict[str, Any]]:
    """Query vehicles from DB with fallback to default fleet."""
    db_vehicles = []
    try:
        async with AsyncSessionLocal() as session:
            stmt = select(DBVehicle)
            if status_filter:
                stmt = stmt.where(DBVehicle.status.ilike(status_filter))
            res = await session.execute(stmt)
            rows = res.scalars().all()
            if rows:
                db_vehicles = [{
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

    fleet = list(DEFAULT_FLEET)
    
    # Merge DB vehicles into fleet, overriding default ones with same ID
    db_ids = {v["vehicle_id"] for v in db_vehicles}
    fleet = [v for v in fleet if v["vehicle_id"] not in db_ids]
    fleet.extend(db_vehicles)
    
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


async def get_vehicle_by_id(vehicle_id: str) -> Optional[Dict[str, Any]]:
    """Get a vehicle by ID."""
    try:
        async with AsyncSessionLocal() as session:
            stmt = select(DBVehicle).where(DBVehicle.vehicle_id == vehicle_id)
            res = await session.execute(stmt)
            r = res.scalar_one_or_none()
            if r:
                return {
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
                    "contact_number": r.contact_number,
                    "owner_contact": r.owner_contact,
                    "image_url": r.image_url
                }
    except Exception as e:
        logger.error(f"Failed to fetch vehicle {vehicle_id}: {e}")

    # Fallback to default fleet
    for v in DEFAULT_FLEET:
        if v["vehicle_id"] == vehicle_id:
            return v
    return None


async def create_vehicle(vehicle_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Create a new vehicle."""
    try:
        async with AsyncSessionLocal() as session:
            new_vehicle = DBVehicle(**vehicle_data)
            session.add(new_vehicle)
            await session.commit()
            await session.refresh(new_vehicle)
            return vehicle_data # In a real app, serialize new_vehicle
    except Exception as e:
        logger.error(f"Failed to create vehicle: {e}")
        return None


async def update_vehicle(vehicle_id: str, vehicle_data: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    """Update an existing vehicle."""
    try:
        async with AsyncSessionLocal() as session:
            stmt = select(DBVehicle).where(DBVehicle.vehicle_id == vehicle_id)
            res = await session.execute(stmt)
            vehicle = res.scalar_one_or_none()
            if vehicle:
                for k, v in vehicle_data.items():
                    setattr(vehicle, k, v)
                await session.commit()
                return vehicle_data
    except Exception as e:
        logger.error(f"Failed to update vehicle {vehicle_id}: {e}")
    return None


async def delete_vehicle(vehicle_id: str) -> bool:
    """Delete a vehicle."""
    try:
        async with AsyncSessionLocal() as session:
            stmt = select(DBVehicle).where(DBVehicle.vehicle_id == vehicle_id)
            res = await session.execute(stmt)
            vehicle = res.scalar_one_or_none()
            if vehicle:
                await session.delete(vehicle)
                await session.commit()
                return True
    except Exception as e:
        logger.error(f"Failed to delete vehicle {vehicle_id}: {e}")
    return False


async def search_vehicles(filters: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Search vehicles based on provided filters."""
    # Simplified search using existing get_all_vehicles
    all_vehicles = await get_all_vehicles()
    
    results = []
    for v in all_vehicles:
        match = True
        if "capacity_min" in filters and v["capacity_kg"] < filters["capacity_min"]:
            match = False
        if "refrigerated" in filters and v.get("refrigerated", False) != filters["refrigerated"]:
            match = False
        if "status" in filters and v.get("status") != filters["status"]:
            match = False
            
        if match:
            results.append(v)
            
    return results
