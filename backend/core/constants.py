"""
backend/core/constants.py

Canonical constants for FarmGenAI — single source of truth.

Rules:
  - backend/core/constants.py is the ONLY place crop names are defined
  - Every route, agent, RAG filter, ML feature key derives from here
  - frontend/src/constants/crops.ts is display-only and must match
  - CROP_MASTER is iterated at startup to validate incoming requests
"""

from typing import Dict, Any

# ─────────────────────────────────────────────────────────────────────────────
# CANONICAL CROP MASTER
# ─────────────────────────────────────────────────────────────────────────────

CROP_MASTER: Dict[str, Dict[str, Any]] = {
    "SUGARCANE": {
        "display_name": "Sugarcane",
        "api_commodity": "Sugarcane",       # key for Mandi/Agmarknet API
        "ml_feature_key": "sugarcane",      # XGBoost feature column name
        "rag_crop_id": "SUGARCANE",         # ChromaDB metadata filter
        "image": "sugarcane.webp",
        "price_unit": "per_quintal",
        "allowed": True,
        "typical_shelf_life_days": 14,
        "crop_group": "KHARIF",
        "min_quantity_kg": 1000,            # minimum viable listing
        "msp_ref_year": "2025-26",
    },
    "SOYBEAN": {
        "display_name": "Soybean",
        "api_commodity": "Soybean",
        "ml_feature_key": "soybean",
        "rag_crop_id": "SOYBEAN",
        "image": "soybean.webp",
        "price_unit": "per_kg",
        "allowed": True,
        "typical_shelf_life_days": 90,
        "crop_group": "KHARIF",
        "min_quantity_kg": 100,
        "msp_ref_year": "2025-26",
    },
    "COTTON": {
        "display_name": "Cotton",
        "api_commodity": "Cotton(Lint)",
        "ml_feature_key": "cotton",
        "rag_crop_id": "COTTON",
        "image": "cotton.webp",
        "price_unit": "per_quintal",
        "allowed": True,
        "typical_shelf_life_days": 180,
        "crop_group": "KHARIF",
        "min_quantity_kg": 100,
        "msp_ref_year": "2025-26",
    },
    "JOWAR": {
        "display_name": "Jowar",
        "api_commodity": "Jowar(Sorghum)",
        "ml_feature_key": "jowar",
        "rag_crop_id": "JOWAR",
        "image": "jowar.webp",
        "price_unit": "per_quintal",
        "allowed": True,
        "typical_shelf_life_days": 180,
        "crop_group": "RABI",
        "min_quantity_kg": 100,
        "msp_ref_year": "2025-26",
    },
    "ONION": {
        "display_name": "Onion",
        "api_commodity": "Onion",
        "ml_feature_key": "onion",
        "rag_crop_id": "ONION",
        "image": "onion.webp",
        "price_unit": "per_kg",
        "allowed": True,
        "typical_shelf_life_days": 4,
        "crop_group": "RABI",
        "min_quantity_kg": 50,
        "msp_ref_year": "N/A",              # Onion has no MSP — uses market reference
    },
    "BAJRA": {
        "display_name": "Bajra",
        "api_commodity": "Bajra(Pearl Millet/Cumbu)",
        "ml_feature_key": "bajra",
        "rag_crop_id": "BAJRA",
        "image": "bajra.webp",
        "price_unit": "per_quintal",
        "allowed": True,
        "typical_shelf_life_days": 120,
        "crop_group": "KHARIF",
        "min_quantity_kg": 100,
        "msp_ref_year": "2025-26",
    },
    "RICE": {
        "display_name": "Rice",
        "api_commodity": "Paddy(Dhan)(Common)",
        "ml_feature_key": "rice",
        "rag_crop_id": "RICE",
        "image": "rice.webp",
        "price_unit": "per_quintal",
        "allowed": True,
        "typical_shelf_life_days": 365,
        "crop_group": "KHARIF",
        "min_quantity_kg": 100,
        "msp_ref_year": "2025-26",
    },
}

# Flat lists derived from master — do NOT redefine elsewhere
SUPPORTED_CROPS = [v["display_name"] for v in CROP_MASTER.values() if v["allowed"]]
SUPPORTED_CROP_IDS = [k for k, v in CROP_MASTER.items() if v["allowed"]]

