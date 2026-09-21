"""
backend/services/transport_cost_service.py

Deterministic transportation cost, pricing, floor price, and profit calculation engine.
All financial and numerical computations are strictly performed in Python logic.
The LLM is NOT permitted to calculate or override these values.
"""

import logging
from typing import Dict, Any, Optional
from sqlalchemy import select
from backend.db.session import AsyncSessionLocal
from backend.db.models.transport_agent_models import DBTransportCostParameter
from backend.services.fuel_service import get_fuel_price, estimate_toll_cost

logger = logging.getLogger("TransportCostService")

DEFAULT_COST_PARAMS = {
    "driver_cost_per_hour": 200.0,
    "maintenance_cost_per_km": 5.0,
    "loading_cost": 200.0,
    "unloading_cost": 200.0,
    "waiting_cost_per_hour": 150.0,
    "risk_buffer_pct": 0.05,
    "minimum_profit_margin_pct": 0.18
}


async def get_cost_parameters(vehicle_type: str) -> Dict[str, float]:
    """Query vehicle type cost parameters from DB with fallback defaults."""
    try:
        async with AsyncSessionLocal() as session:
            stmt = select(DBTransportCostParameter).where(
                DBTransportCostParameter.vehicle_type.ilike(vehicle_type)
            )
            res = await session.execute(stmt)
            param = res.scalars().first()
            if param:
                return {
                    "driver_cost_per_hour": param.driver_cost_per_hour,
                    "maintenance_cost_per_km": param.maintenance_cost_per_km,
                    "loading_cost": param.loading_cost,
                    "unloading_cost": param.unloading_cost,
                    "waiting_cost_per_hour": param.waiting_cost_per_hour,
                    "risk_buffer_pct": param.risk_buffer_pct,
                    "minimum_profit_margin_pct": param.minimum_profit_margin_pct
                }
    except Exception as e:
        logger.warning(f"Failed to query DBTransportCostParameter for {vehicle_type}: {e}")

    return DEFAULT_COST_PARAMS


async def calculate_transportation_cost(
    vehicle: Dict[str, Any],
    distance_km: float,
    estimated_duration_hours: float,
    deadhead_km: float = 0.0,
    waiting_hours: float = 0.0,
    route_name: str = "NH-60",
    is_perishable: bool = False
) -> Dict[str, Any]:
    """
    Deterministic Python business calculation of operating cost, floor price, target price, initial quote.
    """
    vtype = vehicle.get("vehicle_type", "Medium Truck")
    fuel_type = vehicle.get("fuel_type", "Diesel")
    mileage_kmpl = max(1.0, float(vehicle.get("fuel_efficiency_kmpl", 10.0)))

    # Fetch fuel price and toll estimates
    fuel_info = await get_fuel_price(fuel_type=fuel_type)
    fuel_price = fuel_info["price_per_litre"]

    toll_info = await estimate_toll_cost(route_name, vtype, distance_km)
    toll_cost = toll_info["toll_cost"]

    # Fetch cost parameters for vehicle type
    params = await get_cost_parameters(vtype)

    # 1. Fuel cost for loaded trip
    litres_needed = distance_km / mileage_kmpl
    fuel_cost = round(litres_needed * fuel_price, 2)

    # 2. Deadhead fuel cost
    deadhead_litres = deadhead_km / mileage_kmpl
    deadhead_cost = round(deadhead_litres * fuel_price, 2)

    # 3. Driver cost
    driver_cost = round(estimated_duration_hours * params["driver_cost_per_hour"], 2)

    # 4. Maintenance cost
    total_distance_km = distance_km + deadhead_km
    maintenance_cost = round(total_distance_km * params["maintenance_cost_per_km"], 2)

    # 5. Loading/Unloading costs
    loading_cost = params["loading_cost"]
    unloading_cost = params["unloading_cost"]

    # 6. Waiting cost
    waiting_cost = round(waiting_hours * params["waiting_cost_per_hour"], 2)

    # 7. Total Base Operating Cost
    base_operating_cost = round(
        fuel_cost + toll_cost + driver_cost + maintenance_cost +
        loading_cost + unloading_cost + waiting_cost + deadhead_cost,
        2
    )

    # 8. Risk Buffer (Perishability increases risk buffer slightly)
    risk_pct = params["risk_buffer_pct"]
    if is_perishable or vehicle.get("refrigerated", False):
        risk_pct += 0.03
    risk_buffer = round(base_operating_cost * risk_pct, 2)

    risk_adjusted_cost = round(base_operating_cost + risk_buffer, 2)

    # 9. Floor Price (Minimum Acceptable Price)
    min_profit_margin = params["minimum_profit_margin_pct"]
    minimum_acceptable_price = round(risk_adjusted_cost * (1.0 + min_profit_margin), 2)

    # 10. Target Price and Initial Quote
    target_price = round(minimum_acceptable_price * 1.12, 2)
    initial_quote = round(minimum_acceptable_price * 1.20, 2)

    return {
        "vehicle_id": vehicle.get("vehicle_id"),
        "vehicle_type": vtype,
        "fuel_type": fuel_type,
        "fuel_price_per_litre": fuel_price,
        "mileage_kmpl": mileage_kmpl,
        "distance_km": distance_km,
        "deadhead_km": deadhead_km,
        "estimated_duration_hours": estimated_duration_hours,
        "cost_breakdown": {
            "fuel_cost": fuel_cost,
            "deadhead_cost": deadhead_cost,
            "toll_cost": toll_cost,
            "toll_type": toll_info["toll_type"],
            "driver_cost": driver_cost,
            "maintenance_cost": maintenance_cost,
            "loading_cost": loading_cost,
            "unloading_cost": unloading_cost,
            "waiting_cost": waiting_cost,
            "risk_buffer": risk_buffer,
        },
        "total_operating_cost": base_operating_cost,
        "risk_adjusted_cost": risk_adjusted_cost,
        "minimum_acceptable_price": minimum_acceptable_price,
        "target_price": target_price,
        "initial_quote": initial_quote,
        "pricing_rules": {
            "floor_price": minimum_acceptable_price,
            "target_price": target_price,
            "initial_quote": initial_quote
        }
    }


def calculate_expected_profit(agreed_price: float, total_operating_cost: float) -> Dict[str, float]:
    """Calculate expected profit and net margin percentage from an agreed freight price."""
    profit = round(agreed_price - total_operating_cost, 2)
    margin_pct = round((profit / total_operating_cost) * 100.0, 2) if total_operating_cost > 0 else 0.0
    return {
        "agreed_price": agreed_price,
        "total_operating_cost": total_operating_cost,
        "expected_profit": profit,
        "profit_margin_pct": margin_pct
    }
