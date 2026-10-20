"""
backend/routes/transport_routes.py

Transport booking and fleet management endpoints.
FR-9: Transport Coordination
"""

import uuid
import logging
from typing import Optional, Dict, Any, List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, Query, Header
from backend.services.security import get_current_user
from backend.services.transport_service import list_fleet, assign_transport
from backend.schemas.transport_model import TransportBookingRequest, TransportStatusUpdate

router = APIRouter(tags=["Transport"])
logger = logging.getLogger(__name__)

from database.db import Database

@router.get("/fleet")
async def get_fleet(current_user: dict = Depends(get_current_user)):
    """List all available transport vehicles."""
    fleet = await list_fleet()
    return {"success": True, "data": fleet, "count": len(fleet)}


@router.post("/book")
async def book_transport(
    payload: TransportBookingRequest,
    current_user: dict = Depends(get_current_user),
    idempotency_key: Optional[str] = Header(None, alias="Idempotency-Key"),
):
    """
    Book a transport vehicle for a negotiation shipment.
    Guarantees:
    - Distributed idempotency: returns existing booking if negotiation_id or idempotency_key is already booked.
    - Concurrency safety: atomic row locking on DBVehicle; raises 409 Conflict if already booked.
    - Unified dual-persistence: writes DBTransportBooking and DBBooking.
    """
    from backend.services.transporter_marketplace_service import reserve_vehicle_and_create_booking_async
    from backend.core.exceptions import VehicleAlreadyBookedException, ConflictException
    from backend.db.session import AsyncSessionLocal
    from backend.db.models.transport_agent_models import DBTransportBooking
    from sqlalchemy import select, or_

    effective_idempotency_key = idempotency_key or payload.idempotency_key

    # Check if a booking already exists for this negotiation_id or idempotency_key
    async with AsyncSessionLocal() as session:
        conditions = []
        if payload.negotiation_id:
            conditions.append(DBTransportBooking.negotiation_id == payload.negotiation_id)
        if effective_idempotency_key:
            conditions.append(DBTransportBooking.idempotency_key == effective_idempotency_key)
        
        if conditions:
            existing = (await session.execute(select(DBTransportBooking).where(or_(*conditions)))).scalars().first()
            if existing:
                return {
                    "success": True,
                    "is_idempotent_replay": True,
                    "data": {
                        "booking_id": existing.booking_id,
                        "negotiation_id": existing.negotiation_id,
                        "vehicle_id": existing.vehicle_id,
                        "provider_id": existing.provider_id,
                        "agreed_freight": existing.agreed_freight,
                        "status": existing.status,
                        "created_at": existing.created_at,
                    },
                    "message": "Idempotent replay: Existing booking retrieved."
                }

    # If vehicle_id is not specified in payload, compute assignment
    vehicle_id = payload.vehicle_id
    assignment = {}
    if not vehicle_id:
        try:
            assignment = await assign_transport({
                "quantity": payload.quantity,
                "distance_km": payload.distance_km,
                "shelf_life": payload.shelf_life,
                "crop": payload.crop,
                "origin": payload.origin_location,
                "destination": payload.destination_location,
            })
            vehicle_id = assignment.get("vehicle_id")
        except ValueError as e:
            raise HTTPException(status_code=400, detail=str(e))

    booking_id = f"booking_{str(uuid.uuid4())[:8]}"
    reserve_payload = {
        "booking_id": booking_id,
        "negotiation_id": payload.negotiation_id,
        "idempotency_key": effective_idempotency_key,
        "crop": payload.crop,
        "quantity_kg": payload.quantity,
        "origin_location": payload.origin_location,
        "destination_location": payload.destination_location,
        "distance_km": payload.distance_km,
        "booked_by": current_user.get("sub", "unknown"),
        "vehicle_id": vehicle_id,
        "agreed_freight": payload.agreed_freight or assignment.get("estimated_cost", 3500.0),
        "transport_floor": payload.transport_floor,
        "farmer_floor": payload.farmer_floor,
        "estimated_duration_hours": assignment.get("estimated_transit_hours", 4.0),
    }

    try:
        res = await reserve_vehicle_and_create_booking_async(reserve_payload)
        return {
            "success": True,
            "is_idempotent_replay": res.get("is_idempotent_replay", False),
            "data": {
                "booking_id": res["booking_id"],
                "negotiation_id": payload.negotiation_id,
                "vehicle_id": res["vehicle_id"],
                "agreed_freight": res["agreed_freight"],
                "status": res["status"],
                "crop": payload.crop,
                "quantity": payload.quantity,
                "distance_km": payload.distance_km,
                "origin_location": payload.origin_location,
                "destination_location": payload.destination_location,
            }
        }
    except (VehicleAlreadyBookedException, ConflictException) as ce:
        raise HTTPException(status_code=409, detail=str(ce))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Booking failed: {e}")