# Fast lookup: display_name.lower() → canonical ID
_DISPLAY_TO_ID: Dict[str, str] = {
    v["display_name"].lower(): k for k, v in CROP_MASTER.items()
}
# Fast lookup: api_commodity.lower() → canonical ID
_API_COMMODITY_TO_ID: Dict[str, str] = {
    v["api_commodity"].lower(): k for k, v in CROP_MASTER.items()
}


def normalize_crop_id(raw_crop: str) -> str | None:
    """
    Convert any incoming crop string to its canonical CROP_MASTER key.

    Accepts:
      - canonical ID:    "ONION"     → "ONION"
      - display name:    "Onion"     → "ONION"
      - api commodity:   "Onion"     → "ONION"
      - any case:        "onion"     → "ONION"

    Returns None if crop is not in the 7-crop master.
    """
    if not raw_crop:
        return None
    raw_lower = raw_crop.strip().lower()

    # Try canonical ID first
    if raw_lower.upper() in CROP_MASTER:
        return raw_lower.upper()

    # Try display name
    if raw_lower in _DISPLAY_TO_ID:
        return _DISPLAY_TO_ID[raw_lower]

    # Try API commodity name
    if raw_lower in _API_COMMODITY_TO_ID:
        return _API_COMMODITY_TO_ID[raw_lower]

    return None


def get_crop_info(crop_id_or_name: str) -> Dict[str, Any] | None:
    """Get full crop metadata from canonical ID or display name."""
    cid = normalize_crop_id(crop_id_or_name)
    return CROP_MASTER.get(cid) if cid else None


def validate_crop(raw_crop: str) -> tuple[bool, str]:
    """
    Returns (is_valid, error_message).
    Use in FastAPI route validators.
    """
    cid = normalize_crop_id(raw_crop)
    if not cid:
        return False, (
            f"Unsupported crop: '{raw_crop}'. "
            f"Supported crops: {', '.join(SUPPORTED_CROPS)}"
        )
    return True, ""


# ─────────────────────────────────────────────────────────────────────────────
# WORKFLOW SCOPE MODEL
# ─────────────────────────────────────────────────────────────────────────────

class WorkflowMode:
    FULL_SUPPLY_CHAIN = "FULL_SUPPLY_CHAIN"
    BUYER_ONLY        = "BUYER_ONLY"
    TRANSPORT_ONLY    = "TRANSPORT_ONLY"
    WAREHOUSE_ONLY    = "WAREHOUSE_ONLY"
    PROCESSOR_ONLY    = "PROCESSOR_ONLY"

    ALL_MODES = [
        FULL_SUPPLY_CHAIN,
        BUYER_ONLY,
        TRANSPORT_ONLY,
        WAREHOUSE_ONLY,
        PROCESSOR_ONLY,
    ]


