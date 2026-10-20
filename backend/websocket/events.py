"""
backend/websocket/events.py

Strict, typed schemas for all WebSocket events traversing the frontend ↔ backend boundary.
Enforces the 20+ named event types rather than unstructured string logs.
"""

from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from enum import Enum


class WSEventType(str, Enum):
    # System Lifecycle
    CONNECTION_ESTABLISHED = "CONNECTION_ESTABLISHED"
    NEGOTIATION_STARTED = "NEGOTIATION_STARTED"
    NEGOTIATION_COMPLETED = "NEGOTIATION_COMPLETED"
    NEGOTIATION_FAILED = "NEGOTIATION_FAILED"
    ERROR = "ERROR"

    # Agent Activity
    AGENT_THINKING = "AGENT_THINKING"
    AGENT_ACTION = "AGENT_ACTION"
    MARKET_DATA_FETCHED = "MARKET_DATA_FETCHED"
    RAG_CONTEXT_RETRIEVED = "RAG_CONTEXT_RETRIEVED"
    MATCHES_FOUND = "MATCHES_FOUND"

    # Negotiation Loop
    FARMER_OFFER_GENERATED = "FARMER_OFFER_GENERATED"
    BUYER_COUNTER_OFFER = "BUYER_COUNTER_OFFER"
    OFFER_VALIDATED = "OFFER_VALIDATED"
    OFFER_REJECTED = "OFFER_REJECTED"

    # Logistics & Transport Lifecycle
    TRANSPORT_MATCHING_STARTED = "TRANSPORT_MATCHING_STARTED"
    TRANSPORT_CANDIDATES_FOUND = "TRANSPORT_CANDIDATES_FOUND"
    TRANSPORT_FILTERED = "TRANSPORT_FILTERED"
    TRANSPORT_SHORTLISTED = "TRANSPORT_SHORTLISTED"
    TRANSPORTER_CONTACTED = "TRANSPORTER_CONTACTED"
    TRANSPORTER_RESPONSE = "TRANSPORTER_RESPONSE"
    TRANSPORT_NEGOTIATION_STARTED = "TRANSPORT_NEGOTIATION_STARTED"
    TRANSPORT_COUNTER_OFFER = "TRANSPORT_COUNTER_OFFER"
    TRANSPORT_QUOTE_RECEIVED = "TRANSPORT_QUOTE_RECEIVED"
    TRANSPORT_BEST_QUOTE_UPDATED = "TRANSPORT_BEST_QUOTE_UPDATED"
    TRANSPORT_SELECTED = "TRANSPORT_SELECTED"
    TRANSPORT_FAILED = "TRANSPORT_FAILED"
    TRANSPORT_COMPLETED = "TRANSPORT_COMPLETED"
    TRANSPORT_BID_RECEIVED = "TRANSPORT_BID_RECEIVED"
    WAREHOUSE_CAPACITY_CHECKED = "WAREHOUSE_CAPACITY_CHECKED"
    LOGISTICS_PLAN_FINALIZED = "LOGISTICS_PLAN_FINALIZED"

    # Fallback / Reflection
    STRATEGY_UPDATED = "STRATEGY_UPDATED"
    PROCESSOR_ESCALATION = "PROCESSOR_ESCALATION"
    COMPOST_ESCALATION = "COMPOST_ESCALATION"


class WSEventSchema(BaseModel):
    """
    Standard envelope for all WebSocket messages with complete audit lineage.
    """
    type: WSEventType = Field(..., description="The strict event type.")
    trace_id: str = Field(..., description="Unique trace ID tying this event to a specific E2E workflow run.")
    workflow_id: Optional[str] = Field(None, description="The workflow execution ID.")
    request_id: Optional[str] = Field(None, description="The transport or matching request ID.")
    negotiation_id: Optional[str] = Field(None, description="The active negotiation ID, if applicable.")
    provider_id: Optional[str] = Field(None, description="Counterparty transport provider ID.")
    vehicle_id: Optional[str] = Field(None, description="Counterparty vehicle ID.")
    sequence: Optional[int] = Field(None, description="Monotonically increasing sequence number.")
    stage: Optional[str] = Field(None, description="Current workflow stage.")
    status: Optional[str] = Field(None, description="Current lifecycle status.")
    source_agent: str = Field(..., description="Emitting agent or node.")
    timestamp: str = Field(..., description="ISO 8601 timestamp.")
    message: str = Field(..., description="Human-readable summary of the event.")
    payload: Dict[str, Any] = Field(default_factory=dict, description="Structured data associated with the event.")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Additional context (e.g., crop, location, latency).")

    class Config:
        use_enum_values = True


def create_ws_event(
    event_type: WSEventType,
    trace_id: str,
    source_agent: str,
    message: str,
    negotiation_id: Optional[str] = None,
    workflow_id: Optional[str] = None,
    request_id: Optional[str] = None,
    provider_id: Optional[str] = None,
    vehicle_id: Optional[str] = None,
    sequence: Optional[int] = None,
    stage: Optional[str] = None,
    status: Optional[str] = None,
    payload: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Helper to create a serialized WS event dictionary with complete lineage."""
    import datetime
    return WSEventSchema(
        type=event_type,
        trace_id=trace_id,
        workflow_id=workflow_id,
        request_id=request_id,
        negotiation_id=negotiation_id,
        provider_id=provider_id,
        vehicle_id=vehicle_id,
        sequence=sequence,
        stage=stage,
        status=status,
        source_agent=source_agent,
        timestamp=datetime.datetime.utcnow().isoformat() + "Z",
        message=message,
        payload=payload or {},
        metadata=metadata or {}
    ).model_dump()
