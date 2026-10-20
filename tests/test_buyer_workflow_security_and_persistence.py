"""
tests/test_buyer_workflow_security_and_persistence.py

Regression Test Suite for:
1. API Ownership & Authorization on all Buyer workflow endpoints:
   - GET /{id}/workflow
   - POST /{id}/workflow/step
   - POST /{id}/workflow/reevaluate
   - POST /{id}/workflow/agents/select
   - POST /{id}/workflow/execute
   - GET /{id}/workflow/status
   - GET /{id}/workflow/agents/{agent}
   - POST /{id}/orchestrate

2. final_plan durable database persistence & cold-restart recovery:
   - Persistence of final_plan to PostgreSQL / database via DBBuyerWorkflowState
   - Recovery of final_plan after in-memory cache wipe (cold restart simulation)
   - Status endpoint verification ensuring frontend can reconstruct finalized state
   - SHA-256 tamper-evident integrity digest preservation
"""

import pytest
import asyncio
from fastapi.testclient import TestClient

from backend.main import app
from database.db import Database
from backend.core.security import create_access_token
from backend.services.buyer_workflow_service import (
    buyer_workflow_service,
    AGENT_FARMER,
    AGENT_TRANSPORT,
    AGENT_WAREHOUSE,
    AGENT_PROCESSOR,
    DEAL_STATUS_SUCCESS
)

client = TestClient(app)


def get_auth_headers(user_id: str, role: str = "buyer") -> dict:
    """Generate valid JWT Authorization header for a user."""
    token = create_access_token(data={"sub": user_id, "role": role})
    return {"Authorization": f"Bearer {token}"}


@pytest.fixture(autouse=True)
def reset_database_before_test():
    """Reset database and memory caches before each test."""
    asyncio.run(Database.reset())
    Database.buyer_workflows.clear()
    yield


# ==============================================================================
# PART 1: API OWNERSHIP & AUTHORIZATION TESTS
# ==============================================================================

def test_01_unauthenticated_request_rejected():
    """Unauthenticated calls without token must be rejected with 401 or 403."""
    req_id = "req_unauth_01"

    endpoints = [
        ("GET", f"/api/v1/requirements/{req_id}/workflow", None),
        ("POST", f"/api/v1/requirements/{req_id}/workflow/step", {"action": "TRANSPORT"}),
        ("POST", f"/api/v1/requirements/{req_id}/workflow/reevaluate", None),
        ("POST", f"/api/v1/requirements/{req_id}/workflow/agents/select", {"selected_agents": ["TRANSPORT"]}),
        ("POST", f"/api/v1/requirements/{req_id}/workflow/execute", None),
        ("GET", f"/api/v1/requirements/{req_id}/workflow/status", None),
        ("GET", f"/api/v1/requirements/{req_id}/workflow/agents/transport", None),
        ("POST", f"/api/v1/requirements/{req_id}/orchestrate", None),
    ]

    for method, path, body in endpoints:
        if method == "GET":
            res = client.get(path)
        else:
            res = client.post(path, json=body or {})
        assert res.status_code in (401, 403), f"Endpoint {method} {path} allowed unauthenticated access! Status: {res.status_code}"


def test_02_nonexistent_requirement_returns_404():
    """Authenticated request for non-existent requirement returns 404."""
    headers = get_auth_headers("buyer_legit", "buyer")
    req_id = "req_nonexistent_999"

    res = client.get(f"/api/v1/requirements/{req_id}/workflow", headers=headers)
    assert res.status_code == 404
    assert "not found" in res.json()["detail"].lower()

    res_step = client.post(f"/api/v1/requirements/{req_id}/workflow/step", json={}, headers=headers)
    assert res_step.status_code == 404

    res_status = client.get(f"/api/v1/requirements/{req_id}/workflow/status", headers=headers)
    assert res_status.status_code == 404