def get_allowed_agents(stakeholder_role: str, workflow_mode: str) -> list:
    """
    Returns the list of LangGraph agents allowed to execute based on the stakeholder 
    and their selected workflow scope (Stakeholder-Aware Modular Orchestration).
    """
    base_agents = [
        "planner_agent", 
        "market_intelligence_agent", 
        "matching_agent", 
        "rank_responses_agent", 
        "validator_agent", 
        "reflection_agent"
    ]
    
    stakeholder = str(stakeholder_role).upper()
    mode = str(workflow_mode).upper()
    
    allowed = list(base_agents)
    
    if stakeholder == "FARMER":
        allowed.append("farmer_agent")
        if mode == WorkflowMode.FULL_SUPPLY_CHAIN:
            allowed.extend(["buyer_agent", "dynamic_routing_agent", "transport_agent", "warehouse_agent", "processor_agent"])
        elif mode == WorkflowMode.BUYER_ONLY:
            allowed.append("buyer_agent")
        elif mode == WorkflowMode.TRANSPORT_ONLY:
            allowed.extend(["dynamic_routing_agent", "transport_agent"])
        elif mode == WorkflowMode.WAREHOUSE_ONLY:
            allowed.extend(["dynamic_routing_agent", "warehouse_agent"])
        elif mode == WorkflowMode.PROCESSOR_ONLY:
            allowed.extend(["dynamic_routing_agent", "processor_agent"])
            
    elif stakeholder == "BUYER":
        allowed.append("buyer_agent")
        if mode == WorkflowMode.FULL_SUPPLY_CHAIN:
            allowed.extend(["farmer_agent", "dynamic_routing_agent", "transport_agent", "warehouse_agent", "processor_agent"])
        elif mode == WorkflowMode.BUYER_ONLY or mode == "FARMER_ONLY" or mode == "SUPPLIER_ONLY":
            allowed.append("farmer_agent")
        elif mode == WorkflowMode.TRANSPORT_ONLY:
            allowed.extend(["dynamic_routing_agent", "transport_agent"])
        elif mode == WorkflowMode.WAREHOUSE_ONLY:
            allowed.extend(["dynamic_routing_agent", "warehouse_agent"])
        elif mode == WorkflowMode.PROCESSOR_ONLY:
            allowed.extend(["dynamic_routing_agent", "processor_agent"])
            
    elif stakeholder == "PROCESSOR":
        allowed.append("processor_agent")
        if mode == WorkflowMode.FULL_SUPPLY_CHAIN:
            allowed.extend(["farmer_agent", "buyer_agent", "dynamic_routing_agent", "transport_agent", "warehouse_agent"])
        elif mode == WorkflowMode.BUYER_ONLY or mode == "SUPPLIER_ONLY":
            allowed.append("farmer_agent")
        elif mode == WorkflowMode.TRANSPORT_ONLY:
            allowed.extend(["dynamic_routing_agent", "transport_agent"])
        elif mode == WorkflowMode.WAREHOUSE_ONLY:
            allowed.extend(["dynamic_routing_agent", "warehouse_agent"])
            
    elif stakeholder == "WAREHOUSE":
        allowed.append("warehouse_agent")
        if mode == WorkflowMode.FULL_SUPPLY_CHAIN:
            allowed.extend(["farmer_agent", "buyer_agent", "dynamic_routing_agent", "transport_agent", "processor_agent"])
        elif mode == WorkflowMode.TRANSPORT_ONLY:
            allowed.extend(["dynamic_routing_agent", "transport_agent"])
        elif mode == WorkflowMode.WAREHOUSE_ONLY:
            allowed.extend(["dynamic_routing_agent", "warehouse_agent"])
            
    elif stakeholder == "TRANSPORTER":
        allowed.extend(["dynamic_routing_agent", "transport_agent"])
        if mode == WorkflowMode.FULL_SUPPLY_CHAIN:
            allowed.extend(["farmer_agent", "buyer_agent"])
            
    # Fallback/Safe Default if no exact match (only allow base orchestration + self)
    return list(set(allowed))


# ─────────────────────────────────────────────────────────────────────────────
# STATUTORY BENCHMARKS (MSP-based guardrails)
# Keep in sync with negotiation_service.py STATUTORY_BENCHMARKS
# ─────────────────────────────────────────────────────────────────────────────

STATUTORY_BENCHMARKS: Dict[str, Dict[str, float]] = {
    "Sugarcane": {"benchmark": 315.0,  "unit": "per_quintal"},  # FRP 2025-26
    "Soybean":   {"benchmark": 43.36,  "unit": "per_kg"},       # MSP 2025-26: ₹4336/quintal
    "Cotton":    {"benchmark": 70.21,  "unit": "per_kg"},       # MSP 2025-26: ₹7021/quintal (medium)
    "Jowar":     {"benchmark": 33.71,  "unit": "per_kg"},       # MSP 2025-26: ₹3371/quintal (hybrid)
    "Onion":     {"benchmark": 15.0,   "unit": "per_kg"},       # Market reference (no official MSP)
    "Bajra":     {"benchmark": 25.50,  "unit": "per_kg"},       # MSP 2025-26: ₹2550/quintal
    "Rice":      {"benchmark": 23.00,  "unit": "per_kg"},       # MSP 2025-26: ₹2300/quintal (common)
}

# Ceiling = max(target_price × 1.35, benchmark × 1.40) — anti-hallucination guard
# Floor   = benchmark × 0.35                            — anti-predatory guard


# ─────────────────────────────────────────────────────────────────────────────
# MAHARASHTRA DISTRICTS (36)
# ─────────────────────────────────────────────────────────────────────────────

MAHARASHTRA_DISTRICTS = [
    "Ahmednagar", "Akola", "Amravati", "Aurangabad", "Beed",
    "Bhandara", "Buldhana", "Chandrapur", "Dhule", "Gadchiroli",
    "Gondia", "Hingoli", "Jalgaon", "Jalna", "Kolhapur",
    "Latur", "Mumbai", "Mumbai Suburban", "Nagpur", "Nanded",
    "Nandurbar", "Nashik", "Osmanabad", "Palghar", "Parbhani",
    "Pune", "Raigad", "Ratnagiri", "Sangli", "Satara",
    "Sindhudurg", "Solapur", "Thane", "Wardha", "Washim",
    "Yavatmal",
]
