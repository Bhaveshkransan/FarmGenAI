"""
backend/agents/transport_agent/state.py

Defines the LangGraph state TypedDict for the Transport Agent workflow.
"""

from typing import TypedDict, Annotated, List, Dict, Any, Optional
import operator


class TransportAgentState(TypedDict):
    # Request Input
    request_id: str
    crop: str
    quantity_kg: float
    pickup_location: str
    delivery_location: str
    delivery_deadline_hours: float
    shelf_life_hours: float
    urgency: str
    refrigerated_required: bool
    temperature_requirement_c: Optional[float]
    
    # Request Validation State
    is_valid_request: bool
    validation_error: Optional[str]

    # Vehicle Filtering State
    all_vehicles: List[Dict[str, Any]]
    candidate_vehicles: List[Dict[str, Any]]
    selected_vehicle: Optional[Dict[str, Any]]
    rejected_vehicles: List[Dict[str, Any]]

    # Routing State
    distance_km: float
    estimated_duration_hours: float
    deadhead_km: float
    routing_source: str
    estimated_arrival_iso: str

    # Financial Cost State (Deterministic)
    cost_breakdown: Dict[str, float]
    total_operating_cost: float
    risk_adjusted_cost: float
    minimum_acceptable_price: float  # Floor Price
    target_price: float
    initial_quote: float

    # Negotiation State
    current_buyer_offer: Optional[float]
    negotiation_round: int
    max_negotiation_rounds: int
    negotiation_status: str  # INITIAL | IN_NEGOTIATION | ACCEPTED | REJECTED | COUNTERED
    agent_counter_offer: Optional[float]
    agreed_price: Optional[float]
    expected_profit: Optional[float]
    llm_explanation: Optional[str]
    negotiation_history: Annotated[List[Dict[str, Any]], operator.add]

    # Workflow Logs & Status
    logs: Annotated[List[str], operator.add]
    status: str  # PROCESSING | FEASIBLE | INFEASIBLE | CONFIRMED | FAILED
    final_transport_plan: Optional[Dict[str, Any]]
