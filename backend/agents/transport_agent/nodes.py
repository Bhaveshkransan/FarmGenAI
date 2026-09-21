"""
backend/agents/transport_agent/nodes.py

Node implementations for the Transport Agent LangGraph workflow.
All numerical calculations (cost, floor price, profit) are executed deterministically.
The LLM is used exclusively for natural-language communication and negotiation explanations.
"""

import logging
from typing import Dict, Any
from backend.agents.transport_agent.state import TransportAgentState
from backend.services.vehicle_service import filter_suitable_vehicles, get_all_vehicles
from backend.services.routing_service import calculate_transport_route
from backend.services.transport_cost_service import (
    calculate_transportation_cost, calculate_expected_profit
)
from backend.agents.transport_agent.prompts import (
    TRANSPORT_NEGOTIATION_PROMPT, TRANSPORT_PLAN_EXPLANATION_PROMPT
)
from llm.llm_client import LLMClient

logger = logging.getLogger("TransportAgentNodes")
llm_client = LLMClient()


async def receive_transport_request(state: TransportAgentState) -> Dict[str, Any]:
    """Node 1: Receive incoming transport requirement."""
    request_id = state.get("request_id") or "TR-1001"
    crop = state.get("crop", "Tomato")
    quantity_kg = float(state.get("quantity_kg", 1000.0))
    pickup_location = state.get("pickup_location", "Ahmednagar")
    delivery_location = state.get("delivery_location", "Pune")
    delivery_deadline_hours = float(state.get("delivery_deadline_hours", 12.0))
    shelf_life_hours = float(state.get("shelf_life_hours", 24.0))

    log_entry = f"Received transport request [{request_id}]: {quantity_kg}kg of {crop} from {pickup_location} to {delivery_location} (Deadline: {delivery_deadline_hours}h)."
    logger.info(log_entry)

    return {
        "request_id": request_id,
        "crop": crop,
        "quantity_kg": quantity_kg,
        "pickup_location": pickup_location,
        "delivery_location": delivery_location,
        "delivery_deadline_hours": delivery_deadline_hours,
        "shelf_life_hours": shelf_life_hours,
        "status": "PROCESSING",
        "logs": [log_entry]
    }


async def validate_request(state: TransportAgentState) -> Dict[str, Any]:
    """Node 2: Validate transport request parameters."""
    quantity_kg = state.get("quantity_kg", 0)
    pickup = state.get("pickup_location", "").strip()
    delivery = state.get("delivery_location", "").strip()
    deadline = state.get("delivery_deadline_hours", 0)

    if quantity_kg <= 0:
        return {
            "is_valid_request": False,
            "validation_error": "Quantity must be greater than 0 kg.",
            "status": "INFEASIBLE",
            "logs": ["Validation failed: Invalid quantity."]
        }

    if not pickup or not delivery:
        return {
            "is_valid_request": False,
            "validation_error": "Pickup and delivery locations must be specified.",
            "status": "INFEASIBLE",
            "logs": ["Validation failed: Missing pickup or delivery location."]
        }

    if deadline <= 0:
        return {
            "is_valid_request": False,
            "validation_error": "Delivery deadline must be greater than 0 hours.",
            "status": "INFEASIBLE",
            "logs": ["Validation failed: Invalid delivery deadline."]
        }

    return {
        "is_valid_request": True,
        "validation_error": None,
        "logs": ["Transport request validated successfully."]
    }


async def check_vehicle_availability(state: TransportAgentState) -> Dict[str, Any]:
    """Node 3: Fetch active registered fleet from database."""
    all_vehicles = await get_all_vehicles(status_filter="AVAILABLE")
    log_msg = f"Queried vehicle fleet: Found {len(all_vehicles)} active registered vehicles."
    return {
        "all_vehicles": all_vehicles,
        "logs": [log_msg]
    }


