"""
scripts/seed_transport_data.py

Seeds the database with standard initial data for the Transport Agent:
- Registered Vehicles (Mini Truck, LCV, Medium Truck, Heavy Truck, Refrigerated Truck, Tractor + Trailer, Cargo Three-Wheeler)
- Fuel Prices (Diesel, Petrol, CNG in Maharashtra)
- Toll Rates (NHAI highways)
- Transport Cost Parameters (driver cost, maintenance cost, loading, waiting, risk buffer, minimum profit)
"""

import asyncio
import os
import sys
import logging
from datetime import datetime, timezone

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from database.db import AsyncSessionLocal, init_db
from backend.db.models.transport_agent_models import (
    DBVehicle, DBFuelPrice, DBTollRate, DBTransportCostParameter
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("seed_transport_data")

SEED_VEHICLES = [
    {
        "vehicle_id": "V01",
        "transporter_id": "TRANS-01",
        "vehicle_type": "Cargo Three-Wheeler",
        "vehicle_name": "Piaggio Ape Extra",
        "capacity_kg": 600.0,
        "fuel_type": "Diesel",
        "fuel_efficiency_kmpl": 16.0,
        "current_location": "Ahmednagar",
        "current_latitude": 19.0952,
        "current_longitude": 74.7496,
        "refrigerated": False,
        "status": "AVAILABLE",
        "rating": 4.6,
        "contact_number": "+91-9822001122"
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
        "current_latitude": 19.0952,
        "current_longitude": 74.7496,
        "refrigerated": False,
        "status": "AVAILABLE",
        "rating": 4.8,
        "contact_number": "+91-9822001122"
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
        "current_latitude": 19.9975,
        "current_longitude": 73.7898,
        "refrigerated": False,
        "status": "AVAILABLE",
        "rating": 4.7,
        "contact_number": "+91-9822003344"
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
        "current_latitude": 19.0952,
        "current_longitude": 74.7496,
        "refrigerated": False,
        "status": "AVAILABLE",
        "rating": 4.9,
        "contact_number": "+91-9822003344"
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
        "current_latitude": 18.5204,
        "current_longitude": 73.8567,
        "refrigerated": True,
        "temperature_min_c": 2.0,
        "temperature_max_c": 12.0,
        "status": "AVAILABLE",
        "rating": 4.95,
        "contact_number": "+91-9822005566"
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
        "current_latitude": 19.0760,
        "current_longitude": 72.8777,
        "refrigerated": False,
        "status": "AVAILABLE",
        "rating": 4.6,
        "contact_number": "+91-9822005566"
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
        "current_latitude": 19.8762,
        "current_longitude": 75.3433,
        "refrigerated": False,
        "status": "AVAILABLE",
        "rating": 4.5,
        "contact_number": "+91-9822007788"
    }
]

SEED_FUEL_PRICES = [
    {
        "fuel_price_id": "FP-MH-DIESEL",
        "location": "Maharashtra",
        "state": "Maharashtra",
        "fuel_type": "Diesel",
        "price_per_litre": 92.50,
        "effective_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "source": "PPAC Official Benchmark"
    },
    {
        "fuel_price_id": "FP-MH-PETROL",
        "location": "Maharashtra",
        "state": "Maharashtra",
        "fuel_type": "Petrol",
        "price_per_litre": 104.20,
        "effective_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "source": "PPAC Official Benchmark"
    },
    {
        "fuel_price_id": "FP-MH-CNG",
        "location": "Maharashtra",
        "state": "Maharashtra",
        "fuel_type": "CNG",
        "price_per_litre": 86.00,
        "effective_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "source": "MGL Official Benchmark"
    }
]

SEED_TOLL_RATES = [
    {
        "toll_id": "TL-NH60-PUNE-NSK",
        "toll_plaza": "Chaloba Toll Plaza (NH-60)",
        "route_or_highway": "NH-60",
        "vehicle_category": "Medium Truck",
        "amount": 280.0,
        "source": "NHAI Toll Rate Index"
    },
    {
        "toll_id": "TL-NH48-PUNE-MUM",
        "toll_plaza": "Khalapur Toll Plaza (Mumbai-Pune Exp)",
        "route_or_highway": "NH-48",
        "vehicle_category": "Medium Truck",
        "amount": 320.0,
        "source": "MSRDC Official Rate"
    }
]

SEED_COST_PARAMETERS = [
    {
        "parameter_id": "PARAM-3WHEELER",
        "vehicle_type": "Cargo Three-Wheeler",
        "driver_cost_per_hour": 150.0,
        "maintenance_cost_per_km": 3.0,
        "loading_cost": 100.0,
        "unloading_cost": 100.0,
        "waiting_cost_per_hour": 100.0,
        "risk_buffer_pct": 0.05,
        "minimum_profit_margin_pct": 0.15
    },
    {
        "parameter_id": "PARAM-MINITRUCK",
        "vehicle_type": "Mini Truck",
        "driver_cost_per_hour": 180.0,
        "maintenance_cost_per_km": 4.0,
        "loading_cost": 150.0,
        "unloading_cost": 150.0,
        "waiting_cost_per_hour": 120.0,
        "risk_buffer_pct": 0.05,
        "minimum_profit_margin_pct": 0.18
    },
    {
        "parameter_id": "PARAM-LCV",
        "vehicle_type": "LCV",
        "driver_cost_per_hour": 200.0,
        "maintenance_cost_per_km": 5.0,
        "loading_cost": 200.0,
        "unloading_cost": 200.0,
        "waiting_cost_per_hour": 150.0,
        "risk_buffer_pct": 0.05,
        "minimum_profit_margin_pct": 0.18
    },
    {
        "parameter_id": "PARAM-MEDIUMTRUCK",
        "vehicle_type": "Medium Truck",
        "driver_cost_per_hour": 220.0,
        "maintenance_cost_per_km": 6.0,
        "loading_cost": 250.0,
        "unloading_cost": 250.0,
        "waiting_cost_per_hour": 180.0,
        "risk_buffer_pct": 0.06,
        "minimum_profit_margin_pct": 0.20
    },
    {
        "parameter_id": "PARAM-REEFER",
        "vehicle_type": "Refrigerated Truck",
        "driver_cost_per_hour": 280.0,
        "maintenance_cost_per_km": 8.5,
        "loading_cost": 300.0,
        "unloading_cost": 300.0,
        "waiting_cost_per_hour": 250.0,
        "risk_buffer_pct": 0.08,
        "minimum_profit_margin_pct": 0.22
    },
    {
        "parameter_id": "PARAM-HEAVYTRUCK",
        "vehicle_type": "Heavy Truck",
        "driver_cost_per_hour": 300.0,
        "maintenance_cost_per_km": 10.0,
        "loading_cost": 400.0,
        "unloading_cost": 400.0,
        "waiting_cost_per_hour": 250.0,
        "risk_buffer_pct": 0.07,
        "minimum_profit_margin_pct": 0.20
    },
    {
        "parameter_id": "PARAM-TRACTOR",
        "vehicle_type": "Tractor + Trailer",
        "driver_cost_per_hour": 200.0,
        "maintenance_cost_per_km": 6.5,
        "loading_cost": 250.0,
        "unloading_cost": 250.0,
        "waiting_cost_per_hour": 150.0,
        "risk_buffer_pct": 0.06,
        "minimum_profit_margin_pct": 0.18
    }
]


async def seed_transport_data():
    await init_db()
    async with AsyncSessionLocal() as session:
        logger.info("Seeding Transport Agent database tables...")

        # 1. Vehicles
        for vdata in SEED_VEHICLES:
            existing = await session.get(DBVehicle, vdata["vehicle_id"])
            if not existing:
                session.add(DBVehicle(**vdata))

        # 2. Fuel Prices
        for fpdata in SEED_FUEL_PRICES:
            existing = await session.get(DBFuelPrice, fpdata["fuel_price_id"])
            if not existing:
                session.add(DBFuelPrice(**fpdata))

        # 3. Toll Rates
        for tldata in SEED_TOLL_RATES:
            existing = await session.get(DBTollRate, tldata["toll_id"])
            if not existing:
                session.add(DBTollRate(**tldata))

        # 4. Cost Parameters
        for pdata in SEED_COST_PARAMETERS:
            existing = await session.get(DBTransportCostParameter, pdata["parameter_id"])
            if not existing:
                session.add(DBTransportCostParameter(**pdata))

        await session.commit()
        logger.info("Transport Agent data successfully seeded!")


if __name__ == "__main__":
    asyncio.run(seed_transport_data())
