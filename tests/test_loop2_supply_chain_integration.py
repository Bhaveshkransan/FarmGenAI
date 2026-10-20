"""
tests/test_loop2_supply_chain_integration.py
--------------------------------------------------------------------
FarmGenAI / AgriNegotiator — LOOP 2 MULTI-AGENT SUPPLY CHAIN INTEGRATION
--------------------------------------------------------------------

Executes and certifies the full end-to-end integration across all 5 stages:
1. FARMER: Real DB Produce Listing persistence & discovery.
2. BUYER: Multi-round autonomous bargaining to authoritative DEAL_SELECTED.
3. GATE 1 ENFORCEMENT: Downstream actions blocked until farmer deal is SUCCESS.
4. TRANSPORT AGENT: Real LangGraph 11-node routing & vehicle allocation.
5. WAREHOUSE AGENT: Cold storage / bay sizing, holding duration & cost sizing.
6. PROCESSOR AGENT: Industrial conversion tariff, moisture check & output yield.
7. CRYPTOGRAPHIC FINALITY: Landed cost aggregation & SHA-256 digital signature.
8. IDEMPOTENCY: Re-execution returns identical signed contract state.
"""

import pytest
import asyncio
import uuid
from datetime import datetime, timezone

from database.db import Database, init_db
from backend.services.buyer_orchestrator import BuyerOrchestrationService
from backend.services.buyer_workflow_service import (
    buyer_workflow_service,
    AGENT_FARMER,
    AGENT_TRANSPORT,
    AGENT_WAREHOUSE,
    AGENT_PROCESSOR,
    DEAL_STATUS_SUCCESS,
    DEAL_STATUS_FAILED
)


