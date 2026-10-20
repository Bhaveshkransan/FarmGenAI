"""
tests/intelligence/harness/candidate_universe.py
------------------------------------------------
Level 1: Candidate Universe Generator & Explainability Engine.
Generates candidate pools of 10 to 1,000 counterparties, filters hard eligibility,
computes 8-factor NRV matching breakdown, and provides traceable ranking evidence.
"""

import random
from typing import List, Dict, Any, Tuple
from tests.intelligence.harness.schema import (
    CandidateUniverseSpec,
    ListingContext,
    ComparisonEvidence,
    ExplainabilityFact,
)
from backend.services.matching_service import (
    compute_match_breakdown_sync,
    crops_match,
    get_distance_km_sync,
)
from shared.crop_catalog import normalize_crop_name


MAHARASHTRA_DISTRICTS = [
    "Nashik", "Pune", "Mumbai", "Nagpur", "Latur", "Solapur",
    "Ahmednagar", "Aurangabad", "Amravati", "Kolhapur", "Jalgaon"
]

ALL_CROPS = [
    "Sugarcane", "Soybean", "Cotton", "Jowar", "Onion", "Bajra", "Rice"
]


def generate_candidate_universe(
    listing: ListingContext,
    spec: CandidateUniverseSpec
) -> List[Dict[str, Any]]:
    """
    Generates a deterministic synthetic candidate pool of counterparties
    with varying crops, capacities, budgets, locations, and trust scores.
    """
    rng = random.Random(spec.seed)
    candidates = []

    for i in range(spec.total_candidates):
        cid = f"buyer_{spec.total_candidates}_{i+1:03d}"
        
        # Crop assignment
        if rng.random() < spec.target_crop_ratio:
            c_crop = listing.crop
        else:
            other_crops = [c for c in ALL_CROPS if c.lower() != listing.crop.lower()]
            c_crop = rng.choice(other_crops) if other_crops else "Wheat"

        # Location & Distance
        if rng.random() < spec.local_distance_ratio:
            c_location = listing.location
        else:
            c_location = rng.choice([d for d in MAHARASHTRA_DISTRICTS if d != listing.location])

        # Capacity & Pricing
        qty_factor = rng.uniform(0.1, 2.5)
        c_max_qty = round(listing.quantity * qty_factor, 1)

        price_factor = rng.uniform(spec.min_budget_factor, spec.max_budget_factor)
        c_target_price = round(listing.min_price * price_factor, 2)
        c_max_price = round(c_target_price * rng.uniform(1.05, 1.25), 2)
        c_budget = round(c_max_price * c_max_qty * rng.uniform(1.0, 1.3), 2)

        # Quality & Trust
        c_grade = "A" if rng.random() < 0.7 else "B"
        c_verified = rng.random() < spec.verified_ratio
        c_trust = round(rng.uniform(3.5, 4.9) if c_verified else rng.uniform(2.5, 4.2), 1)

        strategy = rng.choice(["balanced", "quality_first", "bargain", "aggressive"])

        candidates.append({
            "id": cid,
            "name": f"Procurement Entity #{i+1:03d} ({c_location})",
            "crop": c_crop,
            "location": c_location,
            "target_price": c_target_price,
            "max_price": c_max_price,
            "budget": c_budget,
            "max_quantity": c_max_qty,
            "grade": c_grade,
            "verified": c_verified,
            "trust_score": c_trust,
            "strategy": strategy,
        })

    return candidates


