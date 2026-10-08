"""
Uber Rides API Endpoints.
Provides live dynamic price estimates, ride booking requests, status tracking, and configuration.
"""
from typing import Optional
from fastapi import APIRouter, HTTPException, Query, status, Depends

from app.services.uber_service import uber_service
from app.core.rate_limit import apply_rate_limit
from app.config import settings
from app.models.responses import (
    UberPriceEstimatesResponse,
    UberRideRequestPayload,
    UberRideStatusResponse,
    UberConfigStatus
)

router = APIRouter(prefix="/uber", tags=["Uber Rides"])


@router.get("/config", response_model=UberConfigStatus, summary="Get Uber API Configuration & Mode")
async def get_uber_config():
    """
    Returns current status of Uber API connectivity, developer keys, and sandbox mode.
    """
    return uber_service.get_config_status()


@router.get(
    "/estimates", 
    response_model=UberPriceEstimatesResponse, 
    summary="Get Dynamic Price Estimates",
    dependencies=[Depends(apply_rate_limit("uber_estimates", settings.RATE_LIMIT_UBER_PER_MINUTE, 60))]
)
async def get_price_estimates(
    dropoff: str = Query(..., description="Destination name or address"),
    pickup: str = Query("Current Location", description="Pickup name or address"),
    start_lat: Optional[float] = Query(None, description="Pickup latitude"),
    start_lng: Optional[float] = Query(None, description="Pickup longitude"),
    end_lat: Optional[float] = Query(None, description="Destination latitude"),
    end_lng: Optional[float] = Query(None, description="Destination longitude")
):
    """
    Fetches dynamic fare quotes and ETA across Uber products (UberX, Comfort, UberXL, Black).
    """
    try:
        estimates = await uber_service.get_price_estimates(
            pickup_address=pickup,
            dropoff_address=dropoff,
            start_lat=start_lat,
            start_lng=start_lng,
            end_lat=end_lat,
            end_lng=end_lng
        )
        return estimates
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate Uber estimates: {str(e)}"
        )


@router.post(
    "/request-ride", 
    response_model=UberRideStatusResponse, 
    summary="Request / Book an Uber Ride",
    dependencies=[Depends(apply_rate_limit("uber_request_ride", 5, 60))]
)
async def request_ride(payload: UberRideRequestPayload):
    """
    Dispatches an Uber ride request with dynamic lifecycle tracking.
    """
    try:
        ride = await uber_service.request_ride(
            product_id=payload.product_id,
            pickup_address=payload.start_address or "Current Location",
            dropoff_address=payload.end_address,
            start_lat=payload.start_latitude,
            start_lng=payload.start_longitude,
            end_lat=payload.end_latitude,
            end_lng=payload.end_longitude
        )
        return ride
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to dispatch Uber ride: {str(e)}"
        )


@router.get("/requests/{request_id}", response_model=UberRideStatusResponse, summary="Get Ride Tracking & Status")
async def get_ride_status(request_id: str):
    """
    Returns live ride state (accepted, driver arriving, in progress, completed) and vehicle details.
    """
    ride = uber_service.get_ride_status(request_id)
    if not ride:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Uber ride request '{request_id}' not found."
        )
    return ride


@router.delete("/requests/{request_id}", summary="Cancel Ride Request")
async def cancel_ride(request_id: str):
    """
    Cancels an active Uber ride request.
    """
    success = uber_service.cancel_ride(request_id)
    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Uber ride request '{request_id}' not found or cannot be canceled."
        )
    return {"status": "SUCCESS", "message": f"Ride {request_id} has been canceled."}