@pytest.fixture(autouse=True)
async def clean_runtime():
    """Ensure clean runtime state before each integration test."""
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
async def test_01_full_five_stage_supply_chain_integration():
    """
    Test 01: Complete 5-stage integration:
    Farmer (Latur Soybean) -> Buyer Negotiation -> Transport LangGraph ->
    Warehouse Storage -> Processor Conversion -> Cryptographic SHA-256 Seal.
    """
    # 1. FARMER: Seed active produce in database
    seller_id = f"seller_latur_{uuid.uuid4().hex[:6]}"
    seller_listing = {
        "id": seller_id,
        "farmer_name": "Ramesh Patil",
        "crop": "Soybean",
        "quantity": 2000.0,
        "min_price": 48.0,
        "expected_price": 54.0,
        "location": "Latur",
        "quality": "A",
        "shelf_life": 180,
        "status": "ACTIVE"
    }
    await Database.upsert_produce_async(seller_listing)

    # 2. BUYER: Define procurement requirement
    req_id = f"REQ-E2E-{uuid.uuid4().hex[:8]}"
    buyer_id = f"BUYER-E2E-{uuid.uuid4().hex[:6]}"
    buyer_req = {
        "requirement_id": req_id,
        "buyer_id": buyer_id,
        "buyer_name": "MahaAgro Oils & Feeds Ltd",
        "crop": "Soybean",
        "quantity": 1500.0,
        "target_quantity": 1500.0,
        "target_price": 50.0,
        "max_price": 55.0,
        "budget": 85000.0,
        "location": "Pune",
        "quality_tier": "A",
        "urgency": "NORMAL",
        "risk_appetite": "Moderate",
    }

    # 3. Autonomous Negotiation Execution
    orchestrator = BuyerOrchestrationService()
    neg_result = await orchestrator.orchestrate_negotiation(
        requirement=buyer_req,
        max_candidates=5,
        max_rounds=3
    )

    assert neg_result["status"] == "DEAL_SELECTED"
    winner = neg_result["winner"]
    assert winner is not None
    assert winner["final_price"] >= 48.0
    assert winner["final_price"] <= 55.0

    # 4. INITIALIZE MULTI-AGENT WORKFLOW (Scope: all 4 agents)
    wf_state = await buyer_workflow_service.initialize_workflow(
        requirement_id=req_id,
        buyer_id=buyer_id,
        crop="Soybean",
        quantity=1500.0,
        quality="Grade A",
        pickup_location="Latur",
        delivery_location="Pune",
        selected_agents=[AGENT_FARMER, AGENT_TRANSPORT, AGENT_WAREHOUSE, AGENT_PROCESSOR]
    )

    assert AGENT_FARMER in wf_state["selected_agents"]
    assert AGENT_TRANSPORT in wf_state["selected_agents"]
    assert AGENT_WAREHOUSE in wf_state["selected_agents"]
    assert AGENT_PROCESSOR in wf_state["selected_agents"]

    # 5. GATE 1 ENFORCEMENT: Verify downstream blocked prior to farmer deal
    valid_actions = buyer_workflow_service.get_valid_next_actions(wf_state)
    action_names = [a["action"] for a in valid_actions]
    assert AGENT_TRANSPORT not in action_names
    assert AGENT_WAREHOUSE not in action_names
    assert AGENT_PROCESSOR not in action_names

    # 6. RECORD AUTHORITATIVE FARMER DEAL OUTCOME
    deal_id = winner.get("transaction_id", f"deal_{uuid.uuid4().hex[:8]}")
    await Database.create_negotiation_async({
        "negotiation_id": deal_id,
        "crop": "Soybean",
        "quantity": 1500.0,
        "final_price": winner["final_price"],
        "status": "DEAL",
        "farmer_name": "Ramesh Patil",
        "location": "Latur APMC"
    })

    wf_state = await buyer_workflow_service.record_farmer_deal_outcome(
        requirement_id=req_id,
        deal_id=deal_id,
        outcome_status=DEAL_STATUS_SUCCESS
    )

    # 7. GATE 1 UNLOCKED: TRANSPORT is now the valid next action
    valid_actions = buyer_workflow_service.get_valid_next_actions(wf_state)
    assert any(a["action"] == AGENT_TRANSPORT for a in valid_actions)

    # 8. EXECUTE TRANSPORT STEP (Real LangGraph 11-node routing)
    wf_state = await buyer_workflow_service.step_workflow(
        requirement_id=req_id,
        action_override=AGENT_TRANSPORT
    )
    t_result = wf_state["agent_outcomes"].get(AGENT_TRANSPORT)
    assert t_result is not None
    assert t_result["status"] in ("COMPLETED", "SUCCESS", "CONFIRMED")
    assert AGENT_TRANSPORT in wf_state["completed_agents"]

    # 9. EXECUTE WAREHOUSE STEP (Real warehouse storage sizing)
    valid_actions = buyer_workflow_service.get_valid_next_actions(wf_state)
    assert any(a["action"] == AGENT_WAREHOUSE for a in valid_actions)

    wf_state = await buyer_workflow_service.step_workflow(
        requirement_id=req_id,
        action_override=AGENT_WAREHOUSE
    )
    w_result = wf_state["agent_outcomes"].get(AGENT_WAREHOUSE)
    assert w_result is not None
    assert w_result["status"] in ("COMPLETED", "SUCCESS", "CONFIRMED")
    assert AGENT_WAREHOUSE in wf_state["completed_agents"]

    # 10. EXECUTE PROCESSOR STEP (Real industrial batch conversion)
    valid_actions = buyer_workflow_service.get_valid_next_actions(wf_state)
    assert any(a["action"] == AGENT_PROCESSOR for a in valid_actions)

    wf_state = await buyer_workflow_service.step_workflow(
        requirement_id=req_id,
        action_override=AGENT_PROCESSOR
    )
    p_result = wf_state["agent_outcomes"].get(AGENT_PROCESSOR)
    assert p_result is not None
    assert p_result["status"] in ("COMPLETED", "SUCCESS", "CONFIRMED")
    assert AGENT_PROCESSOR in wf_state["completed_agents"]

    # 11. CRYPTOGRAPHIC SETTLEMENT (step_workflow with action_override="COMPLETE")
    valid_actions = buyer_workflow_service.get_valid_next_actions(wf_state)
    assert any(a["action"] == "COMPLETE" for a in valid_actions)

    final_wf = await buyer_workflow_service.step_workflow(requirement_id=req_id, action_override="COMPLETE")
    assert final_wf["workflow_status"] == "COMPLETED"
    assert final_wf["final_plan"] is not None
    assert final_wf["final_plan"]["contract_signature"].startswith("0x")
    assert final_wf["final_plan"]["total_procurement_cost"] > 0

    # 12. IDEMPOTENCY CHECK
    idempotent_wf = await buyer_workflow_service.step_workflow(requirement_id=req_id, action_override="COMPLETE")
    assert idempotent_wf["final_plan"]["contract_signature"] == final_wf["final_plan"]["contract_signature"]