@router.get("/booking/{booking_id}")
async def get_booking(booking_id: str, current_user: dict = Depends(get_current_user)):
    """Get transport booking details."""
    booking = await Database.get_booking_async(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")
    return {"success": True, "data": booking}


@router.get("/track/{booking_id}")
async def track_booking(booking_id: str, current_user: dict = Depends(get_current_user)):
    """Alias for getting booking details."""
    return await get_booking(booking_id, current_user)


@router.get("/bookings")
async def list_bookings(current_user: dict = Depends(get_current_user)):
    """List transport bookings for the current user."""
    uid = current_user["sub"]
    all_bookings = await Database.list_bookings_async()
    my_bookings = [b for b in all_bookings if b.get("booked_by") == uid]
    return {"success": True, "data": my_bookings, "count": len(my_bookings)}


@router.patch("/booking/{booking_id}/status")
async def update_booking_status(
    booking_id: str,
    payload: TransportStatusUpdate,
    current_user: dict = Depends(get_current_user),
):
    """Update transport booking status (e.g., IN_TRANSIT, DELIVERED)."""
    booking = await Database.get_booking_async(booking_id)
    if not booking:
        raise HTTPException(status_code=404, detail="Booking not found")

    valid_statuses = {"SCHEDULED", "IN_TRANSIT", "DELIVERED", "CANCELLED"}
    if payload.status not in valid_statuses:
        raise HTTPException(status_code=400, detail=f"Invalid status. Must be one of: {valid_statuses}")

    update_payload = {
        "status": payload.status,
        "updated_at": datetime.now(timezone.utc).isoformat()
    }
    await Database.update_booking_async(booking_id, update_payload)
    booking.update(update_payload)
    return {"success": True, "data": booking}


@router.patch("/status/{booking_id}")
async def update_booking_status_alias(
    booking_id: str,
    payload: TransportStatusUpdate,
    current_user: dict = Depends(get_current_user),
):
    """Alias for updating booking status."""
    return await update_booking_status(booking_id, payload, current_user)


@router.get("/estimate")
async def estimate_transport_cost(
    quantity: float = 100.0,
    distance_km: float = 60.0,
    shelf_life: int = 3,
    current_user: dict = Depends(get_current_user),
):
    """Quick cost estimate without booking."""
    try:
        result = await assign_transport({
            "quantity": quantity,
            "distance_km": distance_km,
            "shelf_life": shelf_life,
        })
        return {"success": True, "data": result}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/route-estimate")
async def get_route_estimate(
    origin: str,
    destination: str,
    quantity_kg: float = 1000.0,
    crop: str = "Produce",
    vehicle_type: str = Query("Medium Truck"),
    fuel_type: str = Query("Diesel"),
    fuel_efficiency_kmpl: float = Query(8.0, gt=0),
    return_trip: bool = Query(False),
    waiting_hours: float = Query(0.0, ge=0),
):
    """
    Fetch alternate routes from OSRM and calculate estimated market value and floor prices
    for each route. Used to preview real-world costs before booking.
    """
    from backend.services.maps_service import get_alternate_routes
    from backend.services.transport_cost_service import calculate_transportation_cost
    
    # 1. Fetch alternate routes
    route_result = get_alternate_routes(origin, destination)
    if not route_result.get("success"):
        raise HTTPException(status_code=400, detail="Could not calculate routes.")
        
    routes = route_result.get("routes", [])
    
    mock_vehicle = {
        "vehicle_type": vehicle_type,
        "fuel_type": fuel_type,
        "fuel_efficiency_kmpl": fuel_efficiency_kmpl,
    }
    
    is_perishable = crop.lower() in {"tomato", "banana", "strawberry", "grape", "mango", "milk", "onion"}
    
    # 2. Calculate costs per route
    enriched_routes = []
    best_route_idx = 0
    lowest_cost = float('inf')
    toll_rates_per_km = {
        "Cargo Three-Wheeler": 0.0,
        "Mini Truck": 1.2,
        "LCV": 1.5,
        "Medium Truck": 2.0,
        "Refrigerated Truck": 2.2,
        "Heavy Truck": 3.0,
        "Tractor + Trailer": 1.8,
    }
    
    for idx, r in enumerate(routes):
        distance_km = float(r["distance_km"])
        return_distance_km = distance_km if return_trip else 0.0
        operational_distance_km = distance_km + return_distance_km
        operational_duration_hours = float(r["duration_hours"]) * (2 if return_trip else 1)
        try:
            cost_res = await calculate_transportation_cost(
                vehicle=mock_vehicle,
                distance_km=distance_km,
                estimated_duration_hours=operational_duration_hours,
                deadhead_km=return_distance_km,
                waiting_hours=waiting_hours,
                is_perishable=is_perishable
            )
            operating_cost = cost_res["total_operating_cost"]
            floor_price = cost_res["minimum_acceptable_price"]
            target_price = cost_res["target_price"]
            opening_quote = cost_res["initial_quote"]
            r["estimated_toll"] = cost_res["cost_breakdown"]["toll_cost"]
            r["estimated_fuel"] = round(
                cost_res["cost_breakdown"]["fuel_cost"] + cost_res["cost_breakdown"]["deadhead_cost"],
                2,
            )
            r["fuel_price_per_litre"] = cost_res["fuel_price_per_litre"]
            r["cost_breakdown"] = cost_res["cost_breakdown"]
            r["cost_source"] = "Deterministic transport cost engine"
        except Exception as e:
            logger.warning("Route cost engine failed for %s -> %s: %s", origin, destination, e)
            fuel_price = 92.5
            operating_cost = round(
                (operational_distance_km / fuel_efficiency_kmpl) * fuel_price
                + operational_distance_km * toll_rates_per_km.get(vehicle_type, 2.0)
                + operational_duration_hours * 200.0
                + waiting_hours * 150.0
                + operational_distance_km * 5.0
                + 400.0,
                2,
            )
            floor_price = round(operating_cost * 1.05 * 1.18, 2)
            target_price = round(floor_price * 1.12, 2)
            opening_quote = round(floor_price * 1.20, 2)
            r["estimated_toll"] = round(operational_distance_km * toll_rates_per_km.get(vehicle_type, 2.0), 2)
            r["estimated_fuel"] = round((operational_distance_km / fuel_efficiency_kmpl) * fuel_price, 2)
            r["fuel_price_per_litre"] = fuel_price
            r["cost_source"] = "Fallback operating-cost estimate"

        r["operational_distance_km"] = round(operational_distance_km, 2)
        r["return_distance_km"] = round(return_distance_km, 2)
        r["waiting_hours"] = waiting_hours
        r["total_operating_cost"] = operating_cost
        r["floor_price"] = floor_price
        r["floor_rate_per_km"] = round(floor_price / operational_distance_km, 5) if operational_distance_km > 0 else 0.0
        r["target_price"] = target_price
        r["target_rate_per_km"] = round(target_price / operational_distance_km, 5) if operational_distance_km > 0 else 0.0
        r["opening_quote"] = opening_quote
        r["opening_quote_rate_per_km"] = round(opening_quote / operational_distance_km, 5) if operational_distance_km > 0 else 0.0
        r["market_average"] = round(operating_cost * 1.20, 2)

        if r.get("cost_breakdown") is None:
            r["cost_breakdown"] = {
                "fuel_cost": r["estimated_fuel"],
                "deadhead_cost": 0.0,
                "toll_cost": r["estimated_toll"],
                "driver_cost": round(operational_duration_hours * 200.0, 2),
                "maintenance_cost": round(operational_distance_km * 5.0, 2),
                "loading_cost": 200.0,
                "unloading_cost": 200.0,
                "waiting_cost": round(waiting_hours * 150.0, 2),
            }

        if operating_cost < lowest_cost:
            lowest_cost = operating_cost
            best_route_idx = len(enriched_routes)

        r["is_recommended"] = False
        enriched_routes.append(r)
        
    if enriched_routes:
        enriched_routes[best_route_idx]["is_recommended"] = True
        
    return {
        "success": True,
        "origin": origin,
        "destination": destination,
        "vehicle_assumed": vehicle_type,
        "fuel_type": fuel_type,
        "fuel_efficiency_kmpl": fuel_efficiency_kmpl,
        "return_trip": return_trip,
        "waiting_hours": waiting_hours,
        "rate_basis": "Trip quote divided by total operational distance, including return travel",
        "routes": enriched_routes
    }


# ── STANDALONE TRANSPORT AGENT MODULE ENDPOINTS ───────────────────
from backend.schemas.transport_agent_schemas import (
    TransportPlanInput, TransportNegotiationInput, VehicleRegistrationInput
)
from backend.agents.transport_agent.graph import run_transport_workflow, run_transport_negotiation
from backend.services.vehicle_service import get_all_vehicles
from backend.services.fuel_service import get_fuel_price
from backend.services.transport_cost_service import DEFAULT_COST_PARAMS

@router.get("/fuel-estimate")
async def estimate_fuel_and_base_rate(
    fuel_type: str = "Diesel",
    location: str = "Ahmednagar",
    efficiency_kmpl: float = 10.0,
    capacity_kg: float = 5000.0,
    vehicle_type: str = "Medium Truck"
):
    """
    Fetch live fuel price and calculate AI-suggested base rate per km.
    """
    fuel_info = await get_fuel_price(fuel_type, location)
    live_price = fuel_info.get("price_per_litre", 90.0)

    # Simple cost formula per km
    fuel_cost_per_km = live_price / efficiency_kmpl if efficiency_kmpl > 0 else 0
    
    # Toll estimates based on vehicle size
    toll_per_km = 2.0
    if vehicle_type == "Mini Truck":
        toll_per_km = 1.2
    elif vehicle_type == "Heavy Truck":
        toll_per_km = 3.0
    elif vehicle_type == "Cargo Three-Wheeler":
        toll_per_km = 0.0
        
    maintenance_per_km = 5.0
    driver_per_km = 4.0 # roughly assuming 200/hr and 50km/hr
    
    total_cost_per_km = fuel_cost_per_km + toll_per_km + maintenance_per_km + driver_per_km
    suggested_rate = round(total_cost_per_km * 1.20, 2) # Add 20% margin

    return {
        "success": True,
        "fuel_price": live_price,
        "fuel_type": fuel_type,
        "location": fuel_info.get("location"),
        "is_estimate": fuel_info.get("is_estimate"),
        "suggested_rate_per_km": suggested_rate
    }

@router.post("/plan")
async def create_transport_plan(payload: TransportPlanInput):
    """
    Run full LangGraph Transport Agent workflow for a standalone transport requirement.
    Uses OSRM routing and deterministic cost calculation engine.
    """
    req_dict = payload.model_dump()
    state_result = await run_transport_workflow(req_dict)

    if not state_result.get("is_valid_request", True):
        raise HTTPException(status_code=400, detail=state_result.get("validation_error", "Invalid transport request"))

    plan = state_result.get("final_transport_plan")
    if not plan or state_result.get("status") in ("INFEASIBLE", "FAILED") or not state_result.get("selected_vehicle"):
        return {
            "success": False,
            "status": "INFEASIBLE",
            "message": "No vehicle available matching requested quantity and hard constraints.",
            "rejected_vehicles": state_result.get("rejected_vehicles", []),
            "logs": state_result.get("logs", [])
        }

    if plan and plan.get("vehicle_id"):
        # Save trip record asynchronously
        await Database.save_transport_trip_async({
            "request_id": plan.get("request_id"),
            "vehicle_id": plan.get("vehicle_id"),
            "vehicle_type": plan.get("vehicle_type"),
            "crop": plan.get("crop"),
            "quantity_kg": plan.get("quantity_kg"),
            "pickup_location": plan.get("pickup_location"),
            "delivery_location": plan.get("delivery_location"),
            "distance_km": plan.get("distance_km"),
            "estimated_duration_hours": plan.get("estimated_duration_hours"),
            "fuel_cost": plan.get("cost_breakdown", {}).get("fuel_cost", 0.0),
            "toll_cost": plan.get("cost_breakdown", {}).get("toll_cost", 0.0),
            "driver_cost": plan.get("cost_breakdown", {}).get("driver_cost", 0.0),
            "maintenance_cost": plan.get("cost_breakdown", {}).get("maintenance_cost", 0.0),
            "loading_cost": plan.get("cost_breakdown", {}).get("loading_cost", 0.0),
            "waiting_cost": plan.get("cost_breakdown", {}).get("waiting_cost", 0.0),
            "total_operating_cost": plan.get("total_operating_cost"),
            "minimum_acceptable_price": plan.get("minimum_acceptable_price"),
            "agreed_price": plan.get("agreed_price"),
            "expected_profit": plan.get("expected_profit"),
            "status": plan.get("status", "CONFIRMED"),
            "details_json": plan,
            "created_at": datetime.now(timezone.utc).isoformat()
        })

    return {
        "success": True,
        "data": plan,
        "full_state": state_result
    }


from backend.services.auto_negotiation_service import run_parallel_negotiation

@router.post("/parallel-negotiate")
async def parallel_negotiate_transport(payload: TransportPlanInput):
    """
    Finds top matching vehicles based on constraints and runs
    parallel AI negotiations with them to secure the best deal.
    """
    result = await run_parallel_negotiation(payload.model_dump())
    return result


@router.post("/negotiate")
async def negotiate_transport_price(payload: TransportNegotiationInput):
    """
    Run an interactive negotiation turn with the Transport Agent.
    Evaluates buyer offer against deterministic floor price and returns agent counter/decision.
    """
    updated_state = await run_transport_negotiation(
        current_state_dict=payload.state,
        buyer_offer=payload.buyer_offer
    )
    return {
        "success": True,
        "negotiation_status": updated_state.get("negotiation_status"),
        "agent_counter_offer": updated_state.get("agent_counter_offer"),
        "agreed_price": updated_state.get("agreed_price"),
        "explanation": updated_state.get("llm_explanation"),
        "plan": updated_state.get("final_transport_plan"),
        "state": updated_state
    }


@router.post("/requests")
async def submit_transport_request(payload: TransportPlanInput):
    """Submit a standalone transport request and generate initial quote."""
    return await create_transport_plan(payload)


@router.get("/vehicles")
async def list_transport_vehicles(status: Optional[str] = "AVAILABLE"):
    """List registered transport vehicles and current status."""
    vehicles = await get_all_vehicles(status_filter=status)
    return {"success": True, "count": len(vehicles), "data": vehicles}


@router.get("/vehicles/me")
async def list_my_transport_vehicles(current_user: dict = Depends(get_current_user)):
    """List registered transport vehicles owned by the current user."""
    from backend.db.session import AsyncSessionLocal
    from backend.db.models.transport_agent_models import DBVehicle
    from sqlalchemy import select
    
    transporter_id = current_user.get("sub", "unknown")
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(DBVehicle).where(DBVehicle.transporter_id == transporter_id)
        )
        vehicles = [v.__dict__ for v in result.scalars().all()]
        
        # Clean up SQLAlchemy state
        for v in vehicles:
            v.pop("_sa_instance_state", None)
            
    return {"success": True, "count": len(vehicles), "data": vehicles}


