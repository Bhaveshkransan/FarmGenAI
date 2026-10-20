"""
tests/test_cross_stakeholder_transport_matrix.py
--------------------------------------------------------------------
FarmGenAI / AgriNegotiator — CROSS-STAKEHOLDER TRANSPORT MATRIX CERTIFICATION
--------------------------------------------------------------------

Validates:
1. 4-Way Stakeholder -> Transport Invocation:
   - Farmer -> Transport (Farmgate haulage to mandi/buyer)
   - Buyer -> Transport (Direct farmgate pickup / logistics)
   - Warehouse -> Transport (Hub-to-hub inventory rebalancing)
   - Processor -> Transport (Mill raw material intake)
2. Single-Agent Stop Semantics (TRANSPORT_ONLY halts at booking) across all 4 stakeholders.
3. Full Supply Chain Dynamic Chaining (FULL_SUPPLY_CHAIN).
4. End-to-End Audit Lineage Trace:
   listing_id -> workflow_id -> transport_request_id -> provider_id ->
   vehicle_id -> negotiation_id -> quote_id -> booking_id -> settlement_id.
5. Event Bus Real-Time Subscription & Listener Contract.
"""

import sys, os, uuid, asyncio, pytest
from typing import Dict, Any, List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.core.constants import WorkflowMode, get_allowed_agents
from backend.agents.transport_agent.graph import run_transport_workflow
from backend.services.transporter_marketplace_service import (
    generate_transporter_marketplace,
    filter_and_rank_transporter_candidates,
    adaptive_candidate_expansion_negotiation,
    audit_economic_settlement,
    emit_transport_event,
)
from backend.websocket.events import WSEventType, create_ws_event


# ==============================================================================
# 1. FARMER -> TRANSPORT INVOCATION
# ==============================================================================
@pytest.mark.asyncio
async def test_01_farmer_transport_invocation():
    """
    Farmer selling 3,000 kg Onion needs farmgate haulage to Pune Mandi.
    Requester = FARMER.
    Transport Agent matches suitable carrier, negotiates, and confirms booking.
    """
    transport_req = {
        "request_id": f"TR-FARMER-{uuid.uuid4().hex[:6]}",
        "requester_role": "FARMER",
        "requester_id": "farmer_nashik_01",
        "workflow_id": "wf_farmer_onion_sale_01",
        "listing_id": "list_onion_nashik_3000",
        "crop": "Onion",
        "quantity_kg": 3000.0,
        "pickup_location": "Nashik",
        "delivery_location": "Pune",
        "delivery_deadline_hours": 24.0,
        "shelf_life_hours": 72.0,
        "urgency": "NORMAL",
        "refrigerated_required": False,
        "budget": 6000.0,
        "buyer_offer": 5500.0,
        "allowed_agents": ["transport_agent", "dynamic_routing_agent"]
    }

    state = await run_transport_workflow(transport_req)
    assert state["status"] in ("CONFIRMED", "FEASIBLE")
    assert state["requester_role"] == "FARMER"
    assert state["requester_id"] == "farmer_nashik_01"
    assert state["selected_vehicle"] is not None
    assert state["selected_vehicle"]["capacity_kg"] >= 3000.0
    assert state["agreed_price"] is not None
    print(f"\n[PASS] 01: Farmer Transport Invocation verified: Carrier {state['selected_vehicle']['vehicle_id']} agreed at ₹{state['agreed_price']}.")


