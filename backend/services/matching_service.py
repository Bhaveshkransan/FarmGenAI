"""
backend/services/matching_service.py

Matching Engine Service — pairs farmer crop listings with buyer requirements.
Implements FR-5: AI-Powered Matching Engine

Scoring factors:
  1. Price compatibility   (40%)
  2. Quantity feasibility  (25%)
  3. Geographic proximity  (20%)
  4. Trust score           (15%)
"""

from backend.repositories.user_repository import UserRepository
import logging
from typing import List, Dict, Optional
from database.db import Database

logger = logging.getLogger("MatchingService")


CITY_DISTANCES_KM: Dict[str, Dict[str, float]] = {
    "Nashik":     {"Nashik": 0, "Pune": 210, "Mumbai": 170, "Nagpur": 450, "Kalyan": 180, "Thane": 165},
    "Pune":       {"Nashik": 210, "Pune": 0, "Mumbai": 150, "Nagpur": 580, "Kalyan": 130, "Thane": 145},
    "Mumbai":     {"Nashik": 170, "Pune": 150, "Mumbai": 0, "Nagpur": 830, "Kalyan": 55, "Thane": 40},
    "Nagpur":     {"Nashik": 450, "Pune": 580, "Mumbai": 830, "Nagpur": 0, "Kalyan": 800, "Thane": 795},
    "Kalyan":     {"Nashik": 180, "Pune": 130, "Mumbai": 55, "Nagpur": 800, "Kalyan": 0, "Thane": 20},
    "Thane":      {"Nashik": 165, "Pune": 145, "Mumbai": 40, "Nagpur": 795, "Kalyan": 20, "Thane": 0},
    "Aurangabad": {"Nashik": 190, "Pune": 230, "Mumbai": 340, "Nagpur": 330, "Kalyan": 300, "Thane": 310},
    "Satara":     {"Nashik": 270, "Pune": 110, "Mumbai": 255, "Nagpur": 690, "Kalyan": 210, "Thane": 225},
    "Ahmednagar": {"Nashik": 120, "Pune": 120, "Mumbai": 275, "Nagpur": 570, "Kalyan": 245, "Thane": 260},
}

MAX_MATCH_DISTANCE_KM = 600.0


async def _get_distance_km(loc_a: str, loc_b: str) -> float:
    """Estimate distance between two locations."""
    if not loc_a or not loc_b:
        return 150.0
    if loc_a == loc_b:
        return 0.0
    a = loc_a.strip()
    b = loc_b.strip()
    dist = CITY_DISTANCES_KM.get(a, {}).get(b)
    if dist is None:
        dist = CITY_DISTANCES_KM.get(b, {}).get(a)
    return dist if dist is not None else 250.0  # default


async def _score_match(listing: Dict, requirement: Dict, buyer_user: Optional[Dict] = None) -> float:
    """
    Compute a 0-100 compatibility score between a crop listing and buyer requirement.
    """
    score = 0.0

    # ── Price compatibility (40 pts) ──────────────────────
    min_price = float(listing.get("min_price", 0))
    target_price = float(requirement.get("target_price", 0))
    max_price = float(requirement.get("max_price") or target_price * 1.2)

    if target_price >= min_price:
        score += 40.0  # Full compatibility
    elif max_price >= min_price:
        # Partial: within budget ceiling
        ratio = (max_price - min_price) / max(max_price, 1)
        score += max(0, 20 + ratio * 20)
    else:
        score += 0.0  # Price incompatible

    # ── Quantity feasibility (25 pts) ──────────────────────
    avail_qty = float(listing.get("quantity", 0))
    req_qty = float(requirement.get("quantity", 0))
    budget = float(requirement.get("budget", 0))
    budget_qty = budget / max(target_price, 1)

    fulfillable_qty = min(avail_qty, req_qty, budget_qty)
    if req_qty > 0:
        ratio = min(fulfillable_qty / req_qty, 1.0)
        score += ratio * 25

    # ── Geographic proximity (20 pts) ─────────────────────
    listing_loc = listing.get("location", "")
    req_loc = requirement.get("location", "")
    dist = await _get_distance_km(listing_loc, req_loc)
    if dist <= MAX_MATCH_DISTANCE_KM:
        proximity_score = max(0, 1.0 - dist / MAX_MATCH_DISTANCE_KM) * 20
        score += proximity_score

    # ── Trust score (15 pts) ──────────────────────────────
    trust = float((buyer_user or {}).get("trust_score", 3.5))
    score += min(trust / 5.0, 1.0) * 15

    return round(score, 2)


