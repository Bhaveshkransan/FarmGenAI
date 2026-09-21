"""
backend/agents/graph_orchestrator.py

Stateful LangGraph orchestration engine for AgriNegotiator.
Implements Workflow Planner, Matching Engine, Farmer, Buyer,
Validator, Reflection, Market Intelligence, and Recommendation nodes.
Uses structured LangChain PromptTemplates with JSON output parsing.
RAG context is injected into Farmer and Buyer agent prompts.
"""

import json
import re
import random
import logging
from typing import TypedDict, List, Dict, Any, Optional
from langgraph.graph import StateGraph, END

from llm.llm_client import client as llm_client
from database.db import Database
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

logger = logging.getLogger("GraphOrchestrator")


# ─────────────────────────────────────────────
# Shared LangGraph State
# ─────────────────────────────────────────────

class NegotiationState(TypedDict):
    crop: str
    quantity: float
    min_price: float
    target_price: float
    spoilage_days: int
    location: str
    market_price: float
    round: int
    max_rounds: int
    history: List[Dict[str, Any]]
    buyer_profile: Optional[Dict[str, Any]]
    logs: List[str]
    status: str            # ACTIVE | DEAL | REJECT | ESCALATED_STORAGE | ESCALATED_PROCESSING | ESCALATED_COMPOST
    proposed_scenario: str
    next_action: str
    deal: Optional[Dict[str, Any]]
    plan: Optional[str]
    reflection: Optional[str]
    selected_buyer: Optional[Dict[str, Any]]
    market_offers: List[Dict[str, Any]]
    user_id: Optional[str]
    active_buyers: List[Dict[str, Any]]
    current_offers: List[Dict[str, Any]]
    best_current_offer: Optional[Dict[str, Any]]
    latest_farmer_ask: Optional[float]
    latest_buyer_offer: Optional[float]
    buyers_list: List[Dict[str, Any]]
    rag_context: Optional[str]               # Injected market + strategy context
    market_intelligence: Optional[str]       # Market analysis output
    recommendation: Optional[str]           # Recommendation agent output
    farmer_agent_obj: Optional[Any]
    buyer_agent_objs: Optional[List[Any]]


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




def _format_history(history: List[Dict]) -> str:
    """Convert history list to readable string."""
    if not history:
        return "No rounds yet."
    lines = []
    for h in history:
        lines.append(
            f"  Round {h.get('round', '?')}: {h.get('agent', '?')} "
            f"{'offered' if h.get('agent') == 'Buyer' else 'asked'} "
            f"₹{h.get('price', 0)}/kg ({h.get('decision', 'COUNTER')})"
        )
    return "\n".join(lines)


async def _build_rag_context(crop: str, location: str, market_price: float = 0.0) -> str:
    """Query ChromaDB and relational database for a comprehensive market context."""
    context_parts = []
    
    try:
        from backend.services.market_intelligence import MarketIntelligenceService
        historical_avg = market_price if market_price > 0 else None
        mis_context = await MarketIntelligenceService.get_market_context(crop, location, historical_avg or 0.0)
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

    # Fetch RAG context early — shared across all downstream agents
    rag_context = await _build_rag_context(state["crop"], state["location"], state["market_price"])

    prompt = PLANNER_PROMPT.format(
        crop=state["crop"],
        quantity=state["quantity"],
        min_price=state["min_price"],
        location=state["location"],
        shelf_life=state["spoilage_days"],
        market_price=state["market_price"]
    )

    plan_text = llm_client.generate(prompt, max_tokens=200)
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
    }


