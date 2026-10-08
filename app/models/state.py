"""
State representations for the deterministic multi-agent state machine.
"""
from pydantic import BaseModel, Field
from typing import List, Dict, Any, Optional


class ContextState(BaseModel):
    """Output state from Context Parsing Agent."""
    destination: str
    duration_days: int
    budget_usd: float
    travelers_count: int
    travel_style: str  # e.g., "Luxury", "Balanced", "Backpacker", "Foodie", "Adventure"
    interests: List[str] = Field(default_factory=list)
    constraints: List[str] = Field(default_factory=list)
    confidence_score: float = 0.95
    model_used: str = ""
    # Guided Multi-Modal Fields
    origin_city: str = "Current Location"
    intent_type: str = "direct"
    companions: str = "Solo"
    trip_mood: Optional[str] = None
    lodging_style: Optional[str] = None


class ActivityItem(BaseModel):
    name: str
    category: str = "Sightseeing"  # "Sightseeing", "Food", "Culture", "Nightlife", "Shopping"
    estimated_duration_hours: float = 2.0
    estimated_cost_usd: float = 0.0
    location_area: str = "Central"
    description: str = ""
    image_url: Optional[str] = None
    why_recommended: Optional[str] = None
    is_saved: bool = False



class DiscoveryState(BaseModel):
    """Output state from Discovery Agent."""
    recommended_activities: List[ActivityItem] = Field(default_factory=list)
    top_neighborhoods: List[str] = Field(default_factory=list)
    local_culinary_highlights: List[str] = Field(default_factory=list)
    model_used: str = ""


class RAGDocument(BaseModel):
    title: str
    content: str
    category: str
    relevance_score: float
    source: str


class EnrichmentState(BaseModel):
    """Output state from RAG Enrichment Agent."""
    retrieved_guides: List[RAGDocument] = Field(default_factory=list)
    local_pro_tips: List[str] = Field(default_factory=list)
    cultural_etiquette: List[str] = Field(default_factory=list)
    transport_advice: str = ""
    model_used: str = ""


class DailyScheduleItem(BaseModel):
    time_slot: str  # "Morning", "Afternoon", "Evening", "Night"
    activity_title: str
    area: str
    description: str
    cost_estimate_usd: float
    pro_tip: Optional[str] = None
    # Uber Rides Integration
    uber_deep_link: Optional[str] = None
    estimated_uber_fare_usd: Optional[float] = None
    estimated_transit_minutes: Optional[int] = None
    dropoff_address: Optional[str] = None
    # Corporate & Business Attributes
    is_meeting: Optional[bool] = False
    wifi_rating: Optional[str] = None  # e.g. "150+ Mbps Fiber"
    noise_level: Optional[str] = None  # "Quiet", "Moderate", "Vibrant"


class DayPlan(BaseModel):
    day_number: int
    day_theme: str
    items: List[DailyScheduleItem] = Field(default_factory=list)
    day_budget_usd: float


# ==========================================
# Door-to-Door & Booking Assistant Models
# ==========================================

class OriginTransitPlan(BaseModel):
    origin_city: str
    destination_city: str
    recommended_mode: str  # "Flight (Direct)", "High-Speed Rail", "Express Coach"
    departure_hub: str
    arrival_hub: str
    estimated_roundtrip_usd: float
    booking_search_link: str
    home_to_airport_uber_link: str
    estimated_airport_uber_usd: float
    transit_tips: str


class LodgingOption(BaseModel):
    name: str
    neighborhood: str
    style: str  # "Boutique Art Hotel", "Luxury Panorama Suite", "Cozy Heritage Ryokan", "Central Family Hotel"
    estimated_nightly_usd: float
    rating: float = 4.8
    amenities: List[str] = Field(default_factory=list)
    booking_search_link: str
    why_recommended: str


class DiningHighlight(BaseModel):
    name: str
    cuisine: str
    price_tier: str  # "$", "$$", "$$$", "$$$$"
    area: str
    signature_dish: str
    reservation_tip: str


class PackingChecklistItem(BaseModel):
    id: str
    item: str
    category: str  # "Essentials & Docs", "Clothing & Weather", "Tech & Power", "Activity & Vibe Gear"
    is_essential: bool = True
    checked: bool = False
    reminder_note: Optional[str] = None


class BookingState(BaseModel):
    """Output state from Booking Reasoning Agent."""
    daily_itinerary: List[DayPlan] = Field(default_factory=list)
    budget_breakdown: Dict[str, float] = Field(default_factory=dict)
    total_estimated_cost_usd: float
    budget_variance_status: str  # "Within Budget", "Optimal", "Budget Warning"
    trade_off_reasoning: str
    # Door-to-Door, Lodging & Packing
    origin_transit: Optional[OriginTransitPlan] = None
    lodging_options: List[LodgingOption] = Field(default_factory=list)
    dining_highlights: List[DiningHighlight] = Field(default_factory=list)
    packing_checklist: List[PackingChecklistItem] = Field(default_factory=list)
    model_used: str = ""