@router.post("/vehicles")
async def register_transport_vehicle(
    payload: VehicleRegistrationInput,
    current_user: dict = Depends(get_current_user)
):
    """Register a new vehicle in the transport fleet."""
    v_dict = payload.model_dump()
    v_id = f"veh_{uuid.uuid4().hex[:6]}"
    v_dict["vehicle_id"] = v_id
    v_dict["status"] = "AVAILABLE"
    
    # Map 'transporter_id' to the logged-in user ID so they can own this vehicle
    v_dict["transporter_id"] = current_user.get("sub", "unknown")

    # Add to DB
    from backend.db.session import AsyncSessionLocal
    from backend.db.models.transport_agent_models import DBVehicle
    async with AsyncSessionLocal() as session:
        db_veh = DBVehicle(**v_dict)
        session.add(db_veh)
        await session.commit()

    return {"success": True, "data": v_dict}


@router.get("/vehicles/{vehicle_id}")
async def get_vehicle_details(vehicle_id: str):
    """Fetch details of a single vehicle by vehicle_id."""
    vehicles = await get_all_vehicles()
    for v in vehicles:
        if v.get("vehicle_id") == vehicle_id:
            return {"success": True, "data": v}
    raise HTTPException(status_code=404, detail="Vehicle not found")


@router.put("/vehicles/{vehicle_id}")
async def update_vehicle_details(
    vehicle_id: str,
    payload: Dict[str, Any],
    current_user: dict = Depends(get_current_user)
):
    """Update details of a registered vehicle."""
    from backend.db.session import AsyncSessionLocal
    from backend.db.models.transport_agent_models import DBVehicle
    from sqlalchemy import select
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(DBVehicle).where(DBVehicle.vehicle_id == vehicle_id)
        )
        veh = result.scalars().first()
        if not veh:
            raise HTTPException(status_code=404, detail="Vehicle not found")
        for key, value in payload.items():
            if hasattr(veh, key) and key not in ("vehicle_id", "transporter_id"):
                setattr(veh, key, value)
        await session.commit()
        clean = {k: v for k, v in veh.__dict__.items() if not k.startswith("_")}
        return {"success": True, "data": clean}


