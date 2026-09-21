"""
backend/services/fuel_service.py

Manages fuel prices and toll estimation for the Transport Agent.
Provides current state/regional fuel prices and verified NHAI toll rates,
falling back gracefully to configured benchmarks when specific values are absent.
"""

import logging
from sqlalchemy import select
from backend.db.session import AsyncSessionLocal
from backend.db.models.transport_agent_models import DBFuelPrice, DBTollRate

logger = logging.getLogger("FuelService")

DEFAULT_FUEL_PRICES = {
    "Diesel": 92.50,
    "Petrol": 104.20,
    "CNG": 86.00
}

DEFAULT_TOLL_RATE_PER_KM = {
    "Cargo Three-Wheeler": 0.0,
    "Mini Truck": 1.2,
    "LCV": 1.5,
    "Medium Truck": 2.0,
    "Refrigerated Truck": 2.2,
    "Heavy Truck": 3.0,
    "Tractor + Trailer": 1.8
}


async def get_fuel_price(fuel_type: str = "Diesel", location: str = "Maharashtra") -> dict:
    """Fetch active fuel price per litre for a given fuel type and region."""
    try:
        async with AsyncSessionLocal() as session:
            stmt = select(DBFuelPrice).where(
                DBFuelPrice.fuel_type.ilike(fuel_type),
                DBFuelPrice.state.ilike(location) | DBFuelPrice.location.ilike(location)
            )
            res = await session.execute(stmt)
            fp = res.scalars().first()
            if fp:
                return {
                    "fuel_type": fp.fuel_type,
                    "price_per_litre": fp.price_per_litre,
                    "location": fp.location,
                    "source": fp.source,
                    "is_estimate": False
                }
    except Exception as e:
        logger.warning(f"Error querying DBFuelPrice: {e}")

    price = DEFAULT_FUEL_PRICES.get(fuel_type, 92.50)
    return {
        "fuel_type": fuel_type,
        "price_per_litre": price,
        "location": location,
        "source": "State Benchmark Fallback",
        "is_estimate": True
    }


async def estimate_toll_cost(route_or_highway: str, vehicle_type: str, distance_km: float) -> dict:
    """Calculate toll cost using exact plaza toll records or per-km category benchmarks."""
    try:
        async with AsyncSessionLocal() as session:
            stmt = select(DBTollRate).where(
                DBTollRate.route_or_highway.ilike(route_or_highway),
                DBTollRate.vehicle_category.ilike(vehicle_type)
            )
            res = await session.execute(stmt)
            toll = res.scalars().first()
            if toll:
                return {
                    "toll_cost": toll.amount,
                    "toll_plaza": toll.toll_plaza,
                    "toll_type": "EXACT",
                    "source": toll.source
                }
    except Exception as e:
        logger.warning(f"Error querying DBTollRate: {e}")

    rate_per_km = DEFAULT_TOLL_RATE_PER_KM.get(vehicle_type, 2.0)
    estimated_amount = round(distance_km * rate_per_km, 2)
    return {
        "toll_cost": estimated_amount,
        "toll_plaza": "Estimated Highway Benchmark",
        "toll_type": "ESTIMATED",
        "source": "Maharashtra NHAI Benchmark Rate"
    }
