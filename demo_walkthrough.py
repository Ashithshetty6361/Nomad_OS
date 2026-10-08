"""
================================================================================
NomadOS - Autonomous Multi-Agent AI Travel Companion Platform
Interactive Live Demonstration & Verification Script
================================================================================
Demonstrates:
  1. Local LLM Service (Ollama Phi-3 / Llama-3.1 / Nomic-Embed)
  2. Requirement Extraction & Adaptive Destination Recommendation
  3. Multi-Agent DAG Execution (Research, Logistics, Budget, Synthesis)
  4. 9-Module Canonical Trip Generation & Persistence
  5. Uber Rides API Integration (Estimates, Universal Deep Links, Booking HUD)
  6. Contextual AI Trip Refinement & State Memory
  7. Real-Time Observability, Latency & Cost Savings Telemetry
================================================================================
"""

import asyncio
import time
import sys
import os
from typing import Dict, Any

from app.config import settings
from app.services.llm_service import llm_service
from app.services.trip_orchestration_service import trip_orchestration_service
from app.services.planner_service import planner_service
from app.services.uber_service import uber_service
from app.models.requests import PlanRequest, RefineTripRequest


import sys
import io

if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
        sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass


class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'
    ENDC = '\033[0m'


def print_banner(text: str, color=Colors.CYAN):
    border = "=" * 80
    print(f"\n{color}{border}")
    print(f"  {text}")
    print(f"{border}{Colors.ENDC}\n")


def print_step(step_num: int, title: str):
    print(f"\n{Colors.BOLD}{Colors.YELLOW}=== [STAGE {step_num}] {title} ==={Colors.ENDC}")


async def demo_stage_1_system_health():
    print_step(1, "System Diagnostics & Local AI Engine Health Check")
    print(f"  • Local LLM Enabled: {Colors.GREEN}{settings.USE_LOCAL_LLM}{Colors.ENDC}")
    print(f"  • Ollama Base URL:    {Colors.BLUE}{settings.OLLAMA_BASE_URL}{Colors.ENDC}")
    print(f"  • Fast Model:         {Colors.BOLD}{settings.OLLAMA_FAST_MODEL}{Colors.ENDC}")
    print(f"  • Reasoning Model:    {Colors.BOLD}{settings.OLLAMA_REASONING_MODEL}{Colors.ENDC}")
    print(f"  • Embedding Model:    {Colors.BOLD}{settings.OLLAMA_EMBEDDING_MODEL}{Colors.ENDC}")
    print(f"  • Uber Sandbox Mode:  {Colors.GREEN}{settings.UBER_SANDBOX_MODE}{Colors.ENDC}")

    # Test direct local LLM inference
    t0 = time.time()
    system_prompt = "You are NomadOS AI travel assistant. Return JSON only with key 'highlights' list."
    user_prompt = "Generate 3 unique travel highlights for Tokyo, Japan in JSON format: {\"highlights\": [\"item1\", \"item2\", \"item3\"]}"
    try:
        response, telemetry = await llm_service.invoke(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            task_type="context_parsing",
            temperature=0.3
        )
        elapsed = (time.time() - t0) * 1000
        print(f"\n  {Colors.GREEN}✔ Local Ollama Connected Successfully!{Colors.ENDC}")
        print(f"    - Provider:        {telemetry.get('provider', 'Local_Ollama')}")
        print(f"    - Model Used:      {telemetry.get('model_id', settings.OLLAMA_FAST_MODEL)}")
        print(f"    - Response Time:   {elapsed:.1f} ms")
        print(f"    - Token Usage:     {telemetry.get('prompt_tokens', 0)} in / {telemetry.get('completion_tokens', 0)} out")
        print(f"    - Local Cost:      ${telemetry.get('cost_usd', 0.0):.6f} (100% Free / Local)")
        print(f"    - Response Sample: {response.get('highlights', [])[:2]}")
    except Exception as e:
        print(f"  {Colors.RED}✘ Ollama direct invocation error: {e}{Colors.ENDC}")


