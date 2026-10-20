"""
tests/test_multi_agent_real_execution.py

Acceptance Test Suite for Multi-Agent Procurement Orchestration — Phases 17 & 18.
Strictly verifies that:
1. When Buyer selects an agent, the system communicates with and executes that agent's actual backend/graph/service.
2. No mock logic is used for downstream agents in the primary acceptance tests.
3. All 18 Test Cases from Phase 17 are covered:
   - TEST 1: Base procurement (Farmer only)
   - TEST 2: Transport only (Farmer -> Transport)
   - TEST 3: Warehouse only (Farmer -> Warehouse)
   - TEST 4: Processor only (Farmer -> Processor)
   - TEST 5: Transport + Warehouse
   - TEST 6: Transport + Processor
   - TEST 7: Warehouse + Processor
   - TEST 8: Transport + Warehouse + Processor (All 3)
   - TEST 9: Transport failure handling
   - TEST 10: Warehouse failure handling
   - TEST 11: Processor failure handling
   - TEST 12: Farmer deal invalid/withdrawn blocks downstream
   - TEST 13: Buyer invokes unselected agent (rejected)
   - TEST 14: Double-click idempotency
   - TEST 15: Browser refresh / persistence restore
   - TEST 16: Backend restart / revalidation
   - TEST 17: Simultaneous buyers isolation
   - TEST 18: Malformed / error handling resilience
"""

import pytest
import asyncio
from datetime import datetime, timezone

from database.db import Database, init_db
from backend.services.buyer_workflow_service import (
    buyer_workflow_service,
    AGENT_FARMER,
    AGENT_TRANSPORT,
    AGENT_WAREHOUSE,
    AGENT_PROCESSOR,
    DEAL_STATUS_SUCCESS,
    DEAL_STATUS_FAILED,
    DEAL_STATUS_WITHDRAWN
)


@pytest.fixture(autouse=True)
async def setup_clean_db():
    """Ensure clean database state before each test."""
    await init_db()
    Database.users.clear()
    Database.buyers.clear()
    Database.produce.clear()
    Database.negotiations.clear()
    Database.contracts.clear()
    Database.history.clear()
    Database.buyer_workflows.clear()
    yield


@pytest.mark.asyncio
async def test_01_buyer_selects_no_downstream_agent():
    """
    TEST 1: Buyer selects no downstream agent (Farmer only).
    Expected: Only the allowed base procurement flow executes.
    """
    req_id = "req_test_01"
    neg_id = "neg_test_01"

    wf = await buyer_workflow_service.initialize_workflow(
        requirement_id=req_id,
        buyer_id="buyer_01",
        crop="Soybean",
        quantity=1500.0,
        selected_agents=[AGENT_FARMER]
    )

    assert wf["selected_agents"] == [AGENT_FARMER]
    assert wf["pending_agents"] == []

    # Settle Farmer deal
    await Database.create_negotiation_async({
        "negotiation_id": neg_id,
        "crop": "Soybean",
        "quantity": 1500.0,
        "final_price": 49.0,
        "status": "DEAL",
        "farmer_name": "Latur FPO",
        "location": "Latur APMC"
    })

    wf_deal = await buyer_workflow_service.record_farmer_deal_outcome(
        requirement_id=req_id,
        deal_id=neg_id,
        outcome_status=DEAL_STATUS_SUCCESS
    )

    # Next action must be COMPLETE
    actions = buyer_workflow_service.get_valid_next_actions(wf_deal)
    assert any(a["action"] == "COMPLETE" for a in actions)
    assert not any(a["action"] in (AGENT_TRANSPORT, AGENT_WAREHOUSE, AGENT_PROCESSOR) for a in actions)

    # Complete workflow
    wf_final = await buyer_workflow_service.step_workflow(requirement_id=req_id)
    assert wf_final["workflow_status"] == "COMPLETED"
    assert wf_final["final_plan"] is not None
    assert wf_final["final_plan"]["transport_plan"] is None
    assert wf_final["final_plan"]["warehouse_plan"] is None
    assert wf_final["final_plan"]["processor_plan"] is None


