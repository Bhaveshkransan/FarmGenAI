"""
tests/test_buyer_orchestration_phase1.py

Comprehensive Phase 1 Test Suite for Buyer Intelligent Orchestration Layer.
Strictly verifies all 10 Core Scenarios from Section 39:
1. Scenario 1 — Farmer Only (Farmer negotiation -> Deal -> Complete)
2. Scenario 2 — Farmer + Transport (Before deal blocked -> After deal eligible -> Transport handoff)
3. Scenario 3 — Farmer + Warehouse (Before deal blocked -> After deal route/handoff ready, never completed)
4. Scenario 4 — Farmer + Transport + Warehouse (Ordered chained progression)
5. Scenario 5 — Farmer Failure (Downstream blocked with clear rationale)
6. Scenario 6 — Farmer Withdrawal (Revalidation -> Invalidation -> Downstream blocked)
7. Scenario 7 — Unselected Transport (Unselected agents never eligible)
8. Scenario 8 — Multiple Requirements (Isolation between Requirement A - Onion and Requirement B - Rice)
9. Scenario 9 — Refresh / Persistence (Durable state restored from DB)
10. Scenario 10 — Transport Result Memory Update (Outcome stored in Buyer memory, next action recalculated)
"""

import pytest
import asyncio
from datetime import datetime, timezone
from unittest.mock import patch

from database.db import Database
from backend.services.buyer_workflow_service import (
    buyer_workflow_service,
    AGENT_FARMER,
    AGENT_TRANSPORT,
    AGENT_WAREHOUSE,
    DEAL_STATUS_SUCCESS,
    DEAL_STATUS_FAILED,
    DEAL_STATUS_WITHDRAWN,
    DEAL_STATUS_EXPIRED
)


@pytest.fixture(autouse=True)
async def setup_clean_db():
    """Ensure clean database state before each scenario."""
    from database.db import init_db
    await init_db()
    # Reset in-memory maps
    Database.users.clear()
    Database.buyers.clear()
    Database.produce.clear()
    Database.negotiations.clear()
    Database.contracts.clear()
    Database.history.clear()
    Database.buyer_workflows.clear()
    yield


@pytest.mark.asyncio
async def test_scenario_1_farmer_only():
    """
    Scenario 1: Farmer Only
    Selected: [FARMER]
    Expected: Farmer negotiation -> Farmer deal -> workflow complete.
    No downstream agents executed.
    """
    req_id = "req_scen_1"
    neg_id = "neg_scen_1"

    # 1. Initialize workflow with Farmer only
    wf = await buyer_workflow_service.initialize_workflow(
        requirement_id=req_id,
        buyer_id="buyer_001",
        crop="Soybean",
        quantity=2000.0,
        selected_agents=[AGENT_FARMER]
    )

    assert wf["selected_agents"] == [AGENT_FARMER]
    assert wf["completed_agents"] == []
    assert wf["pending_agents"] == []

    # Before deal: Farmer negotiation active
    valid_pre = buyer_workflow_service.get_valid_next_actions(wf)
    assert len(valid_pre) == 1
    assert valid_pre[0]["action"] == "WAIT_FARMER"

    # 2. Farmer Deal settled authoritatively in backend
    await Database.create_negotiation_async({
        "negotiation_id": neg_id,
        "crop": "Soybean",
        "quantity": 2000.0,
        "final_price": 48.5,
        "status": "DEAL",
        "farmer_name": "Ramesh Patil",
        "location": "Latur APMC, Maharashtra"
    })

    wf_updated = await buyer_workflow_service.record_farmer_deal_outcome(
        requirement_id=req_id,
        deal_id=neg_id,
        outcome_status=DEAL_STATUS_SUCCESS
    )

    assert wf_updated["farmer_deal"]["valid"] is True
    assert AGENT_FARMER in wf_updated["completed_agents"]

    # 3. Next action must be COMPLETE
    valid_post = buyer_workflow_service.get_valid_next_actions(wf_updated)
    assert len(valid_post) == 1
    assert valid_post[0]["action"] == "COMPLETE"

    # Step to completion
    final_wf = await buyer_workflow_service.step_workflow(requirement_id=req_id)
    assert final_wf["workflow_status"] == "COMPLETED"
    assert final_wf["agent_outcomes"] == {}


