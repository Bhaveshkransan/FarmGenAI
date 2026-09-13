from typing import Optional, Dict, List, Any
from pydantic import BaseModel, Field, root_validator


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

    @root_validator(pre=False, skip_on_failure=True)
    def validate_logic(cls, values):
        qty = values.get('quantity')
        min_qty = values.get('min_sale_quantity')
        if qty is not None and min_qty is not None and min_qty > qty:
            raise ValueError('minimum_sale_quantity cannot be greater than available quantity')
        
        min_p = values.get('min_price')
        exp_p = values.get('expected_price')
        if min_p is not None and exp_p is not None and min_p > exp_p:
            raise ValueError('minimum price cannot be greater than expected price')
        
        return values


class CropListingUpdate(BaseModel):
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

    @root_validator(pre=False, skip_on_failure=True)
    def validate_logic(cls, values):
        qty = values.get('quantity')
        min_qty = values.get('min_sale_quantity')
        if qty is not None and min_qty is not None and min_qty > qty:
            raise ValueError('minimum_sale_quantity cannot be greater than available quantity')
        
        min_p = values.get('min_price')
        exp_p = values.get('expected_price')
        if min_p is not None and exp_p is not None and min_p > exp_p:
            raise ValueError('minimum price cannot be greater than expected price')
        
        return values