async def filter_vehicles(state: TransportAgentState) -> Dict[str, Any]:
    """Node 4: Filter vehicles by hard constraints (capacity, status, deadline, refrigeration)."""
    quantity_kg = state.get("quantity_kg", 1000.0)
    refrigerated_required = state.get("refrigerated_required", False)

    result = await filter_suitable_vehicles(
        quantity_kg=quantity_kg,
        refrigerated_required=refrigerated_required
    )

    if not result["success"]:
        log_msg = f"Vehicle filtering failed: No available vehicle meets hard constraints ({len(result['rejected_vehicles'])} rejected)."
        return {
            "candidate_vehicles": [],
            "selected_vehicle": None,
            "rejected_vehicles": result["rejected_vehicles"],
            "status": "INFEASIBLE",
            "logs": [log_msg]
        }

    selected = result["best_vehicle"]
    log_msg = f"Vehicle filter passed: Selected vehicle [{selected['vehicle_id']}] ({selected['vehicle_name']}, Type: {selected['vehicle_type']}, Capacity: {selected['capacity_kg']}kg)."
    
    return {
        "candidate_vehicles": result["candidates"],
        "selected_vehicle": selected,
        "rejected_vehicles": result["rejected_vehicles"],
        "status": "FEASIBLE",
        "logs": [log_msg]
    }


async def calculate_route(state: TransportAgentState) -> Dict[str, Any]:
    """Node 5: Calculate road distance and estimated travel duration using OSRM."""
    pickup = state.get("pickup_location", "Ahmednagar")
    delivery = state.get("delivery_location", "Pune")
    selected_vehicle = state.get("selected_vehicle") or {}

    vehicle_location = selected_vehicle.get("current_location", pickup)

    route_info = calculate_transport_route(
        pickup_location=pickup,
        delivery_location=delivery,
        vehicle_current_location=vehicle_location
    )

    dist_km = route_info["distance_km"]
    duration_h = route_info["estimated_duration_hours"]
    deadhead = route_info["deadhead_km"]

    log_msg = f"OSRM Routing calculated: {pickup} -> {delivery} = {dist_km} km, estimated travel duration: {duration_h} hours (Deadhead: {deadhead} km, Source: {route_info['routing_source']})."

    return {
        "distance_km": dist_km,
        "estimated_duration_hours": duration_h,
        "deadhead_km": deadhead,
        "routing_source": route_info["routing_source"],
        "estimated_arrival_iso": route_info["estimated_arrival_iso"],
        "logs": [log_msg]
    }


async def calculate_cost(state: TransportAgentState) -> Dict[str, Any]:
    """Node 6: Compute deterministic operating cost and risk-adjusted cost."""
    selected_vehicle = state.get("selected_vehicle") or {}
    distance_km = state.get("distance_km", 50.0)
    duration_hours = state.get("estimated_duration_hours", 2.0)
    deadhead_km = state.get("deadhead_km", 0.0)
    crop = state.get("crop", "Tomato")

    is_perishable = crop.lower() in {"tomato", "banana", "strawberry", "grape", "mango", "milk"}

    cost_result = await calculate_transportation_cost(
        vehicle=selected_vehicle,
        distance_km=distance_km,
        estimated_duration_hours=duration_hours,
        deadhead_km=deadhead_km,
        is_perishable=is_perishable
    )

    log_msg = f"Deterministic Cost Engine: Base Operating Cost = ₹{cost_result['total_operating_cost']}, Risk-Adjusted Cost = ₹{cost_result['risk_adjusted_cost']}."

    return {
        "cost_breakdown": cost_result["cost_breakdown"],
        "total_operating_cost": cost_result["total_operating_cost"],
        "risk_adjusted_cost": cost_result["risk_adjusted_cost"],
        "minimum_acceptable_price": cost_result["minimum_acceptable_price"],
        "target_price": cost_result["target_price"],
        "initial_quote": cost_result["initial_quote"],
        "logs": [log_msg]
    }


async def calculate_profit(state: TransportAgentState) -> Dict[str, Any]:
    """Node 7: Calculate minimum profit margin & expected initial profit."""
    total_cost = state.get("total_operating_cost", 1000.0)
    min_price = state.get("minimum_acceptable_price", 1200.0)
    quote = state.get("initial_quote", 1500.0)

    min_profit_info = calculate_expected_profit(min_price, total_cost)
    quote_profit_info = calculate_expected_profit(quote, total_cost)

    log_msg = f"Profit Analysis: Minimum Required Profit = ₹{min_profit_info['expected_profit']} (at Floor ₹{min_price}), Expected Quote Profit = ₹{quote_profit_info['expected_profit']} (at Quote ₹{quote})."

    return {
        "logs": [log_msg]
    }


