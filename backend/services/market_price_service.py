"""
backend/services/market_price_service.py

AGMARKNET & MSP Market Pricing Service — FR-12.
Provides daily Mandi wholesale rates and Minimum Support Prices (MSP)
for major regional crops across Maharashtra mandis.
"""

import logging
import asyncio
from typing import Dict, List, Any
from backend.services.external_apis import MandiAPIClient
from backend.core.constants import SUPPORTED_CROPS

logger = logging.getLogger("MarketPriceService")

def get_crop_market_price(crop: str, location: str = "Nashik") -> Dict[str, Any]:
    """
    Fetch mandi price benchmarks and MSP for a given crop using MandiAPIClient.
    This acts as a synchronous wrapper if called from sync routes.
    """
    loop = asyncio.new_event_loop()
    try:
        data = loop.run_until_complete(MandiAPIClient.get_live_price(crop, location))
    except Exception as e:
        logger.error(f"Error fetching live price for {crop}: {e}")
        data = {
            "source": "FALLBACK",
            "crop": crop,
            "location": location,
            "mandi": "N/A",
            "min_price": 0.0,
            "max_price": 0.0,
            "modal_price": 0.0,
            "live_modal_price": 0.0,
            "trend": "Unknown",
            "volatility_pct": 0,
            "status": "MARKET_DATA_UNAVAILABLE"
        }
    finally:
        loop.close()
        
    return {
        "crop": data.get("crop", crop),
        "location": data.get("location", location),
        "market_price": data.get("modal_price", 0.0),
        "min_support_price": data.get("min_price", 0.0), # Assuming external api gives sensible min
        "price_range_low": data.get("min_price", 0.0),
        "price_range_high": data.get("max_price", 0.0),
        "top_mandi": data.get("mandi", "N/A"),
        "trend": data.get("trend", "Unknown"),
        "data_source": data.get("source", "MARKET_DATA_UNAVAILABLE"),
        "status": data.get("status", "AVAILABLE") if "status" in data else "AVAILABLE"
    }

def list_all_market_prices() -> List[Dict[str, Any]]:
    """Return all regional crop market prices."""
    results = []
    for crop in SUPPORTED_CROPS:
        res = get_crop_market_price(crop, "Maharashtra")
        results.append(res)
    return results