def test_03_cross_buyer_workflow_access_rejected_403():
    """Buyer A must NOT be able to read Buyer B's workflow state."""
    buyer_b_headers = get_auth_headers("buyer_B", "buyer")
    buyer_a_headers = get_auth_headers("buyer_A", "buyer")

    # Buyer B creates a requirement
    create_payload = {
        "crop": "Soybean",
        "quantity": 1000.0,
        "target_price": 48.0,
        "max_price": 52.0,
        "location": "Pune",
        "budget": 52000.0,
        "quality_grade": "Grade A"
    }
    create_res = client.post("/api/v1/requirements", json=create_payload, headers=buyer_b_headers)
    assert create_res.status_code == 200
    req_id = create_res.json()["requirement_id"]

    # Initialize workflow for Buyer B
    init_res = client.get(f"/api/v1/requirements/{req_id}/workflow", headers=buyer_b_headers)
    assert init_res.status_code == 200
    assert init_res.json()["success"] is True

    # Buyer A attempts to read Buyer B's workflow
    res_a = client.get(f"/api/v1/requirements/{req_id}/workflow", headers=buyer_a_headers)
    assert res_a.status_code == 403
    assert "do not own" in res_a.json()["detail"].lower()


def test_04_cross_buyer_agent_selection_rejected_403():
    """Buyer A must NOT be able to select downstream agents for Buyer B."""
    buyer_b_headers = get_auth_headers("buyer_B", "buyer")
    buyer_a_headers = get_auth_headers("buyer_A", "buyer")

    create_payload = {
        "crop": "Jowar",
        "quantity": 500.0,
        "target_price": 28.0,
        "max_price": 32.0,
        "location": "Nashik",
        "budget": 16000.0
    }
    create_res = client.post("/api/v1/requirements", json=create_payload, headers=buyer_b_headers)
    req_id = create_res.json()["requirement_id"]

    # Buyer A tries to mutate Buyer B's agents
    select_payload = {"selected_agents": ["TRANSPORT", "WAREHOUSE"]}
    res = client.post(f"/api/v1/requirements/{req_id}/workflow/agents/select", json=select_payload, headers=buyer_a_headers)
    assert res.status_code == 403
    assert "do not own" in res.json()["detail"].lower()


def test_05_cross_buyer_workflow_step_and_execute_rejected_403():
    """Buyer A must NOT be able to step or execute Buyer B's workflow."""
    buyer_b_headers = get_auth_headers("buyer_B", "buyer")
    buyer_a_headers = get_auth_headers("buyer_A", "buyer")

    create_payload = {
        "crop": "Cotton",
        "quantity": 800.0,
        "target_price": 70.0,
        "max_price": 75.0,
        "location": "Amravati",
        "budget": 60000.0
    }
    create_res = client.post("/api/v1/requirements", json=create_payload, headers=buyer_b_headers)
    req_id = create_res.json()["requirement_id"]

    # Buyer A attempts to step workflow
    step_res = client.post(f"/api/v1/requirements/{req_id}/workflow/step", json={"action": "TRANSPORT"}, headers=buyer_a_headers)
    assert step_res.status_code == 403
    assert "do not own" in step_res.json()["detail"].lower()

    # Buyer A attempts to execute full workflow
    exec_res = client.post(f"/api/v1/requirements/{req_id}/workflow/execute", headers=buyer_a_headers)
    assert exec_res.status_code == 403
    assert "do not own" in exec_res.json()["detail"].lower()


def test_06_cross_buyer_workflow_status_and_outcomes_rejected_403():
    """Buyer A must NOT be able to read Buyer B's status or agent outcome envelopes."""
    buyer_b_headers = get_auth_headers("buyer_B", "buyer")
    buyer_a_headers = get_auth_headers("buyer_A", "buyer")

    create_payload = {
        "crop": "Onion",
        "quantity": 1200.0,
        "target_price": 20.0,
        "max_price": 25.0,
        "location": "Nashik",
        "budget": 30000.0
    }
    create_res = client.post("/api/v1/requirements", json=create_payload, headers=buyer_b_headers)
    req_id = create_res.json()["requirement_id"]

    # Buyer A attempts to read status
    status_res = client.get(f"/api/v1/requirements/{req_id}/workflow/status", headers=buyer_a_headers)
    assert status_res.status_code == 403
    assert "do not own" in status_res.json()["detail"].lower()

    # Buyer A attempts to read agent outcome
    agent_res = client.get(f"/api/v1/requirements/{req_id}/workflow/agents/transport", headers=buyer_a_headers)
    assert agent_res.status_code == 403
    assert "do not own" in agent_res.json()["detail"].lower()


