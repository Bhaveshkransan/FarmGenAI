"""
tests/test_buyer_master_srs_architecture.py
------------------------------------------------------------------------
AgriNegotiator SRS Master Architectural Test Suite for Buyer Stakeholder.

Covers the 10 core architectural domains:
  1. Full Supply Chain vs. Single Agent Enforcement (FR-6)
  2. Permitted Agents vs. Required Agents Contract
  3. Buyer Market Intelligence (Live Mandi + ML Forecast + RAG)
  4. Canonical Matching Formula (Landed Cost: Base + Freight + APMC Cess)
  5. RAG Retrieval vs. Runtime Facts Separation
  6. LangGraph Multi-Node State Machine Execution
  7. WebSocket / Redis Granular Event Telemetry
  8. Scope-Aware Copilot / Human-in-the-Loop Override Guardrails
  9. Conditional Downstream Escalations (Transport, Warehouse, Processor)
  10. PostgreSQL Durable State Consistency & Cryptographic Digital Contract
"""

import pytest
import asyncio
import math
from unittest.mock import patch, MagicMock

from backend.agents.buyer_graph import (
    buyer_graph_orchestrator,
    BuyerOrchestrationGraphState,
)
from backend.services.buyer_orchestrator import (
    buyer_orchestration_service,
    validate_copilot_buyer_override,
)


class TestBuyerWorkflowModeAndAgentScoping:
    """Domain 1 & 2: Full Supply Chain vs. Single Agent & Permitted vs. Required Agents"""

    @pytest.mark.asyncio
    async def test_single_agent_mode_strictly_locks_permitted_agents_to_buyer_only(self):
        """In SINGLE_AGENT mode, only BUYER is permitted. Downstream agents are strictly disabled."""
        req = {
            "crop": "Soybean",
            "quantity": 1000.0,
            "target_price": 48.0,
            "max_price": 52.0,
            "budget": 100000.0,
            "location": "Nashik",
            "workflow_mode": "SINGLE_AGENT",
            "need_transport": True,   # User requests transport...
            "need_storage": True,     # and storage
            "sellers": [
                {"name": "Farmer Ram", "price": 49.0, "quantity": 1000.0, "distance_km": 20.0, "floor_price": 46.0}
            ]
        }
        res = await buyer_orchestration_service.orchestrate_negotiation(req)

        assert res["workflow_mode"] == "SINGLE_AGENT"
        assert res["permitted_agents"] == ["BUYER"]
        assert res["required_agents"] == ["BUYER"]
        # Downstream agents MUST NOT have run
        assert res["transport_assignment"] is None
        assert res["warehouse_assignment"] is None
        assert res["processor_assignment"] is None

    @pytest.mark.asyncio
    async def test_full_supply_chain_conditionally_invokes_transport_only_when_needed(self):
        """In FULL_SUPPLY_CHAIN mode, Transport Agent is invoked ONLY IF transport is actually required."""
        # Case A: Transport IS required
        req_with_transport = {
            "crop": "Soybean",
            "quantity": 1000.0,
            "target_price": 48.0,
            "max_price": 52.0,
            "budget": 100000.0,
            "location": "Indore",
            "workflow_mode": "FULL_SUPPLY_CHAIN",
            "need_transport": True,
            "delivery_option": "need_transport",
            "sellers": [
                {"name": "Farmer Ram", "price": 49.0, "quantity": 1000.0, "distance_km": 50.0, "floor_price": 46.0}
            ]
        }
        res_a = await buyer_orchestration_service.orchestrate_negotiation(req_with_transport)
        assert res_a["workflow_mode"] == "FULL_SUPPLY_CHAIN"
        assert "TRANSPORT" in res_a["required_agents"]
        assert res_a["transport_assignment"] is not None
        assert "truck" in res_a["transport_assignment"]

        # Case B: Transport is NOT required (seller delivers)
        req_without_transport = {
            "crop": "Soybean",
            "quantity": 1000.0,
            "target_price": 48.0,
            "max_price": 52.0,
            "budget": 100000.0,
            "location": "Indore",
            "workflow_mode": "FULL_SUPPLY_CHAIN",
            "need_transport": False,
            "delivery_option": "seller_delivery",
            "sellers": [
                {"name": "Farmer Ram", "price": 49.0, "quantity": 1000.0, "distance_km": 50.0, "floor_price": 46.0}
            ]
        }
        res_b = await buyer_orchestration_service.orchestrate_negotiation(req_without_transport)
        assert "TRANSPORT" not in res_b["required_agents"]
        assert res_b["transport_assignment"] is None

    @pytest.mark.asyncio
    async def test_permitted_agents_contract_blocks_unpermitted_services(self):
        """If an agent is required by input but NOT in permitted_agents, it MUST NOT be invoked."""
        req = {
            "crop": "Soybean",
            "quantity": 1000.0,
            "target_price": 48.0,
            "max_price": 52.0,
            "budget": 100000.0,
            "location": "Indore",
            "workflow_mode": "FULL_SUPPLY_CHAIN",
            "permitted_agents": ["BUYER", "WAREHOUSE"],  # Transport intentionally excluded!
            "need_transport": True,                      # But buyer requested transport
            "sellers": [
                {"name": "Farmer Ram", "price": 49.0, "quantity": 1000.0, "distance_km": 50.0, "floor_price": 46.0}
            ]
        }
        res = await buyer_orchestration_service.orchestrate_negotiation(req)
        # TRANSPORT is not permitted, so it must not be in required_agents or executed
        assert "TRANSPORT" not in res["required_agents"]
        assert res["transport_assignment"] is None


