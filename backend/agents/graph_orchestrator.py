"""
backend/agents/graph_orchestrator.py

Stateful LangGraph orchestration engine for AgriNegotiator.
Implements Workflow Planner, Matching Engine, Farmer, Buyer,
Validator, Reflection, Market Intelligence, and Recommendation nodes.
Uses structured LangChain PromptTemplates with JSON output parsing.
RAG context is injected into Farmer and Buyer agent prompts.
"""

import asyncio
import json
import re
import random
import logging
from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END

from llm.llm_client import client as llm_client
from database.db import Database
from backend.core.constants import WorkflowMode
from backend.agents.prompts import (
    PLANNER_PROMPT,
    MATCHING_ENGINE_PROMPT,
    FARMER_PROMPT,
    BUYER_PROMPT,
    VALIDATOR_PROMPT,
    REFLECTION_PROMPT,
    MARKET_INTELLIGENCE_PROMPT,
    RECOMMENDATION_PROMPT,
)
from database.db import Database
from backend.services.external_apis import OpenMeteoClient, MandiAPIClient
from backend.services.matching_service import compute_match_score_sync, compute_match_breakdown_sync

logger = logging.getLogger("GraphOrchestrator")


# ─────────────────────────────────────────────
# Shared LangGraph State
# ─────────────────────────────────────────────

class NegotiationState(TypedDict):
    # Identity & Tracing
    trace_id: Optional[str]
    negotiation_id: Optional[str]            # unique run ID used by transport/storage agents
    stakeholder_role: Optional[str]
    workflow_mode: Optional[str]
    allowed_agent_set: Optional[List[str]]
    permitted_agents: Optional[List[str]]    # downstream logistics scope
    user_id: Optional[str]

    # Core Listing
    crop: str
    quantity: float
    min_price: float
    target_price: float
    spoilage_days: int
    location: str
    market_price: float

    # Farmer Resource Flags (from listing payload)
    has_transport: Optional[bool]            # farmer owns transport → skip Transport Agent
    has_storage: Optional[bool]             # farmer owns storage  → skip Warehouse Agent
    holding_days: Optional[int]             # days buyer needs farmer to hold before pickup
    requires_processing: Optional[bool]     # crop needs value-add processing

    # Negotiation Loop
    round: int
    max_rounds: int
    history: List[Dict[str, Any]]
    buyer_profile: Optional[Dict[str, Any]]
    logs: List[str]
    status: str            # ACTIVE | DEAL | REJECT | ESCALATED_STORAGE | ESCALATED_PROCESSING | ESCALATED_COMPOST | HOLD
    proposed_scenario: str
    next_action: str

    # Agent Objects
    farmer_agent_obj: Optional[Any]
    buyer_agent_objs: Optional[List[Any]]

    # Buyer Matching
    buyers_list: List[Dict[str, Any]]
    active_buyers: List[Dict[str, Any]]
    current_offers: List[Dict[str, Any]]
    best_current_offer: Optional[Dict[str, Any]]
    market_offers: List[Dict[str, Any]]
    selected_buyer: Optional[Dict[str, Any]]
    raw_buyers: Optional[List[Dict[str, Any]]]
    contacted_buyer_ids: Optional[List[str]]
    expansion_count: Optional[int]
    max_candidate_expansions: Optional[int]

    # Negotiation Prices
    latest_farmer_ask: Optional[float]
    latest_buyer_offer: Optional[float]
    net_price: Optional[float]
    net_margin: Optional[float]
    est_transport_cost: Optional[float]
    storage_cost: Optional[float]
    has_transport: Optional[bool]

    # RAG / Intelligence Context
    rag_context: Optional[str]               # Injected market + strategy context
    trust_context: Optional[str]             # Buyer trust profile
    market_intelligence: Optional[str]       # Market analysis output
    market_features: Optional[Dict[str, Any]]
    weather: Optional[Dict[str, Any]]        # Open-Meteo weather data
    live_mandi: Optional[Dict[str, Any]]     # Live Agmarknet mandi price

    # Market Decision
    sell_hold_decision: Optional[str]        # "SELL" | "HOLD"
    sell_hold_reasoning: Optional[str]       # explanation for sell/hold decision

    # Outcomes
    deal: Optional[Dict[str, Any]]
    supply_chain_booking: Optional[Dict[str, Any]]  # final transport + storage plan
    plan: Optional[str]
    reflection: Optional[str]
    recommendation: Optional[str]           # Recommendation agent output


# ─────────────────────────────────────────────
# Helper: safe JSON parse from LLM output
# ─────────────────────────────────────────────

async def _parse_json_response(text: str) -> Optional[Dict]:
    """Extract first valid JSON object from LLM response."""
    if not text:
        return None
    try:
        # Strip markdown fences if present
        cleaned = re.sub(r"```(?:json)?", "", text).strip()
        m = re.search(r"\{.*\}", cleaned, re.DOTALL)
        if m:
            return json.loads(m.group())
    except (json.JSONDecodeError, Exception):
        pass
    return None




async def _build_rag_context(crop: str, location: str, market_price: float = 0.0) -> str:
    """Query ChromaDB and relational database for a comprehensive market context."""
    context_parts = []
    
    try:
        from backend.services.market_intelligence import MarketIntelligenceService
        # M1 fix: use the actual market_price from state instead of the undefined local variable
        historical_avg = market_price if market_price > 0 else 23.5
        mis_context = await MarketIntelligenceService.get_market_context(crop, location, historical_avg)
        context_parts.append(mis_context)
    except Exception as ex:
        logger.warning(f"Failed to fetch MIS context: {ex}")

    # 1. Fetch structured facts from Database
    try:
        # a. MSP Price
        msp = Database.get_msp_price(crop)
        if msp:
            context_parts.append(f"Official Government MSP (2026-27) for {crop}: ₹{msp:.2f}/quintal (₹{msp/100:.2f}/kg).")

        # b. Market Mapping
        mappings = Database.get_market_mappings(location)
        if mappings:
            markets_str = ", ".join([m["market_name"] for m in mappings])
            context_parts.append(f"Associated APMC mandis for {location} district: {markets_str}.")

        # c. Seasonal Calendar
        from datetime import datetime
        current_month = datetime.now().strftime("%B").lower()
        calendar_events = Database.get_seasonal_calendar()
        matching_events = []
        for event in calendar_events:
            if current_month in event["month_range"].lower() or any(crop.lower() in c.lower() for c in event["affected_crops"].split(",")):
                matching_events.append(
                    f"  - {event['event_name']} ({event['month_range']}): Trend: {event['price_impact_trend']}. "
                    f"Behavior: {event['market_behavior_description']}"
                )
        if matching_events:
            context_parts.append("Seasonal Market Activity Warnings:\n" + "\n".join(matching_events))
    except Exception as ex:
        logger.warning(f"Failed to fetch structured database facts: {ex}")

    # 2. Fetch live Weather from Open-Meteo API
    try:
        import urllib.request
        # Coordinates map for Maharashtra districts
        coords = {
            "Pune": (18.52, 73.85),
            "Nashik": (19.99, 73.78),
            "Nagpur": (21.14, 79.08),
            "Jalgaon": (21.00, 75.56),
            "Ahmednagar": (19.09, 74.74),
            "Satara": (17.68, 73.98),
            "Latur": (18.40, 76.56),
            "Thane": (19.22, 72.98),
            "Mumbai": (19.07, 72.87),
            "Amravati": (20.93, 77.75),
            "Kolhapur": (16.70, 74.24),
            "Aurangabad": (19.88, 75.34),
            "Sangli": (16.85, 74.58),
            "Dhule": (20.90, 74.77)
        }
        lat, lon = coords.get(location, (19.07, 72.87)) # Default to Mumbai
        url = f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}&current_weather=true"
        req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=3) as resp:
            w_data = json.loads(resp.read().decode('utf-8'))
            current = w_data.get("current_weather", {})
            temp = current.get("temperature")
            wind = current.get("windspeed")
            context_parts.append(f"Live Weather for {location} district: Temp {temp}°C, Wind Speed {wind} km/h (Source: Open-Meteo).")
    except Exception as ex:
        logger.warning(f"Failed to retrieve live weather data: {ex}")

    # 3. Query RAG vector store for unstructured documents
    try:
        from backend.services.rag_service import rag_service
        query = f"{crop} market price {location}"

        # Mandi prices
        mandi_results = rag_service.query_mandi_records(query, n_results=2)
        if mandi_results and mandi_results.get("documents"):
            docs = mandi_results["documents"][0]
            if docs:
                context_parts.append("Recent APMC Mandi price transactions:\n" + "\n".join([f"  - {d}" for d in docs]))

        # Historical negotiation logs (RL Memory)
        strategy_results = rag_service.query_strategies(query, n_results=3)
        if strategy_results and strategy_results.get("documents"):
            docs = strategy_results["documents"][0]
            metadatas = strategy_results.get("metadatas", [[]])[0]
            if docs:
                strategy_lines = []
                for idx, d in enumerate(docs):
                    m = metadatas[idx] if metadatas and len(metadatas) > idx else {}
                    farmer_reward = m.get("farmer_reward", "N/A")
                    buyer_reward = m.get("buyer_reward", "N/A")
                    strategy_lines.append(f"  - [Reward: Farmer={farmer_reward}, Buyer={buyer_reward}] {d}")
                context_parts.append("Past Negotiation Strategies (RL Feedback):\n" + "\n".join(strategy_lines))

        # Crop Knowledge Base
        knowledge_results = rag_service.query_crop_knowledge(
            query_text=f"{crop} cultivation practices diseases harvesting shelf-life",
            crop=crop,
            n_results=1
        )
        if knowledge_results:
            context_parts.append("Agronomic Crop Guidelines (ICAR):\n" + "\n".join([f"  - {k['text']}" for k in knowledge_results]))

        # Government Schemes (Insurance, etc.)
        schemes_results = rag_service.query_government_schemes(
            query_text=f"PMFBY crop insurance premium rate sum insured claim {crop}",
            n_results=1
        )
        if schemes_results:
            context_parts.append("Government Scheme Guidelines (PMFBY):\n" + "\n".join([f"  - {s['text']}" for s in schemes_results]))

    except Exception as e:
        logger.warning(f"RAG document search failed: {e}")

    return "\n\n".join(context_parts) if context_parts else "No historical context available."


