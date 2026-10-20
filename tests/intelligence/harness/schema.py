"""
tests/intelligence/harness/schema.py
------------------------------------
Formal declarative schema for the Scenario-Driven Autonomous Decision System Harness.
Enables generating, parameterizing, and evaluating hundreds of business scenarios
without writing repetitive boilerplate code.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Any, Optional


class MarketTrend(str, Enum):
    RISING = "RISING"
    FALLING = "FALLING"
    STABLE = "STABLE"


class WorkflowScope(str, Enum):
    FULL_SUPPLY_CHAIN = "FULL_SUPPLY_CHAIN"
    BUYER_ONLY = "BUYER_ONLY"
    TRANSPORT_ONLY = "TRANSPORT_ONLY"
    WAREHOUSE_ONLY = "WAREHOUSE_ONLY"
    PROCESSOR_ONLY = "PROCESSOR_ONLY"


class StakeholderRole(str, Enum):
    FARMER = "FARMER"
    BUYER = "BUYER"
    TRANSPORTER = "TRANSPORTER"
    WAREHOUSE = "WAREHOUSE"
    PROCESSOR = "PROCESSOR"


@dataclass
class ListingContext:
    crop: str
    quantity: float
    min_price: float
    expected_price: float
    location: str
    grade: str = "A"
    spoilage_days: int = 7
    has_transport: bool = False
    has_storage: bool = False
    requires_storage: bool = False
    requires_processing: bool = False
    holding_days: int = 0
    transport_rate_per_km: float = 3.0  # ₹/tonne-km


@dataclass
class CandidateUniverseSpec:
    total_candidates: int = 200
    seed: int = 42
    target_crop_ratio: float = 0.6       # 60% of candidates match crop
    local_distance_ratio: float = 0.4    # 40% local (<150km), 60% regional (>150km)
    min_budget_factor: float = 0.7       # Some buyers are under-budget
    max_budget_factor: float = 1.4       # Some buyers are premium
    verified_ratio: float = 0.5


@dataclass
class ExpectedInvariants:
    must_find_eligible: bool = True
    must_respect_floor: bool = True
    must_select_deal: bool = True
    expected_workflow_path: Optional[str] = None
    expected_downstream_agents: List[str] = field(default_factory=list)
    forbidden_downstream_agents: List[str] = field(default_factory=list)
    min_net_realization: Optional[float] = None
    max_distance_km: Optional[float] = None


@dataclass
class ScenarioDefinition:
    scenario_id: str
    name: str
    stakeholder: StakeholderRole
    listing: ListingContext
    market_trend: MarketTrend
    weather: str = "Normal"
    workflow_mode: WorkflowScope = WorkflowScope.FULL_SUPPLY_CHAIN
    candidate_spec: CandidateUniverseSpec = field(default_factory=CandidateUniverseSpec)
    expected: ExpectedInvariants = field(default_factory=ExpectedInvariants)
    description: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ExplainabilityFact:
    factor_name: str
    score_a: float
    score_b: float
    delta: float
    explanation: str


@dataclass
class ComparisonEvidence:
    higher_ranked_id: str
    lower_ranked_id: str
    rank_a: int
    rank_b: int
    score_a: float
    score_b: float
    primary_advantages: List[str]
    tradeoffs: List[str]
    verdict: str


@dataclass
class ScenarioExecutionResult:
    scenario_id: str
    status: str                         # DEAL | REJECT | ERROR
    candidate_universe_size: int
    eligible_count: int
    shortlisted_count: int
    contacted_count: int
    responded_count: int
    negotiated_count: int
    acceptable_offers_count: int
    selected_deal: Optional[Dict[str, Any]]
    ranking_evidence: List[ComparisonEvidence]
    downstream_stages_executed: List[str]
    invariants_passed: bool
    invariant_violations: List[str]
    reasoning_summary: str
