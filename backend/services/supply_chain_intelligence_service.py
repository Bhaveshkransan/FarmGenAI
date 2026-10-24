"""
backend/services/supply_chain_intelligence_service.py
------------------------------------------------------------------------
Intelligent Agricultural Supply-Chain Optimization Service for FarmGenAI Buyer Agent.

Capabilities:
  1. Deterministic Buyer Requirement Analysis & Constraint Validation.
  2. Multi-Factor Warehouse Evaluation & Transparent Ranking (Capacity, Storage Condition, Cost, Spoilage).
  3. Crop-Specific Shelf-Life Degradation & Usability Modeling (Harvest Elapsed Time, Transit, Temperature).
  4. Multi-Trip Transport Vehicle Optimization (Payload, Trips, Reefer Requirements, Freight, Deadline).
  5. Integrated End-to-End Landed Cost Optimization (Produce + Freight + Storage + APMC Cess + Handling).
"""

import math
import logging
from datetime import datetime, timezone, timedelta
from typing import Dict, List, Any, Optional, Tuple

from sqlalchemy import text
from database.db import AsyncSessionLocal
from shared.crop_catalog import (
    BUYER_SUPPORTED_CROPS,
    is_supported_buyer_crop,
    normalize_crop_name,
    validate_buyer_crop,
    get_crop_benchmark_info
)
from backend.services.matching_service import (
    get_distance_km_sync,
    extract_maharashtra_district,
    MAHARASHTRA_DISTRICT_COORDS
)

logger = logging.getLogger("SupplyChainIntelligence")

# Crop Specific Baseline Characteristics & Decay Standards (ICAR / APMC Guidelines)
CROP_STORAGE_RULES = {
    "Sugarcane": {
        "category": "Cash Crops",
        "base_shelf_life_days": 4, # High sucrose inversion if held > 48-72h
        "optimal_storage": "Ventilated Transit Yard / Rapid Mill Delivery",
        "requires_cold_storage": False,
        "max_ambient_holding_days": 3,
        "perishable": True,
        "cold_storage_decay_multiplier": 0.8,
        "ambient_decay_multiplier": 1.5,
        "requires_reefer_transport": False,
        "incompatible_warehouses": ["Dry Grain Silo", "Grain Terminal"],
    },
    "Soybean": {
        "category": "Oilseeds",
        "base_shelf_life_days": 180,
        "optimal_storage": "Dry Grain Silo (Moisture < 10%)",
        "requires_cold_storage": False,
        "max_ambient_holding_days": 180,
        "perishable": False,
        "cold_storage_decay_multiplier": 1.0,
        "ambient_decay_multiplier": 1.0,
        "requires_reefer_transport": False,
        "incompatible_warehouses": ["Cold Storage", "Refrigerated"],
    },
    "Cotton": {
        "category": "Fibre",
        "base_shelf_life_days": 365,
        "optimal_storage": "Ventilated Dry Warehouse (Fire Suppressed)",
        "requires_cold_storage": False,
        "max_ambient_holding_days": 365,
        "perishable": False,
        "cold_storage_decay_multiplier": 1.0,
        "ambient_decay_multiplier": 1.0,
        "requires_reefer_transport": False,
        "incompatible_warehouses": ["Cold Storage", "Refrigerated"],
    },
    "Jowar": {
        "category": "Cereals",
        "base_shelf_life_days": 240,
        "optimal_storage": "Dry Aerated Grain Silo",
        "requires_cold_storage": False,
        "max_ambient_holding_days": 240,
        "perishable": False,
        "cold_storage_decay_multiplier": 1.0,
        "ambient_decay_multiplier": 1.0,
        "requires_reefer_transport": False,
        "incompatible_warehouses": ["Cold Storage", "Refrigerated"],
    },
    "Onion": {
        "category": "Vegetables",
        "base_shelf_life_days": 60, # Ambient shelf life
        "base_cold_shelf_life_days": 180, # Cold storage extends to 6 months
        "optimal_storage": "Cold Storage (0-2°C, 65-70% RH) or Ventilated Chawl",
        "requires_cold_storage": True, # For long holding or hot transit
        "max_ambient_holding_days": 30,
        "perishable": True,
        "cold_storage_decay_multiplier": 0.35, # Slows rot & sprouting by ~65%
        "ambient_decay_multiplier": 1.35,
        "requires_reefer_transport": True, # Recommended for long haul
        "incompatible_warehouses": [],
    },
    "Bajra": {
        "category": "Millets",
        "base_shelf_life_days": 180,
        "optimal_storage": "Dry Aerated Silo / Grain Depot",
        "requires_cold_storage": False,
        "max_ambient_holding_days": 180,
        "perishable": False,
        "cold_storage_decay_multiplier": 1.0,
        "ambient_decay_multiplier": 1.0,
        "requires_reefer_transport": False,
        "incompatible_warehouses": ["Cold Storage", "Refrigerated"],
    },
    "Rice": {
        "category": "Cereals",
        "base_shelf_life_days": 365,
        "optimal_storage": "Dry Grain Silo / Controlled Moisture Depot",
        "requires_cold_storage": False,
        "max_ambient_holding_days": 365,
        "perishable": False,
        "cold_storage_decay_multiplier": 1.0,
        "ambient_decay_multiplier": 1.0,
        "requires_reefer_transport": False,
        "incompatible_warehouses": [],
    }
}