@pytest.mark.asyncio
async def test_02_buyer_selects_transport_only():
    """
    TEST 2: Buyer selects Transport only.
    Expected: Farmer prerequisite -> Transport Agent -> REAL Transport execution -> Transport result -> Buyer state.
    """
    req_id = "req_test_02"
    neg_id = "neg_test_02"

    wf = await buyer_workflow_service.initialize_workflow(
        requirement_id=req_id,
        buyer_id="buyer_02",
        crop="Soybean",
        quantity=2000.0,
        pickup_location="Ahmednagar",
        delivery_location="Pune",
        selected_agents=[AGENT_FARMER, AGENT_TRANSPORT]
    )

    # Before farmer deal: Transport is blocked
    actions_pre = buyer_workflow_service.get_valid_next_actions(wf)
    assert not any(a["action"] == AGENT_TRANSPORT for a in actions_pre)

    # Settle Farmer deal
    await Database.create_negotiation_async({
        "negotiation_id": neg_id,
        "crop": "Soybean",
        "quantity": 2000.0,
        "final_price": 50.0,
        "status": "DEAL",
        "farmer_name": "Ahmednagar FPO",
        "location": "Ahmednagar APMC"
    })

    await buyer_workflow_service.record_farmer_deal_outcome(
        requirement_id=req_id,
        deal_id=neg_id,
        outcome_status=DEAL_STATUS_SUCCESS
    )

    # Real Transport execution
    wf_stepped = await buyer_workflow_service.step_workflow(requirement_id=req_id, action_override=AGENT_TRANSPORT)

    # Verify REAL transport result
    assert AGENT_TRANSPORT in wf_stepped["completed_agents"]
    t_outcome = wf_stepped["agent_outcomes"][AGENT_TRANSPORT]
    assert t_outcome["status"] == "COMPLETED"
    assert t_outcome["decision"] == "CONFIRMED"
    assert t_outcome["cost"] > 0
    assert "vehicle" in t_outcome["result"]
    assert "route" in t_outcome["result"]
    assert "Ahmednagar" in t_outcome["result"]["route"]


@pytest.mark.asyncio
async def test_03_buyer_selects_warehouse_only():
    """
    TEST 3: Buyer selects Warehouse only.
    Expected: Farmer prerequisite -> Warehouse Agent -> REAL Warehouse execution -> Warehouse result -> Buyer state.
    """
    req_id = "req_test_03"
    neg_id = "neg_test_03"

    wf = await buyer_workflow_service.initialize_workflow(
        requirement_id=req_id,
        buyer_id="buyer_03",
        crop="Onion",
        quantity=3000.0,
        delivery_location="Nashik",
        selected_agents=[AGENT_FARMER, AGENT_WAREHOUSE]
    )

    # Settle Farmer deal
    await Database.create_negotiation_async({
        "negotiation_id": neg_id,
        "crop": "Onion",
        "quantity": 3000.0,
        "final_price": 22.0,
        "status": "DEAL",
        "farmer_name": "Lasalgaon FPO",
        "location": "Lasalgaon, Nashik"
    })

    await buyer_workflow_service.record_farmer_deal_outcome(
        requirement_id=req_id,
        deal_id=neg_id,
        outcome_status=DEAL_STATUS_SUCCESS
    )

    # Warehouse is eligible immediately because Transport was not requested
    actions = buyer_workflow_service.get_valid_next_actions(await buyer_workflow_service.get_workflow_state(requirement_id=req_id))
    assert any(a["action"] == AGENT_WAREHOUSE for a in actions)

    # Execute REAL Warehouse workflow
    wf_stepped = await buyer_workflow_service.step_workflow(requirement_id=req_id, action_override=AGENT_WAREHOUSE)

    # Verify REAL warehouse result
    assert AGENT_WAREHOUSE in wf_stepped["completed_agents"]
    w_outcome = wf_stepped["agent_outcomes"][AGENT_WAREHOUSE]
    assert w_outcome["status"] == "COMPLETED"
    assert w_outcome["decision"] == "CONFIRMED"
    assert w_outcome["cost"] > 0
    assert "warehouse_id" in w_outcome["result"]
    assert "reservation_id" in w_outcome["result"]
    assert w_outcome["result"]["holding_days"] == 7


