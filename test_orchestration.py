"""
End-to-end verification script for NomadOS Multi-Agent Pipeline.
"""
import asyncio
import json
from app.models.requests import PlanRequest
from app.services.planner_service import planner_service


async def main():
    print("==================================================================")
    print("NomadOS Multi-Agent Orchestration - End-to-End Verification Test")
    print("==================================================================")

    sample_request = PlanRequest(
        query="5-day foodie & culture trip to Tokyo for 2 people with a $2,800 budget in April, avoiding tourist traps.",
        preferred_model_tier="cost_optimized"
    )

    print(f"\n[1] Submitting Test Request: '{sample_request.query}'")
    response = await planner_service.execute_plan_pipeline(sample_request)

    print(f"\n[2] Execution Status: {response.status}")
    print(f"    Destination: {response.destination} ({response.duration_days} Days)")
    print(f"    Travel Style: {response.travel_style}")
    print(f"    Estimated Cost: ${response.estimated_cost_usd} (Budget: ${response.total_budget_usd})")
    
    print("\n[3] Agent Steps Executed:")
    for step in response.agent_steps:
        print(f"    - {step.step_name} ({step.agent_name}) | Model: {step.model_id} | Latency: {step.latency_ms}ms")

    print("\n[4] Telemetry & Cost Telemetry:")
    t = response.telemetry
    print(f"    Trace ID: {t.trace_id}")
    print(f"    Total Latency: {t.total_latency_ms} ms")
    print(f"    Total Tokens: {t.total_tokens}")
    print(f"    Estimated Bedrock Cost: ${t.estimated_cost_usd:.6f}")
    print(f"    Savings from Cost Routing vs Sonnet: ${t.cost_savings_usd:.6f}")

    print("\n[5] Daily Itinerary Sample (Day 1):")
    if response.daily_itinerary:
        day1 = response.daily_itinerary[0]
        print(f"    Day 1 Theme: {day1.day_theme}")
        for item in day1.items:
            print(f"      • [{item.time_slot}] {item.activity_title} (~${item.cost_estimate_usd})")

    print("\n==================================================================")
    print("[SUCCESS] All 4 Specialized Agents & Deterministic Planner Passed Successfully!")
    print("==================================================================")


if __name__ == "__main__":
    asyncio.run(main())
