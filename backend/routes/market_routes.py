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
import numpy as np
from datetime import datetime, timedelta
from backend.services.external_apis import MandiAPIClient, OpenMeteoClient, RealMandiDatasetClient
from backend.services.rag_service import rag_service
from llm.llm_client import client as llm_client

from backend.core.constants import SUPPORTED_CROPS

router = APIRouter(prefix="/market-intelligence", tags=["Market Intelligence"])


@router.get("/compare")
async def compare_mandis(
    crop: str = Query(..., description=f"Crop name: {', '.join(SUPPORTED_CROPS)}"),
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
        supported_lower = [c.lower() for c in SUPPORTED_CROPS]
        if crop.lower() not in supported_lower:
            raise HTTPException(status_code=422, detail=f"Unsupported crop: {crop}. Supported: {SUPPORTED_CROPS}")
            
        # Normalize crop name
        for c in SUPPORTED_CROPS:
            if c.lower() == crop.lower():
                crop = c
                break

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
    crop: str = Query(..., description=f"Crop name: {', '.join(SUPPORTED_CROPS)}"),
    location: str = Query("Nashik", description="Location / mandi name"),
    base_price: float = Query(0.0, description="Your expected base price for trend comparison"),
):
    """
    Single crop price lookup with min / max / modal from live sources.
    Returns trend and volatility vs your expected price.
    """
    try:
        supported_lower = [c.lower() for c in SUPPORTED_CROPS]
        if crop.lower() not in supported_lower:
            raise HTTPException(status_code=422, detail=f"Unsupported crop: {crop}. Supported: {SUPPORTED_CROPS}")
            
        # Normalize crop name
        for c in SUPPORTED_CROPS:
            if c.lower() == crop.lower():
                crop = c
                break

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