class OrchestrationState(BaseModel):
    """Master workflow state managed by the deterministic planner."""
    trace_id: str
    raw_query: str
    current_step: str = "INITIALIZED"
    completed_steps: List[str] = Field(default_factory=list)
    
    # State components filled by respective agents
    context: Optional[ContextState] = None
    discovery: Optional[DiscoveryState] = None
    enrichment: Optional[EnrichmentState] = None
    booking: Optional[BookingState] = None
    
    # Observability & Errors
    step_latencies: Dict[str, float] = Field(default_factory=dict)
    models_routed: Dict[str, str] = Field(default_factory=dict)
    tokens_consumed: Dict[str, int] = Field(default_factory=dict)
    total_cost_usd: float = 0.0
    errors: List[str] = Field(default_factory=list)


# ==========================================
# Canonical Trip & Multi-Section Models
# ==========================================

class TravelerDetails(BaseModel):
    total: int = 1
    adults: int = 1
    children: int = 0
    seniors: int = 0
    group_type: str = "Solo"  # "Solo", "Couple", "Friends", "Family with Kids"


class TransportationOption(BaseModel):
    id: str
    mode: str  # "Flight", "Train", "Bus", "Cab"
    title: str  # e.g., "Direct Flight (IndiGo 6E-204)" or "Vande Bharat Express"
    carrier: str
    duration_str: str  # e.g. "1h 20m"
    duration_minutes: int
    price: float
    currency: str = "INR"
    transfers: str = "Direct"
    departure_time: str
    arrival_time: str
    departure_hub: str
    arrival_hub: str
    booking_link: str
    is_recommended: bool = False
    highlights: List[str] = Field(default_factory=list)


class HotelItem(BaseModel):
    id: str
    name: str
    neighborhood: str
    rating: float = 4.8
    review_count: int = 420
    price_per_night: float
    total_price: float
    currency: str = "INR"
    distance_to_activities_km: float = 2.1
    style: str = "Boutique Hotel"
    amenities: List[str] = Field(default_factory=list)
    image_url: Optional[str] = None
    why_recommended: str
    booking_url: str
    is_selected: bool = False


class RestaurantItem(BaseModel):
    id: str
    name: str
    meal_type: str  # "Breakfast", "Lunch", "Dinner", "Snacks"
    cuisine: str
    price_tier: str  # "₹", "₹₹", "₹₹₹", "₹₹₹₹" or "$", "$$", "$$$"
    rating: float = 4.7
    distance_km: float = 1.2
    signature_dish: str
    reservation_tip: str
    address: str
    uber_deep_link: str
    is_saved: bool = False
    business_suitability: Optional[str] = None  # e.g. "Ideal for Client Dinners • Quiet Ambience"


class ReminderItem(BaseModel):
    id: str
    title: str
    type: str  # "departure", "checkin", "checkout", "packing", "reservation"
    scheduled_time: str
    is_enabled: bool = True
    notes: Optional[str] = None


class PreTripChecklistItem(BaseModel):
    id: str
    title: str
    category: str  # "Tickets & IDs", "Bookings", "Devices & Power", "Preparation"
    is_completed: bool = False
    is_critical: bool = True


class DestinationRecommendation(BaseModel):
    id: str
    name: str
    state_or_country: str
    vibe_tags: List[str] = Field(default_factory=list)
    estimated_budget_range: str  # e.g., "₹15,000–₹22,000" or "$1,200-$1,800"
    ideal_duration_days: int = 3
    why_it_matches: str
    top_highlight: str
    image_url: Optional[str] = None


class TripPreparationProgress(BaseModel):
    destination_selected: bool = True
    transportation_selected: bool = True
    hotel_selected: bool = True
    itinerary_generated: bool = True
    restaurants_reviewed: bool = False
    activities_reviewed: bool = False
    packing_started: bool = False
    checklist_completed: bool = False
    progress_percentage: int = 50


class CanonicalTrip(BaseModel):
    """The canonical single source of truth for an entire travel journey."""
    trip_id: str
    title: str
    status: str = "planning"  # "planning", "confirmed", "completed"
    origin: str
    destination: str
    dates: Dict[str, str] = Field(default_factory=lambda: {"start": "Upcoming", "end": "Flexible"})
    duration_days: int
    travelers: TravelerDetails
    currency: str = "INR"
    budget: Dict[str, Any] = Field(default_factory=dict)
    preferences: Dict[str, Any] = Field(default_factory=dict)
    trade_off_reasoning: str = ""
    
    # Corporate & Business Trip Attributes
    is_business: bool = False
    trip_purpose: str = "leisure"  # "business", "leisure", "family", "adventure", "culture"
    business_details: Optional[Dict[str, Any]] = None
    
    # 9 Multi-Section Modules
    transportation: List[TransportationOption] = Field(default_factory=list)
    selected_transport_id: Optional[str] = None
    hotels: List[HotelItem] = Field(default_factory=list)
    selected_hotel_id: Optional[str] = None
    activities: List[ActivityItem] = Field(default_factory=list)
    restaurants: List[RestaurantItem] = Field(default_factory=list)
    daily_itinerary: List[DayPlan] = Field(default_factory=list)
    packing_checklist: List[PackingChecklistItem] = Field(default_factory=list)
    pre_trip_checklist: List[PreTripChecklistItem] = Field(default_factory=list)
    reminders: List[ReminderItem] = Field(default_factory=list)
    progress: TripPreparationProgress = Field(default_factory=TripPreparationProgress)
    enrichment_insights: Dict[str, Any] = Field(default_factory=dict)
    created_at: str = ""

