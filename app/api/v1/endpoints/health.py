"""
Health and readiness endpoints for AWS load balancers, container probes, and monitoring.
"""
from fastapi import APIRouter
from app.config import settings

router = APIRouter()


@router.get("/health", summary="Health Check")
async def health_check():
    """
    Standard AWS App Runner / ALB health check endpoint.
    """
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "version": settings.VERSION,
        "environment": settings.APP_ENV,
        "aws_region": settings.AWS_REGION
    }