def _format_history(history: List[Dict]) -> str:
    """Convert history list to readable string."""
    if not history:
        return "No rounds yet."
    lines = []
    for h in history:
        lines.append(
            f"  Round {h.get('round', '?')} - {h.get('agent', '?')}:\n"
            f"    Message: \"{h.get('message', 'No message')}\"\n"
            f"    Offer: ₹{h.get('price', 0)}/kg ({h.get('decision', 'COUNTER')})\n"
            f"    Reasoning: {h.get('reason', 'N/A')}\n"
        )
    return "\n".join(lines)


# ─────────────────────────────────────────────
# Node 1: Workflow Planner
# ─────────────────────────────────────────────

async def planner_node(state: NegotiationState) -> Dict[str, Any]:
    logs = list(state.get("logs", []))
    logs.append("📋 [Planner] Initiating negotiation workflow planner.")

    workflow_mode = state.get("workflow_mode", WorkflowMode.FULL_SUPPLY_CHAIN)
    stakeholder_role = state.get("stakeholder_role", "FARMER")
    
    from backend.core.constants import get_allowed_agents
    allowed_agents = get_allowed_agents(stakeholder_role, workflow_mode)
    
    logs.append(f"📋 [Planner] Workflow Mode: {workflow_mode}")
    logs.append(f"📋 [Planner] Stakeholder: {stakeholder_role}")
    logs.append(f"📋 [Planner] Allowed Agents: {', '.join(allowed_agents)}")

    # Fetch RAG context early — shared across all downstream agents
    # M1 fix: pass the actual market_price so MIS context uses real data
    rag_context = await _build_rag_context(state["crop"], state["location"], market_price=state.get("market_price", 0.0))

    prompt = PLANNER_PROMPT.format(
        crop=state["crop"],
        quantity=state["quantity"],
        min_price=state["min_price"],
        location=state["location"],
        shelf_life=state["spoilage_days"],
        market_price=state.get("market_price", 0.0)
    )

    plan_text = await asyncio.to_thread(llm_client.generate, prompt, max_tokens=200)
    if not plan_text:
        plan_text = (
            f"Strategy: Target bulk and premium buyers in {state['location']} "
            f"for {state['crop']}. Shelf-life={state['spoilage_days']} days. "
            f"Spoilage risk={'HIGH' if state['spoilage_days'] <= 3 else 'MEDIUM' if state['spoilage_days'] <= 7 else 'LOW'}. "
            f"Opening target ₹{round(state['min_price'] * 1.2, 2)}/kg."
        )

    logs.append(f"📋 [Planner] Strategy: {plan_text.strip()[:120]}...")
    return {
        "plan": plan_text.strip(),
        "logs": logs,
        "round": 0,
        "status": "ACTIVE",
        "rag_context": rag_context,
        "allowed_agent_set": allowed_agents,
    }


# ─────────────────────────────────────────────
# Node 1.5: Knowledge Manager (Live External Data)
# ─────────────────────────────────────────────

async def knowledge_manager_node(state: NegotiationState) -> Dict[str, Any]:
    """
    Knowledge Manager Node:
    Acquires real-time external data (Open-Meteo weather and Agmarknet mandi feeds)
    to enrich negotiation state before Market Intelligence analysis.
    """
    logs = list(state.get("logs", []))
    updates: Dict[str, Any] = {}

    loc = state.get("location", "")
    crop = state.get("crop", "")

    # 1. Real-time Weather Feed (Open-Meteo)
    if not state.get("weather") and loc:
        try:
            weather = await OpenMeteoClient.get_weather(loc)
            if weather:
                updates["weather"] = weather
                res_loc = weather.get("location_resolved") or loc
                temp = weather.get("temperature_c", "?")
                rain = weather.get("precipitation_mm", 0)
                logs.append(f"🌦️ [Knowledge Manager] Weather feed active for {res_loc}: {temp}°C, {rain}mm rain.")
        except Exception as e:
            logger.debug(f"[Knowledge Manager] Weather fetch skipped/failed: {e}")

    # 2. Real-time Mandi Feed (Agmarknet APMC)
    if not state.get("live_mandi") and crop and loc:
        try:
            mandi = await MandiAPIClient.get_live_price(crop, loc, state.get("market_price", 0.0))
            if mandi and mandi.get("status") != "UNAVAILABLE":
                updates["live_mandi"] = mandi
                modal_price = mandi.get("live_modal_price") or mandi.get("modal_price", "?")
                trend = mandi.get("trend", "Stable")
                logs.append(f"📈 [Knowledge Manager] Mandi feed active for {crop} at {mandi.get('mandi', 'APMC')}: ₹{modal_price}/kg ({trend}).")
        except Exception as e:
            logger.debug(f"[Knowledge Manager] Mandi fetch skipped/failed: {e}")

    updates["logs"] = logs
    return updates

# ─────────────────────────────────────────────
# Node 2: Market Intelligence
# ─────────────────────────────────────────────

async def market_intelligence_node(state: NegotiationState) -> Dict[str, Any]:
    logs = list(state.get("logs", []))
    logs.append("📊 [Market Intelligence] Analyzing live market conditions.")
    
    # Format weather data safely
    weather = state.get("weather")
    if weather:
        weather_str = f"Live Weather in {weather['location_resolved']}: {weather['temperature_c']}°C, {weather['precipitation_mm']}mm rain, {weather['wind_speed_kmh']}km/h wind."
    else:
        weather_str = f"Location: {state['location']}. Weather data unavailable."
        
    # Format mandi data safely
    mandi = state.get("live_mandi")
    if mandi:
        mandi_str = f"Live Agmarknet Price at {mandi['mandi']}: ₹{mandi['live_modal_price']}/kg ({mandi['trend']}, volatility: {mandi['volatility_pct']}%)."
    else:
        mandi_str = "No mandi data available."

    prompt = MARKET_INTELLIGENCE_PROMPT.format(
        crop=state["crop"],
        location=state["location"],
        season="Kharif" if state["spoilage_days"] <= 90 else "Rabi",
        mandi_data=mandi_str + "\n" + state.get("rag_context", ""),
        weather_data=weather_str
    )

    analysis = await asyncio.to_thread(llm_client.generate, prompt, max_tokens=200)
    if not analysis:
        # Fallback deterministic analysis
        if state["market_price"] > state["min_price"] * 1.1:
            analysis = f"Market is bullish for {state['crop']}. Recommended band: ₹{round(state['market_price'] * 0.9, 2)} - ₹{round(state['market_price'] * 1.15, 2)}/kg."
        else:
            analysis = f"Market is at par for {state['crop']}. Recommended band: ₹{state['min_price']} - ₹{round(state['market_price'] * 1.05, 2)}/kg."

    # Pillar 4: Market Intelligence -> Real XGBoost Forecast + Sell/Hold Analysis
    from backend.services.price_prediction_service import predict_price_xgboost
    ml_result = predict_price_xgboost(
        crop=state["crop"],
        location=state["location"],
        current_modal_price=state["market_price"],
        days_ahead=7
    )
    forecast_price = ml_result["forecast_price"]
    ml_summary = ml_result["summary"]
    logs.append(f"🤖 [ML Intelligence] {ml_summary}")

    if not weather:
        weather_risk = "UNKNOWN"
        weather_source = "FALLBACK"
    else:
        weather_source = "LIVE_OPEN_METEO"
        precip = float(weather.get("precipitation_mm", 0))
        if precip >= 15:
            weather_risk = "High"
        elif precip >= 5:
            weather_risk = "Moderate"
        else:
            weather_risk = "Low"

    shelf_life = state.get("spoilage_days", 10)
    
    # Check if explicit HOLD requested by farmer or indicated by significant upside
    explicit_decision = state.get("sell_hold_decision")
    if explicit_decision in ["HOLD", "SELL"]:
        sell_hold = explicit_decision
        sell_hold_reason = f"Explicit farmer directive: {sell_hold} lot."
    elif forecast_price > state["market_price"] * 1.05 and weather_risk == "Low" and shelf_life > 7:
        sell_hold = "HOLD"
        sell_hold_reason = (
            f"Current Market: ₹{state['market_price']}/kg | 7-day XGBoost Forecast: ₹{forecast_price}/kg | "
            f"Trend: Increasing | Weather Risk: {weather_risk} ({weather_source}). Holding may yield higher returns subject to storage."
        )
    else:
        sell_hold = "SELL"
        if weather_risk == "UNKNOWN":
            sell_hold_reason = (
                f"Current Market: ₹{state['market_price']}/kg is favorable. Weather data is UNKNOWN ({weather_source}); "
                f"prompt execution minimizes unmonitored transit/holding risk."
            )
        else:
            sell_hold_reason = (
                f"Current Market: ₹{state['market_price']}/kg is favorable. Prompt execution minimizes spoilage risk."
            )
    
    logs.append(f"📈 [Market Intelligence][Sell/Hold Decision]: {sell_hold} — {sell_hold_reason}")

    return {
        "market_intelligence": analysis,
        "sell_hold_decision": sell_hold,
        "sell_hold_reasoning": sell_hold_reason,
        "logs": logs,
    }


# ─────────────────────────────────────────────
# Node 3: Matching Engine
# ─────────────────────────────────────────────

