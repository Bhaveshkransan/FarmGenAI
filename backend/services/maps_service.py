"""
backend/services/maps_service.py

OSRM (Open Source Routing Machine) & OpenStreetMap routing service.
Used by Transporter Agent and Matching Engine for real-time driving distances and transit times.

No API key required.
Demo Server: https://router.project-osrm.org
"""

import logging
import requests
from typing import Dict, Any
from backend.services.weather_service import CITY_COORDINATES

logger = logging.getLogger("MapsService")

OSRM_BASE_URL = "https://router.project-osrm.org"


def get_route_distance_and_duration(origin: str, destination: str) -> Dict[str, Any]:
    """
    Calculate driving distance (in km) and duration (in hours) between two cities
    using the public OSRM routing engine API.
    """
    orig_coords = CITY_COORDINATES.get(origin, CITY_COORDINATES.get("Nashik"))
    dest_coords = CITY_COORDINATES.get(destination, CITY_COORDINATES.get("Mumbai"))

    # Format: lon1,lat1;lon2,lat2
    coordinates_str = f"{orig_coords['lon']},{orig_coords['lat']};{dest_coords['lon']},{dest_coords['lat']}"
    url = f"{OSRM_BASE_URL}/route/v1/driving/{coordinates_str}?overview=false"

    try:
        response = requests.get(url, timeout=4)
        if response.status_code == 200:
            routes = response.json().get("routes", [])
            if routes:
                route = routes[0]
                distance_km = round(route.get("distance", 0) / 1000.0, 2)
                duration_hours = round(route.get("duration", 0) / 3600.0, 2)

                return {
                    "success": True,
                    "origin": origin,
                    "destination": destination,
                    "distance_km": distance_km,
                    "duration_hours": duration_hours,
                    "source": "OSRM Routing Engine",
                }
    except Exception as e:
        logger.warning(f"OSRM routing request failed for {origin} -> {destination}: {e}. Falling back to Haversine matrix.")

    # Failsafe fallback distance matrix
    from backend.services.matching_service import CITY_DISTANCES_KM
    orig_clean = (origin or "").strip()
    dest_clean = (destination or "").strip()
    fallback_dist = CITY_DISTANCES_KM.get(orig_clean, {}).get(dest_clean)
    if fallback_dist is None:
        fallback_dist = CITY_DISTANCES_KM.get(dest_clean, {}).get(orig_clean, 150.0 if orig_clean != dest_clean else 0.0)
    fallback_dist = float(fallback_dist)
    fallback_duration = round(fallback_dist / 35.0, 2)  # Avg 35 km/h truck speed

    return {
        "success": True,
        "origin": origin,
        "destination": destination,
        "distance_km": fallback_dist,
        "duration_hours": fallback_duration,
        "source": "Fallback Distance Matrix",
    }