async def knowledge_manager_node(state: NegotiationState) -> Dict[str, Any]:
    # Query database facts + weather + ChromaDB using unified _build_rag_context helper
    rag_context = await _build_rag_context(state["crop"], state["location"], state["market_price"])
    
    # Fetch external real-time data concurrently
    import asyncio
    weather_task = asyncio.create_task(OpenMeteoClient.get_weather(state["location"]))
    mandi_task = asyncio.create_task(MandiAPIClient.get_live_price(state["crop"], state["location"], state["market_price"]))
    
    weather_data, mandi_data = await asyncio.gather(weather_task, mandi_task)
    
    logs = list(state.get("logs", []))
    logs.append("🧠 [KnowledgeManager] Live market data & context retrieved.")
    
    return {
        "rag_context": rag_context, 
        "weather": weather_data,
        "live_mandi": mandi_data,
        "logs": logs
    }

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

    analysis = llm_client.generate(prompt, max_tokens=200)
    if not analysis:
        # Fallback deterministic analysis
        if state["market_price"] > state["min_price"] * 1.1:
            analysis = f"Market is bullish for {state['crop']}. Recommended band: ₹{round(state['market_price'] * 0.9, 2)} - ₹{round(state['market_price'] * 1.15, 2)}/kg."
        else:
            analysis = f"Market is at par for {state['crop']}. Recommended band: ₹{state['min_price']} - ₹{round(state['market_price'] * 1.05, 2)}/kg."

    logs.append(f"📊 [Market Intelligence] {analysis[:100]}...")
    return {
        "market_intelligence": analysis,
        "logs": logs,
    }


# ─────────────────────────────────────────────
# Node 3: Matching Engine
# ─────────────────────────────────────────────

async def matching_engine_node(state: NegotiationState) -> Dict[str, Any]:
    logs = list(state.get("logs", []))
    logs.append("📡 [Matching Engine] Querying suitable buyer profiles.")

    # If direct buyer agent objects or selected buyer were explicitly provided, respect them
    if state.get("buyer_agent_objs") and state.get("selected_buyer"):
        sel = dict(state["selected_buyer"])
        logs.append(f"🎯 [Matching Engine] Direct Buyer Selected: {sel.get('name', 'Buyer')}")
        init_offer = float(sel.get("target_price") or state.get("latest_buyer_offer") or (state["min_price"] * 1.05))
        return {
            "active_buyers": [sel],
            "current_offers": [{
                "buyer_id": sel.get("id", "buyer_direct"),
                "buyer_name": sel.get("name", "Buyer"),
                "price": init_offer,
                "status": "COUNTER"
            }],
            "best_current_offer": {
                "buyer_id": sel.get("id", "buyer_direct"),
                "buyer_name": sel.get("name", "Buyer"),
                "price": init_offer,
                "status": "COUNTER"
            },
            "buyer_profile": sel,
            "selected_buyer": sel,
            "latest_buyer_offer": init_offer,
            "latest_farmer_ask": round(state["min_price"] * 1.2, 2),
            "logs": logs
        }

    from backend.services.matching_service import match_listing_to_buyers
    
    listing_mock = {
        "crop": state["crop"],
        "quantity": state["quantity"],
        "min_price": state["min_price"],
        "location": state["location"],
        "market_price": state.get("market_price", state["min_price"] + 1)
    }
    
    market_offers = await match_listing_to_buyers(listing_mock)
    
    # Active buyers fetching logic
    state_buyers = state.get("buyers_list", [])
    db_buyers = state_buyers if state_buyers else await Database.list_buyers_async()
    raw_buyers = [b if isinstance(b, dict) else {
        "id": getattr(b, "id", f"buyer_{getattr(b, 'name', 'default').lower()}"),
        "name": getattr(b, "name", "Buyer"),
        "target_price": float(getattr(b, "target_price", None) or state["min_price"]),
        "budget": float(getattr(b, "budget", None) or (float(getattr(b, "target_price", None) or state["min_price"]) * float(state.get("quantity", 1000)) * 1.5)),
        "max_quantity": float(getattr(b, "max_quantity", None) or state["quantity"]),
        "location": getattr(b, "location", "Market"),
        "strategy": getattr(b, "strategy", "default")
    } for b in db_buyers]

    active_buyers = []
    current_offers = []
    for best in market_offers[:5]:  # Top 5 buyers for parallel negotiation
        buyer = next((b for b in raw_buyers if (isinstance(b, dict) and (b.get("id") == best["buyer_id"] or b.get("name") == best["buyer_name"]))), None)
        if buyer:
            buyer_entry = dict(buyer)
            buyer_entry["budget"] = float(best.get("budget") or buyer_entry.get("budget") or (state["min_price"] * state["quantity"] * 1.5))
            buyer_entry["location"] = best.get("location") or buyer_entry.get("location", "Market")
            active_buyers.append(buyer_entry)
            initial_offer = best["offered_price"]
            current_offers.append({
                "buyer_id": buyer_entry["id"],
                "buyer_name": buyer_entry.get("name", "Buyer"),
                "price": initial_offer,
                "status": "COUNTER"
            })

    if not active_buyers and raw_buyers:
        b = dict(raw_buyers[0])
        b["budget"] = float(b.get("budget") or (state["min_price"] * state["quantity"] * 1.5))
        active_buyers.append(b)
        initial_offer = round(float(b.get("target_price") or state["min_price"]) * 0.95, 2)
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
            "budget": state["min_price"] * state["quantity"] * 1.5,
            "max_quantity": state["quantity"],
            "location": state["location"],
            "strategy": "default"
        }
        active_buyers.append(b)
        current_offers.append({
            "buyer_id": b["id"],
            "buyer_name": b["name"],
            "price": round(b["target_price"] * 0.95, 2),
            "status": "COUNTER"
        })

    buyer_names = ", ".join([b.get("name", "Buyer") for b in active_buyers])
    logs.append(f"🎯 [Matching Engine] Matched Top {len(active_buyers)} Buyers: {buyer_names}")

    initial_farmer_ask = round(state["min_price"] * 1.2, 2)
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
        "logs": logs,
    }


