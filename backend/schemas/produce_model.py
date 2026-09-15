from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field, model_validator


class CropListingCreate(BaseModel):
    crop: str = Field(..., example="Soybean")
    crop_category: Optional[str] = Field(None, example="Oilseeds")
    variety: str = Field(..., example="JS-335")
    grade: str = Field(..., example="A")
    quantity: float = Field(..., gt=0, example=1500.0)
    unit: str = Field("kg", example="kg")
    min_sale_quantity: float = Field(..., gt=0, example=100.0)
    expected_price: float = Field(..., gt=0, example=78.0)
    min_price: float = Field(..., gt=0, example=70.0)
    price_unit: str = Field("per_kg", example="per_kg")
    quality_info: Optional[Dict[str, Any]] = None
    harvest_date: Optional[str] = None
    availability_date: Optional[str] = None
    preferred_selling_date: Optional[str] = None
    shelf_life: int = Field(..., ge=1, example=7)
    location: str = Field(..., example="Nashik")
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    storage_info: Optional[Dict[str, Any]] = None
    processing_info: Optional[Dict[str, Any]] = None
    transport_reqs: Optional[Dict[str, Any]] = None
    selected_services: Optional[Dict[str, Any]] = None
    images: Optional[List[str]] = None
    description: str = Field("", example="Organic grade A")

    @model_validator(mode='after')
    def validate_logic(self):
        crop = self.crop
        from backend.core.constants import SUPPORTED_CROPS
        if crop:
            # Case-insensitive validation
            supported_lower = [c.lower() for c in SUPPORTED_CROPS]
            if crop.lower() not in supported_lower:
                raise ValueError(f"Crop '{crop}' is not supported. Supported crops: {SUPPORTED_CROPS}")
            # Normalize crop name
            for c in SUPPORTED_CROPS:
                if c.lower() == crop.lower():
                    self.crop = c
                    break

        qty = self.quantity
        min_qty = self.min_sale_quantity
        if qty is not None and min_qty is not None and min_qty > qty:
            raise ValueError('minimum_sale_quantity cannot be greater than available quantity')
        
        min_p = self.min_price
        exp_p = self.expected_price
        if min_p is not None and exp_p is not None and min_p > exp_p:
            raise ValueError('minimum price cannot be greater than expected price')
        
        return self


class CropListingUpdate(BaseModel):
    crop: Optional[str] = None
    quantity: float = None
    min_sale_quantity: float = None
    expected_price: float = None
    min_price: float = None
    quality_info: Optional[Dict[str, Any]] = None
    harvest_date: Optional[str] = None
    availability_date: Optional[str] = None
    preferred_selling_date: Optional[str] = None
    shelf_life: int = None
    location: str = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    storage_info: Optional[Dict[str, Any]] = None
    processing_info: Optional[Dict[str, Any]] = None
    transport_reqs: Optional[Dict[str, Any]] = None
    selected_services: Optional[Dict[str, Any]] = None
    images: Optional[List[str]] = None
    description: str = None
    status: str = None  # "ACTIVE" | "SOLD" | "EXPIRED"

    @model_validator(mode='after')
    def validate_logic(self):
        crop = getattr(self, 'crop', None)
        if crop:
            from backend.core.constants import SUPPORTED_CROPS
            supported_lower = [c.lower() for c in SUPPORTED_CROPS]
            if crop.lower() not in supported_lower:
                raise ValueError(f"Crop '{crop}' is not supported. Supported crops: {SUPPORTED_CROPS}")
            for c in SUPPORTED_CROPS:
                if c.lower() == crop.lower():
                    self.crop = c
                    break

        qty = self.quantity
        min_qty = self.min_sale_quantity
        if qty is not None and min_qty is not None and min_qty > qty:
            raise ValueError('minimum_sale_quantity cannot be greater than available quantity')
        
        min_p = self.min_price
        exp_p = self.expected_price
        if min_p is not None and exp_p is not None and min_p > exp_p:
            raise ValueError('minimum price cannot be greater than expected price')
        
        return self
