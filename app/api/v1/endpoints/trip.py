"""
API Endpoints for Canonical Trip Companion Platform.
Provides requirement extraction, multi-section trip generation, contextual AI refinement,
and destination exploration.
"""
from fastapi import APIRouter, HTTPException, status, Depends
from typing import Dict, Any, List

from app.models.requests import PlanRequest, ExtractIntentRequest, RefineTripRequest
from app.models.responses import ExtractIntentResponse, RefineTripResponse
from app.models.state import CanonicalTrip, DestinationRecommendation
from app.services.trip_orchestration_service import trip_orchestration_service
from app.core.logging import logger
from app.core.rate_limit import apply_rate_limit
from app.config import settings

router = APIRouter()


@router.post(
    "/extract",
    response_model=ExtractIntentResponse,
    summary="Extract Travel Requirements & Missing Fields",
    dependencies=[Depends(apply_rate_limit("trip_extract", 30, 60))]
)
async def extract_trip_requirements(req: ExtractIntentRequest):
    """
    Extracts structured requirements from natural language trip idea.
    Identifies missing fields without re-asking what was already provided,
    and recommends tailored destinations if unspecified.
    """
    try:
        return trip_orchestration_service.extract_requirements(req.query)
    except Exception as e:
        logger.error(f"Error extracting trip requirements: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": f"Failed to extract requirements: {str(e)}"}
        )


@router.post(
    "/generate",
    response_model=CanonicalTrip,
    summary="Synthesize Complete Canonical Trip Across 9 Modules",
    dependencies=[Depends(apply_rate_limit("trip_generate", 20, 60))]
)
async def generate_trip(req: PlanRequest):
    """
    Synthesizes the complete canonical trip holding:
    Overview, Itinerary, Multi-Modal Transport, Hotels, Activities,
    Restaurants, Budget, Packing Checklist, and Smart Reminders.
    """
    try:
        canonical = trip_orchestration_service.generate_canonical_trip(req)
        return canonical
    except Exception as e:
        logger.error(f"Error generating canonical trip: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": f"Failed to generate trip: {str(e)}"}
        )


@router.post(
    "/refine",
    response_model=RefineTripResponse,
    summary="Contextual Conversational AI Trip Refinement",
    dependencies=[Depends(apply_rate_limit("trip_refine", 20, 60))]
)
async def refine_trip(req: RefineTripRequest):
    """
    Applies quiet, user-controlled AI refinements using existing trip context:
    e.g., 'Make Day 2 less tiring', 'Find cheaper hotel', 'Reduce trip cost'.
    """
    try:
        return trip_orchestration_service.refine_trip(
            trip_id=req.trip_id,
            prompt=req.prompt,
            current_state=req.current_trip
        )
    except Exception as e:
        logger.error(f"Error refining trip {req.trip_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"message": f"Failed to refine trip: {str(e)}"}
        )


@router.get(
    "/templates",
    response_model=List[CanonicalTrip],
    summary="Get Preplanned Curated Full Trip Templates"
)
async def get_templates():
    """Returns hand-curated, preplanned complete trips for instant preview and cloning."""
    return trip_orchestration_service.get_preplanned_templates()


@router.post(
    "/templates/{template_id}/clone",
    response_model=CanonicalTrip,
    summary="Clone a Preplanned Template into an Active Trip"
)
async def clone_template(template_id: str):
    """Clones a preplanned full trip template into an active trip for customization."""
    trip = trip_orchestration_service.clone_template(template_id)
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": f"Template {template_id} not found."}
        )
    return trip


@router.get(
    "/explore",
    response_model=List[DestinationRecommendation],
    summary="Get Curated Explore Destinations"
)
async def get_explore_destinations():
    """Returns hand-picked trending destinations for the Explore gallery."""
    return trip_orchestration_service.get_explore_destinations()


@router.get(
    "/{trip_id}",
    response_model=CanonicalTrip,
    summary="Get Canonical Trip by ID"
)
async def get_trip(trip_id: str):
    """Retrieves an existing saved trip state."""
    trip = trip_orchestration_service.get_trip(trip_id)
    if not trip:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"message": f"Trip {trip_id} not found."}
        )
    return trip


@router.post(
    "/{trip_id}/save",
    response_model=CanonicalTrip,
    summary="Persist Canonical Trip State"
)
async def save_trip(trip_id: str, trip_data: Dict[str, Any]):
    """Persists modifications made by the user to the canonical trip state."""
    try:
        return trip_orchestration_service.save_trip(trip_id, trip_data)
    except Exception as e:
        logger.error(f"Error saving trip {trip_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"message": f"Failed to persist trip state: {str(e)}"}
        )