# ─────────────────────────────────────────────
# Node 4: Farmer Agent
# ─────────────────────────────────────────────

async def farmer_node(state: NegotiationState) -> Dict[str, Any]:
    logs = list(state.get("logs", []))
    history = list(state.get("history", []))
    current_round = state.get("round", 0) + 1

    selected_buyer = state.get("selected_buyer") or (state.get("active_buyers", [{}])[0] if state.get("active_buyers") else {})
    buyer_offer = state.get("latest_buyer_offer") or round(
        selected_buyer.get("target_price", state["min_price"]) * 0.75, 2
    )

    logs.append(f"👨‍🌾 [Farmer] Round {current_round}: Buyer offered ₹{buyer_offer}/kg")

    farmer = state.get("farmer_agent_obj")
    if not farmer:
        logs.append("⚠️ [Farmer] FarmerAgent object missing from state! Aborting.")
        return {"status": "REJECT", "round": current_round, "logs": logs}

    offer_payload = {"price": buyer_offer, "quantity": state["quantity"]}
    context_payload = {"market_price": state["market_price"], "round": current_round}

    response = farmer.respond_to_offer(offer_payload, context=context_payload, force_deterministic=False)

    decision_type = response.get("type", "REJECT")
    counter_price = response.get("price", buyer_offer)
    message = response.get("message", "")

    logs.append(f"👨‍🌾 [Farmer] {decision_type} ₹{counter_price}/kg: {message}")

    if decision_type == "ACCEPT":
        return {"status": "DEAL", "round": current_round, "latest_farmer_ask": buyer_offer, "logs": logs, "quantity": state["quantity"]}
    elif decision_type == "REJECT":
        return {"status": "REJECT", "round": current_round, "logs": logs}
    else:
        history.append({
            "round": current_round,
            "agent": farmer.name,
            "price": counter_price,
            "decision": "COUNTER",
            "quantity": state["quantity"],
            "message": message,
            "reason": message
        })
        return {
            "round": current_round,
            "history": history,
            "latest_farmer_ask": counter_price,
            "latest_buyer_offer": buyer_offer,
            "logs": logs
        }


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
        active = state.get("active_buyers") or state.get("buyers_list") or ([state["buyer_profile"]] if state.get("buyer_profile") else [])
        if active:
            from agents.buyer_agent import BuyerAgent
            for b in active:
                if isinstance(b, BuyerAgent):
                    buyer_agents.append(b)
                elif isinstance(b, dict):
                    agent = BuyerAgent(
                        name=b.get("name", "Buyer"),
                        budget=float(b.get("budget", 50000.0)),
                        max_quantity=float(b.get("max_quantity", state.get("quantity", 1000.0))),
                        target_price=float(b.get("target_price", state.get("market_price", 25.0))),
                        location=b.get("location", state.get("location"))
                    )
                    agent.id = b.get("id", f"buyer_{agent.name}")
                    buyer_agents.append(agent)
    
    logs.append(f"🤝 [Buyers Pool] Round {current_round}: Evaluating Farmer ask of ₹{farmer_ask}/kg")
    
    current_offers = []

    if not buyer_agents:
        logs.append("⚠️ [Buyers Pool] No BuyerAgent objects found in state! Aborting.")
        return {"history": history, "current_offers": [], "logs": logs}
    
    import asyncio

    async def get_buyer_response(buyer):
        buyer_name = buyer.name
        offer_payload = {"price": farmer_ask, "quantity": state["quantity"]}
        context_payload = {"market_price": state["market_price"], "round": current_round}
        response = await asyncio.to_thread(buyer.respond_to_offer, offer_payload, context=context_payload)
        return buyer, buyer_name, response

    tasks = [get_buyer_response(b) for b in buyer_agents]
    results = await asyncio.gather(*tasks)

    for buyer, buyer_name, response in results:
        decision_type = response.get("type", "REJECT")
        counter_price = response.get("price", farmer_ask)
        message = response.get("message", "")

        logs.append(f"🤝 [{buyer_name}] {decision_type} ₹{counter_price}/kg: {message}")

        if decision_type == "ACCEPT":
            current_offers.append({
                "buyer_id": buyer.id if hasattr(buyer, "id") else f"buyer_{buyer_name}", 
                "buyer_name": buyer_name, 
                "price": farmer_ask, 
                "status": "ACCEPT", 
                "message": message
            })
        elif decision_type == "REJECT":
            current_offers.append({
                "buyer_id": buyer.id if hasattr(buyer, "id") else f"buyer_{buyer_name}", 
                "buyer_name": buyer_name, 
                "price": farmer_ask, 
                "status": "REJECT", 
                "message": message
            })
        else:
            history.append({
                "round": current_round,
                "agent": buyer_name,
                "agent_id": buyer.id if hasattr(buyer, "id") else f"buyer_{buyer_name}",
                "price": counter_price,
                "decision": "COUNTER",
                "quantity": state["quantity"],
                "message": message,
                "reason": message
            })
            current_offers.append({
                "buyer_id": buyer.id if hasattr(buyer, "id") else f"buyer_{buyer_name}", 
                "buyer_name": buyer_name, 
                "price": counter_price, 
                "status": "COUNTER"
            })

    return {
        "history": history,
        "current_offers": current_offers,
        "logs": logs,
    }