async def match_listing_to_buyers(listing: Dict) -> List[Dict]:
    """
    Find and score all buyer requirements that match a given crop listing.
    Returns ranked list of matches.
    """
    buyers = await Database.list_buyers_async()
    all_requirements = [r for r in buyers if r.get("kind") == "requirement" and r.get("status") == "ACTIVE"]
    
    # Also include simulated buyers / default profiles that might not explicitly have kind="requirement"
    if not all_requirements:
        all_requirements = [b for b in buyers if b.get("kind") != "offer"]

    results = []
    for req in all_requirements:
        # Crop must match (case-insensitive)
        req_crop = req.get("crop", "")
        list_crop = listing.get("crop", "")
        if req_crop and list_crop and req_crop.lower() != list_crop.lower():
            continue

        buyer_user = await UserRepository.get_by_id(req.get("user_id", "")) or {}
        score = await _score_match(listing, req, buyer_user)
        dist = await _get_distance_km(listing.get("location", ""), req.get("location", ""))
        
        # Calculate derived offer details similar to negotiation_service
        req_qty = float(req.get("quantity") or req.get("max_quantity") or listing.get("quantity", 0))
        offered_qty = min(float(listing.get("quantity", 0)), req_qty)
        min_price = float(listing.get("min_price", 0))
        market_price = float(listing.get("market_price", min_price + 1))
        target_price = float(req.get("target_price") or req.get("max_price") or (min_price * 1.05))

        raw_budget = float(req.get("budget", 0))
        budget = raw_budget if raw_budget > 0 else max(target_price * req_qty * 1.2, min_price * offered_qty * 1.1)
        budget_limited_price = budget / max(offered_qty, 1)
        
        strategy = str(req.get("strategy", "")).lower()
        
        if "restaurant" in strategy or "premium" in strategy:
            opening_bid = min(target_price * 0.95, budget_limited_price)
        else:
            # High-feasibility opening offer: between 88% to 98% of target/market, capped by budget
            base_offer = max(target_price * 0.92, min_price if target_price >= min_price else target_price * 0.88)
            opening_bid = min(target_price, budget_limited_price, max(base_offer, 1.0))
            
        offer_price = round(max(1.0, opening_bid), 2)
        is_viable = offer_price >= min_price

        # Strategic Labelling
        label = "Market Option"
        if is_viable:
            if score > 75: label = "👑 Best Profit"
            elif dist == 0: label = "⚡ Fast Handshake"
            elif "restaurant" in strategy: label = "💎 Premium Match"
            elif score > 50: label = "🎯 Strategic Fit"

        results.append({
            "requirement_id": req.get("requirement_id") or req.get("id"),
            "buyer_id": req.get("user_id") or req.get("id"),
            "buyer_name": req.get("buyer_name") or req.get("name", "Unknown Buyer"),
            "crop": req.get("crop") or list_crop,
            "quantity": req_qty,
            "target_price": target_price,
            "max_price": req.get("max_price"),
            "budget": budget,
            "location": req.get("location", "Market"),
            "strategy": label,
            "offered_price": offer_price,
            "offered_quantity": round(offered_qty, 2),
            "status": "VIABLE" if is_viable else "BELOW_MIN_PRICE",
            "distance_km": dist,
            "compatibility_score": score,
            "score": score, # Alias for compatibility
            "match_grade": "A" if score >= 70 else "B" if score >= 45 else "C",
            "notes": req.get("notes", ""),
        })

    results.sort(key=lambda item: (item["status"] == "VIABLE", item["offered_price"], item["compatibility_score"]), reverse=True)
    return results


async def match_requirement_to_listings(requirement: Dict) -> List[Dict]:
    """
    Find and score all active crop listings that match a buyer requirement.
    """
    from backend.routes.crop_listing_routes import router as _  # ensure module loaded
    listings = await Database.list_produce_async()
    active = [l for l in listings if l.get("status") in ("LISTED", "ACTIVE")]

    results = []
    for listing in active:
        if listing.get("crop", "").lower() != requirement.get("crop", "").lower():
            continue

        buyer_user = await UserRepository.get_by_id(requirement.get("user_id", "")) or {}
        score = await _score_match(listing, requirement, buyer_user)
        dist = await _get_distance_km(listing.get("location", ""), requirement.get("location", ""))

        results.append({
            "listing_id": listing.get("id"),
            "farmer_name": listing.get("farmer_name"),
            "farmer_id": listing.get("user_id"),
            "crop": listing.get("crop"),
            "quantity": listing.get("quantity"),
            "min_price": listing.get("min_price"),
            "location": listing.get("location"),
            "spoilage_days": listing.get("spoilage_days", listing.get("shelf_life", 7)),
            "quality": listing.get("quality", "A"),
            "distance_km": dist,
            "compatibility_score": score,
            "match_grade": "A" if score >= 70 else "B" if score >= 45 else "C",
        })

    results.sort(key=lambda x: x["compatibility_score"], reverse=True)
    return results