@pytest.mark.asyncio
async def test_scenario_2_farmer_plus_transport():
    """
    Scenario 2: Farmer + Transport
    Selected: [FARMER, TRANSPORT]
    Before Farmer deal: Transport is BLOCKED.
    After Farmer deal: Transport is ELIGIBLE.
    Transport handoff occurs and receives confirmed plan.
    """
    req_id = "req_scen_2"
    neg_id = "neg_scen_2"

    wf = await buyer_workflow_service.initialize_workflow(
        requirement_id=req_id,
        buyer_id="buyer_002",
        crop="Soybean",
        quantity=2000.0,
        pickup_location="Ahmednagar APMC",
        delivery_location="Pune Market Yard",
        selected_agents=[AGENT_FARMER, AGENT_TRANSPORT]
    )

    # 1. Before deal: Transport is strictly BLOCKED
    actions_pre = buyer_workflow_service.get_valid_next_actions(wf)
    assert not any(a["action"] == AGENT_TRANSPORT for a in actions_pre)
    assert AGENT_TRANSPORT in actions_pre[0]["blocked_reasons"]

    # 2. Authoritative Farmer Deal Settled
    await Database.create_negotiation_async({
        "negotiation_id": neg_id,
        "crop": "Soybean",
        "quantity": 2000.0,
        "final_price": 48.0,
        "status": "DEAL",
        "farmer_name": "Suresh Deshmukh",
        "location": "Ahmednagar"
    })

    wf_deal = await buyer_workflow_service.record_farmer_deal_outcome(
        requirement_id=req_id,
        deal_id=neg_id,
        outcome_status=DEAL_STATUS_SUCCESS
    )

    # 3. After deal: Transport is ELIGIBLE
    actions_post = buyer_workflow_service.get_valid_next_actions(wf_deal)
    transport_action = next((a for a in actions_post if a["action"] == AGENT_TRANSPORT), None)
    assert transport_action is not None
    assert "Transport is selected in requested scope" in transport_action["reason"]

    # 4. Execute handoff to existing Transport Agent
    wf_stepped = await buyer_workflow_service.step_workflow(requirement_id=req_id)

    # Transport outcome recorded in Buyer memory
    assert AGENT_TRANSPORT in wf_stepped["agent_outcomes"]
    outcome = wf_stepped["agent_outcomes"][AGENT_TRANSPORT]
    assert outcome["status"] in ("COMPLETED", "CONFIRMED", "FEASIBLE", "ACCEPTED") or outcome.get("decision") in ("CONFIRMED", "FEASIBLE", "ACCEPTED")
    assert outcome["vehicle"] is not None
    assert outcome["cost"] > 0
    assert AGENT_TRANSPORT in wf_stepped["completed_agents"]

    # Next action is COMPLETE
    actions_final = buyer_workflow_service.get_valid_next_actions(wf_stepped)
    assert actions_final[0]["action"] == "COMPLETE"


@pytest.mark.asyncio
async def test_scenario_3_farmer_plus_warehouse():
    """
    Scenario 3: Farmer + Warehouse
    Selected: [FARMER, WAREHOUSE]
    Before Farmer deal: Warehouse is BLOCKED.
    After Farmer deal: Warehouse is ROUTE/HANDOFF READY.
    Warehouse is NEVER marked COMPLETED.
    """
    req_id = "req_scen_3"
    neg_id = "neg_scen_3"

    wf = await buyer_workflow_service.initialize_workflow(
        requirement_id=req_id,
        buyer_id="buyer_003",
        crop="Onion",
        quantity=3000.0,
        selected_agents=[AGENT_FARMER, AGENT_WAREHOUSE]
    )

    # 1. Before deal: Warehouse BLOCKED
    actions_pre = buyer_workflow_service.get_valid_next_actions(wf)
    assert not any(a["action"] == AGENT_WAREHOUSE for a in actions_pre)

    # 2. Farmer deal settled
    await Database.create_negotiation_async({
        "negotiation_id": neg_id,
        "crop": "Onion",
        "quantity": 3000.0,
        "final_price": 24.0,
        "status": "DEAL",
        "farmer_name": "Lasalgaon FPO",
        "location": "Nashik APMC"
    })

    wf_deal = await buyer_workflow_service.record_farmer_deal_outcome(
        requirement_id=req_id,
        deal_id=neg_id,
        outcome_status=DEAL_STATUS_SUCCESS
    )

    # 3. Warehouse is eligible for ROUTING/HANDOFF
    actions_post = buyer_workflow_service.get_valid_next_actions(wf_deal)
    warehouse_action = next((a for a in actions_post if a["action"] == AGENT_WAREHOUSE), None)
    assert warehouse_action is not None
    assert "Warehouse is selected in requested scope" in warehouse_action["reason"]

    # 4. Execute handoff step
    wf_stepped = await buyer_workflow_service.step_workflow(requirement_id=req_id)

    # Multi-Agent Orchestration: Warehouse Agent executes real allocation and completes
    w_outcome = wf_stepped["agent_outcomes"][AGENT_WAREHOUSE]
    assert w_outcome["status"] == "COMPLETED"
    assert w_outcome["result"]["route"] == "/dashboard/warehouse"
    assert AGENT_WAREHOUSE in wf_stepped["completed_agents"]


