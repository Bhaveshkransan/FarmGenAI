"""
tests/test_transport_agent.py

Comprehensive test suite for the independent Transport Agent module.
Tests vehicle filtering, hard constraints, OSRM routing, deterministic cost calculation,
floor price enforcement, multi-round price negotiation, and regression check for Farmer/Buyer.
"""

import asyncio
from backend.agents.transport_agent.graph import run_transport_workflow, run_transport_negotiation
from backend.services.vehicle_service import filter_suitable_vehicles
from backend.services.routing_service import calculate_transport_route
from backend.services.transport_cost_service import calculate_transportation_cost, calculate_expected_profit


async def test_valid_transport_request():
    """Test 1: Valid transport request flow."""
    request = {
        "request_id": "TR-TEST-01",
        "crop": "Tomato",
        "quantity_kg": 2000.0,
        "pickup_location": "Ahmednagar",
        "delivery_location": "Pune",
        "delivery_deadline_hours": 8.0,
        "buyer_offer": 4700.0
    }
    res = await run_transport_workflow(request)

    assert res["is_valid_request"] is True
    assert res["status"] in {"CONFIRMED", "ACCEPTED", "FEASIBLE", "IN_NEGOTIATION", "COUNTERED"}
    assert res["selected_vehicle"] is not None
    assert res["distance_km"] > 0
    assert res["total_operating_cost"] > 0
    assert res["minimum_acceptable_price"] > res["total_operating_cost"]
    assert res["final_transport_plan"] is not None


async def test_vehicle_capacity_rejection():
    """Test 2: Rejection when requested quantity exceeds vehicle capacity."""
    # Requested 20,000 kg when max single vehicle is 12,000 kg
    res = await filter_suitable_vehicles(quantity_kg=20000.0)
    assert res["success"] is False
    assert len(res["candidates"]) == 0
    assert len(res["rejected_vehicles"]) > 0


async def test_refrigeration_requirement():
    """Test 3: Refrigeration requirement hard constraint filtering."""
    # Non-refrigerated request
    res_normal = await filter_suitable_vehicles(quantity_kg=3000.0, refrigerated_required=False)
    assert res_normal["success"] is True

    # Refrigerated request MUST return a refrigerated vehicle
    res_reefer = await filter_suitable_vehicles(quantity_kg=3000.0, refrigerated_required=True)
    assert res_reefer["success"] is True
    assert res_reefer["best_vehicle"]["refrigerated"] is True


async def test_osrm_route_calculation():
    """Test 4: OSRM route calculation returns distance and estimated duration."""
    route = calculate_transport_route("Ahmednagar", "Pune")
    assert route["success"] is True
    assert route["distance_km"] > 0
    assert route["estimated_duration_hours"] > 0
    assert "estimated travel duration" in route["terminology"]["duration_label"]


async def test_deterministic_cost_calculation():
    """Test 5 & 6: Operating cost and floor price calculation."""
    dummy_vehicle = {
        "vehicle_id": "V-TEST",
        "vehicle_type": "Medium Truck",
        "fuel_type": "Diesel",
        "fuel_efficiency_kmpl": 10.0
    }
    cost_res = await calculate_transportation_cost(
        vehicle=dummy_vehicle,
        distance_km=150.0,
        estimated_duration_hours=4.0
    )

    assert cost_res["total_operating_cost"] > 0
    assert cost_res["minimum_acceptable_price"] > cost_res["risk_adjusted_cost"]
    assert cost_res["initial_quote"] > cost_res["minimum_acceptable_price"]


async def test_offer_below_floor_price():
    """Test 7 & 8: Buyer offer below floor price must be COUNTERED or REJECTED."""
    request = {
        "crop": "Tomato",
        "quantity_kg": 2000.0,
        "pickup_location": "Ahmednagar",
        "delivery_location": "Pune",
        "buyer_offer": 1000.0  # Unreasonably low offer below operating cost
    }
    res = await run_transport_workflow(request)

    assert res["negotiation_status"] in {"COUNTERED", "REJECTED", "IN_NEGOTIATION"}
    assert res["agreed_price"] is None or res["agreed_price"] >= res["minimum_acceptable_price"]


async def test_offer_above_floor_price():
    """Test 9: Buyer offer at/above floor price is ACCEPTED."""
    request = {
        "crop": "Tomato",
        "quantity_kg": 2000.0,
        "pickup_location": "Ahmednagar",
        "delivery_location": "Pune",
        "buyer_offer": 10000.0  # Generous offer well above floor price
    }
    res = await run_transport_workflow(request)

    assert res["negotiation_status"] == "ACCEPTED"
    assert res["agreed_price"] == 10000.0
    assert res["final_transport_plan"]["status"] == "CONFIRMED"


async def test_multi_round_negotiation():
    """Test 10: Multi-round negotiation flow."""
    request = {
        "crop": "Tomato",
        "quantity_kg": 2000.0,
        "pickup_location": "Ahmednagar",
        "delivery_location": "Pune",
        "buyer_offer": 2000.0  # Round 1 low offer
    }
    state_r1 = await run_transport_workflow(request)
    assert state_r1["negotiation_status"] in {"COUNTERED", "IN_NEGOTIATION"}

    # Round 2: Buyer raises offer above floor price
    floor = state_r1["minimum_acceptable_price"]
    good_offer = round(floor + 500.0, 2)
    state_r2 = await run_transport_negotiation(state_r1, buyer_offer=good_offer)

    assert state_r2["negotiation_status"] == "ACCEPTED"
    assert state_r2["agreed_price"] == good_offer


async def test_farmer_buyer_mvp_unaffected():
    """Test 11: Regression check to ensure existing database/services still work."""
    from backend.repositories.database_repo import Database
    # Query buyers list from existing repository
    buyers = await Database.list_buyers_async()
    assert isinstance(buyers, list)

    # Query produce list from existing repository
    produce = await Database.list_produce_async()
    assert isinstance(produce, list)
