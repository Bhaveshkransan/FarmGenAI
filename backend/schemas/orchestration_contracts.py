"""
backend/schemas/orchestration_contracts.py

Multi-Agent Procurement Orchestration Contracts — Phases 1, 4, 5.
Defines standard schemas for:
1. Agent Selection & Permitted Scope.
2. Downstream Agent Context Envelope (Buyer -> Agent).
3. Standardized AgentOutcome Envelope (Agent -> Buyer Orchestrator).
4. Supply Chain Aggregation & Final Plan.
"""

from typing import Dict, Any, List, Optional, Literal
from pydantic import BaseModel, Field
from datetime import datetime, timezone


class AgentOutcome(BaseModel):
    """
    Authoritative Envelope returned by all downstream agents (TRANSPORT, WAREHOUSE, PROCESSOR)
    to the Buyer Orchestrator. Standardizes execution tracking while keeping internal results
    agent-specific.
    """
    agent: str = Field(..., description="Agent name: TRANSPORT | WAREHOUSE | PROCESSOR")
    execution_id: str = Field(..., description="Unique execution instance identifier")
    status: str = Field(..., description="COMPLETED | FAILED | BLOCKED | SKIPPED")
    requirement_id: str = Field(..., description="Scoping Buyer requirement ID")
    workflow_id: Optional[str] = Field(None, description="Buyer workflow state ID")
    started_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    completed_at: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())
    decision: str = Field("CONFIRMED", description="Executive action code: CONFIRMED | REJECTED | INFEASIBLE")
    decision_reason: str = Field("", description="Clear rationale explaining the agent decision")
    cost: float = Field(0.0, description="Cost calculated/agreed by the agent in INR")
    candidates: List[Dict[str, Any]] = Field(default_factory=list, description="Evaluated options/providers")
    selected_option: Optional[Dict[str, Any]] = Field(None, description="Winning candidate / plan summary")
    constraints_checked: Dict[str, Any] = Field(default_factory=dict, description="Constraints verified during execution")
    warnings: List[str] = Field(default_factory=list, description="Non-fatal warnings or advisories")
    error: Optional[str] = Field(None, description="Detailed error description if status == FAILED")
    retryable: bool = Field(False, description="Whether this execution can be retried safely")
    result: Dict[str, Any] = Field(default_factory=dict, description="Detailed domain-specific payload")

    def to_dict(self) -> Dict[str, Any]:
        return self.model_dump() if hasattr(self, "model_dump") else self.dict()


class DownstreamAgentContext(BaseModel):
    """
    Clean, decoupled context passed from Buyer Orchestrator to downstream agents.
    Excludes private negotiation transcripts and internal buyer heuristics.
    """
    buyer_id: str
    requirement_id: str
    workflow_id: str
    crop: str
    quantity_kg: float
    quality_grade: str = "Grade A"
    pickup_location: str
    delivery_location: str
    delivery_deadline_hours: float = 24.0
    farmer_id: Optional[str] = None
    farmer_deal_id: Optional[str] = None
    farmer_deal_price: Optional[float] = None
    farmer_deal_quantity: Optional[float] = None
    selected_agents: List[str] = Field(default_factory=list)
    completed_agents: List[str] = Field(default_factory=list)
    previous_agent_results: Dict[str, Any] = Field(default_factory=dict)
    holding_days: int = 7
    refrigerated_required: bool = False
    max_budget: Optional[float] = None
    notes: Optional[str] = None


class AgentSelectionScope(BaseModel):
    selected_agents: List[str] = Field(
        default_factory=lambda: ["FARMER", "TRANSPORT"],
        description="Authoritative list of agents requested by the Buyer: FARMER, TRANSPORT, WAREHOUSE, PROCESSOR"
    )
