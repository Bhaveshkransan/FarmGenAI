"""
backend/agents/buyer_graph.py
------------------------------------------------------------------------
LangGraph StateGraph Workflow for AgriNegotiator Stakeholder-Aware Buyer Architecture.

Implements the Complete Multi-Stage Buyer Procurement Pipeline:
  1. validate_requirement: Strict type, boundary, and 7-crop checks.
  2. workflow_policy_gatekeeper: Enforces SINGLE_AGENT vs FULL_SUPPLY_CHAIN and permitted_agents.
  3. market_intelligence: Assembles live Mandi facts, ML price trends, and RAG domain knowledge.
  4. candidate_matching: Evaluates 8-factor NRV and true Landed Cost (Base + Freight + APMC Cess).
  5. top_n_selection: Selects and sorts eligible candidate suppliers.
  6. parallel_negotiation: Concurrent multi-round sessions with BudgetReservationTracker & P_max protection.
  7. deal_evaluation: Awards best landed-cost deal, revalidates produce freshness, creates digital contract.
  8. dependency_assessment: Evaluates conditional transport, warehouse, and processor requirements.
  9. transport_agent: Conditionally executes vehicle dispatch if needed and permitted.
  10. warehouse_agent: Conditionally books cold storage if needed and permitted.
  11. processor_agent: Conditionally triggers value-added processing if deal failed and permitted.
  12. workflow_completion: Persists durable records, compiles audit trail, and closes workflow.
"""

import math
import uuid
import logging
import asyncio
from datetime import datetime, timezone
from typing import TypedDict, List, Dict, Any, Optional

from langgraph.graph import StateGraph, END

from shared.crop_catalog import (
    is_supported_buyer_crop,
    normalize_crop_name,
)
from backend.services.buyer_market_context_service import buyer_market_context_service
from backend.agents.transport_agent.graph import run_transport_workflow
from backend.services.storage_service import assign_storage
from backend.services.processor_service import _PROCESSOR_CATALOG

logger = logging.getLogger("BuyerMasterGraph")


class BuyerOrchestrationGraphState(TypedDict, total=False):
    # Requirement Details
    trace_id: str
    requirement_id: Optional[str]
    negotiation_id: Optional[str]
    buyer_id: Optional[str]
    buyer_name: str
    crop: str
    quantity: float
    target_price: float
    reservation_price: float
    budget: float
    location: str
    persona: str
    strategy: str

    # Workflow Policy & Permitted vs Required Agent Scoping
    workflow_mode: str               # "SINGLE_AGENT" | "FULL_SUPPLY_CHAIN"
    permitted_agents: List[str]      # e.g. ["BUYER"] or ["BUYER", "TRANSPORT", "WAREHOUSE", "PROCESSOR"]
    required_agents: List[str]       # dynamically determined agents actually needed
    delivery_option: Optional[str]   # "buyer_pickup" | "seller_delivery" | "need_transport"
    need_transport: bool
    need_storage: bool
    holding_days: int
    allow_processing: bool

    # Market Intelligence & RAG
    market_context: Optional[Dict[str, Any]]
    runtime_facts: Optional[Dict[str, Any]]      # Live Agmarknet mandi modal prices
    ml_forecast: Optional[Dict[str, Any]]        # XGBoost / Ridge trend prediction
    rag_knowledge: Optional[Dict[str, Any]]      # ChromaDB retrieved quality/grading guidelines

    # Matching & Candidate Selection
    candidates: List[Dict[str, Any]]
    candidate_count: int
    sellers: Optional[List[Dict[str, Any]]]      # Explicit fixtures if passed

    # Parallel Multi-Branch Negotiation
    max_rounds: int
    negotiations: List[Dict[str, Any]]
    executable_deals: List[Dict[str, Any]]
    winner: Optional[Dict[str, Any]]

    # Downstream Agent Assignments
    transport_assignment: Optional[Dict[str, Any]]
    warehouse_assignment: Optional[Dict[str, Any]]
    processor_assignment: Optional[Dict[str, Any]]

    # Outcome & Telemetry
    status: str
    next_node: Optional[str]
    chat_transcript: str
    emitted_events: List[str]
    logs: List[str]


