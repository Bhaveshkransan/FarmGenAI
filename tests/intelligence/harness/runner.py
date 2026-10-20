"""
tests/intelligence/harness/runner.py
------------------------------------
Scenario Execution Engine.
Orchestrates the entire decision flow for any given ScenarioDefinition:
  1. Candidate Universe Generation (10 to 1,000)
  2. Hard Eligibility Filtering
  3. 8-Factor NRV Matching & Ranking
  4. Traceable Explainability Comparison Evidence
  5. Multi-Stage Negotiation Funnel (Contact -> Respond -> Negotiate -> Filter -> Select)
  6. Dynamic Downstream Supply Chain Branch Determination
  7. Invariant Property Verification
"""

import time
from typing import Dict, Any, List, Optional
from tests.intelligence.harness.schema import (
    ScenarioDefinition,
    ScenarioExecutionResult,
    WorkflowScope,
)
from tests.intelligence.harness.candidate_universe import (
    generate_candidate_universe,
    evaluate_candidate_universe,
    build_ranking_evidence,
)
from tests.intelligence.harness.negotiation_simulator import (
    simulate_multi_round_negotiation,
)
from tests.intelligence.harness.invariants import (
    verify_scenario_invariants,
)


def execute_scenario(scenario: ScenarioDefinition) -> ScenarioExecutionResult:
    """
    Executes a complete business scenario deterministically through all levels
    of the autonomous supply-chain decision engine.
    """
    t_start = time.time()
    listing = scenario.listing

    # Level 1: Candidate Universe Generation
    candidates = generate_candidate_universe(listing, scenario.candidate_spec)
    universe_size = len(candidates)

    # Level 1: Eligibility Filtering & 8-factor NRV Scoring
    eligible, rejected, ranked = evaluate_candidate_universe(listing, candidates)
    eligible_count = len(eligible)

    # Level 1: Traceable Ranking Evidence (e.g. Buyer #37 vs #91)
    evidence = build_ranking_evidence(ranked, top_n=5)

    # Level 2: Negotiation Funnel
    neg_result = simulate_multi_round_negotiation(
        listing=listing,
        ranked_candidates=ranked,
        market_trend=scenario.market_trend,
        shortlist_limit=20,
        contact_limit=10,
        max_rounds=3,
    )

    shortlisted_count = len(neg_result["shortlisted"])
    contacted_count = len(neg_result["contacted"])
    responded_count = len(neg_result["responding"])
    negotiated_count = len(neg_result["negotiating"])
    acceptable_count = len(neg_result["acceptable_offers"])
    selected_deal = neg_result["selected_deal"]

    status = "DEAL" if selected_deal is not None else "REJECT"

    # Level 7: Downstream Dynamic Routing & Branch Determination
    downstream_stages = []
    mode = scenario.workflow_mode

    if status == "DEAL":
        if mode == WorkflowScope.FULL_SUPPLY_CHAIN:
            # Full supply chain evaluates downstream needs
            # 1. Transport evaluation:
            if not listing.has_transport:
                downstream_stages.append("transport_agent")

            # 2. Warehouse evaluation:
            # Needed if farmer lacks storage AND (holding > 0, spoilage <= 7, or explicitly required)
            needs_storage = (not listing.has_storage) and (listing.requires_storage or listing.holding_days > 0 or listing.spoilage_days <= 7)
            if needs_storage:
                downstream_stages.append("warehouse_agent")

            # 3. Processor evaluation:
            if listing.requires_processing:
                downstream_stages.append("processor_agent")

        elif mode == WorkflowScope.BUYER_ONLY:
            # Stop immediately after buyer stage
            pass
        elif mode == WorkflowScope.TRANSPORT_ONLY:
            downstream_stages.append("transport_agent")
        elif mode == WorkflowScope.WAREHOUSE_ONLY:
            downstream_stages.append("warehouse_agent")
        elif mode == WorkflowScope.PROCESSOR_ONLY:
            downstream_stages.append("processor_agent")

    # Reasoning Summary Construction
    reasoning = (
        f"Evaluated {universe_size} counterparties -> {eligible_count} eligible. "
        f"Shortlisted top {shortlisted_count}, contacted {contacted_count}, {responded_count} responded. "
        f"{negotiated_count} entered multi-round negotiation -> {acceptable_count} met floor price ₹{listing.min_price}. "
    )
    if selected_deal:
        reasoning += (
            f"Selected Best Deal: {selected_deal['buyer_name']} at nominal ₹{selected_deal['nominal_price']}/kg "
            f"(Net take-home ₹{selected_deal['net_price_per_kg']}/kg after ₹{selected_deal['freight_cost']} freight). "
            f"Downstream stages triggered: {downstream_stages if downstream_stages else 'None (Terminal)'}."
        )
    else:
        reasoning += "No viable counterparty satisfied holistic constraints. Order safely aborted without hallucination."

    result = ScenarioExecutionResult(
        scenario_id=scenario.scenario_id,
        status=status,
        candidate_universe_size=universe_size,
        eligible_count=eligible_count,
        shortlisted_count=shortlisted_count,
        contacted_count=contacted_count,
        responded_count=responded_count,
        negotiated_count=negotiated_count,
        acceptable_offers_count=acceptable_count,
        selected_deal=selected_deal,
        ranking_evidence=evidence,
        downstream_stages_executed=downstream_stages,
        invariants_passed=True,
        invariant_violations=[],
        reasoning_summary=reasoning,
    )

    # Level 15: Run invariant checks
    violations = verify_scenario_invariants(scenario, result)
    result.invariant_violations = violations
    result.invariants_passed = len(violations) == 0

    return result