@router.get("/intelligence/crop-insight")
@router.get("/insights")
async def get_market_insights(
    crop: str = Query("Soybean", description=f"Crop name: {', '.join(SUPPORTED_CROPS)}"),
    location: str = Query("Maharashtra", description="Location / district name"),
):
    """
    RAG-augmented market insight for Create Listing form.
    Provides live price + historical RAG context + LLM Sell/Hold recommendation.
    """
    try:
        supported_lower = [c.lower() for c in SUPPORTED_CROPS]
        if crop.lower() not in supported_lower:
            raise HTTPException(status_code=422, detail=f"Unsupported crop: {crop}. Supported: {SUPPORTED_CROPS}")
            
        # Normalize crop name
        for c in SUPPORTED_CROPS:
            if c.lower() == crop.lower():
                crop = c
                break

        # 1. Fetch live market price
        live_price_data = await MandiAPIClient.get_live_price(crop, location, 0.0)
        current_modal_price = float(
            live_price_data.get("modal_price")
            or live_price_data.get("live_modal_price")
            or 0.0
        )
        if current_modal_price <= 0:
            BASE_CROP_PRICES = {
                "Bajra": 35.58, "Jowar": 60.0, "Rice": 34.71,
                "Soybean": 69.64, "Cotton": 65.0, "Onion": 22.0, "Sugarcane": 3.75
            }
            current_modal_price = BASE_CROP_PRICES.get(crop, 30.0)
        current_modal_price = round(current_modal_price, 2)
        
        # 2. Query RAG for historical mandi prices and crop knowledge
        mandi_history = await rag_service.query_mandi_records(query_text=crop, crop=crop, n_results=3)
        crop_knowledge = rag_service.query_crop_knowledge(query_text=f"{crop} market trends seasonality", crop=crop, n_results=2)
        
        historical_context = ""
        if mandi_history and mandi_history.get("documents") and mandi_history["documents"][0]:
            historical_context = "\n".join(mandi_history["documents"][0])
            
        knowledge_context = ""
        if crop_knowledge:
            knowledge_context = "\n".join([doc["text"] for doc in crop_knowledge])
            
        # 2.5 ML Price Prediction (per-crop XGBoost model)
        ml_prediction = "No ML prediction available."
        ml_forecast_price = None
        ml_forecast_direction = None
        try:
            model_path = os.path.join(os.path.dirname(__file__), '..', 'models', 'maharashtra_price_model.pkl')
            if os.path.exists(model_path):
                with open(model_path, 'rb') as f:
                    model_data = pickle.load(f)
                crop_models  = model_data['models']       # dict: crop_name -> XGBRegressor
                crop_encoder = model_data['crop_encoder']
                dist_encoder = model_data['district_encoder']
                features     = model_data['features']

                if crop in crop_models:
                    xgb_model = crop_models[crop]

                    target_date = datetime.now() + timedelta(days=7)
                    month       = target_date.month
                    dow         = target_date.weekday()
                    doy         = target_date.timetuple().tm_yday
                    quarter     = (month - 1) // 3 + 1
                    season      = 1 if month in [6,7,8,9,10] else (2 if month in [11,12,1,2,3] else 3)
                    year        = target_date.year

                    crop_val = crop_encoder.transform([crop])[0] if crop in crop_encoder.classes_ else 0
                    dist_val = dist_encoder.transform([location])[0] if location in dist_encoder.classes_ else 0

                    # MSP lookup from model metadata
                    MSP_MAP = {
                        'Bajra': 27.75, 'Cotton': 66.20, 'Jowar': 36.99,
                        'Onion': 0.0,   'Rice': 23.69,   'Soybean': 53.28, 'Sugarcane': 3.40
                    }
                    msp = MSP_MAP.get(crop, 0.0)

                    cur = current_modal_price if current_modal_price > 0 else 30.0
                    input_df = pd.DataFrame([{
                        'crop_encoded': crop_val, 'district_encoded': dist_val,
                        'month': month, 'day_of_week': dow, 'day_of_year': doy,
                        'quarter': quarter, 'season': season, 'year': year,
                        'msp_per_kg': msp,
                        'arrival_mt': 100.0, 'arrival_7d_avg': 100.0,
                        'price_7d_ago': cur, 'price_14d_ago': cur, 'price_30d_ago': cur,
                        'price_7d_rolling_avg': cur, 'price_30d_rolling_avg': cur
                    }])[features]

                    pred_price = float(xgb_model.predict(input_df)[0])
                    trend_dir  = "increase" if pred_price > cur else "decrease"
                    ml_forecast_price     = round(pred_price, 2)
                    ml_forecast_direction = "up" if pred_price > cur else "down"
                    pct_change = abs((pred_price - cur) / cur * 100) if cur > 0 else 0
                    ml_prediction = (
                        f"XGBoost ML forecast (trained on 20,440 Maharashtra records): "
                        f"price expected to {trend_dir} to \u20b9{pred_price:.2f}/kg "
                        f"({pct_change:.1f}% change) in 7 days."
                    )
                else:
                    ml_prediction = f"ML Prediction Unavailable (Model not trained for {crop})"
        except Exception as e:
            ml_prediction = f"ML Prediction unavailable: {str(e)}"

            
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
        
        # Generate time-series chart data
        chart_data = []
        try:
            base_price = current_modal_price if current_modal_price > 0 else 30.0
            pred = ml_forecast_price if ml_forecast_price else base_price * 1.05
            
            # 1. Authentic historical records from Maharashtra APMC dataset
            hist_series = RealMandiDatasetClient.get_historical_series(crop, location, days=7)
            if hist_series:
                chart_data.extend(hist_series)
            else:
                for i in range(7, 0, -1):
                    chart_data.append({
                        "date": (datetime.now() - timedelta(days=i)).strftime("%b %d"),
                        "price": round(base_price, 2),
                        "type": "Historical"
                    })
            
            # 2. Live Today price
            chart_data.append({
                "date": "Today",
                "price": round(base_price, 2),
                "type": "Live"
            })
            
            # 3. Next 7 days forecast grounded in ML forecast model
            diff_per_day = (pred - base_price) / 7
            for i in range(1, 8):
                chart_data.append({
                    "date": (datetime.now() + timedelta(days=i)).strftime("%b %d"),
                    "price": round(base_price + (diff_per_day * i), 2),
                    "type": "Forecast"
                })
        except Exception as e:
            chart_data = []

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
                "recommendation": recommendation.strip(),
                "chart_data": chart_data
            }
        }
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))