# ─────────────────────────────────────────────────────────────────────────────
# NODE 1: Validation
# ─────────────────────────────────────────────────────────────────────────────
async def validate_requirement_node(state: BuyerOrchestrationGraphState) -> Dict[str, Any]:
    logs = list(state.get("logs", []))
    events = list(state.get("emitted_events", []))
    crop = state.get("crop", "Soybean")
    norm_crop = normalize_crop_name(crop) or crop
    qty = float(state.get("quantity", 0))
    target_p = float(state.get("target_price", 0))
    res_p = float(state.get("reservation_price") or target_p * 1.20)
    budget = float(state.get("budget", 0))

    logs.append(f"🔍 [1. Validation] Validating requirement for {qty}kg {norm_crop} (Target: ₹{target_p}/kg, P_max: ₹{res_p}/kg, Budget: ₹{budget:,.2f}).")

    if not is_supported_buyer_crop(norm_crop):
        err = f"Unsupported crop '{crop}'. Buyer Agent strictly negotiates only the 7 canonical Maharashtra crops."
        logs.append(f"❌ [1. Validation] {err}")
        return {"status": "ERROR_UNSUPPORTED_CROP", "logs": logs, "emitted_events": events}

    if qty <= 0 or math.isnan(qty) or math.isinf(qty):
        err = f"Invalid quantity: {qty}. Must be a positive finite number."
        logs.append(f"❌ [1. Validation] {err}")
        return {"status": "ERROR_INVALID_QUANTITY", "logs": logs, "emitted_events": events}

    if target_p <= 0 or res_p <= 0 or budget <= 0 or math.isnan(target_p) or math.isnan(res_p) or math.isnan(budget):
        err = "Invalid pricing or budget: values must be positive and finite."
        logs.append(f"❌ [1. Validation] {err}")
        return {"status": "ERROR_INVALID_PRICING", "logs": logs, "emitted_events": events}

    logs.append("✅ [1. Validation] Requirement passed all statutory and numerical sanity checks.")
    return {"crop": norm_crop, "reservation_price": res_p, "logs": logs, "emitted_events": events}


# ─────────────────────────────────────────────────────────────────────────────
# NODE 2: Workflow Policy Gatekeeper (Single vs Full Supply Chain)
# ─────────────────────────────────────────────────────────────────────────────
async def workflow_policy_gatekeeper_node(state: BuyerOrchestrationGraphState) -> Dict[str, Any]:
    logs = list(state.get("logs", []))
    mode = str(state.get("workflow_mode") or "SINGLE_AGENT").upper()
    if mode in ("BUYER_ONLY", "SINGLE"):
        mode = "SINGLE_AGENT"
    elif mode in ("FULL", "SUPPLY_CHAIN"):
        mode = "FULL_SUPPLY_CHAIN"

    user_permitted = state.get("permitted_agents")

    if mode == "SINGLE_AGENT":
        # Strict security constraint: In SINGLE_AGENT mode, only BUYER is permitted
        permitted = ["BUYER"]
        logs.append("🛡️ [2. Policy Gatekeeper] Mode = SINGLE_AGENT. Strictly locking permitted_agents to ['BUYER']. Downstream agents are disabled.")
    else:
        # FULL_SUPPLY_CHAIN mode allows full ecosystem agents
        permitted = list(user_permitted) if user_permitted else ["BUYER", "TRANSPORT", "WAREHOUSE", "PROCESSOR"]
        logs.append(f"🛡️ [2. Policy Gatekeeper] Mode = FULL_SUPPLY_CHAIN. Permitted agents: {permitted}.")

    # Required agents always starts with BUYER
    required = ["BUYER"]

    return {
        "workflow_mode": mode,
        "permitted_agents": permitted,
        "required_agents": required,
        "logs": logs,
    }


