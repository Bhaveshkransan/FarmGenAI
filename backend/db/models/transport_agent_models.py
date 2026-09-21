"""
backend/db/models/transport_agent_models.py

SQLAlchemy ORM models for the independent Transport Agent module.
Includes DB models for vehicles, transport requests, fuel prices, toll rates,
transport cost parameters, and completed/active transport trips.
"""

from sqlalchemy import JSON, Float, Integer, String, Boolean
from sqlalchemy.orm import Mapped, mapped_column
from backend.db.session import Base


class DBVehicle(Base):
    __tablename__ = "vehicles"

    vehicle_id: Mapped[str] = mapped_column(String, primary_key=True)
    transporter_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    vehicle_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    vehicle_name: Mapped[str] = mapped_column(String, nullable=True)
    capacity_kg: Mapped[float] = mapped_column(Float, nullable=False)
    fuel_type: Mapped[str] = mapped_column(String, nullable=False, default="Diesel")
    fuel_efficiency_kmpl: Mapped[float] = mapped_column(Float, nullable=False, default=10.0)
    current_location: Mapped[str] = mapped_column(String, nullable=True, default="Ahmednagar")
    current_latitude: Mapped[float] = mapped_column(Float, nullable=True)
    current_longitude: Mapped[float] = mapped_column(Float, nullable=True)
    refrigerated: Mapped[bool] = mapped_column(Boolean, default=False)
    temperature_min_c: Mapped[float] = mapped_column(Float, nullable=True)
    temperature_max_c: Mapped[float] = mapped_column(Float, nullable=True)
    status: Mapped[str] = mapped_column(String, default="AVAILABLE", index=True)
    rating: Mapped[float] = mapped_column(Float, default=4.5)
    contact_number: Mapped[str] = mapped_column(String, nullable=True)


class DBTransportRequest(Base):
    __tablename__ = "transport_requests"

    request_id: Mapped[str] = mapped_column(String, primary_key=True)
    shipment_id: Mapped[str] = mapped_column(String, nullable=True, index=True)
    crop: Mapped[str] = mapped_column(String, nullable=False)
    quantity_kg: Mapped[float] = mapped_column(Float, nullable=False)
    quality: Mapped[str] = mapped_column(String, nullable=True, default="Grade A")
    pickup_location: Mapped[str] = mapped_column(String, nullable=False)
    delivery_location: Mapped[str] = mapped_column(String, nullable=False)
    delivery_deadline_hours: Mapped[float] = mapped_column(Float, nullable=False, default=12.0)
    shelf_life_hours: Mapped[float] = mapped_column(Float, nullable=True, default=24.0)
    urgency: Mapped[str] = mapped_column(String, default="NORMAL")
    temperature_requirement_c: Mapped[float] = mapped_column(Float, nullable=True)
    refrigerated_required: Mapped[bool] = mapped_column(Boolean, default=False)
    status: Mapped[str] = mapped_column(String, default="PENDING")
    created_at: Mapped[str] = mapped_column(String, nullable=True)


class DBFuelPrice(Base):
    __tablename__ = "fuel_prices"

    fuel_price_id: Mapped[str] = mapped_column(String, primary_key=True)
    location: Mapped[str] = mapped_column(String, nullable=False, index=True)
    state: Mapped[str] = mapped_column(String, nullable=True, default="Maharashtra")
    fuel_type: Mapped[str] = mapped_column(String, nullable=False, default="Diesel")
    price_per_litre: Mapped[float] = mapped_column(Float, nullable=False)
    effective_date: Mapped[str] = mapped_column(String, nullable=True)
    source: Mapped[str] = mapped_column(String, default="PPAC/IndianOil Benchmark")


class DBTollRate(Base):
    __tablename__ = "toll_rates"

    toll_id: Mapped[str] = mapped_column(String, primary_key=True)
    toll_plaza: Mapped[str] = mapped_column(String, nullable=False)
    route_or_highway: Mapped[str] = mapped_column(String, nullable=False, index=True)
    vehicle_category: Mapped[str] = mapped_column(String, nullable=False)
    amount: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(String, default="NHAI Rate Matrix")


class DBTransportCostParameter(Base):
    __tablename__ = "transport_cost_parameters"

    parameter_id: Mapped[str] = mapped_column(String, primary_key=True)
    vehicle_type: Mapped[str] = mapped_column(String, nullable=False, index=True)
    driver_cost_per_hour: Mapped[float] = mapped_column(Float, nullable=False, default=200.0)
    maintenance_cost_per_km: Mapped[float] = mapped_column(Float, nullable=False, default=5.0)
    loading_cost: Mapped[float] = mapped_column(Float, nullable=False, default=200.0)
    unloading_cost: Mapped[float] = mapped_column(Float, nullable=False, default=200.0)
    waiting_cost_per_hour: Mapped[float] = mapped_column(Float, nullable=False, default=150.0)
    risk_buffer_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.05)
    minimum_profit_margin_pct: Mapped[float] = mapped_column(Float, nullable=False, default=0.15)


class DBTransportTrip(Base):
    __tablename__ = "transport_trips"

    trip_id: Mapped[str] = mapped_column(String, primary_key=True)
    request_id: Mapped[str] = mapped_column(String, nullable=True, index=True)
    vehicle_id: Mapped[str] = mapped_column(String, nullable=False, index=True)
    vehicle_type: Mapped[str] = mapped_column(String, nullable=False)
    crop: Mapped[str] = mapped_column(String, nullable=True)
    quantity_kg: Mapped[float] = mapped_column(Float, nullable=False)
    pickup_location: Mapped[str] = mapped_column(String, nullable=False)
    delivery_location: Mapped[str] = mapped_column(String, nullable=False)
    distance_km: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_duration_hours: Mapped[float] = mapped_column(Float, nullable=False)
    fuel_cost: Mapped[float] = mapped_column(Float, nullable=False)
    toll_cost: Mapped[float] = mapped_column(Float, nullable=False)
    driver_cost: Mapped[float] = mapped_column(Float, nullable=False)
    maintenance_cost: Mapped[float] = mapped_column(Float, nullable=False)
    loading_cost: Mapped[float] = mapped_column(Float, nullable=False)
    waiting_cost: Mapped[float] = mapped_column(Float, nullable=False)
    total_operating_cost: Mapped[float] = mapped_column(Float, nullable=False)
    minimum_acceptable_price: Mapped[float] = mapped_column(Float, nullable=False)
    agreed_price: Mapped[float] = mapped_column(Float, nullable=False)
    expected_profit: Mapped[float] = mapped_column(Float, nullable=False)
    status: Mapped[str] = mapped_column(String, default="CONFIRMED")
    details_json: Mapped[dict] = mapped_column(JSON, nullable=True)
    created_at: Mapped[str] = mapped_column(String, nullable=True)
