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


def get_coordinates(city_name: str) -> Dict[str, float]:
    for key, value in CITY_COORDINATES.items():
        if key.lower() == city_name.lower():
            return value
    try:
        geocode_url = f"https://nominatim.openstreetmap.org/search?q={city_name},+Maharashtra,+India&format=json&limit=1"
        headers = {'User-Agent': 'FarmGenAI-App'}
        resp = requests.get(geocode_url, headers=headers, timeout=5)
        if resp.status_code == 200:
            data = resp.json()
            if data and len(data) > 0:
                return {"lat": float(data[0]["lat"]), "lon": float(data[0]["lon"])}
    except Exception as e:
        logger.error(f"Geocoding failed for {city_name}: {e}")
    return CITY_COORDINATES.get("Nashik")

_ROUTE_CACHE: Dict[str, Dict[str, Any]] = {}

def get_route_distance_and_duration(origin: str, destination: str) -> Dict[str, Any]:
    """
    Calculate driving distance (in km) and duration (in hours) between two cities
    using the public OSRM routing engine API with memory caching for fast marketplace evaluation.
    """
    orig_clean = (origin or "Nashik").strip()
    dest_clean = (destination or "Pune").strip()

    if orig_clean.lower() == dest_clean.lower():
        return {
            "success": True,
            "origin": orig_clean,
            "destination": dest_clean,
            "distance_km": 0.0,
            "duration_hours": 0.0,
            "route_waypoints": [{"name": orig_clean, "type": "city"}],
            "route_path": orig_clean,
            "source": "Local Station"
        }

    cache_key = f"{orig_clean.lower()}->{dest_clean.lower()}"
    if cache_key in _ROUTE_CACHE:
        return _ROUTE_CACHE[cache_key]

    orig_coords = get_coordinates(origin)
    dest_coords = get_coordinates(destination)

    # Format: lon1,lat1;lon2,lat2
    coordinates_str = f"{orig_coords['lon']},{orig_coords['lat']};{dest_coords['lon']},{dest_coords['lat']}"
    url = f"{OSRM_BASE_URL}/route/v1/driving/{coordinates_str}?overview=false&steps=true"

    try:
        response = requests.get(url, timeout=3)
        if response.status_code == 200:
            routes = response.json().get("routes", [])
            if routes:
                route = routes[0]
                distance_km = round(route.get("distance", 0) / 1000.0, 2)
                duration_hours = round(route.get("duration", 0) / 3600.0, 2)
                duration_hours = round(route.get("duration", 0) / 3600.0, 2)
                
                # Dynamically parse real route steps from OSRM
                route_waypoints = [{"name": origin, "type": "city"}]
                
                legs = route.get("legs", [])
                if legs and "steps" in legs[0]:
                    steps = legs[0]["steps"]
                    accumulated_dist = 0
                    toll_count = 1
                    last_name = origin.lower()
                    
                    for step in steps:
                        step_dist = step.get("distance", 0)
                        accumulated_dist += step_dist
                        name = step.get("name", "")
                        
                        if accumulated_dist > 25000 and name and "ramp" not in name.lower() and name.lower() != last_name:
                            # If it's a major highway, there's likely a toll
                            if "expressway" in name.lower() or "nh" in name.lower() or "ah" in name.lower():
                                route_waypoints.append({
                                    "name": f"{name.split(',')[0]} Toll", 
                                    "type": "toll", 
                                    "cost": 85 + (toll_count * 15)
                                })
                                toll_count += 1
                                last_name = name.lower()
                                accumulated_dist = 0
                            else:
                                # Clean up generic road names
                                clean_name = name.split(',')[0].replace("Road", "").replace("Rd", "").strip()
                                if clean_name.lower() not in last_name and len(clean_name) > 2:
                                    route_waypoints.append({"name": clean_name, "type": "city"})
                                    last_name = clean_name.lower()
                                    accumulated_dist = 0
                
                # Filter out consecutive duplicates from route_waypoints
                filtered_waypoints = [route_waypoints[0]]
                for wp in route_waypoints[1:]:
                    if wp["name"].lower() != filtered_waypoints[-1]["name"].lower():
                        filtered_waypoints.append(wp)
                route_waypoints = filtered_waypoints
                
                # Add destination if not already there
                if route_waypoints[-1]["name"].lower() != destination.lower():
                    route_waypoints.append({"name": destination, "type": "city"})
                
                # Fallback if no steps were parsed
                if len(route_waypoints) <= 2 and distance_km > 50:
                    route_waypoints.insert(1, {"name": "Highway Toll", "type": "toll", "cost": 100})
                
                route_path = " ➔ ".join([wp["name"] for wp in route_waypoints])

                result = {
                    "success": True,
                    "origin": origin,
                    "destination": destination,
                    "distance_km": distance_km,
                    "duration_hours": duration_hours,
                    "route_waypoints": route_waypoints,
                    "route_path": route_path,
                    "source": "OSRM Routing Engine (Live API)",
                }
                _ROUTE_CACHE[cache_key] = result
                return result
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
    
    route_waypoints = [
        {"name": origin, "type": "origin"},
        {"name": "Highway", "type": "waypoint"},
        {"name": destination, "type": "destination"}
    ]

    fallback_result = {
        "success": True,
        "origin": origin,
        "destination": destination,
        "distance_km": fallback_dist,
        "duration_hours": fallback_duration,
        "route_waypoints": route_waypoints,
        "route_path": f"{origin} ➔ Highway ➔ {destination}",
        "source": "Fallback Distance Matrix",
    }
    _ROUTE_CACHE[cache_key] = fallback_result
    return fallback_result