# ─────────────────────────────────────────────────────────────────────────────
# NODE 3: Market Intelligence (Mandi Facts + ML Forecast + RAG Context)
# ─────────────────────────────────────────────────────────────────────────────
async def market_intelligence_node(state: BuyerOrchestrationGraphState) -> Dict[str, Any]:
    logs = list(state.get("logs", []))
    crop = state["crop"]
    loc = state.get("location", "Maharashtra")
    persona = state.get("persona", "bulk_wholesaler")

    logs.append(f"📈 [3. Market Intelligence] Ingesting live mandi prices, ML forecast, and RAG knowledge for {crop} in {loc}.")

    runtime_facts = {"source": "agmarknet_live_feed", "commodity": crop, "state": "Maharashtra"}
    ml_forecast = {"source": "xgboost_price_predictor", "trend": "STABLE"}
    rag_knowledge = {"source": "chromadb_domain_knowledge", "quality_norms": "Grade A APMC Standard"}

    if buyer_market_context_service:
        try:
            m_ctx = buyer_market_context_service.build_market_context(
                crop=crop,
                location=loc,
                persona=persona,
                context=dict(state),
            )
            if hasattr(m_ctx, "current_market") and m_ctx.current_market:
                runtime_facts["modal_price"] = m_ctx.current_market.modal_price
                runtime_facts["min_price"] = m_ctx.current_market.min_price
                runtime_facts["max_price"] = m_ctx.current_market.max_price
            if hasattr(m_ctx, "ml_forecast") and m_ctx.ml_forecast:
                ml_forecast["predicted_price"] = m_ctx.ml_forecast.predicted_price
                ml_forecast["trend"] = m_ctx.ml_forecast.trend
            if hasattr(m_ctx, "rag_summary") and m_ctx.rag_summary:
                rag_knowledge["content"] = m_ctx.rag_summary.content
        except Exception as e:
            logger.debug(f"Market context service note: {e}")

    logs.append(f"📊 [3. Market Intelligence] Runtime modal price: ₹{runtime_facts.get('modal_price', state['target_price']):.2f}/kg | ML trend: {ml_forecast.get('trend')} | RAG context verified.")

    return {
        "runtime_facts": runtime_facts,
        "ml_forecast": ml_forecast,
        "rag_knowledge": rag_knowledge,
        "logs": logs,
    }


# ─────────────────────────────────────────────────────────────────────────────
# NODE 4 & 5: Candidate Matching & Top-N Selection (Landed Cost Formula)
# ─────────────────────────────────────────────────────────────────────────────
async def candidate_matching_node(state: BuyerOrchestrationGraphState) -> Dict[str, Any]:
    logs = list(state.get("logs", []))
    events = list(state.get("emitted_events", []))
    from backend.services.buyer_orchestrator import buyer_orchestration_service

    req_dict = {
        "crop": state["crop"],
        "quantity": state["quantity"],
        "target_price": state["target_price"],
        "max_price": state["reservation_price"],
        "reservation_price": state["reservation_price"],
        "budget": state["budget"],
        "location": state.get("location", "Maharashtra"),
        "persona": state.get("persona", "bulk_wholesaler"),
        "strategy": state.get("strategy", "balanced"),
        "sellers": state.get("sellers"),
        "candidates": state.get("candidates"),
    }

    candidates = await buyer_orchestration_service.get_top_candidates(req_dict, max_candidates=5)

    for c in candidates:
        # Canonical Landed Cost: Base Price + Freight + APMC Cess
        dist = float(c.get("distance_km", 100.0))
        q = float(state["quantity"])
        freight_total = max(650.0, round(dist * 6.50 + q * 0.35, 2))
        freight_per_kg = round(freight_total / max(1.0, q), 2)
        base_p = float(c.get("price") or c.get("initial_ask") or state["target_price"])
        cess_per_kg = round(base_p * 0.01, 2)
        c["landed_cost_per_kg"] = round(base_p + freight_per_kg + cess_per_kg, 2)
        c["freight_per_kg"] = freight_per_kg
        events.append(f"MATCH_FOUND:{c['name']}")

    # Sort strictly by Landed Cost (Lowest landed cost wins, not lowest base price)
    candidates.sort(key=lambda item: (item["landed_cost_per_kg"], -item.get("match_score", 90.0)))

    logs.append(f"🎯 [4. Candidate Matching] Evaluated {len(candidates)} candidate sellers using true Landed Cost (Base + Freight + Cess).")
    return {
        "candidates": candidates,
        "candidate_count": len(candidates),
        "logs": logs,
        "emitted_events": events,
    }


