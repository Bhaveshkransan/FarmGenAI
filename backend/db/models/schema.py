from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import select, delete, text, JSON
from backend.db.session import Base

class DBUser(Base):
    __tablename__ = "users"
    user_id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=True)
    email: Mapped[str] = mapped_column(nullable=True, index=True)
    password: Mapped[str] = mapped_column(nullable=True)
    location: Mapped[str] = mapped_column(nullable=True)
    language: Mapped[str] = mapped_column(nullable=True)
    role: Mapped[str] = mapped_column(nullable=True)
    verification_status: Mapped[str] = mapped_column(default="PENDING")
    verification_docs: Mapped[str] = mapped_column(default="[]")
    preferences: Mapped[str] = mapped_column(default="{}")
    trust_score: Mapped[float] = mapped_column(default=4.0)

class DBFarmer(Base):
    __tablename__ = "farmers"
    id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=True)
    contact_number: Mapped[str] = mapped_column(nullable=True)
    location: Mapped[str] = mapped_column(nullable=True)  # Detailed JSON or string
    village: Mapped[str] = mapped_column(nullable=True)
    taluka: Mapped[str] = mapped_column(nullable=True)
    district: Mapped[str] = mapped_column(nullable=True)
    state: Mapped[str] = mapped_column(nullable=True)
    latitude: Mapped[float] = mapped_column(nullable=True)
    longitude: Mapped[float] = mapped_column(nullable=True)
    language: Mapped[str] = mapped_column(nullable=True)
    farm_size_acres: Mapped[float] = mapped_column(nullable=True)
    farming_type: Mapped[str] = mapped_column(nullable=True)
    preferences: Mapped[dict] = mapped_column(type_=JSON, nullable=True)
    created_at: Mapped[str] = mapped_column(nullable=True)
    updated_at: Mapped[str] = mapped_column(nullable=True)

class DBBuyer(Base):
    __tablename__ = "buyers"
    id: Mapped[str] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(nullable=True, index=True)
    buyer_name: Mapped[str] = mapped_column(nullable=True)
    crop: Mapped[str] = mapped_column(nullable=True)
    min_price: Mapped[float] = mapped_column(nullable=True)
    max_price: Mapped[float] = mapped_column(nullable=True)
    quantity: Mapped[float] = mapped_column(nullable=True)
    location: Mapped[str] = mapped_column(nullable=True)
    urgency: Mapped[str] = mapped_column(nullable=True)
    neg_mode: Mapped[str] = mapped_column(nullable=True)
    strategy: Mapped[str] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(nullable=True)

class DBProduce(Base):
    __tablename__ = "produce"
    id: Mapped[str] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(nullable=True, index=True)
    farmer_name: Mapped[str] = mapped_column(nullable=True)
    crop: Mapped[str] = mapped_column(nullable=True)
    crop_category: Mapped[str] = mapped_column(nullable=True)
    variety: Mapped[str] = mapped_column(nullable=True)
    grade: Mapped[str] = mapped_column(nullable=True)
    quantity: Mapped[float] = mapped_column(nullable=True)
    unit: Mapped[str] = mapped_column(nullable=True, default="kg")
    min_sale_quantity: Mapped[float] = mapped_column(nullable=True)
    expected_price: Mapped[float] = mapped_column(nullable=True)
    min_price: Mapped[float] = mapped_column(nullable=True)
    price_unit: Mapped[str] = mapped_column(nullable=True, default="per_kg")
    quality_info: Mapped[dict] = mapped_column(type_=JSON, nullable=True)
    harvest_date: Mapped[str] = mapped_column(nullable=True)
    availability_date: Mapped[str] = mapped_column(nullable=True)
    preferred_selling_date: Mapped[str] = mapped_column(nullable=True)
    shelf_life: Mapped[int] = mapped_column(nullable=True)
    location: Mapped[str] = mapped_column(nullable=True)
    latitude: Mapped[float] = mapped_column(nullable=True)
    longitude: Mapped[float] = mapped_column(nullable=True)
    storage_info: Mapped[dict] = mapped_column(type_=JSON, nullable=True)
    processing_info: Mapped[dict] = mapped_column(type_=JSON, nullable=True)
    transport_reqs: Mapped[dict] = mapped_column(type_=JSON, nullable=True)
    selected_services: Mapped[dict] = mapped_column(type_=JSON, nullable=True)
    images: Mapped[list] = mapped_column(type_=JSON, nullable=True)
    description: Mapped[str] = mapped_column(nullable=True)
    language: Mapped[str] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(nullable=True, default="ACTIVE")
    created_at: Mapped[str] = mapped_column(nullable=True)
    updated_at: Mapped[str] = mapped_column(nullable=True)