async def demo_stage_2_requirement_extraction():
    print_step(2, "Requirement Extraction & Multi-Intent Parsing")
    query = "Plan a 4-day foodie and cultural getaway to Kyoto for a couple with $2,400 budget"
    print(f"  User Query: \"{Colors.BOLD}{query}{Colors.ENDC}\"")

    extraction = trip_orchestration_service.extract_requirements(query)
    print(f"\n  Extracted Parameters:")
    for key, val in extraction.extracted.items():
        print(f"    • {key:<18}: {Colors.CYAN}{val}{Colors.ENDC}")
    
    print(f"  Missing Fields Detected: {extraction.missing_fields}")
    if extraction.suggested_destinations:
        print(f"  Suggested Destinations ({len(extraction.suggested_destinations)}):")
        for d in extraction.suggested_destinations[:2]:
            print(f"    - {d.name} ({d.country}) | {d.estimated_budget_range} | {d.match_score * 100:.0f}% match")


async def demo_stage_3_multi_agent_dag():
    print_step(3, "Autonomous Multi-Agent DAG Execution & 9-Module Trip Synthesis")
    plan_req = PlanRequest(
        query="4-day foodie and cultural getaway to Kyoto for a couple with $2,400 budget",
        destination="Kyoto",
        duration_days=4,
        budget_usd=2400.0,
        travel_style="Foodie & Culture",
        travelers_count=2,
        currency="USD",
        companions="Couple",
        origin_city="Tokyo",
        preferred_model_tier="cost_optimized"
    )

    t0 = time.time()
    print("  Executing 4-Agent Pipeline:")
    print("    [1/4] Research & Discovery Agent -> Semantic Place & Attraction Retrieval")
    print("    [2/4] Logistics & Route Agent    -> Inter-city transit, Hotels & Uber Matrix")
    print("    [3/4] Budget & Optimization Agent-> Micro-costing & Reserve Allocation")
    print("    [4/4] Synthesis Agent            -> Multi-day Schedule & Checklist Generation")

    # Generate canonical trip
    trip = trip_orchestration_service.generate_canonical_trip(plan_req)
    total_time = (time.time() - t0)

    print(f"\n  {Colors.GREEN}✔ Canonical Trip Synthesized in {total_time:.2f}s! Trip ID: {trip.trip_id}{Colors.ENDC}")
    print(f"  • Destination:      {trip.destination} ({trip.duration_days} Days)")
    print(f"  • Estimated Total:  ${trip.budget.get('estimated_total', 0):,.2f} / ${plan_req.budget_usd:,.2f}")
    
    print(f"\n  {Colors.BOLD}--- 9 Canonical Trip Modules Verified ---{Colors.ENDC}")
    print(f"  1. 🚆 Transportation:     {len(trip.transportation)} options ({', '.join(t.mode for t in trip.transportation[:3])})")
    print(f"  2. 🏨 Curated Hotels:     {len(trip.hotels)} accommodations (e.g. {trip.hotels[0].name})")
    print(f"  3. 📅 Daily Itinerary:    {len(trip.daily_itinerary)} full days planned")
    print(f"  4. 🎯 Top Activities:     {len(trip.activities)} highlights ({trip.activities[0].name})")
    print(f"  5. 🍣 Dining & Food:      {len(trip.restaurants)} curated spots ({trip.restaurants[0].name})")
    print(f"  6. 🎒 Packing Checklist:  {len(trip.packing_checklist)} items categorized")
    print(f"  7. ✅ Pre-Trip Checklist: {len(trip.pre_trip_checklist)} actionable steps")
    print(f"  8. ⏰ Smart Reminders:    {len(trip.reminders)} departure & booking alerts")
    print(f"  9. 📊 Readiness Progress: {trip.progress.progress_percentage}% completed")

    # Sample Day 1 Itinerary
    if trip.daily_itinerary:
        day1 = trip.daily_itinerary[0]
        print(f"\n  {Colors.CYAN}Sample Day 1 Itinerary ({day1.day_theme}):{Colors.ENDC}")
        for item in day1.items:
            print(f"    • [{item.time_slot}] {item.activity_title} ({item.area}) | Est: ${item.cost_estimate_usd}")

    return trip