class SupplyChainIntelligenceService:
    """
    Unified Supply Chain Decision Engine for Buyer Agent.
    """

    def analyze_buyer_requirement(self, req: Dict[str, Any]) -> Dict[str, Any]:
        """
        Extracts, validates, and standardizes buyer requirements.
        Enforces deterministic validation for all mandatory operational constraints.
        """
        # 1. Crop Validation
        raw_crop = req.get("crop") or req.get("crop_name") or ""
        try:
            crop = validate_buyer_crop(raw_crop)
        except ValueError as e:
            raise ValueError(f"Invalid crop '{raw_crop}': {str(e)}")
        crop_rules = CROP_STORAGE_RULES.get(crop, CROP_STORAGE_RULES["Soybean"])

        # 2. Quantity Validation
        try:
            quantity = float(req.get("quantity") or req.get("max_quantity") or 0)
        except (ValueError, TypeError):
            raise ValueError("Quantity must be a valid numerical value.")
        if quantity <= 0:
            raise ValueError(f"Quantity must be strictly greater than 0 kg. Provided: {quantity}")

        # 3. Budget & Price Ceiling Validation
        try:
            target_price = float(req.get("target_price") or req.get("expected_price") or 0)
        except (ValueError, TypeError):
            raise ValueError("Target price must be a valid numerical value.")
        if target_price <= 0:
            raise ValueError(f"Target price must be strictly greater than 0. Provided: {target_price}")

        max_price = float(req.get("max_price") or req.get("reservation_price") or round(target_price * 1.15, 2))
        if max_price < target_price:
            raise ValueError(f"Maximum reservation price (₹{max_price}) cannot be lower than target price (₹{target_price}).")

        # Total authorized budget
        raw_budget = req.get("budget")
        if raw_budget:
            budget = float(raw_budget)
            if budget < (target_price * quantity * 0.9):
                raise ValueError(f"Budget of ₹{budget:,.2f} is insufficient for {quantity:,.0f} kg at target price ₹{target_price}/kg.")
        else:
            budget = round(max_price * quantity * 1.15, 2) # Includes logistics headroom

        # 4. Location Validation (Strict Maharashtra APMC Mandi Hub)
        location = str(req.get("location") or "Pune, Maharashtra").strip()
        district = extract_maharashtra_district(location)
        if not district:
            district = "Pune"

        # 5. Timeline & Deadline Validation
        delivery_deadline = req.get("delivery_deadline") or req.get("deadline")
        earliest_delivery = req.get("earliest_delivery") or req.get("earliest_inflow")
        
        parsed_deadline = None
        parsed_earliest = None
        now_date = datetime.now(timezone.utc).date()

        if delivery_deadline:
            try:
                parsed_deadline = datetime.fromisoformat(str(delivery_deadline).replace("Z", "+00:00")).date()
            except Exception:
                try:
                    parsed_deadline = datetime.strptime(str(delivery_deadline), "%Y-%m-%d").date()
                except Exception:
                    pass

        if earliest_delivery:
            try:
                parsed_earliest = datetime.fromisoformat(str(earliest_delivery).replace("Z", "+00:00")).date()
            except Exception:
                try:
                    parsed_earliest = datetime.strptime(str(earliest_delivery), "%Y-%m-%d").date()
                except Exception:
                    pass

        if parsed_earliest and parsed_deadline and parsed_earliest > parsed_deadline:
            raise ValueError(f"Earliest acceptable inflow ({parsed_earliest}) cannot be after required delivery deadline ({parsed_deadline}).")

        days_to_deadline = (parsed_deadline - now_date).days if parsed_deadline else 14
        if days_to_deadline < 0:
            raise ValueError(f"Delivery deadline ({parsed_deadline}) is in the past. Procurement must be for future fulfillment.")

        # 6. Quality & Storage Constraints
        grade = str(req.get("grade") or req.get("quality_grade") or req.get("quality_preference") or "Grade A").strip()
        shelf_life_needed = int(req.get("shelf_life") or req.get("min_shelf_life") or 14)
        require_cold_chain = bool(req.get("require_cold_chain") or crop_rules["requires_cold_storage"])

        return {
            "crop": crop,
            "crop_category": crop_rules["category"],
            "variety": req.get("variety") or req.get("variety_preference") or "Commercial Standard",
            "quantity_kg": quantity,
            "unit": "kg",
            "target_price": target_price,
            "max_price": max_price,
            "budget": budget,
            "location": location,
            "district": district,
            "delivery_deadline": str(parsed_deadline) if parsed_deadline else None,
            "earliest_delivery": str(parsed_earliest) if parsed_earliest else None,
            "days_to_deadline": days_to_deadline,
            "shelf_life_needed_days": shelf_life_needed,
            "grade": grade,
            "require_cold_chain": require_cold_chain,
            "strategy": req.get("strategy") or "Balanced Mandi Procurement",
            "urgency": req.get("urgency") or ("HIGH" if days_to_deadline <= 3 else "MEDIUM"),
            "storage_rules": crop_rules
        }

    async def evaluate_warehouses(
        self,
        crop: str,
        quantity_kg: float,
        location: str,
        storage_days: int = 7,
        require_cold: bool = False,
        session = None
    ) -> Dict[str, Any]:
        """
        Evaluates eligible warehouses from the database against:
        - Crop compatibility and storage conditions (ambient silo vs cold storage)
        - Available capacity vs required quantity
        - Distance from origin / destination
        - Storage cost over planned duration
        - Spoilage risk calculation
        Outputs selected warehouse, ranked alternatives, and detailed rejection reasons.
        """
        crop_norm = normalize_crop_name(crop)
        crop_rules = CROP_STORAGE_RULES.get(crop_norm, CROP_STORAGE_RULES["Soybean"])
        buyer_dist = extract_maharashtra_district(location) or "Pune"

        # Query all active warehouses from PostgreSQL
        warehouses_data = []
        if session:
            res = await session.execute(text("""
                SELECT warehouse_id, name, district, location, type, capacity_mt, available_capacity_mt, price_per_mt_per_day, rating
                FROM warehouses
            """))
            for r in res.fetchall():
                warehouses_data.append({
                    "warehouse_id": r[0],
                    "name": r[1],
                    "district": r[2],
                    "location": r[3],
                    "type": r[4],
                    "capacity_kg": float(r[5] or 25000) * 1000.0,
                    "available_capacity_kg": float(r[6] or 10000) * 1000.0,
                    "cost_per_kg_per_day": float(r[7] or 80.0) / 1000.0,
                    "rating": float(r[8] or 4.7),
                    "refrigerated": "cold" in str(r[4]).lower() or "refrigerated" in str(r[4]).lower()
                })
        else:
            async with AsyncSessionLocal() as db_session:
                res = await db_session.execute(text("""
                    SELECT warehouse_id, name, district, location, type, capacity_mt, available_capacity_mt, price_per_mt_per_day, rating
                    FROM warehouses
                """))
                for r in res.fetchall():
                    warehouses_data.append({
                        "warehouse_id": r[0],
                        "name": r[1],
                        "district": r[2],
                        "location": r[3],
                        "type": r[4],
                        "capacity_kg": float(r[5] or 25000) * 1000.0,
                        "available_capacity_kg": float(r[6] or 10000) * 1000.0,
                        "cost_per_kg_per_day": float(r[7] or 80.0) / 1000.0,
                        "rating": float(r[8] or 4.7),
                        "refrigerated": "cold" in str(r[4]).lower() or "refrigerated" in str(r[4]).lower()
                    })

        feasible_warehouses = []
        rejected_warehouses = []

        for wh in warehouses_data:
            wh_id = wh["warehouse_id"]
            wh_name = wh["name"]
            wh_dist = wh["district"]
            wh_type = wh["type"]
            avail_cap = wh["available_capacity_kg"]
            is_cold = wh["refrigerated"]
            rate_per_kg_day = wh["cost_per_kg_per_day"]

            # 1. Capacity Check (Hard Constraint)
            if avail_cap < quantity_kg:
                rejected_warehouses.append({
                    "warehouse_id": wh_id,
                    "name": wh_name,
                    "reason": f"Insufficient capacity: required {quantity_kg:,.0f} kg, available {avail_cap:,.0f} kg."
                })
                continue

            # 2. Crop Storage Compatibility Check (Hard Constraint)
            incompatible = False
            for bad_type in crop_rules.get("incompatible_warehouses", []):
                if bad_type.lower() in wh_type.lower():
                    rejected_warehouses.append({
                        "warehouse_id": wh_id,
                        "name": wh_name,
                        "reason": f"Crop incompatible: {crop_norm} cannot be stored in {wh_type}."
                    })
                    incompatible = True
                    break
            if incompatible:
                continue

            # 3. Refrigeration Suitability Check
            if require_cold and not is_cold:
                rejected_warehouses.append({
                    "warehouse_id": wh_id,
                    "name": wh_name,
                    "reason": f"Storage condition violation: {crop_norm} requires refrigerated cold storage, but facility is {wh_type}."
                })
                continue

            # 4. Distance & Logistics Metric
            dist_km = get_distance_km_sync(wh["location"], location)

            # 5. Financial Cost Modeling
            total_storage_cost = round(rate_per_kg_day * quantity_kg * storage_days, 2)
            cost_per_kg = round(total_storage_cost / quantity_kg, 3)

            # 6. Spoilage Risk Calculation (Data-driven estimation)
            if is_cold:
                spoilage_risk_pct = round(1.5 + (storage_days * 0.15), 1) # Low cold-chain decay
            elif crop_rules["perishable"]:
                spoilage_risk_pct = round(8.0 + (storage_days * 1.8), 1) # Ambient perishable decay
            else:
                spoilage_risk_pct = round(0.5 + (storage_days * 0.05), 1) # Ambient dry grain

            # 7. Multi-Factor Transparent Compatibility Scoring (0 to 100)
            # Distance proximity (35 pts), capacity headroom (25 pts), cost efficiency (25 pts), rating (15 pts)
            proximity_score = max(0.0, 35.0 - (dist_km * 0.07))
            headroom_ratio = min(1.0, avail_cap / max(quantity_kg * 1.5, 1.0))
            headroom_score = headroom_ratio * 25.0
            cost_score = max(5.0, 25.0 - (rate_per_kg_day * 120.0))
            rating_score = (wh["rating"] / 5.0) * 15.0

            suitability_score = round(proximity_score + headroom_score + cost_score + rating_score, 1)

            feasible_warehouses.append({
                "warehouse_id": wh_id,
                "name": wh_name,
                "location": wh["location"],
                "district": wh_dist,
                "type": wh_type,
                "distance_km": dist_km,
                "available_capacity_kg": avail_cap,
                "required_capacity_kg": quantity_kg,
                "capacity_utilization_pct": round((quantity_kg / wh["capacity_kg"]) * 100, 1),
                "storage_days": storage_days,
                "daily_rate_per_kg": rate_per_kg_day,
                "total_storage_cost": total_storage_cost,
                "storage_cost_per_kg": cost_per_kg,
                "spoilage_risk_pct": spoilage_risk_pct,
                "is_refrigerated": is_cold,
                "suitability_score": suitability_score,
                "selection_reason": f"Optimal {wh_type} in {wh_dist} ({dist_km} km away). Holds {avail_cap:,.0f} kg capacity with {spoilage_risk_pct}% estimated spoilage risk."
            })

        # Rank by suitability score descending
        feasible_warehouses.sort(key=lambda x: (-x["suitability_score"], x["total_storage_cost"]))

        selected_wh = feasible_warehouses[0] if feasible_warehouses else None

        return {
            "selected_warehouse": selected_wh,
            "ranked_warehouses": feasible_warehouses,
            "rejected_warehouses": rejected_warehouses,
            "feasible_count": len(feasible_warehouses),
            "rejected_count": len(rejected_warehouses),
            "is_feasible": selected_wh is not None
        }

    def evaluate_shelf_life(
        self,
        crop: str,
        harvest_date_str: Optional[str] = None,
        storage_days: int = 7,
        transit_hours: float = 8.0,
        is_refrigerated: bool = False,
        required_shelf_life_days: int = 7
    ) -> Dict[str, Any]:
        """
        Crop-specific shelf-life degradation calculation.
        Accounts for:
        - Baseline crop shelf life (from APMC & ICAR benchmarks)
        - Elapsed days since harvest
        - Cold-chain slowing factor vs ambient acceleration
        - Transit duration
        - Evaluates if product remains usable at delivery.
        """
        crop_norm = normalize_crop_name(crop)
        rules = CROP_STORAGE_RULES.get(crop_norm, CROP_STORAGE_RULES["Soybean"])

        # 1. Base Shelf Life
        if is_refrigerated and "base_cold_shelf_life_days" in rules:
            base_shelf_life = rules["base_cold_shelf_life_days"]
        else:
            base_shelf_life = rules["base_shelf_life_days"]

        # 2. Elapsed Days Since Harvest
        now_date = datetime.now(timezone.utc).date()
        elapsed_days = 5 # Default reasonable fresh farm arrival
        if harvest_date_str:
            try:
                h_date = datetime.strptime(harvest_date_str.split("T")[0], "%Y-%m-%d").date()
                elapsed_days = max(0, (now_date - h_date).days)
            except Exception:
                pass

        # 3. Transit Time Impact
        transit_days = math.ceil(transit_hours / 24.0)

        # 4. Temperature & Storage Decay Factor
        if is_refrigerated:
            decay_multiplier = rules["cold_storage_decay_multiplier"]
            storage_type_desc = "Cold-Chain Controlled Respiration"
        else:
            decay_multiplier = rules["ambient_decay_multiplier"]
            storage_type_desc = "Ambient Field Temperature"

        effective_storage_decay_days = round(storage_days * decay_multiplier, 1)

        # 5. Remaining Usable Life at Delivery
        consumed_life_days = elapsed_days + transit_days + effective_storage_decay_days
        remaining_usable_days = round(max(0.0, base_shelf_life - consumed_life_days), 1)

        is_usable = remaining_usable_days >= required_shelf_life_days

        return {
            "crop": crop_norm,
            "base_shelf_life_days": base_shelf_life,
            "elapsed_since_harvest_days": elapsed_days,
            "transit_days": transit_days,
            "planned_storage_days": storage_days,
            "effective_storage_decay_days": effective_storage_decay_days,
            "remaining_usable_days": remaining_usable_days,
            "required_shelf_life_days": required_shelf_life_days,
            "is_viable": is_usable,
            "storage_condition": storage_type_desc,
            "status": "VIABLE" if is_usable else "INSUFFICIENT_SHELF_LIFE",
            "explanation": (
                f"Product arrives with {remaining_usable_days} days usable shelf life (required: {required_shelf_life_days} days). "
                f"Storage under {storage_type_desc} consumes {effective_storage_decay_days} effective days."
                if is_usable else
                f"Infeasible shelf life: product will only retain {remaining_usable_days} days usability at destination, "
                f"failing the required {required_shelf_life_days} days."
            ),
            "provenance": {
                "measured_data": f"Harvest date: {harvest_date_str or 'Recent'}, Base standard: {base_shelf_life} days.",
                "deterministic_calculations": f"Elapsed: {elapsed_days}d + Transit: {transit_days}d.",
                "model_predictions": f"Storage decay multiplier ({decay_multiplier}x under {storage_type_desc})."
            }
        }

    async def evaluate_transport_vehicles(
        self,
        quantity_kg: float,
        distance_km: float,
        crop: str,
        require_refrigerated: bool = False,
        max_delivery_hours: Optional[float] = None,
        session = None
    ) -> Dict[str, Any]:
        """
        Evaluates vehicles from the PostgreSQL database for multi-trip allocation.
        Accounts for:
        - Vehicle capacity vs quantity
        - Multi-trip calculation when cargo exceeds vehicle capacity
        - Refrigeration requirement for perishable crops
        - Transit duration, loading turnaround, and deadline compliance
        - Freight cost optimization
        """
        crop_norm = normalize_crop_name(crop)
        crop_rules = CROP_STORAGE_RULES.get(crop_norm, CROP_STORAGE_RULES["Soybean"])
        must_refrigerate = require_refrigerated or crop_rules["requires_reefer_transport"]

        # Base freight cost parameters across 6 vehicle classes
        VEHICLE_CLASS_RATES = {
            "Auto Loader 3W": {"rate_per_km": 14.0, "base_fare": 250.0, "avg_speed_kmh": 32.0, "turnaround_h": 1.5},
            "Tata Ace Mini Truck": {"rate_per_km": 18.0, "base_fare": 400.0, "avg_speed_kmh": 40.0, "turnaround_h": 2.0},
            "Eicher 407 LCV": {"rate_per_km": 24.0, "base_fare": 650.0, "avg_speed_kmh": 45.0, "turnaround_h": 2.5},
            "Ashok Leyland 1109 Medium": {"rate_per_km": 34.0, "base_fare": 950.0, "avg_speed_kmh": 48.0, "turnaround_h": 3.0},
            "BharatBenz 25 MT Heavy Hauler": {"rate_per_km": 48.0, "base_fare": 1800.0, "avg_speed_kmh": 42.0, "turnaround_h": 4.0},
            "Reefer Cold Chain Van": {"rate_per_km": 38.0, "base_fare": 1400.0, "avg_speed_kmh": 45.0, "turnaround_h": 2.5},
        }

        # Query database vehicles
        vehicles_data = []
        sql = "SELECT vehicle_id, vehicle_type, vehicle_name, capacity_kg, refrigerated, current_location, rating FROM vehicles WHERE status = 'AVAILABLE'"
        if session:
            res = await session.execute(text(sql))
            rows = res.fetchall()
        else:
            async with AsyncSessionLocal() as db_session:
                res = await db_session.execute(text(sql))
                rows = res.fetchall()

        for r in rows:
            vehicles_data.append({
                "vehicle_id": r[0],
                "vehicle_type": r[1],
                "vehicle_name": r[2],
                "capacity_kg": float(r[3] or 5000.0),
                "refrigerated": bool(r[4]),
                "current_location": r[5] or "Maharashtra",
                "rating": float(r[6] or 4.8)
            })

        feasible_vehicles = []
        rejected_vehicles = []

        for v in vehicles_data:
            vid = v["vehicle_id"]
            vname = v["vehicle_name"]
            vtype = v["vehicle_type"]
            cap = v["capacity_kg"]
            is_reefer = v["refrigerated"]

            # 1. Temperature Control (Hard Constraint)
            if must_refrigerate and not is_reefer:
                rejected_vehicles.append({
                    "vehicle_id": vid,
                    "name": vname,
                    "reason": f"Non-refrigerated: {crop_norm} requires active cold-chain reefer transport to prevent spoilage."
                })
                continue

            # 2. Trip Calculation
            trips_needed = math.ceil(quantity_kg / max(cap, 1.0))
            if trips_needed > 5:
                # Impractical number of single-vehicle repeat trips for commercial haulage
                rejected_vehicles.append({
                    "vehicle_id": vid,
                    "name": vname,
                    "reason": f"Excessive trips required ({trips_needed} trips). Cargo size {quantity_kg:,.0f} kg exceeds vehicle capacity ({cap:,.0f} kg) by over 5x."
                })
                continue

            # 3. Transit Duration & Turnaround Calculation
            params = VEHICLE_CLASS_RATES.get(vtype, {"rate_per_km": 28.0, "base_fare": 500.0, "avg_speed_kmh": 40.0, "turnaround_h": 2.5})
            one_way_hours = round(max(1.0, distance_km / params["avg_speed_kmh"]), 1)
            total_trip_hours = round((one_way_hours + params["turnaround_h"]) * trips_needed, 1)

            # 4. Delivery Deadline Compliance (Hard Constraint)
            if max_delivery_hours and total_trip_hours > max_delivery_hours:
                rejected_vehicles.append({
                    "vehicle_id": vid,
                    "name": vname,
                    "reason": f"Deadline breach: total delivery time of {total_trip_hours}h exceeds allowable window of {max_delivery_hours}h."
                })
                continue

            # 5. Freight Cost Calculation
            # Total distance traveled: for 1 trip = 1x distance; for >1 trip = return trips (2 * trips - 1) * dist
            haul_distance_km = distance_km if trips_needed == 1 else (distance_km * (2 * trips_needed - 1))
            total_freight = round((params["rate_per_km"] * haul_distance_km) + (params["base_fare"] * trips_needed), 2)
            freight_per_kg = round(total_freight / quantity_kg, 2)

            # 6. Optimization Suitability Score (0 to 100)
            # Cost economy (40 pts), trips efficiency (30 pts), transit speed (20 pts), rating (10 pts)
            cost_pts = max(5.0, 40.0 - (freight_per_kg * 4.0))
            trip_pts = 30.0 if trips_needed == 1 else (20.0 if trips_needed == 2 else 10.0)
            speed_pts = max(5.0, 20.0 - (total_trip_hours * 0.3))
            rating_pts = (v["rating"] / 5.0) * 10.0
            total_score = round(cost_pts + trip_pts + speed_pts + rating_pts, 1)

            feasible_vehicles.append({
                "vehicle_id": vid,
                "vehicle_name": vname,
                "vehicle_type": vtype,
                "payload_capacity_kg": cap,
                "trips_required": trips_needed,
                "single_trip_distance_km": distance_km,
                "total_haul_distance_km": haul_distance_km,
                "estimated_transit_hours": total_trip_hours,
                "total_freight_cost": total_freight,
                "freight_cost_per_kg": freight_per_kg,
                "is_refrigerated": is_reefer,
                "suitability_score": total_score,
                "selection_reason": f"Class {vtype} assigned for {quantity_kg:,.0f} kg ({trips_needed} trip(s), ₹{freight_per_kg}/kg freight, {total_trip_hours}h transit)."
            })

        feasible_vehicles.sort(key=lambda x: (-x["suitability_score"], x["total_freight_cost"]))
        selected_vehicle = feasible_vehicles[0] if feasible_vehicles else None

        return {
            "selected_vehicle": selected_vehicle,
            "ranked_vehicles": feasible_vehicles,
            "rejected_vehicles": rejected_vehicles,
            "feasible_count": len(feasible_vehicles),
            "rejected_count": len(rejected_vehicles),
            "is_feasible": selected_vehicle is not None
        }

    async def optimize_supply_chain(
        self,
        requirement: Dict[str, Any],
        candidate_listings: Optional[List[Dict[str, Any]]] = None,
        session = None
    ) -> Dict[str, Any]:
        """
        Integrated Supply-Chain Evaluation:
        Buyer Requirement → Supplier Lot → Warehouse → Transport → Landed Cost → Recommendation.
        """
        parsed_req = self.analyze_buyer_requirement(requirement)
        crop = parsed_req["crop"]
        qty = parsed_req["quantity_kg"]
        buyer_loc = parsed_req["location"]
        buyer_max_price = parsed_req["max_price"]
        buyer_budget = parsed_req["budget"]
        storage_days = 7 if parsed_req["urgency"] == "HIGH" else 14

        # If candidate listings not passed, query real matching listings from database
        if not candidate_listings:
            from backend.services.matching_service import match_requirement_to_listings
            candidate_listings = await match_requirement_to_listings(requirement)

        if not candidate_listings:
            return {
                "status": "NO_SUPPLIER_MATCH",
                "is_feasible": False,
                "requirement": parsed_req,
                "explanation": f"No active produce listings found for {crop} meeting basic filter criteria in Maharashtra mandis.",
                "relaxation_advice": "Consider expanding procurement location radius or relaxing grade preference."
            }

        evaluated_options = []

        for lot in candidate_listings[:5]:
            lot_price = float(lot.get("min_price") or lot.get("expected_price") or 50.0)
            lot_qty = float(lot.get("quantity") or qty)
            farmer_name = lot.get("farmer_name") or "APMC Farmer"
            farmer_loc = lot.get("location") or "Maharashtra"
            harvest_date = lot.get("harvest_date")

            dist_farm_to_buyer = get_distance_km_sync(farmer_loc, buyer_loc)

            # 1. Warehouse Evaluation
            wh_eval = await self.evaluate_warehouses(
                crop=crop,
                quantity_kg=qty,
                location=farmer_loc,
                storage_days=storage_days,
                require_cold=parsed_req["require_cold_chain"],
                session=session
            )

            # 2. Transport Vehicle Evaluation
            trans_eval = await self.evaluate_transport_vehicles(
                quantity_kg=qty,
                distance_km=dist_farm_to_buyer,
                crop=crop,
                require_refrigerated=parsed_req["require_cold_chain"],
                max_delivery_hours=parsed_req["days_to_deadline"] * 24.0,
                session=session
            )

            # 3. Shelf-Life Evaluation
            transit_h = trans_eval["selected_vehicle"]["estimated_transit_hours"] if trans_eval["selected_vehicle"] else 12.0
            is_cold = wh_eval["selected_warehouse"]["is_refrigerated"] if wh_eval["selected_warehouse"] else False
            shelf_eval = self.evaluate_shelf_life(
                crop=crop,
                harvest_date_str=harvest_date,
                storage_days=storage_days,
                transit_hours=transit_h,
                is_refrigerated=is_cold,
                required_shelf_life_days=parsed_req["shelf_life_needed_days"]
            )

            # 4. Landed Cost Calculation
            freight_per_kg = trans_eval["selected_vehicle"]["freight_cost_per_kg"] if trans_eval["selected_vehicle"] else 4.50
            storage_per_kg = wh_eval["selected_warehouse"]["storage_cost_per_kg"] if wh_eval["selected_warehouse"] else 1.20
            apmc_cess_per_kg = round(lot_price * 0.01, 2) # Statutory 1% APMC cess
            handling_per_kg = 0.25 # Standard APMC weighment & loading cess

            landed_cost_per_kg = round(lot_price + freight_per_kg + storage_per_kg + apmc_cess_per_kg + handling_per_kg, 2)
            total_landed_expenditure = round(landed_cost_per_kg * qty, 2)

            # Feasibility Checks
            is_price_feasible = lot_price <= buyer_max_price
            is_budget_feasible = total_landed_expenditure <= buyer_budget
            is_logistics_feasible = wh_eval["is_feasible"] and trans_eval["is_feasible"]
            is_shelf_life_feasible = shelf_eval["is_viable"]

            overall_feasible = is_price_feasible and is_budget_feasible and is_logistics_feasible and is_shelf_life_feasible

            infeasibility_reasons = []
            if not is_price_feasible:
                infeasibility_reasons.append(f"Supplier ask of ₹{lot_price}/kg exceeds buyer price ceiling of ₹{buyer_max_price}/kg.")
            if not is_budget_feasible:
                infeasibility_reasons.append(f"Total landed cost ₹{total_landed_expenditure:,.2f} exceeds total budget ₹{buyer_budget:,.2f}.")
            if not wh_eval["is_feasible"]:
                infeasibility_reasons.append(f"No compatible warehouse available for {crop} in region.")
            if not trans_eval["is_feasible"]:
                infeasibility_reasons.append("No suitable vehicle available meeting payload or reefer criteria.")
            if not is_shelf_life_feasible:
                infeasibility_reasons.append(f"Shelf life insufficient ({shelf_eval['remaining_usable_days']}d < {parsed_req['shelf_life_needed_days']}d).")

            evaluated_options.append({
                "lot_id": lot.get("id") or lot.get("listing_id"),
                "farmer_name": farmer_name,
                "origin_location": farmer_loc,
                "distance_km": dist_farm_to_buyer,
                "base_price_per_kg": lot_price,
                "freight_cost_per_kg": freight_per_kg,
                "storage_cost_per_kg": storage_per_kg,
                "apmc_cess_per_kg": apmc_cess_per_kg,
                "handling_per_kg": handling_per_kg,
                "landed_cost_per_kg": landed_cost_per_kg,
                "total_landed_expenditure": total_landed_expenditure,
                "is_feasible": overall_feasible,
                "infeasibility_reasons": infeasibility_reasons,
                "selected_warehouse": wh_eval["selected_warehouse"],
                "selected_vehicle": trans_eval["selected_vehicle"],
                "shelf_life_assessment": shelf_eval,
                "compatibility_score": lot.get("compatibility_score", 85.0)
            })

        # Rank: Feasible options first (ordered by landed cost per kg), then infeasible options
        evaluated_options.sort(key=lambda x: (not x["is_feasible"], x["landed_cost_per_kg"], -x["compatibility_score"]))

        best_option = evaluated_options[0] if evaluated_options else None
        has_executable = best_option and best_option["is_feasible"]

        relaxation_advice = None
        if not has_executable and evaluated_options:
            top_infeasible = evaluated_options[0]
            reasons = top_infeasible["infeasibility_reasons"]
            if any("exceeds buyer price ceiling" in r for r in reasons):
                diff = round(top_infeasible["base_price_per_kg"] - buyer_max_price, 2)
                relaxation_advice = f"Increase maximum reservation price by ₹{diff}/kg to unlock available Grade A market lots."
            elif any("exceeds total budget" in r for r in reasons):
                budget_diff = round(top_infeasible["total_landed_expenditure"] - buyer_budget, 2)
                relaxation_advice = f"Increase procurement budget by ₹{budget_diff:,.2f} to cover inter-district freight and buffer storage."
            elif any("Shelf life insufficient" in r for r in reasons):
                relaxation_advice = "Relax minimum required shelf-life window or choose expedited cold-chain haulage."
            else:
                relaxation_advice = "Consider sourcing from alternate APMC mandi hubs."

        return {
            "status": "OPTIMAL_PLAN_FOUND" if has_executable else "INFEASIBLE_CONSTRAINTS",
            "is_feasible": has_executable,
            "requirement": parsed_req,
            "best_option": best_option,
            "all_evaluated_options": evaluated_options,
            "relaxation_advice": relaxation_advice
        }


# Singleton service instance
supply_chain_intelligence = SupplyChainIntelligenceService()
supply_chain_intelligence_service = supply_chain_intelligence
