"""
Server Flood Protection & Backpressure Middleware for NomadOS.
Protects against DDoS, connection floods, and thundering herd scenarios.

Features:
  - Global concurrent request limiter (semaphore-based)
  - Backpressure queue with timeout
  - Slow-client detection
  - Graceful degradation under heavy load
"""
import asyncio
import time
from typing import Set
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from app.core.logging import logger
from app.config import settings


class FloodProtectionConfig:
    """Configuration for flood protection."""
    def __init__(
        self,
        max_concurrent_requests: int = 50,
        queue_size: int = 20,
        queue_timeout_s: float = 10.0,
        slow_request_threshold_s: float = 30.0,
        degradation_threshold_pct: float = 80.0,
        global_burst_limit_per_minute: int = 200,
    ):
        self.max_concurrent_requests = max_concurrent_requests
        self.queue_size = queue_size
        self.queue_timeout_s = queue_timeout_s
        self.slow_request_threshold_s = slow_request_threshold_s
        self.degradation_threshold_pct = degradation_threshold_pct
        self.global_burst_limit_per_minute = global_burst_limit_per_minute


class FloodProtectionMetrics:
    """Metrics for AIOps monitoring of server load."""
    def __init__(self):
        self.active_requests: int = 0
        self.queued_requests: int = 0
        self.total_served: int = 0
        self.total_rejected: int = 0
        self.total_queued: int = 0
        self.total_slow_requests: int = 0
        self.total_degraded_responses: int = 0
        self.peak_concurrent: int = 0

    def to_dict(self) -> dict:
        return {
            "active_requests": self.active_requests,
            "queued_requests": self.queued_requests,
            "total_served": self.total_served,
            "total_rejected": self.total_rejected,
            "total_queued": self.total_queued,
            "total_slow_requests": self.total_slow_requests,
            "total_degraded_responses": self.total_degraded_responses,
            "peak_concurrent": self.peak_concurrent
        }


# Non-essential endpoints that can be disabled under heavy load
NON_ESSENTIAL_PATHS = {
    "/api/v1/trip/explore",
    "/api/v1/trip/templates",
    "/api/v1/observability/models",
}

# Paths exempt from flood protection (health checks, static assets)
EXEMPT_PATHS = {"/api/v1/health", "/health", "/docs", "/redoc", "/openapi.json"}


class FloodProtectionMiddleware(BaseHTTPMiddleware):
    """
    Middleware that enforces concurrent request limits with backpressure queuing.
    When the server is at capacity, incoming requests are queued briefly.
    If the queue is also full, requests are rejected with 503.
    Under extreme load, non-essential features are gracefully disabled.
    """

    def __init__(self, app, config: FloodProtectionConfig = None):
        super().__init__(app)
        self.config = config or FloodProtectionConfig()
        self._semaphore = asyncio.Semaphore(self.config.max_concurrent_requests)
        self._queue_semaphore = asyncio.Semaphore(
            self.config.max_concurrent_requests + self.config.queue_size
        )
        self.metrics = FloodProtectionMetrics()

    def _is_exempt(self, path: str) -> bool:
        """Check if the path is exempt from flood protection."""
        if path.startswith("/static"):
            return True
        if path in EXEMPT_PATHS:
            return True
        if path.endswith(".ico") or path.endswith(".css") or path.endswith(".js"):
            return True
        return False

    def _is_degradation_mode(self) -> bool:
        """Check if server load exceeds degradation threshold."""
        capacity_pct = (
            self.metrics.active_requests / max(1, self.config.max_concurrent_requests) * 100
        )
        return capacity_pct >= self.config.degradation_threshold_pct

    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        # Exempt static assets and health checks
        if self._is_exempt(path):
            return await call_next(request)

        # Graceful degradation: disable non-essential endpoints under heavy load
        if self._is_degradation_mode() and path in NON_ESSENTIAL_PATHS:
            self.metrics.total_degraded_responses += 1
            logger.warning(
                f"Graceful degradation: blocking non-essential path {path} "
                f"(active={self.metrics.active_requests}/{self.config.max_concurrent_requests})"
            )
            return JSONResponse(
                status_code=503,
                content={
                    "error": True,
                    "code": "GRACEFUL_DEGRADATION",
                    "message": (
                        "This feature is temporarily paused due to high demand. "
                        "Core trip planning remains available."
                    ),
                    "retry_after": 15
                },
                headers={"Retry-After": "15"}
            )

        # Try to acquire the outer queue semaphore (backpressure)
        acquired_queue = self._queue_semaphore.locked()
        if not self._queue_semaphore._value:
            # Queue is also full — reject immediately
            self.metrics.total_rejected += 1
            logger.error(
                f"Flood protection: REJECTED request to {path} "
                f"(active={self.metrics.active_requests}, queue full)"
            )
            return JSONResponse(
                status_code=503,
                content={
                    "error": True,
                    "code": "SERVER_OVERLOADED",
                    "message": (
                        "The server is experiencing very high traffic. "
                        "Please try again in a few seconds."
                    ),
                    "retry_after": 10
                },
                headers={"Retry-After": "10"}
            )

        # Try to acquire the main processing semaphore with timeout
        start = time.time()
        try:
            acquired = await asyncio.wait_for(
                self._semaphore.acquire(),
                timeout=self.config.queue_timeout_s
            )
        except asyncio.TimeoutError:
            self.metrics.total_rejected += 1
            wait_time = round(time.time() - start, 1)
            logger.warning(
                f"Flood protection: request to {path} TIMED OUT after {wait_time}s in queue"
            )
            return JSONResponse(
                status_code=503,
                content={
                    "error": True,
                    "code": "QUEUE_TIMEOUT",
                    "message": (
                        "Your request was queued but the server is still busy. "
                        "Please try again shortly."
                    ),
                    "retry_after": 5
                },
                headers={"Retry-After": "5"}
            )

        # Request is now being processed
        self.metrics.active_requests += 1
        self.metrics.total_served += 1
        if self.metrics.active_requests > self.metrics.peak_concurrent:
            self.metrics.peak_concurrent = self.metrics.active_requests

        request_start = time.time()
        try:
            response = await call_next(request)

            # Slow-client detection
            elapsed = time.time() - request_start
            if elapsed > self.config.slow_request_threshold_s:
                self.metrics.total_slow_requests += 1
                logger.warning(
                    f"Slow request detected: {request.method} {path} took {elapsed:.1f}s "
                    f"(threshold: {self.config.slow_request_threshold_s}s)"
                )

            # Add server load headers for debugging
            response.headers["X-Server-Active-Requests"] = str(self.metrics.active_requests)
            return response

        finally:
            self.metrics.active_requests -= 1
            self._semaphore.release()


# Global metrics instance (shared with AIOps endpoints)
flood_metrics = FloodProtectionMetrics()
