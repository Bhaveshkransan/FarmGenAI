"""
tests/intelligence/harness/negotiation_simulator.py
---------------------------------------------------
Level 2 & Level 10: Negotiation Intelligence & Net Realization Decision Engine.
Implements the multi-stage funnel:
  Candidate pool (200) -> Shortlist (20) -> Contacted (10) -> Responded (7)
  -> Negotiate (5) -> Acceptable (3) -> Quantity/Shelf-life filter -> 1 Best Deal.

Calculates Net Realization:
  Net Farmer Margin = (Price * Quantity) - Transport Freight - Storage Cost
  Net Price/kg = Net Farmer Margin / Quantity
"""

from typing import List, Dict, Any, Optional, Tuple
from tests.intelligence.harness.schema import ListingContext, MarketTrend
from backend.agents.graph_orchestrator import estimate_distance_km


def simulate_multi_round_negotiation(
    listing: ListingContext,
    ranked_candidates: List[Dict[str, Any]],
    market_trend: MarketTrend,
    shortlist_limit: int = 20,
    contact_limit: int = 10,
    max_rounds: int = 3,
) -> Dict[str, Any]:
    """
    Executes a structured, multi-stage negotiation funnel across the candidate pool.
    Considers the whole situation: shelf life, quantity fulfillment, freight deductions,
    and market trend dynamics.
    """
    # Stage 1: Shortlisting (e.g. Top 20)
    shortlisted = ranked_candidates[:shortlist_limit]

    # Stage 2: Contacted Subset (e.g. Top 10)
    contacted = shortlisted[:contact_limit]

    # Stage 3: Response Rate (simulate realistic network / availability drop-off, e.g. 70-80%)
    # Buyers with higher trust score and closer proximity respond reliably
    responding_buyers = []
    for c in contacted:
        prob = 0.5 + (c["trust_score"] / 5.0) * 0.35
        if c["distance_km"] < 150:
            prob += 0.15
        if prob >= 0.70 or len(responding_buyers) < 5:
            responding_buyers.append(c)

    # Stage 4: Negotiation Subset (Active buyers that enter bargaining, e.g. top 5)
    negotiating_buyers = responding_buyers[:5]

    # Stage 5: Multi-Round Bargaining Loop
    # Farmer opening ask depends on market trend
    farmer_markup = 1.25 if market_trend == MarketTrend.RISING else (1.15 if market_trend == MarketTrend.STABLE else 1.05)
    farmer_ask = round(listing.min_price * farmer_markup, 2)

    active_dialogues = []
    for b in negotiating_buyers:
        b_target = b["target_price"]
        b_max = b["max_price"]
        b_strat = b.get("strategy", "balanced")

        # Round 1 opening bid
        if b_strat == "aggressive" or b_strat == "bargain":
            r1_bid = round(min(b_target * 0.92, b_max * 0.85), 2)
        else:
            r1_bid = round(min(b_target, b_max * 0.95), 2)

        # Multi-round concessions
        current_bid = r1_bid
        farmer_concession = farmer_ask
        rounds_taken = 1

        for r in range(2, max_rounds + 1):
            if current_bid >= listing.min_price and current_bid >= farmer_concession * 0.96:
                # Acceptable agreement reached
                break
            
            # Farmer concedes towards expected price, but NEVER below min_price
            step_down = (farmer_ask - listing.min_price) / max_rounds
            farmer_concession = round(max(listing.min_price, farmer_concession - step_down), 2)

            # Buyer concedes towards max_price if farmer is reasonable
            step_up = (b_max - current_bid) * 0.4
            current_bid = round(min(b_max, current_bid + step_up), 2)
            rounds_taken = r

        active_dialogues.append({
            "buyer": b,
            "final_offer_price": current_bid,
            "rounds": rounds_taken,
            "farmer_final_ask": farmer_concession,
            "accepted_by_buyer": current_bid >= b_target or current_bid <= b_max,
        })

    # Stage 6: Hard Floor Filter (Reject offers strictly below listing min_price)
    acceptable_offers = []
    for d in active_dialogues:
        if d["final_offer_price"] >= listing.min_price:
            acceptable_offers.append(d)

    # Stage 7: Holistic Evaluation (Quantity, Shelf-Life & Net Margin Realization)
    evaluated_deals = []
    for d in acceptable_offers:
        buyer = d["buyer"]
        nominal_price = d["final_offer_price"]
        buyer_max_qty = buyer["max_quantity"]

        # Quantity fulfillment check
        fulfilled_qty = min(listing.quantity, buyer_max_qty)
        qty_ratio = fulfilled_qty / listing.quantity

        # Distance & Freight calculation
        dist_km = buyer.get("distance_km") or estimate_distance_km(listing.location, buyer["location"])
        
        # Freight rate: if farmer has transport, freight is 0; otherwise distance * rate
        if listing.has_transport:
            freight_cost = 0.0
            transit_days = 1
        else:
            freight_cost = round((dist_km * listing.transport_rate_per_km * fulfilled_qty) / 1000.0, 2)
            # Estimate transit days: 1 day per 250km, minimum 1
            transit_days = max(1, int(dist_km / 250) + 1)

        # Shelf life check: if transit time exceeds available shelf-life, severe risk
        shelf_life_viable = transit_days <= listing.spoilage_days
        shelf_life_penalty = 0.0
        if not shelf_life_viable:
            # Transit exceeds shelf life: high spoilage risk
            shelf_life_penalty = fulfilled_qty * nominal_price * 0.40

        # Storage cost calculation
        storage_cost = (listing.holding_days * 0.5 * fulfilled_qty) if (listing.requires_storage and not listing.has_storage) else 0.0

        # Economic Net Margin Calculation (The Net Realization Principle)
        gross_revenue = round(nominal_price * fulfilled_qty, 2)
        net_take_home = round(gross_revenue - freight_cost - storage_cost - shelf_life_penalty, 2)
        net_price_per_kg = round(net_take_home / fulfilled_qty, 2) if fulfilled_qty > 0 else 0.0

        evaluated_deals.append({
            "buyer_id": buyer["id"],
            "buyer_name": buyer["name"],
            "location": buyer["location"],
            "distance_km": dist_km,
            "nominal_price": nominal_price,
            "fulfilled_quantity": fulfilled_qty,
            "quantity_ratio": round(qty_ratio, 2),
            "gross_revenue": gross_revenue,
            "freight_cost": freight_cost,
            "storage_cost": storage_cost,
            "shelf_life_viable": shelf_life_viable,
            "transit_days": transit_days,
            "net_margin": net_take_home,
            "net_price_per_kg": net_price_per_kg,
            "rounds_negotiated": d["rounds"],
        })

    # Stage 8: Best Deal Selection based on NET Realization (NOT raw gross price!)
    # Must also satisfy shelf life viability
    viable_deals = [d for d in evaluated_deals if d["shelf_life_viable"] and d["quantity_ratio"] >= 0.20]
    
    selected_deal = None
    if viable_deals:
        # Sort by Net Farmer Margin (highest take-home pay)
        viable_deals.sort(key=lambda x: (x["net_margin"], x["net_price_per_kg"]), reverse=True)
        selected_deal = viable_deals[0]

    return {
        "shortlisted": shortlisted,
        "contacted": contacted,
        "responding": responding_buyers,
        "negotiating": negotiating_buyers,
        "acceptable_offers": acceptable_offers,
        "evaluated_deals": evaluated_deals,
        "viable_deals": viable_deals,
        "selected_deal": selected_deal,
    }