class DBNegotiation(Base):
    __tablename__ = "negotiations"
    negotiation_id: Mapped[str] = mapped_column(primary_key=True)
    crop: Mapped[str] = mapped_column(nullable=True)
    quantity: Mapped[float] = mapped_column(nullable=True)
    farmer_id: Mapped[str] = mapped_column(nullable=True)
    buyer_id: Mapped[str] = mapped_column(nullable=True)
    user_id: Mapped[str] = mapped_column(nullable=True)
    farmer_name: Mapped[str] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(nullable=True)
    current_round: Mapped[int] = mapped_column(default=0)
    summary: Mapped[str] = mapped_column(nullable=True)
    final_price: Mapped[float] = mapped_column(nullable=True)
    transport_plan: Mapped[str] = mapped_column(nullable=True)
    peer_node: Mapped[str] = mapped_column(nullable=True)
    logs: Mapped[list] = mapped_column(type_=JSON, nullable=True)
    market_offers: Mapped[list] = mapped_column(type_=JSON, nullable=True)
    selected_buyer: Mapped[dict] = mapped_column(type_=JSON, nullable=True)
    signatures: Mapped[dict] = mapped_column(type_=JSON, nullable=True)
    market_price: Mapped[float] = mapped_column(nullable=True)
    min_price: Mapped[float] = mapped_column(nullable=True)

class DBOffer(Base):
    __tablename__ = "offers"
    id: Mapped[str] = mapped_column(primary_key=True)
    negotiation_id: Mapped[str] = mapped_column(nullable=True, index=True)
    round_num: Mapped[int] = mapped_column(default=0)
    sender: Mapped[str] = mapped_column(nullable=True)
    price: Mapped[float] = mapped_column(nullable=True)
    quantity: Mapped[float] = mapped_column(nullable=True)
    message: Mapped[str] = mapped_column(nullable=True)

class DBContract(Base):
    __tablename__ = "contracts"
    id: Mapped[str] = mapped_column(primary_key=True)
    negotiation_id: Mapped[str] = mapped_column(nullable=True)
    farmer_id: Mapped[str] = mapped_column(nullable=True)
    buyer_id: Mapped[str] = mapped_column(nullable=True)
    crop: Mapped[str] = mapped_column(nullable=True)
    quantity: Mapped[float] = mapped_column(nullable=True)
    final_price: Mapped[float] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(nullable=True)

class DBHistory(Base):
    __tablename__ = "history"
    id: Mapped[str] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(nullable=True, index=True)
    data: Mapped[str] = mapped_column(nullable=True)
    negotiation_id: Mapped[str] = mapped_column(nullable=True)
    crop: Mapped[str] = mapped_column(nullable=True)
    quantity: Mapped[float] = mapped_column(nullable=True)
    status: Mapped[str] = mapped_column(nullable=True)
    final_price: Mapped[float] = mapped_column(nullable=True)
    summary: Mapped[str] = mapped_column(nullable=True)
    
    # RL Strategy & Reward Memory Fields
    market_price: Mapped[float] = mapped_column(nullable=True)
    negotiation_rounds: Mapped[int] = mapped_column(nullable=True)
    successful: Mapped[bool] = mapped_column(nullable=True)
    failure_reason: Mapped[str] = mapped_column(nullable=True)
    
    farmer_strategy: Mapped[str] = mapped_column(nullable=True)
    farmer_reward: Mapped[float] = mapped_column(nullable=True)
    buyer_strategy: Mapped[str] = mapped_column(nullable=True)
    buyer_reward: Mapped[float] = mapped_column(nullable=True)
    warehouse_strategy: Mapped[str] = mapped_column(nullable=True)
    warehouse_reward: Mapped[float] = mapped_column(nullable=True)
    transport_strategy: Mapped[str] = mapped_column(nullable=True)
    transport_reward: Mapped[float] = mapped_column(nullable=True)
    processor_strategy: Mapped[str] = mapped_column(nullable=True)
    processor_reward: Mapped[float] = mapped_column(nullable=True)
    compost_strategy: Mapped[str] = mapped_column(nullable=True)
    compost_reward: Mapped[float] = mapped_column(nullable=True)