@pytest.mark.asyncio
async def test_04_buyer_selects_processor_only():
    """
    TEST 4: Buyer selects Processor only.
    Expected: Farmer prerequisite -> Processor Agent -> REAL Processor execution -> Processor result -> Buyer state.
    """
    req_id = "req_test_04"
    neg_id = "neg_test_04"

    wf = await buyer_workflow_service.initialize_workflow(
        requirement_id=req_id,
        buyer_id="buyer_04",
        crop="Soybean",
        quantity=2500.0,
        delivery_location="Latur",
        selected_agents=[AGENT_FARMER, AGENT_PROCESSOR]
    )

    # Settle Farmer deal
    await Database.create_negotiation_async({
        "negotiation_id": neg_id,
        "crop": "Soybean",
        "quantity": 2500.0,
        "final_price": 48.5,
        "status": "DEAL",
        "farmer_name": "Latur Farmers Guild",
        "location": "Latur APMC"
    })

    await buyer_workflow_service.record_farmer_deal_outcome(
        requirement_id=req_id,
        deal_id=neg_id,
        outcome_status=DEAL_STATUS_SUCCESS
    )

    # Processor is eligible immediately because Transport and Warehouse were not requested
    actions = buyer_workflow_service.get_valid_next_actions(await buyer_workflow_service.get_workflow_state(requirement_id=req_id))
    assert any(a["action"] == AGENT_PROCESSOR for a in actions)

    # Execute REAL Processor workflow
    wf_stepped = await buyer_workflow_service.step_workflow(requirement_id=req_id, action_override=AGENT_PROCESSOR)

    # Verify REAL processor result
    assert AGENT_PROCESSOR in wf_stepped["completed_agents"]
    p_outcome = wf_stepped["agent_outcomes"][AGENT_PROCESSOR]
    assert p_outcome["status"] == "COMPLETED"
    assert p_outcome["decision"] == "CONFIRMED"
    assert p_outcome["cost"] > 0
    assert "output_product" in p_outcome["result"]
    assert "batch_id" in p_outcome["result"]
    assert "Soybean" in p_outcome["result"]["output_product"] or "Oil" in p_outcome["result"]["output_product"]


@pytest.mark.asyncio
async def test_05_buyer_selects_transport_and_warehouse():
    """
    TEST 5: Buyer selects Transport + Warehouse.
    Expected: Both actual agents execute according to dependency graph:
    Farmer -> Transport -> Warehouse.
    """
    req_id = "req_test_05"
    neg_id = "neg_test_05"

    await buyer_workflow_service.initialize_workflow(
        requirement_id=req_id,
        buyer_id="buyer_05",
        crop="Tomato",
        quantity=1200.0,
        pickup_location="Nashik",
        delivery_location="Pune",
        selected_agents=[AGENT_FARMER, AGENT_TRANSPORT, AGENT_WAREHOUSE]
    )

    await Database.create_negotiation_async({
        "negotiation_id": neg_id,
        "crop": "Tomato",
        "quantity": 1200.0,
        "final_price": 28.0,
        "status": "DEAL",
        "farmer_name": "Nashik Tomato Growers",
        "location": "Pimpalgaon, Nashik"
    })

    wf_deal = await buyer_workflow_service.record_farmer_deal_outcome(
        requirement_id=req_id,
        deal_id=neg_id,
        outcome_status=DEAL_STATUS_SUCCESS
    )

    # Dependency check: Transport must be eligible, Warehouse must be BLOCKED
    actions = buyer_workflow_service.get_valid_next_actions(wf_deal)
    assert any(a["action"] == AGENT_TRANSPORT for a in actions)
    assert not any(a["action"] == AGENT_WAREHOUSE for a in actions)

    # Execute Transport
    wf_t = await buyer_workflow_service.step_workflow(requirement_id=req_id, action_override=AGENT_TRANSPORT)
    assert AGENT_TRANSPORT in wf_t["completed_agents"]

    # Now Warehouse must be ELIGIBLE
    actions_after_t = buyer_workflow_service.get_valid_next_actions(wf_t)
    assert any(a["action"] == AGENT_WAREHOUSE for a in actions_after_t)

    # Execute Warehouse
    wf_w = await buyer_workflow_service.step_workflow(requirement_id=req_id, action_override=AGENT_WAREHOUSE)
    assert AGENT_WAREHOUSE in wf_w["completed_agents"]

    # Both completed!
    assert AGENT_TRANSPORT in wf_w["completed_agents"]
    assert AGENT_WAREHOUSE in wf_w["completed_agents"]


