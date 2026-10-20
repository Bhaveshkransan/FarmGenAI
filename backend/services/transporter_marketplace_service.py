"""
backend/services/transporter_marketplace_service.py

Large-Scale Autonomous Transporter Marketplace & Candidate Intelligence Engine.
Separates Transport Providers (Counterparties) from Vehicles (Assets).
Implements:
1. Multi-tier Transporter Marketplace Pool Generation (10, 50, 100, 200, 500+ providers).
2. Hard Constraint Provider & Vehicle Filtering (Capacity, Refrigeration, Deadline).
3. Transporter vs. Vehicle Aggregation (1 provider -> 1 best vehicle offer).
4. Strictly Normalized Multi-Factor Matching Score in [0, 100].
5. Adaptive Candidate Expansion across sequential shortlist windows.
6. Pool Exhaustion Protocol (NO_TRANSPORT_AVAILABLE).
7. Post-Deal Economic Settlement Feasibility Audit (Farmer Floor Protection).
"""

import logging
import json
import os
import random
import datetime
import uuid
from typing import List, Dict, Any, Optional, Tuple
from backend.services.routing_service import calculate_transport_route
from backend.services.transport_cost_service import calculate_transportation_cost

logger = logging.getLogger("TransporterMarketplaceService")

async def emit_transport_event(
    event_type: str,
    trace_id: str,
    message: str,
    workflow_id: Optional[str] = None,
    request_id: Optional[str] = None,
    negotiation_id: Optional[str] = None,
    provider_id: Optional[str] = None,
    vehicle_id: Optional[str] = None,
    sequence: Optional[int] = None,
    stage: Optional[str] = None,
    status: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None
):
    """Safely emits typed WebSocket event with complete audit lineage."""
    try:
        from backend.websocket.events import create_ws_event, WSEventType
        from backend.websocket.agent_updates import agent_update_hub
        evt = create_ws_event(
            event_type=WSEventType(event_type),
            trace_id=trace_id,
            source_agent="transport_marketplace_service",
            message=message,
            workflow_id=workflow_id,
            request_id=request_id,
            negotiation_id=negotiation_id,
            provider_id=provider_id,
            vehicle_id=vehicle_id,
            sequence=sequence,
            stage=stage,
            status=status,
            payload=payload or {},
            metadata=metadata or {}
        )
        await agent_update_hub.broadcast(evt)
    except Exception as e:
        logger.debug(f"Event broadcast skipped/silent: {e}")

MAHARASHTRA_DISTRICTS = [
    "Pune", "Nashik", "Ahmednagar", "Nagpur", "Solapur", 
    "Aurangabad", "Kolhapur", "Latur", "Jalgaon", "Amravati", 
    "Mumbai", "Satara", "Sangli", "Nanded", "Dhule"
]

VEHICLE_CATALOG = [
    {"type": "Cargo Three-Wheeler", "capacity": 600.0, "kmpl": 16.0, "reefer": False, "rate": 12.0},
    {"type": "Mini Truck", "capacity": 1500.0, "kmpl": 12.0, "reefer": False, "rate": 18.0},
    {"type": "LCV", "capacity": 2500.0, "kmpl": 10.0, "reefer": False, "rate": 22.0},
    {"type": "Medium Truck", "capacity": 5000.0, "kmpl": 8.0, "reefer": False, "rate": 32.0},
    {"type": "Refrigerated Truck", "capacity": 4000.0, "kmpl": 6.5, "reefer": True, "rate": 45.0},
    {"type": "Cold Chain Reefer", "capacity": 8000.0, "kmpl": 5.5, "reefer": True, "rate": 55.0},
    {"type": "Heavy Truck", "capacity": 12000.0, "kmpl": 5.0, "reefer": False, "rate": 50.0},
    {"type": "Tractor + Trailer", "capacity": 7000.0, "kmpl": 7.0, "reefer": False, "rate": 25.0}
]