async def matching_engine_node(state: NegotiationState) -> Dict[str, Any]:
    logs = list(state.get("logs", []))
    logs.append("📡 [Matching Engine] Querying suitable buyer profiles.")

    state_buyers = state.get("buyers_list", [])
    db_buyers = state_buyers if state_buyers else await Database.list_buyers_async()

    raw_buyers = []
    for b in db_buyers:
        if isinstance(b, dict):
            raw_buyers.append(b)
        else:
            raw_buyers.append({
                "id": getattr(b, "id", f"buyer_{getattr(b, 'name', 'default').lower()}"),
                "name": getattr(b, "name", "Buyer"),
                "target_price": getattr(b, "target_price", state["min_price"]),
                "budget": getattr(b, "budget", 100000.0),
                "max_quantity": getattr(b, "max_quantity", state["quantity"]),
                "location": getattr(b, "location", "Market"),
                "strategy": getattr(b, "strategy", "default")
            })

    market_offers = []
    for profile in raw_buyers:
        if profile.get("kind") == "offer":
            continue
        offered_qty = min(state["quantity"], float(profile.get("max_quantity", state["quantity"])))
        budget_limited_price = float(profile.get("budget", 0)) / max(offered_qty, 1)

        target_price_clean = float(profile.get("target_price") if profile.get("target_price") is not None else state.get("min_price", 0.0))
        market_price_clean = float(state.get("market_price") if state.get("market_price") is not None else target_price_clean)

        strategy = (profile.get("strategy") or "").lower()
        if profile.get("offered_price") is not None:
            opening_bid = min(float(profile["offered_price"]), budget_limited_price)
        elif "restaurant" in strategy or "premium" in strategy:
            opening_bid = min(target_price_clean, budget_limited_price)
        else:
            opening_bid = min(
                target_price_clean,
                budget_limited_price,
                market_price_clean + 3.0
            )

        offer_price = round(max(1.0, opening_bid), 2)
        is_viable = offer_price >= state["min_price"]

        # Canonical 8-factor NRV matching formula with per-factor explainability
        match_info = compute_match_breakdown_sync(
            listing={
                "min_price": state["min_price"],
                "quantity": state["quantity"],
                "location": state.get("location", ""),
                "crop": state.get("crop", ""),
                "grade": state.get("grade", "A"),
                "spoilage_days": state.get("spoilage_days", 14),
            },
            requirement={
                "target_price": target_price_clean,
                "max_price": float(profile.get("max_price") or budget_limited_price),
                "quantity": offered_qty,
                "location": profile.get("location", "Market"),
                "grade": profile.get("grade") or profile.get("quality_grade") or "A",
                "urgency": profile.get("urgency", "NORMAL"),
                "budget": float(profile.get("budget", 0)),
            },
            buyer_user={
                "trust_score": float(profile.get("trust_score", 4.5 if profile.get("verified") else 3.5)),
                "verified": bool(profile.get("verified", False)),
            },
        )
        canonical_score = match_info["total_score"]
        factor_breakdown = match_info["factor_breakdown"]

        distance_penalty = 0 if profile.get("location") == state["location"] else 0.2
        legacy_score = round(
            (offer_price - distance_penalty) * 100
            + (20.0 if profile.get("verified") else 0.0),
            2
        )

        market_offers.append({
            "buyer_id": profile.get("id"),
            "buyer_name": profile.get("name"),
            "location": profile.get("location", "Market"),
            "strategy": profile.get("strategy", "Market Option"),
            "offered_price": offer_price,
            "offered_quantity": round(offered_qty, 2),
            "budget": float(profile.get("budget", 0)),
            "target_price": target_price_clean,
            "status": "VIABLE" if is_viable else "BELOW_MIN_PRICE",
            "score": canonical_score,
            "match_score": canonical_score,
            "factor_breakdown": factor_breakdown,
            "legacy_score": legacy_score,
        })

    market_offers.sort(
        key=lambda item: (item["status"] == "VIABLE", item["score"], item["offered_price"]),
        reverse=True
    )

    if market_offers:
        top_cand = market_offers[0]
        fb = top_cand.get("factor_breakdown", {})
        logs.append(
            f"🎯 [Matching Engine] Top Candidate '{top_cand['buyer_name']}' compatibility: {top_cand['score']}/100 "
            f"[Price: {fb.get('price_feasibility')}/20, Qty: {fb.get('quantity_fulfillment')}/20, "
            f"Dist: {fb.get('distance_proximity')}/15, Trust: {fb.get('trust_reliability')}/15, "
            f"Grade: {fb.get('quality_grade')}/10, Spoilage: {fb.get('spoilage_urgency')}/10, "
            f"Transport: {fb.get('transport_efficiency')}/5, Storage: {fb.get('storage_efficiency')}/5]"
        )

    active_buyers = []
    current_offers = []
    for best in market_offers[:5]:  # Top 5 buyers for parallel negotiation
        raw_b = next((b for b in raw_buyers if b.get("id") == best["buyer_id"] or b.get("name") == best["buyer_name"]), None)
        if raw_b:
            buyer = dict(raw_b)
            buyer["score"] = best["score"]
            buyer["factor_breakdown"] = best.get("factor_breakdown", {})
            active_buyers.append(buyer)
            initial_offer = best.get("offered_price") or round(buyer.get("target_price", state["min_price"]), 2)
            current_offers.append({
                "buyer_id": buyer["id"],
                "buyer_name": buyer.get("name", "Buyer"),
                "price": initial_offer,
                "status": "COUNTER"
            })

    if not active_buyers and raw_buyers:
        b = raw_buyers[0]
        active_buyers.append(b)
        initial_offer = round(b.get("target_price", state["min_price"]), 2)
        current_offers.append({
            "buyer_id": b["id"],
            "buyer_name": b.get("name", "Buyer"),
            "price": initial_offer,
            "status": "COUNTER"
        })

    if not active_buyers:
        b = {
            "id": "buyer_default",
            "name": "Marketplace Aggregator",
            "target_price": state["min_price"] * 1.1,
            "budget": state["min_price"] * state["quantity"] * 1.3,
            "max_quantity": state["quantity"],
            "location": state["location"],
            "strategy": "default"
        }
        active_buyers.append(b)
        current_offers.append({
            "buyer_id": b["id"],
            "buyer_name": b["name"],
            "price": round(b["target_price"], 2),
            "status": "COUNTER"
        })

    buyer_names = ", ".join([b.get("name", "Buyer") for b in active_buyers])
    logs.append(f"🎯 [Matching Engine] Matched Top {len(active_buyers)} Buyers: {buyer_names}")

    farmer_obj = state.get("farmer_agent_obj")
    initial_farmer_ask = float(getattr(farmer_obj, "current_price", 0)) or round(state["min_price"] * 1.2, 2)
    best_initial = max(current_offers, key=lambda x: x["price"]) if current_offers else None

    return {
        "active_buyers": active_buyers,
        "current_offers": current_offers,
        "best_current_offer": best_initial,
        "buyer_profile": active_buyers[0] if active_buyers else None,
        "selected_buyer": active_buyers[0] if active_buyers else None,
        "latest_buyer_offer": best_initial["price"] if best_initial else None,
        "latest_farmer_ask": initial_farmer_ask,
        "market_offers": market_offers,
        "raw_buyers": raw_buyers,
        "contacted_buyer_ids": [b.get("id") for b in active_buyers if b.get("id")],
        "expansion_count": 0,
        "logs": logs,
    }


# ─────────────────────────────────────────────
# Node 4: Farmer Agent
# ─────────────────────────────────────────────

async def farmer_node(state: NegotiationState) -> Dict[str, Any]:
    from backend.agents.stakeholders.farmer_agent import FarmerAgent
    
    farmer = FarmerAgent()
    return await farmer(state)


# ─────────────────────────────────────────────
# Node 5: Buyer Agent
# ─────────────────────────────────────────────