@pytest.mark.asyncio
async def test_06_buyer_selects_transport_and_processor():
    """
    TEST 6: Buyer selects Transport + Processor.
    Expected: Both actual agents execute according to dependency rules:
    Farmer -> Transport -> Processor.
    """
    req_id = "req_test_06"
    neg_id = "neg_test_06"

    await buyer_workflow_service.initialize_workflow(
        requirement_id=req_id,
        buyer_id="buyer_06",
        crop="Cotton",
        quantity=3000.0,
        pickup_location="Amravati",
        delivery_location="Amravati",
        selected_agents=[AGENT_FARMER, AGENT_TRANSPORT, AGENT_PROCESSOR]
    )

    await Database.create_negotiation_async({
        "negotiation_id": neg_id,
        "crop": "Cotton",
        "quantity": 3000.0,
        "final_price": 72.0,
        "status": "DEAL",
        "farmer_name": "Vidarbha Cotton FPO",
        "location": "Amravati APMC"
    })

    await buyer_workflow_service.record_farmer_deal_outcome(
        requirement_id=req_id,
        deal_id=neg_id,
        outcome_status=DEAL_STATUS_SUCCESS
    )

    # Step Transport
    wf_t = await buyer_workflow_service.step_workflow(requirement_id=req_id, action_override=AGENT_TRANSPORT)
    assert AGENT_TRANSPORT in wf_t["completed_agents"]

    # Step Processor
    wf_p = await buyer_workflow_service.step_workflow(requirement_id=req_id, action_override=AGENT_PROCESSOR)
    assert AGENT_PROCESSOR in wf_p["completed_agents"]
    assert wf_p["agent_outcomes"][AGENT_PROCESSOR]["result"]["output_product"] is not None


@pytest.mark.asyncio
async def test_07_buyer_selects_warehouse_and_processor():
    """
    TEST 7: Buyer selects Warehouse + Processor.
    Expected: Both actual agents execute according to dependency rules:
    Farmer -> Warehouse -> Processor.
    """
    req_id = "req_test_07"
    neg_id = "neg_test_07"

    await buyer_workflow_service.initialize_workflow(
        requirement_id=req_id,
        buyer_id="buyer_07",
        crop="Jowar",
        quantity=2000.0,
        delivery_location="Solapur",
        selected_agents=[AGENT_FARMER, AGENT_WAREHOUSE, AGENT_PROCESSOR]
    )

    await Database.create_negotiation_async({
        "negotiation_id": neg_id,
        "crop": "Jowar",
        "quantity": 2000.0,
        "final_price": 34.0,
        "status": "DEAL",
        "farmer_name": "Solapur Millets FPO",
        "location": "Solapur APMC"
    })

    await buyer_workflow_service.record_farmer_deal_outcome(
        requirement_id=req_id,
        deal_id=neg_id,
        outcome_status=DEAL_STATUS_SUCCESS
    )

    # Warehouse is eligible first
    wf_w = await buyer_workflow_service.step_workflow(requirement_id=req_id, action_override=AGENT_WAREHOUSE)
    assert AGENT_WAREHOUSE in wf_w["completed_agents"]

    # Processor is eligible next
    wf_p = await buyer_workflow_service.step_workflow(requirement_id=req_id, action_override=AGENT_PROCESSOR)
    assert AGENT_PROCESSOR in wf_p["completed_agents"]


