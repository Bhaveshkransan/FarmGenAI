"""
backend/agents/transport_agent/graph.py

Compiles and orchestrates the Transport Agent LangGraph StateGraph workflow.
Provides entry-point functions to run full transport planning workflows
and interactive multi-round price negotiations.
"""

import logging
from typing import Dict, Any, Optional
from langgraph.graph import StateGraph, END
from backend.agents.transport_agent.state import TransportAgentState
from backend.agents.transport_agent.nodes import (
    receive_transport_request,
    validate_request,
    check_vehicle_availability,
    filter_vehicles,
    calculate_route,
    calculate_cost,
    calculate_profit,
    calculate_floor_price,
    negotiate,
    final_validation,
    generate_transport_plan
)

logger = logging.getLogger("TransportAgentGraph")


def route_after_validation(state: TransportAgentState) -> str:
    """Conditional edge routing after request validation."""
    if not state.get("is_valid_request", True):
        return "end"
    return "check_vehicle_availability"


def route_after_filtering(state: TransportAgentState) -> str:
    """Conditional edge routing after vehicle filtering."""
    if not state.get("selected_vehicle"):
        return "generate_transport_plan"
    return "calculate_route"


def build_transport_agent_graph():
    """Build and compile the 11-node Transport Agent LangGraph workflow."""
    builder = StateGraph(TransportAgentState)

    # 1. Add nodes
    builder.add_node("receive_transport_request", receive_transport_request)
    builder.add_node("validate_request", validate_request)
    builder.add_node("check_vehicle_availability", check_vehicle_availability)
    builder.add_node("filter_vehicles", filter_vehicles)
    builder.add_node("calculate_route", calculate_route)
    builder.add_node("calculate_cost", calculate_cost)
    builder.add_node("calculate_profit", calculate_profit)
    builder.add_node("calculate_floor_price", calculate_floor_price)
    builder.add_node("negotiate", negotiate)
    builder.add_node("final_validation", final_validation)
    builder.add_node("generate_transport_plan", generate_transport_plan)

    # 2. Define edges
    builder.set_entry_point("receive_transport_request")
    builder.add_edge("receive_transport_request", "validate_request")

    builder.add_conditional_edges(
        "validate_request",
        route_after_validation,
        {
            "check_vehicle_availability": "check_vehicle_availability",
            "end": END
        }
    )

    builder.add_edge("check_vehicle_availability", "filter_vehicles")

    builder.add_conditional_edges(
        "filter_vehicles",
        route_after_filtering,
        {
            "calculate_route": "calculate_route",
            "generate_transport_plan": "generate_transport_plan"
        }
    )

    builder.add_edge("calculate_route", "calculate_cost")
    builder.add_edge("calculate_cost", "calculate_profit")
    builder.add_edge("calculate_profit", "calculate_floor_price")
    builder.add_edge("calculate_floor_price", "negotiate")
    builder.add_edge("negotiate", "final_validation")
    builder.add_edge("final_validation", "generate_transport_plan")
    builder.add_edge("generate_transport_plan", END)

    return builder.compile()


# Compile global workflow graph instance
transport_graph = build_transport_agent_graph()


async def run_transport_workflow(input_request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Entry point to run full standalone Transport Agent planning workflow.
    
    Example input_request:
    {
        "crop": "Tomato",
        "quantity_kg": 2000,
        "pickup_location": "Ahmednagar",
        "delivery_location": "Pune",
        "delivery_deadline_hours": 8,
        "buyer_offer": 4700
    }
    """
    initial_state: TransportAgentState = {
        "request_id": input_request.get("request_id") or "TR-1001",
        "crop": input_request.get("crop", "Tomato"),
        "quantity_kg": float(input_request.get("quantity_kg", 1000.0)),
        "pickup_location": input_request.get("pickup_location", "Ahmednagar"),
        "delivery_location": input_request.get("delivery_location", "Pune"),
        "delivery_deadline_hours": float(input_request.get("delivery_deadline_hours", 12.0)),
        "shelf_life_hours": float(input_request.get("shelf_life_hours", 24.0)),
        "urgency": input_request.get("urgency", "NORMAL"),
        "refrigerated_required": bool(input_request.get("refrigerated_required", False)),
        "temperature_requirement_c": input_request.get("temperature_requirement_c"),
        "is_valid_request": True,
        "validation_error": None,
        "all_vehicles": [],
        "candidate_vehicles": [],
        "selected_vehicle": None,
        "rejected_vehicles": [],
        "distance_km": 0.0,
        "estimated_duration_hours": 0.0,
        "deadhead_km": 0.0,
        "routing_source": "Pending",
        "estimated_arrival_iso": "",
        "cost_breakdown": {},
        "total_operating_cost": 0.0,
        "risk_adjusted_cost": 0.0,
        "minimum_acceptable_price": 0.0,
        "target_price": 0.0,
        "initial_quote": 0.0,
        "current_buyer_offer": input_request.get("buyer_offer"),
        "negotiation_round": 1,
        "max_negotiation_rounds": input_request.get("max_negotiation_rounds", 3),
        "negotiation_status": "INITIAL",
        "agent_counter_offer": None,
        "agreed_price": None,
        "expected_profit": None,
        "llm_explanation": None,
        "negotiation_history": [],
        "logs": [],
        "status": "PROCESSING",
        "final_transport_plan": None
    }

    final_state = await transport_graph.ainvoke(initial_state)
    return final_state


async def run_transport_negotiation(
    current_state_dict: Dict[str, Any],
    buyer_offer: float
) -> Dict[str, Any]:
    """
    Run an interactive multi-round negotiation turn on an existing transport state.
    """
    next_round = current_state_dict.get("negotiation_round", 1) + 1
    current_state_dict["current_buyer_offer"] = buyer_offer
    current_state_dict["negotiation_round"] = next_round

    # Re-run negotiate, final_validation, and generate_transport_plan
    n_res = await negotiate(current_state_dict)
    current_state_dict.update(n_res)

    v_res = await final_validation(current_state_dict)
    current_state_dict.update(v_res)

    p_res = await generate_transport_plan(current_state_dict)
    current_state_dict.update(p_res)

    return current_state_dict