async def buyer_node(state: NegotiationState) -> Dict[str, Any]:
    logs = list(state.get("logs", []))
    history = list(state.get("history", []))
    current_round = state.get("round", 0)

    farmer_ask = state.get("latest_farmer_ask", round(state["min_price"] * 1.2, 2))
    buyer_agents = list(state.get("buyer_agent_objs") or [])
    
    if not buyer_agents:
        candidate_buyers = state.get("active_buyers") or []
        if not candidate_buyers and state.get("buyer_profile"):
            candidate_buyers = [state.get("buyer_profile")]
        elif not candidate_buyers and state.get("selected_buyer"):
            candidate_buyers = [state.get("selected_buyer")]

        from agents.buyer_agent import BuyerAgent
        from shared.crop_catalog import is_supported_buyer_crop

        for b in candidate_buyers:
            if not isinstance(b, dict):
                continue
            b_name = b.get("name") or b.get("buyer_name") or "Buyer"
            b_budget = float(b.get("budget", 100000.0) or 100000.0)
            b_qty = float(b.get("max_quantity", state.get("quantity", 100.0)) or state.get("quantity", 100.0))
            b_target = float(b.get("target_price", state.get("min_price", 20.0)) or state.get("min_price", 20.0))
            b_loc = b.get("location", state.get("location"))
            b_strat = b.get("strategy") or "balanced"
            b_crop = state.get("crop") if is_supported_buyer_crop(state.get("crop")) else None

            b_obj = BuyerAgent(
                name=b_name,
                budget=b_budget,
                max_quantity=b_qty,
                target_price=b_target,
                location=b_loc,
                strategy=b_strat,
                crop=b_crop,
                agent_id=b.get("id", f"buyer_{b_name}")
            )
            b_obj.id = b.get("id", f"buyer_{b_name}")
            buyer_agents.append(b_obj)

    logs.append(f"🤝 [Buyers Pool] Round {current_round}: Evaluating Farmer ask of ₹{farmer_ask}/kg")
    
    current_offers = []

    if not buyer_agents:
        logs.append("⚠️ [Buyers Pool] No BuyerAgent objects found in state! Aborting.")
        return {"history": history, "current_offers": [], "logs": logs}
    
    # Auto-resolve legitimate market features from real APMC dataset if not already in graph state
    resolved_features = state.get("market_features")
    feature_meta = None
    if not resolved_features and state.get("crop"):
        try:
            from backend.services.buyer_pricing_service import get_buyer_pricing_service
            pricing_svc = get_buyer_pricing_service()
            if pricing_svc:
                resolved_features, feature_meta = pricing_svc.get_market_features(
                    state.get("crop"), state.get("location")
                )
        except Exception as ex:
            logger.debug(f"Could not auto-resolve market features in buyer_node: {ex}")

    # Pre-resolve shared base market context for this round once to avoid redundant I/O
    base_context_payload = {
        "market_price": state["market_price"],
        "round": current_round,
        "crop": state.get("crop"),
        "location": state.get("location"),
    }
    if resolved_features:
        base_context_payload["market_features"] = resolved_features
        if feature_meta:
            base_context_payload["feature_source"] = feature_meta

    # Retrieve current daily mandi price observation once for this round
    try:
        from backend.services.current_mandi_service import current_mandi_service
        c_mandi_data = current_mandi_service.get_current_market_price(
            crop=state.get("crop"),
            location=state.get("location")
        )
        if c_mandi_data.get("success", False):
            base_context_payload["current_mandi_data"] = c_mandi_data
    except Exception as ex:
        logger.debug(f"Could not fetch current_mandi_data in graph_orchestrator: {ex}")

    # Pre-assemble unified composite BuyerMarketContext once per round
    try:
        from backend.services.buyer_market_context_service import buyer_market_context_service
        base_market_ctx = buyer_market_context_service.build_market_context(
            crop=state.get("crop", ""),
            location=state.get("location"),
            persona="custom",
            context=base_context_payload,
        )
        base_context_payload["buyer_market_context"] = base_market_ctx
    except Exception as ex:
        logger.debug(f"Could not assemble buyer_market_context in graph_orchestrator: {ex}")

    import time

    async def _evaluate_single_buyer(buyer):
        buyer_name = buyer.name
        t_start = time.time()
        contacted_at = round(t_start, 4)

        offer_payload = {"price": farmer_ask, "quantity": state["quantity"], "crop": state.get("crop")}
        context_payload = dict(base_context_payload)

        # Retrieve purpose-built Buyer RAG context if specific persona exists
        buyer_persona = getattr(buyer, "persona", None)
        if buyer_persona and buyer_persona != "custom":
            try:
                from backend.services.buyer_rag_service import buyer_rag_service
                b_rag_ctx = buyer_rag_service.get_buyer_context(
                    crop=state.get("crop"),
                    location=state.get("location"),
                    persona=buyer_persona
                )
                if not b_rag_ctx.is_empty:
                    context_payload["buyer_rag_context"] = b_rag_ctx
                    from backend.services.buyer_market_context_service import buyer_market_context_service
                    context_payload["buyer_market_context"] = buyer_market_context_service.build_market_context(
                        crop=state.get("crop", ""),
                        location=state.get("location"),
                        persona=buyer_persona,
                        context=context_payload,
                    )
            except Exception as ex:
                logger.debug(f"Could not fetch persona buyer_rag_context in graph_orchestrator: {ex}")

        import inspect
        res = buyer.respond_to_offer(offer_payload, context=context_payload)
        response = await res if inspect.isawaitable(res) else res

        t_end = time.time()
        duration_ms = round((t_end - t_start) * 1000, 2)
        responded_at = round(t_end, 4)

        decision_type = response.get("type", "REJECT")
        counter_price = response.get("price", farmer_ask)
        message = response.get("message", "")
        buyer_id = buyer.id if hasattr(buyer, "id") else f"buyer_{buyer_name}"

        return {
            "buyer": buyer,
            "buyer_id": buyer_id,
            "buyer_name": buyer_name,
            "decision_type": decision_type,
            "counter_price": counter_price,
            "message": message,
            "contacted_at": contacted_at,
            "responded_at": responded_at,
            "duration_ms": duration_ms,
            "last_ml_prediction": getattr(buyer, "last_ml_prediction", None),
        }

    # Execute all shortlisted buyer evaluations concurrently via asyncio.gather
    t_parallel_start = time.time()
    buyer_evaluations = await asyncio.gather(*[_evaluate_single_buyer(b) for b in buyer_agents])
    t_parallel_duration = round((time.time() - t_parallel_start) * 1000, 2)
    logs.append(f"⚡ [Buyers Pool] Concurrent parallel evaluation of {len(buyer_agents)} buyer(s) completed in {t_parallel_duration}ms.")

    for ev in buyer_evaluations:
        buyer_name = ev["buyer_name"]
        buyer_id = ev["buyer_id"]
        decision_type = ev["decision_type"]
        counter_price = ev["counter_price"]
        message = ev["message"]
        contacted_at = ev["contacted_at"]
        responded_at = ev["responded_at"]
        duration_ms = ev["duration_ms"]

        # Log ML prediction anchor if utilized
        if ev.get("last_ml_prediction") and ev["last_ml_prediction"].get("audit_status") == "ML_USED":
            pred_p = ev["last_ml_prediction"]["predicted_modal_price"]
            src_desc = ev["last_ml_prediction"].get("feature_source", {}).get("match_level", "APMC historical")
            logs.append(f"🧠 [{buyer_name}] ML Market Anchor: ₹{pred_p}/kg (Source: {src_desc})")

        logs.append(f"🤝 [{buyer_name}] {decision_type} ₹{counter_price}/kg: {message} ({duration_ms}ms)")

        if decision_type == "ACCEPT":
            history.append({
                "round": current_round,
                "agent": buyer_name,
                "agent_id": buyer_id,
                "price": farmer_ask,
                "decision": "ACCEPT",
                "quantity": state["quantity"],
                "message": message or f"Accepted ask at ₹{farmer_ask}/kg",
                "reason": message,
            })
            current_offers.append({
                "buyer_id": buyer_id, 
                "buyer_name": buyer_name, 
                "price": farmer_ask, 
                "status": "ACCEPT", 
                "message": message,
                "contacted_at": contacted_at,
                "responded_at": responded_at,
                "duration_ms": duration_ms,
                "execution_mode": "PARALLEL_ASYNCIO",
            })
        elif decision_type == "REJECT":
            history.append({
                "round": current_round,
                "agent": buyer_name,
                "agent_id": buyer_id,
                "price": farmer_ask,
                "decision": "REJECT",
                "quantity": state["quantity"],
                "message": message or "Buyer rejected ask.",
                "reason": message,
            })
            current_offers.append({
                "buyer_id": buyer_id, 
                "buyer_name": buyer_name, 
                "price": farmer_ask, 
                "status": "REJECT", 
                "message": message,
                "contacted_at": contacted_at,
                "responded_at": responded_at,
                "duration_ms": duration_ms,
                "execution_mode": "PARALLEL_ASYNCIO",
            })
        else:
            history.append({
                "round": current_round,
                "agent": buyer_name,
                "agent_id": buyer_id,
                "price": counter_price,
                "decision": "COUNTER",
                "quantity": state["quantity"],
                "message": message,
                "reason": message,
            })
            current_offers.append({
                "buyer_id": buyer_id, 
                "buyer_name": buyer_name, 
                "price": counter_price, 
                "status": "COUNTER",
                "contacted_at": contacted_at,
                "responded_at": responded_at,
                "duration_ms": duration_ms,
                "execution_mode": "PARALLEL_ASYNCIO",
            })

    result = {
        "history": history,
        "current_offers": current_offers,
        "logs": logs,
        "buyer_agent_objs": buyer_agents,
        "parallel_eval_duration_ms": t_parallel_duration,
    }
    if resolved_features:
        result["market_features"] = resolved_features
    return result


# ─────────────────────────────────────────────
# Node 5.5: Rank Responses Node (Net Farmer Margin)
# ─────────────────────────────────────────────

CITY_DISTANCES_KM: Dict[str, Dict[str, float]] = {
    "Nashik":     {"Nashik": 0, "Pune": 210, "Mumbai": 170, "Nagpur": 450, "Kalyan": 180, "Thane": 165},
    "Pune":       {"Nashik": 210, "Pune": 0, "Mumbai": 150, "Nagpur": 580, "Kalyan": 130, "Thane": 145},
    "Mumbai":     {"Nashik": 170, "Pune": 150, "Mumbai": 0, "Nagpur": 830, "Kalyan": 55, "Thane": 40},
    "Nagpur":     {"Nashik": 450, "Pune": 580, "Mumbai": 830, "Nagpur": 0, "Kalyan": 800, "Thane": 795},
    "Kalyan":     {"Nashik": 180, "Pune": 130, "Mumbai": 55, "Nagpur": 800, "Kalyan": 0, "Thane": 20},
    "Thane":      {"Nashik": 165, "Pune": 145, "Mumbai": 40, "Nagpur": 795, "Kalyan": 20, "Thane": 0},
    "Aurangabad": {"Nashik": 190, "Pune": 230, "Mumbai": 340, "Nagpur": 330, "Kalyan": 300, "Thane": 310},
    "Satara":     {"Nashik": 270, "Pune": 110, "Mumbai": 255, "Nagpur": 690, "Kalyan": 210, "Thane": 225},
    "Ahmednagar": {"Nashik": 120, "Pune": 120, "Mumbai": 275, "Nagpur": 570, "Kalyan": 245, "Thane": 260},
}


def estimate_distance_km(loc_a: str, loc_b: str) -> float:
    """Estimates road transit distance (km) between Maharashtra districts/APMCs."""
    if not loc_a or not loc_b:
        return 0.0
    a = loc_a.strip().title()
    b = loc_b.strip().title()
    if a.lower() == b.lower():
        return 0.0
    dist = CITY_DISTANCES_KM.get(a, {}).get(b)
    if dist is None:
        dist = CITY_DISTANCES_KM.get(b, {}).get(a)
    return float(dist) if dist is not None else 150.0


def compute_net_farmer_margin(
    offer: Dict[str, Any],
    state: NegotiationState,
) -> Dict[str, Any]:
    """
    Computes Net Farmer Margin (Take-Home Realization) for a candidate buyer offer:
      Gross Revenue = Offered Price * Quantity
      Est. Freight = (Distance_km * ₹3.0/tonne-km * Quantity) / 1000.0
      Storage Cost = state.get('storage_cost', 0.0)
      Net Farmer Margin = Gross Revenue - Est. Freight - Storage Cost
      Net Price per kg = Net Farmer Margin / Quantity
    """
    qty = float(state.get("quantity", 1000.0) or 1000.0)
    nominal_price = float(offer.get("price", 0.0) or 0.0)
    farmer_loc = state.get("location", "")
    has_transport = bool(state.get("has_transport", False))

    buyer_id = offer.get("buyer_id")
    buyer = None
    if buyer_id:
        for pool in (state.get("active_buyers", []), state.get("market_offers", []), state.get("raw_buyers", [])):
            if pool:
                buyer = next((b for b in pool if b.get("id") == buyer_id or b.get("buyer_id") == buyer_id), None)
                if buyer:
                    break

    buyer_loc = ""
    dist_km = 0.0
    if buyer:
        buyer_loc = buyer.get("location", "")
        if "distance_km" in buyer and buyer["distance_km"] is not None:
            dist_km = float(buyer["distance_km"])
        elif "distance" in buyer and buyer["distance"] is not None:
            dist_km = float(buyer["distance"])

    if not dist_km and buyer_loc and farmer_loc and not has_transport:
        dist_km = estimate_distance_km(farmer_loc, buyer_loc)

    if has_transport or not buyer_loc or not farmer_loc:
        dist_km = 0.0
        est_transport_cost = 0.0
    else:
        est_transport_cost = (dist_km * 3.0 * qty) / 1000.0

    storage_cost = float(state.get("storage_cost", 0.0) or (buyer.get("storage_cost", 0.0) if buyer else 0.0) or 0.0)
    gross_revenue = nominal_price * qty
    net_margin = gross_revenue - est_transport_cost - storage_cost
    net_price_per_kg = round(net_margin / qty, 2) if qty > 0 else nominal_price

    return {
        "nominal_price": nominal_price,
        "quantity": qty,
        "distance_km": round(dist_km, 1),
        "est_transport_cost": round(est_transport_cost, 2),
        "storage_cost": round(storage_cost, 2),
        "gross_revenue": round(gross_revenue, 2),
        "net_margin": round(net_margin, 2),
        "net_price": net_price_per_kg,
    }


