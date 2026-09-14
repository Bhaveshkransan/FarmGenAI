"""Shelf-life utilities for decision-making in escalation logic."""


CROP_DEFAULT_SHELF_LIFE = {
    "Tomato": 4,
    "Onion": 30,
    "Spinach": 2,
    "Capsicum": 5,
    "Cabbage": 6,
    "Wheat": 180,
    "Rice": 180,
    "Sugarcane": 3,
    "Soybean": 180,
    "Cotton": 365,
    "Jowar": 180,
    "Sorghum": 180,
    "Bajra": 180,
    "Pearl Millet": 180,
    "Maize": 30,
    "Potato": 45,
}


def default_shelf_life(crop: str) -> int:
    """Return default shelf life in days for a given crop name with alias awareness."""
    if not crop:
        return 4
    c_clean = str(crop).strip()
    if c_clean in CROP_DEFAULT_SHELF_LIFE:
        return CROP_DEFAULT_SHELF_LIFE[c_clean]
    
    # Case-insensitive and alias / substring lookup
    c_lower = c_clean.lower()
    for name, days in CROP_DEFAULT_SHELF_LIFE.items():
        if name.lower() in c_lower or c_lower in name.lower():
            return days

    if "cotton" in c_lower:
        return 365
    if any(k in c_lower for k in ["jowar", "sorghum", "bajra", "millet", "soybean", "soya", "rice", "paddy"]):
        return 180
    if "sugarcane" in c_lower or "cane" in c_lower:
        return 3
    if "onion" in c_lower:
        return 30

    return 7


def is_critical(shelf_life_days: int, threshold: int = 2) -> bool:
    """Return True if shelf life is at or below the critical threshold."""
    return shelf_life_days <= threshold


def urgency_level(shelf_life_days: int) -> str:
    """Return 'critical' | 'urgent' | 'normal'."""
    if shelf_life_days <= 2:
        return "critical"
    if shelf_life_days <= 4:
        return "urgent"
    return "normal"