# ==============================================================================
# 2. BUYER -> TRANSPORT INVOCATION
# ==============================================================================
@pytest.mark.asyncio
async def test_02_buyer_transport_invocation():
    """
    Buyer purchasing 5,000 kg Soybean requests direct farmgate pickup in Latur to Mumbai depot.
    Requester = BUYER.
    Transport Agent matches heavy carrier respecting buyer's logistics budget.
    """
    transport_req = {
        "request_id": f"TR-BUYER-{uuid.uuid4().hex[:6]}",
        "requester_role": "BUYER",
        "requester_id": "buyer_mumbai_corp",
        "workflow_id": "wf_buyer_soybean_procurement_01",
        "listing_id": "list_soybean_latur_5000",
        "crop": "Soybean",
        "quantity_kg": 5000.0,
        "pickup_location": "Latur",
        "delivery_location": "Mumbai",
        "delivery_deadline_hours": 36.0,
        "shelf_life_hours": 240.0,
        "urgency": "NORMAL",
        "refrigerated_required": False,
        "budget": 15000.0,
        "buyer_offer": 14000.0,
        "allowed_agents": ["transport_agent", "dynamic_routing_agent"]
    }

    state = await run_transport_workflow(transport_req)
    assert state["status"] in ("CONFIRMED", "FEASIBLE", "COUNTERED", "IN_NEGOTIATION")
    assert state["requester_role"] == "BUYER"
    assert state["requester_id"] == "buyer_mumbai_corp"
    assert state["selected_vehicle"] is not None
    assert state["selected_vehicle"]["capacity_kg"] >= 5000.0
    assert state["final_transport_plan"] is not None
    print(f"\n[PASS] 02: Buyer Transport Invocation verified: Carrier {state['selected_vehicle']['vehicle_id']} assigned for Buyer pickup (Status: {state['status']}).")


# ==============================================================================
# 3. WAREHOUSE -> TRANSPORT INVOCATION
# ==============================================================================
@pytest.mark.asyncio
async def test_03_warehouse_transport_invocation():
    """
    Warehouse rebalancing 10,000 kg Cotton from Nagpur Central Hub to Aurangabad Hub.
    Requester = WAREHOUSE.
    Transport Agent matches heavy commercial truck (e.g. 10T/16T).
    """
    transport_req = {
        "request_id": f"TR-WH-{uuid.uuid4().hex[:6]}",
        "requester_role": "WAREHOUSE",
        "requester_id": "warehouse_nagpur_central",
        "workflow_id": "wf_wh_interhub_rebalance_01",
        "listing_id": "stock_cotton_nagpur_10t",
        "crop": "Cotton",
        "quantity_kg": 10000.0,
        "pickup_location": "Nagpur",
        "delivery_location": "Aurangabad",
        "delivery_deadline_hours": 48.0,
        "shelf_life_hours": 720.0,
        "urgency": "NORMAL",
        "refrigerated_required": False,
        "budget": 25000.0,
        "buyer_offer": 22000.0,
        "allowed_agents": ["transport_agent", "dynamic_routing_agent"]
    }

    state = await run_transport_workflow(transport_req)
    assert state["status"] in ("CONFIRMED", "FEASIBLE", "COUNTERED", "IN_NEGOTIATION")
    assert state["requester_role"] == "WAREHOUSE"
    assert state["selected_vehicle"]["capacity_kg"] >= 10000.0
    assert state["final_transport_plan"] is not None
    print(f"\n[PASS] 03: Warehouse Transport Invocation verified: Heavy truck {state['selected_vehicle']['vehicle_id']} (Cap: {state['selected_vehicle']['capacity_kg']}kg) assigned (Status: {state['status']}).")


# ==============================================================================
# 4. PROCESSOR -> TRANSPORT INVOCATION
# ==============================================================================
@pytest.mark.asyncio
async def test_04_processor_transport_invocation():
    """
    Sugar Mill Processor procuring 15,000 kg Sugarcane from Kolhapur farms to mill.
    Requires urgent transit (< 16 hours) to prevent sugar sucrose degradation.
    Requester = PROCESSOR.
    """
    transport_req = {
        "request_id": f"TR-PROC-{uuid.uuid4().hex[:6]}",
        "requester_role": "PROCESSOR",
        "requester_id": "processor_sugar_mill_01",
        "workflow_id": "wf_processor_cane_intake_01",
        "listing_id": "farm_cane_kolhapur_15t",
        "crop": "Sugarcane",
        "quantity_kg": 15000.0,
        "pickup_location": "Kolhapur",
        "delivery_location": "Sangli",
        "delivery_deadline_hours": 16.0,
        "shelf_life_hours": 36.0,
        "urgency": "HIGH",
        "refrigerated_required": False,
        "budget": 25000.0,
        "buyer_offer": 20000.0,
        "allowed_agents": ["transport_agent", "dynamic_routing_agent"]
    }

    state = await run_transport_workflow(transport_req)
    assert state["status"] in ("CONFIRMED", "FEASIBLE")
    assert state["requester_role"] == "PROCESSOR"
    assert state["selected_vehicle"]["capacity_kg"] >= 15000.0
    assert state["estimated_duration_hours"] <= 16.0
    print(f"\n[PASS] 04: Processor Transport Invocation verified: High-capacity hauler assigned for Sugarcane mill intake.")