async def rank_responses_node(state: NegotiationState) -> Dict[str, Any]:
    logs = list(state.get("logs", []))
    current_offers = state.get("current_offers", [])
    
    if not current_offers:
        logs.append("⚠️ [Ranker] No current offers to rank. Rejecting.")
        return {"status": "REJECT", "logs": logs}
        
    logs.append("⚖️ [Ranker] Evaluating buyer responses against Net Farmer Margin...")

    # Enrich each offer with Net Farmer Margin economics
    for o in current_offers:
        margin_info = compute_net_farmer_margin(o, state)
        o.update(margin_info)
    
    current_round = state.get("round", 0) + 1

    # 1. Did anyone accept?
    accepts = [o for o in current_offers if o["status"] == "ACCEPT"]
    if accepts:
        # Rank by Net Farmer Margin, tie-breaking on nominal price
        best = max(accepts, key=lambda x: (x.get("net_margin", x["price"]), x["price"]))
        if best.get("est_transport_cost", 0.0) > 0:
            logs.append(
                f"🏆 [Ranker] {best['buyer_name']} ACCEPTED at ₹{best['price']}/kg "
                f"(Net Farmer Value: ₹{best.get('net_price')}/kg, Margin: ₹{best.get('net_margin'):,.2f} after ₹{best.get('est_transport_cost'):,.2f} freight for {best.get('distance_km')} km). Moving to DEAL."
            )
        else:
            logs.append(f"🏆 [Ranker] {best['buyer_name']} ACCEPTED at ₹{best['price']}/kg (Net Margin: ₹{best.get('net_margin'):,.2f}). Moving to DEAL.")

        # Find the full profile from active_buyers
        selected_profile = next((b for b in state.get("active_buyers", []) if b.get("id") == best["buyer_id"]), {"name": best["buyer_name"]})
        selected_profile["net_margin"] = best.get("net_margin")
        selected_profile["net_price"] = best.get("net_price")
        selected_profile["est_transport_cost"] = best.get("est_transport_cost")

        return {
            "status": "DEAL",
            "best_current_offer": best,
            "latest_buyer_offer": best["price"],
            "net_price": best.get("net_price"),
            "net_margin": best.get("net_margin"),
            "est_transport_cost": best.get("est_transport_cost"),
            "selected_buyer": selected_profile,
            "logs": logs,
            "round": current_round,
        }
        
    # 2. Did anyone counter?
    counters = [o for o in current_offers if o["status"] == "COUNTER"]
    max_rounds = state.get("max_rounds", 5)

    if counters and current_round < max_rounds:
        # Rank counters by Net Farmer Margin
        best = max(counters, key=lambda x: (x.get("net_margin", x["price"]), x["price"]))
        if best.get("est_transport_cost", 0.0) > 0:
            logs.append(
                f"🏆 [Ranker] Top Net Margin counter: {best['buyer_name']} at ₹{best['price']}/kg "
                f"(Net: ₹{best.get('net_price')}/kg, Margin: ₹{best.get('net_margin'):,.2f}, Freight: ₹{best.get('est_transport_cost'):,.2f} for {best.get('distance_km')} km) [Round {current_round}/{max_rounds}]."
            )
        else:
            logs.append(f"🏆 [Ranker] Best counter from {best['buyer_name']} at ₹{best['price']}/kg (Round {current_round}/{max_rounds}).")

        selected_profile = next((b for b in state.get("active_buyers", []) if b.get("id") == best["buyer_id"]), {"name": best["buyer_name"]})
        selected_profile["net_margin"] = best.get("net_margin")
        selected_profile["net_price"] = best.get("net_price")
        selected_profile["est_transport_cost"] = best.get("est_transport_cost")

        return {
            "status": "ACTIVE", # Keep negotiating with current batch
            "best_current_offer": best,
            "latest_buyer_offer": best["price"],
            "net_price": best.get("net_price"),
            "net_margin": best.get("net_margin"),
            "est_transport_cost": best.get("est_transport_cost"),
            "selected_buyer": selected_profile,
            "logs": logs,
            "round": current_round,
        }
        
    # 3. No deal with current active batch (all rejected OR max rounds reached with this batch)
    market_offers = state.get("market_offers") or []
    raw_buyers = state.get("raw_buyers") or []
    contacted_ids = set(state.get("contacted_buyer_ids") or [b.get("id") for b in state.get("active_buyers", []) if b.get("id")])
    expansion_count = state.get("expansion_count", 0)
    max_expansions = state.get("max_candidate_expansions", 3)

    # Find remaining uncontacted viable buyers in market_offers
    remaining_candidates = [
        m for m in market_offers
        if m.get("buyer_id") and m.get("buyer_id") not in contacted_ids and m.get("status") == "VIABLE"
    ]
    if not remaining_candidates:
        remaining_candidates = [
            m for m in market_offers
            if m.get("buyer_id") and m.get("buyer_id") not in contacted_ids
        ]

    if remaining_candidates and expansion_count < max_expansions:
        next_batch_offers = remaining_candidates[:5]
        new_active_buyers = []
        new_current_offers = []
        for best in next_batch_offers:
            buyer = next((b for b in raw_buyers if b.get("id") == best.get("buyer_id") or b.get("name") == best.get("buyer_name")), None)
            if buyer:
                new_active_buyers.append(buyer)
                initial_offer = best.get("offered_price") or round(buyer.get("target_price", state["min_price"]), 2)
                cand_offer = {
                    "buyer_id": buyer["id"],
                    "buyer_name": buyer.get("name", "Buyer"),
                    "price": initial_offer,
                    "status": "COUNTER"
                }
                cand_offer.update(compute_net_farmer_margin(cand_offer, state))
                new_current_offers.append(cand_offer)
                contacted_ids.add(buyer["id"])

        if new_active_buyers:
            new_best_initial = max(new_current_offers, key=lambda x: (x.get("net_margin", x["price"]), x["price"])) if new_current_offers else None
            buyer_names = ", ".join([b.get("name", "Buyer") for b in new_active_buyers])
            fail_reason = "max rounds reached without deal" if current_round >= max_rounds else "all counter-offers rejected"
            logs.append(
                f"🔄 [Adaptive Expansion] Current buyer batch concluded ({fail_reason}). "
                f"Expanding candidate pool (Batch {expansion_count + 1}): contacting {len(new_active_buyers)} new candidates ({buyer_names})."
            )
            return {
                "status": "ACTIVE",
                "active_buyers": new_active_buyers,
                "buyer_agent_objs": [],  # Clear old buyer agents so buyer_node re-instantiates new candidates
                "current_offers": new_current_offers,
                "best_current_offer": new_best_initial,
                "selected_buyer": new_active_buyers[0],
                "latest_buyer_offer": new_best_initial["price"] if new_best_initial else None,
                "net_price": new_best_initial.get("net_price") if new_best_initial else None,
                "net_margin": new_best_initial.get("net_margin") if new_best_initial else None,
                "est_transport_cost": new_best_initial.get("est_transport_cost") if new_best_initial else None,
                "contacted_buyer_ids": list(contacted_ids),
                "expansion_count": expansion_count + 1,
                "round": 0,  # Reset round counter for the new candidate batch
                "logs": logs,
            }

    # If no remaining candidates or expansion limit reached:
    logs.append(f"🚫 [Ranker] Candidate pool exhausted ({len(contacted_ids)} buyer(s) contacted across {expansion_count} batch(es)). All offers rejected.")
    return {"status": "REJECT", "logs": logs, "round": current_round}


# ─────────────────────────────────────────────
# Node 6: Validator
# ─────────────────────────────────────────────

async def validator_node(state: NegotiationState) -> Dict[str, Any]:
    logs = list(state.get("logs", []))
    logs.append("⚖️ [Validator] Validating deal constraints.")

    deal_price = state.get("latest_buyer_offer", 0)
    selected = state.get("selected_buyer", {})
    budget = float(selected.get("budget", 100000)) if selected else 100000
    quantity = state.get("quantity", 0)

    from backend.agents.prompts import VALIDATOR_PROMPT
    prompt = VALIDATOR_PROMPT.format(
        farmer_price=state.get("latest_farmer_ask", state["min_price"]),
        buyer_price=deal_price,
        min_price=state["min_price"],
        budget=budget,
        quantity=quantity,
        msp=Database.get_msp_price(state["crop"]) or 0
    )
    
    raw = await asyncio.to_thread(llm_client.generate, prompt, max_tokens=150, temperature=0.2)
    decision = await _parse_json_response(raw)
    
    valid = decision.get("valid", True) if decision else (deal_price * quantity <= budget and deal_price >= state["min_price"])
    reason = decision.get("reason", "Validation fallback.") if decision else "Validation fallback."
    message = decision.get("message", "Validation successful.") if decision else "Validation successful."

    # Pillar 5: Deterministic Business Rules Overwrite LLM (Floor Price Protection)
    if deal_price < state["min_price"]:
        logs.append(f"🛑 [Validator][Hard Guardrail] REJECTED: Deal price ₹{deal_price}/kg is below farmer floor price ₹{state['min_price']}/kg.")
        return {"status": "REJECT", "logs": logs}

    if valid:
        buyer_p = state.get("buyer_profile") or state.get("selected_buyer") or {}
        best_off = state.get("best_current_offer") or {}
        deal = {
            "buyer_name": buyer_p.get("name") or buyer_p.get("buyer_name") or "Buyer",
            "buyer_id": buyer_p.get("id", "Unknown"),
            "price": deal_price,
            "net_price": buyer_p.get("net_price") or best_off.get("net_price") or deal_price,
            "net_margin": buyer_p.get("net_margin") or best_off.get("net_margin") or round(deal_price * quantity, 2),
            "est_transport_cost": buyer_p.get("est_transport_cost") or best_off.get("est_transport_cost") or 0.0,
            "quantity": quantity,
            "total_value": round(deal_price * quantity, 2),
            "status": "DEAL",
            "validation_message": message
        }
        return {"status": "DEAL", "deal": deal, "logs": logs}
    else:
        return {"status": "REJECT", "logs": logs}


# ─────────────────────────────────────────────
# Node 7: Dynamic Routing (Transport/Warehouse)
# ─────────────────────────────────────────────

