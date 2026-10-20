import logging
import asyncio
from typing import Dict, Any, List
from backend.services.vehicle_service import filter_suitable_vehicles
from backend.services.recommendation_service import recommend_vehicles_for_request
from backend.services.transport_cost_service import calculate_transportation_cost
from backend.services.routing_service import calculate_transport_route
from llm.llm_client import LLMClient
from backend.agents.transport_agent.prompts import TRANSPORT_NEGOTIATION_PROMPT

logger = logging.getLogger("AutoNegotiationService")
llm_client = LLMClient()

async def run_parallel_negotiation(transport_request: Dict[str, Any]) -> Dict[str, Any]:
    """
    Orchestrates automated agent-to-agent negotiation for the top recommended vehicles.
    """
    quantity_kg = float(transport_request.get("quantity_kg", 1000.0))
    refrigerated_required = bool(transport_request.get("refrigerated_required", False))
    pickup_location = transport_request.get("pickup_location", "Ahmednagar")
    delivery_location = transport_request.get("delivery_location", "Pune")
    crop = transport_request.get("crop", "Produce")

    # 1. Filter and Recommend
    filter_res = await filter_suitable_vehicles(
        quantity_kg=quantity_kg,
        refrigerated_required=refrigerated_required
    )
    
    if not filter_res.get("success"):
        return {
            "success": False,
            "message": "No vehicles meet the basic hard constraints.",
            "candidates": []
        }

    candidates = filter_res.get("candidates", [])
    scored_candidates = recommend_vehicles_for_request(candidates, transport_request)
    
    # Take top 7 for parallel negotiation
    top_candidates = scored_candidates[:7]
    
    negotiation_tasks = []
    for vehicle in top_candidates:
        negotiation_tasks.append(simulate_agent_negotiation(vehicle, pickup_location, delivery_location, crop, transport_request.get("buyer_offer")))

    results = await asyncio.gather(*negotiation_tasks)
    
    # 2. Find the winner (Successful deal with the lowest agreed price)
    successful_deals = [r for r in results if r["status"] == "ACCEPTED"]
    winner = None
    if successful_deals:
        # Sort by agreed price ascending, then by recommendation score descending
        successful_deals.sort(key=lambda x: (x["agreed_price"], -x["vehicle"]["recommendation_score"]))
        winner = successful_deals[0]
        
        # Generate AI Reasoning for the winner
        try:
            prompt = (
                f"Explain concisely in 2 sentences why we chose the {winner['vehicle']['vehicle_name']} "
                f"({winner['vehicle']['vehicle_type']}) for ₹{winner['agreed_price']} for the "
                f"{pickup_location} to {delivery_location} route. Emphasize cost-efficiency."
            )
            reasoning = await asyncio.to_thread(llm_client.generate, prompt, max_tokens=100)
            winner["ai_reasoning"] = reasoning
        except Exception as e:
            logger.warning(f"Failed to generate AI reasoning: {e}")
            winner["ai_reasoning"] = f"This transporter offered the most competitive agreed price of ₹{winner['agreed_price']}."

    return {
        "success": True,
        "winner": winner,
        "all_negotiations": results
    }


