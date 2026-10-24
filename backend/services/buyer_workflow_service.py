"""
backend/services/buyer_workflow_service.py

Buyer Agent — Multi-Agent Procurement Orchestration Layer
---------------------------------------------------------
Authoritative Coordinator for FarmGenAI Buyer Multi-Agent Procurement:
1. Buyer Workflow Memory (Authoritative business state + conversation context + audit logs).
2. Requirement-scoped & Buyer-scoped isolation.
3. Authoritative Farmer Deal Gate (verify_farmer_deal_authoritative). No valid deal = No downstream execution.
4. Valid-Next-Agent Intelligence & Dependency Graph ("Why this agent?", "Why not this agent?").
5. Deterministic Buyer Policy (Clean interface for future RL insertion).
6. Controlled Handoff & Real Execution of TRANSPORT Agent (run_transport_workflow).
7. Controlled Handoff & Real Execution of WAREHOUSE Agent (run_warehouse_workflow).
8. Controlled Handoff & Real Execution of PROCESSOR Agent (run_processor_workflow).
9. Standardized AgentOutcome envelopes across all downstream executions.
10. Final Supply Chain Aggregation & Cryptographic SHA-256 Contract Signing.
11. Idempotency & Double-Click Protection.
12. Failure Handling & Non-Zero Error Propagation.
13. Durable persistence to PostgreSQL (DBBuyerWorkflowState).
"""

import uuid
import logging
import hashlib
from abc import ABC, abstractmethod
from copy import deepcopy
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional

from database.db import Database
from backend.agents.transport_agent.graph import run_transport_workflow
from backend.agents.warehouse_agent.workflow import run_warehouse_workflow
from backend.agents.processor_agent.workflow import run_processor_workflow
from backend.schemas.orchestration_contracts import AgentOutcome

logger = logging.getLogger("BuyerWorkflowService")

# Canonical Agent Identifiers
AGENT_FARMER = "FARMER"
AGENT_TRANSPORT = "TRANSPORT"
AGENT_WAREHOUSE = "WAREHOUSE"
AGENT_PROCESSOR = "PROCESSOR"
SUPPORTED_AGENTS = {AGENT_FARMER, AGENT_TRANSPORT, AGENT_WAREHOUSE, AGENT_PROCESSOR}

# Authoritative Deal Statuses
DEAL_STATUS_SUCCESS = "SUCCESS"
DEAL_STATUS_FAILED = "FAILED"
DEAL_STATUS_TIMEOUT = "TIMEOUT"
DEAL_STATUS_WITHDRAWN = "WITHDRAWN"
DEAL_STATUS_EXPIRED = "EXPIRED"
DEAL_STATUS_PENDING = "PENDING"


# ─────────────────────────────────────────────────────────────────────────────
# 1. POLICY INTERFACE (Deterministic now, RL-Ready for Phase 4/5)
# ─────────────────────────────────────────────────────────────────────────────