async def dynamic_routing_node(state: NegotiationState) -> Dict[str, Any]:
    logs = list(state.get("logs", []))
    
    if state["status"] != "DEAL":
        return {"logs": logs}
        
    deal = state.get("deal") or {}
    deal["type"] = "DIRECT"
    deal["price"] = state.get("latest_buyer_offer", 0)
    deal["quantity"] = state["quantity"]
    
    selected = state.get("selected_buyer", {})
    deal["buyer_name"] = selected.get("name", "Unknown Buyer")
    buyer_loc = selected.get("location", "Market")

    # Pillar 2 & 3: Permission + Conditional Orchestration
    mode = str(state.get("workflow_mode") or "FULL_SUPPLY_CHAIN").upper()
    permitted = state.get("permitted_agents") or ["buyer_agent", "dynamic_routing_agent"]

    # Normalize aliases: TRANSPORT/TRANSPORT_AGENT → dynamic_routing_agent for compatibility
    normalized_permitted = set()
    for p in permitted:
        normalized_permitted.add(p.lower())
    is_transport_permitted = (
        "dynamic_routing_agent" in normalized_permitted
        or "transport" in normalized_permitted
        or "transport_agent" in normalized_permitted
        or mode in ("FULL_SUPPLY_CHAIN", "TRANSPORT_ONLY")
    )

    if mode == "BUYER_ONLY" or not is_transport_permitted:
        logs.append("ℹ️ [Dynamic Routing] Scope is BUYER_ONLY. Concluding workflow at agreement without downstream logistics.")
        return {"deal": deal, "logs": logs}
        
    logs.append("🚚 [Dynamic Routing] Assessing downstream logistics requirements...")
    
    import asyncio

    # --- Conditional Transport Assessment (Full Transport Agent Graph) ---
    eval_transport = mode in ["FULL_SUPPLY_CHAIN", "TRANSPORT_ONLY"]
    if not eval_transport:
        logs.append(f"ℹ️ [Dynamic Routing] Scope is {mode}. Transport procurement skipped.")
    elif state.get("has_transport"):
        logs.append("🚛 [Logistics] Farmer possesses own transport. Third-party transport agent procurement skipped.")
        deal["transport_plan"] = {"type": "SELF_TRANSPORT", "status": "CONFIRMED", "cost": 0.0}
    else:
        # --- Invoke full Transport Agent LangGraph workflow ---
        from backend.agents.transport_agent.graph import run_transport_workflow
        import uuid

        spoilage_days = state.get("spoilage_days", 5)
        shelf_life_hours = spoilage_days * 24
        # Deadline = 80% of shelf life (leave buffer)
        deadline_hours = max(4.0, round(shelf_life_hours * 0.8, 1))

        transport_request = {
            "request_id": f"TR-{state.get('negotiation_id', uuid.uuid4().hex[:8])}",
            "requester_role": state.get("stakeholder_role", "FARMER"),
            "requester_id": state.get("user_id", "stakeholder_01"),
            "workflow_id": state.get("negotiation_id"),
            "listing_id": state.get("listing_id"),
            "crop": state.get("crop", "Produce"),
            "quantity_kg": float(state.get("quantity", 500)),
            "pickup_location": state.get("location", "Ahmednagar"),
            "delivery_location": buyer_loc,
            "delivery_deadline_hours": deadline_hours,
            "shelf_life_hours": shelf_life_hours,
            "urgency": "HIGH" if spoilage_days <= 3 else "NORMAL",
            "refrigerated_required": state.get("crop", "").lower() in {"tomato", "strawberry", "grape", "banana", "mango"},
            "budget": state.get("transport_budget"),
            "allowed_agents": permitted,
            # No buyer_offer → agent will issue initial quote
        }

        try:
            transport_state = await run_transport_workflow(transport_request)
            transport_plan = transport_state.get("final_transport_plan") or {}
            if transport_state.get("status") in ("CONFIRMED", "FEASIBLE"):
                logs.append(
                    f"🚛 [Transport Agent] Plan CONFIRMED: {transport_plan.get('vehicle_name')} "
                    f"({transport_plan.get('vehicle_type')}) | "
                    f"Route: {transport_plan.get('pickup_location')} → {transport_plan.get('delivery_location')} "
                    f"({transport_plan.get('distance_km')} km) | "
                    f"Agreed Freight: ₹{transport_plan.get('agreed_price')} | "
                    f"ETA: {transport_plan.get('estimated_arrival_iso', 'N/A')}"
                )
            else:
                logs.append(f"⚠️ [Transport Agent] Status: {transport_state.get('status')}. Plan may be partial.")
            deal["transport_plan"] = transport_plan
        except Exception as e:
            logger.warning(f"Transport Agent workflow failed: {e}")
            deal["transport_plan"] = {"status": "FAILED", "error": str(e)}
    
    # --- Conditional Storage Assessment (Existing Resources, Holding Duration & Spoilage Risk) ---
    has_storage = state.get("has_storage", False)
    spoilage_days = state.get("spoilage_days", 10)
    requires_storage = state.get("requires_storage", False)
    holding_days = state.get("holding_days", 0)

    # Storage is procured if farmer lacks own storage AND (explicitly requested, holding days > 0, or high spoilage risk)
    needs_storage = (
        not has_storage and (
            requires_storage or
            holding_days > 0 or
            spoilage_days <= 7 or
            "warehouse_agent" in permitted
        )
    )

    eval_storage = mode in ["FULL_SUPPLY_CHAIN", "WAREHOUSE_ONLY"]
    if not eval_storage:
        logs.append(f"ℹ️ [Dynamic Routing] Scope is {mode}. Warehouse procurement skipped.")
    elif has_storage:
        logs.append("🏢 [Storage] Farmer possesses own storage facility. Third-party warehouse procurement skipped.")
    elif needs_storage and ("warehouse_agent" in permitted or "dynamic_routing_agent" in permitted):
        baseline_warehouse = 0.5  # ₹0.5/kg/day
        from backend.agents.stakeholders.warehouse_agent import WarehouseAgent
        warehouses = [WarehouseAgent(agent_id=f"warehouse_{i}", name=f"ColdStorage_{i}") for i in range(1, 6)]
        
        async def get_warehouse_bid(agent):
            context = {
                "crop": state.get("crop"),
                "quantity": state.get("quantity"),
                "buyer_loc": buyer_loc,
                "spoilage_days": spoilage_days,
                "holding_days": holding_days,
                "baseline_warehouse": baseline_warehouse
            }
            return await agent.generate_bid(context)

        w_tasks = [get_warehouse_bid(w) for w in warehouses]
        w_bids = await asyncio.gather(*w_tasks)
        
        best_warehouse = min(w_bids, key=lambda x: x["score"])
        logs.append(f"🏢 [Warehouse] {len(w_bids)} bids received. Selected {best_warehouse['name']} at ₹{best_warehouse['bid']}/day (Farmer Priority Enforced). Reason: {best_warehouse['reason']}")
        deal["warehouse_option"] = best_warehouse

    # --- Conditional Processor Assessment (Value-add / Processing Requirements) ---
    eval_processor = mode in ["FULL_SUPPLY_CHAIN", "PROCESSOR_ONLY"]
    requires_processing = state.get("requires_processing", False)
    if eval_processor and requires_processing and ("processor_agent" in permitted or "dynamic_routing_agent" in permitted):
        from backend.agents.stakeholders.processor_agent import ProcessorAgent
        processors = [ProcessorAgent(agent_id=f"processor_{i}", name=f"AgriProcessor_{i}") for i in range(1, 4)]

        async def get_processor_bid(agent):
            context = {
                "crop": state.get("crop"),
                "quantity": state.get("quantity"),
                "location": state.get("location", "Maharashtra"),
                "market_price": state.get("market_price", state.get("min_price", 10.0)),
                "spoilage_days": spoilage_days,
                "min_price": state.get("min_price", 10.0)
            }
            return await agent.generate_salvage_bid(context)

        p_tasks = [get_processor_bid(p) for p in processors]
        p_bids = await asyncio.gather(*p_tasks)
        if p_bids:
            best_processor = max(p_bids, key=lambda x: x.get("salvage_bid", 0.0))
            logs.append(f"🏭 [Processor] {len(p_bids)} processor quotes evaluated. Selected {best_processor.get('name', 'AgriProcessor')} for value-addition. Reason: {best_processor.get('reason', 'Processing agreement secured')}")
            deal["processor_option"] = best_processor

    # --- Economic Settlement Feasibility Audit (Resolving Audit Gap #13) ---
    # Re-evaluate final farmer net profit using actual carrier quote vs pre-deal benchmark estimate
    gross_revenue = float(deal.get("price", 0.0)) * float(state.get("quantity", 0.0))
    transport_plan = deal.get("transport_plan", {})
    actual_freight = float(transport_plan.get("agreed_price", 0.0) or 0.0)
    storage_option = deal.get("warehouse_option", {})
    actual_storage = float(storage_option.get("bid", 0.0) or 0.0) * float(state.get("holding_days", 0) or 0)

    actual_net_margin = gross_revenue - actual_freight - actual_storage
    actual_net_price = round(actual_net_margin / max(float(state.get("quantity", 1.0)), 1.0), 2)
    farmer_product_floor = float(state.get("min_price", 0.0))
    transport_freight_floor = float(transport_plan.get("minimum_acceptable_price") or transport_plan.get("floor_price") or 0.0)

    is_profitable = actual_net_price >= farmer_product_floor
    settlement_status = "FEASIBLE_PROFITABLE" if is_profitable else "SETTLEMENT_REJECTED_FLOOR_VIOLATED"

    deal["economic_settlement"] = {
        "gross_revenue": round(gross_revenue, 2),
        "estimated_freight": round(float(deal.get("est_transport_cost", 0.0) or 0.0), 2),
        "actual_freight": round(actual_freight, 2),
        "storage_cost": round(actual_storage, 2),
        "final_net_margin": round(actual_net_margin, 2),
        "final_net_price_per_kg": actual_net_price,
        "farmer_product_floor_price": farmer_product_floor,
        "transport_freight_floor_price": transport_freight_floor,
        "is_profitable_above_floor": is_profitable,
        "settlement_status": settlement_status
    }

    if is_profitable:
        logs.append(
            f"📊 [Economic Settlement Audit] Final Net Farmer Realization: ₹{actual_net_price}/kg "
            f"(Net Margin: ₹{actual_net_margin:,.2f} after actual carrier freight of ₹{actual_freight:,.2f}). "
            f"Settlement Status: FEASIBLE_PROFITABLE."
        )
        booking_status = "BOOKED"
    else:
        dilution = round(farmer_product_floor - actual_net_price, 2)
        logs.append(
            f"❌ [Economic Settlement Audit] Actual carrier freight of ₹{actual_freight:,.2f} dilutes net realization to "
            f"₹{actual_net_price}/kg (₹{dilution}/kg below farmer product floor ₹{farmer_product_floor}/kg). "
            f"Transport booking REJECTED to protect farmer livelihood."
        )
        if deal.get("transport_plan"):
            deal["transport_plan"]["status"] = "REJECTED_MARGIN_DILUTION"
        booking_status = "REJECTED_FLOOR_VIOLATED"

    # Populate supply_chain_booking for downstream API consumers
    supply_chain_booking = {
        "negotiation_id": state.get("negotiation_id"),
        "crop": state.get("crop"),
        "quantity": state.get("quantity"),
        "deal_price": deal.get("price"),
        "transport_plan": deal.get("transport_plan"),
        "warehouse_option": deal.get("warehouse_option"),
        "processor_option": deal.get("processor_option"),
        "economic_settlement": deal.get("economic_settlement"),
        "status": booking_status,
    }

    return {"deal": deal, "supply_chain_booking": supply_chain_booking, "logs": logs}