def test_07_cross_buyer_orchestrate_rejected_403():
    """Buyer A must NOT be able to trigger autonomous negotiation for Buyer B's requirement."""
    buyer_b_headers = get_auth_headers("buyer_B", "buyer")
    buyer_a_headers = get_auth_headers("buyer_A", "buyer")

    create_payload = {
        "crop": "Soybean",
        "quantity": 600.0,
        "target_price": 46.0,
        "max_price": 50.0,
        "location": "Latur",
        "budget": 30000.0
    }
    create_res = client.post("/api/v1/requirements", json=create_payload, headers=buyer_b_headers)
    req_id = create_res.json()["requirement_id"]

    res = client.post(f"/api/v1/requirements/{req_id}/orchestrate", headers=buyer_a_headers)
    assert res.status_code == 403
    assert "do not own" in res.json()["detail"].lower()


def test_08_admin_access_permitted():
    """Admin role must have oversight access to Buyer requirements and workflows."""
    buyer_b_headers = get_auth_headers("buyer_B", "buyer")
    admin_headers = get_auth_headers("admin_user", "admin")

    create_payload = {
        "crop": "Bajra",
        "quantity": 1000.0,
        "target_price": 20.0,
        "max_price": 24.0,
        "location": "Pune",
        "budget": 24000.0
    }
    create_res = client.post("/api/v1/requirements", json=create_payload, headers=buyer_b_headers)
    req_id = create_res.json()["requirement_id"]

    # Admin reads workflow
    admin_res = client.get(f"/api/v1/requirements/{req_id}/workflow", headers=admin_headers)
    assert admin_res.status_code == 200
    assert admin_res.json()["success"] is True


# ==============================================================================
# PART 2: FINAL_PLAN PERSISTENCE & COLD-RESTART RECOVERY TESTS
# ==============================================================================

