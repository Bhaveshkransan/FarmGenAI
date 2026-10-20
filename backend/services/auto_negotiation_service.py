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
    
    # Retrieve batch RAG context once with 1.5s timeout
    batch_rag_results = {}
    try:
        from backend.services.rag_service import rag_service
        rag_query = f"{crop} transport {pickup_location} to {delivery_location}"
        def _get_rag():
            mp = rag_service.query_collection("market_prices", rag_query, n_results=2)
            rm = rag_service.query_collection("reflection_memory", rag_query, n_results=2)
            return {"market_prices": mp, "reflection_memory": rm}
        batch_rag_results = await asyncio.wait_for(asyncio.to_thread(_get_rag), timeout=1.5)
    except Exception as e:
        logger.info(f"Batch RAG skipped/fallback: {e}")

    # Top 4 candidates for parallel negotiation
    top_candidates = scored_candidates[:4]

    negotiation_tasks = []
    for vehicle in top_candidates:
        negotiation_tasks.append(simulate_agent_negotiation(vehicle, pickup_location, delivery_location, crop, transport_request.get("buyer_offer"), batch_rag_results))

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
            reasoning = await asyncio.wait_for(
                asyncio.to_thread(llm_client.generate, prompt, max_tokens=100),
                timeout=2.0
            )
            winner["ai_reasoning"] = reasoning
        except Exception as e:
            logger.info(f"AI reasoning quick fallback used: {e}")
            winner["ai_reasoning"] = f"Transporter {winner['vehicle']['vehicle_name']} ({winner['vehicle']['vehicle_type']}) secured the most cost-efficient freight rate of ₹{winner['agreed_price']} with high transit reliability."

    return {
        "success": True,
        "winner": winner,
        "all_negotiations": results
    }


async def simulate_agent_negotiation(vehicle: Dict[str, Any], pickup: str, delivery: str, crop: str, buyer_offer: float = None, rag_results: Dict[str, Any] = None) -> Dict[str, Any]:
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
    market_average = total_cost * 1.20
    stakeholder_budget = buyer_offer if buyer_offer else round(total_cost * 1.10)
    
    # Generate the entire organic negotiation transcript in one LLM call for speed and realism
    v_name = vehicle.get('vehicle_name', 'Truck')
    v_type = vehicle.get('vehicle_type', 'Vehicle')
    
    rag_query = f"{crop} transport {pickup} to {delivery} {distance_km}km {v_type}"
    rag_results = rag_results or {}
        
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
        llm_response = await asyncio.wait_for(
            asyncio.to_thread(llm_client.generate, prompt, max_tokens=600),
            timeout=3.5
        )
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
            if transcript:
                transcript[-1]["status"] = "REJECTED"
                transcript[-1]["message"] += " Actually, I cannot go below my floor operating cost."
            
    except Exception as e:
        logger.info(f"Fast deterministic organic transcript used for {v_name}: {e}")
        # High quality multi-round negotiation fallback
        mid_offer = round((stakeholder_budget + target_price) / 2)
        final_deal_price = max(mid_offer, round(floor_price * 1.05))
        is_deal = final_deal_price >= floor_price
        
        fuel_cost = round(cost_result.get('cost_breakdown', {}).get('fuel_cost', total_cost * 0.5))
        toll_cost = round(cost_result.get('cost_breakdown', {}).get('toll_cost', total_cost * 0.15))

        transcript = [
            {
                "round": 1,
                "stakeholder_offer": stakeholder_budget,
                "stakeholder_message": f"I need to transport {crop} from {pickup} to {delivery} ({distance_km}km). Can we do ₹{stakeholder_budget}?",
                "stakeholder_reasoning": ["Initial budget boundary", "Market bulk rate parity"],
                "transporter_counter": target_price,
                "status": "COUNTERED",
                "message": f"₹{stakeholder_budget} cannot cover our diesel overhead (₹{fuel_cost}) and NH highway tolls (₹{toll_cost}). Our baseline is ₹{target_price}.",
                "transporter_reasoning": [f"Fuel overhead ₹{fuel_cost}", f"Toll tariffs ₹{toll_cost}", "Fleet margin defense"]
            },
            {
                "round": 2,
                "stakeholder_offer": mid_offer,
                "stakeholder_message": f"We can adjust for fuel. Can we meet closer to ₹{mid_offer} for expedited loading?",
                "stakeholder_reasoning": ["Middle ground concession", "Expedited dispatch priority"],
                "transporter_counter": final_deal_price,
                "status": "COUNTERED" if not is_deal else "ACCEPTED",
                "message": f"If loading is ready at origin without dock delays, I can offer our fleet discount at ₹{final_deal_price}." if is_deal else f"₹{mid_offer} is still below our minimum floor price of ₹{floor_price}.",
                "transporter_reasoning": ["Capacity utilization concession", "Floor cost boundary check"]
            },
            {
                "round": 3,
                "stakeholder_offer": final_deal_price,
                "stakeholder_message": f"Agreed. We confirm ₹{final_deal_price} with guaranteed transit timeline.",
                "stakeholder_reasoning": ["Price lock within operating tolerance"],
                "transporter_counter": final_deal_price,
                "status": "ACCEPTED" if is_deal else "REJECTED",
                "message": f"Confirmed! Deal accepted at ₹{final_deal_price}. Vehicle assigned and ready for pickup." if is_deal else "Cannot bridge margin gap. Route rejected.",
                "transporter_reasoning": ["Margin secured above floor threshold", "Contract finalized"]
            }
        ]
        status = "ACCEPTED" if is_deal else "REJECTED"
        agreed_price = final_deal_price if status == "ACCEPTED" else None

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
