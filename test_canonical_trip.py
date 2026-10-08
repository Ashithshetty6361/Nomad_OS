"""
Test Suite for NomadOS Canonical Trip Companion Platform.
Verifies requirement extraction, destination recommendation, canonical multi-module generation,
and contextual AI refinement.
"""
import pytest
import asyncio
from app.services.trip_orchestration_service import trip_orchestration_service
from app.models.requests import PlanRequest


def test_requirement_extraction_full():
    """Verifies that an input with all parameters extracts cleanly without redundant missing fields."""
    query = "I want to go to Goa with 3 friends for 3 days around ₹20,000"
    res = trip_orchestration_service.extract_requirements(query)
    
    assert res.status == "SUCCESS"

    assert res.extracted["destination"] == "Goa"
    assert res.extracted["duration_days"] == 3
    assert res.extracted["budget"] == 20000.0
    assert res.extracted["travelers_count"] == 4
    assert res.extracted["companions"] == "Friends"
    assert res.extracted["currency"] == "INR"
    assert "destination" not in res.missing_fields
    assert "duration_days" not in res.missing_fields
    assert "budget" not in res.missing_fields


def test_requirement_extraction_mood_destination_matches():
    """Verifies that when a destination is omitted, tailored matches with rationale are provided."""
    query = "I want a chill vacation with my family"
    res = trip_orchestration_service.extract_requirements(query)
    
    assert "destination" in res.missing_fields
    assert res.extracted["companions"] == "Family with Kids"
    assert len(res.suggested_destinations) >= 3
    
    names = [d.name for d in res.suggested_destinations]
    assert "Coorg" in names or "Kyoto" in names or "Kerala" in names
    
    # Check that each recommendation contains rationale
    for d in res.suggested_destinations:
        assert len(d.why_it_matches) > 10
        assert d.estimated_budget_range != ""


def test_canonical_trip_generation_all_nine_modules():
    """Verifies that all 9 modules of the canonical trip are correctly populated."""
    req = PlanRequest(
        query="4-day trip to Manali for couple",
        destination="Manali",
        duration_days=4,
        currency="INR",
        companions="Couple",
        origin_city="Delhi"
    )
    trip = trip_orchestration_service.generate_canonical_trip(req)
    
    assert trip.trip_id.startswith("trip-")
    assert trip.destination == "Manali"
    assert trip.duration_days == 4
    assert trip.currency == "INR"
    
    # 1. Transportation
    assert len(trip.transportation) >= 3
    modes = [t.mode for t in trip.transportation]
    assert "Flight" in modes or "Bus" in modes or "Cab" in modes
    
    # 2. Hotels
    assert len(trip.hotels) >= 3
    assert all(h.booking_url.startswith("http") for h in trip.hotels)
    
    # 3. Daily Itinerary
    assert len(trip.daily_itinerary) == 4
    for day in trip.daily_itinerary:
        assert len(day.items) >= 2
        
    # 4. Activities & Restaurants
    assert len(trip.activities) >= 3
    assert len(trip.restaurants) >= 3
    
    # 5. Packing & Pre-Trip Checklist
    assert len(trip.packing_checklist) >= 8
    assert len(trip.pre_trip_checklist) >= 5
    
    # 6. Reminders
    assert len(trip.reminders) >= 3
    
    # 7. Progress
    assert trip.progress.progress_percentage >= 50


def test_contextual_ai_refinement():
    """Verifies that the contextual assistant refines active trip without resetting state."""
    req = PlanRequest(
        query="3-day Goa trip",
        destination="Goa",
        duration_days=3,
        currency="INR"
    )
    trip = trip_orchestration_service.generate_canonical_trip(req)
    initial_cost = trip.budget["estimated_total"]
    
    # Test pace adjustment
    res_pace = trip_orchestration_service.refine_trip(trip.trip_id, "Can you make Day 2 less tiring?", trip.dict())
    assert "relaxed" in res_pace.message.lower() or "slow" in res_pace.message.lower()
    assert len(res_pace.change_summary) > 0
    
    # Test hotel price reduction
    res_hotel = trip_orchestration_service.refine_trip(trip.trip_id, "Find a cheaper hotel", trip.dict())
    assert len(res_hotel.change_summary) > 0
    assert res_hotel.updated_trip["budget"]["estimated_total"] <= initial_cost


if __name__ == "__main__":
    print("Running NomadOS Canonical Trip Test Suite...")
    test_requirement_extraction_full()
    print("[OK] Requirement extraction full passed.")
    test_requirement_extraction_mood_destination_matches()
    print("[OK] Destination recommendations passed.")
    test_canonical_trip_generation_all_nine_modules()
    print("[OK] 9-Module canonical trip generation passed.")
    test_contextual_ai_refinement()
    print("[OK] Contextual AI refinement passed.")
    print("ALL TESTS PASSED SUCCESSFULLY!")
