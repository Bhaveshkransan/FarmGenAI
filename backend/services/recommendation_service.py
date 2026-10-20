import logging
from typing import List, Dict, Any
from backend.services.routing_service import calculate_transport_route

logger = logging.getLogger("RecommendationService")

def score_vehicle(vehicle: Dict[str, Any], transport_request: Dict[str, Any]) -> float:
    """
    Computes a strictly normalized recommendation score in [0.0, 100.0] for a given vehicle.
    Sub-factors are independently normalized to [0.0, 1.0] before weighted aggregation:
    - Distance Proximity (25%)
    - Capacity Utilization (20%)
    - Vehicle / Transporter Reliability (20%)
    - Shelf-Life Suitability (15%)
    - Urgency Fulfillment (10%)
    - Refrigeration Compliance (10%)
    """
    pickup_location = transport_request.get("pickup_location", "Ahmednagar")
    delivery_location = transport_request.get("delivery_location", "Pune")
    vehicle_location = vehicle.get("current_location", pickup_location)

    # 1. Distance (deadhead to pickup + pickup to delivery)
    try:
        route_info = calculate_transport_route(
            pickup_location=pickup_location,
            delivery_location=delivery_location,
            vehicle_current_location=vehicle_location
        )
        total_distance = route_info.get("distance_km", 50.0) + route_info.get("deadhead_km", 0.0)
    except Exception as e:
        logger.error(f"Routing failed in recommendation: {e}")
        total_distance = 100.0  # fallback

    s_dist = max(0.0, 1.0 - (total_distance / 600.0))

    # 2. Capacity Fit (normalized [0, 1])
    req_capacity = float(transport_request.get("quantity_kg", 1000.0))
    veh_capacity = float(vehicle.get("capacity_kg", 1000.0))
    capacity_ratio = veh_capacity / req_capacity if req_capacity > 0 else 1.0
    if capacity_ratio < 1.0:
        s_cap = 0.0  # Cannot carry payload
    else:
        s_cap = max(0.0, 1.0 - (capacity_ratio - 1.0) / 3.0)

    # 3. Reliability & Rating (normalized [0, 1])
    rating = float(vehicle.get("rating", 4.0))
    s_rel = min(1.0, max(0.0, rating / 5.0))

    # 4. Shelf Life Factor (normalized [0, 1])
    shelf_life_hours = float(transport_request.get("shelf_life_hours", 24.0))
    is_perishable = transport_request.get("crop", "").lower() in {"tomato", "banana", "strawberry", "grape", "mango", "milk"}
    s_shelf = 1.0 if not is_perishable else min(1.0, shelf_life_hours / 72.0)

    # 5. Urgency Factor (normalized [0, 1])
    urgency = transport_request.get("urgency", "NORMAL").upper()
    s_urgency = 1.0 if urgency == "HIGH" else (0.8 if urgency == "NORMAL" else 0.5)

    # 6. Refrigeration Compliance (normalized [0, 1])
    req_refrig = transport_request.get("refrigerated_required", False) or is_perishable
    veh_refrig = bool(vehicle.get("refrigerated", False))
    s_refrig = 1.0 if (req_refrig and veh_refrig) else (1.0 if not req_refrig else 0.0)

    # Composite weighted aggregation in [0.0, 100.0]
    score = round(100.0 * (
        0.25 * s_dist +
        0.20 * s_cap +
        0.20 * s_rel +
        0.15 * s_shelf +
        0.10 * s_urgency +
        0.10 * s_refrig
    ), 2)
    return float(score)

def recommend_vehicles_for_request(candidate_vehicles: List[Dict[str, Any]], transport_request: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Ranks a list of candidate vehicles for a given transport request.
    Returns the list sorted by score descending.
    """
    scored_vehicles = []
    for v in candidate_vehicles:
        # Avoid modifying original vehicle dict if possible
        v_copy = dict(v)
        score = score_vehicle(v_copy, transport_request)
        v_copy["recommendation_score"] = score
        scored_vehicles.append(v_copy)
    
    # Sort descending by score
    scored_vehicles.sort(key=lambda x: x.get("recommendation_score", 0.0), reverse=True)
    return scored_vehicles