@router.delete("/vehicles/{vehicle_id}")
async def delete_vehicle(
    vehicle_id: str,
    current_user: dict = Depends(get_current_user)
):
    """Remove a vehicle from the fleet."""
    from backend.db.session import AsyncSessionLocal
    from backend.db.models.transport_agent_models import DBVehicle
    from sqlalchemy import select
    
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(DBVehicle).where(DBVehicle.vehicle_id == vehicle_id)
        )
        veh = result.scalars().first()
        if not veh:
            raise HTTPException(status_code=404, detail="Vehicle not found")
        await session.delete(veh)
        await session.commit()
        return {"success": True, "message": "Vehicle removed successfully"}


@router.post("/vehicles/search")
async def search_vehicles_endpoint(payload: Dict[str, Any]):
    """Search vehicles matching quantity and refrigeration filters."""
    quantity_kg = float(payload.get("quantity_kg", 1000.0))
    refrigerated = bool(payload.get("refrigerated", False))
    from backend.services.vehicle_service import filter_suitable_vehicles
    result = await filter_suitable_vehicles(quantity_kg=quantity_kg, refrigerated_required=refrigerated)
    return {"success": True, "data": result.get("candidates", [])}


@router.post("/vehicles/recommend")
async def recommend_vehicles_endpoint(payload: Dict[str, Any]):
    """Score and rank candidate vehicles for a given transport requirement."""
    from backend.services.vehicle_service import filter_suitable_vehicles
    from backend.services.recommendation_service import recommend_vehicles_for_request
    quantity_kg = float(payload.get("quantity_kg", 1000.0))
    refrigerated = bool(payload.get("refrigerated", False))
    filter_res = await filter_suitable_vehicles(quantity_kg=quantity_kg, refrigerated_required=refrigerated)
    candidates = filter_res.get("candidates", [])
    ranked = recommend_vehicles_for_request(candidates, payload)
    return {"success": True, "data": ranked}


