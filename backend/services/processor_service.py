"""
backend/services/processor_service.py

Processor / Value-Added Processing Service — FR-11

Manages industrial processor listings and order submission for
crops that failed direct sale and are escalated to processing.
"""

import uuid
from datetime import datetime, timezone
from copy import deepcopy
from typing import Dict, List

_PROCESSOR_CATALOG: List[Dict] = [
    {
        "processor_id": "proc_sugar_kolhapur",
        "name": "Shree Chhatrapati Sugar & Ethanol Mills",
        "crop_types": ["Sugarcane"],
        "price_per_kg": 3.75,
        "capacity_kg": 50000,
        "location": "Kolhapur",
        "output_product": "Refined Sugar / Ethanol / Jaggery (Gul)",
        "min_order_kg": 1000,
    },
    {
        "processor_id": "proc_soy_latur",
        "name": "Marathwada Solvent Extractions & Soya Foods",
        "crop_types": ["Soybean"],
        "price_per_kg": 68.0,
        "capacity_kg": 20000,
        "location": "Latur",
        "output_product": "Refined Soybean Oil / De-oiled Cake (DOC) / Soya Flour",
        "min_order_kg": 500,
    },
    {
        "processor_id": "proc_cotton_amravati",
        "name": "Vidarbha Ginning & Spinning Textiles Ltd",
        "crop_types": ["Cotton"],
        "price_per_kg": 64.5,
        "capacity_kg": 15000,
        "location": "Amravati",
        "output_product": "Baled Lint / Cotton Yarn / Cottonseed Oil",
        "min_order_kg": 500,
    },
    {
        "processor_id": "proc_onion_dehydration_nashik",
        "name": "Nashik Agro Dehydration Plant",
        "crop_types": ["Onion"],
        "price_per_kg": 19.5,
        "capacity_kg": 10000,
        "location": "Nashik",
        "output_product": "Dehydrated Onion Flakes / Onion Powder / Puree",
        "min_order_kg": 200,
    },
    {
        "processor_id": "proc_grains_solapur",
        "name": "Solapur Millets & Flour Processing Corp",
        "crop_types": ["Jowar", "Bajra"],
        "price_per_kg": 38.0,
        "capacity_kg": 12000,
        "location": "Solapur",
        "output_product": "Fortified Jowar & Bajra Flour / Malt / Poultry Feed",
        "min_order_kg": 300,
    },
    {
        "processor_id": "proc_rice_bhandara",
        "name": "Wainganga Modern Rice Mill",
        "crop_types": ["Rice"],
        "price_per_kg": 34.0,
        "capacity_kg": 25000,
        "location": "Bhandara",
        "output_product": "Milled Grade A Rice / Parboiled Rice / Poha / Bran Oil",
        "min_order_kg": 500,
    },
]

# In-memory order store
_processor_orders: Dict[str, Dict] = {}


async def list_processors(crop: str = None) -> List[Dict]:
    """List available processors, optionally filtered by crop type."""
    if not crop:
        return deepcopy(_PROCESSOR_CATALOG)
    return [
        deepcopy(p) for p in _PROCESSOR_CATALOG
        if any(crop.lower() in c.lower() for c in p["crop_types"])
    ]


async def submit_processing_order(order: Dict) -> Dict:
    """
    Submit a crop lot to a processor.

    Required fields: negotiation_id, processor_id, crop, quantity, farmer_id
    """
    processor_id = order.get("processor_id")
    processor = next((p for p in _PROCESSOR_CATALOG if p["processor_id"] == processor_id), None)
    if not processor:
        raise ValueError(f"Processor '{processor_id}' not found.")

    quantity = float(order.get("quantity", 0))
    if quantity < processor["min_order_kg"]:
        raise ValueError(
            f"Minimum order for {processor['name']} is {processor['min_order_kg']} kg. Got {quantity} kg."
        )
    if quantity > processor["capacity_kg"]:
        raise ValueError(
            f"Order exceeds processor capacity ({processor['capacity_kg']} kg). Got {quantity} kg."
        )

    total_payment = round(processor["price_per_kg"] * quantity, 2)
    order_id = f"porder_{str(uuid.uuid4())[:8]}"

    record = {
        "order_id": order_id,
        "processor_id": processor_id,
        "processor_name": processor["name"],
        "negotiation_id": order.get("negotiation_id"),
        "farmer_id": order.get("farmer_id"),
        "crop": order.get("crop"),
        "quantity": quantity,
        "price_per_kg": processor["price_per_kg"],
        "total_payment": total_payment,
        "output_product": processor["output_product"],
        "status": "SUBMITTED",
        "submitted_at": datetime.now(timezone.utc).isoformat(),
    }

    _processor_orders[order_id] = record
    return record


async def get_processor_order(order_id: str) -> Dict:
    """Retrieve a processor order by ID."""
    order = _processor_orders.get(order_id)
    if not order:
        raise ValueError(f"Order '{order_id}' not found.")
    return order


async def list_processor_orders(farmer_id: str = None) -> List[Dict]:
    """List all processing orders, optionally filtered by farmer."""
    orders = list(_processor_orders.values())
    if farmer_id:
        orders = [o for o in orders if o.get("farmer_id") == farmer_id]
    return orders