@pytest.mark.asyncio
async def test_08_buyer_selects_transport_warehouse_processor_all_three():
    """
    TEST 8: Buyer selects Transport + Warehouse + Processor.
    Expected: All implemented agents execute correctly according to dependency rules:
    Farmer -> Transport -> Warehouse -> Processor -> Final Plan.
    """
    req_id = "req_test_08"
    neg_id = "neg_test_08"

    await buyer_workflow_service.initialize_workflow(
        requirement_id=req_id,
        buyer_id="buyer_08",
        crop="Soybean",
        quantity=3500.0,
        pickup_location="Latur",
        delivery_location="Pune",
        selected_agents=[AGENT_FARMER, AGENT_TRANSPORT, AGENT_WAREHOUSE, AGENT_PROCESSOR]
    )

    await Database.create_negotiation_async({
        "negotiation_id": neg_id,
        "crop": "Soybean",
        "quantity": 3500.0,
        "final_price": 49.5,
        "status": "DEAL",
        "farmer_name": "Marathwada Agro Coop",
        "location": "Latur APMC"
    })

    await buyer_workflow_service.record_farmer_deal_outcome(
        requirement_id=req_id,
        deal_id=neg_id,
        outcome_status=DEAL_STATUS_SUCCESS
    )

    # Step Transport
    wf_1 = await buyer_workflow_service.step_workflow(requirement_id=req_id, action_override=AGENT_TRANSPORT)
    assert AGENT_TRANSPORT in wf_1["completed_agents"]

    # Step Warehouse
    wf_2 = await buyer_workflow_service.step_workflow(requirement_id=req_id, action_override=AGENT_WAREHOUSE)
    assert AGENT_WAREHOUSE in wf_2["completed_agents"]

    # Step Processor
    wf_3 = await buyer_workflow_service.step_workflow(requirement_id=req_id, action_override=AGENT_PROCESSOR)
    assert AGENT_PROCESSOR in wf_3["completed_agents"]

    # Finalize
    wf_final = await buyer_workflow_service.step_workflow(requirement_id=req_id, action_override="COMPLETE")
    assert wf_final["workflow_status"] == "COMPLETED"

    # Verify Final Plan
    plan = wf_final["final_plan"]
    assert plan is not None
    assert plan["farmer_procurement_cost"] == 3500.0 * 49.5
    assert plan["transport_cost"] > 0
    assert plan["warehouse_cost"] > 0
    assert plan["processor_cost"] > 0
    assert plan["total_procurement_cost"] > plan["farmer_procurement_cost"]
    assert plan["contract_signature"].startswith("0x")


@pytest.mark.asyncio
async def test_09_transport_failure_handling():
    """
    TEST 9: Transport fails (e.g. impossible quantity exceeding all vehicles).
    Expected: Transport = FAILED. No false success.
    """
    req_id = "req_test_09"
    neg_id = "neg_test_09"

    await buyer_workflow_service.initialize_workflow(
        requirement_id=req_id,
        buyer_id="buyer_09",
        crop="Soybean",
        quantity=999999.0,  # 1 million kg exceeds vehicle fleet
        selected_agents=[AGENT_FARMER, AGENT_TRANSPORT]
    )

    await Database.create_negotiation_async({
        "negotiation_id": neg_id,
        "crop": "Soybean",
        "quantity": 999999.0,
        "final_price": 48.0,
        "status": "DEAL",
        "farmer_name": "Mega Farm",
        "location": "Latur"
    })

    await buyer_workflow_service.record_farmer_deal_outcome(
        requirement_id=req_id,
        deal_id=neg_id,
        outcome_status=DEAL_STATUS_SUCCESS
    )

    wf_stepped = await buyer_workflow_service.step_workflow(requirement_id=req_id, action_override=AGENT_TRANSPORT)

    assert AGENT_TRANSPORT in wf_stepped["failed_agents"]
    assert AGENT_TRANSPORT not in wf_stepped["completed_agents"]
    assert wf_stepped["agent_outcomes"][AGENT_TRANSPORT]["status"] == "FAILED"


@pytest.mark.asyncio
async def test_10_warehouse_failure_handling():
    """
    TEST 10: Warehouse fails (e.g. requested capacity exceeds all available facilities).
    Expected: Warehouse = FAILED. Existing successful Transport remains recorded.
    """
    req_id = "req_test_10"
    neg_id = "neg_test_10"

    await buyer_workflow_service.initialize_workflow(
        requirement_id=req_id,
        buyer_id="buyer_10",
        crop="Onion",
        quantity=2000.0,
        selected_agents=[AGENT_FARMER, AGENT_TRANSPORT, AGENT_WAREHOUSE]
    )

    await Database.create_negotiation_async({
        "negotiation_id": neg_id,
        "crop": "Onion",
        "quantity": 2000.0,
        "final_price": 24.0,
        "status": "DEAL",
        "farmer_name": "Nashik FPO",
        "location": "Nashik"
    })

    await buyer_workflow_service.record_farmer_deal_outcome(
        requirement_id=req_id,
        deal_id=neg_id,
        outcome_status=DEAL_STATUS_SUCCESS
    )

    # 1. Transport succeeds
    wf_t = await buyer_workflow_service.step_workflow(requirement_id=req_id, action_override=AGENT_TRANSPORT)
    assert AGENT_TRANSPORT in wf_t["completed_agents"]

    # 2. Simulate warehouse capacity exhaustion
    wf_t["quantity"] = 500000000.0  # 500,000 MT exceeds all warehouse capacity
    await Database.upsert_buyer_workflow_async(wf_t)

    wf_w = await buyer_workflow_service.step_workflow(requirement_id=req_id, action_override=AGENT_WAREHOUSE)
    assert AGENT_WAREHOUSE in wf_w["failed_agents"]
    assert AGENT_WAREHOUSE not in wf_w["completed_agents"]
    # Existing Transport remains recorded!
    assert AGENT_TRANSPORT in wf_w["completed_agents"]