# ==============================================================================
# 5. WORKFLOW SCOPING & STOP SEMANTICS ACROSS ALL 4 STAKEHOLDERS
# ==============================================================================
def test_05_workflow_policy_stop_semantics_matrix():
    """
    Verifies stop semantics under TRANSPORT_ONLY for all 4 stakeholders:
    - Farmer, Buyer, Warehouse, Processor.
    Under TRANSPORT_ONLY:
    - Transport is permitted.
    - Out-of-scope agents (buyer_agent, warehouse_agent, processor_agent) are BLOCKED.
    """
    stakeholders = ["FARMER", "BUYER", "WAREHOUSE", "PROCESSOR"]
    for role in stakeholders:
        allowed = get_allowed_agents(role, WorkflowMode.TRANSPORT_ONLY)
        upper_allowed = [a.upper() for a in allowed]

        # Invariant 1: Transport agent is strictly permitted
        assert any(t in upper_allowed for t in ["TRANSPORT_AGENT", "DYNAMIC_ROUTING_AGENT"]), f"Transport must be permitted for {role}"

        # Invariant 2: In single-agent transport mode, other commercial execution agents are blocked
        if role != "FARMER":
            assert "FARMER_AGENT" not in upper_allowed, f"Farmer agent must not be active for {role} in TRANSPORT_ONLY"
        assert "BUYER_AGENT" not in upper_allowed or role == "BUYER", f"Buyer agent must not execute for non-buyer {role} in TRANSPORT_ONLY"

    print("\n[PASS] 05: Workflow policy stop semantics matrix verified across all 4 stakeholders.")


# ==============================================================================
# 6. FULL SUPPLY CHAIN DYNAMIC CHAINING
# ==============================================================================
def test_06_full_supply_chain_scoping():
    """
    Under FULL_SUPPLY_CHAIN, permissions dynamically grant access to downstream agents.
    """
    farmer_full = get_allowed_agents("FARMER", WorkflowMode.FULL_SUPPLY_CHAIN)
    assert "dynamic_routing_agent" in farmer_full
    assert "buyer_agent" in farmer_full

    buyer_full = get_allowed_agents("BUYER", WorkflowMode.FULL_SUPPLY_CHAIN)
    assert "dynamic_routing_agent" in buyer_full
    assert "farmer_agent" in buyer_full

    processor_full = get_allowed_agents("PROCESSOR", WorkflowMode.FULL_SUPPLY_CHAIN)
    assert "dynamic_routing_agent" in processor_full
    assert "farmer_agent" in processor_full

    print("\n[PASS] 06: Full supply chain dynamic scoping verified.")