async def simulate_agent_negotiation(vehicle: Dict[str, Any], pickup: str, delivery: str, crop: str, buyer_offer: float = None) -> Dict[str, Any]:
    """Simulates a rapid 3-round negotiation between Stakeholder Agent and Transport Agent."""
    
    # 1. Calculate Route & Costs (Transport Agent's perspective)
    route_info = calculate_transport_route(pickup, delivery, vehicle.get("current_location", pickup))
    distance_km = route_info["distance_km"]
    
    is_perishable = crop.lower() in {"tomato", "banana", "strawberry", "grape", "mango", "milk"}
    cost_result = await calculate_transportation_cost(
        vehicle=vehicle,
        distance_km=distance_km,
        estimated_duration_hours=route_info["estimated_duration_hours"],
        deadhead_km=route_info["deadhead_km"],
        is_perishable=is_perishable
    )

    floor_price = cost_result["minimum_acceptable_price"]
    initial_quote = cost_result["initial_quote"]
    target_price = cost_result["target_price"]
    total_cost = cost_result["total_operating_cost"]

    # 2. Stakeholder Agent's perspective (wants a deal, but has a budget)
    # Assume market average is total_cost + 20%. Stakeholder wants it for total_cost + 10%
    market_average = total_cost * 1.20
    stakeholder_budget = total_cost * 1.10
    
    market_average = total_cost * 1.20
    stakeholder_budget = buyer_offer if buyer_offer else round(total_cost * 1.10)
    
    # Generate the entire organic negotiation transcript in one LLM call for speed and realism
    v_name = vehicle.get('vehicle_name', 'Truck')
    v_type = vehicle.get('vehicle_type', 'Vehicle')
    
    # RAG Retrieval
    from backend.services.rag_service import rag_service
    rag_query = f"{crop} transport {pickup} to {delivery} {distance_km}km {v_type} freight handling shelf life negotiation"
    rag_results = {}
    try:
        mp = rag_service.query_collection("market_prices", rag_query, n_results=3)
        rm = rag_service.query_collection("reflection_memory", rag_query, n_results=3)
        ck = rag_service.query_collection("crop_knowledge", rag_query, n_results=3)
        tk = rag_service.query_collection("transport_knowledge", rag_query, n_results=3)

        def _fmt(res):
            fmt = []
            if isinstance(res, dict) and "documents" in res:
                docs = res.get("documents", [[]])[0]
                metas = res.get("metadatas", [[]])[0]
                for i in range(len(docs)):
                    fmt.append({"text": docs[i], "metadata": metas[i] if i < len(metas) else {}})
            else:
                fmt = res if isinstance(res, list) else []
            return fmt

        rag_results["market_prices"] = _fmt(mp)
        rag_results["reflection_memory"] = _fmt(rm)
        rag_results["crop_knowledge"] = _fmt(ck)
        rag_results["transport_knowledge"] = _fmt(tk)
    except Exception as e:
        logger.warning(f"Auto Negotiation RAG Retrieval failed: {e}")
        
    import json
    
    prompt = f"""
    Simulate a realistic, organic business negotiation between a Stakeholder (who wants to transport {vehicle.get('capacity_kg', 1000)}kg of {crop} from {pickup} to {delivery} - {distance_km}km) and a Transporter Agent owning a {v_name} ({v_type}).

    Constraints:
    - Stakeholder's initial offer: ₹{stakeholder_budget}
    - Transporter's absolute minimum floor price (secret): ₹{floor_price}
    - Transporter's target price: ₹{target_price}
    - Max Rounds: up to 5.
    
    RAG CONTEXT (Real World Knowledge):
    - Strategies: {json.dumps(rag_results.get("reflection_memory", [])[:2])}
    - Transport Logistics: {json.dumps(rag_results.get("transport_knowledge", [])[:2])}
    - Crop Knowledge: {json.dumps(rag_results.get("crop_knowledge", [])[:2])}
    
    Rules for Realism & Maximum Profit:
    - YOU ARE THE TRANSPORTER AGENT. Your primary objective is to MAXIMIZE PROFIT.
    - Do NOT jump straight to the floor price. You should aggressively defend your profit margin (mentioning fuel costs of ₹{round(cost_result['cost_breakdown']['fuel_cost'])}, tolls of ₹{round(cost_result['cost_breakdown']['toll_cost'])}, vehicle wear and tear, and high market demand).
    - Use the RAG CONTEXT knowledge in your transporter reasoning and messages.
    - NEVER, UNDER ANY CIRCUMSTANCES, ACCEPT A DEAL BELOW YOUR ABSOLUTE MINIMUM FLOOR PRICE (₹{floor_price}). If the stakeholder refuses to meet this, the deal MUST be "REJECTED".
    - The Stakeholder should argue (mentioning market rates, bulk deals), but you must remain firm on securing high margins.
    - It can end in "ACCEPTED" (ONLY if they agree on a price >= {floor_price}) or "REJECTED" (if Stakeholder refuses to go above {floor_price}).

    Return ONLY a valid JSON object matching exactly this structure:
    {{
        "transcript": [
            {{
                "round": 1,
                "stakeholder_offer": 4500,
                "stakeholder_message": "I need to transport 1000kg. Can you do 4500?",
                "stakeholder_reasoning": ["Market budget limit", "High volume shipment"],
                "transporter_counter": 5800,
                "status": "COUNTERED",
                "message": "I cannot accept 4500. My fuel alone is 3000. My counter is 5800.",
                "transporter_reasoning": ["Fuel overhead", "Maintenance markup"]
            }}
        ],
        "final_status": "ACCEPTED",
        "final_agreed_price": 5500
    }}
    (Make sure it is valid JSON, no markdown formatting or backticks around it).
    """
    
    try:
        llm_response = await asyncio.to_thread(llm_client.generate, prompt, max_tokens=1500)
        import json, re
        
        # Regex to find JSON object to prevent markdown parsing errors
        json_match = re.search(r'\{.*\}', llm_response, re.DOTALL)
        if json_match:
            json_str = json_match.group()
        else:
            json_str = llm_response
            
        data = json.loads(json_str)
        transcript = data.get("transcript", [])
        status = data.get("final_status", "REJECTED")
        agreed_price = data.get("final_agreed_price")
        
        # Failsafe logic
        if status == "ACCEPTED" and agreed_price and agreed_price < floor_price:
            status = "REJECTED"
            agreed_price = None
            transcript[-1]["status"] = "REJECTED"
            transcript[-1]["message"] += " Actually, I miscalculated. I cannot go below my floor price."
            
    except Exception as e:
        logger.warning(f"Organic LLM negotiation failed: {e}")
        # Fallback transcript
        transcript = [
            {"round": 1, "stakeholder_offer": stakeholder_budget, "stakeholder_message": f"I need to transport {crop}. Can you do ₹{stakeholder_budget}?", "stakeholder_reasoning": ["Initial floor budget"], "transporter_counter": target_price, "status": "COUNTERED", "message": f"Your offer of ₹{stakeholder_budget} is too low. My target is ₹{target_price}.", "transporter_reasoning": ["Target pricing baseline"]},
            {"round": 2, "stakeholder_offer": round((stakeholder_budget + target_price)/2), "stakeholder_message": f"How about we meet in the middle at ₹{round((stakeholder_budget + target_price)/2)}?", "stakeholder_reasoning": ["Compromise formulation"], "transporter_counter": floor_price, "status": "ACCEPTED" if round((stakeholder_budget + target_price)/2) >= floor_price else "REJECTED", "message": "Deal.", "transporter_reasoning": ["Acceptable margin threshold"]}
        ]
        status = "ACCEPTED" if round((stakeholder_budget + target_price)/2) >= floor_price else "REJECTED"
        agreed_price = round((stakeholder_budget + target_price)/2) if status == "ACCEPTED" else None

    return {
        "vehicle": vehicle,
        "status": status,
        "agreed_price": agreed_price,
        "transcript": transcript,
        "route": route_info,
        "rag_query": rag_query,
        "rag_results": rag_results,
        "pricing_rules": {
            "floor_price": floor_price,
            "market_average": market_average,
            "target_price": target_price,
            "initial_quote": initial_quote
        }
    }