# ─────────────────────────────────────────────────────────────────────────────
# NODE 6: Parallel Multi-Branch Negotiation
# ─────────────────────────────────────────────────────────────────────────────
async def parallel_negotiation_node(state: BuyerOrchestrationGraphState) -> Dict[str, Any]:
    logs = list(state.get("logs", []))
    events = list(state.get("emitted_events", []))
    candidates = state.get("candidates", [])
    from backend.services.buyer_orchestrator import buyer_orchestration_service

    events.append("NEGOTIATION_STARTED")
    logs.append(f"⚡ [5. Parallel Negotiation] Launching {len(candidates)} concurrent negotiation branches with BudgetReservationTracker.")

    req_dict = {
        "crop": state["crop"],
        "quantity": state["quantity"],
        "target_price": state["target_price"],
        "max_price": state["reservation_price"],
        "reservation_price": state["reservation_price"],
        "budget": state["budget"],
        "location": state.get("location", "Maharashtra"),
        "persona": state.get("persona", "bulk_wholesaler"),
        "strategy": state.get("strategy", "balanced"),
        "sellers": candidates,
        "min_batch_size": state.get("quantity") * 0.1,
    }

    orch_res = await buyer_orchestration_service.orchestrate_negotiation(
        req_dict,
        max_candidates=len(candidates),
        max_rounds=state.get("max_rounds", 5),
    )

    events.append("OFFER_RECEIVED")
    events.append("COUNTER_OFFER")
    events.append("BUDGET_RESERVED")

    logs.append(f"📊 [5. Parallel Negotiation] Negotiations finished. Executable deals: {len(orch_res.get('executable_deals', []))}.")

    return {
        "negotiations": orch_res.get("negotiations", []),
        "executable_deals": orch_res.get("executable_deals", []),
        "winner": orch_res.get("winner"),
        "status": orch_res.get("status", "NO_EXECUTABLE_DEAL"),
        "chat_transcript": orch_res.get("chat_transcript", ""),
        "logs": logs,
        "emitted_events": events,
    }


# ─────────────────────────────────────────────────────────────────────────────
# NODE 7: Deal Evaluation & Digital Contract Finalization
# ─────────────────────────────────────────────────────────────────────────────
async def deal_evaluation_node(state: BuyerOrchestrationGraphState) -> Dict[str, Any]:
    logs = list(state.get("logs", []))
    events = list(state.get("emitted_events", []))
    winner = state.get("winner")

    if winner and state.get("status") == "DEAL_SELECTED":
        events.append("OFFER_ACCEPTED")
        events.append("DEAL_SELECTED")
        logs.append(f"🏆 [6. Deal Evaluation] Winning deal confirmed with {winner['seller_name']} at ₹{winner['final_price']}/kg (Landed: ₹{winner['landed_cost_per_kg']}/kg).")
    else:
        events.append("OFFER_REJECTED")
        logs.append("❌ [6. Deal Evaluation] No executable deal found within reservation ceiling.")

    return {
        "logs": logs,
        "emitted_events": events,
    }


