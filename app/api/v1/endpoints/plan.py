"""
Multi-Agent Plan orchestration endpoint.
"""
from fastapi import APIRouter, HTTPException, status, Depends, Request
from app.models.requests import PlanRequest
from app.models.responses import PlanResponse
from app.services.planner_service import planner_service
from app.core.exceptions import NomadException
from app.core.logging import logger
from app.core.rate_limit import apply_rate_limit
from app.config import settings

router = APIRouter()


@router.post(
    "/plan",
    response_model=PlanResponse,
    summary="Orchestrate Multi-Agent Travel Plan",
    dependencies=[Depends(apply_rate_limit("plan", settings.RATE_LIMIT_PLAN_PER_MINUTE, 60))]
)
async def generate_travel_plan(request: PlanRequest, raw_request: Request):
    """
    Executes the 4-agent orchestration pipeline:
    1. **ContextParsingAgent** (Fast Model Route)
    2. **DiscoveryAgent** (Fast Model Route)
    3. **RAGEnrichmentAgent** (ChromaDB Vector Retrieval)
    4. **BookingReasoningAgent** (Reasoning Model Route)
    
    Production Role-Based Separation:
    - If user_role == 'admin' or header X-User-Role == 'admin': Full engineering telemetry & logs returned.
    - If user_role == 'customer' (default): Returns clean customer travel payload, masking raw tokens & AI bills.
    """
    try:
        response = await planner_service.execute_plan_pipeline(request)
        
        # Check if caller has admin privileges
        role_header = raw_request.headers.get("X-User-Role", "").lower()
        is_admin = (request.user_role == "admin" or role_header == "admin")
        
        if not is_admin:
            # Mask company internal engineering metrics for customer privacy and clean UX
            response.telemetry = None
            response.agent_steps = None
            
        return response
    except NomadException as e:
        logger.error(f"Domain error in /plan endpoint: {e.message}")
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"code": e.code, "message": e.message}
        )
    except Exception as e:
        logger.error(f"Unhandled error in /plan endpoint: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={"code": "INTERNAL_SERVER_ERROR", "message": str(e)}
        )
