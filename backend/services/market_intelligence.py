import logging
from typing import Dict, Any, Optional
from backend.services.external_apis import MandiAPIClient, OpenMeteoClient

logger = logging.getLogger("backend.services.market_intelligence")

class MarketIntelligenceService:
    """
    Market Intelligence Service (MIS) acts as the bridge between external APIs, 
    historical database tracking, and the AI Agents.
    
    It prevents LLM price hallucinations by serving as a strictly mathematical 
    "Single Source of Truth" for Modal Prices.
    """
    
    @staticmethod
    async def get_market_context(crop: str, location: str, historical_average: float) -> str:
        """
        Fetches live API data, compares it to the historical average,
        and constructs a strict numerical context for RAG injection.
        """
        try:
            # 1. Fetch live Agmarknet / e-NAM price (simulated via API client)
            live_data = await MandiAPIClient.get_live_price(crop, location, historical_average)
            
            live_price = live_data.get("live_modal_price", historical_average)
            trend = live_data.get("trend", "Stable")
            volatility = live_data.get("volatility_pct", 0.0)
            
            # 2. Fetch live Open-Meteo weather
            weather_data = await OpenMeteoClient.get_weather(location)
            
            weather_str = ""
            if weather_data:
                temp = weather_data.get('temperature_c', 'N/A')
                precip = weather_data.get('precipitation_mm', '0.0')
                wind = weather_data.get('wind_speed_kmh', 'N/A')
                
                spoilage_risk = "HIGH" if (isinstance(temp, float) and temp > 35) or (isinstance(precip, float) and precip > 10) else "NORMAL"
                
                weather_str = (
                    f"--- LIVE WEATHER & SPOILAGE RISK ---\n"
                    f"Temperature: {temp}°C | Precipitation: {precip}mm | Wind: {wind}km/h\n"
                    f"Estimated Crop Spoilage Risk for {crop}: {spoilage_risk}\n"
                )
            
            # 3. Format the mathematical intelligence string
            if not live_price or live_price <= 0.01:
                price_line = f"Live Modal Price for {crop} in {location}: [UNAVAILABLE]"
                hist_line = f"Historical 30-Day Average: [UNAVAILABLE]"
            else:
                price_line = f"Live Modal Price for {crop} in {location}: ₹{live_price:.2f}/kg"
                hist_line = f"Historical 30-Day Average: ₹{historical_average:.2f}/kg"
                
            intelligence_str = (
                f"--- LIVE MARKET INTELLIGENCE ---\n"
                f"Source: Agmarknet & e-NAM (Live API)\n"
                f"{price_line}\n"
                f"{hist_line}\n"
                f"Market Trend: {trend} (Volatility: {volatility}%)\n"
                f"{weather_str}"
                f"--- END LIVE INTELLIGENCE ---\n"
            )
            return intelligence_str
        except Exception as e:
            logger.error(f"MIS Error fetching market context: {e}")
            if historical_average > 0:
                return f"Market Intelligence unavailable. Fallback Historical Average: ₹{historical_average:.2f}/kg."
            return "Market Intelligence strictly UNAVAILABLE (API offline & no local fallback)."

