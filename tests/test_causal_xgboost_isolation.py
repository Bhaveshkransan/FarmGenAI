"""
tests/test_causal_xgboost_isolation.py

Controlled One-Variable Causal Isolation Test for XGBoost Forecast Influence.
Strictly addresses Audit Gap #7:
Holding ALL other parameters identical:
- crop: 'Onion'
- quantity: 1000
- location: 'Nashik'
- shelf_life (spoilage_days): 14
- weather: Low precipitation (< 5mm)
- current market_price: 20.0
- min_price: 18.0

Varying ONLY the XGBoost forecast price:
Experiment 1: Forecast = 23.61 (> market_price * 1.05 = 21.0) -> Decision MUST be HOLD -> Route to hold_decision_node
Experiment 2: Forecast = 18.00 (< market_price * 1.05 = 21.0) -> Decision MUST be SELL -> Route to matching_agent
"""

import pytest
from unittest.mock import patch, MagicMock
from backend.agents.graph_orchestrator import (
    market_intelligence_node,
    route_after_market_intelligence,
    NegotiationState
)

@pytest.mark.asyncio
async def test_xgboost_causal_isolation():
    # Base invariant state (ALL variables strictly controlled and identical)
    base_state: NegotiationState = {
        "listing_id": "test_causal_xgboost_01",
        "crop": "Onion",
        "quantity": 1000,
        "base_price": 18.0,
        "min_price": 18.0,
        "market_price": 20.0,
        "spoilage_days": 14,
        "location": "Nashik",
        "current_round": 0,
        "max_rounds": 3,
        "status": "ACTIVE",
        "farmer_id": "farmer_nashik_01",
        "execution_mode": "FULL_SUPPLY_CHAIN",
        "logs": [],
        "weather": {
            "location_resolved": "Nashik, Maharashtra",
            "temperature_c": 28.0,
            "precipitation_mm": 0.0,
            "wind_speed_kmh": 12.0
        },
    }

    # -------------------------------------------------------------
    # Experiment A: XGBoost Forecast = 23.61 (+18.05% expected surge)
    # -------------------------------------------------------------
    mock_ml_high = MagicMock(return_value={
        "forecast_price": 23.61,
        "summary": "XGBoost 7-day forecast: ₹23.61/kg (+18.05% vs current modal ₹20.0/kg)"
    })

    with patch("backend.services.price_prediction_service.predict_price_xgboost", mock_ml_high), \
         patch("backend.agents.graph_orchestrator.llm_client.generate", return_value="Market steady."):
        
        result_high = await market_intelligence_node(dict(base_state))
        branch_high = await route_after_market_intelligence(result_high)

        # Assert causal outcome: High forecast forces HOLD
        assert result_high["sell_hold_decision"] == "HOLD", "Forecast 23.61 > 21.0 must trigger HOLD"
        assert branch_high == "hold_decision_node", "HOLD decision must route to hold_decision_node"
        assert "Holding may yield higher returns subject to storage" in result_high["sell_hold_reasoning"]

    # -------------------------------------------------------------
    # Experiment B: XGBoost Forecast = 18.00 (-10.0% expected decline)
    # ONLY difference is the forecast output; all inputs identical
    # -------------------------------------------------------------
    mock_ml_low = MagicMock(return_value={
        "forecast_price": 18.00,
        "summary": "XGBoost 7-day forecast: ₹18.00/kg (-10.0% vs current modal ₹20.0/kg)"
    })

    with patch("backend.services.price_prediction_service.predict_price_xgboost", mock_ml_low), \
         patch("backend.agents.graph_orchestrator.llm_client.generate", return_value="Market steady."):
        
        result_low = await market_intelligence_node(dict(base_state))
        branch_low = await route_after_market_intelligence(result_low)

        # Assert causal outcome: Lower forecast forces SELL
        assert result_low["sell_hold_decision"] == "SELL", "Forecast 18.00 <= 21.0 must trigger SELL"
        assert branch_low == "matching_agent", "SELL decision must route to matching_agent"
        assert "Prompt execution minimizes spoilage risk" in result_low["sell_hold_reasoning"]

    print("SUCCESS: XGBoost causal isolation verified under strict one-variable control.")
