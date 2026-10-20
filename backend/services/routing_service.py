"""
backend/services/routing_service.py

Routing service for the Transport Agent using OSRM API.
Calculates road distance (km), estimated travel duration (hours),
estimated arrival time, and deadhead distance from vehicle location to pickup.
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Dict, Any, Optional
from backend.services.maps_service import get_route_distance_and_duration

logger = logging.getLogger("RoutingService")


def calculate_transport_route(
    pickup_location: str,
    delivery_location: str,
    vehicle_current_location: Optional[str] = None
) -> Dict[str, Any]:
    """
    Obtain road distance (km) and estimated travel duration (hours) using OSRM engine.
    Calculates both main trip distance and optional deadhead distance.
    """
    # 1. Main loaded trip: Pickup -> Delivery
    trip_route = get_route_distance_and_duration(pickup_location, delivery_location)
    main_distance_km = trip_route.get("distance_km", 50.0)
    main_duration_hours = trip_route.get("duration_hours", 2.0)
    routing_source = trip_route.get("source", "OSRM Routing Engine")

    # 2. Deadhead trip: Vehicle Current Location -> Pickup Location
    deadhead_km = 0.0
    deadhead_duration_hours = 0.0
    if vehicle_current_location and vehicle_current_location.lower() != pickup_location.lower():
        deadhead_route = get_route_distance_and_duration(vehicle_current_location, pickup_location)
        deadhead_km = deadhead_route.get("distance_km", 0.0)
        deadhead_duration_hours = deadhead_route.get("duration_hours", 0.0)

    total_operational_distance_km = round(main_distance_km + deadhead_km, 2)
    total_travel_duration_hours = round(main_duration_hours + deadhead_duration_hours, 2)

    # Calculate estimated arrival time
    now_utc = datetime.now(timezone.utc)
    estimated_arrival_utc = now_utc + timedelta(hours=main_duration_hours)

    return {
        "success": True,
        "pickup_location": pickup_location,
        "delivery_location": delivery_location,
        "vehicle_current_location": vehicle_current_location or pickup_location,
        "distance_km": main_distance_km,
        "estimated_duration_hours": main_duration_hours,
        "deadhead_km": deadhead_km,
        "deadhead_duration_hours": deadhead_duration_hours,
        "total_operational_distance_km": total_operational_distance_km,
        "total_travel_duration_hours": total_travel_duration_hours,
        "estimated_arrival_iso": estimated_arrival_utc.isoformat(),
        "routing_source": routing_source,
        "route_waypoints": trip_route.get("route_waypoints", []),
        "route_path": trip_route.get("route_path", ""),
        "terminology": {
            "duration_label": "estimated travel duration",
            "arrival_label": "estimated arrival time"
        }
    }