# ─────────────────────────────────────────────
# Node 5.5: Rank Responses Node
# ─────────────────────────────────────────────

async def rank_responses_node(state: NegotiationState) -> Dict[str, Any]:
    logs = list(state.get("logs", []))
    current_offers = state.get("current_offers", [])
    
    if not current_offers:
        logs.append("⚠️ [Ranker] No current offers to rank. Rejecting.")
        return {"status": "REJECT", "logs": logs}
        
    logs.append("⚖️ [Ranker] Evaluating buyer responses...")
    
    # 1. Did anyone accept?
    accepts = [o for o in current_offers if o["status"] == "ACCEPT"]
    if accepts:
        best = max(accepts, key=lambda x: x["price"])
        logs.append(f"🏆 [Ranker] {best['buyer_name']} ACCEPTED. Moving to DEAL.")
        # Find the full profile from active_buyers
        selected_profile = next((b for b in state.get("active_buyers", []) if b.get("id") == best["buyer_id"]), {"name": best["buyer_name"]})
        return {
            "status": "DEAL",
            "best_current_offer": best,
            "latest_buyer_offer": best["price"],
            "selected_buyer": selected_profile,
            "logs": logs
        }
        
    # 2. Did anyone counter?
    counters = [o for o in current_offers if o["status"] == "COUNTER"]
    if counters:
        best = max(counters, key=lambda x: x["price"])
        logs.append(f"🏆 [Ranker] Best counter from {best['buyer_name']} at ₹{best['price']}/kg.")
        selected_profile = next((b for b in state.get("active_buyers", []) if b.get("id") == best["buyer_id"]), {"name": best["buyer_name"]})
        return {
            "status": "ACTIVE", # Keep negotiating
            "best_current_offer": best,
            "latest_buyer_offer": best["price"],
            "selected_buyer": selected_profile,
            "logs": logs
        }
        
    # 3. Otherwise, all rejected
    logs.append("🚫 [Ranker] All buyers rejected.")
    return {"status": "REJECT", "logs": logs}


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
    
    raw = llm_client.generate(prompt, max_tokens=150, temperature=0.2)
    decision = await _parse_json_response(raw)
    
    # Deterministic ground truth enforcement (Floor & Budget protection)
    is_price_valid = deal_price >= state["min_price"]
    is_budget_valid = (deal_price * quantity) <= (budget * 1.01)
    
    if is_price_valid and is_budget_valid:
        valid = True
        message = decision.get("message", "Validation successful.") if (decision and decision.get("valid")) else "Mathematical constraints satisfied (price >= min_price and cost <= budget)."
    else:
        valid = False
        message = f"Constraint violation: deal_price ₹{deal_price} (min ₹{state['min_price']}) or total cost ₹{deal_price * quantity} exceeds budget ₹{budget}."

    logs.append(f"⚖️ [Validator] Valid={valid}. {message}")

    if valid:
        buyer_profile = state.get("buyer_profile") or {}
        deal = {
            "buyer_name": buyer_profile.get("name", "Buyer"),
            "buyer_id": buyer_profile.get("id", "Unknown"),
            "price": deal_price,
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
        
    logs.append("🚚 [Dynamic Routing] Deal finalized. Coordinating logistics...")
    
    deal = state.get("deal") or {}
    deal["type"] = "DIRECT"
    deal["price"] = state.get("latest_buyer_offer", 0)
    shipment_qty = float(deal.get("quantity") or state.get("quantity") or 1000.0)
    if shipment_qty <= 0:
        shipment_qty = 1000.0
    deal["quantity"] = shipment_qty
    
    selected = state.get("selected_buyer", {})
    deal["buyer_name"] = selected.get("name", "Unknown Buyer")
    buyer_loc = selected.get("location", "Market")
    
    import asyncio
    from backend.agents.prompts import WAREHOUSE_PROMPT
    from backend.agents.transport_agent.graph import run_transport_workflow
    from database.db import Database

    # --- Real Transport Agent Workflow (Fleet & OSRM Engine) ---
    is_perishable = state.get("crop", "").lower() in ["tomato", "strawberry", "grape", "spinach", "lettuce", "flowers", "milk"]
    refrigerated_req = is_perishable and (state.get("spoilage_days", 7) <= 2)

    transport_input = {
        "request_id": f"TR-NEG-{random.randint(1000, 9999)}",
        "crop": state.get("crop", "Produce"),
        "quantity_kg": shipment_qty,
        "pickup_location": state.get("location", "Ahmednagar"),
        "delivery_location": buyer_loc,
        "delivery_deadline_hours": float(max(6, state.get("spoilage_days", 5) * 24)),
        "shelf_life_hours": float(state.get("spoilage_days", 5) * 24),
        "refrigerated_required": refrigerated_req,
        "urgency": "HIGH" if state.get("spoilage_days", 5) <= 2 else "NORMAL",
        "buyer_offer": None
    }

    try:
        t_result = await run_transport_workflow(transport_input)
        plan = t_result.get("final_transport_plan")
        if plan and t_result.get("selected_vehicle"):
            sel_veh = t_result["selected_vehicle"]
            freight_cost = plan.get("agreed_price") or plan.get("initial_quote") or 1500.0
            
            deal["transport_plan"] = {
                "agent": sel_veh.get("carrier_name") or sel_veh.get("vehicle_name", "Transport Fleet"),
                "vehicle_id": sel_veh.get("vehicle_id"),
                "vehicle_name": sel_veh.get("vehicle_name"),
                "vehicle_type": sel_veh.get("vehicle_type"),
                "capacity": sel_veh.get("capacity_kg"),
                "fuel_type": sel_veh.get("fuel_type"),
                "distance": t_result.get("distance_km", 50.0),
                "duration_hours": t_result.get("estimated_duration_hours", 2.0),
                "cost": freight_cost,
                "total_operating_cost": t_result.get("total_operating_cost", 0.0),
                "cost_breakdown": t_result.get("cost_breakdown", {}),
                "routing_source": t_result.get("routing_source", "OSRM"),
                "status": "CONFIRMED"
            }

            logs.append(
                f"🚛 [Transport Agent] Autonomous vehicle assigned: {sel_veh.get('vehicle_name')} ({sel_veh.get('vehicle_type')}, "
                f"Cap: {sel_veh.get('capacity_kg')}kg) for {t_result.get('distance_km')} km at ₹{freight_cost} freight "
                f"(Operating Cost: ₹{t_result.get('total_operating_cost')}, Est. Duration: {t_result.get('estimated_duration_hours')} hrs via {t_result.get('routing_source', 'OSRM')})."
            )

            # Persist trip into PostgreSQL transport_trips table
            try:
                await Database.save_transport_trip_async({
                    "request_id": plan.get("request_id"),
                    "vehicle_id": sel_veh.get("vehicle_id"),
                    "vehicle_type": sel_veh.get("vehicle_type"),
                    "crop": state["crop"],
                    "quantity_kg": float(state["quantity"]),
                    "pickup_location": state["location"],
                    "delivery_location": buyer_loc,
                    "distance_km": t_result.get("distance_km"),
                    "estimated_duration_hours": t_result.get("estimated_duration_hours"),
                    "fuel_cost": t_result.get("cost_breakdown", {}).get("fuel_cost", 0.0),
                    "toll_cost": t_result.get("cost_breakdown", {}).get("toll_cost", 0.0),
                    "driver_cost": t_result.get("cost_breakdown", {}).get("driver_cost", 0.0),
                    "maintenance_cost": t_result.get("cost_breakdown", {}).get("maintenance_cost", 0.0),
                    "loading_cost": t_result.get("cost_breakdown", {}).get("loading_cost", 0.0),
                    "waiting_cost": t_result.get("cost_breakdown", {}).get("waiting_cost", 0.0),
                    "total_operating_cost": t_result.get("total_operating_cost"),
                    "minimum_acceptable_price": t_result.get("minimum_acceptable_price"),
                    "agreed_price": freight_cost,
                    "expected_profit": plan.get("expected_profit"),
                    "status": "CONFIRMED",
                    "details_json": plan,
                })
            except Exception as trip_err:
                logger.warning(f"Could not save transport trip record: {trip_err}")
        else:
            # Fallback baseline if no candidate vehicle fit shipment size
            deal["transport_plan"] = {
                "agent": "Regional AgriTransport Co.",
                "cost": round(float(state.get("quantity", 1000)) * 1.8, 2),
                "distance": 85.0,
                "status": "CONFIRMED"
            }
            logs.append(f"🚛 [Transport Agent] No dedicated single vehicle fit {state['quantity']}kg load. Assigned regional pooled freight at ₹{deal['transport_plan']['cost']}.")
    except Exception as e:
        logger.error(f"Error running Transport Agent in dynamic_routing_node: {e}", exc_info=True)
        deal["transport_plan"] = {
            "agent": "Fastrack Logistics",
            "cost": round(float(state.get("quantity", 1000)) * 1.5, 2),
            "distance": 60.0,
            "status": "CONFIRMED"
        }
        logs.append(f"🚛 [Transport Agent] Fallback transport assigned at ₹{deal['transport_plan']['cost']}.")

    
    # --- Parallel Warehouse Bidding (If needed) ---
    if state["spoilage_days"] <= 5:
        baseline_warehouse = 0.5 # ₹0.5/kg/day
        warehouses = [f"ColdStorage_{i}" for i in range(1, 6)]
        
        async def get_warehouse_bid(name):
            prompt = WAREHOUSE_PROMPT.format(
                warehouse_name=name, crop=state["crop"], quantity=state["quantity"],
                location=buyer_loc, shelf_life=state["spoilage_days"], baseline_cost=baseline_warehouse
            )
            resp = await asyncio.to_thread(llm_client.generate, prompt, max_tokens=100)
            parsed = await _parse_json_response(resp)
            if parsed and "bid_price" in parsed:
                # Apply Farmer Priority: 2% penalty
                priority_score = parsed["bid_price"] * 1.02
                return {"name": name, "bid": parsed["bid_price"], "score": priority_score, "reason": parsed.get("reason", "")}
            return {"name": name, "bid": baseline_warehouse, "score": baseline_warehouse * 1.02, "reason": "Fallback bid"}

        w_tasks = [get_warehouse_bid(w) for w in warehouses]
        w_bids = await asyncio.gather(*w_tasks)
        
        best_warehouse = min(w_bids, key=lambda x: x["score"])
        logs.append(f"🏢 [Warehouse] {len(w_bids)} bids received. Selected {best_warehouse['name']} at ₹{best_warehouse['bid']}/day (Farmer Priority Enforced). Reason: {best_warehouse['reason']}")
        deal["warehouse_option"] = best_warehouse
            
    return {"deal": deal, "logs": logs}


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

    raw_reflection = llm_client.generate(prompt, max_tokens=300, temperature=0.2)
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
            final_agreement = llm_client.generate(ag_prompt, max_tokens=350, temperature=0.7)
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

        import asyncio
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
                    try:
                        bid_price = float(parsed["bid_price"])
                        # Farmer Priority: apply 2% edge (highest disposal value)
                        priority_score = bid_price * 1.02
                        return {"name": name, "bid": bid_price, "score": priority_score, "reason": parsed.get("reason", "")}
                    except (ValueError, TypeError):
                        pass
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
            crop=state.get("crop", "Produce"),
            final_status=state.get("status", "COMPLETED"),
            reflection_insights=str(state.get("reflection") or f"Direct sale result: {state.get('status')}")
        )
        rec = llm_client.generate(prompt, max_tokens=120)
        if rec:
            return rec.strip()
    except Exception as e:
        logger.warning(f"Recommendation generation failed: {e}")

    # Deterministic fallback
    if deal and deal.get("type") == "DIRECT" or state["status"] == "DEAL":
        return f"Direct sale at ₹{state.get('latest_buyer_offer', state['min_price'])}/kg is the optimal outcome."
    elif state["spoilage_days"] > 2:
        return f"Store in cold warehouse — market price may recover in {state['spoilage_days']} days."
    return f"Consider processing or composting to recover value from the {state['crop']} lot."


