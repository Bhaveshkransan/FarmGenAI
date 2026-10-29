from pydantic import BaseModel
from typing import List, Optional, Any, Dict


class HistoryItem(BaseModel):
    negotiation_id: str
    crop: Optional[str] = None
    quantity: Optional[float] = None
    status: Optional[str] = None
    final_price: Optional[float] = None
    summary: Optional[str] = None
    farmer: Optional[str] = None
    farmer_name: Optional[str] = None
    buyer: Optional[str] = None
    buyer_name: Optional[str] = None
    transaction_id: Optional[str] = None
    total: Optional[float] = None
    details: Optional[Dict[str, Any]] = None

    class Config:
        extra = "allow"


class HistoryResponse(BaseModel):
    user_id: str
    history: List[HistoryItem]

    class Config:
        extra = "allow"