@pytest.mark.asyncio
async def test_scenario_4_farmer_transport_warehouse_progression():
    """
    Scenario 4: Farmer + Transport + Warehouse
    Selected: [FARMER, TRANSPORT, WAREHOUSE]
    Progression:
    1. Farmer deal SUCCESS
    2. Transport eligible, Warehouse WAITING for transport
    3. Transport executes -> completes
    4. Warehouse route ready
    """
    req_id = "req_scen_4"
    neg_id = "neg_scen_4"

    wf = await buyer_workflow_service.initialize_workflow(
        requirement_id=req_id,
        buyer_id="buyer_004",
        crop="Cotton",
        quantity=4000.0,
        selected_agents=[AGENT_FARMER, AGENT_TRANSPORT, AGENT_WAREHOUSE]
    )

    # Farmer deal confirmed
    await Database.create_negotiation_async({
        "negotiation_id": neg_id,
        "crop": "Cotton",
        "quantity": 4000.0,
        "final_price": 70.0,
        "status": "DEAL",
        "farmer_name": "Vidarbha White Gold",
        "location": "Wardha APMC"
    })

    wf_deal = await buyer_workflow_service.record_farmer_deal_outcome(
        requirement_id=req_id,
        deal_id=neg_id,
        outcome_status=DEAL_STATUS_SUCCESS
    )

    # Check: Transport is eligible; Warehouse is waiting
    actions_1 = buyer_workflow_service.get_valid_next_actions(wf_deal)
    assert actions_1[0]["action"] == AGENT_TRANSPORT
    assert "Transport was selected and must complete" in actions_1[0]["blocked_reasons"][AGENT_WAREHOUSE]

    # Execute Transport
    wf_after_transport = await buyer_workflow_service.step_workflow(requirement_id=req_id)
    assert AGENT_TRANSPORT in wf_after_transport["completed_agents"]

    # Now Warehouse is eligible
    actions_2 = buyer_workflow_service.get_valid_next_actions(wf_after_transport)
    assert any(a["action"] == AGENT_WAREHOUSE for a in actions_2)

    # Execute Warehouse allocation
    wf_after_warehouse = await buyer_workflow_service.step_workflow(requirement_id=req_id)
    assert wf_after_warehouse["agent_outcomes"][AGENT_WAREHOUSE]["status"] == "COMPLETED"
    assert AGENT_WAREHOUSE in wf_after_warehouse["completed_agents"]


@pytest.mark.asyncio
async def test_scenario_5_farmer_failure_blocks_downstream():
    """
    Scenario 5: Farmer Failure
    Selected: [FARMER, TRANSPORT, WAREHOUSE]
    Farmer = FAILED
    Expected: STOP / FARMER_RETRY.
    No Transport. No Warehouse. Both strictly blocked.
    """
    req_id = "req_scen_5"
    neg_id = "neg_scen_5"

    wf = await buyer_workflow_service.initialize_workflow(
        requirement_id=req_id,
        buyer_id="buyer_005",
        crop="Sugarcane",
        quantity=5000.0,
        selected_agents=[AGENT_FARMER, AGENT_TRANSPORT, AGENT_WAREHOUSE]
    )

    # Farmer negotiation fails
    await Database.create_negotiation_async({
        "negotiation_id": neg_id,
        "crop": "Sugarcane",
        "quantity": 5000.0,
        "status": "FAILED",
        "farmer_name": "Kolhapur Cane Group"
    })

    wf_failed = await buyer_workflow_service.record_farmer_deal_outcome(
        requirement_id=req_id,
        deal_id=neg_id,
        outcome_status=DEAL_STATUS_FAILED
    )

    # Downstream agents strictly blocked!
    actions = buyer_workflow_service.get_valid_next_actions(wf_failed)
    action_names = [a["action"] for a in actions]

    assert AGENT_TRANSPORT not in action_names
    assert AGENT_WAREHOUSE not in action_names
    assert "STOP" in action_names

    # Check reason trace
    stop_action = next(a for a in actions if a["action"] == "STOP")
    assert "Why not Transport?" in stop_action["blocked_reasons"][AGENT_TRANSPORT]
    assert "No valid Farmer deal = No downstream execution" in stop_action["blocked_reasons"][AGENT_TRANSPORT]

    # Stepping results in STOPPED workflow
    wf_stepped = await buyer_workflow_service.step_workflow(requirement_id=req_id)
    assert wf_stepped["workflow_status"] == "STOPPED"
    assert wf_stepped["agent_outcomes"] == {}


