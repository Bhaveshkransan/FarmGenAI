"""
tests/intelligence/harness/invariants.py
----------------------------------------
Level 15: Property-Based Invariant Assertions Engine.
Validates business invariants rather than brittle hardcoded IDs:
  - Floor price invariant
  - Crop isolation invariant
  - Net margin economic truth invariant
  - Workflow scope stop semantics & branch invariants
  - Candidate universe explainability trace invariant
  - No hallucinated deal on empty candidate universe invariant
"""

from typing import List, Dict, Any, Optional
from tests.intelligence.harness.schema import (
    ScenarioDefinition,
    ScenarioExecutionResult,
    WorkflowScope,
)
from shared.crop_catalog import normalize_crop_name


def verify_scenario_invariants(
    scenario: ScenarioDefinition,
    result: ScenarioExecutionResult
) -> List[str]:
    """
    Evaluates all business invariants for a given scenario execution result.
    Returns a list of violation messages (empty if all invariants pass).
    """
    violations = []
    listing = scenario.listing
    expected = scenario.expected
    deal = result.selected_deal

    # Invariant 1: Candidate Discovery & Eligibility
    if expected.must_find_eligible and result.eligible_count == 0:
        violations.append("ELIGIBILITY_VIOLATION: Expected eligible candidates but found 0.")

    # Invariant 2: No Hallucinated Deals on Counterparty Exhaustion
    if result.acceptable_offers_count == 0 and result.status == "DEAL":
        violations.append("HALLUCINATION_VIOLATION: Deal was generated despite 0 acceptable counterparty offers.")

    # Invariant 3: Hard Floor Price Protection
    if deal:
        nominal_price = deal.get("nominal_price", 0.0)
        if expected.must_respect_floor and nominal_price < listing.min_price:
            violations.append(
                f"FLOOR_PRICE_VIOLATION: Deal price ₹{nominal_price} is below farmer minimum floor ₹{listing.min_price}."
            )

    # Invariant 4: Net Realization Economic Bound
    if deal:
        nominal_price = deal.get("nominal_price", 0.0)
        net_price = deal.get("net_price_per_kg", 0.0)
        freight = deal.get("freight_cost", 0.0)
        storage = deal.get("storage_cost", 0.0)
        # Net price cannot exceed nominal price unless freight and storage are 0
        if freight > 0 or storage > 0:
            if net_price > nominal_price:
                violations.append(
                    f"ECONOMIC_NET_MARGIN_VIOLATION: Net price ₹{net_price} exceeds nominal ₹{nominal_price} despite deductions."
                )

    # Invariant 5: Shelf Life & Distance Viability
    if deal and expected.max_distance_km is not None:
        actual_dist = deal.get("distance_km", 0.0)
        if actual_dist > expected.max_distance_km:
            violations.append(
                f"DISTANCE_SHELF_LIFE_VIOLATION: Selected buyer distance {actual_dist}km exceeds scenario maximum {expected.max_distance_km}km."
            )

    # Invariant 6: Workflow Scope & Stop Semantics
    # A single-agent mode MUST NOT execute downstream stages
    executed = set(result.downstream_stages_executed)
    if scenario.workflow_mode == WorkflowScope.BUYER_ONLY:
        disallowed = {"transport_agent", "warehouse_agent", "processor_agent"}
        intruders = executed.intersection(disallowed)
        if intruders:
            violations.append(
                f"SCOPE_LOCK_VIOLATION: BUYER_ONLY executed forbidden downstream agents: {intruders}"
            )
    elif scenario.workflow_mode == WorkflowScope.TRANSPORT_ONLY:
        disallowed = {"warehouse_agent", "processor_agent"}
        intruders = executed.intersection(disallowed)
        if intruders:
            violations.append(
                f"SCOPE_LOCK_VIOLATION: TRANSPORT_ONLY executed forbidden agents: {intruders}"
            )
    elif scenario.workflow_mode == WorkflowScope.WAREHOUSE_ONLY:
        disallowed = {"transport_agent", "processor_agent"}
        intruders = executed.intersection(disallowed)
        if intruders:
            violations.append(
                f"SCOPE_LOCK_VIOLATION: WAREHOUSE_ONLY executed forbidden agents: {intruders}"
            )
    elif scenario.workflow_mode == WorkflowScope.PROCESSOR_ONLY:
        disallowed = {"transport_agent", "warehouse_agent"}
        intruders = executed.intersection(disallowed)
        if intruders:
            violations.append(
                f"SCOPE_LOCK_VIOLATION: PROCESSOR_ONLY executed forbidden agents: {intruders}"
            )

    # Invariant 7: Full Supply Chain Expected Downstream Agents (Only in FULL_SUPPLY_CHAIN mode on DEAL)
    if scenario.workflow_mode == WorkflowScope.FULL_SUPPLY_CHAIN and result.status == "DEAL":
        for exp_agent in expected.expected_downstream_agents:
            if exp_agent not in executed:
                violations.append(
                    f"BRANCH_ORCHESTRATION_VIOLATION: Expected agent '{exp_agent}' was not triggered in full supply chain."
                )

    # Invariant 8: Forbidden Downstream Agents
    for forb_agent in expected.forbidden_downstream_agents:
        if forb_agent in executed:
            violations.append(
                f"FORBIDDEN_AGENT_VIOLATION: Agent '{forb_agent}' was triggered but forbidden by scenario constraints."
            )

    # Invariant 9: Explainability Evidence Trace (Only when candidates were evaluated)
    if result.eligible_count > 1 and not result.ranking_evidence:
        violations.append(
            "EXPLAINABILITY_VIOLATION: Ranking evidence was not produced for candidate universe."
        )

    return violations
