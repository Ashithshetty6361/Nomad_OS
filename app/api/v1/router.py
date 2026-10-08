"""
API V1 main router.
"""
from fastapi import APIRouter
from app.api.v1.endpoints import health, plan, observability, uber, trip, aiops

api_router = APIRouter()
api_router.include_router(health.router, tags=["Health"])
api_router.include_router(plan.router, tags=["Planning"])
api_router.include_router(trip.router, prefix="/trip", tags=["Trip Companion"])
api_router.include_router(observability.router, tags=["Observability"])
api_router.include_router(uber.router, tags=["Uber Rides"])
api_router.include_router(aiops.router, tags=["AIOps Engineering"])
