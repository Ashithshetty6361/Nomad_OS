"""
Global FastAPI Exception Handlers for NomadOS.
Ensures every error returns a consistent, structured JSON response
with correlation ID, error code, and retry guidance.

Never crashes the whole application because one component failed.
"""
import traceback
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from app.core.exceptions import (
    NomadException,
    CircuitOpenError,
    RateLimitExceededError,
    FloodProtectionError,
    GracefulDegradationError,
    TripNotFoundError,
    ExternalServiceTimeoutError,
    ValidationFailedError
)
from app.core.logging import logger, correlation_id_ctx


def _build_error_response(
    status_code: int,
    code: str,
    message: str,
    retry_after: int = 0,
    details: dict = None
) -> JSONResponse:
    """Builds a consistent error response body."""
    body = {
        "error": True,
        "code": code,
        "message": message,
        "correlation_id": correlation_id_ctx.get("unknown")
    }
    if retry_after > 0:
        body["retry_after"] = retry_after
    if details:
        body["details"] = details

    headers = {}
    if retry_after > 0:
        headers["Retry-After"] = str(retry_after)

    return JSONResponse(status_code=status_code, content=body, headers=headers)


def register_exception_handlers(app: FastAPI):
    """Registers all global exception handlers on the FastAPI app instance."""

    @app.exception_handler(CircuitOpenError)
    async def handle_circuit_open(request: Request, exc: CircuitOpenError):
        logger.warning(f"Circuit open: {exc.service_name} — {exc.message}")
        return _build_error_response(
            status_code=503,
            code="CIRCUIT_OPEN",
            message="AI service is temporarily unavailable. Your trip data is safe. Please try again shortly.",
            retry_after=exc.retry_after
        )

    @app.exception_handler(RateLimitExceededError)
    async def handle_rate_limit(request: Request, exc: RateLimitExceededError):
        logger.warning(f"Rate limit: {exc.endpoint} — {exc.message}")
        return _build_error_response(
            status_code=429,
            code="RATE_LIMIT_EXCEEDED",
            message=f"Too many requests. Please wait {exc.retry_after} seconds before trying again.",
            retry_after=exc.retry_after
        )

    @app.exception_handler(FloodProtectionError)
    async def handle_flood(request: Request, exc: FloodProtectionError):
        logger.warning(f"Flood protection triggered: {exc.message}")
        return _build_error_response(
            status_code=503,
            code="SERVER_OVERLOADED",
            message="The server is handling a high volume of requests. Please try again in a moment.",
            retry_after=exc.retry_after
        )

    @app.exception_handler(GracefulDegradationError)
    async def handle_degradation(request: Request, exc: GracefulDegradationError):
        logger.info(f"Graceful degradation: {exc.feature}")
        return _build_error_response(
            status_code=503,
            code="GRACEFUL_DEGRADATION",
            message=exc.message,
            retry_after=15
        )

    @app.exception_handler(TripNotFoundError)
    async def handle_trip_not_found(request: Request, exc: TripNotFoundError):
        return _build_error_response(
            status_code=404,
            code="TRIP_NOT_FOUND",
            message=exc.message
        )

    @app.exception_handler(ExternalServiceTimeoutError)
    async def handle_timeout(request: Request, exc: ExternalServiceTimeoutError):
        logger.error(f"External timeout: {exc.service_name} ({exc.timeout_seconds}s)")
        return _build_error_response(
            status_code=504,
            code="EXTERNAL_TIMEOUT",
            message="An external service took too long to respond. Your data is safe. Please try again.",
            retry_after=5
        )

    @app.exception_handler(ValidationFailedError)
    async def handle_validation(request: Request, exc: ValidationFailedError):
        return _build_error_response(
            status_code=422,
            code="VALIDATION_FAILED",
            message=exc.message,
            details={"field": exc.field}
        )

    @app.exception_handler(NomadException)
    async def handle_nomad_exception(request: Request, exc: NomadException):
        logger.error(f"NomadException [{exc.code}]: {exc.message}")
        return _build_error_response(
            status_code=exc.http_status,
            code=exc.code,
            message="An internal error occurred. Our team has been notified. Your trip data is safe."
        )

    @app.exception_handler(RequestValidationError)
    async def handle_request_validation(request: Request, exc: RequestValidationError):
        """Converts Pydantic validation errors to human-readable messages."""
        errors = []
        for err in exc.errors():
            loc = " → ".join(str(l) for l in err.get("loc", []))
            msg = err.get("msg", "Invalid value")
            errors.append(f"{loc}: {msg}")

        return _build_error_response(
            status_code=422,
            code="REQUEST_VALIDATION_ERROR",
            message="Please check your input and try again.",
            details={"validation_errors": errors}
        )

    @app.exception_handler(HTTPException)
    async def handle_http_exception(request: Request, exc: HTTPException):
        """Wraps standard FastAPI HTTPExceptions in our consistent format."""
        return _build_error_response(
            status_code=exc.status_code,
            code=f"HTTP_{exc.status_code}",
            message=str(exc.detail) if isinstance(exc.detail, str) else "Request could not be processed."
        )

    @app.exception_handler(Exception)
    async def handle_unhandled(request: Request, exc: Exception):
        """
        Catch-all for unhandled exceptions.
        Logs the full traceback for debugging but returns a safe message to the client.
        """
        trace_id = correlation_id_ctx.get("unknown")
        logger.critical(
            f"UNHANDLED EXCEPTION [trace={trace_id}]: {type(exc).__name__}: {exc}\n"
            f"{traceback.format_exc()}"
        )
        return _build_error_response(
            status_code=500,
            code="INTERNAL_SERVER_ERROR",
            message=(
                "Something unexpected happened. Your trip data is safe. "
                f"If this persists, reference ID: {trace_id}"
            )
        )
