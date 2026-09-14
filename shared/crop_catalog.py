"""
shared/crop_catalog.py
------------------------------------------------------------------------
Authoritative Agricultural Crop Catalog & Normalization Service for AgriNegotiator.

BuyerAgent is strictly restricted to ONLY 7 Maharashtra agricultural crops:
  1. Sugarcane (FRP - Fair & Remunerative Price)
  2. Soybean (MSP - Minimum Support Price)
  3. Cotton (MSP - Minimum Support Price)
  4. Jowar (MSP - Minimum Support Price)
  5. Onion (APMC Mandi Modal Rate — Note: No central MSP exists)
  6. Bajra (MSP - Minimum Support Price)
  7. Rice (MSP - Minimum Support Price)

All other crops (Tomato, Wheat, Potato, Maize, Cabbage, etc.) MUST be rejected.
"""

from typing import Dict, List, Optional, Tuple, Any
import re

# ─────────────────────────────────────────────────────────────────────────────
# Canonical 7 Crops Definition & Official Government of India Benchmark Data
# ─────────────────────────────────────────────────────────────────────────────

BUYER_SUPPORTED_CROPS: Dict[str, Dict[str, Any]] = {
    "Sugarcane": {
        "canonical_name": "Sugarcane",
        "category": "Cash / Industrial Crop",
        "pricing_mechanism": "FRP",  # Fair & Remunerative Price (DO NOT call MSP)
        "frp_price_per_quintal": 340.00,  # 2024-25 CCEA benchmark (₹355 for 2025-26)
        "frp_price_per_kg": 3.40,
        "msp_price_per_kg": None,  # Explicitly None: Sugarcane uses FRP, not MSP
        "modal_price_range_per_kg": (3.20, 4.20),
        "primary_mandi": "Kolhapur APMC",
        "perishable": False,
        "storage_viable": False,  # Crushed immediately at mills
        "shelf_life_days": 3,  # Invert sugar degradation begins rapidly post-harvest
        "aliases": [
            "sugarcane", "cane", "ganna", "sugar cane", "sugarcane (ganna)",
            "sugar-cane", "oos", "sugar_cane"
        ]
    },
    "Soybean": {
        "canonical_name": "Soybean",
        "category": "Oilseed / Commercial",
        "pricing_mechanism": "MSP",
        "frp_price_per_kg": None,
        "msp_price_per_quintal": 4892.00,  # 2024-25 MSP benchmark (5328 in projection)
        "msp_price_per_kg": 48.92,
        "modal_price_range_per_kg": (42.00, 55.00),
        "primary_mandi": "Latur APMC",
        "perishable": False,
        "storage_viable": True,
        "shelf_life_days": 180,
        "aliases": [
            "soybean", "soya", "soyabean", "yellow soybean", "soya bean",
            "soy", "glycine max", "soya-bean"
        ]
    },
    "Cotton": {
        "canonical_name": "Cotton",
        "category": "Fibre / Cash Crop",
        "pricing_mechanism": "MSP",
        "frp_price_per_kg": None,
        "msp_price_per_quintal": 7121.00,  # Medium staple MSP (7521 for long staple)
        "msp_price_per_kg": 71.21,
        "modal_price_range_per_kg": (68.00, 78.00),
        "primary_mandi": "Jalgaon APMC",
        "perishable": False,
        "storage_viable": True,
        "shelf_life_days": 365,
        "aliases": [
            "cotton", "kapas", "raw cotton", "medium staple cotton",
            "long staple cotton", "kapaas", "rui", "raw_cotton"
        ]
    },
    "Jowar": {
        "canonical_name": "Jowar",
        "category": "Coarse Grain / Nutri-Cereal",
        "pricing_mechanism": "MSP",
        "frp_price_per_kg": None,
        "msp_price_per_quintal": 3371.00,  # Hybrid (3421 for Maldandi)
        "msp_price_per_kg": 33.71,
        "modal_price_range_per_kg": (29.00, 38.00),
        "primary_mandi": "Solapur APMC",
        "perishable": False,
        "storage_viable": True,
        "shelf_life_days": 270,
        "aliases": [
            "jowar", "sorghum", "maldandi jowar", "jowari", "sorghum bicolor",
            "great millet", "shalu jowar", "jowar (sorghum)"
        ]
    },
    "Onion": {
        "canonical_name": "Onion",
        "category": "Perishable / Vegetable",
        "pricing_mechanism": "MANDI_MODAL",  # NO CENTRAL MSP EXISTS FOR ONION
        "frp_price_per_kg": None,
        "msp_price_per_quintal": None,  # Explicitly None: No central MSP
        "msp_price_per_kg": None,
        "modal_price_range_per_kg": (15.00, 26.00),
        "primary_mandi": "Lasalgaon APMC (Nashik)",
        "perishable": True,
        "storage_viable": True,  # Aerated onion chawls
        "shelf_life_days": 21,  # Depends on moisture & sprout inhibition
        "aliases": [
            "onion", "onions", "kanda", "pyaz", "red onion", "garva onion",
            "pol onion", "kanda (onion)", "pyaaz", "nasik onion"
        ]
    },
    "Bajra": {
        "canonical_name": "Bajra",
        "category": "Millet / Nutri-Cereal",
        "pricing_mechanism": "MSP",
        "frp_price_per_kg": None,
        "msp_price_per_quintal": 2625.00,  # 2024-25 MSP
        "msp_price_per_kg": 26.25,
        "modal_price_range_per_kg": (23.00, 30.00),
        "primary_mandi": "Ahmednagar APMC",
        "perishable": False,
        "storage_viable": True,
        "shelf_life_days": 240,
        "aliases": [
            "bajra", "pearl millet", "cumbu", "sajje", "bajri",
            "pearl_millet", "pennisetum glaucum", "bajra (pearl millet)"
        ]
    },
    "Rice": {
        "canonical_name": "Rice",
        "category": "Staple Cereal / Grain",
        "pricing_mechanism": "MSP",
        "frp_price_per_kg": None,
        "msp_price_per_quintal": 2300.00,  # Common Paddy (2320 for Grade A)
        "msp_price_per_kg": 23.00,
        "modal_price_range_per_kg": (22.00, 36.00),
        "primary_mandi": "Bhandara / Gondia APMC",
        "perishable": False,
        "storage_viable": True,
        "shelf_life_days": 365,
        "aliases": [
            "rice", "paddy", "dhan", "chawal", "basmati", "common paddy",
            "kolam rice", "indrayani rice", "paddy (common)", "paddy (dhan)"
        ]
    }
}