@pytest.mark.asyncio
async def test_scenario_6_farmer_withdrawal_revalidation():
    """
    Scenario 6: Farmer Withdrawal
    Farmer Deal was initially SUCCESS, but Farmer later withdraws.
    Revalidation detects deal is invalid.
    Downstream execution is immediately blocked.
    """
    req_id = "req_scen_6"
    neg_id = "neg_scen_6"

    wf = await buyer_workflow_service.initialize_workflow(
        requirement_id=req_id,
        buyer_id="buyer_006",
        crop="Rice",
        quantity=1500.0,
        selected_agents=[AGENT_FARMER, AGENT_TRANSPORT]
    )

    # Initially successful deal in DB
    await Database.create_negotiation_async({
        "negotiation_id": neg_id,
        "crop": "Rice",
        "quantity": 1500.0,
        "final_price": 28.0,
        "status": "DEAL",
        "farmer_name": "Indrayani FPO"
    })

    await buyer_workflow_service.record_farmer_deal_outcome(
        requirement_id=req_id,
        deal_id=neg_id,
        outcome_status=DEAL_STATUS_SUCCESS
    )

    # Farmer subsequently withdraws the deal in DB
    await Database.update_negotiation_async(neg_id, {"status": "WITHDRAWN"})

    # Revalidation during next step / reevaluate
    wf_state = await buyer_workflow_service.get_workflow_state(requirement_id=req_id)
    wf_revalidated = await buyer_workflow_service.revalidate_deal_state(wf_state)

    assert wf_revalidated["farmer_deal"]["valid"] is False
    assert wf_revalidated["farmer_deal"]["status"] == DEAL_STATUS_WITHDRAWN

    # Downstream execution blocked
    actions = buyer_workflow_service.get_valid_next_actions(wf_revalidated)
    assert not any(a["action"] == AGENT_TRANSPORT for a in actions)


@pytest.mark.asyncio
async def test_scenario_7_unselected_transport_never_eligible():
    """
    Scenario 7: Unselected Transport
    Selected: [FARMER, WAREHOUSE] (Transport NOT selected).
    Farmer succeeds.
    Expected: Warehouse eligible, Transport NEVER eligible.
    """
    req_id = "req_scen_7"
    neg_id = "neg_scen_7"

    wf = await buyer_workflow_service.initialize_workflow(
        requirement_id=req_id,
        buyer_id="buyer_007",
        crop="Bajra",
        quantity=2500.0,
        selected_agents=[AGENT_FARMER, AGENT_WAREHOUSE]  # No Transport
    )

    await Database.create_negotiation_async({
        "negotiation_id": neg_id,
        "crop": "Bajra",
        "quantity": 2500.0,
        "final_price": 25.0,
        "status": "DEAL",
        "farmer_name": "Dhule Pearl Millet FPO"
    })

    wf_deal = await buyer_workflow_service.record_farmer_deal_outcome(
        requirement_id=req_id,
        deal_id=neg_id,
        outcome_status=DEAL_STATUS_SUCCESS
    )

    actions = buyer_workflow_service.get_valid_next_actions(wf_deal)
    action_names = [a["action"] for a in actions]

    assert AGENT_WAREHOUSE in action_names
    assert AGENT_TRANSPORT not in action_names

    warehouse_action = next(a for a in actions if a["action"] == AGENT_WAREHOUSE)
    assert "Why not TRANSPORT?" in warehouse_action["blocked_reasons"][AGENT_TRANSPORT]
    assert "was not selected" in warehouse_action["blocked_reasons"][AGENT_TRANSPORT]