@pytest.mark.asyncio
async def test_09_final_plan_persisted_and_restored_across_cold_restart():
    """
    FIX 2 Verification:
    1. Workflow runs to COMPLETE with Transport + Warehouse + Processor.
    2. final_plan is generated with total_procurement_cost & SHA-256 tamper-evident digest.
    3. Application memory / in-memory cache is wiped (cold restart simulation).
    4. Database.get_buyer_workflow_async loads state from durable DB.
    5. final_plan is still present and intact.
    6. REST status endpoint returns final_plan for frontend reconstruction.
    """
    req_id = "req_persist_restart_01"
    neg_id = "neg_persist_restart_01"
    buyer_id = "buyer_persist_test"
    headers = get_auth_headers(buyer_id, "buyer")

    # 1. Create requirement in Database
    req_payload = {
        "id": req_id,
        "requirement_id": req_id,
        "kind": "requirement",
        "user_id": buyer_id,
        "crop": "Soybean",
        "quantity": 1000.0,
        "target_price": 48.0,
        "max_price": 52.0,
        "budget": 52000.0,
        "location": "Pune APMC",
        "status": "ACTIVE"
    }
    await Database.upsert_buyer_async(req_payload)

    # 2. Initialize workflow with all 3 agents
    wf = await buyer_workflow_service.initialize_workflow(
        requirement_id=req_id,
        buyer_id=buyer_id,
        crop="Soybean",
        quantity=1000.0,
        quality="Grade A",
        pickup_location="Latur APMC",
        delivery_location="Pune APMC",
        selected_agents=[AGENT_FARMER, AGENT_TRANSPORT, AGENT_WAREHOUSE, AGENT_PROCESSOR]
    )
    assert wf["workflow_status"] == "FARMER_NEGOTIATING"
    assert wf["final_plan"] is None

    # 3. Create authoritative farmer deal in Database
    await Database.create_negotiation_async({
        "negotiation_id": neg_id,
        "crop": "Soybean",
        "quantity": 1000.0,
        "final_price": 50.0,
        "status": "DEAL",
        "farmer_name": "Balasaheb Patil",
        "location": "Latur APMC, Maharashtra",
        "contract_hash": "sha256_mock_farmer_deal"
    })

    # Record farmer deal outcome
    wf = await buyer_workflow_service.record_farmer_deal_outcome(
        requirement_id=req_id,
        deal_id=neg_id,
        outcome_status=DEAL_STATUS_SUCCESS
    )
    assert wf["farmer_deal"]["valid"] is True

    # 4. Step through Transport, Warehouse, Processor, and COMPLETE
    wf = await buyer_workflow_service.step_workflow(requirement_id=req_id, action_override=AGENT_TRANSPORT)
    assert AGENT_TRANSPORT in wf["completed_agents"]

    wf = await buyer_workflow_service.step_workflow(requirement_id=req_id, action_override=AGENT_WAREHOUSE)
    assert AGENT_WAREHOUSE in wf["completed_agents"]

    wf = await buyer_workflow_service.step_workflow(requirement_id=req_id, action_override=AGENT_PROCESSOR)
    assert AGENT_PROCESSOR in wf["completed_agents"]

    # Step COMPLETE to finalize procurement plan
    wf = await buyer_workflow_service.step_workflow(requirement_id=req_id, action_override="COMPLETE")
    assert wf["workflow_status"] == "COMPLETED"
    assert wf["final_plan"] is not None

    generated_plan = wf["final_plan"]
    assert generated_plan["crop"] == "Soybean"
    assert generated_plan["quantity_kg"] == 1000.0
    assert generated_plan["total_procurement_cost"] > 50000.0
    assert "contract_signature" in generated_plan
    assert generated_plan["contract_signature"].startswith("0x")
    original_signature = generated_plan["contract_signature"]
    original_cost = generated_plan["total_procurement_cost"]

    # 5. COLD RESTART SIMULATION:
    # Completely wipe the in-memory cache
    Database.buyer_workflows.clear()
    assert req_id not in Database.buyer_workflows
    assert wf["workflow_id"] not in Database.buyer_workflows

    # 6. Load workflow from PostgreSQL / SQLite durable repository
    restored = await Database.get_buyer_workflow_async(requirement_id=req_id)
    assert restored is not None, "Workflow state failed to restore from durable database!"
    assert restored["workflow_status"] == "COMPLETED"
    assert restored["final_plan"] is not None, "final_plan was lost after cold restart (in-memory wipe)!"
    assert restored["final_plan"]["contract_signature"] == original_signature
    assert restored["final_plan"]["total_procurement_cost"] == original_cost
    assert restored["final_plan"]["farmer_procurement_cost"] == 50000.0
    assert restored["final_plan"]["transport_cost"] > 0
    assert restored["final_plan"]["warehouse_cost"] > 0
    assert restored["final_plan"]["processor_cost"] > 0

    # 7. Verify REST status endpoint queries durable DB and provides final_plan for frontend
    status_res = client.get(f"/api/v1/requirements/{req_id}/workflow/status", headers=headers)
    assert status_res.status_code == 200
    status_data = status_res.json()
    assert status_data["success"] is True
    assert status_data["workflow_status"] == "COMPLETED"
    assert status_data["final_plan"] is not None
    assert status_data["final_plan"]["contract_signature"] == original_signature
    assert status_data["final_plan"]["total_procurement_cost"] == original_cost

    # Verify frontend-required fields are present
    plan = status_data["final_plan"]
    assert "total_procurement_cost" in plan
    assert "contract_signature" in plan
    assert "transport_plan" in plan
    assert "warehouse_plan" in plan
    assert "processor_plan" in plan
    assert "farmer_deal" in plan
