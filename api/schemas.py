"""Pydantic schemas for Qatar AI Platform API."""
from pydantic import BaseModel, Field
from typing import Optional, List, Any


class PriceRequest(BaseModel):
    make: str
    model: str
    trim: Optional[str] = ""
    year: int
    mileage_km: Optional[int] = None
    color_exterior: Optional[str] = ""
    body_type: Optional[str] = ""
    sunroof_flag: Optional[bool] = False
    ventilated_seats_flag: Optional[bool] = False
    displacement_cc: Optional[float] = None
    color_demand_score: Optional[float] = 70.0
    feature_demand_score: Optional[float] = 80.0


class PriceResponse(BaseModel):
    recommended_price_qar: float
    price_range_low: float
    price_range_high: float
    confidence_pct: float
    time_to_sell_days: Optional[int] = None
    time_to_sell_fast_days: Optional[int] = None  # at -6%
    time_to_sell_max_days: Optional[int] = None   # at +6%
    similar_transactions_count: Optional[int] = None
    market_context: List[str] = []
    ai_advice: Optional[str] = None
    source: str = "price_predictor"


class InventoryFilters(BaseModel):
    risk_flag: Optional[str] = None
    body_type: Optional[str] = None
    make: Optional[str] = None
    color: Optional[str] = None
    days_min: Optional[int] = None
    days_max: Optional[int] = None
    limit: int = 100
    offset: int = 0


class MarketBriefingResponse(BaseModel):
    market_health_score: Optional[float] = None
    oil_price: Optional[float] = None
    interest_rate: Optional[float] = None
    signal: str = "Hold"
    actions: List[str] = []


class MatchRequest(BaseModel):
    customer_id: Optional[int] = None
    budget_qar: Optional[float] = None
    preferred_body_type: Optional[str] = None
    preferred_color: Optional[str] = None
    top_n: int = 5


class ChatRequest(BaseModel):
    message: str
    context: Optional[dict] = None


class ChatResponse(BaseModel):
    reply: str
    sources: List[str] = []