class DBAuthLog(Base):
    __tablename__ = "auth_logs"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    user_id: Mapped[str] = mapped_column(nullable=True)
    action: Mapped[str] = mapped_column(nullable=True)
    ip_address: Mapped[str] = mapped_column(nullable=True)
    timestamp: Mapped[str] = mapped_column(nullable=True)

class DBWorkflowPlan(Base):
    __tablename__ = "workflow_plans"
    plan_id: Mapped[str] = mapped_column(primary_key=True)
    user_id: Mapped[str] = mapped_column(nullable=True, index=True)
    listing_id: Mapped[str] = mapped_column(nullable=True, index=True)
    crop: Mapped[str] = mapped_column(nullable=True)
    quantity: Mapped[float] = mapped_column(nullable=True)
    urgency: Mapped[str] = mapped_column(nullable=True)
    recommendation: Mapped[str] = mapped_column(nullable=True)
    options: Mapped[list] = mapped_column(type_=JSON, nullable=True)
    created_at: Mapped[str] = mapped_column(nullable=True)

class DBMspPrice(Base):
    __tablename__ = "msp_prices"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    crop: Mapped[str] = mapped_column(nullable=False, index=True)
    crop_full_name: Mapped[str] = mapped_column(nullable=True)
    group: Mapped[str] = mapped_column(nullable=True)
    year: Mapped[str] = mapped_column(nullable=False)
    msp_price_per_quintal: Mapped[float] = mapped_column(nullable=False)

class DBMarketMapping(Base):
    __tablename__ = "market_mappings"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    district: Mapped[str] = mapped_column(nullable=False, index=True)
    market_name: Mapped[str] = mapped_column(nullable=False)
    state: Mapped[str] = mapped_column(nullable=False)

class DBCropQualityReference(Base):
    __tablename__ = "crop_quality_references"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    crop: Mapped[str] = mapped_column(nullable=False, index=True)
    variety: Mapped[str] = mapped_column(nullable=False)
    grade: Mapped[str] = mapped_column(nullable=False)
    min_size_mm: Mapped[float] = mapped_column(nullable=True)
    max_moisture_pct: Mapped[float] = mapped_column(nullable=True)
    color_standards: Mapped[str] = mapped_column(nullable=True)
    skin_firmness: Mapped[str] = mapped_column(nullable=True)
    common_defects_allowed: Mapped[str] = mapped_column(nullable=True)

class DBWarehouse(Base):
    __tablename__ = "warehouses"
    warehouse_id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False)
    district: Mapped[str] = mapped_column(nullable=False, index=True)
    location: Mapped[str] = mapped_column(nullable=False)
    type: Mapped[str] = mapped_column(nullable=False)
    capacity_mt: Mapped[float] = mapped_column(nullable=False)
    available_capacity_mt: Mapped[float] = mapped_column(nullable=False)
    price_per_mt_per_day: Mapped[float] = mapped_column(nullable=False)
    rating: Mapped[float] = mapped_column(nullable=True)
    contact_number: Mapped[str] = mapped_column(nullable=True)

class DBTransporter(Base):
    __tablename__ = "transporters"
    transporter_id: Mapped[str] = mapped_column(primary_key=True)
    provider_name: Mapped[str] = mapped_column(nullable=False)
    vehicle_type: Mapped[str] = mapped_column(nullable=False)
    capacity_mt: Mapped[float] = mapped_column(nullable=False)
    rate_per_km: Mapped[float] = mapped_column(nullable=False)
    base_fare: Mapped[float] = mapped_column(nullable=False)
    rating: Mapped[float] = mapped_column(nullable=True)
    contact_number: Mapped[str] = mapped_column(nullable=True)
    current_location: Mapped[str] = mapped_column(nullable=True)