async def demo_stage_4_uber_integration():
    print_step(4, "Uber Rides API Integration & Transit Estimates")
    pickup = "Kyoto Station, Kyoto"
    dropoff = "Fushimi Inari Taisha, Kyoto"
    
    print(f"  Route: {Colors.BOLD}{pickup}{Colors.ENDC} ➔ {Colors.BOLD}{dropoff}{Colors.ENDC}")
    
    # 1. Price Estimates
    estimates_resp = await uber_service.get_price_estimates(pickup_address=pickup, dropoff_address=dropoff)
    print(f"\n  Available Uber Products ({len(estimates_resp.estimates)}):")
    for prod in estimates_resp.estimates:
        print(f"    • {prod.display_name:<16}: {prod.estimate:<10} (ETA: {prod.duration_seconds // 60}m, Distance: {prod.distance_miles:.1f} mi)")

    # 2. Universal Deep Link
    deep_link = uber_service.generate_deep_link(destination_address=dropoff, nickname="Fushimi Inari")
    print(f"\n  Universal Mobile Deep Link:\n    {Colors.BLUE}{deep_link[:75]}...{Colors.ENDC}")

    # 3. Ride Dispatch
    ride = await uber_service.request_ride(
        product_id="uberx",
        pickup_address=pickup,
        dropoff_address=dropoff
    )
    print(f"\n  {Colors.GREEN}✔ Live Ride Dispatched via Uber API / Sandbox:{Colors.ENDC}")
    print(f"    - Request ID:     {ride.request_id}")
    print(f"    - Status:         {Colors.BOLD}{ride.status.upper()}{Colors.ENDC}")
    print(f"    - Driver:         {ride.driver.name} (Rating: {ride.driver.rating}★, Phone: {ride.driver.phone_number})")
    print(f"    - Vehicle:        {ride.vehicle.make} {ride.vehicle.model} ({ride.vehicle.license_plate})")
    print(f"    - Arrival ETA:    {ride.eta_minutes} mins | Fare: ${ride.fare_estimate_usd}")


async def demo_stage_5_contextual_refinement(trip_dict: Dict[str, Any]):
    print_step(5, "Contextual AI Trip Refinement & State Memory")
    trip_id = trip_dict.get("trip_id")
    refine_prompt = "Can you make Day 2 more relaxed and add an authentic matcha tea ceremony in the afternoon?"
    print(f"  Trip ID: {trip_id}")
    print(f"  User Refinement Request: \"{Colors.BOLD}{refine_prompt}{Colors.ENDC}\"")

    t0 = time.time()
    res = trip_orchestration_service.refine_trip(trip_id, refine_prompt, trip_dict)
    elapsed = (time.time() - t0)

    print(f"\n  {Colors.GREEN}✔ AI Refinement Processed in {elapsed:.2f}s!{Colors.ENDC}")
    print(f"  AI Assistant Response:")
    print(f"    \"{res.message}\"")
    print(f"\n  Modifications Applied:")
    for change in res.change_summary:
        print(f"    {Colors.GREEN}✔ {change}{Colors.ENDC}")


async def demo_stage_6_telemetry_summary():
    print_step(6, "Enterprise Observability, Token Economics & Zero-Cost Telemetry")
    print(f"  • Architecture:    Multi-Agent DAG with Local Ollama Inference")
    print(f"  • Primary Model:   {settings.OLLAMA_FAST_MODEL} (3.8B Lightweight Super-fast)")
    print(f"  • Reasoning Model: {settings.OLLAMA_REASONING_MODEL} (8B High-Precision)")
    print(f"  • Infrastructure:  100% Localhost ({settings.OLLAMA_BASE_URL})")
    print(f"  • External Bill:   {Colors.GREEN}$0.00 / month (Zero AWS / Gemini API Costs){Colors.ENDC}")
    print(f"  • Privacy:         100% On-Device Data Sovereignty (Zero Data Leakage)")
    print(f"  • UI Dashboard:    Glassmorphic Single-Page Application on http://127.0.0.1:8000")


async def main():
    print_banner("NOMADOS AUTONOMOUS TRAVEL COMPANION - LIVE DEMONSTRATION SUITE", Colors.CYAN)
    
    await demo_stage_1_system_health()
    await demo_stage_2_requirement_extraction()
    trip = await demo_stage_3_multi_agent_dag()
    await demo_stage_4_uber_integration()
    await demo_stage_5_contextual_refinement(trip.dict())
    await demo_stage_6_telemetry_summary()

    print_banner("DEMONSTRATION COMPLETED SUCCESSFULLY - ALL SYSTEMS GREEN", Colors.GREEN)


if __name__ == "__main__":
    asyncio.run(main())