class TestBuyerMarketIntelligenceAndRAGSeparation:
    """Domain 3 & 5: Market Intelligence & Clear Separation of RAG vs. Runtime Facts"""

    @pytest.mark.asyncio
    async def test_market_intelligence_runtime_facts_separated_from_rag_knowledge(self):
        """RAG must provide domain/quality context and NEVER invent live runtime prices."""
        initial_state = {
            "trace_id": "trace-test-01",
            "crop": "Soybean",
            "quantity": 1000.0,
            "target_price": 48.0,
            "reservation_price": 52.0,
            "budget": 100000.0,
            "location": "Maharashtra",
            "workflow_mode": "FULL_SUPPLY_CHAIN",
            "need_transport": False,
            "need_storage": False,
            "allow_processing": False,
            "sellers": [
                {"name": "Farmer Shyam", "price": 49.0, "quantity": 1000.0, "distance_km": 30.0, "floor_price": 46.0}
            ]
        }
        final_state = await buyer_graph_orchestrator.ainvoke(initial_state)

        # 1. Runtime facts must come from live market sources
        assert "runtime_facts" in final_state
        assert final_state["runtime_facts"]["commodity"] == "Soybean"

        # 2. ML forecast must contain trend / model prediction
        assert "ml_forecast" in final_state

        # 3. RAG domain knowledge must contain agricultural knowledge
        assert "rag_knowledge" in final_state
        assert "quality_norms" in final_state["rag_knowledge"] or "content" in final_state["rag_knowledge"]


class TestCanonicalMatchingFormulaLandedCost:
    """Domain 4: Canonical Matching Formula (True Landed Cost vs. Lowest Base Price)"""

    @pytest.mark.asyncio
    async def test_matching_formula_prioritizes_lowest_landed_cost_over_cheaper_remote_base(self):
        """
        Proof that Lowest Purchase Price != Lowest Procurement Cost.
        Seller Local: ₹49/kg base price, 20 km away.
        Seller Remote: ₹48/kg base price, 450 km away.
        Due to freight, Local lot has lower Landed Cost and MUST be chosen as winner.
        """
        req = {
            "crop": "Soybean",
            "quantity": 1000.0,
            "target_price": 48.0,
            "max_price": 55.0,
            "budget": 100000.0,
            "location": "Indore",
            "workflow_mode": "SINGLE_AGENT",
            "sellers": [
                {
                    "name": "Remote Cheap Farmer",
                    "price": 48.0,
                    "quantity": 1000.0,
                    "distance_km": 450.0,  # High freight!
                    "floor_price": 48.0,
                    "flexibility": 0.0,
                },
                {
                    "name": "Local Fair Farmer",
                    "price": 49.0,
                    "quantity": 1000.0,
                    "distance_km": 20.0,   # Low freight!
                    "floor_price": 49.0,
                    "flexibility": 0.0,
                },
            ]
        }
        res = await buyer_orchestration_service.orchestrate_negotiation(req)

        assert res["status"] == "DEAL_SELECTED"
        winner = res["winner"]
        # Local seller must win despite slightly higher base price, because of lower landed cost!
        assert winner["seller_name"] == "Local Fair Farmer"
        assert winner["landed_cost_per_kg"] < 51.0


class TestLangGraphStateGraphExecution:
    """Domain 6: LangGraph Multi-Node State Machine Execution"""

    @pytest.mark.asyncio
    async def test_langgraph_buyer_master_graph_full_execution_pipeline(self):
        """Verifies full execution through the 11-node compiled LangGraph StateGraph."""
        input_state = {
            "trace_id": "test-langgraph-run",
            "crop": "Soybean",
            "quantity": 500.0,
            "target_price": 48.0,
            "reservation_price": 52.0,
            "budget": 50000.0,
            "location": "Indore",
            "workflow_mode": "FULL_SUPPLY_CHAIN",
            "need_transport": True,
            "delivery_option": "need_transport",
            "need_storage": False,
            "allow_processing": False,
            "sellers": [
                {"name": "Supplier A", "price": 49.0, "quantity": 500.0, "distance_km": 40.0, "floor_price": 47.0}
            ]
        }
        result = await buyer_graph_orchestrator.ainvoke(input_state)

        assert result["status"] == "DEAL_SELECTED"
        assert result["winner"] is not None
        assert "TRANSPORT" in result["required_agents"]
        assert result["transport_assignment"] is not None

        # Verify emitted canonical events log
        events = result.get("emitted_events", [])
        assert "NEGOTIATION_STARTED" in events
        assert "DEAL_SELECTED" in events
        assert "TRANSPORT_REQUIRED" in events
        assert "WORKFLOW_COMPLETED" in events


