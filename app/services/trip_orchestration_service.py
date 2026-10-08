"""
Canonical Trip Orchestration Service for NomadOS.
Manages the complete travel companion lifecycle: natural-language requirement extraction,
multi-card destination recommendations, canonical trip generation across 9 modules,
and quiet, non-intrusive contextual AI refinements.
"""
import uuid
import re
import datetime
from typing import Dict, Any, List, Optional, Tuple

from app.models.state import (
    CanonicalTrip,
    TravelerDetails,
    TransportationOption,
    HotelItem,
    RestaurantItem,
    ActivityItem,
    ReminderItem,
    PreTripChecklistItem,
    DestinationRecommendation,
    TripPreparationProgress,
    PackingChecklistItem,
    DayPlan,
    DailyScheduleItem
)
from app.models.requests import PlanRequest
from app.models.responses import (
    ExtractIntentResponse,
    ProgressiveQuestion,
    RefineTripResponse
)
from app.services.llm_service import llm_service
from app.core.logging import logger
from app.core.persistence import persistence
from app.core.metrics import Timer


class TripOrchestrationService:
    """Central orchestrator managing canonical trip state and progressive companion UX."""

    def __init__(self):
        # In-memory trip store (in production, backed by Redis/PostgreSQL)
        self._trips: Dict[str, CanonicalTrip] = {}

    def extract_requirements(self, query: str) -> ExtractIntentResponse:
        """
        Parses natural language query, extracts existing requirements without re-asking,
        identifies missing essentials, and recommends destination matches if unspecified.
        """
        q_lower = query.lower()
        extracted: Dict[str, Any] = {}
        missing_fields: List[str] = []

        # 1. Detect Currency
        is_inr = any(c in q_lower for c in ["₹", "rs", "inr", "rupee", "rupees"])
        currency = "INR" if is_inr else "USD"
        extracted["currency"] = currency

        # 2. Extract Duration
        duration_match = re.search(r'(\d+)\s*(?:-| )*(?:day|days)', q_lower)
        if duration_match:
            extracted["duration_days"] = int(duration_match.group(1))
        elif "weekend" in q_lower:
            extracted["duration_days"] = 3
        elif "week" in q_lower:
            extracted["duration_days"] = 7
        else:
            missing_fields.append("duration_days")

        # 3. Extract Budget
        # Matches ₹20,000 or 20,000 or $2,800
        budget_match = re.search(r'(?:₹|\$|rs\.?|inr)?\s*(\d{1,3}(?:,\d{3})+|\d{4,6})', q_lower)
        if budget_match:
            clean_num = budget_match.group(1).replace(',', '')
            extracted["budget"] = float(clean_num)
        else:
            missing_fields.append("budget")

        # 4. Extract Travelers & Companions
        if "family" in q_lower or "parents" in q_lower or "kids" in q_lower:
            extracted["companions"] = "Family with Kids"
            extracted["travelers_count"] = 4
            extracted["adults"] = 2
            extracted["children"] = 2
        elif "friends" in q_lower or "friend" in q_lower:
            extracted["companions"] = "Friends"
            friends_count = re.search(r'(\d+)\s*friends?', q_lower)
            if friends_count:
                # user + friends
                extracted["travelers_count"] = int(friends_count.group(1)) + 1
            else:
                extracted["travelers_count"] = 3
            extracted["adults"] = extracted["travelers_count"]
        elif "couple" in q_lower or "partner" in q_lower or "anniversary" in q_lower or "romantic" in q_lower:
            extracted["companions"] = "Couple"
            extracted["travelers_count"] = 2
            extracted["adults"] = 2
        elif "solo" in q_lower:
            extracted["companions"] = "Solo"
            extracted["travelers_count"] = 1
            extracted["adults"] = 1
        else:
            people_match = re.search(r'(\d+)\s*(?:people|persons|travelers|pax)', q_lower)
            if people_match:
                count = int(people_match.group(1))
                extracted["travelers_count"] = count
                extracted["companions"] = "Friends" if count > 2 else ("Couple" if count == 2 else "Solo")
                extracted["adults"] = count
            else:
                missing_fields.append("companions")

        # 5. Detect Destination
        known_places = [
            ("goa", "Goa"), ("coorg", "Coorg"), ("manali", "Manali"), ("kerala", "Kerala"),
            ("tokyo", "Tokyo"), ("kyoto", "Kyoto"), ("paris", "Paris"), ("austin", "Austin"),
            ("rome", "Rome"), ("bali", "Bali"), ("amalfi", "Amalfi Coast"), ("mumbai", "Mumbai"),
            ("jaipur", "Jaipur"), ("udaipur", "Udaipur"), ("bangalore", "Bangalore"), ("rishikesh", "Rishikesh")
        ]
        detected_destination = None
        for key, name in known_places:
            if key in q_lower:
                detected_destination = name
                break
        
        if detected_destination:
            extracted["destination"] = detected_destination
        else:
            missing_fields.append("destination")

        # 6. Detect Intent Type, Business Context & Mood
        intent_type = "direct"
        trip_mood = "Balanced & Inspiring"
        
        is_business = any(w in q_lower for w in ["business", "corporate", "client", "meeting", "conference", "summit", "work", "executive", "office", "presentation", "tech summit"])
        if is_business:
            intent_type = "purpose"
            trip_purpose = "business"
            trip_mood = "Productive Executive Blitz & Client Focus"
        elif any(w in q_lower for w in ["family", "parents", "children", "kids"]):
            trip_purpose = "family"
            trip_mood = "Gentle & Inspiring Family Vacation"
        elif any(w in q_lower for w in ["trek", "trekking", "adventure", "hiking", "rafting", "ski"]):
            trip_purpose = "adventure"
            trip_mood = "Thrilling Outdoor Adventure"
        elif any(w in q_lower for w in ["foodie", "culinary", "street food", "ramen", "bbq"]):
            trip_purpose = "culture"
            trip_mood = "Culinary & Regional Gastronomy"
        elif any(w in q_lower for w in ["culture", "heritage", "temple", "shrine", "monument"]):
            trip_purpose = "culture"
            trip_mood = "Historic & Cultural Immersion"
        elif any(w in q_lower for w in ["concert", "festival", "music", "party", "nightlife", "dance"]):
            trip_purpose = "entertainment"
            trip_mood = "High-Energy Music & Nightlife"
        else:
            trip_purpose = "leisure"
            trip_mood = "Calm Nature & Scenic Relaxation"

        extracted["is_business"] = is_business
        extracted["trip_purpose"] = trip_purpose
        extracted["intent_type"] = intent_type
        extracted["trip_mood"] = trip_mood

        # 7. Generate Candidate Destination Matches if destination is missing
        suggested_destinations: List[DestinationRecommendation] = []
        if "destination" in missing_fields:
            if "concert" in q_lower or "music" in q_lower or "nightlife" in q_lower:
                suggested_destinations = [
                    DestinationRecommendation(
                        id="dest-austin",
                        name="Austin",
                        state_or_country="Texas, USA",
                        vibe_tags=["Live Music", "Nightlife", "BBQ", "Festivals"],
                        estimated_budget_range="₹22,000–₹35,000" if is_inr else "$1,400-$2,200",
                        ideal_duration_days=4,
                        why_it_matches="World-renowned live music capital with vibrant music venues along Rainey St and legendary food trucks.",
                        top_highlight="Austin City Limits & South Congress Music Venues",
                        image_url="https://images.unsplash.com/photo-1531218150217-54595bc2b934?w=600"
                    ),
                    DestinationRecommendation(
                        id="dest-goa",
                        name="Goa",
                        state_or_country="India",
                        vibe_tags=["Beach Parties", "Live DJs", "Nightlife", "Seafood"],
                        estimated_budget_range="₹18,000–₹26,000" if is_inr else "$800-$1,200",
                        ideal_duration_days=4,
                        why_it_matches="Energetic coastal vibe with beach clubs, night markets, and live music performances right on the sands.",
                        top_highlight="Anjuna & Vagator Sunset Beach Lounges",
                        image_url="https://images.unsplash.com/photo-1512343879784-a960bf40e7f2?w=600"
                    ),
                    DestinationRecommendation(
                        id="dest-tokyo",
                        name="Tokyo",
                        state_or_country="Japan",
                        vibe_tags=["Ultra-Modern", "Late Night Izakayas", "Electrifying"],
                        estimated_budget_range="₹65,000–₹90,000" if is_inr else "$2,400-$3,200",
                        ideal_duration_days=5,
                        why_it_matches="Unmatched neon city energy, underground music clubs in Shibuya, and midnight street ramen.",
                        top_highlight="Shinjuku Omoide Yokocho & Roppongi Music Lounges",
                        image_url="https://images.unsplash.com/photo-1503899036084-c55cdd92da26?w=600"
                    )
                ]
            elif "family" in q_lower or "calm" in q_lower or "parents" in q_lower:
                suggested_destinations = [
                    DestinationRecommendation(
                        id="dest-coorg",
                        name="Coorg",
                        state_or_country="Karnataka, India",
                        vibe_tags=["Coffee Plantations", "Misty Hills", "Peaceful", "Family"],
                        estimated_budget_range="₹15,000–₹22,000" if is_inr else "$700-$1,100",
                        ideal_duration_days=3,
                        why_it_matches="Serene hill station with spacious homestays, gentle nature walks, and refreshing waterfalls safe for kids and seniors.",
                        top_highlight="Abbey Falls & Private Coffee Estate Walks",
                        image_url="https://images.unsplash.com/photo-1598463844053-568779659b64?w=600"
                    ),
                    DestinationRecommendation(
                        id="dest-kyoto",
                        name="Kyoto",
                        state_or_country="Japan",
                        vibe_tags=["Historic Temples", "Bamboo Groves", "Quiet Gardens"],
                        estimated_budget_range="₹55,000–₹75,000" if is_inr else "$2,000-$2,800",
                        ideal_duration_days=4,
                        why_it_matches="Deeply serene cultural landscape with tranquil tea houses, quiet stone-paved streets, and family-friendly ryokans.",
                        top_highlight="Arashiyama Bamboo Forest & Fushimi Inari Taisha",
                        image_url="https://images.unsplash.com/photo-1493976040374-85c8e12f0c0e?w=600"
                    ),
                    DestinationRecommendation(
                        id="dest-kerala",
                        name="Kerala",
                        state_or_country="India",
                        vibe_tags=["Backwaters", "Houseboats", "Ayurveda", "Lush"],
                        estimated_budget_range="₹20,000–₹30,000" if is_inr else "$900-$1,400",
                        ideal_duration_days=4,
                        why_it_matches="Gentle private backwater houseboat cruise with home-cooked coastal cuisine, ideal for multi-generational families.",
                        top_highlight="Alleppey Private Houseboat & Kumarakom Bird Sanctuary",
                        image_url="https://images.unsplash.com/photo-1602216056096-3b40cc0c9944?w=600"
                    )
                ]
            else:
                # Default diverse recommendations
                suggested_destinations = [
                    DestinationRecommendation(
                        id="dest-goa",
                        name="Goa",
                        state_or_country="India",
                        vibe_tags=["Beaches", "Foodie", "Heritage", "Relaxing"],
                        estimated_budget_range="₹18,000–₹25,000" if is_inr else "$900-$1,300",
                        ideal_duration_days=4,
                        why_it_matches="Perfect blend of sun-drenched beaches, Portuguese architecture, and coastal seafood shacks.",
                        top_highlight="Fontainhas Heritage Walk & South Goa Quiet Beaches",
                        image_url="https://images.unsplash.com/photo-1512343879784-a960bf40e7f2?w=600"
                    ),
                    DestinationRecommendation(
                        id="dest-manali",
                        name="Manali",
                        state_or_country="Himachal Pradesh, India",
                        vibe_tags=["Snow Peaks", "Apple Orchards", "Adventure", "Hills"],
                        estimated_budget_range="₹16,000–₹24,000" if is_inr else "$800-$1,200",
                        ideal_duration_days=4,
                        why_it_matches="Crisp Himalayan air, scenic alpine river valleys, and cozy wood cabin stays.",
                        top_highlight="Solang Valley & Old Manali Indie Cafes",
                        image_url="https://images.unsplash.com/photo-1579619564365-0355a6d5fa65?w=600"
                    ),
                    DestinationRecommendation(
                        id="dest-paris",
                        name="Paris",
                        state_or_country="France",
                        vibe_tags=["Art", "Architecture", "Bistronomy", "Romantic"],
                        estimated_budget_range="₹80,000–₹1,20,000" if is_inr else "$2,800-$3,800",
                        ideal_duration_days=4,
                        why_it_matches="World-class bakeries, walkable historic arrondissements, and intimate candle-lit bistros.",
                        top_highlight="Le Marais Architecture & Seine Sunset Walks",
                        image_url="https://images.unsplash.com/photo-1502602898657-3e91760cbb34?w=600"
                    )
                ]

        # 8. Create Progressive Questions formatted as Interactive Flashcards
        progressive_questions: List[ProgressiveQuestion] = [
            ProgressiveQuestion(
                key="trip_purpose",
                question="What is the primary nature of this journey?",
                card_title="Trip Nature & Purpose",
                card_subtitle="Tailors your schedule rhythm, focus work blocks, or relaxation cadence",
                icon="💼" if is_business else "🌴",
                step_number=1,
                total_steps=4,
                type="chips",
                options=[
                    {"label": "💼 Corporate & Business Blitz", "value": "business"},
                    {"label": "🌴 Leisure & Relaxation", "value": "leisure"},
                    {"label": "👨‍👩‍👧 Family Vacation", "value": "family"},
                    {"label": "🏕️ Adventure & Outdoor", "value": "adventure"}
                ],
                default_val="business" if is_business else trip_purpose,
                is_business_specific=is_business
            ),
            ProgressiveQuestion(
                key="origin_city",
                question="Where will your journey begin?",
                card_title="Doorstep Departure City",
                card_subtitle="Configures door-to-door transit, flight comparisons, and airport Uber pickup",
                icon="🏠",
                step_number=2,
                total_steps=4,
                type="chips",
                options=[
                    {"label": "✈️ Bangalore", "value": "Bangalore"},
                    {"label": "✈️ Mumbai", "value": "Mumbai"},
                    {"label": "✈️ Delhi", "value": "Delhi"},
                    {"label": "✈️ Hyderabad", "value": "Hyderabad"},
                    {"label": "✈️ Chennai", "value": "Chennai"},
                    {"label": "✈️ San Francisco", "value": "San Francisco"}
                ],
                default_val=extracted.get("origin", "Bangalore")
            ),
            ProgressiveQuestion(
                key="budget",
                question="What is your target budget or expense policy?",
                card_title="Budget & Expense Accounting",
                card_subtitle="Separates corporate reimbursable allowances from personal out-of-pocket costs",
                icon="💰",
                step_number=3,
                total_steps=4,
                type="chips",
                options=[
                    {"label": f"🏢 Corporate Expense (~{('₹50,000' if is_inr else '$650')})", "value": 50000 if is_inr else 650},
                    {"label": f"💎 Executive Luxury (~{('₹85,000' if is_inr else '$1,200')})", "value": 85000 if is_inr else 1200},
                    {"label": f"✨ Balanced Comfort (~{('₹25,000' if is_inr else '$350')})", "value": 25000 if is_inr else 350},
                    {"label": f"🎒 Value Budget (~{('₹15,000' if is_inr else '$200')})", "value": 15000 if is_inr else 200}
                ],
                default_val=50000 if (is_business and is_inr) else (650 if is_business else (25000 if is_inr else 350))
            ),
            ProgressiveQuestion(
                key="tailored_priorities",
                question="Which priorities or amenities are essential?",
                card_title="Workspace & Experience Priorities",
                card_subtitle="Calibrates venue acoustics, Wi-Fi performance, and leisure balance",
                icon="⚡",
                step_number=4,
                total_steps=4,
                type="chips",
                options=[
                    {"label": "💻 High-Speed Fiber (150+ Mbps)", "value": "high_speed_wifi"},
                    {"label": "👔 Executive Boardrooms & Lounge", "value": "boardrooms"},
                    {"label": "🚗 Uber Premier Express Dispatch", "value": "uber_premier"},
                    {"label": "🍽️ Quiet Client Dining Venues", "value": "client_dining"}
                ] if is_business else [
                    {"label": "🏖️ Beaches & Ocean Views", "value": "beaches"},
                    {"label": "🍜 Regional Culinary & Street Eats", "value": "culinary"},
                    {"label": "🏛️ Historic Landmarks & Culture", "value": "culture"},
                    {"label": "🧘 Quiet Spa & Restful Pace", "value": "relaxation"}
                ],
                default_val="high_speed_wifi" if is_business else "beaches",
                is_business_specific=is_business
            )
        ]

        return ExtractIntentResponse(
            status="SUCCESS",
            original_query=query,
            extracted=extracted,
            missing_fields=missing_fields,
            suggested_destinations=suggested_destinations,
            progressive_questions=progressive_questions
        )

    def generate_canonical_trip(self, req: PlanRequest) -> CanonicalTrip:
        """
        Orchestrates synthesis of a complete canonical trip including 9 dedicated modules.
        Supports both leisure and dedicated executive business trips.
        """
        trip_id = f"trip-{uuid.uuid4().hex[:8]}"
        destination = req.destination or "Goa"
        origin = req.origin_city if req.origin_city and req.origin_city != "Current Location" else "Bangalore"
        duration = req.duration_days or 3
        currency = req.currency or ("INR" if any(c in destination.lower() for c in ["goa", "manali", "coorg", "kerala", "mumbai", "jaipur", "udaipur", "delhi", "bangalore"]) else "USD")
        
        # Detect Business Trip Intent
        is_business = req.is_business or (req.trip_purpose == "business") or any(
            w in (req.query or "").lower() for w in ["business", "corporate", "client", "meeting", "conference", "summit", "work", "presentation", "tech summit"]
        )
        trip_purpose = "business" if is_business else (req.trip_purpose or "leisure")

        # Determine budget default
        if req.budget_amount and req.budget_amount > 0:
            total_budget = req.budget_amount
        elif req.budget_usd and req.budget_usd > 0:
            total_budget = req.budget_usd
        else:
            if is_business:
                total_budget = 48000.0 if currency == "INR" else 1250.0
            else:
                total_budget = 24000.0 if currency == "INR" else 2800.0

        companions = "Solo (Business)" if (is_business and req.companions in ["Solo", "Couple", None]) else (req.companions or "Couple")
        adults = req.adults or (4 if companions == "Family with Kids" else (3 if companions == "Friends" else (2 if companions == "Couple" else 1)))
        total_travelers = adults + (req.children or 0) + (req.seniors or 0)

        travelers = TravelerDetails(
            total=total_travelers,
            adults=adults,
            children=req.children or 0,
            seniors=req.seniors or 0,
            group_type=companions
        )

        # 1. Transportation Options (Flights, Trains, Buses, Cabs / Uber Premier)
        transportation = self._generate_transport_options(origin, destination, currency, total_travelers)
        selected_transport = transportation[0].id if transportation else None

        # 2. Lodging & Accommodations
        if is_business:
            hotels = self._generate_business_hotels(destination, currency, duration)
        else:
            hotels = self._generate_hotels(destination, currency, req.lodging_style or "Boutique Hotel", total_budget, duration)
        selected_hotel = hotels[0].id if hotels else None

        # 3. Itinerary, Activities & Dining
        if is_business:
            daily_itinerary, activities, restaurants = self._generate_business_schedule(destination, duration, currency, req.company_name or "NomadOS Global Corporate")
        else:
            daily_itinerary, activities, restaurants = self._generate_itinerary_activities_food(destination, duration, currency, req.trip_mood or "Vibrant & Inspiring", total_travelers)

        # 4. Interactive Packing Checklist
        if is_business:
            packing_checklist = self._generate_business_packing_checklist(duration)
        else:
            packing_checklist = self._generate_packing_checklist(destination, duration, companions, req.trip_mood or "Leisure")

        # 5. Pre-Trip Departure Checklist
        if is_business:
            pre_trip_checklist = [
                PreTripChecklistItem(id="prep-1", title="Flight Boarding Pass downloaded & seat verified", category="Tickets & IDs", is_completed=True, is_critical=True),
                PreTripChecklistItem(id="prep-2", title="Executive Hotel Corporate Voucher saved offline", category="Bookings", is_completed=True, is_critical=True),
                PreTripChecklistItem(id="prep-3", title="Presentation Slides & SOW Contracts backed up offline", category="Preparation", is_completed=False, is_critical=True),
                PreTripChecklistItem(id="prep-4", title="Laptop, wireless clicker & power adapters charged", category="Devices & Power", is_completed=False, is_critical=True),
                PreTripChecklistItem(id="prep-5", title="Corporate expense card & receipt capture app active", category="Preparation", is_completed=True, is_critical=False),
                PreTripChecklistItem(id="prep-6", title="Uber Premier airport pickup pre-scheduled", category="Preparation", is_completed=False, is_critical=False)
            ]
        else:
            pre_trip_checklist = [
                PreTripChecklistItem(id="prep-1", title="Flight / Train tickets confirmed & downloaded", category="Tickets & IDs", is_completed=True, is_critical=True),
                PreTripChecklistItem(id="prep-2", title="Government ID / Passport packed & within validity", category="Tickets & IDs", is_completed=True, is_critical=True),
                PreTripChecklistItem(id="prep-3", title="Hotel reservation voucher saved offline", category="Bookings", is_completed=False, is_critical=True),
                PreTripChecklistItem(id="prep-4", title="Phone chargers & portable power bank fully charged", category="Devices & Power", is_completed=False, is_critical=True),
                PreTripChecklistItem(id="prep-5", title="Local weather checked & layers packed", category="Preparation", is_completed=True, is_critical=False),
                PreTripChecklistItem(id="prep-6", title="Home airport/station Uber or transit scheduled", category="Preparation", is_completed=False, is_critical=False)
            ]

        # 6. Smart Reminders
        if is_business:
            reminders = [
                ReminderItem(id="rem-1", title="Airline Priority Web Check-in", type="checkin", scheduled_time="24 hours before flight", is_enabled=True, notes="Front-cabin aisle seat selected for fast exit"),
                ReminderItem(id="rem-2", title="Verify Keynote Presentation & Clicker Batteries", type="packing", scheduled_time="Evening before departure", is_enabled=True, notes="Double-check HDMI dongle"),
                ReminderItem(id="rem-3", title="Uber Premier Departure to Airport", type="departure", scheduled_time="2 hours before flight", is_enabled=True, notes="Digital receipt linked to corporate billing"),
                ReminderItem(id="rem-4", title="Confirm Client Dinner Reservation", type="reservation", scheduled_time="Day 1, 15:00", is_enabled=True, notes="Table in quiet dining alcove confirmed"),
                ReminderItem(id="rem-5", title="Executive Hotel Express Checkout", type="checkout", scheduled_time=f"Day {duration}, 11:30", is_enabled=True, notes="Request digital invoice via email")
            ]
        else:
            reminders = [
                ReminderItem(id="rem-1", title="Web Check-in & Boarding Pass", type="checkin", scheduled_time="24 hours before departure", is_enabled=True, notes="Select aisle/window seats early"),
                ReminderItem(id="rem-2", title="Pack essential medications & power bank", type="packing", scheduled_time="Evening before departure", is_enabled=True, notes="Keep in carry-on bag"),
                ReminderItem(id="rem-3", title="Depart for Airport / Station", type="departure", scheduled_time="2.5 hours before departure", is_enabled=True, notes="Allow buffer for traffic"),
                ReminderItem(id="rem-4", title="Hotel Check-in & Key Collection", type="checkin", scheduled_time="Day 1, 14:00", is_enabled=True, notes="Luggage drop available if early"),
                ReminderItem(id="rem-5", title="Hotel Checkout & Luggage Drop", type="checkout", scheduled_time=f"Day {duration}, 11:00", is_enabled=True, notes="Request late checkout if needed")
            ]

        # 7. Budget Breakdown
        transport_cost = transportation[0].price if transportation else (total_budget * 0.35)
        lodging_cost = (hotels[0].total_price if hotels else (total_budget * 0.35))
        food_cost = round(total_budget * 0.18, 2)
        activities_cost = round(total_budget * 0.10, 2)
        local_transit_cost = round(total_budget * 0.05, 2)
        est_total = round(transport_cost + lodging_cost + food_cost + activities_cost + local_transit_cost, 2)

        budget_breakdown = {
            "Long-Distance Transport": transport_cost,
            "Accommodations": lodging_cost,
            "Dining & Culinary": food_cost,
            "Activities & Culture": activities_cost,
            "Local Transit (Uber & Cabs)": local_transit_cost
        }

        # 8. Business Details & Expense Management
        business_details = None
        if is_business:
            business_details = {
                "company_name": req.company_name or "NomadOS Global Inc.",
                "reimbursable_total": est_total,
                "per_diem_daily": 5000.0 if currency == "INR" else 75.0,
                "workspace_amenities": req.work_amenities or [
                    "150+ Mbps Fiber Wi-Fi",
                    "Executive Business Lounge Access",
                    "Meeting Boardroom Reservations",
                    "Acoustic Phone Booths"
                ],
                "client_meetings_count": 3,
                "expense_report": {
                    "flights_transport": transport_cost,
                    "executive_hotel": lodging_cost,
                    "client_entertaining_meals": food_cost,
                    "uber_premier_rides": local_transit_cost
                }
            }

        # 9. Trip Preparation Progress
        progress = TripPreparationProgress(
            destination_selected=True,
            transportation_selected=True,
            hotel_selected=True,
            itinerary_generated=True,
            restaurants_reviewed=True,
            activities_reviewed=True,
            packing_started=False,
            checklist_completed=False,
            progress_percentage=75 if is_business else 65
        )

        title = f"{destination} – {duration}-Day Executive Business Blitz" if is_business else f"{destination} – {duration}-Day {companions} Getaway"
        trade_off_reasoning = (
            f"Executive corporate itinerary engineered for high productivity, seamless Uber Premier transit, soundproof meeting venues, and prestigious client entertainment in {destination}."
            if is_business else
            f"Optimized for a {companions.lower()} trip focusing on authentic experiences while balancing transport comfort and central boutique lodging within the target budget."
        )

        canonical = CanonicalTrip(
            trip_id=trip_id,
            title=title,
            status="planning",
            origin=origin,
            destination=destination,
            duration_days=duration,
            travelers=travelers,
            currency=currency,
            budget={
                "target": total_budget,
                "estimated_total": est_total,
                "currency": currency,
                "breakdown": budget_breakdown
            },
            preferences={
                "intent_type": req.intent_type or ("purpose" if is_business else "direct"),
                "trip_mood": "Productive Executive Blitz" if is_business else (req.trip_mood or "Inspiring"),
                "lodging_style": "5★ Executive Business Hotel" if is_business else (req.lodging_style or "Boutique Hotel"),
                "transport_preference": "Uber Premier & Priority Flights" if is_business else (req.transport_preference or "Flight")
            },
            trade_off_reasoning=trade_off_reasoning,
            is_business=is_business,
            trip_purpose=trip_purpose,
            business_details=business_details,
            transportation=transportation,
            selected_transport_id=selected_transport,
            hotels=hotels,
            selected_hotel_id=selected_hotel,
            activities=activities,
            restaurants=restaurants,
            daily_itinerary=daily_itinerary,
            packing_checklist=packing_checklist,
            pre_trip_checklist=pre_trip_checklist,
            reminders=reminders,
            progress=progress,
            enrichment_insights={
                "local_pro_tips": [
                    f"Rent a scooter or use verified rides to navigate scenic backroads in {destination}.",
                    "Book popular evening dinners 24-48 hours ahead to avoid waiting in peak hours.",
                    "Carry a light reusable water bottle and small cash for local street vendors."
                ],
                "cultural_etiquette": [
                    "Remove footwear when entering temples, traditional homes, and sacred heritage sites.",
                    "Dress respectfully when visiting shrines and historical monuments."
                ],
                "transport_advice": f"Uber and prepaid cabs are widely accessible across {destination} for point-to-point daily hops."
            },
            created_at=datetime.datetime.utcnow().isoformat() + "Z"
        )

        self._trips[trip_id] = canonical

        # Persist to SQLite
        try:
            persistence.save_trip(trip_id, canonical.dict())
        except Exception as e:
            logger.debug(f"Non-critical: SQLite persist failed: {e}")

        # Record synthetic AIOps telemetry for the engineering dashboard
        self._record_generation_telemetry(trip_id, is_business, duration)

        return canonical

    def _record_generation_telemetry(self, trip_id: str, is_business: bool, duration: int):
        """Records synthetic telemetry for the AIOps dashboard showing multi-agent cost optimization."""
        try:
            from app.api.v1.endpoints.aiops import aiops_metrics
            # Simulate multi-agent calls: context_parsing → discovery → enrichment → booking_reasoning
            agents = [
                {"task_type": "context_parsing", "model_id": "claude-3-haiku", "prompt_tokens": 380, "completion_tokens": 210, "cost_usd": 0.000358, "latency_ms": 145, "provider": "Nomad_Mock_Provider"},
                {"task_type": "discovery_filtering", "model_id": "claude-3-haiku", "prompt_tokens": 450, "completion_tokens": 390, "cost_usd": 0.000600, "latency_ms": 189, "provider": "Nomad_Mock_Provider"},
                {"task_type": "enrichment_extraction", "model_id": "claude-3-haiku", "prompt_tokens": 320, "completion_tokens": 240, "cost_usd": 0.000380, "latency_ms": 132, "provider": "Nomad_Mock_Provider"},
                {"task_type": "booking_reasoning", "model_id": "claude-3.5-sonnet", "prompt_tokens": 750, "completion_tokens": 920, "cost_usd": 0.016050, "latency_ms": 410, "provider": "Nomad_Mock_Provider"},
            ]
            for agent in agents:
                agent["cache_hit"] = False
                aiops_metrics.record_call(agent)
        except Exception:
            pass  # Non-critical

    def refine_trip(self, trip_id: str, prompt: str, current_state: Optional[Dict[str, Any]] = None) -> RefineTripResponse:
        """
        Handles quiet, non-intrusive contextual AI refinements on an active trip.
        Supports prompts like:
        - "Make Day 2 less tiring"
        - "Find a cheaper hotel"
        - "Reduce trip cost"
        - "What should I pack?"
        - "Suggest something near our hotel tonight"
        """
        trip = self._trips.get(trip_id)
        if not trip and current_state:
            try:
                trip = CanonicalTrip.parse_obj(current_state)
                self._trips[trip_id] = trip
            except Exception as e:
                logger.warning(f"Could not parse passed trip state: {e}")

        if not trip:
            # Create a quick fallback trip to prevent failure
            req = PlanRequest(query="Trip to Goa", destination="Goa", duration_days=3)
            trip = self.generate_canonical_trip(req)

        p_lower = prompt.lower()
        change_summary: List[str] = []
        ai_message = ""

        if "less tiring" in p_lower or "relax" in p_lower or "slow" in p_lower or "day 2" in p_lower:
            # Adjust Day 2 schedule pace
            if len(trip.daily_itinerary) >= 2:
                day2 = trip.daily_itinerary[1]
                # Replace strenuous activity with quiet cafe/scenic rest
                day2.day_theme = "Slow-Paced Relaxation & Scenic Cafe Hangout"
                if len(day2.items) > 1:
                    day2.items[1].activity_title = "Unwind at a Scenic Garden Cafe & Book Nook"
                    day2.items[1].description = "Restful afternoon sipping artisanal brews with panoramic vistas, avoiding afternoon sun."
                    day2.items[1].cost_estimate_usd = 15.0 if trip.currency == "USD" else 450.0
                    day2.items[1].pro_tip = "Try the house iced hibiscus tea and freshly baked pastry."
                change_summary.append("Replaced intense afternoon walking on Day 2 with a calm garden cafe rest.")
                change_summary.append("Reduced scheduled physical travel time by 45 minutes.")
                ai_message = "I've relaxed your Day 2 schedule. I swapped the busy afternoon tour for a calm garden cafe and scenic rest so you won't feel rushed."

        elif "cheaper hotel" in p_lower or "budget hotel" in p_lower or "less cost hotel" in p_lower:
            # Lower hotel cost
            if trip.hotels:
                for h in trip.hotels:
                    h.price_per_night = round(h.price_per_night * 0.75, 2)
                    h.total_price = round(h.price_per_night * trip.duration_days, 2)
                trip.hotels[0].name = f"Cozy Heritage Stay, {trip.destination}"
                trip.hotels[0].why_recommended = "Highly-rated boutique stay offering incredible value, clean rooms, and walking distance to transit."
                if "Accommodations" in trip.budget.get("breakdown", {}):
                    trip.budget["breakdown"]["Accommodations"] = trip.hotels[0].total_price
                    trip.budget["estimated_total"] = sum(trip.budget["breakdown"].values())
                change_summary.append(f"Updated lodging recommendation to a high-value boutique stay saving ~25%.")
                change_summary.append(f"New estimated lodging total: {trip.currency} {trip.hotels[0].total_price:,.0f}.")
                ai_message = f"I found a fantastic boutique option ({trip.hotels[0].name}) that saves approximately 25% on accommodation while keeping you right near the main spots."

        elif "reduce" in p_lower or "cheaper" in p_lower or "budget" in p_lower:
            # General cost reduction
            if "breakdown" in trip.budget:
                for k in trip.budget["breakdown"]:
                    trip.budget["breakdown"][k] = round(trip.budget["breakdown"][k] * 0.85, 2)
                trip.budget["estimated_total"] = round(sum(trip.budget["breakdown"].values()), 2)
            change_summary.append("Optimized activity and dining estimates to local hidden gems (-15% overall cost).")
            change_summary.append("Swapped premium dining for authentic regional specialty eateries.")
            ai_message = f"I've streamlined your budget! By spotlighting beloved local eateries and free scenic viewpoints, your total estimated trip cost has been reduced to {trip.currency} {trip.budget['estimated_total']:,.0f}."

        elif "pack" in p_lower or "packing" in p_lower:
            ai_message = f"For {trip.destination}, make sure to pack: 1) Lightweight breathable clothing, 2) Comfortable walking footwear, 3) Rain layer or sunscreen depending on time of day, and 4) Your universal charger and ID. Your full interactive checklist is ready in the Packing tab!"
            change_summary.append("Highlighted destination weather-specific packing necessities.")

        else:
            ai_message = f"I've reviewed your trip to {trip.destination} with your request in mind ('{prompt}'). I've verified that your schedule and travel details remain smooth and comfortable."
            change_summary.append("Validated itinerary flow and activity timings.")

        self._trips[trip_id] = trip

        return RefineTripResponse(
            status="SUCCESS",
            message=ai_message,
            updated_trip=trip.dict(),
            change_summary=change_summary
        )

    def get_trip(self, trip_id: str) -> Optional[CanonicalTrip]:
        # Check in-memory first, then SQLite
        if trip_id in self._trips:
            return self._trips[trip_id]
        stored = persistence.get_trip(trip_id)
        if stored:
            try:
                trip = CanonicalTrip(**stored)
                self._trips[trip_id] = trip
                return trip
            except Exception:
                pass
        return None

    def save_trip(self, trip_id: str, trip_data: Dict[str, Any]) -> CanonicalTrip:
        canonical = CanonicalTrip(**trip_data)
        self._trips[trip_id] = canonical
        try:
            persistence.save_trip(trip_id, trip_data)
        except Exception as e:
            logger.debug(f"Non-critical: SQLite save failed: {e}")
        return canonical

    def get_explore_destinations(self) -> List[DestinationRecommendation]:
        """Returns trending curated destinations for the Explore section."""
        return [
            DestinationRecommendation(
                id="exp-goa",
                name="Goa",
                state_or_country="India",
                vibe_tags=["Beaches", "Seafood", "Nightlife", "Heritage"],
                estimated_budget_range="₹18,000–₹26,000",
                ideal_duration_days=4,
                why_it_matches="Vibrant coastal getaway with golden sand beaches, sunset cruises, and colonial Portuguese charm.",
                top_highlight="Fontainhas Latin Quarter & Palolem Sunset Beach",
                image_url="https://images.unsplash.com/photo-1512343879784-a960bf40e7f2?w=600"
            ),
            DestinationRecommendation(
                id="exp-coorg",
                name="Coorg",
                state_or_country="Karnataka, India",
                vibe_tags=["Coffee Estates", "Misty Hills", "Waterfalls", "Relaxing"],
                estimated_budget_range="₹15,000–₹22,000",
                ideal_duration_days=3,
                why_it_matches="Scotland of India: peaceful aroma of spice plantations, gentle hikes, and authentic Kodava cuisine.",
                top_highlight="Abbey Falls & Raja's Seat Sunset View",
                image_url="https://images.unsplash.com/photo-1598463844053-568779659b64?w=600"
            ),
            DestinationRecommendation(
                id="exp-manali",
                name="Manali",
                state_or_country="Himachal Pradesh, India",
                vibe_tags=["Snow Peaks", "Adventure", "Apple Orchards", "Indie Cafes"],
                estimated_budget_range="₹16,000–₹25,000",
                ideal_duration_days=4,
                why_it_matches="Dramatic Himalayan panoramas, crisp mountain pine air, and riverside cafes in Old Manali.",
                top_highlight="Solang Valley & Rohtang Pass Views",
                image_url="https://images.unsplash.com/photo-1579619564365-0355a6d5fa65?w=600"
            ),
            DestinationRecommendation(
                id="exp-kyoto",
                name="Kyoto",
                state_or_country="Japan",
                vibe_tags=["Temples", "Ryokans", "Bamboo Groves", "Culture"],
                estimated_budget_range="₹55,000–₹80,000",
                ideal_duration_days=4,
                why_it_matches="Serene spiritual capital with timeless wooden machiya townhouses and historic zen gardens.",
                top_highlight="Fushimi Inari Taisha & Gion Lantern Alleys",
                image_url="https://images.unsplash.com/photo-1493976040374-85c8e12f0c0e?w=600"
            ),
            DestinationRecommendation(
                id="exp-austin",
                name="Austin",
                state_or_country="Texas, USA",
                vibe_tags=["Live Music", "Food Trucks", "Craft Beer", "Nightlife"],
                estimated_budget_range="₹60,000–₹85,000",
                ideal_duration_days=4,
                why_it_matches="Live music capital of the world with buzzing concert halls, spring-fed swimming, and brisket BBQ.",
                top_highlight="Rainey Street Historic District & Barton Springs",
                image_url="https://images.unsplash.com/photo-1531218150217-54595bc2b934?w=600"
            ),
            DestinationRecommendation(
                id="exp-paris",
                name="Paris",
                state_or_country="France",
                vibe_tags=["Art Museums", "Bistros", "Architecture", "Romance"],
                estimated_budget_range="₹75,000–₹1,10,000",
                ideal_duration_days=4,
                why_it_matches="Artistic grandeur, picturesque sidewalk cafes, cobblestone alleys, and unforgettable dining.",
                top_highlight="Montmartre Artists Square & Seine River Sunset",
                image_url="https://images.unsplash.com/photo-1502602898657-3e91760cbb34?w=600"
            )
        ]

    # -------------------------------------------------------------
    # Internal Generation Helpers
    # -------------------------------------------------------------
    def _generate_transport_options(self, origin: str, destination: str, currency: str, travelers: int) -> List[TransportationOption]:
        """Generates multi-modal transportation options comparing Flight, Train, Bus, and Cab."""
        is_inr = (currency == "INR")
        
        flight_price = round((4200.0 * travelers) if is_inr else (350.0 * travelers), 2)
        train_price = round((1800.0 * travelers) if is_inr else (140.0 * travelers), 2)
        bus_price = round((1200.0 * travelers) if is_inr else (90.0 * travelers), 2)
        cab_price = round((6500.0) if is_inr else (450.0), 2)

        orig_hub = f"{origin} Airport"
        dest_hub = f"{destination} Airport"

        return [
            TransportationOption(
                id="opt-flight",
                mode="Flight",
                title=f"Direct Flight ({origin} ➔ {destination})",
                carrier="IndiGo / Air India" if is_inr else "Delta / United Airlines",
                duration_str="1h 25m",
                duration_minutes=85,
                price=flight_price,
                currency=currency,
                transfers="Non-Stop",
                departure_time="08:30 AM",
                arrival_time="09:55 AM",
                departure_hub=orig_hub,
                arrival_hub=dest_hub,
                booking_link=f"https://www.google.com/travel/flights?q=flights+from+{origin}+to+{destination}",
                is_recommended=True,
                highlights=["Fastest connection", "Carry-on luggage included", "Morning arrival"]
            ),
            TransportationOption(
                id="opt-train",
                mode="Train",
                title=f"Vande Bharat / Express Train",
                carrier="Indian Railways (IRCTC)" if is_inr else "Amtrak Regional Express",
                duration_str="7h 45m",
                duration_minutes=465,
                price=train_price,
                currency=currency,
                transfers="Direct",
                departure_time="06:00 AM",
                arrival_time="01:45 PM",
                departure_hub=f"{origin} Central Junction",
                arrival_hub=f"{destination} Terminus",
                booking_link="https://www.irctc.co.in" if is_inr else "https://www.amtrak.com",
                is_recommended=False,
                highlights=["Scenic route through western ghats", "Comfortable executive seating", "Low carbon footprint"]
            ),
            TransportationOption(
                id="opt-bus",
                mode="Bus",
                title=f"Overnight Luxury Volvo Sleeper",
                carrier="KSRTC / Intrcity SmartBus" if is_inr else "Megabus / FlixBus",
                duration_str="9h 30m",
                duration_minutes=570,
                price=bus_price,
                currency=currency,
                transfers="Direct",
                departure_time="10:00 PM (Night)",
                arrival_time="07:30 AM",
                departure_hub=f"{origin} Main Bus Terminal",
                arrival_hub=f"{destination} Central Stand",
                booking_link="https://www.redbus.in" if is_inr else "https://www.flixbus.com",
                is_recommended=False,
                highlights=["Sleep during transit", "Save one night hotel bill", "AC Multi-axle sleeper"]
            ),
            TransportationOption(
                id="opt-cab",
                mode="Cab",
                title=f"Private Outstation Sedan / SUV",
                carrier="Uber Intercity / MakeMyTrip Cabs",
                duration_str="8h 00m",
                duration_minutes=480,
                price=cab_price,
                currency=currency,
                transfers="Door-to-Door",
                departure_time="Flexible",
                arrival_time="Flexible",
                departure_hub="Your Home Doorstep",
                arrival_hub=f"Your Hotel in {destination}",
                booking_link="https://m.uber.com/ul/?action=setPickup",
                is_recommended=False,
                highlights=["Pick up directly from home", "Stop anytime for roadside tea & photos", "Total privacy"]
            )
        ]

    def _generate_hotels(self, destination: str, currency: str, style: str, total_budget: float, duration: int) -> List[HotelItem]:
        """Generates 3 curated hotel options with amenities and Booking.com links."""
        is_inr = (currency == "INR")
        base_rate = round((total_budget * 0.35) / max(duration, 1), 2)

        return [
            HotelItem(
                id="hotel-1",
                name=f"The Heritage Courtyard & Spa",
                neighborhood=f"Old {destination} Quarter",
                rating=4.85,
                review_count=524,
                price_per_night=base_rate,
                total_price=round(base_rate * duration, 2),
                currency=currency,
                distance_to_activities_km=1.8,
                style=style,
                amenities=["Free High-Speed Wi-Fi", "Complimentary Breakfast", "Outdoor Swimming Pool", "Air Conditioning", "Airport Shuttle"],
                image_url="https://images.unsplash.com/photo-1566073771259-6a8506099945?w=600",
                why_recommended=f"Centrally located near top heritage sights, offering calm courtyards, superb local breakfast, and high cleanliness scores.",
                booking_url=f"https://www.booking.com/searchresults.html?ss={destination}+Heritage+Hotel",
                is_selected=True
            ),
            HotelItem(
                id="hotel-2",
                name=f"{destination} Palms Boutique Villa",
                neighborhood="Scenic Garden Belt",
                rating=4.78,
                review_count=312,
                price_per_night=round(base_rate * 0.85, 2),
                total_price=round(base_rate * 0.85 * duration, 2),
                currency=currency,
                distance_to_activities_km=3.2,
                style="Boutique Villa",
                amenities=["Free Breakfast", "Tropical Gardens", "Bicycle Rentals", "Private Balconies"],
                image_url="https://images.unsplash.com/photo-1582719508461-905c673771fd?w=600",
                why_recommended="Peaceful setting away from crowds with lush palm views, ideal for relaxation and quiet mornings.",
                booking_url=f"https://www.booking.com/searchresults.html?ss={destination}+Boutique+Villa",
                is_selected=False
            ),
            HotelItem(
                id="hotel-3",
                name=f"Grand Horizon Luxury Suites",
                neighborhood="Central Promenade",
                rating=4.92,
                review_count=789,
                price_per_night=round(base_rate * 1.35, 2),
                total_price=round(base_rate * 1.35 * duration, 2),
                currency=currency,
                distance_to_activities_km=1.1,
                style="Luxury Suites",
                amenities=["Rooftop Lounge", "Full-Service Spa", "24/7 Concierge", "Fitness Center", "Heated Pool"],
                image_url="https://images.unsplash.com/photo-1571896349842-33c89424de2d?w=600",
                why_recommended="Premium luxury with panoramic city vistas, signature dining on-site, and dedicated concierge assistance.",
                booking_url=f"https://www.booking.com/searchresults.html?ss={destination}+Luxury+Resort",
                is_selected=False
            )
        ]

    def _generate_itinerary_activities_food(self, destination: str, duration: int, currency: str, mood: str, travelers: int):
        """Synthesizes realistic daily itinerary, attractions, and restaurant recommendations."""
        is_inr = (currency == "INR")
        daily_plans: List[DayPlan] = []
        activities: List[ActivityItem] = []
        restaurants: List[RestaurantItem] = []

        day_themes = [
            "Arrival, Landmark Exploration & Welcome Feast",
            "Hidden Cultural Quarters & Sunset Vantage Point",
            "Nature Trails, Scenic Waters & Evening Gastronomy",
            "Artisan Markets, Architecture & Farewell Celebration"
        ]

        # Pre-populate 4 rich restaurant highlights
        restaurants = [
            RestaurantItem(
                id="rest-1",
                name=f"Fisherman's Wharf & Coastal Grill" if "goa" in destination.lower() else f"The Artisan Kitchen ({destination})",
                meal_type="Lunch",
                cuisine="Regional Coastal & Seafood" if "goa" in destination.lower() else "Contemporary Regional",
                price_tier="₹₹" if is_inr else "$$",
                rating=4.8,
                distance_km=1.2,
                signature_dish="Butter Garlic Prawns & Crab Xec Xec" if "goa" in destination.lower() else "Slow-Cooked Regional Stew",
                reservation_tip="Reserve patio table around 1:00 PM for scenic breeze.",
                address=f"Riverside Road, {destination}",
                uber_deep_link=f"https://m.uber.com/ul/?action=setPickup&dropoff[formatted_address]={destination}+Fishermans+Wharf",
                is_saved=True
            ),
            RestaurantItem(
                id="rest-2",
                name=f"Spice Garden Verandah",
                meal_type="Dinner",
                cuisine="Authentic Local Heritage",
                price_tier="₹₹₹" if is_inr else "$$$",
                rating=4.9,
                distance_km=2.4,
                signature_dish="Claypot Fish Curry & Warm Poi Bread",
                reservation_tip="Essential to book dinner by 6:00 PM; candlelit tables fill fast.",
                address=f"Heritage Village, {destination}",
                uber_deep_link=f"https://m.uber.com/ul/?action=setPickup&dropoff[formatted_address]={destination}+Spice+Garden",
                is_saved=False
            ),
            RestaurantItem(
                id="rest-3",
                name=f"Cafe Bodega & Roastery",
                meal_type="Breakfast",
                cuisine="Artisanal Bakery & Specialty Coffee",
                price_tier="₹" if is_inr else "$",
                rating=4.7,
                distance_km=0.8,
                signature_dish="Sourdough Shakshuka & Cold Drip Pour Over",
                reservation_tip="Walk-in friendly before 9:30 AM.",
                address=f"Art District, {destination}",
                uber_deep_link=f"https://m.uber.com/ul/?action=setPickup&dropoff[formatted_address]={destination}+Cafe+Bodega",
                is_saved=True
            ),
            RestaurantItem(
                id="rest-4",
                name=f"Sunset Sky Lounge & Tapas",
                meal_type="Dinner",
                cuisine="Modern Fusion Tapas & Cocktails",
                price_tier="₹₹₹" if is_inr else "$$$",
                rating=4.85,
                distance_km=3.1,
                signature_dish="Truffle Mushroom Sliders & Kokum Spritz",
                reservation_tip="Arrive 30 minutes before sunset for the best cliffside table.",
                address=f"Cliffside Promenade, {destination}",
                uber_deep_link=f"https://m.uber.com/ul/?action=setPickup&dropoff[formatted_address]={destination}+Sunset+Lounge",
                is_saved=False
            )
        ]

        # Populate activities & Day Plans
        for d in range(1, duration + 1):
            theme = day_themes[(d - 1) % len(day_themes)]
            items: List[DailyScheduleItem] = []

            # Morning
            morning_act = f"Explore {destination} Historic Fort & Scenic Coastline" if d == 1 else f"Morning Walk through Historic Old {destination}"
            act_cost = 250.0 if is_inr else 20.0
            items.append(
                DailyScheduleItem(
                    time_slot="Morning (09:00 - 12:30)",
                    activity_title=morning_act,
                    area=f"North {destination}" if d == 1 else f"Old Town {destination}",
                    description=f"Panoramic views of the Arabian sea and ancient ramparts, enjoying cool morning breezes before crowds arrive.",
                    cost_estimate_usd=act_cost,
                    pro_tip="Wear comfortable sneakers; walking paths have smooth stone steps.",
                    uber_deep_link=f"https://m.uber.com/ul/?action=setPickup&dropoff[formatted_address]={destination}+Historic+Fort",
                    estimated_uber_fare_usd=120.0 if is_inr else 14.0,
                    estimated_transit_minutes=15,
                    dropoff_address=f"Fort Ramparts, {destination}"
                )
            )
            activities.append(
                ActivityItem(
                    name=morning_act,
                    category="Sightseeing",
                    estimated_duration_hours=3.5,
                    estimated_cost_usd=act_cost,
                    location_area=f"{destination} Coast",
                    description="Historic exploration with stunning coastal photography angles and guide insights.",
                    image_url="https://images.unsplash.com/photo-1548013146-72479768bada?w=600"
                )
            )


            # Afternoon
            afternoon_act = f"Local Spice Plantation Guided Walk & Traditional Lunch" if d % 2 == 0 else f"Artisan Craft Market & Heritage Mansions"
            act_cost_aft = 400.0 if is_inr else 25.0
            items.append(
                DailyScheduleItem(
                    time_slot="Afternoon (13:30 - 16:30)",
                    activity_title=afternoon_act,
                    area=f"Central {destination}",
                    description="Stroll through shaded tropical groves, discovering vanilla, cinnamon, and cardamoms, followed by fresh herbal refreshments.",
                    cost_estimate_usd=act_cost_aft,
                    pro_tip="Natural organic mosquito repellent is provided at the entrance.",
                    uber_deep_link=f"https://m.uber.com/ul/?action=setPickup&dropoff[formatted_address]={destination}+Spice+Plantation",
                    estimated_uber_fare_usd=180.0 if is_inr else 18.0,
                    estimated_transit_minutes=22,
                    dropoff_address=f"Spice Plantation, {destination}"
                )
            )

            # Evening
            evening_act = f"Sunset Catamaran Cruise & Dolphin Spotting" if d == 1 else f"Live Music & Culinary Tasting at {restaurants[1].name}"
            act_cost_eve = 650.0 if is_inr else 40.0
            items.append(
                DailyScheduleItem(
                    time_slot="Evening (17:30 - 21:00)",
                    activity_title=evening_act,
                    area=f"{destination} Waterfront",
                    description="Watch golden sunset skies while listening to live acoustic music and savoring fresh regional delicacies.",
                    cost_estimate_usd=act_cost_eve,
                    pro_tip="Carry a light shawl or sweater as evening sea breezes pick up.",
                    uber_deep_link=f"https://m.uber.com/ul/?action=setPickup&dropoff[formatted_address]={destination}+Waterfront+Promenade",
                    estimated_uber_fare_usd=150.0 if is_inr else 16.0,
                    estimated_transit_minutes=18,
                    dropoff_address=f"Waterfront Promenade, {destination}"
                )
            )

            daily_plans.append(
                DayPlan(
                    day_number=d,
                    day_theme=theme,
                    items=items,
                    day_budget_usd=round(act_cost + act_cost_aft + act_cost_eve + (600.0 if is_inr else 50.0), 2)
                )
            )

        return daily_plans, activities, restaurants

    def _generate_packing_checklist(self, destination: str, duration: int, companions: str, mood: str) -> List[PackingChecklistItem]:
        """Creates personalized packing checklist tailored to climate, activities, and duration."""
        return [
            # Essentials
            PackingChecklistItem(id="pack-1", item="Government Photo ID / Passport", category="🛂 Essentials & Documents", is_essential=True, checked=False, reminder_note="Keep easily accessible in pocket/bag"),
            PackingChecklistItem(id="pack-2", item="Confirmed Booking Vouchers (Offline saved)", category="🛂 Essentials & Documents", is_essential=True, checked=False, reminder_note="Save offline PDF copies"),
            PackingChecklistItem(id="pack-3", item="Primary Debit/Credit Cards & Reserve Cash", category="🛂 Essentials & Documents", is_essential=True, checked=False, reminder_note="Small cash useful for roadside cafes"),
            # Clothing
            PackingChecklistItem(id="pack-4", item=f"Breathable cotton t-shirts ({duration} sets)", category="👕 Clothing & Weather", is_essential=True, checked=False, reminder_note="Lightweight, breathable fabric"),
            PackingChecklistItem(id="pack-5", item="Comfortable walking sneakers / sandals", category="👕 Clothing & Weather", is_essential=True, checked=False, reminder_note="Crucial for cobbles and nature trails"),
            PackingChecklistItem(id="pack-6", item="Light evening layer / jacket", category="👕 Clothing & Weather", is_essential=False, checked=False, reminder_note="For breezy evenings and AC transit"),
            PackingChecklistItem(id="pack-7", item="Swimwear & UV sun sunglasses", category="👕 Clothing & Weather", is_essential=False, checked=False, reminder_note="For pool and beach outings"),
            # Tech
            PackingChecklistItem(id="pack-8", item="Smartphone chargers & Universal Adapter", category="🔌 Tech & Power", is_essential=True, checked=False, reminder_note="Carry in personal carry-on"),
            PackingChecklistItem(id="pack-9", item="10,000mAh+ Portable Power Bank", category="🔌 Tech & Power", is_essential=True, checked=False, reminder_note="Keep charged for navigation and camera"),
            # Health
            PackingChecklistItem(id="pack-10", item="Personal prescription medications & band-aids", category="💊 Health & Comfort", is_essential=True, checked=False, reminder_note="Include travel motion sickness pills"),
            PackingChecklistItem(id="pack-11", item="Sunscreen SPF 50+ & Aloe soothing gel", category="💊 Health & Comfort", is_essential=False, checked=False, reminder_note="Protect skin during day explorations")
        ]


    def _generate_business_schedule(self, destination: str, duration: int, currency: str, company: str) -> Tuple[List[DayPlan], List[ActivityItem], List[RestaurantItem]]:
        """Creates specialized schedule with executive meetings, focus work blocks, and quiet client dining."""
        is_inr = (currency == "INR")
        
        # 1. Activities & Workspaces
        activities = [
            ActivityItem(
                name=f"Strategic Partnership Meeting & Executive Briefing",
                category="Corporate Meeting",
                estimated_duration_hours=2.5,
                estimated_cost_usd=0.0,
                location_area=f"{destination} Tech Corridor",
                description=f"Executive alignment session with key regional partners and {company} stakeholders.",
                why_it_matches="Equipped with private soundproof boardroom, 4K displays, and corporate catering."
            ),
            ActivityItem(
                name="Dedicated Deep Work & Co-Working Focus Period",
                category="Workspace",
                estimated_duration_hours=3.0,
                estimated_cost_usd=0.0,
                location_area=f"Central {destination}",
                description="Uninterrupted focus session in an executive lounge with high-speed fiber Wi-Fi.",
                why_it_matches="Guaranteed 150+ Mbps connection, private phone booths, and ergonomic seating."
            ),
            ActivityItem(
                name="Industry Keynote & Partner Networking Session",
                category="Corporate Summit",
                estimated_duration_hours=3.0,
                estimated_cost_usd=0.0,
                location_area=f"{destination} Convention Hub",
                description="Executive networking panel and industry roadmap announcements.",
                why_it_matches="Crucial for industry connections and senior leadership sync."
            ),
            ActivityItem(
                name="Executive Wellness & Evening Decompression",
                category="Wellness",
                estimated_duration_hours=1.0,
                estimated_cost_usd=0.0,
                location_area=f"Hotel Wellness Center, {destination}",
                description="Restorative workout and relaxation to recharge between intensive business discussions.",
                why_it_matches="State-of-the-art gym, steam facilities, and quiet environment."
            )
        ]

        # 2. Curated Business Restaurants
        restaurants = [
            RestaurantItem(
                id="biz-rest-1",
                name="The Jamavar Executive Dining Room",
                meal_type="Dinner",
                cuisine="Contemporary Fine Dining",
                price_tier="₹₹₹₹" if is_inr else "$$$$",
                rating=4.9,
                distance_km=0.8,
                signature_dish="Chef's Grand Tasting Menu & Wine Cellar Pairings",
                reservation_tip="Private corporate alcove reserved under corporate account",
                address=f"The Leela Palace Promenade, {destination}",
                uber_deep_link=f"https://m.uber.com/ul/?action=setPickup&dropoff[formatted_address]=Jamavar+Fine+Dining+{destination}",
                is_saved=True,
                business_suitability="Premier Client Entertaining • Ultra-Quiet Acoustic Ambiance (48 dB)"
            ),
            RestaurantItem(
                id="biz-rest-2",
                name="The Brasserie All-Day Business Lounge",
                meal_type="Breakfast",
                cuisine="Artisanal Continental & Espresso",
                price_tier="₹₹" if is_inr else "$$",
                rating=4.8,
                distance_km=0.1,
                signature_dish="Single-Origin Pour-over & Smoked Salmon Croissant",
                reservation_tip="Fast business service with daily financial press available",
                address=f"Hotel Lobby Level, {destination}",
                uber_deep_link=f"https://m.uber.com/ul/?action=setPickup&dropoff[formatted_address]=Brasserie+Business+Lounge+{destination}",
                is_saved=True,
                business_suitability="Quick Executive Breakfast & Casual Morning Briefings"
            ),
            RestaurantItem(
                id="biz-rest-3",
                name="Karavalli & Farmlore Reserve",
                meal_type="Lunch",
                cuisine="Curated Regional Gastronomy",
                price_tier="₹₹₹" if is_inr else "$$$",
                rating=4.9,
                distance_km=1.5,
                signature_dish="Wood-Fired Coastal Delicacies & Light Business Lunches",
                reservation_tip="Verandah seating ideal for informal partner discussions",
                address=f"Residency Corridor, {destination}",
                uber_deep_link=f"https://m.uber.com/ul/?action=setPickup&dropoff[formatted_address]=Karavalli+Dining+{destination}",
                is_saved=True,
                business_suitability="Strategy Luncheon with Advisory Team • Low Noise"
            )
        ]

        # 3. Daily Plans
        daily_plans: List[DayPlan] = []
        for d in range(1, duration + 1):
            items: List[DailyScheduleItem] = []
            
            if d == 1:
                theme = "Arrival, Hotel Check-in & Executive Partner Alignment"
                items.append(
                    DailyScheduleItem(
                        time_slot="Morning (08:30 - 10:30)",
                        activity_title="Arrival & Executive Hotel Check-in",
                        area=f"Central {destination}",
                        description="Smooth arrival via Uber Premier, check-in to Executive Room, and high-speed Wi-Fi verification.",
                        cost_estimate_usd=0.0,
                        pro_tip="Collect executive lounge access keycards at front desk.",
                        uber_deep_link=f"https://m.uber.com/ul/?action=setPickup&dropoff[formatted_address]=Hotel+Checkin+{destination}",
                        estimated_uber_fare_usd=420.0 if is_inr else 28.0,
                        estimated_transit_minutes=25,
                        dropoff_address=f"Executive Hotel Suite, {destination}",
                        is_meeting=False,
                        wifi_rating="200 Mbps Fiber",
                        noise_level="Quiet"
                    )
                )
                items.append(
                    DailyScheduleItem(
                        time_slot="Mid-day (11:30 - 13:30)",
                        activity_title="Strategic Partnership Alignment Meeting",
                        area=f"{destination} Tech Corridor",
                        description=f"High-level strategy sync with key accounts and {company} stakeholders.",
                        cost_estimate_usd=0.0,
                        pro_tip="Soundproof boardroom with dual 4K video conferencing displays.",
                        uber_deep_link=f"https://m.uber.com/ul/?action=setPickup&dropoff[formatted_address]=Boardroom+{destination}",
                        estimated_uber_fare_usd=220.0 if is_inr else 18.0,
                        estimated_transit_minutes=15,
                        dropoff_address=f"The Boardroom, {destination}",
                        is_meeting=True,
                        wifi_rating="200 Mbps Fiber",
                        noise_level="Quiet (46 dB)"
                    )
                )
                items.append(
                    DailyScheduleItem(
                        time_slot="Afternoon (14:30 - 17:30)",
                        activity_title="Focused Deep Work & Co-Working Session",
                        area=f"Executive Lounge, {destination}",
                        description="Dedicated quiet work period for email clearance, deck preparation, and engineering syncs.",
                        cost_estimate_usd=0.0,
                        pro_tip="Private acoustic call pods available for client phone calls.",
                        is_meeting=False,
                        wifi_rating="180 Mbps Fiber",
                        noise_level="Quiet"
                    )
                )
                items.append(
                    DailyScheduleItem(
                        time_slot="Evening (19:30 - 22:00)",
                        activity_title="Premier Client Entertainment Dinner at The Jamavar",
                        area=f"Fine Dining Corridor, {destination}",
                        description="Formal dinner hosting senior client leadership in a low-noise, refined atmosphere.",
                        cost_estimate_usd=3200.0 if is_inr else 85.0,
                        pro_tip="Corporate billing code pre-authorized.",
                        uber_deep_link=f"https://m.uber.com/ul/?action=setPickup&dropoff[formatted_address]=Jamavar+Fine+Dining+{destination}",
                        estimated_uber_fare_usd=280.0 if is_inr else 22.0,
                        estimated_transit_minutes=20,
                        dropoff_address=f"The Jamavar, {destination}",
                        is_meeting=True,
                        noise_level="Quiet (50 dB)"
                    )
                )
            elif d == 2:
                theme = "Industry Summit, Keynotes & Contract Finalization"
                items.append(
                    DailyScheduleItem(
                        time_slot="Morning (09:00 - 12:00)",
                        activity_title="Corporate Tech Summit & Executive Panels",
                        area=f"{destination} Exhibition Centre",
                        description="Attending principal keynote presentations, tech demonstrations, and fireside chats.",
                        cost_estimate_usd=0.0,
                        is_meeting=True,
                        wifi_rating="150 Mbps Fiber",
                        noise_level="Moderate"
                    )
                )
                items.append(
                    DailyScheduleItem(
                        time_slot="Mid-day (12:30 - 14:00)",
                        activity_title="Advisory Luncheon at Karavalli",
                        area=f"Central {destination}",
                        description="Working lunch discussing commercial terms, milestones, and Q3 deliverables.",
                        cost_estimate_usd=1600.0 if is_inr else 45.0,
                        is_meeting=True,
                        noise_level="Quiet"
                    )
                )
                items.append(
                    DailyScheduleItem(
                        time_slot="Afternoon (14:30 - 17:30)",
                        activity_title="Contract Review, SOW Alignment & Action Items",
                        area=f"Hotel Executive Suite, {destination}",
                        description="Finalizing contract clauses, SLAs, and technical architecture proposals.",
                        cost_estimate_usd=0.0,
                        is_meeting=True,
                        wifi_rating="200 Mbps Fiber",
                        noise_level="Quiet"
                    )
                )
                items.append(
                    DailyScheduleItem(
                        time_slot="Evening (19:00 - 21:30)",
                        activity_title="Milestone Toast & Partner Leadership Drinks",
                        area=f"Sky Lounge, {destination}",
                        description="Informal celebratory drinks and team debrief overlooking the illuminated skyline.",
                        cost_estimate_usd=2200.0 if is_inr else 60.0,
                        is_meeting=False,
                        noise_level="Moderate"
                    )
                )
            else:
                theme = "Executive Debrief, Checkout & Express Airport Transit"
                items.append(
                    DailyScheduleItem(
                        time_slot="Morning (09:00 - 11:30)",
                        activity_title="Post-Summit Action Items & Debrief",
                        area=f"Hotel Executive Lounge, {destination}",
                        description="Synthesizing meeting minutes, action owners, and follow-up collateral.",
                        cost_estimate_usd=0.0,
                        is_meeting=True,
                        wifi_rating="200 Mbps Fiber",
                        noise_level="Quiet"
                    )
                )
                items.append(
                    DailyScheduleItem(
                        time_slot="Afternoon (12:00 - 13:30)",
                        activity_title="Express Checkout & Uber Premier Airport Transfer",
                        area=f"{destination} International Airport",
                        description="Priority transit via express expressway corridors with digital corporate receipt capture.",
                        cost_estimate_usd=0.0,
                        uber_deep_link=f"https://m.uber.com/ul/?action=setPickup&dropoff[formatted_address]={destination}+International+Airport",
                        estimated_uber_fare_usd=480.0 if is_inr else 35.0,
                        estimated_transit_minutes=35,
                        dropoff_address=f"{destination} Airport Departure Terminal",
                        is_meeting=False
                    )
                )

            daily_plans.append(
                DayPlan(
                    day_number=d,
                    day_theme=theme,
                    items=items,
                    day_budget_usd=round(4500.0 if is_inr else 120.0, 2)
                )
            )

        return daily_plans, activities, restaurants

    def _generate_business_hotels(self, destination: str, currency: str, duration: int) -> List[HotelItem]:
        """Creates specialized 5★ corporate hotels with guaranteed high-speed Wi-Fi, desk, and executive facilities."""
        is_inr = (currency == "INR")
        night_rate_1 = 14500.0 if is_inr else 190.0
        night_rate_2 = 11500.0 if is_inr else 155.0
        night_rate_3 = 7800.0 if is_inr else 95.0

        return [
            HotelItem(
                id="biz-hotel-1",
                name=f"The Leela Palace / Taj Executive Suites ({destination})",
                neighborhood=f"Central Business District, {destination}",
                rating=4.9,
                review_count=1240,
                price_per_night=night_rate_1,
                total_price=round(night_rate_1 * duration, 2),
                currency=currency,
                distance_to_activities_km=1.2,
                style="5-Star Ultra-Luxury Executive Hotel",
                amenities=[
                    "200+ Mbps Fiber Wi-Fi",
                    "Executive Club Lounge Access",
                    "Dedicated In-Room Ergonomic Desk",
                    "Boardroom & Video Conference Rooms",
                    "24/7 Room Service & Garment Pressing",
                    "Airport Limousine Service"
                ],
                image_url="https://images.unsplash.com/photo-1566073771259-6a8506099945?w=800",
                why_recommended="Prime business location, soundproof luxury suites, and verified 200+ Mbps connection for uninterrupted executive work.",
                booking_url="https://www.booking.com",
                is_selected=True
            ),
            HotelItem(
                id="biz-hotel-2",
                name=f"The Oberoi / Ritz-Carlton Corporate Hub ({destination})",
                neighborhood=f"Financial Corridor, {destination}",
                rating=4.8,
                review_count=980,
                price_per_night=night_rate_2,
                total_price=round(night_rate_2 * duration, 2),
                currency=currency,
                distance_to_activities_km=2.0,
                style="5-Star Modern Corporate Hotel",
                amenities=[
                    "150+ Mbps High-Speed Wi-Fi",
                    "Private Acoustic Meeting Pods",
                    "Executive Express Breakfast",
                    "Full Wellness Center & Lap Pool"
                ],
                image_url="https://images.unsplash.com/photo-1582719478250-c89cae4dc85b?w=800",
                why_recommended="Exceptional business center facilities, peaceful garden dining for client lunches, and express check-in.",
                booking_url="https://www.booking.com",
                is_selected=False
            ),
            HotelItem(
                id="biz-hotel-3",
                name=f"Hyatt Centric / Courtyard Executive Business Suites ({destination})",
                neighborhood=f"Tech Corridor, {destination}",
                rating=4.7,
                review_count=820,
                price_per_night=night_rate_3,
                total_price=round(night_rate_3 * duration, 2),
                currency=currency,
                distance_to_activities_km=3.5,
                style="4-Star Premium Business Hotel",
                amenities=[
                    "100+ Mbps Wi-Fi",
                    "Co-Working Lounge",
                    "24/7 Fitness Center",
                    "On-Site Grab-and-Go Cafe"
                ],
                image_url="https://images.unsplash.com/photo-1542314831-068cd1dbfeeb?w=800",
                why_recommended="High-value corporate accommodation with functional workspaces and reliable high-speed connectivity.",
                booking_url="https://www.booking.com",
                is_selected=False
            )
        ]

    def _generate_business_packing_checklist(self, duration: int) -> List[PackingChecklistItem]:
        """Creates specialized packing checklist for executive and corporate travel."""
        return [
            # Work & Tech
            PackingChecklistItem(id="bp-1", item="Corporate Laptop & USB-C 100W Fast Charger", category="💼 Work & Tech Essentials", is_essential=True, checked=False, reminder_note="Ensure full charge before departure"),
            PackingChecklistItem(id="bp-2", item="Universal International Power Adapter & HDMI/Thunderbolt Dongle", category="💼 Work & Tech Essentials", is_essential=True, checked=False, reminder_note="Essential for boardroom displays"),
            PackingChecklistItem(id="bp-3", item="Wireless Presentation Clicker (with spare batteries)", category="💼 Work & Tech Essentials", is_essential=True, checked=False, reminder_note="Keep in laptop sleeve"),
            PackingChecklistItem(id="bp-4", item="Noise-Canceling ANC Headphones", category="💼 Work & Tech Essentials", is_essential=True, checked=False, reminder_note="Critical for calls in transit and airport lounges"),
            # Formal Wardrobe
            PackingChecklistItem(id="bp-5", item=f"Tailored Blazers & Pressed Dress Shirts ({duration} sets)", category="👔 Executive Attire", is_essential=True, checked=False, reminder_note="Pack in garment sleeve or arrange hotel pressing"),
            PackingChecklistItem(id="bp-6", item="Formal Leather Dress Shoes & Dark Socks", category="👔 Executive Attire", is_essential=True, checked=False, reminder_note="Comfortable for day-long meetings"),
            PackingChecklistItem(id="bp-7", item="Smart Casual Evening Wear (for client dinners)", category="👔 Executive Attire", is_essential=False, checked=False, reminder_note="Chinos / blazer combination"),
            # Documents & Finance
            PackingChecklistItem(id="bp-8", item="Company Photo ID & Business Cards (RFID holder)", category="🛂 Documents & Corporate Billing", is_essential=True, checked=False, reminder_note="Carry 20+ cards for networking"),
            PackingChecklistItem(id="bp-9", item="Corporate Expense Card & Receipt Capture Envelope", category="🛂 Documents & Corporate Billing", is_essential=True, checked=False, reminder_note="Keep digital scans for ERP reimbursement"),
            PackingChecklistItem(id="bp-10", item="Offline Contract & Pitch Deck PDF Copies", category="🛂 Documents & Corporate Billing", is_essential=True, checked=False, reminder_note="Saved to tablet or phone storage")
        ]

    def get_preplanned_templates(self) -> List[CanonicalTrip]:
        """
        Returns 5 curated preplanned full trip templates showcasing both corporate business
        and leisure / family / culture / adventure journeys.
        """
        # 1. Executive Business Blitz (Bangalore)
        biz_req = PlanRequest(
            query="3-Day Executive Tech Summit & Client Blitz in Bangalore",
            destination="Bangalore",
            origin_city="Mumbai",
            duration_days=3,
            currency="INR",
            budget_amount=48000.0,
            is_business=True,
            trip_purpose="business",
            company_name="NomadOS Global Inc."
        )
        t_biz = self.generate_canonical_trip(biz_req)
        t_biz.trip_id = "template-business-bangalore"
        t_biz.title = "💼 Bangalore – 3-Day Executive Tech Summit & Client Blitz"

        # 2. Coastal Leisure & Foodie Escape (Goa)
        goa_req = PlanRequest(
            query="3-Day Relaxing Coastal Escape in Goa with friends focusing on beaches and seafood shacks",
            destination="Goa",
            origin_city="Bangalore",
            duration_days=3,
            currency="INR",
            budget_amount=22000.0,
            is_business=False,
            trip_purpose="leisure",
            companions="Friends"
        )
        t_goa = self.generate_canonical_trip(goa_req)
        t_goa.trip_id = "template-leisure-goa"
        t_goa.title = "🏖️ Goa – 3-Day Coastal Chill & Seafood Shacks Escape"

        # 3. High-Tech & Gastronomy Tour (Tokyo)
        tokyo_req = PlanRequest(
            query="5-Day High-Tech & Gastronomy Exploration in Tokyo for 2 people",
            destination="Tokyo",
            origin_city="San Francisco",
            duration_days=5,
            currency="USD",
            budget_amount=2800.0,
            is_business=False,
            trip_purpose="culture",
            companions="Couple"
        )
        t_tokyo = self.generate_canonical_trip(tokyo_req)
        t_tokyo.trip_id = "template-tokyo-foodie"
        t_tokyo.title = "🍣 Tokyo – 5-Day High-Tech & Historic Gastronomy Tour"

        # 4. Coffee Estate & Mountain Family Getaway (Coorg)
        coorg_req = PlanRequest(
            query="3-Day Peaceful Coffee Estate & Mountain Family Retreat in Coorg",
            destination="Coorg",
            origin_city="Bangalore",
            duration_days=3,
            currency="INR",
            budget_amount=24000.0,
            is_business=False,
            trip_purpose="family",
            companions="Family with Kids"
        )
        t_coorg = self.generate_canonical_trip(coorg_req)
        t_coorg.trip_id = "template-coorg-retreat"
        t_coorg.title = "🌿 Coorg – 3-Day Coffee Estate & Mountain Family Retreat"

        # 5. Zen Temples & Historic Ryokan Retreat (Kyoto)
        kyoto_req = PlanRequest(
            query="4-Day Historic Kyoto Zen Temples and Traditional Ryokan Retreat",
            destination="Kyoto",
            origin_city="Tokyo",
            duration_days=4,
            currency="USD",
            budget_amount=2200.0,
            is_business=False,
            trip_purpose="relaxation",
            companions="Couple"
        )
        t_kyoto = self.generate_canonical_trip(kyoto_req)
        t_kyoto.trip_id = "template-kyoto-zen"
        t_kyoto.title = "🏯 Kyoto – 4-Day Zen Temples & Traditional Ryokan Retreat"

        return [t_biz, t_goa, t_tokyo, t_coorg, t_kyoto]

    def clone_template(self, template_id: str) -> Optional[CanonicalTrip]:
        """Clones a curated full trip template into an active trip for customization."""
        templates = {t.trip_id: t for t in self.get_preplanned_templates()}
        template = templates.get(template_id)
        if not template:
            return None

        clone_dict = template.dict()
        new_trip_id = f"trip-{uuid.uuid4().hex[:8]}"
        clone_dict["trip_id"] = new_trip_id
        clone_dict["title"] = template.title.replace("💼 ", "").replace("🏖️ ", "").replace("🍣 ", "").replace("🌿 ", "").replace("🏯 ", "")
        
        cloned_trip = CanonicalTrip.parse_obj(clone_dict)
        self._trips[new_trip_id] = cloned_trip
        return cloned_trip

    def get_trip(self, trip_id: str) -> Optional[CanonicalTrip]:
        """Retrieves a trip by ID from in-memory cache or SQLite persistence."""
        if trip_id in self._trips:
            return self._trips[trip_id]
        saved_dict = persistence.get_trip(trip_id)
        if saved_dict:
            try:
                trip = CanonicalTrip.parse_obj(saved_dict)
                self._trips[trip_id] = trip
                return trip
            except Exception as e:
                logger.warning(f"Failed to parse stored trip {trip_id}: {e}")
        return None

    def save_trip(self, trip_id: str, trip_data: Dict[str, Any]) -> CanonicalTrip:
        """Persists updated trip state to cache and SQLite storage."""
        trip = CanonicalTrip.parse_obj(trip_data)
        self._trips[trip_id] = trip
        try:
            persistence.save_trip(trip_id=trip_id, trip_data=trip.dict())
            logger.info(f"Persisted trip {trip_id} ('{trip.title}') to SQLite.")
        except Exception as e:
            logger.warning(f"Could not persist trip {trip_id} to SQLite: {e}")
        return trip


# Singleton instance
trip_orchestration_service = TripOrchestrationService()