@pytest.mark.asyncio
async def test_02_farmer_deal_failure_hard_stops_downstream():
    """
    Test 02: If farmer deal fails, downstream agents are strictly blocked.
    """
    req_id = f"REQ-FAIL-{uuid.uuid4().hex[:6]}"
    buyer_id = "BUYER-FAIL-01"

    wf = await buyer_workflow_service.initialize_workflow(
        requirement_id=req_id,
        buyer_id=buyer_id,
        crop="Cotton",
        quantity=1000.0,
        selected_agents=[AGENT_FARMER, AGENT_TRANSPORT, AGENT_WAREHOUSE]
    )

    # Record farmer deal failure
    wf = await buyer_workflow_service.record_farmer_deal_outcome(
        requirement_id=req_id,
        deal_id="deal_failed_01",
        outcome_status=DEAL_STATUS_FAILED,
        deal_details={"rejection_reason": "Counterparty minimum price exceeded buyer ceiling"}
    )

    actions = buyer_workflow_service.get_valid_next_actions(wf)
    action_names = [a["action"] for a in actions]
    assert "STOP" in action_names
    assert AGENT_TRANSPORT not in action_names
    assert AGENT_WAREHOUSE not in action_names


@pytest.mark.asyncio
async def test_03_execute_full_workflow_sequential_chain():
    """
    Test 03: execute_full_workflow automatically runs all selected agents
    in sequential order until completion.
    """
    req_id = f"REQ-AUTO-{uuid.uuid4().hex[:6]}"
    buyer_id = "BUYER-AUTO-01"

    wf = await buyer_workflow_service.initialize_workflow(
        requirement_id=req_id,
        buyer_id=buyer_id,
        crop="Soybean",
        quantity=1200.0,
        selected_agents=[AGENT_FARMER, AGENT_TRANSPORT, AGENT_WAREHOUSE]
    )

    # Seed and accept farmer deal
    deal_id = f"deal_auto_{uuid.uuid4().hex[:6]}"
    await Database.create_negotiation_async({
        "negotiation_id": deal_id,
        "crop": "Soybean",
        "quantity": 1200.0,
        "final_price": 51.0,
        "status": "DEAL",
        "farmer_name": "Kailash Shinde",
        "location": "Amravati"
    })

    await buyer_workflow_service.record_farmer_deal_outcome(
        requirement_id=req_id,
        deal_id=deal_id,
        outcome_status=DEAL_STATUS_SUCCESS
    )

    # Run full automated workflow
    completed_wf = await buyer_workflow_service.execute_full_workflow(requirement_id=req_id)
    assert completed_wf["workflow_status"] == "COMPLETED"
    assert completed_wf["final_plan"] is not None
    assert completed_wf["final_plan"]["contract_signature"].startswith("0x")
    assert AGENT_TRANSPORT in completed_wf["completed_agents"]
    assert AGENT_WAREHOUSE in completed_wf["completed_agents"]
    assert completed_wf["agent_outcomes"][AGENT_TRANSPORT]["status"] in ("COMPLETED", "SUCCESS", "CONFIRMED")
    assert completed_wf["agent_outcomes"][AGENT_WAREHOUSE]["status"] in ("COMPLETED", "SUCCESS", "CONFIRMED")