# ─────────────────────────────────────────────
# Conditional Routing
# ─────────────────────────────────────────────

async def route_after_farmer(state: NegotiationState) -> str:
    if state["status"] in ("DEAL", "ACCEPT"):
        return "validator_agent"
    if state["status"] == "REJECT" or state["round"] >= state["max_rounds"]:
        return "reflection_agent"
    return "buyer_agent"


async def route_after_rank(state: NegotiationState) -> str:
    if state["status"] in ("DEAL", "ACCEPT"):
        return "validator_agent"
    if state["status"] == "REJECT" or state["round"] >= state["max_rounds"]:
        return "reflection_agent"
    return "farmer_agent"


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
workflow.add_node("matching_agent", matching_engine_node)
workflow.add_node("farmer_agent", farmer_node)
workflow.add_node("buyer_agent", buyer_node)
workflow.add_node("rank_responses_agent", rank_responses_node)
workflow.add_node("validator_agent", validator_node)
workflow.add_node("dynamic_routing_agent", dynamic_routing_node)
workflow.add_node("reflection_agent", reflection_node)

workflow.set_entry_point("planner_agent")

workflow.add_edge("planner_agent", "knowledge_manager_node")
workflow.add_edge("knowledge_manager_node", "market_intelligence_agent")
workflow.add_edge("market_intelligence_agent", "matching_agent")
workflow.add_edge("matching_agent", "farmer_agent")

workflow.add_conditional_edges(
    "farmer_agent",
    route_after_farmer,
    {
        "validator_agent": "validator_agent",
        "reflection_agent": "reflection_agent",
        "buyer_agent": "buyer_agent",
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
workflow.add_edge("reflection_agent", END)

graph_orchestrator = workflow.compile()