@router.get("/trips")
async def list_transport_trips(limit: int = 50):
    """List recent completed and active transport trips."""
    trips = await Database.list_transport_trips_async(limit=limit)
    return {"success": True, "count": len(trips), "data": trips}


@router.get("/trips/{trip_id}")
async def get_transport_trip_details(trip_id: str):
    """Fetch stored details of a transport trip."""
    trip = await Database.get_transport_trip_async(trip_id)
    if not trip:
        raise HTTPException(status_code=404, detail="Transport trip not found")
    return {"success": True, "data": trip}


@router.get("/parameters")
async def get_transport_cost_parameters():
    """Retrieve cost calculation parameters and active fuel price benchmarks."""
    fuel_info = await get_fuel_price("Diesel", "Maharashtra")
    return {
        "success": True,
        "fuel_benchmark": fuel_info,
        "cost_parameters": DEFAULT_COST_PARAMS
    }


@router.post("/marketplace/search")
async def search_transporter_marketplace(payload: Dict[str, Any]):
    """
    Search and rank candidate transport providers across large candidate pools.
    Separates Transporter Providers from Vehicles, picking one best vehicle per provider.
    """
    from backend.services.transporter_marketplace_service import (
        generate_transporter_marketplace,
        filter_and_rank_transporter_candidates
    )
    pool_size = int(payload.get("pool_size", 100))
    providers = generate_transporter_marketplace(pool_size=pool_size)
    result = filter_and_rank_transporter_candidates(providers, payload)
    return {"success": True, "data": result}