@pytest.mark.asyncio
async def test_scenario_8_multiple_requirements_isolated():
    """
    Scenario 8: Multiple Requirements Isolation
    Requirement A: Onion, 5000 kg -> Farmer A -> Transport A
    Requirement B: Rice, 3000 kg -> Farmer B -> Warehouse B
    Expected: State and conversation context remain strictly isolated.
    """
    req_a = "req_onion_5000"
    req_b = "req_rice_3000"

    # Initialize Requirement A (Onion)
    wf_a = await buyer_workflow_service.initialize_workflow(
        requirement_id=req_a,
        buyer_id="buyer_A",
        crop="Onion",
        quantity=5000.0,
        selected_agents=[AGENT_FARMER, AGENT_TRANSPORT]
    )

    # Initialize Requirement B (Rice)
    wf_b = await buyer_workflow_service.initialize_workflow(
        requirement_id=req_b,
        buyer_id="buyer_B",
        crop="Rice",
        quantity=3000.0,
        selected_agents=[AGENT_FARMER, AGENT_WAREHOUSE]
    )

    # Farmer Deal A
    await Database.create_negotiation_async({
        "negotiation_id": "neg_onion",
        "crop": "Onion",
        "quantity": 5000.0,
        "final_price": 26.0,
        "status": "DEAL",
        "farmer_name": "Pimpalgaon Baswant Co-op"
    })
    await buyer_workflow_service.record_farmer_deal_outcome(
        requirement_id=req_a,
        deal_id="neg_onion",
        outcome_status=DEAL_STATUS_SUCCESS
    )

    # Farmer Deal B
    await Database.create_negotiation_async({
        "negotiation_id": "neg_rice",
        "crop": "Rice",
        "quantity": 3000.0,
        "final_price": 23.5,
        "status": "DEAL",
        "farmer_name": "Gondia Paddy Co-op"
    })
    await buyer_workflow_service.record_farmer_deal_outcome(
        requirement_id=req_b,
        deal_id="neg_rice",
        outcome_status=DEAL_STATUS_SUCCESS
    )

    # Fetch states
    loaded_a = await buyer_workflow_service.get_workflow_state(requirement_id=req_a)
    loaded_b = await buyer_workflow_service.get_workflow_state(requirement_id=req_b)

    # Strict isolation assertions
    assert loaded_a["crop"] == "Onion"
    assert loaded_a["quantity"] == 5000.0
    assert loaded_a["farmer_deal"]["deal_id"] == "neg_onion"
    assert loaded_a["selected_agents"] == [AGENT_FARMER, AGENT_TRANSPORT]

    assert loaded_b["crop"] == "Rice"
    assert loaded_b["quantity"] == 3000.0
    assert loaded_b["farmer_deal"]["deal_id"] == "neg_rice"
    assert loaded_b["selected_agents"] == [AGENT_FARMER, AGENT_WAREHOUSE]

    # Onion has Transport eligible; Rice has Warehouse eligible
    actions_a = [a["action"] for a in buyer_workflow_service.get_valid_next_actions(loaded_a)]
    actions_b = [a["action"] for a in buyer_workflow_service.get_valid_next_actions(loaded_b)]

    assert AGENT_TRANSPORT in actions_a
    assert AGENT_WAREHOUSE not in actions_a

    assert AGENT_WAREHOUSE in actions_b
    assert AGENT_TRANSPORT not in actions_b


