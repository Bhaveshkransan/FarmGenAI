"""
tests/intelligence/harness/perturbation_engine.py
-------------------------------------------------
Level 4: Sensitivity & Perturbation Testing Engine ("Change One Variable At a Time").
Validates that the system's reasoning and workflow behavior adapt appropriately
when single variables are perturbed (Market trend, shelf-life, storage, processor, transport).
"""

from copy import deepcopy
from typing import Dict, Any, Callable
from tests.intelligence.harness.schema import (
    ScenarioDefinition,
    ListingContext,
    MarketTrend,
    WorkflowScope,
    StakeholderRole,
    CandidateUniverseSpec,
    ExpectedInvariants,
)


def create_canonical_onion_scenario(scenario_id: str = "F-O-001") -> ScenarioDefinition:
    """
    Base Scenario F-O-001 as defined in the autonomous decision system specification:
      Crop: Onion
      Quantity: 5000 kg
      Shelf life: 7 days
      Storage: No
      Processor: Yes (Requires processing / value-add option)
      Expected price: ₹30.00
      Minimum price: ₹27.00
      Market: Rising
      Weather: Normal
      Transport: ₹2.0/tonne-km
      Mode: Full Supply Chain
    """
    return ScenarioDefinition(
        scenario_id=scenario_id,
        name="Canonical Onion Autonomous Supply Chain",
        stakeholder=StakeholderRole.FARMER,
        listing=ListingContext(
            crop="Onion",
            quantity=5000.0,
            min_price=27.0,
            expected_price=30.0,
            location="Nashik",
            grade="A",
            spoilage_days=7,
            has_transport=False,
            has_storage=False,
            requires_storage=False,
            requires_processing=True,
            holding_days=0,
            transport_rate_per_km=2.0,
        ),
        market_trend=MarketTrend.RISING,
        weather="Normal",
        workflow_mode=WorkflowScope.FULL_SUPPLY_CHAIN,
        candidate_spec=CandidateUniverseSpec(
            total_candidates=200,
            seed=101,
            target_crop_ratio=0.65,
            local_distance_ratio=0.45,
            min_budget_factor=0.85,
            max_budget_factor=1.35,
        ),
        expected=ExpectedInvariants(
            must_find_eligible=True,
            must_respect_floor=True,
            must_select_deal=True,
            expected_downstream_agents=["transport_agent", "processor_agent"],
            forbidden_downstream_agents=[],
        ),
        description="Comprehensive autonomous negotiation and supply-chain routing for 5,000kg Nashik Onions.",
    )


def generate_sensitivity_matrix(base: ScenarioDefinition) -> Dict[str, ScenarioDefinition]:
    """
    Generates the canonical Tests A through J by changing strictly ONE variable at a time.
    """
    matrix = {}

    # Test A: Market rising (Already base, but formalized)
    sc_a = deepcopy(base)
    sc_a.scenario_id = f"{base.scenario_id}-TEST-A-MARKET-RISING"
    sc_a.market_trend = MarketTrend.RISING
    matrix["TEST_A_MARKET_RISING"] = sc_a

    # Test B: Market falling
    sc_b = deepcopy(base)
    sc_b.scenario_id = f"{base.scenario_id}-TEST-B-MARKET-FALLING"
    sc_b.market_trend = MarketTrend.FALLING
    matrix["TEST_B_MARKET_FALLING"] = sc_b

    # Test C: Shelf life = 10 days
    sc_c = deepcopy(base)
    sc_c.scenario_id = f"{base.scenario_id}-TEST-C-SHELF-LIFE-10D"
    sc_c.listing.spoilage_days = 10
    matrix["TEST_C_SHELF_LIFE_10D"] = sc_c

    # Test D: Shelf life = 1 day (Extreme urgency, distant buyers disqualified)
    sc_d = deepcopy(base)
    sc_d.scenario_id = f"{base.scenario_id}-TEST-D-SHELF-LIFE-1D"
    sc_d.listing.spoilage_days = 1
    sc_d.expected.max_distance_km = 100.0  # Must choose immediate local buyer
    matrix["TEST_D_SHELF_LIFE_1D"] = sc_d

    # Test E: Storage available (Farmer has storage -> skip warehouse)
    sc_e = deepcopy(base)
    sc_e.scenario_id = f"{base.scenario_id}-TEST-E-STORAGE-AVAILABLE"
    sc_e.listing.has_storage = True
    sc_e.listing.requires_storage = False
    sc_e.expected.forbidden_downstream_agents.append("warehouse_agent")
    matrix["TEST_E_STORAGE_AVAILABLE"] = sc_e

    # Test F: Storage unavailable + holding required -> warehouse agent must engage
    sc_f = deepcopy(base)
    sc_f.scenario_id = f"{base.scenario_id}-TEST-F-STORAGE-UNAVAILABLE-HOLDING"
    sc_f.listing.has_storage = False
    sc_f.listing.requires_storage = True
    sc_f.listing.holding_days = 5
    sc_f.expected.expected_downstream_agents.append("warehouse_agent")
    matrix["TEST_F_STORAGE_UNAVAILABLE_HOLDING"] = sc_f

    # Test G: Processor available / required
    sc_g = deepcopy(base)
    sc_g.scenario_id = f"{base.scenario_id}-TEST-G-PROCESSOR-REQUIRED"
    sc_g.listing.requires_processing = True
    sc_g.expected.expected_downstream_agents.append("processor_agent")
    matrix["TEST_G_PROCESSOR_REQUIRED"] = sc_g

    # Test H: Processor unavailable / not required -> skip processor agent
    sc_h = deepcopy(base)
    sc_h.scenario_id = f"{base.scenario_id}-TEST-H-PROCESSOR-NOT-REQUIRED"
    sc_h.listing.requires_processing = False
    sc_h.expected.forbidden_downstream_agents.append("processor_agent")
    if "processor_agent" in sc_h.expected.expected_downstream_agents:
        sc_h.expected.expected_downstream_agents.remove("processor_agent")
    matrix["TEST_H_PROCESSOR_NOT_REQUIRED"] = sc_h

    # Test I: Transport cheap (₹0.80/tonne-km) -> Distant premium buyers remain viable
    sc_i = deepcopy(base)
    sc_i.scenario_id = f"{base.scenario_id}-TEST-I-TRANSPORT-CHEAP"
    sc_i.listing.transport_rate_per_km = 0.80
    matrix["TEST_I_TRANSPORT_CHEAP"] = sc_i

    # Test J: Transport expensive (₹8.0/tonne-km) -> Freight dominates, local buyers strongly prioritized
    sc_j = deepcopy(base)
    sc_j.scenario_id = f"{base.scenario_id}-TEST-J-TRANSPORT-EXPENSIVE"
    sc_j.listing.transport_rate_per_km = 8.0
    matrix["TEST_J_TRANSPORT_EXPENSIVE"] = sc_j

    return matrix
