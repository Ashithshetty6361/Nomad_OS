"""
API Response Schemas for NomadOS.
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional
from app.models.state import (
    DayPlan, 
    ActivityItem, 
    RAGDocument,
    OriginTransitPlan,
    LodgingOption,
    DiningHighlight,
    PackingChecklistItem
)


class TelemetrySummary(BaseModel):
    trace_id: str
    total_latency_ms: float
    step_latencies: Dict[str, float]
    total_tokens: int
    estimated_cost_usd: float
    models_used: Dict[str, str]
    cost_savings_usd: float


class AgentStepLog(BaseModel):
    step_name: str
    agent_name: str
    model_id: str
    latency_ms: float
    summary: str
    key_outputs: Dict[str, Any]


class PlanResponse(BaseModel):
    status: str = "SUCCESS"
    destination: str
    duration_days: int
    travel_style: str
    total_budget_usd: float
    estimated_cost_usd: float
    budget_breakdown: Dict[str, float]
    trade_off_reasoning: str
    daily_itinerary: List[DayPlan]
    enrichment_insights: Dict[str, Any]
    
    # Door-to-Door Assistant Enhancements
    origin_city: str = "Current Location"
    companions: str = "Solo"
    trip_mood: Optional[str] = None
    origin_transit: Optional[OriginTransitPlan] = None
    lodging_options: List[LodgingOption] = Field(default_factory=list)
    dining_highlights: List[DiningHighlight] = Field(default_factory=list)
    packing_checklist: List[PackingChecklistItem] = Field(default_factory=list)
    
    # Production Role Separation: Optional for customers, populated for company admin
    agent_steps: Optional[List[AgentStepLog]] = None
    telemetry: Optional[TelemetrySummary] = None
    
    # Canonical Unified Trip Model
    canonical_trip: Optional[Any] = None


class ProgressiveQuestion(BaseModel):
    key: str
    question: str
    type: str  # "choice", "slider", "chips", "date"
    options: List[Dict[str, Any]] = Field(default_factory=list)
    default_val: Optional[Any] = None
    
    # Interactive Flashcard Properties
    card_title: Optional[str] = None
    card_subtitle: Optional[str] = None
    icon: Optional[str] = "✨"
    step_number: Optional[int] = 1
    total_steps: Optional[int] = 4
    is_business_specific: Optional[bool] = False


class ExtractIntentResponse(BaseModel):
    status: str = "SUCCESS"
    original_query: str
    extracted: Dict[str, Any]
    missing_fields: List[str] = Field(default_factory=list)
    suggested_destinations: List[Any] = Field(default_factory=list)
    progressive_questions: List[ProgressiveQuestion] = Field(default_factory=list)


class RefineTripResponse(BaseModel):
    status: str = "SUCCESS"
    message: str
    updated_trip: Dict[str, Any]
    change_summary: List[str] = Field(default_factory=list)




# ==========================================
# Uber Rides API Schemas
# ==========================================

class UberPriceEstimate(BaseModel):
    product_id: str
    display_name: str  # e.g., "UberX", "UberXL", "Uber Comfort", "Uber Black"
    estimate: str      # e.g., "$15-19"
    low_estimate: Optional[float] = None
    high_estimate: Optional[float] = None
    currency_code: str = "USD"
    duration_seconds: int = 900
    distance_miles: float = 3.5
    surge_multiplier: float = 1.0


class UberPriceEstimatesResponse(BaseModel):
    pickup: str
    dropoff: str
    estimates: List[UberPriceEstimate]
    deep_link: str
    provider_mode: str  # "live", "sandbox", "mock"


class UberRideRequestPayload(BaseModel):
    product_id: str = "uberx"
    start_latitude: Optional[float] = None
    start_longitude: Optional[float] = None
    end_latitude: Optional[float] = None
    end_longitude: Optional[float] = None
    start_address: Optional[str] = "Current Location"
    end_address: str


class UberDriverInfo(BaseModel):
    name: str = "Kenji S."
    rating: float = 4.96
    phone_number: str = "+1 (555) 234-5678"
    picture_url: Optional[str] = None


class UberVehicleInfo(BaseModel):
    make: str = "Toyota"
    model: str = "Camry Hybrid"
    license_plate: str = "7XYZ89"
    color: str = "Midnight Black"


class UberRideStatusResponse(BaseModel):
    request_id: str
    status: str  # "processing", "accepted", "arriving", "in_progress", "completed", "canceled"
    product_name: str
    eta_minutes: int
    fare_estimate_usd: float
    pickup_address: str
    dropoff_address: str
    driver: Optional[UberDriverInfo] = None
    vehicle: Optional[UberVehicleInfo] = None
    deep_link: str


class UberConfigStatus(BaseModel):
    client_id_configured: bool
    server_token_configured: bool
    sandbox_mode: bool
    provider_mode: str