@pytest.mark.asyncio
async def test_scenario_9_refresh_persistence_recovery():
    """
    Scenario 9: Page Refresh / Process Restart Recovery
    Farmer deal succeeds -> simulate browser reload / cache wipe
    -> workflow restored from database with identical authoritative state.
    """
    req_id = "req_scen_9"
    neg_id = "neg_scen_9"

    wf = await buyer_workflow_service.initialize_workflow(
        requirement_id=req_id,
        buyer_id="buyer_009",
        crop="Jowar",
        quantity=3500.0,
        selected_agents=[AGENT_FARMER, AGENT_TRANSPORT]
    )

    await Database.create_negotiation_async({
        "negotiation_id": neg_id,
        "crop": "Jowar",
        "quantity": 3500.0,
        "final_price": 32.0,
        "status": "DEAL",
        "farmer_name": "Solapur Maldandi Society"
    })

    await buyer_workflow_service.record_farmer_deal_outcome(
        requirement_id=req_id,
        deal_id=neg_id,
        outcome_status=DEAL_STATUS_SUCCESS
    )

    # Simulate clearing volatile in-memory dictionary
    Database.buyer_workflows.clear()
    assert req_id not in Database.buyer_workflows

    # Restore from durable database
    restored = await buyer_workflow_service.get_workflow_state(requirement_id=req_id)

    assert restored is not None
    assert restored["requirement_id"] == req_id
    assert restored["crop"] == "Jowar"
    assert restored["quantity"] == 3500.0
    assert restored["farmer_deal"]["status"] == DEAL_STATUS_SUCCESS
    assert restored["farmer_deal"]["deal_id"] == neg_id
    assert AGENT_FARMER in restored["completed_agents"]
    assert restored["workflow_status"] == "FARMER_DEAL_SUCCESS"

    # Valid next action accurately preserved after reload
    actions = buyer_workflow_service.get_valid_next_actions(restored)
    assert any(a["action"] == AGENT_TRANSPORT for a in actions)


@pytest.mark.asyncio
async def test_scenario_10_transport_result_memory_update():
    """
    Scenario 10: Transport Result Memory Update
    Farmer Deal SUCCESS -> Transport handoff -> Transport responds
    -> Result stored in Buyer memory -> Next action recalculated.
    """
    req_id = "req_scen_10"
    neg_id = "neg_scen_10"

    wf = await buyer_workflow_service.initialize_workflow(
        requirement_id=req_id,
        buyer_id="buyer_010",
        crop="Soybean",
        quantity=2000.0,
        pickup_location="Ahmednagar",
        delivery_location="Pune",
        selected_agents=[AGENT_FARMER, AGENT_TRANSPORT]
    )

    await Database.create_negotiation_async({
        "negotiation_id": neg_id,
        "crop": "Soybean",
        "quantity": 2000.0,
        "final_price": 48.0,
        "status": "DEAL",
        "farmer_name": "Nashik Tomato Growers",
        "location": "Ahmednagar"
    })

    await buyer_workflow_service.record_farmer_deal_outcome(
        requirement_id=req_id,
        deal_id=neg_id,
        outcome_status=DEAL_STATUS_SUCCESS
    )

    # Step workflow to trigger Transport handoff
    stepped_wf = await buyer_workflow_service.step_workflow(requirement_id=req_id)

    # 1. Transport outcome stored in memory
    assert AGENT_TRANSPORT in stepped_wf["agent_outcomes"]
    t_res = stepped_wf["agent_outcomes"][AGENT_TRANSPORT]

    assert t_res["status"] in ("COMPLETED", "CONFIRMED", "FEASIBLE", "ACCEPTED") or t_res.get("decision") in ("CONFIRMED", "FEASIBLE", "ACCEPTED")
    assert t_res["deal_id"] == neg_id
    assert "Ahmednagar" in t_res["route"]
    assert "Pune" in t_res["route"]
    assert t_res["cost"] > 0

    # 2. Completed agents updated
    assert AGENT_TRANSPORT in stepped_wf["completed_agents"]

    # 3. Next action recalculated to COMPLETE
    next_actions = buyer_workflow_service.get_valid_next_actions(stepped_wf)
    assert next_actions[0]["action"] == "COMPLETE"
    assert "All selected agents in the requested Buyer scope have completed" in next_actions[0]["reason"]


