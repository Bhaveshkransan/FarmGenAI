"""
backend/services/matching_service.py

Matching Engine Service — pairs farmer crop listings with buyer requirements.
Implements FR-5: AI-Powered Matching Engine

Scoring factors (8-factor NRV model):
  1. Base price compatibility   (20%)
  2. Quantity match             (20%)
  3. Distance proximity         (15%)
  4. Trust & Reliability        (15%)
  5. Quality & Grade match      (10%)
  6. Urgency / Spoilage match   (10%)
  7. Transport cost efficiency  (5%)
  8. Storage cost efficiency    (5%)
"""

from backend.repositories.user_repository import UserRepository
import logging
from typing import List, Dict, Optional, Any
from database.db import Database
from shared.crop_catalog import normalize_crop_name

logger = logging.getLogger("MatchingService")


def crops_match(crop_a: str, crop_b: str) -> bool:
    norm_a = normalize_crop_name(crop_a)
    norm_b = normalize_crop_name(crop_b)
    if norm_a and norm_b:
        return norm_a == norm_b
    if not norm_a and not norm_b:
        raw_a = (crop_a or "").strip().lower()
        raw_b = (crop_b or "").strip().lower()
        return bool(raw_a and raw_b and raw_a == raw_b)
    return False



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


MAHARASHTRA_DISTRICT_COORDS: Dict[str, tuple] = {
    "Pune": (18.5204, 73.8567),
    "Mumbai": (19.0760, 72.8777),
    "Nashik": (19.9975, 73.7898),
    "Nagpur": (21.1458, 79.0882),
    "Thane": (19.2183, 72.9781),
    "Kalyan": (19.2437, 73.1355),
    "Aurangabad": (19.8762, 75.3433),
    "Ahmednagar": (19.0948, 74.7480),
    "Satara": (17.6805, 74.0183),
    "Solapur": (17.6599, 75.9064),
    "Kolhapur": (16.7050, 74.2433),
    "Latur": (18.4088, 76.5604),
    "Amravati": (20.9374, 77.7796),
    "Gondia": (21.4600, 80.1900),
    "Jalgaon": (21.0077, 75.5626),
    "Dhule": (20.9042, 74.7749),
    "Nanded": (19.1383, 77.3210),
    "Sangli": (16.8524, 74.5815),
    "Wardha": (20.7453, 78.6022),
    "Yavatmal": (20.3888, 78.1204),
    "Akola": (20.7002, 77.0082),
    "Palghar": (19.6967, 72.7655),
    "Ratnagiri": (16.9902, 73.3120),
    "Beed": (18.9891, 75.7601),
    "Jalna": (19.8410, 75.8864),
    "Bhandara": (21.1667, 79.6500),
    "Dharashiv": (18.1856, 76.0420),
    "Osmanabad": (18.1856, 76.0420)
}

def extract_maharashtra_district(loc: str) -> str:
    if not loc:
        return ""
    loc_lower = str(loc).lower()
    for d in MAHARASHTRA_DISTRICT_COORDS:
        if d.lower() in loc_lower:
            return d
    return str(loc).strip().title()

def get_distance_km_sync(loc_a: str, loc_b: str) -> float:
    """Synchronous distance calculation between two city locations with intelligent district extraction and haversine road fallback."""
    if not loc_a or not loc_b:
        return 150.0
    if loc_a == loc_b:
        return 0.0
    da = extract_maharashtra_district(loc_a)
    db = extract_maharashtra_district(loc_b)
    if da and db and da.lower() == db.lower():
        return 15.0  # Same district cluster / local APMC mandi transit
    
    # 1. Lookup in predefined road distance matrix
    dist = CITY_DISTANCES_KM.get(da, {}).get(db)
    if dist is None:
        dist = CITY_DISTANCES_KM.get(db, {}).get(da)
    if dist is not None:
        return dist
        
    # 2. Highway road approximation via coordinates (1.25x road detour multiplier)
    ca = MAHARASHTRA_DISTRICT_COORDS.get(da)
    cb = MAHARASHTRA_DISTRICT_COORDS.get(db)
    if ca and cb:
        import math
        lat1, lon1 = math.radians(ca[0]), math.radians(ca[1])
        lat2, lon2 = math.radians(cb[0]), math.radians(cb[1])
        dlat = lat2 - lat1
        dlon = lon2 - lon1
        a_val = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
        c_val = 2 * math.asin(math.sqrt(a_val))
        return round(6371.0 * c_val * 1.25, 1)

    return 250.0  # default


async def _get_distance_km(loc_a: str, loc_b: str) -> float:
    """Estimate distance between two locations (async wrapper)."""
    return get_distance_km_sync(loc_a, loc_b)