@router.post("/marketplace/negotiate")
async def adaptive_expansion_negotiation_endpoint(payload: Dict[str, Any]):
    """
    Executes windowed adaptive candidate expansion negotiation across ranked providers.
    Contracts sequential batches (e.g. 1-5 -> 6-10) until deal or exhaustion.
    """
    from backend.services.transporter_marketplace_service import (
        generate_transporter_marketplace,
        filter_and_rank_transporter_candidates,
        adaptive_candidate_expansion_negotiation
    )
    pool_size = int(payload.get("pool_size", 100))
    batch_size = int(payload.get("batch_size", 5))
    max_batches = int(payload.get("max_batches", 4))

    providers = generate_transporter_marketplace(pool_size=pool_size)
    ranking_res = filter_and_rank_transporter_candidates(providers, payload)
    ranked = ranking_res.get("ranked_candidates", [])

    deal_res = await adaptive_candidate_expansion_negotiation(
        ranked_candidates=ranked,
        transport_request=payload,
        batch_size=batch_size,
        max_batches=max_batches
    )
    return {"success": True, "data": deal_res}


@router.post("/settlement-audit")
async def audit_settlement_endpoint(payload: Dict[str, Any]):
    """
    Audits post-deal economic settlement feasibility.
    Guarantees farmer product floor price is protected against actual carrier freight.
    """
    from backend.services.transporter_marketplace_service import audit_economic_settlement
    gross_revenue = float(payload.get("gross_revenue", 0.0))
    actual_carrier_freight = float(payload.get("actual_carrier_freight", 0.0))
    actual_storage_cost = float(payload.get("actual_storage_cost", 0.0))
    quantity_kg = float(payload.get("quantity_kg", 1.0))
    farmer_product_floor_price = float(payload.get("farmer_product_floor_price", 0.0))

    result = audit_economic_settlement(
        gross_revenue=gross_revenue,
        actual_carrier_freight=actual_carrier_freight,
        actual_storage_cost=actual_storage_cost,
        quantity_kg=quantity_kg,
        farmer_product_floor_price=farmer_product_floor_price
    )
    return {"success": True, "data": result}