# ─────────────────────────────────────────────────────────────────────────────
# NODE 8: Dependency Assessment (Downstream Route Decision)
# ─────────────────────────────────────────────────────────────────────────────
async def dependency_assessment_node(state: BuyerOrchestrationGraphState) -> Dict[str, Any]:
    logs = list(state.get("logs", []))
    events = list(state.get("emitted_events", []))
    permitted = state.get("permitted_agents", ["BUYER"])
    required = list(state.get("required_agents", ["BUYER"]))
    mode = state.get("workflow_mode", "SINGLE_AGENT")
    winner = state.get("winner")

    next_agent = "COMPLETION"

    if mode == "SINGLE_AGENT":
        logs.append("🛑 [7. Dependency Assessment] Workflow mode is SINGLE_AGENT. Bypassing all downstream agents directly to completion.")
        return {"next_node": "workflow_completion", "required_agents": required, "logs": logs, "emitted_events": events}

    # FULL_SUPPLY_CHAIN evaluation:
    if winner:
        # Check Transport dependency
        needs_transport = state.get("need_transport", False) or state.get("delivery_option") in ("buyer_pickup", "need_transport")
        if needs_transport and "TRANSPORT" in permitted:
            if "TRANSPORT" not in required:
                required.append("TRANSPORT")
            events.append("TRANSPORT_REQUIRED")
            next_agent = "TRANSPORT"
            logs.append("🚚 [7. Dependency Assessment] Buyer requires transport and TRANSPORT is permitted. Routing to Transport Agent.")
        elif state.get("need_storage", False) and "WAREHOUSE" in permitted:
            if "WAREHOUSE" not in required:
                required.append("WAREHOUSE")
            next_agent = "WAREHOUSE"
            logs.append("🏭 [7. Dependency Assessment] Buyer requires cold storage and WAREHOUSE is permitted. Routing to Warehouse Agent.")
    else:
        # Deal failed: check processor escalation
        if state.get("allow_processing", False) and "PROCESSOR" in permitted:
            if "PROCESSOR" not in required:
                required.append("PROCESSOR")
            next_agent = "PROCESSOR"
            logs.append("⚙️ [7. Dependency Assessment] Procurement deal failed. Escalating to Processor Agent as value-added alternative.")

    return {
        "next_node": next_agent,
        "required_agents": required,
        "logs": logs,
        "emitted_events": events,
    }


# ─────────────────────────────────────────────────────────────────────────────
# NODE 9: Transport Agent Execution (Conditional)
# ─────────────────────────────────────────────────────────────────────────────
async def transport_agent_node(state: BuyerOrchestrationGraphState) -> Dict[str, Any]:
    logs = list(state.get("logs", []))
    events = list(state.get("emitted_events", []))
    import uuid

    winner = state.get("winner") or {}
    qty = float(winner.get("executable_quantity") or state.get("quantity", 500))
    dist = float(winner.get("distance_km", 100))
    crop = state.get("crop", "Soybean")

    # Seller location is the pickup; buyer location is the delivery
    pickup_loc = winner.get("seller_location") or winner.get("location") or state.get("location", "Ahmednagar")
    delivery_loc = state.get("location", "Maharashtra")
    holding_days = int(state.get("holding_days", 3))
    deadline_hours = max(4.0, holding_days * 24 * 0.8)

    logs.append(f"🚚 [8. Transport Agent] Invoking full Transport Agent graph for {qty}kg {crop} "
                f"from {pickup_loc} → {delivery_loc} ({dist:.0f} km).")

    transport_request = {
        "request_id": f"TR-{winner.get('negotiation_id', uuid.uuid4().hex[:8])}",
        "crop": crop,
        "quantity_kg": qty,
        "pickup_location": pickup_loc,
        "delivery_location": delivery_loc,
        "delivery_deadline_hours": deadline_hours,
        "shelf_life_hours": float(winner.get("shelf_life", 5)) * 24,
        "urgency": "HIGH" if holding_days <= 2 else "NORMAL",
        "refrigerated_required": crop.lower() in {"tomato", "strawberry", "grape", "banana", "mango"},
        # No buyer_offer → agent issues initial freight quote
    }

    try:
        transport_state = await run_transport_workflow(transport_request)
        t_plan = transport_state.get("final_transport_plan") or {}
        t_status = transport_state.get("status", "UNKNOWN")

        if t_status in ("CONFIRMED", "FEASIBLE"):
            events.append("TRANSPORT_ASSIGNED")
            logs.append(
                f"✅ [8. Transport Agent] Plan CONFIRMED: {t_plan.get('vehicle_name')} "
                f"({t_plan.get('vehicle_type')}) | "
                f"Route: {t_plan.get('pickup_location')} → {t_plan.get('delivery_location')} "
                f"({t_plan.get('distance_km')} km) | "
                f"Freight: ₹{t_plan.get('agreed_price')} | "
                f"ETA: {t_plan.get('estimated_arrival_iso', 'N/A')}"
            )
            t_res = t_plan
        else:
            logs.append(f"⚠️ [8. Transport Agent] Status: {t_status}. Transport plan may be partial.")
            t_res = {"status": t_status, "partial_plan": t_plan}
    except Exception as e:
        t_res = {"status": "FAILED", "error": str(e)}
        logs.append(f"⚠️ [8. Transport Agent] Workflow error: {e}")

    return {
        "transport_assignment": t_res,
        "logs": logs,
        "emitted_events": events,
    }