def compute_match_breakdown_sync(listing: Dict, requirement: Dict, buyer_user: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Compute full 8-factor NRV match score along with per-factor transparent explainability breakdown.
    Provides complete mathematical traceability for candidate ranking.
    """
    breakdown = {}
    
    # 1. Base Price (20 pts)
    p_score = 0.0
    min_price = float(listing.get("min_price") or 0)
    target_price = float(requirement.get("target_price") or 0)
    max_price = float(requirement.get("max_price") or target_price * 1.2)
    if target_price >= min_price:
        p_score = 20.0
    elif max_price >= min_price:
        ratio = (max_price - min_price) / max(max_price, 1)
        p_score = max(0, 10 + ratio * 10)
    breakdown["price_feasibility"] = round(p_score, 2)

    # 2. Quantity (20 pts)
    q_score = 0.0
    avail_qty = float(listing.get("quantity") or 0)
    req_qty = float(requirement.get("quantity") or 0)
    if req_qty > 0 and avail_qty > 0:
        ratio = min(avail_qty, req_qty) / max(avail_qty, req_qty)
        q_score = ratio * 20.0
    breakdown["quantity_fulfillment"] = round(q_score, 2)

    # 3. Distance (15 pts)
    d_score = 0.0
    listing_loc = listing.get("location") or ""
    req_loc = requirement.get("location") or ""
    dist = get_distance_km_sync(listing_loc, req_loc)
    if dist <= MAX_MATCH_DISTANCE_KM:
        d_score = max(0, 1.0 - dist / MAX_MATCH_DISTANCE_KM) * 15.0
    breakdown["distance_proximity"] = round(d_score, 2)

    # 4. Trust (15 pts)
    raw_trust = (buyer_user or {}).get("trust_score")
    trust = float(raw_trust if raw_trust is not None else 3.5)
    t_score = min(trust / 5.0, 1.0) * 15.0
    breakdown["trust_reliability"] = round(t_score, 2)

    # 5. Quality/Grade (10 pts)
    g_score = 0.0
    list_grade = str(listing.get("grade") or listing.get("quality") or "A").upper()
    req_grade = str(requirement.get("grade") or requirement.get("quality_grade") or "A").upper()
    if list_grade == req_grade:
        g_score = 10.0
    elif list_grade in ["A", "PREMIUM"] and req_grade in ["B", "C", "STANDARD"]:
        g_score = 8.0
    else:
        g_score = 4.0
    breakdown["quality_grade"] = round(g_score, 2)

    # 6. Urgency / Spoilage (10 pts)
    raw_spoil = listing.get("spoilage_days")
    if raw_spoil is None:
        raw_spoil = listing.get("shelf_life")
    try:
        spoilage = int(raw_spoil if raw_spoil is not None else 14)
    except (ValueError, TypeError):
        spoilage = 14

    u_score = 6.0
    urgency = str(requirement.get("urgency") or "NORMAL").upper()
    if spoilage <= 3 and urgency == "HIGH":
        u_score = 10.0
    elif spoilage > 7 and urgency == "LOW":
        u_score = 10.0
    breakdown["spoilage_urgency"] = round(u_score, 2)

    # 7. Transport Cost Efficiency (5 pts)
    est_transport_cost = (dist * 3.0 * req_qty) / 1000.0
    raw_budget = requirement.get("budget")
    budget = float(raw_budget if raw_budget is not None else (target_price * req_qty))
    tr_score = 5.0
    if budget > 0:
        transport_ratio = min(est_transport_cost / budget, 1.0)
        tr_score = (1.0 - transport_ratio) * 5.0
    breakdown["transport_efficiency"] = round(tr_score, 2)

    # 8. Storage Cost Efficiency (5 pts)
    st_score = 5.0 if req_qty >= avail_qty else 2.0
    breakdown["storage_efficiency"] = round(st_score, 2)

    total = round(p_score + q_score + d_score + t_score + g_score + u_score + tr_score + st_score, 2)
    return {
        "total_score": total,
        "factor_breakdown": breakdown,
        "distance_km": dist
    }


def compute_match_score_sync(listing: Dict, requirement: Dict, buyer_user: Optional[Dict] = None) -> float:
    """
    Compute a 0-100 compatibility score using the canonical 8-factor NRV model.
    Single source of truth for candidate scoring across matching_service and LangGraph.
    """
    res = compute_match_breakdown_sync(listing, requirement, buyer_user)
    return res["total_score"]


async def _score_match(listing: Dict, requirement: Dict, buyer_user: Optional[Dict] = None) -> float:
    """
    Compute a 0-100 compatibility score using the 8-factor NRV model.
    Maintains async API compatibility.
    """
    return compute_match_score_sync(listing, requirement, buyer_user)


async def match_listing_to_buyers(listing: Dict) -> List[Dict]:
    """
    Find and score all buyer requirements that match a given crop listing.
    Returns ranked list of matches using the canonical 8-factor NRV model.
    Prioritizes real active buyer requirements posted in the system, then augments
    with verified APMC institutional buyers.
    """
    buyers = await Database.list_buyers_async()
    list_crop = (listing.get("crop") or "").strip()

    # 1. Real active buyer requirements matching this crop
    real_reqs = [
        r for r in buyers 
        if (r.get("kind") == "requirement" or str(r.get("id", "")).startswith("req_"))
        and (r.get("status") in ("ACTIVE", None, ""))
        and crops_match(str(r.get("crop", "")), list_crop)
    ]
    
    # 2. Institutional / verified buyer profiles as supplementary candidates
    institutional_profiles = [
        b for b in buyers 
        if b not in real_reqs and b.get("kind") != "offer"
        and (not b.get("crop") or b.get("crop") in ("ALL", "*", "any") or crops_match(str(b.get("crop", "")), list_crop))
    ]

    all_candidates = []
    for r in real_reqs:
        all_candidates.append((r, 1))  # source_priority = 1 (Real Buyer Requirement)

    for p in institutional_profiles:
        all_candidates.append((p, 2))  # source_priority = 2 (Institutional Pool)

    results = []
    seen_ids = set()

    for cand, priority in all_candidates:
        cand_id = cand.get("requirement_id") or cand.get("id") or cand.get("buyer_id")
        if cand_id and cand_id in seen_ids:
            continue
        if cand_id:
            seen_ids.add(cand_id)

        buyer_user = await UserRepository.get_by_id(cand.get("user_id", "")) or {}
        score = await _score_match(listing, cand, buyer_user)
        dist = await _get_distance_km(listing.get("location", ""), cand.get("location", ""))
        
        req_qty = float(cand.get("quantity") or cand.get("max_quantity") or listing.get("quantity", 0))
        offered_qty = min(float(listing.get("quantity", 0)), req_qty)
        min_price = float(listing.get("min_price", 0))
        market_price = float(listing.get("market_price", min_price + 1))
        target_price = float(cand.get("target_price") or cand.get("max_price") or (min_price * 1.05))

        raw_budget = float(cand.get("budget", 0))
        budget = raw_budget if raw_budget > 0 else max(target_price * req_qty * 1.2, min_price * offered_qty * 1.1)
        budget_limited_price = budget / max(offered_qty, 1)
        
        strategy = str(cand.get("strategy", "")).lower()
        
        if "restaurant" in strategy or "premium" in strategy:
            opening_bid = min(target_price * 0.95, budget_limited_price)
        else:
            base_offer = max(target_price * 0.92, min_price if target_price >= min_price else target_price * 0.88)
            opening_bid = min(target_price, budget_limited_price, max(base_offer, 1.0))
            
        offer_price = round(max(1.0, opening_bid), 2)
        is_viable = offer_price >= min_price

        # Strategic Labelling
        label = "Market Option"
        if priority == 1:
            label = "Verified Live Buyer Demand"
        if is_viable:
            if score > 75: label = "👑 Best Profit"
            elif dist == 0: label = "⚡ Fast Handshake"
            elif "restaurant" in strategy: label = "💎 Premium Match"
            elif score > 50: label = "🎯 Strategic Fit"

        b_name = cand.get("buyer_name") or cand.get("name") or "Institutional Buyer"

        results.append({
            "requirement_id": cand.get("requirement_id") or cand.get("id"),
            "buyer_id": cand.get("user_id") or cand.get("id"),
            "buyer_name": b_name,
            "crop": cand.get("crop") or list_crop,
            "quantity": req_qty,
            "target_price": target_price,
            "max_price": cand.get("max_price"),
            "budget": budget,
            "location": cand.get("location", "Market"),
            "strategy": label,
            "offered_price": offer_price,
            "offered_quantity": round(offered_qty, 2),
            "status": "VIABLE" if is_viable else "BELOW_MIN_PRICE",
            "distance_km": dist,
            "compatibility_score": score,
            "score": score,
            "match_grade": "A" if score >= 70 else "B" if score >= 45 else "C",
            "source_priority": priority,
            "notes": cand.get("notes", ""),
        })

    # Strict ranking: Real demands first (priority=1), then viability, then score, then offer price
    results.sort(
        key=lambda item: (
            -item["source_priority"],
            item["status"] == "VIABLE",
            item["compatibility_score"],
            item["offered_price"]
        ),
        reverse=True
    )
    return results


async def match_requirement_to_listings(requirement: Dict) -> List[Dict]:
    """
    Find and score all active crop listings that match a buyer requirement.
    """
    from backend.routes.crop_listing_routes import router as _  # ensure module loaded
    listings = await Database.list_produce_async()
    active = [
        l for l in listings
        if l.get("status") in ("LISTED", "ACTIVE", "NEGOTIATING", None, "")
        and l.get("status") not in ("SOLD", "EXPIRED", "WITHDRAWN", "CANCELLED")
        and float(l.get("quantity") or 0) > 0
    ]

    results = []
    for listing in active:
        if not crops_match(requirement.get("crop", ""), listing.get("crop", "")):
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