# Inverted alias lookup table for O(1) matching
CROP_ALIAS_LOOKUP: Dict[str, str] = {}
for canonical, meta in BUYER_SUPPORTED_CROPS.items():
    CROP_ALIAS_LOOKUP[canonical.lower()] = canonical
    for alias in meta["aliases"]:
        CROP_ALIAS_LOOKUP[alias.lower().strip()] = canonical


# ─────────────────────────────────────────────────────────────────────────────
# Normalization & Validation Functions
# ─────────────────────────────────────────────────────────────────────────────

def normalize_crop_name(crop_input: Any) -> Optional[str]:
    """
    Normalizes a crop string or alias to the canonical TitleCase crop name.
    
    Returns:
        Canonical crop name ('Sugarcane', 'Soybean', 'Cotton', 'Jowar',
        'Onion', 'Bajra', 'Rice') if valid, else None.
    """
    if not crop_input or not isinstance(crop_input, str):
        return None
    
    cleaned = crop_input.strip().lower()
    
    # 1. Exact alias match
    if cleaned in CROP_ALIAS_LOOKUP:
        return CROP_ALIAS_LOOKUP[cleaned]
    
    # 2. Strip common parentheses e.g. "Jowar (Sorghum)" -> "jowar"
    sub_match = re.sub(r"\(.*?\)", "", cleaned).strip()
    if sub_match in CROP_ALIAS_LOOKUP:
        return CROP_ALIAS_LOOKUP[sub_match]

    # 3. Substring check against canonical names and main aliases
    for alias, canonical in CROP_ALIAS_LOOKUP.items():
        if alias in cleaned or cleaned in alias:
            return canonical

    return None


def is_supported_buyer_crop(crop_input: Any) -> bool:
    """Returns True if the crop is one of the 7 supported Maharashtra crops."""
    return normalize_crop_name(crop_input) is not None


def validate_buyer_crop(crop_input: Any) -> str:
    """
    Strict validation helper. Returns canonical crop name if valid.
    Raises ValueError with a helpful message if unsupported.
    """
    canonical = normalize_crop_name(crop_input)
    if not canonical:
        allowed = ", ".join(list(BUYER_SUPPORTED_CROPS.keys()))
        raise ValueError(
            f"Unsupported crop '{crop_input}'. BuyerAgent strictly supports only "
            f"the 7 Maharashtra crops: {allowed}. Non-supported produce "
            f"(e.g. Tomato, Wheat, Potato, Maize, Cabbage) cannot enter BuyerAgent negotiation."
        )
    return canonical


def get_crop_benchmark_info(crop_input: Any) -> Optional[Dict[str, Any]]:
    """Returns official GoI metadata (FRP/MSP/Mandi modal rate) for a valid crop."""
    canonical = normalize_crop_name(crop_input)
    if not canonical:
        return None
    return BUYER_SUPPORTED_CROPS[canonical]