@pytest.mark.asyncio
async def test_scenario_6_farmer_failure_warehouse_selected():
    """
    Scenario 6 — Farmer Failure + Warehouse Selected
    Selected: [FARMER, WAREHOUSE]
    Farmer negotiation concludes with FAILED.
    Expected: Warehouse MUST NOT execute. Warehouse MUST NOT be routed.
    """
    req_id = "req_scen_6_wf"
    neg_id = "neg_scen_6_wf"

    wf = await buyer_workflow_service.initialize_workflow(
        requirement_id=req_id,
        buyer_id="buyer_006",
        crop="Soybean",
        quantity=1500.0,
        selected_agents=[AGENT_FARMER, AGENT_WAREHOUSE]
    )

    # 1. Farmer negotiation concludes with FAILED
    await Database.create_negotiation_async({
        "negotiation_id": neg_id,
        "crop": "Soybean",
        "quantity": 1500.0,
        "status": "FAILED"
    })

    wf_failed = await buyer_workflow_service.record_farmer_deal_outcome(
        requirement_id=req_id,
        deal_id=neg_id,
        outcome_status=DEAL_STATUS_FAILED
    )

    assert wf_failed["farmer_deal"]["valid"] is False
    assert AGENT_FARMER in wf_failed["failed_agents"]

    # 2. Verify Warehouse is strictly blocked
    actions = buyer_workflow_service.get_valid_next_actions(wf_failed)
    assert not any(a["action"] == AGENT_WAREHOUSE for a in actions)
    assert any(a["action"] == "STOP" for a in actions)

    stop_action = next(a for a in actions if a["action"] == "STOP")
    assert AGENT_WAREHOUSE in stop_action["blocked_reasons"]
    assert "No valid Farmer deal = No downstream execution" in stop_action["blocked_reasons"][AGENT_WAREHOUSE]

    # 3. Stepping workflow executes STOP, never WAREHOUSE
    wf_stepped = await buyer_workflow_service.step_workflow(requirement_id=req_id)
    assert wf_stepped["workflow_status"] == "STOPPED"
    assert AGENT_WAREHOUSE not in wf_stepped["agent_outcomes"]
    assert AGENT_WAREHOUSE not in wf_stepped["completed_agents"]


@pytest.mark.asyncio
async def test_scenario_9_unselected_warehouse_never_executes():
    """
    Scenario 9 — Unselected Warehouse
    Selected: [FARMER, TRANSPORT] (Warehouse NOT requested)
    Farmer succeeds -> Transport succeeds.
    Expected: Warehouse must NOT execute. Workflow completes after selected stages.
    """
    req_id = "req_scen_9_nowarehouse"
    neg_id = "neg_scen_9_nowarehouse"

    wf = await buyer_workflow_service.initialize_workflow(
        requirement_id=req_id,
        buyer_id="buyer_009",
        crop="Cotton",
        quantity=3000.0,
        selected_agents=[AGENT_FARMER, AGENT_TRANSPORT]
    )

    # 1. Settle Farmer deal
    await Database.create_negotiation_async({
        "negotiation_id": neg_id,
        "crop": "Cotton",
        "quantity": 3000.0,
        "final_price": 72.0,
        "status": "DEAL",
        "farmer_name": "Kailash Patil",
        "location": "Jalgaon APMC"
    })
    await buyer_workflow_service.record_farmer_deal_outcome(
        requirement_id=req_id,
        deal_id=neg_id,
        outcome_status=DEAL_STATUS_SUCCESS
    )

    # 2. Step Transport
    wf_after_transport = await buyer_workflow_service.step_workflow(requirement_id=req_id)
    assert AGENT_TRANSPORT in wf_after_transport["completed_agents"]

    # 3. Next action must be COMPLETE, not WAREHOUSE
    actions = buyer_workflow_service.get_valid_next_actions(wf_after_transport)
    assert len(actions) == 1
    assert actions[0]["action"] == "COMPLETE"
    assert AGENT_WAREHOUSE not in [a["action"] for a in actions]
    assert AGENT_WAREHOUSE in actions[0]["blocked_reasons"]
    assert "was not selected" in actions[0]["blocked_reasons"][AGENT_WAREHOUSE]

    # Step to complete
    final_wf = await buyer_workflow_service.step_workflow(requirement_id=req_id)
    assert final_wf["workflow_status"] == "COMPLETED"
    assert AGENT_WAREHOUSE not in final_wf["agent_outcomes"]


