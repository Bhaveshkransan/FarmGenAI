"""
backend/models/profile_model.py

Pydantic schemas for User Profile management.
Covers farmer profiles, buyer profiles, and generic user profiles.
"""

from pydantic import BaseModel, Field
from typing import Optional, List, Dict


class UserProfileUpdate(BaseModel):
    """Update user display profile."""
    name: Optional[str] = None
    location: Optional[str] = None
    language: Optional[str] = None
    phone: Optional[str] = None
    bio: Optional[str] = None
    profile_image_url: Optional[str] = None


class FarmerProfileCreate(BaseModel):
    """Full farmer profile — extends user with agricultural context."""
    user_id: str
    farm_name: Optional[str] = None
    contact_number: Optional[str] = None
    farm_size_acres: Optional[float] = None
    crops_grown: List[str] = Field(default_factory=list)
    location: str
    village: Optional[str] = None
    taluka: Optional[str] = None
    district: Optional[str] = None
    state: str = "Maharashtra"
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    farming_type: Optional[str] = None
    soil_type: Optional[str] = None
    irrigation_type: Optional[str] = None
    certifications: List[str] = Field(default_factory=list)
    preferences: Optional[Dict] = None


class FarmerProfileResponse(FarmerProfileCreate):
    id: str
    trust_score: float = 4.0
    verification_status: str = "PENDING"
    total_negotiations: int = 0
    successful_deals: int = 0


class BuyerProfileCreate(BaseModel):
    """Full buyer profile."""
    user_id: str
    company_name: Optional[str] = None
    business_type: str = "Wholesale"  # Wholesale | Retail | Restaurant | Export | Processing
    preferred_crops: List[str] = Field(default_factory=list)
    location: str
    procurement_budget_monthly: Optional[float] = None
    quality_requirements: str = "A"


class BuyerProfileResponse(BuyerProfileCreate):
    id: str
    trust_score: float = 4.0
    verification_status: str = "PENDING"
    total_purchases: int = 0


class ProfileResponse(BaseModel):
    """Combined user + role-specific profile."""
    user_id: str
    name: str
    email: str
    role: str
    location: str
    language: str
    trust_score: float
    verification_status: str
    preferences: Dict = {}
    farmer_profile: Optional[Dict] = None
    buyer_profile: Optional[Dict] = None