@pytest.mark.asyncio
async def test_11_processor_failure_handling():
    """
    TEST 11: Processor fails (e.g. moisture exceeds statutory ceiling).
    Expected: Processor = FAILED. No false success.
    """
    from backend.agents.processor_agent.workflow import run_processor_workflow

    # Direct execution test with bad moisture
    res = await run_processor_workflow({
        "crop": "Soybean",
        "quantity_kg": 2000.0,
        "moisture": 18.0  # 18% moisture exceeds 12% ceiling
    })

    assert res["status"] == "FAILED"
    assert res["decision"] == "REJECTED_QUALITY"
    assert "exceeds" in res["decision_reason"]


@pytest.mark.asyncio
async def test_12_farmer_deal_invalid_or_withdrawn():
    """
    TEST 12: Farmer deal is invalid/withdrawn.
    Expected: Downstream agent execution is strictly blocked.
    """
    req_id = "req_test_12"
    neg_id = "neg_test_12"

    wf = await buyer_workflow_service.initialize_workflow(
        requirement_id=req_id,
        buyer_id="buyer_12",
        crop="Soybean",
        quantity=1000.0,
        selected_agents=[AGENT_FARMER, AGENT_TRANSPORT]
    )

    # Deal is withdrawn
    await Database.create_negotiation_async({
        "negotiation_id": neg_id,
        "crop": "Soybean",
        "quantity": 1000.0,
        "status": "WITHDRAWN"
    })

    wf_withdrawn = await buyer_workflow_service.record_farmer_deal_outcome(
        requirement_id=req_id,
        deal_id=neg_id,
        outcome_status=DEAL_STATUS_WITHDRAWN
    )

    actions = buyer_workflow_service.get_valid_next_actions(wf_withdrawn)
    assert any(a["action"] == "STOP" for a in actions)
    assert not any(a["action"] == AGENT_TRANSPORT for a in actions)


@pytest.mark.asyncio
async def test_13_buyer_invokes_unselected_agent_directly():
    """
    TEST 13: Buyer tries to invoke an unselected agent directly.
    Expected: Backend rejects the operation with ValueError.
    """
    req_id = "req_test_13"
    neg_id = "neg_test_13"

    await buyer_workflow_service.initialize_workflow(
        requirement_id=req_id,
        buyer_id="buyer_13",
        crop="Soybean",
        quantity=1000.0,
        selected_agents=[AGENT_FARMER, AGENT_TRANSPORT]  # Warehouse NOT selected
    )

    await Database.create_negotiation_async({
        "negotiation_id": neg_id,
        "crop": "Soybean",
        "quantity": 1000.0,
        "final_price": 50.0,
        "status": "DEAL",
        "farmer_name": "Pune FPO",
        "location": "Pune"
    })

    await buyer_workflow_service.record_farmer_deal_outcome(
        requirement_id=req_id,
        deal_id=neg_id,
        outcome_status=DEAL_STATUS_SUCCESS
    )

    # Trying to step WAREHOUSE directly must be rejected
    with pytest.raises(ValueError) as excinfo:
        await buyer_workflow_service.step_workflow(requirement_id=req_id, action_override=AGENT_WAREHOUSE)

    assert "not valid right now" in str(excinfo.value)