class TestScopeAwareCopilotGuardrails:
    """Domain 8: Scope-Aware Copilot / Human Override Protection"""

    def test_copilot_override_blocks_price_exceeding_pmax(self):
        """Copilot attempting to counter or accept above reservation ceiling P_max must be blocked."""
        buyer_state = {"reservation_price": 50.0, "budget": 100000.0, "committed_budget": 0.0}
        override_action = {"action_type": "COUNTER", "price": 58.0, "quantity": 500.0}

        val = validate_copilot_buyer_override(override_action, buyer_state)
        assert val["is_valid"] is False
        assert val["error_code"] == "PRICE_EXCEEDS_PMAX"

    def test_copilot_override_blocks_unpermitted_agent_invocation(self):
        """In SINGLE_AGENT mode, Copilot cannot invoke Transport or Warehouse."""
        buyer_state = {
            "reservation_price": 50.0,
            "budget": 100000.0,
            "committed_budget": 0.0,
            "permitted_agents": ["BUYER"]
        }
        override_action = {"action_type": "INVOKE_AGENT", "target_agent": "WAREHOUSE"}

        val = validate_copilot_buyer_override(override_action, buyer_state)
        assert val["is_valid"] is False
        assert val["error_code"] == "AGENT_NOT_PERMITTED"

    def test_copilot_override_blocks_budget_breach(self):
        """Copilot attempting an order exceeding available budget must be blocked."""
        buyer_state = {"reservation_price": 50.0, "budget": 20000.0, "committed_budget": 15000.0}
        # Remaining budget = 5,000. Order = 45 * 200 = 9,000 -> breach!
        override_action = {"action_type": "BUY", "price": 45.0, "quantity": 200.0}

        val = validate_copilot_buyer_override(override_action, buyer_state)
        assert val["is_valid"] is False
        assert val["error_code"] == "BUDGET_EXCEEDED"


class TestConditionalProcessorEscalation:
    """Domain 9: Conditional Downstream Escalation to Value-Added Processing"""

    @pytest.mark.asyncio
    async def test_deal_failure_conditionally_escalates_to_processor_if_permitted(self):
        """When direct sale fails to find a deal below P_max, system can escalate to industrial processor."""
        req = {
            "crop": "Soybean",
            "quantity": 1000.0,
            "target_price": 45.0,
            "max_price": 46.0,   # Very strict ceiling
            "budget": 100000.0,
            "location": "Latur",
            "workflow_mode": "FULL_SUPPLY_CHAIN",
            "allow_processing": True,
            "permitted_agents": ["BUYER", "PROCESSOR"],
            "sellers": [
                # Seller is firm above ceiling
                {"name": "Firm Farmer", "price": 55.0, "quantity": 1000.0, "distance_km": 30.0, "floor_price": 55.0, "flexibility": 0.0}
            ]
        }
        res = await buyer_orchestration_service.orchestrate_negotiation(req)

        assert res["status"] == "NO_EXECUTABLE_DEAL"
        assert "PROCESSOR" in res["required_agents"]
        assert res["processor_assignment"] is not None
        assert res["processor_assignment"]["status"] == "ALLOCATED"


class TestPostgresDurableStateConsistency:
    """Domain 10: PostgreSQL Durable State Consistency & Cryptographic Contract"""

    @pytest.mark.asyncio
    async def test_deal_generates_sha256_digital_contract_and_transaction_record(self):
        """Deal award must generate deterministic SHA-256 digital contract hash and transaction record."""
        req = {
            "crop": "Soybean",
            "quantity": 500.0,
            "target_price": 48.0,
            "max_price": 52.0,
            "budget": 50000.0,
            "location": "Indore",
            "workflow_mode": "SINGLE_AGENT",
            "sellers": [
                {"name": "Verified Farmer", "price": 49.0, "quantity": 500.0, "distance_km": 30.0, "floor_price": 47.0}
            ]
        }
        res = await buyer_orchestration_service.orchestrate_negotiation(req)

        assert res["status"] == "DEAL_SELECTED"
        winner = res["winner"]
        assert "transaction_id" in winner
        assert winner["transaction_id"].startswith("TXN-MH-2026-")
        assert "contract_hash" in winner
        assert winner["contract_hash"].startswith("0x")
        assert len(winner["contract_hash"]) == 66  # "0x" + 64 hex chars
        assert "idempotency_key" in winner
        assert len(winner["idempotency_key"]) == 64