def get_alternate_routes(origin: str, destination: str) -> Dict[str, Any]:
    """
    Calculate multiple driving routes between two cities using OSRM.
    Returns up to 3 alternate routes.
    """
    orig_coords = CITY_COORDINATES.get(origin, CITY_COORDINATES.get("Nashik"))
    dest_coords = CITY_COORDINATES.get(destination, CITY_COORDINATES.get("Mumbai"))

    coordinates_str = f"{orig_coords['lon']},{orig_coords['lat']};{dest_coords['lon']},{dest_coords['lat']}"
    url = f"{OSRM_BASE_URL}/route/v1/driving/{coordinates_str}?overview=false&alternatives=true"

    try:
        response = requests.get(url, timeout=4)
        if response.status_code == 200:
            routes_data = response.json().get("routes", [])
            parsed_routes = []
            
            for idx, route in enumerate(routes_data):
                dist_km = round(route.get("distance", 0) / 1000.0, 2)
                dur_hrs = round(route.get("duration", 0) / 3600.0, 2)
                
                # Determine route name based on typical Indian highways or generic fallback
                route_name = f"Route {idx + 1}"
                via_cities = []
                
                if idx == 0:
                    route_name = "Primary Route (Fastest)"
                    via_cities = [origin, "Main Highway", destination]
                elif idx == 1:
                    route_name = "Alternate Route (State Highway)"
                    via_cities = [origin, "State Route", destination]
                else:
                    route_name = "Alternate Route 2"
                    via_cities = [origin, "Bypass Road", destination]
                    
                # Enhance realistic Indian routes for the demo
                route_mapping = {
                    "pune-mumbai": [["Pune", "Lonavala", "Navi Mumbai", "Mumbai"], ["Pune", "Panvel", "Mumbai"]],
                    "ahmednagar-pune": [["Ahmednagar", "Shirur", "Wagholi", "Pune"], ["Ahmednagar", "Kondhapuri", "Pune"]],
                    "nashik-mumbai": [["Nashik", "Igatpuri", "Thane", "Mumbai"], ["Nashik", "Kasara", "Mumbai"]],
                    "nagpur-pune": [["Nagpur", "Amravati", "Aurangabad", "Pune"], ["Nagpur", "Wardha", "Jalna", "Pune"]]
                }
                
                route_key = f"{origin.lower()}-{destination.lower()}"
                if route_key in route_mapping:
                    options = route_mapping[route_key]
                    via_cities = options[idx % len(options)]
                elif f"{destination.lower()}-{origin.lower()}" in route_mapping:
                    options = route_mapping[f"{destination.lower()}-{origin.lower()}"]
                    via_cities = list(reversed(options[idx % len(options)]))
                
                route_path = " ➔ ".join(via_cities)
                    
                parsed_routes.append({
                    "route_id": f"route_{idx}",
                    "name": route_name,
                    "distance_km": dist_km,
                    "duration_hours": dur_hrs,
                    "route_path": route_path
                })

            if parsed_routes:
                return {
                    "success": True,
                    "origin": origin,
                    "destination": destination,
                    "routes": parsed_routes
                }
    except Exception as e:
        logger.warning(f"OSRM alternate routing failed for {origin} -> {destination}: {e}")

    # Fallback to single route matrix
    fallback_route = get_route_distance_and_duration(origin, destination)
    return {
        "success": True,
        "origin": origin,
        "destination": destination,
        "routes": [{
            "route_id": "route_fallback",
            "name": "Standard Route",
            "distance_km": fallback_route.get("distance_km", 150),
            "duration_hours": fallback_route.get("duration_hours", 4.0),
            "route_path": f"{origin} ➔ Highway ➔ {destination}"
        }]
    }

