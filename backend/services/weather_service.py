"""
backend/services/weather_service.py

Open-Meteo weather integration service for AgriNegotiator.
Used by Warehouse Agent, Negotiation Engine, and Spoilage Prediction.

No API key required.
API Docs: https://open-meteo.com/
"""

import logging
import requests
from typing import Dict, Any
from config.settings import settings

logger = logging.getLogger("WeatherService")

# Known coordinates for major agricultural hubs in Maharashtra
# Known coordinates for major agricultural hubs in Maharashtra
CITY_COORDINATES: Dict[str, Dict[str, float]] = {
    "Nashik": {"lat": 19.9975, "lon": 73.7898},
    "Pune": {"lat": 18.5204, "lon": 73.8567},
    "Mumbai": {"lat": 19.0760, "lon": 72.8777},
    "Nagpur": {"lat": 21.1458, "lon": 79.0882},
    "Aurangabad": {"lat": 19.8762, "lon": 75.3433},
    "Satara": {"lat": 17.6805, "lon": 74.0183},
    "Ahmednagar": {"lat": 19.0952, "lon": 74.7496},
    "Kolhapur": {"lat": 16.7050, "lon": 74.2433},
    "Kalyan": {"lat": 19.2403, "lon": 73.1305},
    "Thane": {"lat": 19.2183, "lon": 72.9781},
    "Solapur": {"lat": 17.6599, "lon": 75.9064},
    "Sangli": {"lat": 16.8524, "lon": 74.5815},
    "Jalgaon": {"lat": 21.0077, "lon": 75.5626},
    "Amravati": {"lat": 20.9374, "lon": 77.7796},
    "Nanded": {"lat": 19.1383, "lon": 77.3210},
    "Latur": {"lat": 18.4088, "lon": 76.5604},
    "Dhule": {"lat": 20.9042, "lon": 74.7749},
    "Ratnagiri": {"lat": 16.9902, "lon": 73.3120},
    "Akola": {"lat": 20.7002, "lon": 77.0082},
    "Baramati": {"lat": 18.1513, "lon": 74.5771},
    "Shrirampur": {"lat": 19.6179, "lon": 74.6586},
    "Vashi": {"lat": 19.0771, "lon": 72.9986},
    "Surat": {"lat": 21.1702, "lon": 72.8311},
    "Delhi": {"lat": 28.6139, "lon": 77.2090},
    "Bengaluru": {"lat": 12.9716, "lon": 77.5946}
}



def get_current_weather(location: str) -> Dict[str, Any]:
    """
    Fetch current weather metrics (temperature, humidity, precipitation, wind)
    from Open-Meteo for a given city/location.
    """
    coords = CITY_COORDINATES.get(location, CITY_COORDINATES["Nashik"])
    lat, lon = coords["lat"], coords["lon"]

    url = (
        f"https://api.open-meteo.com/v1/forecast"
        f"?latitude={lat}&longitude={lon}"
        f"&current=temperature_2m,relative_humidity_2m,precipitation,wind_speed_10m"
        f"&forecast_days=1"
    )

    try:
        response = requests.get(url, timeout=4)
        if response.status_code == 200:
            data = response.json().get("current", {})
            temp = data.get("temperature_2m", 28.0)
            humidity = data.get("relative_humidity_2m", 65.0)
            precip = data.get("precipitation", 0.0)

            # Spoilage risk multiplier based on heat and humidity
            spoilage_risk = "HIGH" if (temp > 32 or humidity > 80) else "MEDIUM" if (temp > 26 or humidity > 65) else "LOW"

            return {
                "success": True,
                "location": location,
                "temperature_celsius": temp,
                "relative_humidity_pct": humidity,
                "precipitation_mm": precip,
                "wind_speed_kmh": data.get("wind_speed_10m", 10.0),
                "spoilage_risk_level": spoilage_risk,
                "source": "Open-Meteo Live API",
            }
    except Exception as e:
        logger.warning(f"Open-Meteo request failed for {location}: {e}. Returning fallback estimates.")

    # Failsafe deterministic fallback
    return {
        "success": True,
        "location": location,
        "temperature_celsius": 28.5,
        "relative_humidity_pct": 62.0,
        "precipitation_mm": 0.0,
        "wind_speed_kmh": 12.0,
        "spoilage_risk_level": "MEDIUM",
        "source": "Fallback Estimate",
    }


def predict_spoilage_acceleration(crop: str, shelf_life_days: int, location: str) -> Dict[str, Any]:
    """
    Calculate adjusted shelf life based on temperature and humidity.
    Heat/humidity accelerates degradation of perishables like Tomatoes/Berries.
    """
    weather = get_current_weather(location)
    temp = weather["temperature_celsius"]
    humidity = weather["relative_humidity_pct"]

    decay_factor = 1.0
    if temp > 33:
        decay_factor += 0.35
    elif temp > 28:
        decay_factor += 0.15

    if humidity > 75:
        decay_factor += 0.2

    adjusted_shelf_life = max(1, round(shelf_life_days / decay_factor))

    return {
        "crop": crop,
        "nominal_shelf_life_days": shelf_life_days,
        "adjusted_shelf_life_days": adjusted_shelf_life,
        "decay_acceleration_factor": round(decay_factor, 2),
        "weather_summary": f"Temp: {temp}°C, Humidity: {humidity}%",
        "urgency": "CRITICAL" if adjusted_shelf_life <= 2 else "HIGH" if adjusted_shelf_life <= 4 else "NORMAL",
    }

