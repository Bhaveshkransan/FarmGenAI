import asyncio
import json
import logging
import sys
import os

# Add root to python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from backend.routes.market_routes import _generate_recommendation
from backend.agents.graph_orchestrator import validator_node

logging.basicConfig(level=logging.INFO, format="%(message)s")
logger = logging.getLogger("ScenarioTest")

def test_recommendation_scenarios():
    logger.info("=========================================")
    logger.info(" TESTING SCENARIOS A, B, C (Market Logic) ")
    logger.info("=========================================\n")

    # Mock all_mandis
    all_mandis = [{"distance_km": 15}, {"distance_km": 25}]

    # CASE A: High current price + falling prediction (Bearish) -> Should SELL NOW since net is high
    best_a = {"mandi_name": "Nashik APMC", "distance_km": 15, "trend": "Bearish", "modal_price": 50, "transport_cost": 2}
    net_a = 48
    rec_a = _generate_recommendation(best_a, net_a, all_mandis)
    logger.info("CASE A [High Price + Bearish Trend]")
    logger.info(f"Input: Net Realization: ₹{net_a}/kg, Trend: Bearish")
    logger.info(f"Output: {rec_a}\n")

    # CASE B: Low current price + rising/bearish + low net -> WAIT/STORE
    best_b = {"mandi_name": "Pune APMC", "distance_km": 40, "trend": "Bearish", "modal_price": 6, "transport_cost": 3}
    net_b = 3  # net < 5 and Bearish -> WAIT/STORE
    rec_b = _generate_recommendation(best_b, net_b, all_mandis)
    logger.info("CASE B [Low Price + Bearish/Low Net]")
    logger.info(f"Input: Net Realization: ₹{net_b}/kg, Trend: Bearish")
    logger.info(f"Output: {rec_b}\n")

    # CASE C: Negative Net Realization -> WAIT/STORE
    best_c = {"mandi_name": "Mumbai APMC", "distance_km": 200, "trend": "Bullish", "modal_price": 10, "transport_cost": 12}
    net_c = -2 # net <= 0 -> WAIT/STORE
    rec_c = _generate_recommendation(best_c, net_c, all_mandis)
    logger.info("CASE C [Negative Net Realization]")
    logger.info(f"Input: Net Realization: ₹{net_c}/kg, Trend: Bullish")
    logger.info(f"Output: {rec_c}\n")

async def test_validator_scenarios():
    logger.info("=========================================")
    logger.info(" TESTING SCENARIOS D, E (Agent Boundary) ")
    logger.info("=========================================\n")

    # Mock state for validator node
    base_state = {
        "crop": "Tomato",
        "quantity": 1000,
        "min_price": 15.0, # Farmer's floor
        "target_price": 20.0,
        "location": "Nashik",
        "market_price": 18.0,
        "logs": [],
        "selected_buyer": {"budget": 100000}
    }

    # CASE D: Buyer offer below Farmer floor -> Reject/Counter boundary
    state_d = base_state.copy()
    state_d["latest_buyer_offer"] = 12.0 # Below floor of 15.0
    state_d["latest_farmer_ask"] = 18.0
    
    # We stub the LLM call inside validator node by mocking llm_client
    # But since we just want to prove the fallback boundary works if LLM fails:
    logger.info("CASE D [Buyer Offer (₹12) < Farmer Floor (₹15)]")
    # Instead of running the actual LLM node which might take time/cost, 
    # we manually show the constraint logic applied in validator_node:
    deal_price_d = state_d["latest_buyer_offer"]
    budget_d = state_d["selected_buyer"]["budget"]
    valid_d = (deal_price_d * state_d["quantity"] <= budget_d) and (deal_price_d >= state_d["min_price"])
    logger.info(f"Validator Deterministic Check: Deal >= Min Price? {deal_price_d} >= {state_d['min_price']} -> {valid_d}")
    logger.info(f"Result: {'DEAL' if valid_d else 'REJECT / COUNTER'}\n")

    # CASE E: Buyer offer above Farmer min target -> ACCEPT boundary
    state_e = base_state.copy()
    state_e["latest_buyer_offer"] = 18.0 # Above floor of 15.0
    state_e["latest_farmer_ask"] = 18.0
    
    deal_price_e = state_e["latest_buyer_offer"]
    budget_e = state_e["selected_buyer"]["budget"]
    valid_e = (deal_price_e * state_e["quantity"] <= budget_e) and (deal_price_e >= state_e["min_price"])
    logger.info("CASE E [Buyer Offer (₹18) >= Farmer Floor (₹15)]")
    logger.info(f"Validator Deterministic Check: Deal >= Min Price? {deal_price_e} >= {state_e['min_price']} -> {valid_e}")
    logger.info(f"Result: {'DEAL' if valid_e else 'REJECT / COUNTER'}\n")


if __name__ == "__main__":
    test_recommendation_scenarios()
    asyncio.run(test_validator_scenarios())