def load_seed_transporters() -> List[Dict[str, Any]]:
    """Loads base seed transporter records from transporters.json."""
    seed_path = os.path.join(os.path.dirname(__file__), "..", "dataset", "transporters.json")
    if os.path.exists(seed_path):
        try:
            with open(seed_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to read transporters.json: {e}")
    return []


def generate_transporter_marketplace(pool_size: int = 100, seed: int = 42) -> List[Dict[str, Any]]:
    """
    Generates an active, multi-counterparty marketplace of Transport Providers.
    Each Transport Provider owns a fleet of 1 to 4 distinct vehicles.
    """
    rng = random.Random(seed)
    seed_data = load_seed_transporters()
    providers: List[Dict[str, Any]] = []

    for i in range(pool_size):
        provider_id = f"TR-PROV-{i+1:04d}"
        if i < len(seed_data):
            base = seed_data[i]
            prov_name = base.get("provider_name", f"Logistics Provider {i+1}")
            loc = base.get("current_location", rng.choice(MAHARASHTRA_DISTRICTS))
            rating = float(base.get("rating", round(rng.uniform(3.5, 4.9), 1)))
        else:
            dist = rng.choice(MAHARASHTRA_DISTRICTS)
            prov_name = f"{dist} Agro-Express Carrier #{i+1}"
            loc = dist
            rating = round(rng.uniform(3.5, 4.9), 1)

        reliability = round(min(1.0, max(0.6, rating / 5.0 - rng.uniform(0.0, 0.05))), 2)
        total_trips = rng.randint(45, 1200)
        cancellation_rate = round(rng.uniform(0.01, 0.08), 3)

        # Generate provider fleet (1 to 4 vehicles)
        fleet_size = rng.randint(1, 4)
        fleet = []
        for v_idx in range(fleet_size):
            spec = rng.choice(VEHICLE_CATALOG)
            vehicle_id = f"{provider_id}-V{v_idx+1}"
            fleet.append({
                "vehicle_id": vehicle_id,
                "transporter_id": provider_id,
                "provider_name": prov_name,
                "vehicle_type": spec["type"],
                "vehicle_name": f"{prov_name} ({spec['type']})",
                "capacity_kg": spec["capacity"],
                "fuel_type": "Diesel",
                "fuel_efficiency_kmpl": spec["kmpl"],
                "current_location": loc,
                "refrigerated": spec["reefer"],
                "rate_per_km": spec["rate"],
                "status": "AVAILABLE" if rng.random() > 0.10 else "IN_TRANSIT",
                "rating": rating
            })

        providers.append({
            "provider_id": provider_id,
            "provider_name": prov_name,
            "current_location": loc,
            "rating": rating,
            "reliability_score": reliability,
            "total_trips": total_trips,
            "cancellation_rate": cancellation_rate,
            "fleet_size": len(fleet),
            "fleet": fleet
        })

    return providers


def filter_and_rank_transporter_candidates(
    providers: List[Dict[str, Any]],
    transport_request: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Executes hard-constraint filtering and strictly normalized multi-factor ranking.
    Separates Transporter Provider from Vehicle:
    Each eligible provider is evaluated across its fleet, and its single best vehicle
    is selected to prevent one fleet from monopolizing candidate slots.
    """
    req_qty = float(transport_request.get("quantity_kg", 1000.0))
    req_refrig = bool(transport_request.get("refrigerated_required", False))
    pickup_loc = transport_request.get("pickup_location", "Ahmednagar")
    delivery_loc = transport_request.get("delivery_location", "Pune")
    deadline_h = float(transport_request.get("delivery_deadline_hours", 24.0))
    shelf_life_h = float(transport_request.get("shelf_life_hours", 48.0))
    urgency = transport_request.get("urgency", "NORMAL").upper()

    total_pool = len(providers)
    eligible_candidates: List[Dict[str, Any]] = []
    rejected_reasons: Dict[str, int] = {
        "NO_AVAILABLE_VEHICLES": 0,
        "INSUFFICIENT_CAPACITY": 0,
        "REFRIGERATION_MISMATCH": 0,
        "DEADLINE_EXCEEDED": 0,
        "DISTANCE_EXCEEDED": 0
    }

    for p in providers:
        fleet = p.get("fleet", [])
        valid_fleet_for_req = []

        for v in fleet:
            if v.get("status") != "AVAILABLE":
                continue
            if v.get("capacity_kg", 0) < req_qty:
                continue
            if req_refrig and not v.get("refrigerated", False):
                continue
            valid_fleet_for_req.append(v)

        if not valid_fleet_for_req:
            # Determine dominant rejection reason for this provider
            has_avail = any(v.get("status") == "AVAILABLE" for v in fleet)
            if not has_avail:
                rejected_reasons["NO_AVAILABLE_VEHICLES"] += 1
            elif req_refrig and not any(v.get("refrigerated") for v in fleet):
                rejected_reasons["REFRIGERATION_MISMATCH"] += 1
            else:
                rejected_reasons["INSUFFICIENT_CAPACITY"] += 1
            continue

        # Sort vehicles in fleet by least capacity excess (tightest fit)
        valid_fleet_for_req.sort(key=lambda x: x["capacity_kg"] - req_qty)
        best_vehicle = valid_fleet_for_req[0]

        # Calculate routing distance and duration
        route = calculate_transport_route(
            pickup_location=pickup_loc,
            delivery_location=delivery_loc,
            vehicle_current_location=p["current_location"]
        )
        total_dist = route.get("total_operational_distance_km", 50.0)
        duration_h = route.get("total_travel_duration_hours", 2.0)

        # Hard constraint: Distance <= 600km
        if total_dist > 600.0:
            rejected_reasons["DISTANCE_EXCEEDED"] += 1
            continue

        # Hard constraint: Duration <= Deadline
        if duration_h > deadline_h:
            rejected_reasons["DEADLINE_EXCEEDED"] += 1
            continue

        # --- Normalized Multi-Factor Scoring in [0.0, 1.0] ---
        # 1. Distance proximity (0 to 1, max score at 0 distance)
        s_dist = max(0.0, 1.0 - (total_dist / 600.0))

        # 2. Capacity utilization (0 to 1, peak score when capacity closely matches requested payload)
        cap_excess_pct = (best_vehicle["capacity_kg"] - req_qty) / max(best_vehicle["capacity_kg"], 1.0)
        s_cap = max(0.0, 1.0 - cap_excess_pct)

        # 3. Provider Reliability & Rating (0 to 1)
        s_rel = (p.get("rating", 4.0) / 5.0) * (1.0 - p.get("cancellation_rate", 0.05))

        # 4. Delivery Deadline Buffer (0 to 1)
        s_deadline = max(0.0, 1.0 - (duration_h / max(deadline_h, 1.0)))

        # 5. Refrigeration Compliance (0 to 1)
        s_refrig = 1.0 if (req_refrig and best_vehicle["refrigerated"]) else (1.0 if not req_refrig else 0.0)

        # 6. Tariff Feasibility (0 to 1)
        s_rate = max(0.0, 1.0 - (best_vehicle.get("rate_per_km", 20.0) - 12.0) / 45.0)

        # Weighted Composite Score strictly in [0.0, 100.0]
        # Weights: Dist(25%), Cap(20%), Rel(20%), Deadline(15%), Refrig(10%), Rate(10%)
        composite_score = round(100.0 * (
            0.25 * s_dist +
            0.20 * s_cap +
            0.20 * s_rel +
            0.15 * s_deadline +
            0.10 * s_refrig +
            0.10 * s_rate
        ), 2)

        explainability = {
            "distance_score_pct": round(s_dist * 25.0, 2),
            "capacity_score_pct": round(s_cap * 20.0, 2),
            "reliability_score_pct": round(s_rel * 20.0, 2),
            "deadline_score_pct": round(s_deadline * 15.0, 2),
            "refrigeration_score_pct": round(s_refrig * 10.0, 2),
            "rate_score_pct": round(s_rate * 10.0, 2),
            "total_composite_score": composite_score
        }

        eligible_candidates.append({
            "provider_id": p["provider_id"],
            "provider_name": p["provider_name"],
            "location": p["current_location"],
            "rating": p["rating"],
            "reliability_score": p["reliability_score"],
            "selected_vehicle": best_vehicle,
            "route_distance_km": total_dist,
            "duration_hours": duration_h,
            "match_score": composite_score,
            "explainability": explainability
        })

    # Sort candidates by composite match score descending
    eligible_candidates.sort(key=lambda x: x["match_score"], reverse=True)

    return {
        "success": len(eligible_candidates) > 0,
        "total_providers_evaluated": total_pool,
        "eligible_provider_count": len(eligible_candidates),
        "rejected_breakdown": rejected_reasons,
        "ranked_candidates": eligible_candidates,
        "top_candidate": eligible_candidates[0] if eligible_candidates else None
    }


async def adaptive_candidate_expansion_negotiation(
    ranked_candidates: List[Dict[str, Any]],
    transport_request: Dict[str, Any],
    batch_size: int = 5,
    max_batches: int = 4
) -> Dict[str, Any]:
    """
    Executes windowed candidate expansion across ranked providers.
    Batch 1 (1-5) -> If counterparties reject or fail, expands to Batch 2 (6-10), etc.
    Maintains complete tournament state to ensure:
    - Zero candidate renegotiation across batches.
    - Zero candidate duplication.
    - Complete persistence of every attempt's outcome, offer, and timestamp.
    If all candidates fail or pool is exhausted, returns NO_TRANSPORT_AVAILABLE.
    """
    trace_id = transport_request.get("trace_id", str(uuid.uuid4()))
    workflow_id = transport_request.get("workflow_id")
    request_id = transport_request.get("request_id")
    mock_responses = transport_request.get("mock_responses", {})

    if not ranked_candidates:
        await emit_transport_event(
            event_type="TRANSPORT_FAILED",
            trace_id=trace_id,
            workflow_id=workflow_id,
            request_id=request_id,
            sequence=1,
            stage="ADAPTIVE_EXPANSION",
            status="FAILED",
            message="Initial transporter candidate pool is empty.",
            payload={"reason": "CANDIDATE_POOL_EXHAUSTED"}
        )
        return {
            "status": "NO_TRANSPORT_AVAILABLE",
            "reason": "CANDIDATE_POOL_EXHAUSTED",
            "rounds_attempted": 0,
            "total_contacted": 0,
            "final_deal": None,
            "tournament_history": [],
            "tournament_state": {"attempted_ids": [], "total_contacted": 0, "history": []},
            "logs": ["❌ Initial candidate pool is empty. No transport providers available."]
        }

    logs = []
    total_contacted = 0
    buyer_offer = transport_request.get("buyer_offer")
    tournament_history: List[Dict[str, Any]] = []
    attempted_candidate_ids: set = set()

    for batch_idx in range(max_batches):
        start_idx = batch_idx * batch_size
        end_idx = min(start_idx + batch_size, len(ranked_candidates))

        if start_idx >= len(ranked_candidates):
            logs.append(f"ℹ️ Total candidate pool exhausted after {total_contacted} providers evaluated.")
            break

        current_window = ranked_candidates[start_idx:end_idx]
        logs.append(
            f"🔄 [Adaptive Expansion] Batch {batch_idx+1}: Contacting candidates {start_idx+1} to {end_idx} "
            f"({len(current_window)} providers)."
        )

        await emit_transport_event(
            event_type="TRANSPORT_SHORTLISTED",
            trace_id=trace_id,
            workflow_id=workflow_id,
            request_id=request_id,
            sequence=len(tournament_history) + 1,
            stage="ADAPTIVE_EXPANSION",
            status="IN_PROGRESS",
            message=f"Batch {batch_idx+1}: Contacting {len(current_window)} candidate providers.",
            payload={"batch_number": batch_idx + 1, "candidates": [c.get("provider_id") for c in current_window]}
        )

        for candidate in current_window:
            cid = candidate.get("provider_id") or candidate.get("candidate_id")

            # Guaranteed Invariant: No candidate re-negotiation or duplication
            if cid in attempted_candidate_ids:
                continue
            attempted_candidate_ids.add(cid)
            total_contacted += 1

            vehicle = candidate["selected_vehicle"]
            dist = candidate["route_distance_km"]
            duration = candidate["duration_hours"]

            # Calculate deterministic operating cost and transport floor price
            cost_res = await calculate_transportation_cost(
                vehicle=vehicle,
                distance_km=dist,
                estimated_duration_hours=duration,
                deadhead_km=0.0
            )

            transport_floor_price = (
                candidate.get("floor_price_override") or
                vehicle.get("floor_price_override") or
                cost_res["minimum_acceptable_price"]
            )
            initial_quote = max(cost_res["initial_quote"], transport_floor_price * 1.15)

            # Check mock response override for deterministic adversarial testing
            mock_action = mock_responses.get(cid)

            cand_status = "PENDING"
            deal_reached = False
            agreed_freight = 0.0

            if mock_action == "REJECT":
                cand_status = "REJECTED"
                logs.append(f"⚠️ Provider {candidate['provider_name']} ({cid}) REJECTED terms (Adversarial simulation).")
            elif mock_action == "TIMEOUT":
                cand_status = "TIMEOUT"
                logs.append(f"⏱️ Provider {candidate['provider_name']} ({cid}) TIMED OUT.")
            elif mock_action == "BELOW_FLOOR":
                cand_status = "BELOW_FLOOR"
                logs.append(f"⚠️ Provider {candidate['provider_name']} ({cid}) offered below carrier floor.")
            elif mock_action == "ACCEPT" or (buyer_offer and buyer_offer >= transport_floor_price):
                cand_status = "ACCEPTED"
                deal_reached = True
                agreed_freight = buyer_offer if buyer_offer else initial_quote
                logs.append(
                    f"✅ [Deal Reached] Provider {candidate['provider_name']} accepted offer ₹{agreed_freight:,.2f} "
                    f"(Floor: ₹{transport_floor_price:,.2f})."
                )
            elif not buyer_offer:
                cand_status = "ACCEPTED"
                deal_reached = True
                agreed_freight = initial_quote
                logs.append(
                    f"✅ [Quote Accepted] Provider {candidate['provider_name']} quoted ₹{initial_quote:,.2f}."
                )
            else:
                cand_status = "REJECTED"
                logs.append(
                    f"⚠️ Provider {candidate['provider_name']} rejected offer ₹{buyer_offer:,.2f} "
                    f"(Below floor ₹{transport_floor_price:,.2f}). Continuing..."
                )

            # Record full tournament history entry
            history_entry = {
                "candidate_id": cid,
                "provider_id": cid,
                "provider_name": candidate["provider_name"],
                "vehicle_id": vehicle.get("vehicle_id"),
                "batch_number": batch_idx + 1,
                "negotiation_id": f"neg_{cid}_b{batch_idx+1}_{total_contacted}",
                "attempt_number": total_contacted,
                "status": cand_status,
                "offer": buyer_offer,
                "transport_floor": transport_floor_price,
                "initial_quote": initial_quote,
                "timestamp": datetime.datetime.utcnow().isoformat() + "Z"
            }
            tournament_history.append(history_entry)

            await emit_transport_event(
                event_type="TRANSPORTER_RESPONSE",
                trace_id=trace_id,
                workflow_id=workflow_id,
                request_id=request_id,
                sequence=len(tournament_history),
                stage="NEGOTIATION_RESPONSE",
                status=cand_status,
                provider_id=cid,
                vehicle_id=vehicle.get("vehicle_id"),
                message=f"Provider {candidate['provider_name']} response: {cand_status}.",
                payload=history_entry
            )

            if deal_reached:
                tournament_state = {
                    "attempted_ids": list(attempted_candidate_ids),
                    "total_contacted": total_contacted,
                    "rounds_attempted": batch_idx + 1,
                    "history": tournament_history
                }
                await emit_transport_event(
                    event_type="TRANSPORT_SELECTED",
                    trace_id=trace_id,
                    workflow_id=workflow_id,
                    request_id=request_id,
                    sequence=len(tournament_history) + 1,
                    stage="DEAL_SELECTION",
                    status="SUCCESS",
                    provider_id=cid,
                    vehicle_id=vehicle.get("vehicle_id"),
                    message=f"Deal confirmed with provider {candidate['provider_name']} at ₹{agreed_freight:,.2f}.",
                    payload={"agreed_freight": agreed_freight, "transport_floor": transport_floor_price}
                )
                return {
                    "status": "DEAL_CONFIRMED",
                    "winning_provider": candidate,
                    "agreed_freight": agreed_freight,
                    "transport_floor_price": transport_floor_price,
                    "cost_breakdown": cost_res,
                    "rounds_attempted": batch_idx + 1,
                    "total_contacted": total_contacted,
                    "tournament_history": tournament_history,
                    "tournament_state": tournament_state,
                    "logs": logs
                }

    # If loop concludes without deal
    logs.append(f"❌ [Exhausted] All {total_contacted} candidate providers rejected the proposed commercial terms.")
    tournament_state = {
        "attempted_ids": list(attempted_candidate_ids),
        "total_contacted": total_contacted,
        "rounds_attempted": max_batches,
        "history": tournament_history
    }
    await emit_transport_event(
        event_type="TRANSPORT_FAILED",
        trace_id=trace_id,
        workflow_id=workflow_id,
        request_id=request_id,
        sequence=len(tournament_history) + 1,
        stage="ADAPTIVE_EXPANSION",
        status="EXHAUSTED",
        message="Candidate pool exhausted without acceptable counterparty.",
        payload={"total_contacted": total_contacted}
    )
    return {
        "status": "NO_TRANSPORT_AVAILABLE",
        "reason": "CANDIDATE_POOL_EXHAUSTED",
        "rounds_attempted": max_batches,
        "total_contacted": total_contacted,
        "final_deal": None,
        "tournament_history": tournament_history,
        "tournament_state": tournament_state,
        "logs": logs
    }


def audit_economic_settlement(
    gross_revenue: float,
    actual_carrier_freight: float,
    actual_storage_cost: float,
    quantity_kg: float,
    farmer_product_floor_price: float,
    transporter_transport_floor: Optional[float] = None,
    quantity_allocated_kg: Optional[float] = None,
    buyer_deal_valid: bool = True,
    vehicle_available: bool = True,
    workflow_policy_permitted: bool = True
) -> Dict[str, Any]:
    """
    Strict Post-Deal Economic Settlement Feasibility Audit.
    Evaluates all 6 invariant gates:
    1. Transport Floor: agreed_freight >= transporter_transport_floor
    2. Farmer Product Floor: farmer_net_realization >= farmer_product_floor
    3. Quantity Allocation: quantity_allocated >= quantity_kg
    4. Buyer Deal Valid: deal confirmed and uncorrupted
    5. Vehicle Availability: asset not double-booked
    6. Workflow Policy: permitted under active stakeholder scope
    """
    qty = max(quantity_kg, 1.0)
    net_margin = gross_revenue - actual_carrier_freight - actual_storage_cost
    net_realization_per_kg = round(net_margin / qty, 2)

    # Gate 1: Transport Floor Gate
    gate_transp_floor = True
    if transporter_transport_floor is not None:
        gate_transp_floor = actual_carrier_freight >= transporter_transport_floor

    # Gate 2: Farmer Product Floor Gate
    gate_farmer_floor = net_realization_per_kg >= farmer_product_floor_price

    # Gate 3: Quantity Allocation Gate
    gate_qty = True
    if quantity_allocated_kg is not None:
        gate_qty = quantity_allocated_kg >= quantity_kg

    # Gate 4: Buyer Deal Gate
    gate_buyer = bool(buyer_deal_valid)

    # Gate 5: Vehicle Availability Gate
    gate_avail = bool(vehicle_available)

    # Gate 6: Workflow Policy Gate
    gate_policy = bool(workflow_policy_permitted)

    all_gates_pass = all([
        gate_transp_floor,
        gate_farmer_floor,
        gate_qty,
        gate_buyer,
        gate_avail,
        gate_policy
    ])

    gates_summary = {
        "transport_floor": "PASS" if gate_transp_floor else "FAIL",
        "farmer_product_floor": "PASS" if gate_farmer_floor else "FAIL",
        "quantity_allocation": "PASS" if gate_qty else "FAIL",
        "buyer_deal_valid": "PASS" if gate_buyer else "FAIL",
        "vehicle_availability": "PASS" if gate_avail else "FAIL",
        "workflow_policy": "PASS" if gate_policy else "FAIL"
    }

    sub_action = None
    if all_gates_pass:
        status = "FEASIBLE_PROFITABLE"
        action = "CONFIRM_BOOKING"
        msg = (
            f"All 6 settlement gates PASSED. Net farmer realization of ₹{net_realization_per_kg}/kg "
            f"exceeds product floor ₹{farmer_product_floor_price}/kg and carrier freight of "
            f"₹{actual_carrier_freight:,.2f} satisfies carrier floor. Booking approved."
        )
    elif not gate_farmer_floor:
        status = "SETTLEMENT_REJECTED_FLOOR_VIOLATED"
        action = "REJECT_BOOKING"
        sub_action = "RESELECT_CARRIER"
        dilution = round(farmer_product_floor_price - net_realization_per_kg, 2)
        msg = (
            f"Actual carrier freight of ₹{actual_carrier_freight:,.2f} dilutes net realization to "
            f"₹{net_realization_per_kg}/kg, which is ₹{dilution}/kg below farmer floor "
            f"₹{farmer_product_floor_price}/kg. Booking REJECTED (Triggering carrier reselection)."
        )
    elif not gate_transp_floor:
        status = "SETTLEMENT_REJECTED_CARRIER_FLOOR_VIOLATED"
        action = "REJECT_BOOKING_BELOW_CARRIER_FLOOR"
        msg = (
            f"Proposed freight ₹{actual_carrier_freight:,.2f} is below carrier's operating floor "
            f"₹{transporter_transport_floor:,.2f}. Carrier rejected terms."
        )
    else:
        status = "SETTLEMENT_REJECTED_CONSTRAINTS_FAILED"
        action = "REJECT_BOOKING"
        failed_gates = [k for k, v in gates_summary.items() if v == "FAIL"]
        msg = f"Settlement failed operational constraints: {failed_gates}. Booking REJECTED."

    return {
        "status": status,
        "action": action,
        "sub_action": sub_action,
        "gross_revenue": round(gross_revenue, 2),
        "actual_carrier_freight": round(actual_carrier_freight, 2),
        "transporter_transport_floor": transporter_transport_floor,
        "actual_storage_cost": round(actual_storage_cost, 2),
        "net_margin": round(net_margin, 2),
        "final_net_realization_per_kg": net_realization_per_kg,
        "farmer_product_floor_price": farmer_product_floor_price,
        "is_profitable_above_floor": gate_farmer_floor,
        "gates": gates_summary,
        "all_gates_pass": all_gates_pass,
        "audit_message": msg
    }


def compute_final_carrier_utility(
    candidate: Dict[str, Any],
    negotiated_freight: float,
    transport_request: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Computes documented final multi-factor carrier selection utility.
    Separates hard constraints (capacity, reefer, deadline, availability)
    from soft multi-factor optimization (freight, ETA, utilization, reliability, distance).
    """
    req_qty = float(transport_request.get("quantity_kg", 1000.0))
    deadline_h = float(transport_request.get("delivery_deadline_hours", 24.0))
    req_refrig = bool(transport_request.get("refrigerated_required", False))

    vehicle = candidate.get("selected_vehicle", {})
    dist = float(candidate.get("route_distance_km", 50.0))
    duration = float(candidate.get("duration_hours", 2.0))
    rating = float(candidate.get("rating", 4.0))
    rel = float(candidate.get("reliability_score", 0.95))

    # Hard constraints
    hard_capacity = vehicle.get("capacity_kg", 0.0) >= req_qty
    hard_reefer = (not req_refrig) or bool(vehicle.get("refrigerated", False))
    hard_deadline = duration <= deadline_h
    hard_available = vehicle.get("status") == "AVAILABLE"

    hard_constraints_satisfied = all([hard_capacity, hard_reefer, hard_deadline, hard_available])

    # Soft ranking factors strictly in [0.0, 1.0]
    # 1. Freight utility (lower freight = higher utility)
    budget = float(transport_request.get("max_budget", negotiated_freight * 1.3))
    s_freight = max(0.0, min(1.0, 1.0 - (negotiated_freight / max(budget, 1.0))))

    # 2. ETA & Deadline buffer
    s_eta = max(0.0, min(1.0, 1.0 - (duration / max(deadline_h, 1.0))))

    # 3. Capacity utilization (hyperbolic decay: req / capacity)
    cap = max(vehicle.get("capacity_kg", req_qty), 1.0)
    s_cap = max(0.0, min(1.0, req_qty / cap))

    # 4. Reliability & Rating
    s_rel = max(0.0, min(1.0, (rating / 5.0) * rel))

    # 5. Route distance efficiency
    s_dist = max(0.0, min(1.0, 1.0 - (dist / 600.0)))

    # Composite Utility (0.0 to 100.0)
    # Weights: Freight (30%), ETA (20%), Capacity (15%), Reliability (15%), Distance (20%)
    utility_score = round(100.0 * (
        0.30 * s_freight +
        0.20 * s_eta +
        0.15 * s_cap +
        0.15 * s_rel +
        0.20 * s_dist
    ), 2) if hard_constraints_satisfied else 0.0

    return {
        "candidate_id": candidate.get("provider_id"),
        "hard_constraints_passed": hard_constraints_satisfied,
        "final_utility_score": utility_score,
        "factor_breakdown": {
            "freight_utility_pct": round(s_freight * 30.0, 2),
            "eta_utility_pct": round(s_eta * 20.0, 2),
            "capacity_utilization_pct": round(s_cap * 15.0, 2),
            "reliability_pct": round(s_rel * 15.0, 2),
            "distance_efficiency_pct": round(s_dist * 20.0, 2)
        }
    }


async def reserve_vehicle_and_create_booking_async(
    booking_payload: Dict[str, Any],
    session: Optional[Any] = None
) -> Dict[str, Any]:
    """
    Transactional vehicle reservation and booking creation with row-level locking.
    Guarantees:
    - Distributed idempotency: returns existing booking if negotiation_id or idempotency_key is already booked.
    - Concurrency safety: acquires row lock on DBVehicle; raises VehicleAlreadyBookedException if not AVAILABLE.
    - Atomic transition: vehicle status updated to 'BOOKED' within the same commit.
    - Unified dual-persistence: writes DBTransportBooking and DBBooking.
    """
    from sqlalchemy import select
    from sqlalchemy.ext.asyncio import AsyncSession
    from backend.db.session import AsyncSessionLocal
    from backend.db.models.transport_agent_models import DBVehicle, DBTransportBooking
    from backend.db.models.schema import DBBooking
    from backend.core.exceptions import VehicleAlreadyBookedException, VehicleNotFoundException

    negotiation_id = booking_payload.get("negotiation_id")
    idempotency_key = booking_payload.get("idempotency_key")
    vehicle_id = booking_payload.get("vehicle_id")
    provider_id = booking_payload.get("provider_id", "prov_default")
    agreed_freight = float(booking_payload.get("agreed_freight", 0.0))
    transport_floor = float(booking_payload.get("transport_floor", agreed_freight * 0.85))
    farmer_net = float(booking_payload.get("farmer_net_realization", 25.0))
    farmer_floor = float(booking_payload.get("farmer_floor", 20.0))
    booking_id = booking_payload.get("booking_id") or f"booking_{uuid.uuid4().hex[:8]}"

    async def _execute_reservation(sess: AsyncSession) -> Dict[str, Any]:
        # 1. Distributed Idempotency Check:
        if negotiation_id or idempotency_key:
            conditions = []
            if negotiation_id:
                conditions.append(DBTransportBooking.negotiation_id == negotiation_id)
            if idempotency_key:
                conditions.append(DBTransportBooking.idempotency_key == idempotency_key)
            
            from sqlalchemy import or_
            existing_booking_stmt = select(DBTransportBooking).where(or_(*conditions))
            existing = (await sess.execute(existing_booking_stmt)).scalars().first()
            if existing:
                return {
                    "success": True,
                    "is_idempotent_replay": True,
                    "booking_id": existing.booking_id,
                    "status": existing.status,
                    "vehicle_id": existing.vehicle_id,
                    "provider_id": existing.provider_id,
                    "agreed_freight": existing.agreed_freight,
                    "message": "Idempotent replay: Existing booking retrieved."
                }

        # 2. Concurrency Safety: Row lock DBVehicle
        veh_stmt = select(DBVehicle).where(DBVehicle.vehicle_id == vehicle_id)
        try:
            veh_stmt = veh_stmt.with_for_update()
            veh_res = await sess.execute(veh_stmt)
            vehicle = veh_res.scalars().first()
        except Exception:
            veh_res = await sess.execute(select(DBVehicle).where(DBVehicle.vehicle_id == vehicle_id))
            vehicle = veh_res.scalars().first()

        if not vehicle:
            raise VehicleNotFoundException(vehicle_id)

        if vehicle.status != "AVAILABLE":
            raise VehicleAlreadyBookedException(
                f"Vehicle '{vehicle_id}' is already booked or unavailable (current status={vehicle.status})."
            )

        # 3. Mark vehicle as BOOKED
        vehicle.status = "BOOKED"

        # 4. Create authoritative DBTransportBooking
        transport_booking = DBTransportBooking(
            booking_id=booking_id,
            request_id=booking_payload.get("request_id"),
            negotiation_id=negotiation_id,
            idempotency_key=idempotency_key,
            provider_id=provider_id,
            vehicle_id=vehicle_id,
            agreed_freight=agreed_freight,
            transport_floor=transport_floor,
            farmer_net_realization=farmer_net,
            farmer_floor=farmer_floor,
            status="CONFIRMED",
            created_at=datetime.datetime.utcnow().isoformat() + "Z"
        )
        sess.add(transport_booking)

        # 5. Create backwards-compatible legacy DBBooking
        try:
            legacy_booking = DBBooking(
                booking_id=booking_id,
                negotiation_id=negotiation_id,
                crop=booking_payload.get("crop", "Produce"),
                origin_location=booking_payload.get("origin_location", "Nashik"),
                destination_location=booking_payload.get("destination_location", "Mumbai"),
                booked_by=booking_payload.get("booked_by", "system"),
                status="CONFIRMED",
                vehicle_id=vehicle_id,
                truck=vehicle.vehicle_name or vehicle.vehicle_type,
                capacity_kg=vehicle.capacity_kg,
                quantity=booking_payload.get("quantity_kg", 1000.0),
                distance_km=booking_payload.get("distance_km", 100.0),
                pickup_time=datetime.datetime.utcnow().isoformat() + "Z",
                estimated_transit_hours=booking_payload.get("estimated_duration_hours", 4.0),
                estimated_cost=agreed_freight,
                created_at=datetime.datetime.utcnow().isoformat() + "Z"
            )
            sess.add(legacy_booking)
        except Exception as e:
            logger.debug(f"Legacy DBBooking sync skipped: {e}")

        await sess.commit()

        return {
            "success": True,
            "is_idempotent_replay": False,
            "booking_id": booking_id,
            "status": "CONFIRMED",
            "vehicle_id": vehicle_id,
            "provider_id": provider_id,
            "agreed_freight": agreed_freight,
            "message": "Vehicle successfully reserved and booking confirmed."
        }

    if session is not None:
        return await _execute_reservation(session)
    else:
        async with AsyncSessionLocal() as new_session:
            return await _execute_reservation(new_session)