# ─────────────────────────────────────────────
# Node 8: Reflection + Supply Chain Fallback + RL Memory
# ─────────────────────────────────────────────

def calculate_supply_chain_rewards(state: NegotiationState) -> Dict[str, float]:
    rewards = {
        "farmer": 0.0,
        "buyer": 0.0,
        "warehouse": 0.0,
        "transport": 0.0,
        "processor": 0.0,
        "compost": 0.0
    }
    status = state.get("status")
    rounds = state.get("round", 0)
    
    # Penalize long negotiations
    time_penalty = rounds * 2.0
    rewards["farmer"] -= time_penalty
    rewards["buyer"] -= time_penalty
    
    if status == "DEAL":
        rewards["farmer"] += 100.0
        rewards["buyer"] += 100.0
        
        # Check transport/warehouse usage
        deal = state.get("deal", {})
        if "transport_plan" in deal:
            rewards["transport"] += 50.0
        if "warehouse_option" in deal:
            rewards["warehouse"] += 50.0
            
    elif status == "REJECT":
        rewards["farmer"] -= 50.0
        rewards["buyer"] -= 50.0
        
    elif status in ("ESCALATED_PROCESSING", "ESCALATED_COMPOST"):
        rewards["farmer"] -= 20.0
        if status == "ESCALATED_PROCESSING":
            rewards["processor"] += 40.0
        else:
            rewards["compost"] += 20.0

    return rewards

async def reflection_node(state: NegotiationState) -> Dict[str, Any]:
    logs = list(state.get("logs", []))
    logs.append("🧐 [Reflection] Post-negotiation analysis started.")

    history_str = _format_history(state.get("history", []))
    final_price = state.get("latest_buyer_offer", 0)

    prompt = REFLECTION_PROMPT.format(
        crop=state["crop"],
        status=state["status"],
        rounds=state["round"],
        history=history_str,
        summary=f"Status: {state['status']}. Final price considered: ₹{final_price}/kg.",
        market_price=state["market_price"],
        final_price=final_price
    )

    raw_reflection = await asyncio.to_thread(llm_client.generate, prompt, max_tokens=300, temperature=0.2)
    parsed_reflection = await _parse_json_response(raw_reflection)
    
    if not parsed_reflection:
        parsed_reflection = {
            "reason_for_success_or_failure": f"Negotiation ended with {state['status']}",
            "farmer_strategy": "Fallback strategy",
            "buyer_strategy": "Fallback strategy"
        }
        
    rewards = calculate_supply_chain_rewards(state)
    logs.append(f"🧐 [Reflection] Strategies extracted. Rewards: Farmer({rewards['farmer']}), Buyer({rewards['buyer']}), Transporter({rewards['transport']})")
    
    if state["status"] == "DEAL":
        try:
            from backend.agents.prompts import FINAL_AGREEMENT_PROMPT
            selected = state.get("selected_buyer", {})
            ag_prompt = FINAL_AGREEMENT_PROMPT.format(
                crop=state["crop"],
                quantity=state["quantity"],
                farmer_name="Farmer",
                buyer_name=selected.get("name", "Buyer"),
                final_price=final_price,
                history=history_str
            )
            final_agreement = await asyncio.to_thread(llm_client.generate, ag_prompt, max_tokens=350, temperature=0.7)
            logs.append(f"\n📝 [FINAL AGREEMENT]\n{final_agreement}\n")
        except Exception as e:
            logger.warning(f"Failed to generate Final Agreement: {e}")

    # Save Full Supply Chain RL Memory to Database
    from uuid import uuid4
    try:
        history_entry = {
            "negotiation_id": f"neg_{uuid4().hex[:8]}",
            "crop": state["crop"],
            "quantity": state["quantity"],
            "status": state["status"],
            "final_price": final_price,
            "market_price": state["market_price"],
            "negotiation_rounds": state["round"],
            "successful": state["status"] == "DEAL",
            "failure_reason": parsed_reflection.get("reason_for_success_or_failure") if state["status"] != "DEAL" else None,
            "farmer_strategy": parsed_reflection.get("farmer_strategy"),
            "farmer_reward": rewards["farmer"],
            "buyer_strategy": parsed_reflection.get("buyer_strategy"),
            "buyer_reward": rewards["buyer"],
            "warehouse_strategy": parsed_reflection.get("warehouse_strategy"),
            "warehouse_reward": rewards["warehouse"],
            "transport_strategy": parsed_reflection.get("transport_strategy"),
            "transport_reward": rewards["transport"],
            "processor_strategy": parsed_reflection.get("processor_strategy"),
            "processor_reward": rewards["processor"],
            "compost_strategy": parsed_reflection.get("compost_strategy"),
            "compost_reward": rewards["compost"],
            "summary": parsed_reflection.get("reason_for_success_or_failure")
        }
        
        user_id = state.get("user_id", "system")
        await Database.add_history_async(user_id, history_entry)
        logs.append("💾 [Memory] RL Strategy & Reward Memory saved to PostgreSQL.")
    except Exception as e:
        logger.warning(f"PostgreSQL RL Memory save failed: {e}")

    # Write to ChromaDB strategies_index
    try:
        from backend.services.rag_service import rag_service
        log_id = str(uuid4())
        await rag_service.add_strategy_log(
            log_id=log_id,
            text=json.dumps(parsed_reflection),
            metadata={
                "crop": state["crop"],
                "status": state["status"],
                "rounds": state["round"],
                "farmer_reward": rewards["farmer"],
                "buyer_reward": rewards["buyer"]
            }
        )
        logs.append("🧠 [Reflection] Strategy log embedded into ChromaDB.")
    except Exception as e:
        logger.warning(f"ChromaDB strategy write failed: {e}")

    # ── Supply chain fallbacks if no deal ──
    final_status = state["status"]
    deal = state.get("deal")

    if final_status != "DEAL":
        logs.append("⚠️ [Reflection] Direct sale failed. Evaluating supply chain fallbacks.")
        spoilage = state["spoilage_days"]
        storage_cost = 1.8 * state["quantity"] * spoilage

        from backend.agents.prompts import PROCESSOR_PROMPT, COMPOST_PROMPT

        if spoilage > 2 and storage_cost < state["market_price"] * state["quantity"] * 0.3:
            logs.append("🏗️ [Reflection] Fallback: STORAGE (Deferred to Warehouse Agent routing)")
            final_status = "ESCALATED_STORAGE"
            deal = {
                "type": "STORAGE",
                "price": round(state["market_price"] * 0.9, 2),
                "quantity": state["quantity"],
                "warehouse": "WarehouseAgent",
                "storage_cost": round(storage_cost, 2),
            }
        elif state["market_price"] * 0.8 >= state["min_price"] * 0.6:
            logs.append("⚙️ [Reflection] Fallback: PROCESSING")
            final_status = "ESCALATED_PROCESSING"
            
            # --- Parallel Processor Bidding ---
            processors = [f"FoodProcessor_{i}" for i in range(1, 6)]
            async def get_processor_bid(name):
                prompt = PROCESSOR_PROMPT.format(
                    processor_name=name, crop=state["crop"], quantity=state["quantity"],
                    location=state["location"], market_price=state["market_price"]
                )
                resp = await asyncio.to_thread(llm_client.generate, prompt, max_tokens=100)
                parsed = await _parse_json_response(resp)
                if parsed and "bid_price" in parsed:
                    try:
                        # Farmer Priority: apply 2% edge for the farmer in processors too (select highest bid)
                        bid_price = float(parsed["bid_price"])  # cast: LLM may return string
                        priority_score = bid_price * 1.02
                        return {"name": name, "bid": bid_price, "score": priority_score, "reason": parsed.get("reason", "")}
                    except (ValueError, TypeError):
                        pass
                return {"name": name, "bid": round(state["market_price"] * 0.6, 2), "score": 0, "reason": "Fallback"}

            p_tasks = [get_processor_bid(p) for p in processors]
            p_bids = await asyncio.gather(*p_tasks)
            best_processor = max(p_bids, key=lambda x: x["score"]) # Max is best for farmer
            
            logs.append(f"⚙️ [Processor] {len(p_bids)} bids received. Selected {best_processor['name']} at ₹{best_processor['bid']}/kg (Farmer Priority Enforced). Reason: {best_processor['reason']}")
            deal = {
                "type": "PROCESSING",
                "price": best_processor["bid"],
                "quantity": state["quantity"],
                "processor": best_processor,
            }
        else:
            logs.append("♻️ [Reflection] Fallback: COMPOSTING")
            final_status = "ESCALATED_COMPOST"
            
            # --- Parallel Compost Bidding ---
            composters = [f"CompostCenter_{i}" for i in range(1, 6)]
            async def get_compost_bid(name):
                prompt = COMPOST_PROMPT.format(
                    compost_name=name, crop=state["crop"], quantity=state["quantity"], location=state["location"]
                )
                resp = await asyncio.to_thread(llm_client.generate, prompt, max_tokens=100)
                parsed = await _parse_json_response(resp)
                if parsed and "bid_price" in parsed:
                    # Farmer Priority: apply 2% edge (highest disposal value)
                    priority_score = parsed["bid_price"] * 1.02
                    return {"name": name, "bid": parsed["bid_price"], "score": priority_score, "reason": parsed.get("reason", "")}
                return {"name": name, "bid": 5.0, "score": 0, "reason": "Fallback"}

            c_tasks = [get_compost_bid(c) for c in composters]
            c_bids = await asyncio.gather(*c_tasks)
            best_compost = max(c_bids, key=lambda x: x["score"])
            
            logs.append(f"♻️ [Compost] {len(c_bids)} bids received. Selected {best_compost['name']} at ₹{best_compost['bid']}/kg (Farmer Priority Enforced). Reason: {best_compost['reason']}")
            deal = {
                "type": "COMPOST",
                "price": best_compost["bid"],
                "quantity": state["quantity"],
                "compost": best_compost,
            }

    # Recommendation analysis
    recommendation = await _generate_recommendation(state, deal)

    return {
        "status": final_status,
        "deal": deal,
        "reflection": parsed_reflection.get("reason_for_success_or_failure", "Negotiation Finished"),
        "recommendation": recommendation,
        "logs": logs,
    }