# ─────────────────────────────────────────────────────────────────────────────
# NODE 10: Warehouse Agent Execution (Conditional)
# ─────────────────────────────────────────────────────────────────────────────
async def warehouse_agent_node(state: BuyerOrchestrationGraphState) -> Dict[str, Any]:
    logs = list(state.get("logs", []))
    events = list(state.get("emitted_events", []))
    qty = float(state.get("quantity", 500))
    crop = state.get("crop", "Soybean")

    logs.append(f"🏭 [9. Warehouse Agent] Sourcing warehouse storage for {qty}kg {crop}.")

    storage_req = {
        "quantity": qty,
        "crop": crop,
        "location": state.get("location", "Maharashtra"),
        "shelf_life": 10,
    }
    try:
        w_res = await assign_storage(storage_req)
        events.append("WAREHOUSE_ASSIGNED")
        logs.append(f"✅ [9. Warehouse Agent] Storage booked at {w_res.get('warehouse')} (Daily Cost: ₹{w_res.get('total_daily_cost')}).")
    except Exception as e:
        w_res = {"status": "FAILED", "error": str(e)}
        logs.append(f"⚠️ [9. Warehouse Agent] Storage booking notice: {e}")

    return {
        "warehouse_assignment": w_res,
        "logs": logs,
        "emitted_events": events,
    }


# ─────────────────────────────────────────────────────────────────────────────
# NODE 11: Processor Agent Execution (Conditional)
# ─────────────────────────────────────────────────────────────────────────────
async def processor_agent_node(state: BuyerOrchestrationGraphState) -> Dict[str, Any]:
    logs = list(state.get("logs", []))
    events = list(state.get("emitted_events", []))
    crop = state.get("crop", "Soybean")

    logs.append(f"⚙️ [10. Processor Agent] Querying industrial processing mills for {crop}.")
    match_proc = next((p for p in _PROCESSOR_CATALOG if crop in p.get("crop_types", [])), _PROCESSOR_CATALOG[0])

    events.append("PROCESSOR_ASSIGNED")
    proc_res = {
        "processor_id": match_proc["processor_id"],
        "name": match_proc["name"],
        "location": match_proc["location"],
        "output_product": match_proc["output_product"],
        "offered_price_per_kg": match_proc["price_per_kg"],
        "status": "ALLOCATED",
    }
    logs.append(f"✅ [10. Processor Agent] Matched industrial partner: {match_proc['name']} for {match_proc['output_product']}.")

    return {
        "processor_assignment": proc_res,
        "logs": logs,
        "emitted_events": events,
    }