class BuyerPolicy(ABC):
    """
    Abstract interface for Buyer orchestration action selection.
    In Phase 1, DeterministicBuyerPolicy implements rule-based selection.
    In Phase 4/5, RLBuyerPolicy will implement learned policy selection
    using the exact same contract without changing orchestration mechanics.
    """
    @abstractmethod
    def select_action(
        self,
        state: Dict[str, Any],
        valid_actions: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        """Given workflow state and valid actions, select the next action to execute."""
        pass


class DeterministicBuyerPolicy(BuyerPolicy):
    """
    Deterministic Policy.
    Picks the next valid action based on strict supply-chain dependencies:
    1. If workflow is ready to complete -> COMPLETE
    2. If farmer deal failed -> STOP
    3. If TRANSPORT is eligible -> TRANSPORT
    4. If WAREHOUSE is eligible -> WAREHOUSE
    5. If PROCESSOR is eligible -> PROCESSOR
    6. If farmer negotiation active -> WAIT_FARMER
    """
    def select_action(
        self,
        state: Dict[str, Any],
        valid_actions: List[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        if not valid_actions:
            return None

        action_map = {a["action"]: a for a in valid_actions}

        # Deterministic priority hierarchy
        if "COMPLETE" in action_map:
            return action_map["COMPLETE"]
        if "STOP" in action_map:
            return action_map["STOP"]
        if AGENT_TRANSPORT in action_map:
            return action_map[AGENT_TRANSPORT]
        if AGENT_WAREHOUSE in action_map:
            return action_map[AGENT_WAREHOUSE]
        if AGENT_PROCESSOR in action_map:
            return action_map[AGENT_PROCESSOR]
        if "WAIT_FARMER" in action_map:
            return action_map["WAIT_FARMER"]
        if "FARMER_RETRY" in action_map:
            return action_map["FARMER_RETRY"]

        return valid_actions[0]


# ─────────────────────────────────────────────────────────────────────────────
# 2. BUYER WORKFLOW ORCHESTRATION SERVICE
# ─────────────────────────────────────────────────────────────────────────────

class BuyerWorkflowService:
    def __init__(self, policy: Optional[BuyerPolicy] = None):
        self.policy: BuyerPolicy = policy or DeterministicBuyerPolicy()

    # ── State Creation & Initialization ─────────────────────────────────────
    async def initialize_workflow(
        self,
        requirement_id: str,
        buyer_id: str,
        crop: str,
        quantity: float,
        quality: str = "Grade A",
        pickup_location: str = "Maharashtra",
        delivery_location: str = "Pune, Maharashtra",
        delivery_deadline_hours: float = 24.0,
        selected_services: Optional[Dict[str, Any]] = None,
        selected_agents: Optional[List[str]] = None,
        workflow_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Creates or restores requirement-scoped Buyer Workflow Memory.
        Maps requested frontend services into the requested agent scope.
        """
        wf_id = workflow_id or f"wf_{str(uuid.uuid4())[:8]}"

        # Deduce selected agents from explicit list or services dict
        agents = []
        if selected_agents is not None:
            agents = [a.upper() for a in selected_agents if a.upper() in SUPPORTED_AGENTS]
        elif selected_services:
            # Always include Farmer if farmer_matching or negotiation requested
            if selected_services.get("farmer_matching") or selected_services.get("negotiation") or selected_services.get("market_intelligence"):
                agents.append(AGENT_FARMER)
            if selected_services.get("transport"):
                agents.append(AGENT_TRANSPORT)
            if selected_services.get("warehouse"):
                agents.append(AGENT_WAREHOUSE)
            if selected_services.get("processor"):
                agents.append(AGENT_PROCESSOR)

        if AGENT_FARMER not in agents:
            # Baseline: Farmer is always the entry prerequisite for procurement
            agents.insert(0, AGENT_FARMER)

        now_iso = datetime.now(timezone.utc).isoformat()
        initial_pending = [a for a in agents if a != AGENT_FARMER]

        state: Dict[str, Any] = {
            "workflow_id": wf_id,
            "requirement_id": requirement_id,
            "buyer_id": buyer_id,
            "crop": crop,
            "quantity": float(quantity),
            "quality": quality,
            "pickup_location": pickup_location,
            "delivery_location": delivery_location,
            "delivery_deadline_hours": float(delivery_deadline_hours),

            # Requested scope
            "selected_agents": agents,
            "current_agent": AGENT_FARMER,
            "completed_agents": [],
            "failed_agents": [],
            "pending_agents": initial_pending,

            # Authoritative Farmer Deal State
            "farmer_deal": {
                "status": None,
                "deal_id": None,
                "transaction_id": None,
                "supplier_id": None,
                "supplier_name": None,
                "supplier_location": pickup_location,
                "quantity": None,
                "price": None,
                "contract_hash": None,
                "finalized_at": None,
                "valid": False,
                "expiry_time": None
            },

            # Outcomes from downstream agents
            "agent_outcomes": {},

            # Final aggregated supply-chain plan
            "final_plan": None,

            # Two separate memory streams
            "conversation_context": [
                {
                    "timestamp": now_iso,
                    "agent": "BUYER_ORCHESTRATOR",
                    "event": "WORKFLOW_INITIALIZED",
                    "message": f"Initialized requirement workflow for {quantity}kg {crop}. Selected agents: {agents}."
                }
            ],
            "audit_logs": [
                {
                    "timestamp": now_iso,
                    "event": "STATE_INITIALIZED",
                    "reason": f"Buyer selected scope: {agents}. Farmer deal required as gate.",
                    "valid_next_actions": ["FARMER"]
                }
            ],

            "last_action": "INITIALIZE",
            "last_response": None,
            "workflow_status": "FARMER_NEGOTIATING",
            "created_at": now_iso,
            "updated_at": now_iso
        }

        # Persist to durable database
        persisted = await Database.upsert_buyer_workflow_async(state)
        logger.info(f"[BUYER_ORCHESTRATOR] Initialized Buyer Workflow {wf_id} for req: {requirement_id}. Selected agents: {agents}")
        return persisted

    # ── State Retrieval ──────────────────────────────────────────────────────
    async def get_workflow_state(
        self,
        workflow_id: Optional[str] = None,
        requirement_id: Optional[str] = None
    ) -> Optional[Dict[str, Any]]:
        """Retrieves workflow memory by workflow_id or requirement_id."""
        return await Database.get_buyer_workflow_async(
            workflow_id=workflow_id,
            requirement_id=requirement_id
        )

    # ── Agent Scope Update ──────────────────────────────────────────────────
    async def update_selected_agents(
        self,
        requirement_id: str,
        selected_agents: List[str]
    ) -> Dict[str, Any]:
        """
        Updates the authoritative list of selected downstream agents requested by the Buyer.
        """
        state = await self.get_workflow_state(requirement_id=requirement_id)
        if not state:
            raise ValueError(f"Workflow state not found for requirement: {requirement_id}")

        cleaned = [a.upper() for a in selected_agents if a.upper() in SUPPORTED_AGENTS]
        if AGENT_FARMER not in cleaned:
            cleaned.insert(0, AGENT_FARMER)

        now_iso = datetime.now(timezone.utc).isoformat()
        state["selected_agents"] = cleaned
        completed = set(state.get("completed_agents", []))
        state["pending_agents"] = [a for a in cleaned if a != AGENT_FARMER and a not in completed]
        state["updated_at"] = now_iso

        state["audit_logs"].append({
            "timestamp": now_iso,
            "event": "AGENTS_SCOPE_UPDATED",
            "selected_agents": cleaned,
            "reason": f"Authoritative agent scope updated to {cleaned}"
        })

        logger.info(f"[BUYER_ORCHESTRATOR] Requirement {requirement_id} updated selected agents: {cleaned}")
        return await Database.upsert_buyer_workflow_async(state)

    # ── Authoritative Farmer Deal Verification ───────────────────────────────
    async def verify_farmer_deal_authoritative(
        self,
        deal_id: Optional[str] = None,
        negotiation_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Pillar 7 Rule: DO NOT TRUST FRONTEND OR LLM FOR DEAL STATE.
        Queries the authoritative backend database to verify that the negotiation
        actually has a status of DEAL or COMPLETED and is not expired or withdrawn.
        """
        target_id = deal_id or negotiation_id
        if not target_id:
            return {"valid": False, "status": DEAL_STATUS_FAILED, "reason": "No deal identifier provided."}

        # Check in negotiations table
        neg = await Database.get_negotiation_async(target_id)
        if not neg:
            # Fallback check by stripping prefixes or searching list
            negs = await Database.list_negotiations_async(limit=100)
            neg = next((n for n in negs if n.get("negotiation_id") == target_id or n.get("id") == target_id), None)

        if not neg:
            return {"valid": False, "status": DEAL_STATUS_FAILED, "reason": f"Deal {target_id} not found in authoritative database."}

        neg_status = str(neg.get("status", "")).upper()

        if neg_status in ("DEAL", "COMPLETED"):
            # Check price and quantity sanity
            final_p = float(neg.get("final_price") or neg.get("price") or 0.0)
            final_q = float(neg.get("quantity") or 0.0)
            if final_p <= 0 or final_q <= 0:
                return {
                    "valid": False,
                    "status": DEAL_STATUS_FAILED,
                    "reason": f"Deal {target_id} has invalid non-positive terms (price={final_p}, qty={final_q})."
                }

            supplier_loc = neg.get("location") or neg.get("pickup_location")
            if not supplier_loc and neg.get("listing_id"):
                try:
                    listing = await Database.get_produce_listing_async(neg["listing_id"])
                    if listing:
                        supplier_loc = listing.get("location")
                except Exception:
                    pass

            return {
                "valid": True,
                "status": DEAL_STATUS_SUCCESS,
                "deal_id": target_id,
                "transaction_id": neg.get("transaction_id") or f"TXN-MH-2026-{str(target_id).replace('neg_', '').upper()}",
                "supplier_id": neg.get("farmer_id") or "farmer_verified",
                "supplier_name": neg.get("farmer_name") or neg.get("farmer") or "Verified APMC Farmer",
                "supplier_location": supplier_loc,
                "crop": neg.get("crop"),
                "quantity": final_q,
                "price": final_p,
                "contract_hash": neg.get("contract_hash"),
                "finalized_at": datetime.now(timezone.utc).isoformat()
            }
        elif neg_status in ("WITHDRAWN", "CANCELLED"):
            return {"valid": False, "status": DEAL_STATUS_WITHDRAWN, "reason": f"Deal {target_id} was withdrawn/cancelled."}
        elif neg_status in ("EXPIRED", "TIMEOUT"):
            return {"valid": False, "status": DEAL_STATUS_EXPIRED, "reason": f"Deal {target_id} expired."}
        else:
            return {"valid": False, "status": DEAL_STATUS_FAILED, "reason": f"Deal {target_id} has non-deal status: {neg_status}."}

    # ── Deal Finalization / State Update Hook ────────────────────────────────
    async def record_farmer_deal_outcome(
        self,
        requirement_id: str,
        deal_id: str,
        outcome_status: str,  # "SUCCESS", "FAILED", "WITHDRAWN", "EXPIRED"
        deal_details: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Updates Buyer Workflow Memory when Farmer negotiation concludes.
        Re-evaluates authoritative deal validity before updating downstream eligibility.
        """
        state = await self.get_workflow_state(requirement_id=requirement_id)
        if not state:
            raise ValueError(f"Workflow state not found for requirement: {requirement_id}")

        now_iso = datetime.now(timezone.utc).isoformat()
        current_completed = list(state.get("completed_agents", []))
        current_failed = list(state.get("failed_agents", []))
        audit = list(state.get("audit_logs", []))
        conv = list(state.get("conversation_context", []))

        auth_verification = {"valid": False}
        if outcome_status == DEAL_STATUS_SUCCESS:
            auth_verification = await self.verify_farmer_deal_authoritative(deal_id)
            if not auth_verification["valid"]:
                logger.warning(f"Authoritative verification failed for deal {deal_id}: {auth_verification.get('reason')}")
                outcome_status = auth_verification.get("status", DEAL_STATUS_FAILED)

        if outcome_status == DEAL_STATUS_SUCCESS:
            auth_deal = auth_verification
            state["farmer_deal"] = {
                "status": DEAL_STATUS_SUCCESS,
                "deal_id": deal_id,
                "transaction_id": auth_deal.get("transaction_id"),
                "supplier_id": auth_deal.get("supplier_id"),
                "supplier_name": auth_deal.get("supplier_name"),
                "supplier_location": (
                    auth_deal.get("supplier_location")
                    or (deal_details.get("supplier_location") if deal_details else None)
                    or state.get("pickup_location")
                    or "Nashik APMC, Maharashtra"
                ),
                "crop": auth_deal.get("crop", state.get("crop")),
                "quantity": auth_deal.get("quantity", state.get("quantity")),
                "price": auth_deal.get("price"),
                "contract_hash": auth_deal.get("contract_hash"),
                "finalized_at": auth_deal.get("finalized_at", now_iso),
                "valid": True
            }
            if AGENT_FARMER not in current_completed:
                current_completed.append(AGENT_FARMER)
            if AGENT_FARMER in current_failed:
                current_failed.remove(AGENT_FARMER)

            state["workflow_status"] = "FARMER_DEAL_SUCCESS"
            conv.append({
                "timestamp": now_iso,
                "agent": AGENT_FARMER,
                "event": "DEAL_SUCCESS",
                "message": f"Farmer deal confirmed: {state['farmer_deal']['quantity']}kg {state['farmer_deal']['crop']} at ₹{state['farmer_deal']['price']}/kg (Deal ID: {deal_id})."
            })
            audit.append({
                "timestamp": now_iso,
                "event": "FARMER_DEAL_VERIFIED",
                "reason": f"Authoritative backend verified deal {deal_id}. Downstream routing is now eligible.",
                "deal_id": deal_id
            })
        else:
            state["farmer_deal"] = {
                "status": outcome_status,
                "deal_id": deal_id,
                "transaction_id": None,
                "supplier_id": None,
                "supplier_name": None,
                "supplier_location": None,
                "quantity": None,
                "price": None,
                "contract_hash": None,
                "finalized_at": now_iso,
                "valid": False
            }
            if AGENT_FARMER not in current_failed:
                current_failed.append(AGENT_FARMER)
            if AGENT_FARMER in current_completed:
                current_completed.remove(AGENT_FARMER)

            state["workflow_status"] = f"FARMER_DEAL_{outcome_status}"
            conv.append({
                "timestamp": now_iso,
                "agent": AGENT_FARMER,
                "event": f"DEAL_{outcome_status}",
                "message": f"Farmer negotiation concluded with status: {outcome_status}. Downstream agents blocked."
            })
            audit.append({
                "timestamp": now_iso,
                "event": "FARMER_DEAL_INVALID",
                "reason": f"Farmer deal status is {outcome_status}. CRITICAL INVARIANT: No valid deal means no downstream supply-chain agent can execute.",
                "deal_id": deal_id
            })

        state["completed_agents"] = current_completed
        state["failed_agents"] = current_failed
        state["conversation_context"] = conv
        state["audit_logs"] = audit
        state["updated_at"] = now_iso

        return await Database.upsert_buyer_workflow_async(state)

    # ── Deal Revalidation (Withdrawal & Expiration Checks) ───────────────────
    async def revalidate_deal_state(self, state: Dict[str, Any]) -> Dict[str, Any]:
        """
        Revalidates existing farmer deal before any downstream handoff.
        If deal was invalidated, marks it invalid and updates memory.
        """
        farmer_deal = state.get("farmer_deal") or {}
        if not farmer_deal.get("valid"):
            return state

        deal_id = farmer_deal.get("deal_id")
        auth = await self.verify_farmer_deal_authoritative(deal_id)
        if not auth["valid"]:
            logger.warning(f"Revalidation of deal {deal_id} failed: {auth.get('reason')}")
            return await self.record_farmer_deal_outcome(
                requirement_id=state["requirement_id"],
                deal_id=deal_id or "invalid_deal",
                outcome_status=auth.get("status", DEAL_STATUS_WITHDRAWN)
            )
        return state

    # ── Valid-Next-Agent Intelligence Service ────────────────────────────────
    def get_valid_next_actions(self, state: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Authoritative Decision Engine:
        Answers: 'Given everything that has happened so far, which actions/agents are valid right now?'
        Incorporates 'Why this agent?' and 'Why not this agent?' rationale into every decision.
        Enforces Phase 9 dependency graph.
        """
        valid_actions: List[Dict[str, Any]] = []
        blocked_reasons: Dict[str, str] = {}

        selected_agents = list(state.get("selected_agents", []))
        completed_agents = set(state.get("completed_agents", []))
        failed_agents = set(state.get("failed_agents", []))
        farmer_deal = state.get("farmer_deal", {})
        deal_valid = bool(farmer_deal.get("valid", False))
        deal_status = farmer_deal.get("status")

        # ── 1. Farmer Gate Evaluation ─────────────────────────────────────────
        if AGENT_FARMER not in completed_agents:
            if deal_status in (DEAL_STATUS_FAILED, DEAL_STATUS_WITHDRAWN, DEAL_STATUS_EXPIRED):
                for agent in [AGENT_TRANSPORT, AGENT_WAREHOUSE, AGENT_PROCESSOR]:
                    agent_title = agent.title()
                    blocked_reasons[agent] = (
                        f"Why not {agent}? Why not {agent_title}? {agent} was requested, but the required Farmer procurement "
                        f"deal failed (status: {deal_status}). No valid Farmer deal = No downstream execution."
                    )

                valid_actions.append({
                    "action": "STOP",
                    "reason": f"Farmer deal failed with status '{deal_status}'. Workflow halted. All downstream agents blocked.",
                    "blocked_reasons": blocked_reasons
                })
                valid_actions.append({
                    "action": "FARMER_RETRY",
                    "reason": "Optionally restart Farmer discovery and negotiation with adjusted parameters.",
                    "blocked_reasons": blocked_reasons
                })
                return valid_actions

            # Negotiation still in progress
            for agent in [AGENT_TRANSPORT, AGENT_WAREHOUSE, AGENT_PROCESSOR]:
                blocked_reasons[agent] = f"Why not {agent}? Why not {agent.title()}? Waiting for Farmer negotiation to reach an authoritative deal."
            valid_actions.append({
                "action": "WAIT_FARMER",
                "reason": "Farmer negotiation is currently active and awaiting authoritative counter-offers or deal settlement.",
                "blocked_reasons": blocked_reasons
            })
            return valid_actions

        # ── 2. Downstream Agent Intelligence (Only when Farmer Deal is Valid) ─
        if not deal_valid:
            for agent in [AGENT_TRANSPORT, AGENT_WAREHOUSE, AGENT_PROCESSOR]:
                blocked_reasons[agent] = f"Why not {agent}? Why not {agent.title()}? Farmer deal is marked invalid."
            valid_actions.append({
                "action": "STOP",
                "reason": "Farmer deal is invalid or has expired. Downstream agents are strictly blocked.",
                "blocked_reasons": blocked_reasons
            })
            return valid_actions

        # Check Unselected Invariant
        for agent in [AGENT_TRANSPORT, AGENT_WAREHOUSE, AGENT_PROCESSOR]:
            if agent not in selected_agents:
                blocked_reasons[agent] = f"Why not {agent}? Why not {agent.title()}? {agent} was not selected in the Buyer requested scope."

        transport_selected = AGENT_TRANSPORT in selected_agents
        transport_completed = AGENT_TRANSPORT in completed_agents
        transport_failed = AGENT_TRANSPORT in failed_agents

        warehouse_selected = AGENT_WAREHOUSE in selected_agents
        warehouse_completed = AGENT_WAREHOUSE in completed_agents
        warehouse_failed = AGENT_WAREHOUSE in failed_agents

        processor_selected = AGENT_PROCESSOR in selected_agents
        processor_completed = AGENT_PROCESSOR in completed_agents
        processor_failed = AGENT_PROCESSOR in failed_agents

        # ── 3. Transport Dependency Rule ──────────────────────────────────────
        # Transport can run immediately after Farmer is verified.
        if transport_selected and not transport_completed and not transport_failed:
            valid_actions.append({
                "action": AGENT_TRANSPORT,
                "eligible_agent": AGENT_TRANSPORT,
                "reason": (
                    "Transport is selected in requested scope, Farmer procurement deal is verified, "
                    "and Transport is the next permitted workflow dependency."
                ),
                "blocked_reasons": {
                    AGENT_WAREHOUSE: "Why not Warehouse yet? Transport was selected and must complete dispatch planning first.",
                    AGENT_PROCESSOR: "Why not Processor yet? Transport was selected and must complete transit scheduling first."
                }
            })

        # ── 4. Warehouse Dependency Rule ──────────────────────────────────────
        # Warehouse can run if:
        # - Warehouse is selected, not completed, not failed
        # - IF Transport was also selected, Transport MUST be completed!
        if warehouse_selected and not warehouse_completed and not warehouse_failed:
            if transport_selected and not transport_completed:
                blocked_reasons[AGENT_WAREHOUSE] = (
                    "Why not Warehouse yet? Transport is currently pending and must complete before warehouse routing."
                )
            else:
                valid_actions.append({
                    "action": AGENT_WAREHOUSE,
                    "eligible_agent": AGENT_WAREHOUSE,
                    "reason": (
                        "Warehouse is selected in requested scope, Farmer procurement deal is verified "
                        f"{'(and Transport completed)' if transport_selected else '(Transport not selected)'}. "
                        "Ready for Warehouse allocation."
                    ),
                    "blocked_reasons": blocked_reasons
                })

        # ── 5. Processor Dependency Rule ──────────────────────────────────────
        # Processor can run if:
        # - Processor is selected, not completed, not failed
        # - IF Transport was selected, Transport must be completed!
        # - IF Warehouse was selected, Warehouse must be completed!
        if processor_selected and not processor_completed and not processor_failed:
            if transport_selected and not transport_completed:
                blocked_reasons[AGENT_PROCESSOR] = (
                    "Why not Processor yet? Transport is currently pending and must complete before industrial processing handoff."
                )
            elif warehouse_selected and not warehouse_completed:
                blocked_reasons[AGENT_PROCESSOR] = (
                    "Why not Processor yet? Warehouse buffer storage is pending and must complete before industrial processing intake."
                )
            else:
                valid_actions.append({
                    "action": AGENT_PROCESSOR,
                    "eligible_agent": AGENT_PROCESSOR,
                    "reason": (
                        "Processor is selected in requested scope, Farmer procurement deal is verified "
                        f"{'(Transport completed)' if transport_selected else ''} "
                        f"{'(Warehouse allocated)' if warehouse_selected else ''}. "
                        "Ready for industrial processing conversion."
                    ),
                    "blocked_reasons": blocked_reasons
                })

        # ── 6. Completion Rule ────────────────────────────────────────────────
        # All selected downstream agents must be completed
        downstream_selected = [a for a in selected_agents if a != AGENT_FARMER]
        all_downstream_done = all(a in completed_agents for a in downstream_selected)

        if all_downstream_done and not valid_actions:
            valid_actions.append({
                "action": "COMPLETE",
                "reason": "All selected agents in the requested Buyer scope have completed their required stages.",
                "blocked_reasons": blocked_reasons
            })

        return valid_actions

    # ── Action Execution / Handoff ───────────────────────────────────────────
    async def step_workflow(
        self,
        requirement_id: str,
        action_override: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Orchestration Step Execution:
        1. Reads and revalidates state.
        2. Calculates valid next actions.
        3. Uses Policy to select next action or validates action_override.
        4. Invokes the REAL downstream agent entrypoint.
        5. Records standardized AgentOutcome in Buyer memory.
        6. Re-evaluates next actions and persists to PostgreSQL.
        """
        state = await self.get_workflow_state(requirement_id=requirement_id)
        if not state:
            raise ValueError(f"Workflow not found for requirement: {requirement_id}")

        # Deal revalidation guard
        state = await self.revalidate_deal_state(state)

        valid_actions = self.get_valid_next_actions(state)
        now_iso = datetime.now(timezone.utc).isoformat()

        # Select action via Policy or explicit override
        if action_override:
            act_clean = action_override.strip().upper()
            # Double-click idempotency guard:
            # If the requested agent has already executed (completed or failed),
            # return current state cleanly without throwing ValueError.
            if act_clean in state.get("completed_agents", []) or act_clean in state.get("failed_agents", []):
                logger.info(f"[BUYER_ORCHESTRATOR] Idempotent call: {act_clean} already executed for req {requirement_id}. Returning state.")
                return state

            selected_action_obj = next((a for a in valid_actions if a["action"] == act_clean), None)
            if not selected_action_obj:
                raise ValueError(
                    f"Action '{action_override}' is not valid right now. "
                    f"Valid actions: {[a['action'] for a in valid_actions]}"
                )
        else:
            selected_action_obj = self.policy.select_action(state, valid_actions)

        if not selected_action_obj:
            logger.info(f"[BUYER_ORCHESTRATOR] No action to execute for workflow {state['workflow_id']}.")
            return state

        action_name = selected_action_obj["action"]
        reason = selected_action_obj.get("reason", "")
        logger.info(f"[BUYER_ORCHESTRATOR] Executing Action: {action_name} for req {requirement_id} (Reason: {reason})")

        state["last_action"] = action_name
        state["current_agent"] = selected_action_obj.get("eligible_agent")

        farmer_deal = state.get("farmer_deal", {})
        qty = float(state.get("quantity") if state.get("quantity") is not None else (farmer_deal.get("quantity") or 1000.0))
        crop = str(state.get("crop") if state.get("crop") is not None else (farmer_deal.get("crop") or "Soybean"))
        pickup = str(farmer_deal.get("supplier_location") or state.get("pickup_location") or "Nashik APMC, Maharashtra")
        delivery = str(state.get("delivery_location") or "Pune, Maharashtra")
        deal_id = farmer_deal.get("deal_id", "DEAL-UNKN")

        # ── Handoff Branch: TRANSPORT ─────────────────────────────────────────
        if action_name == AGENT_TRANSPORT:
            # Idempotency check: if already completed, do not re-run
            if AGENT_TRANSPORT in state.get("completed_agents", []):
                logger.info(f"[BUYER_ORCHESTRATOR] Transport already completed for {requirement_id}. Skipping re-execution.")
                return state

            transport_request = {
                "request_id": f"TR-{state['requirement_id']}-{str(uuid.uuid4())[:4]}",
                "workflow_id": state["workflow_id"],
                "requirement_id": state["requirement_id"],
                "farmer_deal_id": deal_id,
                "crop": crop,
                "quantity_kg": qty,
                "pickup_location": pickup,
                "delivery_location": delivery,
                "delivery_deadline_hours": float(state.get("delivery_deadline_hours") or 24.0),
                "shelf_life_hours": 72.0,
                "refrigerated_required": crop.lower() in {"tomato", "strawberry", "grape", "banana", "mango"}
            }

            state["conversation_context"].append({
                "timestamp": now_iso,
                "agent": "BUYER_ORCHESTRATOR",
                "event": "TRANSPORT_HANDOFF_DISPATCHED",
                "message": f"Handed off {qty}kg {crop} from {pickup} to {delivery} to Transport Agent."
            })

            try:
                logger.info(f"[BUYER_ORCHESTRATOR] Invoking TRANSPORT execution {transport_request['request_id']}")
                transport_outcome = await run_transport_workflow(transport_request)
                t_status = transport_outcome.get("status", "UNKNOWN")
                t_plan = transport_outcome.get("final_transport_plan") or {}
                is_successful = bool(t_plan) and t_status not in ("INFEASIBLE", "FAILED", "REJECTED")

                cost_val = float(t_plan.get("agreed_price") or transport_outcome.get("total_operating_cost") or 0.0)
                vehicle_name = t_plan.get("vehicle_name") or transport_outcome.get("selected_vehicle", {}).get("vehicle_type") or "Freight Vehicle"
                dist = transport_outcome.get("distance_km", 0.0)

                # Standardized AgentOutcome
                outcome = AgentOutcome(
                    agent=AGENT_TRANSPORT,
                    execution_id=transport_request["request_id"],
                    status="COMPLETED" if is_successful else "FAILED",
                    requirement_id=state["requirement_id"],
                    workflow_id=state["workflow_id"],
                    started_at=now_iso,
                    completed_at=datetime.now(timezone.utc).isoformat(),
                    decision="CONFIRMED" if is_successful else "REJECTED",
                    decision_reason=(
                        f"Selected {vehicle_name} for route {pickup} → {delivery} ({dist:.0f}km) at ₹{cost_val:,.2f}"
                        if is_successful else f"Transport planning failed: {t_status}"
                    ),
                    cost=cost_val,
                    candidates=[v for v in transport_outcome.get("candidate_vehicles", [])],
                    selected_option=t_plan,
                    constraints_checked={
                        "crop": crop,
                        "quantity_kg": qty,
                        "pickup": pickup,
                        "delivery": delivery,
                        "refrigerated_required": transport_request["refrigerated_required"]
                    },
                    warnings=[],
                    error=None if is_successful else f"Transport status: {t_status}",
                    retryable=not is_successful,
                    result={
                        "status": "CONFIRMED" if is_successful else "FAILED",
                        "request_id": transport_request["request_id"],
                        "deal_id": deal_id,
                        "vehicle": vehicle_name,
                        "vehicle_type": t_plan.get("vehicle_type"),
                        "route": f"{t_plan.get('pickup_location', pickup)} → {t_plan.get('delivery_location', delivery)}",
                        "distance_km": dist,
                        "cost": cost_val,
                        "response": t_status,
                        "plan": t_plan,
                        "completed_at": datetime.now(timezone.utc).isoformat()
                    }
                )

                outcome_dict = outcome.to_dict()
                if outcome.result:
                    for k, v in outcome.result.items():
                        if k not in outcome_dict:
                            outcome_dict[k] = v
                state["agent_outcomes"][AGENT_TRANSPORT] = outcome_dict

                if is_successful:
                    if AGENT_TRANSPORT not in state["completed_agents"]:
                        state["completed_agents"].append(AGENT_TRANSPORT)
                    if AGENT_TRANSPORT in state["pending_agents"]:
                        state["pending_agents"].remove(AGENT_TRANSPORT)
                    state["last_response"] = f"Transport confirmed via {vehicle_name} at ₹{cost_val}."
                    logger.info(f"[BUYER_ORCHESTRATOR] TRANSPORT completed successfully: {outcome.decision_reason}")
                else:
                    if AGENT_TRANSPORT not in state["failed_agents"]:
                        state["failed_agents"].append(AGENT_TRANSPORT)
                    if AGENT_TRANSPORT in state["pending_agents"]:
                        state["pending_agents"].remove(AGENT_TRANSPORT)
                    state["last_response"] = f"Transport planning failed: {t_status}."
                    logger.warning(f"[BUYER_ORCHESTRATOR] TRANSPORT failed: {t_status}")

            except Exception as e:
                logger.error(f"[BUYER_ORCHESTRATOR] Transport execution error: {e}", exc_info=True)
                outcome = AgentOutcome(
                    agent=AGENT_TRANSPORT,
                    execution_id=transport_request["request_id"],
                    status="FAILED",
                    requirement_id=state["requirement_id"],
                    workflow_id=state["workflow_id"],
                    started_at=now_iso,
                    completed_at=datetime.now(timezone.utc).isoformat(),
                    decision="ERROR",
                    decision_reason=str(e),
                    cost=0.0,
                    error=str(e),
                    retryable=True,
                    result={"error": str(e)}
                )
                state["agent_outcomes"][AGENT_TRANSPORT] = outcome.to_dict()
                if AGENT_TRANSPORT not in state["failed_agents"]:
                    state["failed_agents"].append(AGENT_TRANSPORT)
                state["last_response"] = f"Transport error: {e}."

        # ── Handoff Branch: WAREHOUSE ─────────────────────────────────────────
        elif action_name == AGENT_WAREHOUSE:
            # Idempotency check: if already completed, do not re-run
            if AGENT_WAREHOUSE in state.get("completed_agents", []):
                logger.info(f"[BUYER_ORCHESTRATOR] Warehouse already completed for {requirement_id}. Skipping re-execution.")
                return state

            warehouse_request = {
                "requirement_id": state["requirement_id"],
                "workflow_id": state["workflow_id"],
                "farmer_deal_id": deal_id,
                "crop": crop,
                "quantity_kg": qty,
                "location": delivery,
                "pickup_location": pickup,
                "delivery_location": delivery,
                "holding_days": 7,
                "refrigerated_required": crop.lower() in {"tomato", "strawberry", "grape", "banana", "mango"}
            }

            state["conversation_context"].append({
                "timestamp": now_iso,
                "agent": "BUYER_ORCHESTRATOR",
                "event": "WAREHOUSE_HANDOFF_DISPATCHED",
                "message": f"Handed off {qty}kg {crop} storage allocation to Warehouse Agent."
            })

            try:
                logger.info(f"[BUYER_ORCHESTRATOR] Invoking WAREHOUSE execution for req {state['requirement_id']}")
                wh_result = await run_warehouse_workflow(warehouse_request)
                wh_status = wh_result.get("status", "FAILED")
                is_successful = (wh_status == "COMPLETED")

                # Wrap in AgentOutcome
                outcome = AgentOutcome(
                    agent=AGENT_WAREHOUSE,
                    execution_id=wh_result.get("execution_id") or f"WH-EXEC-{uuid.uuid4().hex[:8]}",
                    status=wh_status,
                    requirement_id=state["requirement_id"],
                    workflow_id=state["workflow_id"],
                    started_at=wh_result.get("started_at", now_iso),
                    completed_at=wh_result.get("completed_at", datetime.now(timezone.utc).isoformat()),
                    decision=wh_result.get("decision", "CONFIRMED"),
                    decision_reason=wh_result.get("decision_reason", ""),
                    cost=float(wh_result.get("cost", 0.0)),
                    candidates=wh_result.get("candidates", []),
                    selected_option=wh_result.get("selected_option"),
                    constraints_checked=wh_result.get("constraints_checked", {}),
                    warnings=wh_result.get("warnings", []),
                    error=wh_result.get("error"),
                    retryable=wh_result.get("retryable", False),
                    result=wh_result.get("result", {})
                )

                outcome_dict = outcome.to_dict()
                if outcome.result:
                    for k, v in outcome.result.items():
                        if k not in outcome_dict:
                            outcome_dict[k] = v
                state["agent_outcomes"][AGENT_WAREHOUSE] = outcome_dict

                if is_successful:
                    if AGENT_WAREHOUSE not in state["completed_agents"]:
                        state["completed_agents"].append(AGENT_WAREHOUSE)
                    if AGENT_WAREHOUSE in state["pending_agents"]:
                        state["pending_agents"].remove(AGENT_WAREHOUSE)
                    sel_name = wh_result.get("selected_option", {}).get("name", "Warehouse Hub")
                    cost_val = wh_result.get("cost", 0.0)
                    state["last_response"] = f"Warehouse confirmed at {sel_name} (Cost: ₹{cost_val:,.2f})."
                    logger.info(f"[BUYER_ORCHESTRATOR] WAREHOUSE completed successfully: {outcome.decision_reason}")
                else:
                    if AGENT_WAREHOUSE not in state["failed_agents"]:
                        state["failed_agents"].append(AGENT_WAREHOUSE)
                    if AGENT_WAREHOUSE in state["pending_agents"]:
                        state["pending_agents"].remove(AGENT_WAREHOUSE)
                    state["last_response"] = f"Warehouse allocation failed: {wh_result.get('decision_reason')}."
                    logger.warning(f"[BUYER_ORCHESTRATOR] WAREHOUSE failed: {wh_result.get('decision_reason')}")

            except Exception as e:
                logger.error(f"[BUYER_ORCHESTRATOR] Warehouse execution error: {e}", exc_info=True)
                outcome = AgentOutcome(
                    agent=AGENT_WAREHOUSE,
                    execution_id=f"WH-EXEC-{uuid.uuid4().hex[:8]}",
                    status="FAILED",
                    requirement_id=state["requirement_id"],
                    workflow_id=state["workflow_id"],
                    started_at=now_iso,
                    completed_at=datetime.now(timezone.utc).isoformat(),
                    decision="ERROR",
                    decision_reason=str(e),
                    cost=0.0,
                    error=str(e),
                    retryable=True,
                    result={"error": str(e)}
                )
                state["agent_outcomes"][AGENT_WAREHOUSE] = outcome.to_dict()
                if AGENT_WAREHOUSE not in state["failed_agents"]:
                    state["failed_agents"].append(AGENT_WAREHOUSE)
                state["last_response"] = f"Warehouse error: {e}."

        # ── Handoff Branch: PROCESSOR ─────────────────────────────────────────
        elif action_name == AGENT_PROCESSOR:
            # Idempotency check: if already completed, do not re-run
            if AGENT_PROCESSOR in state.get("completed_agents", []):
                logger.info(f"[BUYER_ORCHESTRATOR] Processor already completed for {requirement_id}. Skipping re-execution.")
                return state

            crop_lower = crop.lower()
            default_moist = 7.5 if "cotton" in crop_lower else (10.0 if "soybean" in crop_lower else 12.0)
            processor_request = {
                "requirement_id": state["requirement_id"],
                "workflow_id": state["workflow_id"],
                "farmer_deal_id": deal_id,
                "crop": crop,
                "quantity_kg": qty,
                "quality_grade": state.get("quality", "Grade A"),
                "moisture": float(state.get("moisture") or default_moist),
                "location": delivery,
                "purpose": "commercial_processing"
            }

            state["conversation_context"].append({
                "timestamp": now_iso,
                "agent": "BUYER_ORCHESTRATOR",
                "event": "PROCESSOR_HANDOFF_DISPATCHED",
                "message": f"Handed off {qty}kg {crop} industrial milling to Processor Agent."
            })

            try:
                logger.info(f"[BUYER_ORCHESTRATOR] Invoking PROCESSOR execution for req {state['requirement_id']}")
                proc_result = await run_processor_workflow(processor_request)
                proc_status = proc_result.get("status", "FAILED")
                is_successful = (proc_status == "COMPLETED")

                # Wrap in AgentOutcome
                outcome = AgentOutcome(
                    agent=AGENT_PROCESSOR,
                    execution_id=proc_result.get("execution_id") or f"PROC-EXEC-{uuid.uuid4().hex[:8]}",
                    status=proc_status,
                    requirement_id=state["requirement_id"],
                    workflow_id=state["workflow_id"],
                    started_at=proc_result.get("started_at", now_iso),
                    completed_at=proc_result.get("completed_at", datetime.now(timezone.utc).isoformat()),
                    decision=proc_result.get("decision", "CONFIRMED"),
                    decision_reason=proc_result.get("decision_reason", ""),
                    cost=float(proc_result.get("cost", 0.0)),
                    candidates=proc_result.get("candidates", []),
                    selected_option=proc_result.get("selected_option"),
                    constraints_checked=proc_result.get("constraints_checked", {}),
                    warnings=proc_result.get("warnings", []),
                    error=proc_result.get("error"),
                    retryable=proc_result.get("retryable", False),
                    result=proc_result.get("result", {})
                )

                outcome_dict = outcome.to_dict()
                if outcome.result:
                    for k, v in outcome.result.items():
                        if k not in outcome_dict:
                            outcome_dict[k] = v
                state["agent_outcomes"][AGENT_PROCESSOR] = outcome_dict

                if is_successful:
                    if AGENT_PROCESSOR not in state["completed_agents"]:
                        state["completed_agents"].append(AGENT_PROCESSOR)
                    if AGENT_PROCESSOR in state["pending_agents"]:
                        state["pending_agents"].remove(AGENT_PROCESSOR)
                    p_name = proc_result.get("selected_option", {}).get("name", "Processor Mill")
                    cost_val = proc_result.get("cost", 0.0)
                    state["last_response"] = f"Processor confirmed at {p_name} (Cost: ₹{cost_val:,.2f})."
                    logger.info(f"[BUYER_ORCHESTRATOR] PROCESSOR completed successfully: {outcome.decision_reason}")
                else:
                    if AGENT_PROCESSOR not in state["failed_agents"]:
                        state["failed_agents"].append(AGENT_PROCESSOR)
                    if AGENT_PROCESSOR in state["pending_agents"]:
                        state["pending_agents"].remove(AGENT_PROCESSOR)
                    state["last_response"] = f"Processor batch failed: {proc_result.get('decision_reason')}."
                    logger.warning(f"[BUYER_ORCHESTRATOR] PROCESSOR failed: {proc_result.get('decision_reason')}")

            except Exception as e:
                logger.error(f"[BUYER_ORCHESTRATOR] Processor execution error: {e}", exc_info=True)
                outcome = AgentOutcome(
                    agent=AGENT_PROCESSOR,
                    execution_id=f"PROC-EXEC-{uuid.uuid4().hex[:8]}",
                    status="FAILED",
                    requirement_id=state["requirement_id"],
                    workflow_id=state["workflow_id"],
                    started_at=now_iso,
                    completed_at=datetime.now(timezone.utc).isoformat(),
                    decision="ERROR",
                    decision_reason=str(e),
                    cost=0.0,
                    error=str(e),
                    retryable=True,
                    result={"error": str(e)}
                )
                state["agent_outcomes"][AGENT_PROCESSOR] = outcome.to_dict()
                if AGENT_PROCESSOR not in state["failed_agents"]:
                    state["failed_agents"].append(AGENT_PROCESSOR)
                state["last_response"] = f"Processor error: {e}."

        # ── Handoff Branch: COMPLETE / STOP ───────────────────────────────────
        elif action_name == "COMPLETE":
            # Calculate final aggregated procurement economics
            farmer_price = float(farmer_deal.get("price") or 0.0)
            farmer_total = round(farmer_price * qty, 2)

            t_outcome = state.get("agent_outcomes", {}).get(AGENT_TRANSPORT, {})
            w_outcome = state.get("agent_outcomes", {}).get(AGENT_WAREHOUSE, {})
            p_outcome = state.get("agent_outcomes", {}).get(AGENT_PROCESSOR, {})

            transport_cost = float(t_outcome.get("cost") or 0.0)
            warehouse_cost = float(w_outcome.get("cost") or 0.0)
            processor_cost = float(p_outcome.get("cost") or 0.0)

            total_supply_chain_cost = round(farmer_total + transport_cost + warehouse_cost + processor_cost, 2)

            # Generate Digital Contract Signature Hash
            proof_str = f"{requirement_id}:{deal_id}:{qty}:{farmer_total}:{transport_cost}:{warehouse_cost}:{processor_cost}"
            digital_sig = f"0x{hashlib.sha256(proof_str.encode()).hexdigest()[:16]}"

            state["final_plan"] = {
                "requirement_id": requirement_id,
                "workflow_id": state["workflow_id"],
                "crop": crop,
                "quantity_kg": qty,
                "farmer_deal": farmer_deal,
                "farmer_procurement_cost": farmer_total,
                "transport_plan": t_outcome.get("selected_option") or t_outcome.get("result"),
                "transport_cost": transport_cost,
                "warehouse_plan": w_outcome.get("selected_option") or w_outcome.get("result"),
                "warehouse_cost": warehouse_cost,
                "processor_plan": p_outcome.get("selected_option") or p_outcome.get("result"),
                "processor_cost": processor_cost,
                "total_procurement_cost": total_supply_chain_cost,
                "contract_signature": digital_sig,
                "completed_at": now_iso
            }

            state["workflow_status"] = "COMPLETED"
            state["current_agent"] = None
            state["last_response"] = (
                f"Supply-chain procurement completed successfully. "
                f"Total: ₹{total_supply_chain_cost:,.2f} (Digital Contract: {digital_sig})."
            )
            logger.info(f"[BUYER_ORCHESTRATOR] Requirement {requirement_id} workflow completed successfully: {digital_sig}")

        elif action_name == "STOP":
            state["workflow_status"] = "STOPPED"
            state["current_agent"] = None
            state["last_response"] = "Workflow stopped due to prerequisite failure or invalid deal."

        # Audit Decision Logging
        state["audit_logs"].append({
            "timestamp": now_iso,
            "buyer_id": state["buyer_id"],
            "requirement_id": state["requirement_id"],
            "workflow_id": state["workflow_id"],
            "selected_agents": state["selected_agents"],
            "current_agent": state["current_agent"],
            "farmer_deal_status": state.get("farmer_deal", {}).get("status"),
            "farmer_deal_id": state.get("farmer_deal", {}).get("deal_id"),
            "completed_agents": state["completed_agents"],
            "failed_agents": state["failed_agents"],
            "pending_agents": state["pending_agents"],
            "valid_next_actions": [a["action"] for a in valid_actions],
            "selected_action": action_name,
            "reason": reason
        })

        state["updated_at"] = now_iso
        return await Database.upsert_buyer_workflow_async(state)

    # ── Full Automated Execution Helper ──────────────────────────────────────
    async def execute_full_workflow(self, requirement_id: str) -> Dict[str, Any]:
        """
        Executes the entire multi-agent supply chain sequentially across all selected agents
        until workflow completes or encounters an unrecoverable failure.
        """
        state = await self.get_workflow_state(requirement_id=requirement_id)
        if not state:
            raise ValueError(f"Workflow not found for requirement: {requirement_id}")

        max_steps = 10
        step_count = 0

        while step_count < max_steps:
            step_count += 1
            valid_actions = self.get_valid_next_actions(state)
            if not valid_actions:
                break

            action_names = [a["action"] for a in valid_actions]
            if "COMPLETE" in action_names:
                state = await self.step_workflow(requirement_id=requirement_id, action_override="COMPLETE")
                break
            elif "STOP" in action_names:
                state = await self.step_workflow(requirement_id=requirement_id, action_override="STOP")
                break
            elif "WAIT_FARMER" in action_names:
                logger.info(f"[BUYER_ORCHESTRATOR] Workflow {requirement_id} waiting on Farmer negotiation.")
                break

            # Pick next eligible agent
            next_action = self.policy.select_action(state, valid_actions)
            if not next_action or next_action["action"] in ("WAIT_FARMER", "FARMER_RETRY"):
                break

            state = await self.step_workflow(requirement_id=requirement_id, action_override=next_action["action"])

            # If the step failed, break to prevent infinite loops
            if next_action["action"] in state.get("failed_agents", []):
                logger.warning(f"[BUYER_ORCHESTRATOR] Agent {next_action['action']} failed. Halting automated execution.")
                break

        return state


# Global singleton instance
buyer_workflow_service = BuyerWorkflowService()