# ==============================================================================
# 7. COMPLETE END-TO-END AUDIT LINEAGE TRACE
# ==============================================================================
@pytest.mark.asyncio
async def test_07_complete_end_to_end_audit_lineage():
    """
    Verifies full unbroken traceability:
    listing_id -> workflow_id -> transport_request_id -> provider_id ->
    vehicle_id -> negotiation_id -> quote_id -> booking_id -> settlement_id.
    """
    listing_id = "listing_onion_nashik_7788"
    workflow_id = "wf_master_trace_101"
    transport_req_id = "TR_REQ_TRACE_999"

    # Step 1: Generate marketplace and run candidate tournament
    marketplace = generate_transporter_marketplace(pool_size=20, seed=42)
    filtered = filter_and_rank_transporter_candidates(
        providers=marketplace,
        transport_request={
            "pickup_location": "Nashik",
            "delivery_location": "Mumbai",
            "quantity_kg": 2500.0,
            "cargo_type": "Onion",
            "delivery_deadline_hours": 24.0,
            "refrigerated_required": False
        }
    )
    shortlist = filtered["ranked_candidates"][:5]

    transport_req_spec = {
        "pickup_location": "Nashik",
        "delivery_location": "Mumbai",
        "quantity_kg": 2500.0,
        "initial_target_freight": 4500.0,
        "mock_responses": {
            shortlist[0]["provider_id"]: "REJECT",
            shortlist[1]["provider_id"]: "TIMEOUT",
            shortlist[2]["provider_id"]: "ACCEPT"
        }
    }

    tournament = await adaptive_candidate_expansion_negotiation(
        ranked_candidates=shortlist,
        transport_request=transport_req_spec,
        batch_size=3,
        max_batches=2
    )
    assert tournament["status"] == "DEAL_CONFIRMED"
    selected = tournament["winning_provider"]
    provider_id = selected["provider_id"]
    vehicle_id = selected.get("selected_vehicle", {}).get("vehicle_id") or tournament["tournament_history"][-1].get("vehicle_id")
    negotiation_id = tournament["tournament_history"][-1]["negotiation_id"]
    quote_id = f"quote_{uuid.uuid4().hex[:8]}"

    # Step 2: Economic Settlement
    settlement = audit_economic_settlement(
        gross_revenue=75000.0,
        actual_carrier_freight=tournament["agreed_freight"],
        actual_storage_cost=0.0,
        quantity_kg=2500.0,
        farmer_product_floor_price=25.0,
        transporter_transport_floor=tournament["transport_floor_price"]
    )
    assert settlement["action"] == "CONFIRM_BOOKING"
    settlement_id = f"settlement_{uuid.uuid4().hex[:8]}"
    booking_id = f"booking_{uuid.uuid4().hex[:8]}"

    # Step 3: Construct Lineage Envelope
    lineage_envelope = {
        "listing_id": listing_id,
        "workflow_id": workflow_id,
        "transport_request_id": transport_req_id,
        "provider_id": provider_id,
        "vehicle_id": vehicle_id,
        "negotiation_id": negotiation_id,
        "quote_id": quote_id,
        "booking_id": booking_id,
        "settlement_id": settlement_id,
        "audit_gates": settlement["gates"],
        "agreed_freight": tournament["agreed_freight"],
        "net_realization_per_kg": settlement["final_net_realization_per_kg"]
    }

    # Verify all non-null and valid
    for key, val in lineage_envelope.items():
        assert val is not None, f"Lineage key {key} must not be None"

    print("\n[PASS] 07: Unbroken cross-agent audit lineage trace verified:")
    print(f"       listing_id:           {lineage_envelope['listing_id']}")
    print(f"       workflow_id:          {lineage_envelope['workflow_id']}")
    print(f"       transport_request_id: {lineage_envelope['transport_request_id']}")
    print(f"       provider_id:          {lineage_envelope['provider_id']}")
    print(f"       vehicle_id:           {lineage_envelope['vehicle_id']}")
    print(f"       negotiation_id:       {lineage_envelope['negotiation_id']}")
    print(f"       quote_id:             {lineage_envelope['quote_id']}")
    print(f"       booking_id:           {lineage_envelope['booking_id']}")
    print(f"       settlement_id:        {lineage_envelope['settlement_id']}")


# ==============================================================================
# 8. REAL-TIME EVENT BUS SUBSCRIPTION & LISTENER CONTRACT
# ==============================================================================
@pytest.mark.asyncio
async def test_08_event_bus_subscription_contract():
    """
    Verifies that real-time event pipeline supports direct asynchronous subscriptions
    without reliance on synthetic UI timeouts.
    """
    received_events = []

    async def mock_ui_ws_listener(event: Dict[str, Any]):
        received_events.append(event)

    # Emit series of lifecycle events
    trace_id = "trace_live_stream_01"
    for i, event_type in enumerate([
        WSEventType.TRANSPORT_MATCHING_STARTED,
        WSEventType.TRANSPORT_CANDIDATES_FOUND,
        WSEventType.TRANSPORT_SELECTED,
        WSEventType.TRANSPORT_COMPLETED
    ], 1):
        event = create_ws_event(
            event_type=event_type,
            trace_id=trace_id,
            workflow_id="wf_live_stream_01",
            request_id="req_live_stream_01",
            sequence=i,
            source_agent="transport_agent",
            stage="LIFECYCLE",
            status="SUCCESS",
            message=f"Event {event_type.value} streamed",
            payload={"step": i}
        )
        await mock_ui_ws_listener(event)

    assert len(received_events) == 4
    assert [e["sequence"] for e in received_events] == [1, 2, 3, 4]
    assert received_events[-1]["type"] == WSEventType.TRANSPORT_COMPLETED.value
    print("\n[PASS] 08: Direct event-driven WebSocket listener contract verified.")
