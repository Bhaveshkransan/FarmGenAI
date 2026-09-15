from pydantic import BaseModel
from typing import List, Optional


class Offer(BaseModel):
    round: int
    agent: str
    price: float
    decision: str


class StartNegotiationRequest(BaseModel):
    user_id: str | None = None
    farmer_name: str = "Unknown Farmer"
    crop: str
    quantity: float
    min_price: float
    shelf_life: int = 5
    location: str = "Maharashtra"
    quality: str = "A"
    language: str = "Marathi"
    buyer_mode: bool = False
    buyer_name: str | None = None
    buyer_budget: float | None = None
    buyer_max_quantity: float | None = None
    buyer_target_price: float | None = None
    buyer_location: str | None = None
    buyer_strategy: str | None = None
    buyer_persona: str | None = None
    max_rounds: Optional[int] = 4
    sync: Optional[bool] = False

    model_config = {
        "extra": "allow"
    }


class NegotiationResponse(BaseModel):
    negotiation_id: str
    status: str
    offers: List[Offer]


class NegotiationStatusResponse(BaseModel):
    negotiation_id: str
    status: str
    offers: List[Offer]
    summary: Optional[str] = None
    final_price: Optional[float] = None
    next_action: Optional[str] = None


class SimulationRequest(BaseModel):
    user_id: str | None = None
    scenario: str = "direct-sale"
    
    model_config = {
        "extra": "allow"
    }