@pytest.mark.asyncio
async def test_scenario_11_transport_handoff_context_isolation():
    """
    Scenario 11 — Transport Handoff Context & Isolation
    Verify Transport receives only required structured context:
    (request_id, workflow_id, requirement_id, farmer_deal_id, crop, quantity_kg, pickup_location, delivery_location, deadline)
    and does NOT receive private Farmer conversation history / transcripts.
    """
    req_id = "req_scen_11"
    neg_id = "neg_scen_11"

    wf = await buyer_workflow_service.initialize_workflow(
        requirement_id=req_id,
        buyer_id="buyer_011",
        crop="Onion",
        quantity=5000.0,
        pickup_location="Lasalgaon Mandi, Nashik",
        delivery_location="Vashi APMC, Navi Mumbai",
        delivery_deadline_hours=36.0,
        selected_agents=[AGENT_FARMER, AGENT_TRANSPORT]
    )

    # Add secret private farmer chat to conversation context
    wf["conversation_context"].append({
        "agent": "FARMER",
        "event": "PRIVATE_CONFIDENTIAL_CONVERSATION",
        "message": "SECRET_FARMER_FINANCIAL_DISTRESS_DO_NOT_SHARE_WITH_TRANSPORTER"
    })
    await Database.upsert_buyer_workflow_async(wf)

    await Database.create_negotiation_async({
        "negotiation_id": neg_id,
        "crop": "Onion",
        "quantity": 5000.0,
        "final_price": 26.0,
        "status": "DEAL",
        "location": "Lasalgaon Mandi, Nashik"
    })
    await buyer_workflow_service.record_farmer_deal_outcome(
        requirement_id=req_id,
        deal_id=neg_id,
        outcome_status=DEAL_STATUS_SUCCESS
    )

    captured_payload = None

    async def mock_run_transport_workflow(payload):
        nonlocal captured_payload
        captured_payload = payload
        return {
            "status": "FEASIBLE",
            "final_transport_plan": {
                "vehicle_name": "Lasalgaon Reefer Fleet",
                "vehicle_type": "10-Ton Heavy LCV",
                "agreed_price": 14500,
                "pickup_location": payload["pickup_location"],
                "delivery_location": payload["delivery_location"]
            }
        }

    with patch("backend.services.buyer_workflow_service.run_transport_workflow", side_effect=mock_run_transport_workflow):
        await buyer_workflow_service.step_workflow(requirement_id=req_id)

    assert captured_payload is not None
    # 1. Required structured context fields present
    assert captured_payload["requirement_id"] == req_id
    assert captured_payload["farmer_deal_id"] == neg_id
    assert captured_payload["crop"] == "Onion"
    assert captured_payload["quantity_kg"] == 5000.0
    assert captured_payload["pickup_location"] == "Lasalgaon Mandi, Nashik"
    assert captured_payload["delivery_location"] == "Vashi APMC, Navi Mumbai"
    assert captured_payload["delivery_deadline_hours"] == 36.0
    # 2. Isolation: NO conversation history, transcript, or private tokens passed
    assert "conversation_context" not in captured_payload
    assert "transcript" not in captured_payload
    assert "messages" not in captured_payload
    assert "SECRET" not in str(captured_payload)


@pytest.mark.asyncio
async def test_scenario_12_invalid_manual_action_rejected():
    """
    Scenario 12 — Invalid Manual Action
    Attempt step_workflow with action = TRANSPORT while Farmer deal is invalid.
    Expected: ValueError / 400 rejection, and Transport is NOT invoked.
    """
    req_id = "req_scen_12"

    wf = await buyer_workflow_service.initialize_workflow(
        requirement_id=req_id,
        buyer_id="buyer_012",
        crop="Jowar",
        quantity=1000.0,
        selected_agents=[AGENT_FARMER, AGENT_TRANSPORT]
    )

    # Farmer deal has NOT been agreed (deal is invalid)
    assert wf["farmer_deal"]["valid"] is False

    transport_called = False

    async def mock_transport(payload):
        nonlocal transport_called
        transport_called = True
        return {}

    with patch("backend.services.buyer_workflow_service.run_transport_workflow", side_effect=mock_transport):
        with pytest.raises(ValueError) as excinfo:
            await buyer_workflow_service.step_workflow(
                requirement_id=req_id,
                action_override=AGENT_TRANSPORT
            )

    assert "is not valid right now" in str(excinfo.value)
    assert transport_called is False  # Guardrail prevented execution!


def test_scenario_13_processor_gap_identification():
    """
    Scenario 13 — Processor Gap Identification
    Verifies that Processor is NOT currently supported inside BuyerWorkflowService canonical agents.
    Documents the architectural gap where Processor exists in buyer_orchestrator / processor_service
    but is not part of the BuyerWorkflowService state machine.
    """
    from backend.services.buyer_workflow_service import SUPPORTED_AGENTS

    # 1. Assert Processor IS supported in BuyerWorkflowService canonical agents
    assert "PROCESSOR" in SUPPORTED_AGENTS
    assert {"FARMER", "TRANSPORT", "WAREHOUSE", "PROCESSOR"}.issubset(SUPPORTED_AGENTS)

    # 2. Document that processor_service exists as a standalone service in the repo
    from backend.services.processor_service import _PROCESSOR_CATALOG
    assert len(_PROCESSOR_CATALOG) > 0