async def _generate_recommendation(state: NegotiationState, deal: Optional[Dict]) -> str:
    """Generate a farmer recommendation based on deal outcome."""
    try:
        from backend.agents.prompts import RECOMMENDATION_PROMPT
        deal_type = deal.get("type", "DIRECT") if deal else "NONE"
        prompt = RECOMMENDATION_PROMPT.format(
            crop=state["crop"],
            quantity=state["quantity"],
            farmer_min_price=state["min_price"],
            direct_sale_result=f"Status={state['status']}, Type={deal_type}, Price=\u20b9{state.get('latest_buyer_offer', 0)}/kg",
            storage_cost=round(1.8 * state["quantity"] * state["spoilage_days"], 2),
            storage_days=state["spoilage_days"],
            processor_offer=round(state["market_price"] * 0.8, 2),
            market_price=state["market_price"]
        )
        raw = await asyncio.to_thread(llm_client.generate, prompt, max_tokens=180)
        if raw:
            # RECOMMENDATION_PROMPT returns JSON {"message": "..."} — parse it
            parsed_rec = await _parse_json_response(raw)
            if parsed_rec and parsed_rec.get("message"):
                return parsed_rec["message"].strip()
            # Fallback: if LLM returned plain text (not JSON), use it directly
            return raw.strip()
    except Exception as e:
        logger.warning(f"Recommendation generation failed: {e}")

    # Deterministic fallback — covers all deal types
    status = state["status"]
    final_price = state.get("latest_buyer_offer", state["min_price"])
    if status == "DEAL" or (deal and deal.get("type") == "DIRECT"):
        return (
            f"Direct sale at \u20b9{final_price}/kg is the optimal outcome for {state['crop']}. "
            f"Total value: \u20b9{round(final_price * state['quantity'], 2)}. Confirm logistics and proceed to invoicing."
        )
    elif deal and deal.get("type") == "PROCESSING":
        return (
            f"Processing route activated at \u20b9{deal.get('price', 0)}/kg. "
            f"This recovers partial value. Consider FPO membership for better rates next season."
        )
    elif deal and deal.get("type") == "STORAGE":
        return (
            f"Cold storage recommended for {state['spoilage_days']} days (est. cost: \u20b9{deal.get('storage_cost', 0)}). "
            f"Retry sale when market crosses \u20b9{round(state['market_price'] * 1.08, 2)}/kg."
        )
    elif status == "HOLD":
        return (
            f"HOLD directive active — XGBoost forecast suggests price may rise. "
            f"Review in 7 days before re-listing {state['crop']}."
        )
    elif state["spoilage_days"] > 2:
        return (
            f"Negotiation failed with {state['spoilage_days']} shelf days remaining. "
            f"Recommend cold warehouse storage and retry with a different buyer segment."
        )
    return f"Consider processor salvage or compost route to recover residual value from the {state['crop']} lot."



# ─────────────────────────────────────────────
# Node: Escalation Nodes (Storage & Processing)
# ─────────────────────────────────────────────

async def escalated_storage_node(state: NegotiationState) -> Dict[str, Any]:
    logs = list(state.get("logs", []))
    logs.append("❄️ [Escalation] Routing crop to Warehouse/Cold Storage due to negotiation failure.")
    return {"status": "ESCALATED_STORAGE", "logs": logs}

async def escalated_processing_node(state: NegotiationState) -> Dict[str, Any]:
    logs = list(state.get("logs", []))
    logs.append("🏭 [Escalation] Routing crop to Processor for salvage value.")
    
    from backend.agents.stakeholders.processor_agent import ProcessorAgent
    processor = ProcessorAgent(agent_id="processor_01", name="AgriProcessor")
    context = {
        "crop": state.get("crop"),
        "quantity": state.get("quantity"),
        "spoilage_days": state.get("spoilage_days"),
        "min_price": state.get("min_price", 10.0)
    }
    
    bid_result = await processor.generate_salvage_bid(context)
    logs.append(f"🏭 [Processor] Received salvage bid from {bid_result['name']}: {bid_result['decision']} at ₹{bid_result['bid']}/kg. Reason: {bid_result['reason']}")
    
    deal = state.get("deal") or {}
    deal["processor_salvage"] = bid_result
    
    return {"status": "ESCALATED_PROCESSING", "logs": logs, "deal": deal}


# ─────────────────────────────────────────────
# Conditional Routing
# ─────────────────────────────────────────────

async def route_after_farmer(state: NegotiationState) -> str:
    if state.get("status") in ("DEAL", "ACCEPT"):
        return "validator_agent"
    if state.get("status") == "REJECT" or state.get("round", 0) >= state.get("max_rounds", 5):
        allowed = state.get("allowed_agent_set", [])
        if any(x in allowed for x in ("WAREHOUSE", "warehouse_agent", "dynamic_routing_agent")) and state.get("spoilage_days", 14) > 2:
            return "escalated_storage_agent"
        if any(x in allowed for x in ("PROCESSOR", "processor_agent")):
            return "escalated_processing_agent"
        return "reflection_agent"
    
    allowed = state.get("allowed_agent_set", [])
    if not allowed or any(x in allowed for x in ("BUYER", "buyer_agent")):
        return "buyer_agent"
    return "reflection_agent"


async def route_after_rank(state: NegotiationState) -> str:
    if state.get("status") in ("DEAL", "ACCEPT"):
        return "validator_agent"
    if state.get("status") == "REJECT" or state.get("round", 0) >= state.get("max_rounds", 5):
        allowed = state.get("allowed_agent_set", [])
        if any(x in allowed for x in ("WAREHOUSE", "warehouse_agent", "dynamic_routing_agent")) and state.get("spoilage_days", 14) > 2:
            return "escalated_storage_agent"
        if any(x in allowed for x in ("PROCESSOR", "processor_agent")):
            return "escalated_processing_agent"
        return "reflection_agent"
    return "farmer_agent"


async def hold_decision_node(state: NegotiationState) -> Dict[str, Any]:
    logs = list(state.get("logs", []))
    logs.append("🛑 [Market Intelligence] HOLD Execution Path Activated. Projected wholesale price surge justifies holding lot. Buyer matching and active negotiation bypassed.")
    deal = {
        "type": "HOLD",
        "status": "HOLD",
        "reason": state.get("sell_hold_reasoning", "Holding lot for anticipated market appreciation."),
        "holding_period_days": 7
    }
    return {
        "status": "HOLD",
        "deal": deal,
        "logs": logs
    }


async def route_after_market_intelligence(state: NegotiationState) -> str:
    # Pillar 4: Explicit Graph Branching for HOLD vs SELL
    if state.get("sell_hold_decision") == "HOLD":
        return "hold_decision_node"
    return "matching_agent"


async def route_after_validator(state: NegotiationState) -> str:
    if state["status"] == "DEAL":
        return "dynamic_routing_agent"
    return "reflection_agent"


# ─────────────────────────────────────────────
# Compile LangGraph State Machine
# ─────────────────────────────────────────────

workflow = StateGraph(NegotiationState)

workflow.add_node("planner_agent", planner_node)
workflow.add_node("knowledge_manager_node", knowledge_manager_node)
workflow.add_node("market_intelligence_agent", market_intelligence_node)
workflow.add_node("hold_decision_node", hold_decision_node)
workflow.add_node("matching_agent", matching_engine_node)
workflow.add_node("farmer_agent", farmer_node)
workflow.add_node("buyer_agent", buyer_node)
workflow.add_node("rank_responses_agent", rank_responses_node)
workflow.add_node("validator_agent", validator_node)
workflow.add_node("dynamic_routing_agent", dynamic_routing_node)
workflow.add_node("reflection_agent", reflection_node)
workflow.add_node("escalated_storage_agent", escalated_storage_node)
workflow.add_node("escalated_processing_agent", escalated_processing_node)

workflow.set_entry_point("planner_agent")

workflow.add_edge("planner_agent", "knowledge_manager_node")
workflow.add_edge("knowledge_manager_node", "market_intelligence_agent")

# Explicit Conditional Branch: SELL -> matching_agent | HOLD -> hold_decision_node
workflow.add_conditional_edges(
    "market_intelligence_agent",
    route_after_market_intelligence,
    {
        "matching_agent": "matching_agent",
        "hold_decision_node": "hold_decision_node"
    }
)
workflow.add_edge("hold_decision_node", "reflection_agent")
workflow.add_edge("matching_agent", "farmer_agent")

workflow.add_conditional_edges(
    "farmer_agent",
    route_after_farmer,
    {
        "validator_agent": "validator_agent",
        "reflection_agent": "reflection_agent",
        "buyer_agent": "buyer_agent",
        "escalated_storage_agent": "escalated_storage_agent",
        "escalated_processing_agent": "escalated_processing_agent"
    }
)

# buyer_agent evaluates all active_buyers and passes offers to rank_responses_agent
workflow.add_edge("buyer_agent", "rank_responses_agent")

workflow.add_conditional_edges(
    "rank_responses_agent",
    route_after_rank,
    {
        "validator_agent": "validator_agent",
        "reflection_agent": "reflection_agent",
        "farmer_agent": "farmer_agent",
        "escalated_storage_agent": "escalated_storage_agent",
        "escalated_processing_agent": "escalated_processing_agent"
    }
)

workflow.add_conditional_edges(
    "validator_agent",
    route_after_validator,
    {
        "dynamic_routing_agent": "dynamic_routing_agent",
        "reflection_agent": "reflection_agent"
    }
)

workflow.add_edge("dynamic_routing_agent", "reflection_agent")
workflow.add_edge("escalated_storage_agent", "reflection_agent")
workflow.add_edge("escalated_processing_agent", "reflection_agent")
workflow.add_edge("reflection_agent", END)

graph_orchestrator = workflow.compile()

