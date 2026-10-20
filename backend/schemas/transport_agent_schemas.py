"""
backend/schemas/transport_agent_schemas.py

Pydantic schemas for the standalone Transport Agent API endpoints.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class TransportPlanInput(BaseModel):
    request_id: Optional[str] = None
    crop: str = Field(..., min_length=1, json_schema_extra={"example": "Tomato"})
    quantity_kg: float = Field(..., gt=0, json_schema_extra={"example": 2000.0})
    pickup_location: str = Field(..., min_length=1, json_schema_extra={"example": "Ahmednagar"})
    delivery_location: str = Field(..., min_length=1, json_schema_extra={"example": "Pune"})
    delivery_deadline_hours: float = Field(12.0, gt=0, json_schema_extra={"example": 8.0})
    shelf_life_hours: float = Field(24.0, gt=0, json_schema_extra={"example": 12.0})
    urgency: Optional[str] = Field("NORMAL", json_schema_extra={"example": "HIGH"})
    refrigerated_required: bool = False
    temperature_requirement_c: Optional[float] = None
    buyer_offer: Optional[float] = Field(None, json_schema_extra={"example": 4700.0})
    max_negotiation_rounds: Optional[int] = Field(3, ge=1)


class TransportNegotiationInput(BaseModel):
    state: Dict[str, Any]
    buyer_offer: float = Field(..., gt=0, json_schema_extra={"example": 4400.0})


class VehicleRegistrationInput(BaseModel):
    transporter_id: Optional[str] = None
    registration_number: str = Field(..., min_length=1)
    driver_name: str = Field(..., min_length=1)
    base_rate_per_km: float = Field(..., gt=0)
    vehicle_type: str  # Mini Truck | LCV | Medium Truck | Heavy Truck | Refrigerated Truck | Tractor + Trailer | Cargo Three-Wheeler
    vehicle_name: str
    capacity_kg: float = Field(..., gt=0)
    fuel_type: str = "Diesel"
    fuel_efficiency_kmpl: float = Field(10.0, gt=0)
    current_location: str = "Ahmednagar"
    refrigerated: bool = False
    temperature_min_c: Optional[float] = None
    temperature_max_c: Optional[float] = None
    contact_number: Optional[str] = None
