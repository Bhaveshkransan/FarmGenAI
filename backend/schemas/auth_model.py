from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict


class SignupRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    location: str
    language: str = "Marathi"
    role: str # Added for role-based testing
    buyer_persona: Optional[str] = None # restaurant, food_processing, wholesale_trader, retail_chain, institutional
    business_name: Optional[str] = None
    fssai_license: Optional[str] = None
    gstin: Optional[str] = None
    mandi_license: Optional[str] = None
    processing_capacity: Optional[str] = None
    procurement_window: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class AuthResponse(BaseModel):
    user_id: str
    name: str
    email: EmailStr
    location: str
    language: str
    role: Optional[str] = None
    verification_status: Optional[str] = "PENDING"
    preferences: Optional[Dict] = {}
    trust_score: float = 4.0
    message: str
    buyer_persona: Optional[str] = None
    business_name: Optional[str] = None
    fssai_license: Optional[str] = None
    gstin: Optional[str] = None


class VerificationRequest(BaseModel):
    user_id: Optional[str] = None
    docs: List[str] # List of mock file names


class PreferenceRequest(BaseModel):
    user_id: Optional[str] = None
    preferences: Dict