def evaluate_candidate_universe(
    listing: ListingContext,
    candidates: List[Dict[str, Any]]
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]], List[Dict[str, Any]]]:
    """
    Filters raw candidates by hard business rules, then scores eligible candidates
    using the authentic 8-factor NRV matching engine.
    
    Returns:
        (eligible_candidates, rejected_candidates, ranked_candidates)
    """
    eligible = []
    rejected = []

    for c in candidates:
        # 1. Crop Match
        if not crops_match(c["crop"], listing.crop):
            rejected.append({
                "candidate": c,
                "reason": f"CROP_INCOMPATIBLE: Expected {listing.crop}, buyer trades {c['crop']}"
            })
            continue

        # 2. Minimum Viable Capacity (Buyer must accept at least 15% of farmer listing)
        if c["max_quantity"] < listing.quantity * 0.15:
            rejected.append({
                "candidate": c,
                "reason": f"CAPACITY_TOO_LOW: Max {c['max_quantity']}kg < {listing.quantity * 0.15}kg threshold"
            })
            continue

        # 3. Budget Feasibility
        effective_unit_budget = c["budget"] / min(listing.quantity, c["max_quantity"])
        if effective_unit_budget < listing.min_price * 0.85:
            rejected.append({
                "candidate": c,
                "reason": f"BUDGET_INSUFFICIENT: Max unit budget ₹{effective_unit_budget:.2f} < floor ₹{listing.min_price}"
            })
            continue

        # 4. Regional Distance Boundary (<600km)
        dist = get_distance_km_sync(listing.location, c["location"])
        if dist > 600.0:
            rejected.append({
                "candidate": c,
                "reason": f"DISTANCE_EXCEEDED: {dist}km exceeds 600km logistics limit"
            })
            continue

        eligible.append(c)

    # Score each eligible candidate
    ranked = []
    for c in eligible:
        offered_qty = min(listing.quantity, c["max_quantity"])
        breakdown = compute_match_breakdown_sync(
            listing={
                "min_price": listing.min_price,
                "quantity": listing.quantity,
                "location": listing.location,
                "crop": listing.crop,
                "grade": listing.grade,
                "spoilage_days": listing.spoilage_days,
            },
            requirement={
                "target_price": c["target_price"],
                "max_price": c["max_price"],
                "quantity": offered_qty,
                "location": c["location"],
                "grade": c["grade"],
                "urgency": "HIGH" if listing.spoilage_days <= 3 else "NORMAL",
                "budget": c["budget"],
            },
            buyer_user={
                "trust_score": c["trust_score"],
                "verified": c["verified"]
            }
        )
        dist = get_distance_km_sync(listing.location, c["location"])

        c_enriched = dict(c)
        c_enriched["score"] = breakdown["total_score"]
        c_enriched["factor_breakdown"] = breakdown["factor_breakdown"]
        c_enriched["distance_km"] = dist
        ranked.append(c_enriched)

    # Sort descending by match score
    ranked.sort(key=lambda x: x["score"], reverse=True)
    return eligible, rejected, ranked


def build_ranking_evidence(
    ranked_candidates: List[Dict[str, Any]],
    top_n: int = 5
) -> List[ComparisonEvidence]:
    """
    Generates traceable comparison evidence explaining why candidate #N was selected
    over candidate #N+1 (or specific pairs like Buyer #37 vs Buyer #91).
    """
    evidence_list = []
    
    for i in range(min(top_n, len(ranked_candidates) - 1)):
        cand_a = ranked_candidates[i]
        cand_b = ranked_candidates[i + 1]

        fb_a = cand_a.get("factor_breakdown", {})
        fb_b = cand_b.get("factor_breakdown", {})

        advantages = []
        tradeoffs = []

        factors = [
            ("price_feasibility", "Price / Budget Compatibility", 20.0),
            ("quantity_fulfillment", "Quantity Capacity", 20.0),
            ("distance_proximity", "Proximity & Distance", 15.0),
            ("trust_reliability", "Trust & Verified Status", 15.0),
            ("quality_grade", "Quality Grade Compatibility", 10.0),
            ("spoilage_urgency", "Urgency / Shelf-life Handling", 10.0),
            ("transport_efficiency", "Logistics Efficiency", 5.0),
            ("storage_efficiency", "Storage Cost Efficiency", 5.0),
        ]

        for key, label, max_val in factors:
            val_a = fb_a.get(key, 0.0)
            val_b = fb_b.get(key, 0.0)
            diff = round(val_a - val_b, 2)
            if diff > 0.5:
                advantages.append(f"{label} (+{diff} pts, {val_a}/{max_val} vs {val_b}/{max_val})")
            elif diff < -0.5:
                tradeoffs.append(f"{label} ({diff} pts, {val_a}/{max_val} vs {val_b}/{max_val})")

        verdict = (
            f"Rank #{i+1} ({cand_a['name']}, score {cand_a['score']}) outranked "
            f"Rank #{i+2} ({cand_b['name']}, score {cand_b['score']}) "
            f"primarily due to: {', '.join(advantages[:2]) if advantages else 'balanced composite factors'}"
        )

        evidence_list.append(ComparisonEvidence(
            higher_ranked_id=cand_a["id"],
            lower_ranked_id=cand_b["id"],
            rank_a=i+1,
            rank_b=i+2,
            score_a=cand_a["score"],
            score_b=cand_b["score"],
            primary_advantages=advantages,
            tradeoffs=tradeoffs,
            verdict=verdict
        ))

    return evidence_list
