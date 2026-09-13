"""Shelf-life utilities for decision-making in escalation logic."""


CROP_DEFAULT_SHELF_LIFE = {
    "Sugarcane": 2,    # Must be crushed within 24-48 hrs of harvest
    "Soybean":   180,  # Dry godown
    "Cotton":    365,  # Dry warehouse
    "Jowar":     180,  # Dry grain storage
    "Onion":     45,   # Aerated farm storage / APMC shed
    "Bajra":     180,  # Dry grain storage
    "Rice":      365,  # Milled / Paddy storage
}


def default_shelf_life(crop: str) -> int:
    """Return default shelf life in days for a given crop name."""
    return CROP_DEFAULT_SHELF_LIFE.get(crop, 4)


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
