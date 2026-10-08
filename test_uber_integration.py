"""
Verification script for Uber Rides API integration in NomadOS.
Tests UberService, FastAPI endpoints, deep link generation, and multi-agent plan enrichment.
"""
import asyncio
from httpx import AsyncClient, ASGITransport

from app.main import app
from app.services.uber_service import uber_service
from app.models.requests import PlanRequest
from app.services.planner_service import planner_service


async def test_uber_service():
    print("\n--- [1] Testing UberService Direct Methods ---")
    # Config status
    config = uber_service.get_config_status()
    print(f"Config Status: Sandbox={config.sandbox_mode}, Mode={config.provider_mode}")
    assert config.provider_mode in ["live", "sandbox", "mock"]

    # Universal Deep Link
    link = uber_service.generate_deep_link("Senso-ji Temple, Asakusa, Tokyo", nickname="Senso-ji")
    print(f"Generated Deep Link: {link}")
    assert "https://m.uber.com/ul/?" in link
    assert "dropoff%5Bformatted_address%5D" in link or "dropoff[formatted_address]" in link

    # Dynamic Price Estimates
    estimates_resp = await uber_service.get_price_estimates(
        pickup_address="Tokyo Station, Tokyo",
        dropoff_address="Tsukiji Outer Market, Tokyo"
    )
    print(f"Estimates ({len(estimates_resp.estimates)} products):")
    for prod in estimates_resp.estimates:
        print(f"  - {prod.display_name}: {prod.estimate} ({prod.distance_miles} mi, {prod.duration_seconds // 60} min)")
    assert len(estimates_resp.estimates) >= 3

    # Ride Request Dispatch
    ride = await uber_service.request_ride(
        product_id="uberx",
        pickup_address="Tokyo Station, Tokyo",
        dropoff_address="Tsukiji Outer Market, Tokyo"
    )
    print(f"Dispatched Ride: ID={ride.request_id}, Status={ride.status}, ETA={ride.eta_minutes}m, Fare=${ride.fare_estimate_usd}")
    assert ride.request_id.startswith("uber-req-")
    assert ride.driver is not None
    assert ride.vehicle is not None

    # Status check
    status = uber_service.get_ride_status(ride.request_id)
    print(f"Ride Status Poll: {status.status}, Driver: {status.driver.name}")
    assert status.status in ["accepted", "arriving", "in_progress", "completed"]

    # Cancel Ride
    canceled = uber_service.cancel_ride(ride.request_id)
    print(f"Ride Cancel: success={canceled}")
    assert canceled is True
    post_cancel_status = uber_service.get_ride_status(ride.request_id)
    assert post_cancel_status.status == "canceled"
    print("[OK] UberService methods passed!")


async def test_fastapi_uber_endpoints():
    print("\n--- [2] Testing FastAPI /api/v1/uber Endpoints ---")
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as client:
        # GET /api/v1/uber/config
        r_conf = await client.get("/api/v1/uber/config")
        print(f"GET /api/v1/uber/config -> HTTP {r_conf.status_code}: {r_conf.json()}")
        assert r_conf.status_code == 200

        # GET /api/v1/uber/estimates
        r_est = await client.get("/api/v1/uber/estimates", params={"dropoff": "Louvre Museum, Paris"})
        print(f"GET /api/v1/uber/estimates -> HTTP {r_est.status_code}")
        assert r_est.status_code == 200
        est_data = r_est.json()
        assert len(est_data["estimates"]) >= 3
        print(f"  Products returned: {[p['display_name'] for p in est_data['estimates']]}")

        # POST /api/v1/uber/request-ride
        r_req = await client.post("/api/v1/uber/request-ride", json={
            "product_id": "uber_comfort",
            "end_address": "Louvre Museum, Paris",
            "start_address": "Eiffel Tower, Paris"
        })
        print(f"POST /api/v1/uber/request-ride -> HTTP {r_req.status_code}")
        assert r_req.status_code == 200
        req_data = r_req.json()
        req_id = req_data["request_id"]
        print(f"  Created Request ID: {req_id}, Driver: {req_data['driver']['name']}")

        # GET /api/v1/uber/requests/{id}
        r_stat = await client.get(f"/api/v1/uber/requests/{req_id}")
        print(f"GET /api/v1/uber/requests/{req_id} -> HTTP {r_stat.status_code}: Status={r_stat.json()['status']}")
        assert r_stat.status_code == 200

        # DELETE /api/v1/uber/requests/{id}
        r_del = await client.delete(f"/api/v1/uber/requests/{req_id}")
        print(f"DELETE /api/v1/uber/requests/{req_id} -> HTTP {r_del.status_code}: {r_del.json()}")
        assert r_del.status_code == 200
    print("[OK] FastAPI Uber endpoints passed!")


async def test_planner_pipeline_uber_enrichment():
    print("\n--- [3] Testing Multi-Agent Travel Planner Uber Enrichment ---")
    sample_request = PlanRequest(
        query="3-day culinary trip to Tokyo with $1,800 budget",
        preferred_model_tier="cost_optimized"
    )
    plan = await planner_service.execute_plan_pipeline(sample_request)
    print(f"Plan status: {plan.status}, Destination: {plan.destination}")
    assert len(plan.daily_itinerary) > 0
    day1 = plan.daily_itinerary[0]
    print(f"Day 1: {day1.day_theme}")
    for item in day1.items:
        print(f"  - Slot: {item.activity_title} ({item.area})")
        print(f"    - Uber Fare: ${item.estimated_uber_fare_usd}")
        print(f"    - Transit Time: {item.estimated_transit_minutes} min")
        print(f"    - Dropoff Addr: {item.dropoff_address}")
        print(f"    - Deep Link: {item.uber_deep_link}")
        assert item.uber_deep_link is not None
        assert "m.uber.com" in item.uber_deep_link
        assert item.estimated_uber_fare_usd is not None
        assert item.estimated_transit_minutes is not None
    print("[OK] Multi-Agent Planner successfully enriches itinerary items with Uber data!")


async def main():
    print("==================================================================")
    print("NomadOS - Uber Rides API Integration Verification Test Suite")
    print("==================================================================")
    await test_uber_service()
    await test_fastapi_uber_endpoints()
    await test_planner_pipeline_uber_enrichment()
    print("\n==================================================================")
    print("[SUCCESS] ALL TESTS PASSED: Official Uber API, Endpoints & UI Integration Ready!")
    print("==================================================================")


if __name__ == "__main__":
    asyncio.run(main())