async def calculate_floor_price(state: TransportAgentState) -> Dict[str, Any]:
    """Node 8: Finalize pricing boundaries (Floor Price, Target Price, Initial Quote)."""
    floor = state.get("minimum_acceptable_price", 1200.0)
    target = state.get("target_price", 1400.0)
    quote = state.get("initial_quote", 1500.0)

    log_msg = f"Pricing Boundaries Set: Floor Price = ₹{floor}, Target Price = ₹{target}, Initial Quote = ₹{quote}."

    return {
        "negotiation_status": "INITIAL",
        "agent_counter_offer": quote,
        "agreed_price": None,
        "logs": [log_msg]
    }


async def negotiate(state: TransportAgentState) -> Dict[str, Any]:
    """Node 9: Execute multi-round price negotiation step."""
    buyer_offer = state.get("current_buyer_offer")
    floor_price = state.get("minimum_acceptable_price", 1200.0)
    target_price = state.get("target_price", 1400.0)
    initial_quote = state.get("initial_quote", 1500.0)
    total_cost = state.get("total_operating_cost", 1000.0)
    current_round = state.get("negotiation_round", 1)
    max_rounds = state.get("max_negotiation_rounds", 3)

    if buyer_offer is None:
        # Initial agent quote issuance
        action = "QUOTE"
        counter = initial_quote
        status = "IN_NEGOTIATION"
        explanation = f"Initial freight quote issued at ₹{initial_quote} for {state.get('distance_km', 50)} km trip."
    elif buyer_offer >= floor_price:
        # Offer meets or exceeds minimum acceptable price -> ACCEPT
        action = "ACCEPTED"
        counter = buyer_offer
        status = "ACCEPTED"
        profit_info = calculate_expected_profit(buyer_offer, total_cost)
        explanation = f"Freight offer of ₹{buyer_offer} accepted! Meets minimum operating floor. Expected profit: ₹{profit_info['expected_profit']}."
    else:
        # Offer is below floor price -> COUNTER or REJECT
        if current_round >= max_rounds:
            action = "REJECTED"
            counter = None
            status = "REJECTED"
            explanation = f"Offer of ₹{buyer_offer} is below floor price ₹{floor_price}. Negotiation closed."
        else:
            action = "COUNTERED"
            # Move counter offer down towards floor price proportionally
            gap = target_price - floor_price
            reduction_factor = (current_round / max_rounds) * 0.7
            counter = round(max(floor_price, target_price - (gap * reduction_factor)), 2)
            status = "COUNTERED"
            explanation = f"Offer of ₹{buyer_offer} is below floor price. Counter-offer issued at ₹{counter}."

    # Formulate natural-language response using LLM if available (non-blocking with strict timeout)
    llm_prompt = TRANSPORT_NEGOTIATION_PROMPT.format(
        crop=state.get("crop", "Produce"),
        quantity_kg=state.get("quantity_kg", 1000),
        pickup_location=state.get("pickup_location", "Origin"),
        delivery_location=state.get("delivery_location", "Destination"),
        distance_km=state.get("distance_km", 50),
        estimated_duration_hours=state.get("estimated_duration_hours", 2.0),
        vehicle_name=(state.get("selected_vehicle") or {}).get("vehicle_name", "Vehicle"),
        vehicle_type=(state.get("selected_vehicle") or {}).get("vehicle_type", "Truck"),
        total_operating_cost=total_cost,
        minimum_acceptable_price=floor_price,
        target_price=target_price,
        buyer_offer=buyer_offer or 0.0,
        action=action,
        counter_offer=counter or floor_price
    )

    try:
        import asyncio
        llm_response = await asyncio.wait_for(
            asyncio.to_thread(llm_client.generate, llm_prompt, max_tokens=150),
            timeout=1.5
        )
    except Exception:
        llm_response = None

    final_text = llm_response if (llm_response and len(llm_response) > 10) else explanation

    history_item = {
        "round": current_round,
        "buyer_offer": buyer_offer,
        "agent_action": action,
        "agent_counter": counter,
        "status": status,
        "message": final_text
    }

    log_msg = f"Negotiation Round {current_round}: Buyer Offer = ₹{buyer_offer} -> Agent Action = {action} (Counter/Agreed: ₹{counter})."

    return {
        "negotiation_round": current_round,
        "negotiation_status": status,
        "agent_counter_offer": counter,
        "agreed_price": counter if status == "ACCEPTED" else None,
        "llm_explanation": final_text,
        "negotiation_history": [history_item],
        "logs": [log_msg]
    }


