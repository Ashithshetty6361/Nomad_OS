"""
API Request Schemas for NomadOS.
"""
from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any


class PlanRequest(BaseModel):
    """User input prompt and optional explicit constraints for travel itinerary generation."""
    query: str = Field(
        ..., 
        min_length=3,
        max_length=1500,
        description="Natural language trip description",
        example="Plan a 4-day foodie and cultural trip to Tokyo for 2 people in Autumn with a $2,500 budget."
    )
    destination: Optional[str] = Field(None, max_length=100, description="Explicit destination city if provided", example="Tokyo")
    duration_days: Optional[int] = Field(None, description="Number of days for trip", ge=1, le=14, example=4)
    budget_usd: Optional[float] = Field(None, description="Total budget amount", ge=100.0, example=2500.0)
    currency: Optional[str] = Field("INR", description="'INR' or 'USD'")
    travelers_count: Optional[int] = Field(1, description="Number of travelers", ge=1, le=15, example=2)
    adults: Optional[int] = Field(1, ge=1, le=15)
    children: Optional[int] = Field(0, ge=0, le=10)
    seniors: Optional[int] = Field(0, ge=0, le=10)
    interests: Optional[List[str]] = Field(default_factory=list, description="Explicit interests", example=["food", "temples", "shopping"])
    preferred_model_tier: Optional[str] = Field("cost_optimized", description="'cost_optimized' or 'max_reasoning'")
    
    budget_amount: Optional[float] = Field(None, description="Target budget amount in active currency")
    
    # Guided Multi-Modal Wizard Fields
    intent_type: Optional[str] = Field("direct", description="'direct', 'purpose', or 'mood'")
    origin_city: Optional[str] = Field("Current Location", description="Departure/Home city for door-to-door transit")
    companions: Optional[str] = Field("Solo", description="'Solo', 'Couple', 'Friends', or 'Family with Kids'")
    trip_mood: Optional[str] = Field(None, description="Primary mood/vibe, e.g., 'Concert & Nightlife', 'Family Retreat'")
    lodging_style: Optional[str] = Field(None, description="'Boutique', 'Luxury Resort', 'Budget Friendly', 'Central'")
    transport_preference: Optional[str] = Field("Flight", description="'Flight', 'Train', 'Bus', 'Cab', 'No preference'")
    user_role: Optional[str] = Field("customer", description="'customer' (clean view) or 'admin' (full AI dev telemetry)")
    
    # Dedicated Corporate & Business Trip Fields
    is_business: Optional[bool] = Field(False, description="Whether this trip is for corporate/business purpose")
    trip_purpose: Optional[str] = Field("leisure", description="'business', 'leisure', 'family', 'adventure', 'culture'")
    company_name: Optional[str] = Field(None, description="Company or organization for expense accounting")
    work_amenities: Optional[List[str]] = Field(default_factory=list, description="Requested business amenities like High-speed Wi-Fi, Meeting Rooms")


class ExtractIntentRequest(BaseModel):
    """Natural language query for automatic requirement extraction & missing fields identification."""
    query: str = Field(..., min_length=2, max_length=1500, description="Natural language trip idea or request")


class RefineTripRequest(BaseModel):
    """Conversational refinement of an active trip (e.g., 'Make Day 2 less tiring', 'Find cheaper hotel')."""
    trip_id: str
    prompt: str = Field(..., min_length=2, max_length=1000)
    current_trip: Optional[Dict[str, Any]] = Field(default_factory=dict)
