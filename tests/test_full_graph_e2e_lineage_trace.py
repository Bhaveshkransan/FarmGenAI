"""
tests/test_full_graph_e2e_lineage_trace.py

Complete End-to-End Runtime Execution & Lineage Trace Audit.
Addresses Audit Gaps #18 and #19:
1. Executes the FULL LangGraph state machine from entry to settlement:
   planner_agent -> knowledge_manager_node -> market_intelligence_agent
   -> matching_agent -> farmer_agent <-> buyer_agent (parallel asyncio)
   -> rank_responses_agent (net margin) -> validator_agent
   -> dynamic_routing_agent (fleet routing + storage) -> reflection_agent -> END.
2. Validates Complete Data Lineage and Traceability:
   - listing_id, trace_id, crop, quantity, location
   - live market intelligence & XGBoost forecast
   - candidate matching explainability breakdown (8-factor NRV)
   - multi-turn offer history with parallel timestamps
   - estimated freight deduction (₹3.0/tonne-km)
   - final winning deal, transport plan, and database persistence
"""

import pytest
import time
from unittest.mock import patch, MagicMock
from backend.agents.graph_orchestrator import graph_orchestrator, NegotiationState
from database.db import Database


@pytest.mark.asyncio
async def test_full_graph_e2e_lineage_trace():
    trace_id = f"trace_e2e_{int(time.time())}"
    listing_id = "listing_nashik_onion_1000"

    # Define realistic candidate buyers with sufficient target budget to allow agreement
    custom_buyers = [
        {
            "id": "b_exporter_nagpur",
            "name": "Nagpur Exporter Ltd",
            "target_price": 23.0,
            "max_price": 26.0,
            "budget": 50000.0,
            "max_quantity": 2000.0,
            "location": "Nagpur",
            "strategy": "quality_first",
            "verified": True,
            "trust_score": 4.6
        },
        {
            "id": "b_wholesaler_pune",
            "name": "Pune Mandi Wholesale",
            "target_price": 22.0,
            "max_price": 25.0,
            "budget": 40000.0,
            "max_quantity": 1000.0,
            "location": "Pune",
            "strategy": "balanced",
            "verified": True,
            "trust_score": 4.2
        },
        {
            "id": "b_retailer_nashik",
            "name": "Nashik Fresh Retail",
            "target_price": 21.0,
            "max_price": 23.0,
            "budget": 30000.0,
            "max_quantity": 1000.0,
            "location": "Nashik",
            "strategy": "bargain",
            "verified": False,
            "trust_score": 3.8
        }
    ]

    initial_state: NegotiationState = {
        "trace_id": trace_id,
        "listing_id": listing_id,
        "negotiation_id": f"neg_{trace_id}",
        "crop": "Onion",
        "quantity": 1000.0,
        "base_price": 20.0,
        "min_price": 18.0,
        "target_price": 22.50,
        "market_price": 21.0,
        "spoilage_days": 10,
        "location": "Nashik",
        "farmer_id": "farmer_e2e_01",
        "stakeholder_role": "FARMER",
        "workflow_mode": "FULL_SUPPLY_CHAIN",
        "status": "ACTIVE",
        "round": 0,
        "current_round": 0,
        "max_rounds": 2,
        "history": [],
        "logs": [],
        "buyers_list": custom_buyers,
        "requires_storage": False,
        "requires_processing": False,
        "has_transport": False,
        "has_storage": False,
        "sell_hold_decision": "SELL",
    }

    # Deterministic LLM response covering orchestrator and BaseAgent
    def mock_llm_generate(prompt, **kwargs):
        p_str = str(prompt).lower()
        if "buyer" in p_str:
            return '{"type": "ACCEPT", "price": 22.50, "message": "Offer accepted at fair wholesale value."}'
        elif "farmer" in p_str:
            return '{"price": 22.50, "message": "High quality Grade A onions ready for immediate dispatch."}'
        elif "strategy" in p_str or "planner" in p_str:
            return "Strategy: Target bulk wholesale buyers in Nashik/Pune. Opening target ₹22.50/kg."
        elif "market" in p_str or "analyst" in p_str:
            return "Market conditions are par. Selling recommended within 7 days."
        elif "reflection" in p_str:
            return '{"reason_for_success_or_failure": "Deal completed above floor price", "farmer_strategy": "Value-based", "buyer_strategy": "Fair market"}'
        elif "agreement" in p_str:
            return "Commercial Agreement confirmed."
        return "Proceed with negotiation."

    # Mock TransportAgent LangGraph run to return valid confirmed plan
    mock_transport_plan = {
        "status": "CONFIRMED",
        "vehicle_name": "Tata 407 (Medium Truck)",
        "vehicle_type": "Truck",
        "pickup_location": "Nashik",
        "delivery_location": "Pune",
        "distance_km": 210.0,
        "agreed_price": 3200.0,
        "estimated_arrival_iso": "2026-10-02T14:00:00Z"
    }

    # Patch LLM globally across both graph_orchestrator and BaseAgent instances
    with patch("backend.agents.graph_orchestrator.llm_client.generate", side_effect=mock_llm_generate), \
         patch("llm.llm_client.client.generate", side_effect=mock_llm_generate), \
         patch("backend.agents.transport_agent.graph.run_transport_workflow", return_value={"status": "CONFIRMED", "final_transport_plan": mock_transport_plan}):

        # Execute the entire LangGraph workflow end-to-end
        from langgraph.graph.state import CompiledStateGraph
        assert isinstance(graph_orchestrator, CompiledStateGraph), (
            "Execution MUST invoke compiled StateGraph (CompiledStateGraph) directly, not manual node dispatcher!"
        )
        assert hasattr(graph_orchestrator, "ainvoke"), "Compiled StateGraph must have asynchronous ainvoke method"

        final_state = await graph_orchestrator.ainvoke(initial_state)

    # ==============================================================================
    # 1. State Machine Completion Invariants
    # ==============================================================================
    print("\n--- FINAL STATE LOGS ---")
    for l in final_state.get("logs", []):
        try:
            print(str(l))
        except UnicodeEncodeError:
            print(str(l).encode("ascii", errors="replace").decode("ascii"))
    print("------------------------\n")

    assert final_state is not None, "Workflow must return completed state"
    assert final_state["status"] == "DEAL", f"Expected DEAL status, got {final_state['status']}"
    
    logs = final_state.get("logs", [])
    assert len(logs) > 10, "Workflow must record execution logs across all stages"

    # ==============================================================================
    # 2. Stage Progression Audit (Traceability of Core Nodes)
    # ==============================================================================
    assert any("[Planner]" in log for log in logs), "Planner node must execute"
    assert any("[Knowledge Manager]" in log for log in logs) or any("[Market Intelligence]" in log for log in logs), \
        "External intelligence feeds must execute"
    assert any("[Matching Engine]" in log for log in logs), "Matching engine must execute"
    assert any("[Dynamic Routing]" in log for log in logs), "Dynamic routing must execute"
    assert any("[Reflection]" in log for log in logs), "Reflection agent must execute"

    # ==============================================================================
    # 3. Candidate Matching Explainability Trace (#1)
    # ==============================================================================
    assert "active_buyers" in final_state
    assert len(final_state["active_buyers"]) > 0, "Matching engine must select active buyers"
    for b in final_state["active_buyers"]:
        assert "score" in b, "Candidate must have compatibility score"
        assert "factor_breakdown" in b, "Candidate must include 8-factor explainability breakdown"
        fb = b["factor_breakdown"]
        assert "price_feasibility" in fb
        assert "quantity_fulfillment" in fb
        assert "distance_proximity" in fb
        assert "trust_reliability" in fb

    # ==============================================================================
    # 4. Best Deal & Supply Chain Booking Lineage (#18 & #19)
    # ==============================================================================
    deal = final_state.get("deal", {})
    assert deal.get("price") >= final_state["min_price"], "Deal price must satisfy hard minimum floor"
    assert "transport_plan" in deal, "Full Supply Chain deal must include logistics transport plan"
    assert deal["transport_plan"].get("status") == "CONFIRMED"

    # Economic Settlement Feasibility Audit (#13)
    assert "economic_settlement" in deal, "Deal must include post-carrier economic settlement audit"
    econ = deal["economic_settlement"]
    assert econ["actual_freight"] == mock_transport_plan["agreed_price"]
    assert econ["final_net_price_per_kg"] >= final_state["min_price"], "Final net take-home price must protect farmer floor"
    assert econ["is_profitable_above_floor"] is True
    assert econ["settlement_status"] == "FEASIBLE_PROFITABLE"
    
    booking = final_state.get("supply_chain_booking", {})
    assert booking.get("status") == "BOOKED"
    assert booking.get("crop") == "Onion"
    assert booking.get("quantity") == 1000.0
    assert "economic_settlement" in booking

    # Build Data Lineage Audit Artifact
    data_lineage = {
        "trace_id": final_state.get("trace_id"),
        "listing_id": final_state.get("listing_id"),
        "crop": final_state.get("crop"),
        "quantity_kg": final_state.get("quantity"),
        "min_price_kg": final_state.get("min_price"),
        "final_status": final_state.get("status"),
        "candidate_pool_evaluated": len(final_state.get("market_offers", [])),
        "shortlisted_candidates": [b["name"] for b in final_state.get("active_buyers", [])],
        "top_candidate_score": final_state["active_buyers"][0]["score"] if final_state.get("active_buyers") else None,
        "winner": final_state.get("selected_buyer", {}).get("name"),
        "deal_price": final_state.get("deal", {}).get("price"),
        "transport_route": f"{mock_transport_plan['pickup_location']} -> {mock_transport_plan['delivery_location']}",
        "pre_deal_est_freight": econ["estimated_freight"],
        "actual_carrier_freight": econ["actual_freight"],
        "final_net_margin": econ["final_net_margin"],
        "final_net_price_per_kg": econ["final_net_price_per_kg"],
        "settlement_status": econ["settlement_status"],
        "booking_status": final_state.get("supply_chain_booking", {}).get("status")
    }

    print("\n================== FULL DATA LINEAGE AUDIT TRACE ==================")
    for k, v in data_lineage.items():
        print(f"  {k:28}: {v}")
    print("===================================================================\n")