@pytest.mark.asyncio
async def test_14_buyer_double_click_idempotency():
    """
    TEST 14: Buyer double-clicks agent execution.
    Expected: No duplicate uncontrolled execution; returns existing state cleanly.
    """
    req_id = "req_test_14"
    neg_id = "neg_test_14"

    await buyer_workflow_service.initialize_workflow(
        requirement_id=req_id,
        buyer_id="buyer_14",
        crop="Soybean",
        quantity=1000.0,
        selected_agents=[AGENT_FARMER, AGENT_TRANSPORT]
    )

    await Database.create_negotiation_async({
        "negotiation_id": neg_id,
        "crop": "Soybean",
        "quantity": 1000.0,
        "final_price": 50.0,
        "status": "DEAL",
        "farmer_name": "Latur FPO",
        "location": "Latur"
    })

    await buyer_workflow_service.record_farmer_deal_outcome(
        requirement_id=req_id,
        deal_id=neg_id,
        outcome_status=DEAL_STATUS_SUCCESS
    )

    # First click
    wf_1 = await buyer_workflow_service.step_workflow(requirement_id=req_id, action_override=AGENT_TRANSPORT)
    exec_id_1 = wf_1["agent_outcomes"][AGENT_TRANSPORT]["execution_id"]

    # Second click (double click)
    wf_2 = await buyer_workflow_service.step_workflow(requirement_id=req_id, action_override=AGENT_TRANSPORT)
    exec_id_2 = wf_2["agent_outcomes"][AGENT_TRANSPORT]["execution_id"]

    # Must be identical; no second uncontrolled execution created
    assert exec_id_1 == exec_id_2


@pytest.mark.asyncio
async def test_15_browser_refresh_persistence():
    """
    TEST 15: Browser refresh occurs during/after workflow execution.
    Expected: State is restored completely from backend persistence.
    """
    req_id = "req_test_15"
    neg_id = "neg_test_15"

    await buyer_workflow_service.initialize_workflow(
        requirement_id=req_id,
        buyer_id="buyer_15",
        crop="Soybean",
        quantity=2000.0,
        selected_agents=[AGENT_FARMER, AGENT_TRANSPORT]
    )

    await Database.create_negotiation_async({
        "negotiation_id": neg_id,
        "crop": "Soybean",
        "quantity": 2000.0,
        "final_price": 50.0,
        "status": "DEAL",
        "farmer_name": "Latur FPO",
        "location": "Latur"
    })

    await buyer_workflow_service.record_farmer_deal_outcome(
        requirement_id=req_id,
        deal_id=neg_id,
        outcome_status=DEAL_STATUS_SUCCESS
    )

    await buyer_workflow_service.step_workflow(requirement_id=req_id, action_override=AGENT_TRANSPORT)

    # Simulate fresh browser request querying GET /requirements/{id}/workflow
    restored = await Database.get_buyer_workflow_async(requirement_id=req_id)
    assert restored is not None
    assert AGENT_TRANSPORT in restored["completed_agents"]
    assert restored["agent_outcomes"][AGENT_TRANSPORT]["status"] == "COMPLETED"


@pytest.mark.asyncio
async def test_16_backend_restart_and_deal_revalidation():
    """
    TEST 16: Backend restarts during/after workflow.
    Expected: Persisted workflow state remains authoritative; revalidation checks deal integrity.
    """
    req_id = "req_test_16"
    neg_id = "neg_test_16"

    await buyer_workflow_service.initialize_workflow(
        requirement_id=req_id,
        buyer_id="buyer_16",
        crop="Cotton",
        quantity=1500.0,
        selected_agents=[AGENT_FARMER, AGENT_TRANSPORT]
    )

    await Database.create_negotiation_async({
        "negotiation_id": neg_id,
        "crop": "Cotton",
        "quantity": 1500.0,
        "final_price": 70.0,
        "status": "DEAL",
        "farmer_name": "Amravati FPO",
        "location": "Amravati"
    })

    await buyer_workflow_service.record_farmer_deal_outcome(
        requirement_id=req_id,
        deal_id=neg_id,
        outcome_status=DEAL_STATUS_SUCCESS
    )

    # Revalidation succeeds while deal is in DB
    state = await buyer_workflow_service.get_workflow_state(requirement_id=req_id)
    revalidated = await buyer_workflow_service.revalidate_deal_state(state)
    assert revalidated["farmer_deal"]["valid"] is True