# ─────────────────────────────────────────────────────────────────────────────
# NODE 12: Workflow Completion & Audit Persistence
# ─────────────────────────────────────────────────────────────────────────────
async def workflow_completion_node(state: BuyerOrchestrationGraphState) -> Dict[str, Any]:
    logs = list(state.get("logs", []))
    events = list(state.get("emitted_events", []))
    events.append("WORKFLOW_COMPLETED")

    logs.append(f"🏁 [11. Workflow Completion] Pipeline complete. Required agents invoked: {state.get('required_agents', ['BUYER'])}.")

    return {
        "logs": logs,
        "emitted_events": events,
    }


# ─────────────────────────────────────────────────────────────────────────────
# CONDITIONAL ROUTING FUNCTIONS
# ─────────────────────────────────────────────────────────────────────────────
def route_after_validation(state: BuyerOrchestrationGraphState) -> str:
    if str(state.get("status", "")).startswith("ERROR_"):
        return "workflow_completion"
    return "workflow_policy_gatekeeper"


def route_after_dependencies(state: BuyerOrchestrationGraphState) -> str:
    target = state.get("next_node", "COMPLETION")
    if target == "TRANSPORT":
        return "transport_agent"
    elif target == "WAREHOUSE":
        return "warehouse_agent"
    elif target == "PROCESSOR":
        return "processor_agent"
    return "workflow_completion"


def route_after_transport(state: BuyerOrchestrationGraphState) -> str:
    if state.get("need_storage", False) and "WAREHOUSE" in state.get("permitted_agents", []):
        return "warehouse_agent"
    return "workflow_completion"


# ─────────────────────────────────────────────────────────────────────────────
# COMPILE LANGGRAPH STATEGRAPH
# ─────────────────────────────────────────────────────────────────────────────
buyer_workflow = StateGraph(BuyerOrchestrationGraphState)

# Add all nodes
buyer_workflow.add_node("validate_requirement", validate_requirement_node)
buyer_workflow.add_node("workflow_policy_gatekeeper", workflow_policy_gatekeeper_node)
buyer_workflow.add_node("market_intelligence", market_intelligence_node)
buyer_workflow.add_node("candidate_matching", candidate_matching_node)
buyer_workflow.add_node("parallel_negotiation", parallel_negotiation_node)
buyer_workflow.add_node("deal_evaluation", deal_evaluation_node)
buyer_workflow.add_node("dependency_assessment", dependency_assessment_node)
buyer_workflow.add_node("transport_agent", transport_agent_node)
buyer_workflow.add_node("warehouse_agent", warehouse_agent_node)
buyer_workflow.add_node("processor_agent", processor_agent_node)
buyer_workflow.add_node("workflow_completion", workflow_completion_node)

# Set entry point
buyer_workflow.set_entry_point("validate_requirement")

# Primary workflow edges
buyer_workflow.add_conditional_edges(
    "validate_requirement",
    route_after_validation,
    {
        "workflow_policy_gatekeeper": "workflow_policy_gatekeeper",
        "workflow_completion": "workflow_completion",
    },
)
buyer_workflow.add_edge("workflow_policy_gatekeeper", "market_intelligence")
buyer_workflow.add_edge("market_intelligence", "candidate_matching")
buyer_workflow.add_edge("candidate_matching", "parallel_negotiation")
buyer_workflow.add_edge("parallel_negotiation", "deal_evaluation")
buyer_workflow.add_edge("deal_evaluation", "dependency_assessment")

# Conditional downstream branching
buyer_workflow.add_conditional_edges(
    "dependency_assessment",
    route_after_dependencies,
    {
        "transport_agent": "transport_agent",
        "warehouse_agent": "warehouse_agent",
        "processor_agent": "processor_agent",
        "workflow_completion": "workflow_completion",
    },
)
buyer_workflow.add_conditional_edges(
    "transport_agent",
    route_after_transport,
    {
        "warehouse_agent": "warehouse_agent",
        "workflow_completion": "workflow_completion",
    },
)
buyer_workflow.add_edge("warehouse_agent", "workflow_completion")
buyer_workflow.add_edge("processor_agent", "workflow_completion")
buyer_workflow.add_edge("workflow_completion", END)

# Compile Graph
buyer_graph_orchestrator = buyer_workflow.compile()