class DBBooking(Base):
    __tablename__ = "transport_bookings"
    booking_id: Mapped[str] = mapped_column(primary_key=True)
    negotiation_id: Mapped[str] = mapped_column(nullable=True, index=True)
    crop: Mapped[str] = mapped_column(nullable=True)
    origin_location: Mapped[str] = mapped_column(nullable=True)
    destination_location: Mapped[str] = mapped_column(nullable=True)
    booked_by: Mapped[str] = mapped_column(nullable=True, index=True)
    status: Mapped[str] = mapped_column(nullable=True)
    vehicle_id: Mapped[str] = mapped_column(nullable=True)
    truck: Mapped[str] = mapped_column(nullable=True)
    capacity_kg: Mapped[float] = mapped_column(nullable=True)
    quantity: Mapped[float] = mapped_column(nullable=True)
    distance_km: Mapped[float] = mapped_column(nullable=True)
    pickup_time: Mapped[str] = mapped_column(nullable=True)
    estimated_transit_hours: Mapped[int] = mapped_column(nullable=True)
    estimated_cost: Mapped[float] = mapped_column(nullable=True)
    created_at: Mapped[str] = mapped_column(nullable=True)
    updated_at: Mapped[str] = mapped_column(nullable=True)

class DBTrustScore(Base):
    __tablename__ = "trust_scores"
    user_id: Mapped[str] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(nullable=False)
    role: Mapped[str] = mapped_column(nullable=False)
    average_rating: Mapped[float] = mapped_column(nullable=False, default=4.0)
    fulfillment_rate: Mapped[float] = mapped_column(nullable=False, default=100.0)
    payment_punctuality: Mapped[float] = mapped_column(nullable=False, default=100.0)
    total_completed_deals: Mapped[int] = mapped_column(nullable=False, default=0)
    contract_breaches: Mapped[int] = mapped_column(nullable=False, default=0)
    trust_score_final: Mapped[float] = mapped_column(nullable=False, default=4.0)

class DBSeasonalCalendar(Base):
    __tablename__ = "seasonal_calendar"
    season_id: Mapped[str] = mapped_column(primary_key=True)
    event_name: Mapped[str] = mapped_column(nullable=False)
    month_range: Mapped[str] = mapped_column(nullable=False)
    affected_crops: Mapped[str] = mapped_column(nullable=False)
    price_impact_trend: Mapped[str] = mapped_column(nullable=False)
    market_behavior_description: Mapped[str] = mapped_column(nullable=True)

class DBProcessor(Base):
    __tablename__ = "processors"
    processor_id: Mapped[str] = mapped_column(primary_key=True)
    company_name: Mapped[str] = mapped_column(nullable=False, index=True)
    crop_accepted: Mapped[str] = mapped_column(nullable=False, index=True)
    capacity_mt: Mapped[float] = mapped_column(nullable=False)
    purchase_price_per_kg: Mapped[float] = mapped_column(nullable=False)
    district: Mapped[str] = mapped_column(nullable=False, index=True)

class DBCompost(Base):
    __tablename__ = "compost_plants"
    plant_id: Mapped[str] = mapped_column(primary_key=True)
    plant_name: Mapped[str] = mapped_column(nullable=False, index=True)
    waste_accepted: Mapped[str] = mapped_column(nullable=True)
    capacity_mt: Mapped[float] = mapped_column(nullable=False)
    district: Mapped[str] = mapped_column(nullable=False, index=True)

class DBCurrentMandiPrice(Base):
    __tablename__ = "current_mandi_prices"
    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    state: Mapped[str] = mapped_column(nullable=False, index=True)
    district: Mapped[str] = mapped_column(nullable=False, index=True)
    market: Mapped[str] = mapped_column(nullable=False, index=True)
    commodity: Mapped[str] = mapped_column(nullable=False, index=True)
    variety: Mapped[str] = mapped_column(nullable=True)
    grade: Mapped[str] = mapped_column(nullable=True)
    arrival_date: Mapped[str] = mapped_column(nullable=False, index=True)
    min_price_quintal: Mapped[float] = mapped_column(nullable=True)
    max_price_quintal: Mapped[float] = mapped_column(nullable=True)
    modal_price_quintal: Mapped[float] = mapped_column(nullable=True)
    min_price_kg: Mapped[float] = mapped_column(nullable=True)
    max_price_kg: Mapped[float] = mapped_column(nullable=True)
    modal_price_kg: Mapped[float] = mapped_column(nullable=False)
    source: Mapped[str] = mapped_column(nullable=False)
    fetched_at: Mapped[str] = mapped_column(nullable=False)
    freshness: Mapped[str] = mapped_column(nullable=False, default="CURRENT")