@pytest.mark.asyncio
async def test_17_simultaneous_buyers_isolation():
    """
    TEST 17: Two different Buyers run procurement simultaneously.
    Expected: Their workflow state and agent contexts remain completely isolated.
    """
    req_a = "req_iso_A"
    neg_a = "neg_iso_A"
    req_b = "req_iso_B"
    neg_b = "neg_iso_B"

    # Buyer A: Soybean in Latur
    wf_a = await buyer_workflow_service.initialize_workflow(
        requirement_id=req_a,
        buyer_id="buyer_A",
        crop="Soybean",
        quantity=1000.0,
        pickup_location="Latur",
        selected_agents=[AGENT_FARMER, AGENT_TRANSPORT]
    )

    # Buyer B: Onion in Nashik
    wf_b = await buyer_workflow_service.initialize_workflow(
        requirement_id=req_b,
        buyer_id="buyer_B",
        crop="Onion",
        quantity=3000.0,
        pickup_location="Nashik",
        selected_agents=[AGENT_FARMER, AGENT_WAREHOUSE]
    )

    await Database.create_negotiation_async({
        "negotiation_id": neg_a,
        "crop": "Soybean",
        "quantity": 1000.0,
        "final_price": 49.0,
        "status": "DEAL",
        "farmer_name": "Latur FPO"
    })

    await Database.create_negotiation_async({
        "negotiation_id": neg_b,
        "crop": "Onion",
        "quantity": 3000.0,
        "final_price": 22.0,
        "status": "DEAL",
        "farmer_name": "Nashik FPO"
    })

    # Execute both in parallel
    await asyncio.gather(
        buyer_workflow_service.record_farmer_deal_outcome(req_a, neg_a, DEAL_STATUS_SUCCESS),
        buyer_workflow_service.record_farmer_deal_outcome(req_b, neg_b, DEAL_STATUS_SUCCESS)
    )

    await asyncio.gather(
        buyer_workflow_service.step_workflow(req_a, action_override=AGENT_TRANSPORT),
        buyer_workflow_service.step_workflow(req_b, action_override=AGENT_WAREHOUSE)
    )

    # Verify Buyer A
    state_a = await buyer_workflow_service.get_workflow_state(requirement_id=req_a)
    assert state_a["crop"] == "Soybean"
    assert AGENT_TRANSPORT in state_a["completed_agents"]
    assert AGENT_WAREHOUSE not in state_a["completed_agents"]

    # Verify Buyer B
    state_b = await buyer_workflow_service.get_workflow_state(requirement_id=req_b)
    assert state_b["crop"] == "Onion"
    assert AGENT_WAREHOUSE in state_b["completed_agents"]
    assert AGENT_TRANSPORT not in state_b["completed_agents"]


@pytest.mark.asyncio
async def test_18_malformed_downstream_resilience():
    """
    TEST 18: Downstream agent error or exception handling.
    Expected: Orchestrator captures error gracefully in AgentOutcome without crashing.
    """
    req_id = "req_test_18"
    neg_id = "neg_test_18"

    await buyer_workflow_service.initialize_workflow(
        requirement_id=req_id,
        buyer_id="buyer_18",
        crop="Soybean",
        quantity=1000.0,
        selected_agents=[AGENT_FARMER, AGENT_PROCESSOR]
    )

    await Database.create_negotiation_async({
        "negotiation_id": neg_id,
        "crop": "Soybean",
        "quantity": 1000.0,
        "final_price": 50.0,
        "status": "DEAL",
        "farmer_name": "Pune FPO"
    })

    await buyer_workflow_service.record_farmer_deal_outcome(
        requirement_id=req_id,
        deal_id=neg_id,
        outcome_status=DEAL_STATUS_SUCCESS
    )

    # Deliberately pass unsupported crop to processor
    state = await buyer_workflow_service.get_workflow_state(requirement_id=req_id)
    state["crop"] = "UnknownUnsupportedExoticFruit"
    await Database.upsert_buyer_workflow_async(state)

    wf_stepped = await buyer_workflow_service.step_workflow(requirement_id=req_id, action_override=AGENT_PROCESSOR)

    assert AGENT_PROCESSOR in wf_stepped["failed_agents"]
    assert wf_stepped["agent_outcomes"][AGENT_PROCESSOR]["status"] == "FAILED"
    assert wf_stepped["agent_outcomes"][AGENT_PROCESSOR]["retryable"] is True
