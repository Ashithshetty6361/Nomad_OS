"""
NomadOS - Multi-Agent AI Orchestration Platform Backend Entrypoint.
Production-hardened with flood protection, global error handlers,
circuit breakers, and structured observability.
"""
import time
import os
import uuid
import asyncio
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from app.config import settings
from app.api.v1.router import api_router
from app.core.logging import logger, correlation_id_ctx
from app.core.error_handlers import register_exception_handlers
from app.core.flood_protection import FloodProtectionMiddleware, FloodProtectionConfig
from app.core.rate_limit import rate_limiter
from app.core.response_cache import response_cache

app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Production-Ready Multi-Agent AI Orchestration Platform on AWS (Bedrock, ChromaDB, S3, FastAPI)",
    docs_url="/docs",
    redoc_url="/redoc"
)

# ============================================================
# Register Global Exception Handlers
# ============================================================
register_exception_handlers(app)

# ============================================================
# Middleware Stack (order matters — outermost first)
# ============================================================

# 1. CORS Security Configuration
dev_origins = [
    "http://localhost:8000",
    "http://127.0.0.1:8000",
    "http://localhost:3000",
    "http://127.0.0.1:3000"
]
prod_origins = ["https://nomados.app"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=dev_origins if settings.APP_ENV == "development" else prod_origins,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# 2. Flood Protection (DDoS / server overload defense)
app.add_middleware(
    FloodProtectionMiddleware,
    config=FloodProtectionConfig(
        max_concurrent_requests=50,
        queue_size=20,
        queue_timeout_s=10.0,
        slow_request_threshold_s=30.0,
        degradation_threshold_pct=80.0
    )
)


@app.middleware("http")
async def observability_middleware(request: Request, call_next):
    """
    Middleware for trace correlation, structured request logging,
    latency tracking, and security headers.
    """
    trace_id = request.headers.get("X-Correlation-ID", f"req-{uuid.uuid4().hex[:8]}")
    correlation_id_ctx.set(trace_id)

    start_time = time.perf_counter()

    try:
        response = await call_next(request)
    except Exception as e:
        # This should rarely happen since error handlers catch most exceptions
        logger.error(f"Unhandled middleware error: {type(e).__name__}: {e}")
        from fastapi.responses import JSONResponse
        response = JSONResponse(
            status_code=500,
            content={
                "error": True,
                "code": "MIDDLEWARE_ERROR",
                "message": "An unexpected error occurred.",
                "correlation_id": trace_id
            }
        )

    duration_ms = round((time.perf_counter() - start_time) * 1000.0, 2)

    # Telemetry & Traceability
    response.headers["X-Correlation-ID"] = trace_id
    response.headers["X-Response-Time-Ms"] = str(duration_ms)

    # Defense-in-Depth Security Headers
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["X-XSS-Protection"] = "1; mode=block"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"

    # Add rate-limit headers if available
    if hasattr(request, "state"):
        if hasattr(request.state, "rate_limit_limit"):
            response.headers["X-RateLimit-Limit"] = str(request.state.rate_limit_limit)
        if hasattr(request.state, "rate_limit_remaining"):
            response.headers["X-RateLimit-Remaining"] = str(request.state.rate_limit_remaining)

    # Exclude static assets from detailed request logging
    if not request.url.path.startswith("/static") and not request.url.path.endswith(".ico"):
        logger.info(
            f"{request.method} {request.url.path} [{response.status_code}] ({duration_ms}ms)",
            extra={"latency_ms": duration_ms}
        )
    return response


# Include API V1 Router
app.include_router(api_router, prefix=settings.API_V1_STR)

# Mount web directory for Stitch UI
web_dir = os.path.join(os.path.dirname(__file__), "..", "web")
if os.path.exists(web_dir):
    static_dir = os.path.join(web_dir, "static")
    if os.path.exists(static_dir):
        app.mount("/static", StaticFiles(directory=static_dir), name="static")

    # Landing page route
    @app.get("/landing", include_in_schema=False)
    async def serve_landing():
        landing_file = os.path.join(web_dir, "landing.html")
        if os.path.exists(landing_file):
            return FileResponse(landing_file)
        # Fallback to main app
        index_file = os.path.join(web_dir, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        return {"message": f"Welcome to {settings.PROJECT_NAME}."}

    # Feature Showcase + Mock Interview platform
    @app.get("/showcase", include_in_schema=False)
    async def serve_showcase():
        showcase_file = os.path.join(web_dir, "showcase.html")
        if os.path.exists(showcase_file):
            return FileResponse(showcase_file)
        return {"message": "Showcase page not found."}

    @app.get("/", include_in_schema=False)
    async def serve_ui():
        index_file = os.path.join(web_dir, "index.html")
        if os.path.exists(index_file):
            return FileResponse(index_file)
        return {"message": f"Welcome to {settings.PROJECT_NAME}. Visit /docs for API schema."}


# ============================================================
# Periodic Maintenance Tasks
# ============================================================
async def _periodic_cleanup():
    """Runs periodic cleanup for rate limiter and response cache."""
    while True:
        try:
            await asyncio.sleep(300)  # Every 5 minutes
            rate_limiter.cleanup()
            response_cache.cleanup_expired()
            logger.debug("Periodic cleanup completed (rate limiter + response cache)")
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.debug(f"Periodic cleanup error (non-critical): {e}")


@app.on_event("startup")
async def startup_event():
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION} in {settings.APP_ENV} mode.")
    logger.info("Production resilience active: Circuit Breakers, Retry, Flood Protection, Response Cache")

    # Initialize persistence
    from app.core.persistence import persistence
    stats = persistence.get_stats()
    logger.info(f"SQLite persistence: {stats['total_trips']} trips, {stats['total_users']} users")

    # Start periodic cleanup task
    asyncio.create_task(_periodic_cleanup())


@app.on_event("shutdown")
async def shutdown_event():
    logger.info(f"Shutting down {settings.PROJECT_NAME}.")
