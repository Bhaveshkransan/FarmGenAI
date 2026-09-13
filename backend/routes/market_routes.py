"""
market_routes.py — MandiMitra / Market Intelligence API
Implements the Net Realisable Price formula from the research document:

  Net Realisable Price = Selling Price − Transport Cost − Handling Cost − Storage Cost − Other Costs

Endpoints:
  GET /api/v1/market-intelligence/compare   — Mandi comparison within radius
  GET /api/v1/market-intelligence/price     — Single crop live price lookup
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Optional
import asyncio
import os
import pickle
import pandas as pd
from datetime import datetime, timedelta
from backend.services.external_apis import MandiAPIClient, OpenMeteoClient
from backend.services.rag_service import rag_service
from llm.llm_client import client as llm_client

router = APIRouter(prefix="/market-intelligence", tags=["Market Intelligence"])


@router.get("/compare")
async def compare_mandis(
    crop: str = Query(..., description="Crop name, e.g. Tomato, Onion, Wheat"),
    lat: float = Query(..., description="Farmer's latitude"),
    lon: float = Query(..., description="Farmer's longitude"),
    radius_km: float = Query(500.0, description="Search radius in km (default 500)"),
    quantity_kg: float = Query(1000.0, description="Quantity to sell in kg"),
    handling_cost: float = Query(0.5, description="Handling/loading cost per kg (₹)"),
    storage_cost: float = Query(0.0, description="Storage cost per kg (₹)"),
):
    """
    MandiMitra — Compare government mandis within radius.

    Returns per-mandi:
    - Distance (km)
    - Modal price, Min price, Max price
    - Transport cost (₹/kg) — calculated as ₹2 base + ₹0.05/km
    - Net Realisable Price = Modal − Transport − Handling − Storage
    - Market trend (Bullish / Stable / Bearish)
    - Data source (data.gov.in / Farmer.in / Mock)

    Also returns the AI recommendation (SELL NOW / WAIT/STORE).
    """
    try:
        nearby_mandis = await MandiAPIClient.get_nearby_mandis(lat, lon, crop, radius_km)

        if not nearby_mandis:
            return {
                "success": True,
                "data": {
                    "mandis": [],
                    "best_option": None,
                    "recommendation": "No active mandis found in this radius. Consider direct buyer negotiation or storage.",
                    "data_source": "None",
                }
            }

        enriched = []
        best = None
        highest_net = float("-inf")
        data_source = nearby_mandis[0].get("source", "Unknown") if nearby_mandis else "Unknown"

        for m in nearby_mandis:
            distance = m["distance_km"]
            modal = m["price_per_kg"]

            # Net Realisable Price formula (from research doc §9)
            transport_cost = round(2.0 + (distance * 0.05), 2)
            net = round(modal - transport_cost - handling_cost - storage_cost, 2)

            # Projected revenue for the quantity
            gross_revenue = round(modal * quantity_kg, 2)
            net_revenue   = round(net * quantity_kg, 2)

            entry = {
                "mandi_name":      m["mandi"],
                "state":           m.get("state", ""),
                "district":        m.get("district", ""),
                "variety":         m.get("variety", "General"),
                "distance_km":     distance,
                "min_price":       m.get("min_price", round(modal * 0.90, 2)),
                "max_price":       m.get("max_price", round(modal * 1.10, 2)),
                "modal_price":     modal,
                "transport_cost":  transport_cost,
                "handling_cost":   handling_cost,
                "storage_cost":    storage_cost,
                "net_realization": net,
                "gross_revenue":   gross_revenue,
                "net_revenue":     net_revenue,
                "trend":           m.get("trend", "Stable"),
                "arrival_date":    m.get("arrival_date", "Today"),
                "source":          m.get("source", "Unknown"),
                "lat":             m.get("lat", lat),
                "lon":             m.get("lon", lon),
            }
            enriched.append(entry)

            if net > highest_net:
                highest_net = net
                best = entry

        # ── AI Recommendation ────────────────────────────────────────────────
        recommendation = _generate_recommendation(best, highest_net, enriched)

        return {
            "success": True,
            "data": {
                "mandis":          enriched,
                "best_option":     best,
                "recommendation":  recommendation,
                "data_source":     data_source,
                "formula":         "Net Realisable Price = Modal Price − Transport Cost − Handling Cost − Storage Cost",
            }
        }

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/price")
async def get_crop_price(
    crop: str = Query(..., description="Crop name"),
    location: str = Query("Nashik", description="Location / mandi name"),
    base_price: float = Query(0.0, description="Your expected base price for trend comparison"),
):
    """
    Single crop price lookup with min / max / modal from live sources.
    Returns trend and volatility vs your expected price.
    """
    try:
        result = await MandiAPIClient.get_live_price(crop, location, base_price)
        weather = await OpenMeteoClient.get_weather(location)
        return {
            "success": True,
            "data": {
                "price_data": result,
                "weather": weather,
            }
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


# ── Helpers ──────────────────────────────────────────────────────────────────

def _generate_recommendation(best: Optional[dict], highest_net: float, all_mandis: list) -> str:
    if not best:
        return "Insufficient data to generate a recommendation."

    mandi = best["mandi_name"]
    distance = best["distance_km"]
    trend = best["trend"]
    net = highest_net

    # Critical scenarios
    if net <= 0:
        return (
            f"WAIT/STORE. Net realization across all nearby mandis is negative after transport costs. "
            f"Consider storage or direct buyer negotiation to avoid losses."
        )

    if trend == "Bearish" and net < 5:
        return (
            f"WAIT/STORE. Prices at {mandi} are on a bearish trend "
            f"and net realization (₹{net}/kg) is critically low. "
            f"Consider storage for 5–7 days or explore direct buyers."
        )

    base = f"SELL NOW at {mandi}."

    if distance == 0 or distance < 10:
        base += f" Your local mandi offers the best net realization at ₹{net}/kg."
    elif distance > 100:
        base += (
            f" Despite the {distance}km distance, it offers the highest net profit "
            f"at ₹{net}/kg after transport costs of ₹{best['transport_cost']}/kg."
        )
    else:
        base += f" Best net realization: ₹{net}/kg (Modal ₹{best['modal_price']} − ₹{best['transport_cost']} transport)."

    if trend == "Bullish":
        base += " 📈 Prices are trending upward — good time to sell."

    nearby_count = len([m for m in all_mandis if m["distance_km"] <= 50])
    if nearby_count > 1:
        base += f" {nearby_count} mandis are within 50km — compare before loading the truck."

    return base

@router.get("/insights")
async def get_market_insights(
    crop: str = Query(..., description="Crop name"),
    location: str = Query("Maharashtra", description="Location / district name"),
):
    """
    RAG-augmented market insight for Create Listing form.
    Provides live price + historical RAG context + LLM Sell/Hold recommendation.
    """
    try:
        # 1. Fetch live market price
        live_price_data = await MandiAPIClient.get_live_price(crop, location, 0.0)
        current_modal_price = live_price_data.get("modal_price", 0)
        
        # 2. Query RAG for historical mandi prices and crop knowledge
        mandi_history = await rag_service.query_mandi_records(query_text=crop, crop=crop, n_results=3)
        crop_knowledge = rag_service.query_crop_knowledge(query_text=f"{crop} market trends seasonality", crop=crop, n_results=2)
        
        historical_context = ""
        if mandi_history and mandi_history.get("documents") and mandi_history["documents"][0]:
            historical_context = "\n".join(mandi_history["documents"][0])
            
        knowledge_context = ""
        if crop_knowledge:
            knowledge_context = "\n".join([doc["text"] for doc in crop_knowledge])
            
        # 2.5 Optional: ML Price Prediction
        ml_prediction = "No prediction available."
        ml_forecast_price = None
        ml_forecast_direction = None
        try:
            model_path = os.path.join(os.path.dirname(__file__), '..', 'models', 'xgboost_price_model.pkl')
            if os.path.exists(model_path):
                with open(model_path, 'rb') as f:
                    model_data = pickle.load(f)
                xgb_model = model_data['model']
                crop_encoder = model_data['crop_encoder']
                dist_encoder = model_data['district_encoder']
                features = model_data['features']
                
                # We need to simulate the features for "next week"
                target_date = datetime.now() + timedelta(days=7)
                month = target_date.month
                day_of_week = target_date.weekday()
                day_of_year = target_date.timetuple().tm_yday
                
                crop_val = crop_encoder.transform([crop])[0] if crop in crop_encoder.classes_ else 0
                dist_val = dist_encoder.transform([location])[0] if location in dist_encoder.classes_ else 0
                
                # Rough estimates for lag based on current modal price
                input_df = pd.DataFrame([{
                    'crop_encoded': crop_val,
                    'district_encoded': dist_val,
                    'month': month,
                    'day_of_week': day_of_week,
                    'day_of_year': day_of_year,
                    'arrival_mt': 100.0, # assumed average arrival
                    'price_7d_ago': current_modal_price,
                    'price_30d_ago': current_modal_price
                }])[features]
                
                pred_price = xgb_model.predict(input_df)[0]
                trend_dir = "increase" if pred_price > current_modal_price else "decrease"
                ml_forecast_price = round(float(pred_price), 2)
                ml_forecast_direction = "up" if pred_price > current_modal_price else "down"
                ml_prediction = f"XGBoost ML Model forecasts the price will {trend_dir} to \u20b9{pred_price:.2f}/kg in 7 days."
        except Exception as e:
            ml_prediction = f"ML Prediction failed: {str(e)}"
            
        # 3. Prompt LLM for recommendation
        prompt = f"""
You are an expert Agricultural Market Analyst AI for AgriNegotiator.
A farmer is planning to list their crop: {crop} in {location}.

[LIVE MARKET DATA]
Current Modal Price: ₹{current_modal_price}/kg
Trend: {live_price_data.get('trend', 'Stable')}

[XGBOOST ML FORECAST]
{ml_prediction}

[HISTORICAL RAG DATA]
{historical_context}

[CROP KNOWLEDGE & SEASONALITY]
{knowledge_context}

Based on the above, provide a short, punchy, 2-3 sentence recommendation for the farmer on whether they should SELL NOW, HOLD/STORE, or PROCESS. 
Focus on actionable advice based on the ML Forecast and market trends. Do not use markdown formatting.
"""
        recommendation = await asyncio.to_thread(llm_client.generate, prompt, max_tokens=150, temperature=0.3)
        
        return {
            "success": True,
            "data": {
                "crop": crop,
                "location": location,
                "live_price": current_modal_price,
                "trend": live_price_data.get("trend", "Stable"),
                "ml_forecast_price": ml_forecast_price,
                "ml_forecast_direction": ml_forecast_direction,
                "ml_prediction": ml_prediction,
                "recommendation": recommendation.strip()
            }
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