async def final_validation(state: TransportAgentState) -> Dict[str, Any]:
    """Node 10: Perform final validation before confirming transport plan."""
    status = state.get("negotiation_status")
    selected_vehicle = state.get("selected_vehicle")
    agreed_price = state.get("agreed_price")
    floor_price = state.get("minimum_acceptable_price", 0.0)

    if not selected_vehicle:
        return {
            "status": "FAILED",
            "logs": ["Final validation failed: No vehicle selected."]
        }

    if status == "ACCEPTED" and agreed_price:
        if agreed_price < floor_price:
            return {
                "status": "FAILED",
                "logs": [f"Final validation FAILED: Agreed price ₹{agreed_price} violates floor price ₹{floor_price}!"]
            }

    log_msg = "Final validation PASSED: All physical and financial constraints satisfied."
    return {
        "logs": [log_msg]
    }


async def generate_transport_plan(state: TransportAgentState) -> Dict[str, Any]:
    """Node 11: Construct final structured Transport Plan output."""
    selected = state.get("selected_vehicle")
    if not selected or state.get("status") == "INFEASIBLE":
        return {
            "final_transport_plan": None,
            "status": "INFEASIBLE",
            "logs": ["No feasible vehicle available matching hard constraints. Transport plan could not be generated."]
        }

    total_cost = state.get("total_operating_cost", 0.0)
    agreed = state.get("agreed_price") or state.get("initial_quote") or 0.0
    profit_info = calculate_expected_profit(agreed, total_cost)

    plan = {
        "request_id": state.get("request_id"),
        "crop": state.get("crop"),
        "quantity_kg": state.get("quantity_kg"),
        "pickup_location": state.get("pickup_location"),
        "delivery_location": state.get("delivery_location"),
        "delivery_deadline_hours": state.get("delivery_deadline_hours"),
        "vehicle_id": selected.get("vehicle_id"),
        "vehicle_name": selected.get("vehicle_name"),
        "vehicle_type": selected.get("vehicle_type"),
        "capacity_kg": selected.get("capacity_kg"),
        "fuel_type": selected.get("fuel_type"),
        "distance_km": state.get("distance_km"),
        "estimated_duration_hours": state.get("estimated_duration_hours"),
        "deadhead_km": state.get("deadhead_km"),
        "estimated_arrival_iso": state.get("estimated_arrival_iso"),
        "cost_breakdown": state.get("cost_breakdown"),
        "total_operating_cost": total_cost,
        "minimum_acceptable_price": state.get("minimum_acceptable_price"),
        "agreed_price": agreed,
        "expected_profit": profit_info["expected_profit"],
        "profit_margin_pct": profit_info["profit_margin_pct"],
        "negotiation_status": state.get("negotiation_status"),
        "llm_summary": state.get("llm_explanation"),
        "status": "CONFIRMED" if state.get("negotiation_status") in {"ACCEPTED", "INITIAL", "FEASIBLE"} else state.get("negotiation_status")
    }

    log_msg = f"Transport Plan generated successfully for Vehicle [{plan['vehicle_id']}] ({plan['vehicle_type']}) - Agreed Freight: ₹{agreed}, Expected Profit: ₹{plan['expected_profit']}."

    return {
        "final_transport_plan": plan,
        "status": plan["status"],
        "logs": [log_msg]
    }
