"""
Domain exceptions for NomadOS multi-agent platform.
Extended with resilience-specific exceptions for circuit breakers,
timeouts, rate limiting, and data validation.
"""


class NomadException(Exception):
    """Base exception for NomadOS."""
    def __init__(self, message: str, code: str = "INTERNAL_ERROR", http_status: int = 500):
        super().__init__(message)
        self.message = message
        self.code = code
        self.http_status = http_status


class AgentExecutionError(NomadException):
    """Raised when an individual agent fails during execution."""
    def __init__(self, agent_name: str, reason: str):
        super().__init__(
            f"Agent [{agent_name}] execution failed: {reason}",
            code="AGENT_ERROR",
            http_status=500
        )
        self.agent_name = agent_name


class LLMServiceError(NomadException):
    """Raised when AWS Bedrock or LLM provider invocation fails."""
    def __init__(self, provider: str, details: str = ""):
        super().__init__(
            f"LLM Provider [{provider}] error: {details}",
            code="LLM_PROVIDER_ERROR",
            http_status=502
        )
        self.provider = provider


class RAGRetrievalError(NomadException):
    """Raised when vector retrieval encounters an error."""
    def __init__(self, query: str, details: str):
        super().__init__(
            f"RAG retrieval failed for query '{query}': {details}",
            code="RAG_ERROR",
            http_status=500
        )


class InvalidPlanStateError(NomadException):
    """Raised when the deterministic planner encounters an invalid state transition."""
    def __init__(self, state_name: str, reason: str):
        super().__init__(
            f"Invalid state transition at [{state_name}]: {reason}",
            code="PLANNER_STATE_ERROR",
            http_status=400
        )


# ============================================================
# Production Resilience Exceptions
# ============================================================

class CircuitOpenError(NomadException):
    """Raised when a circuit breaker is OPEN and the service is unavailable."""
    def __init__(self, service_name: str, retry_after: int = 30):
        super().__init__(
            f"Service [{service_name}] is temporarily unavailable. "
            f"The system detected repeated failures and is protecting itself. "
            f"Please try again in {retry_after} seconds.",
            code="CIRCUIT_OPEN",
            http_status=503
        )
        self.service_name = service_name
        self.retry_after = retry_after


class ExternalServiceTimeoutError(NomadException):
    """Raised when an external API call exceeds the configured timeout."""
    def __init__(self, service_name: str, timeout_seconds: float):
        super().__init__(
            f"External service [{service_name}] did not respond within {timeout_seconds}s.",
            code="EXTERNAL_TIMEOUT",
            http_status=504
        )
        self.service_name = service_name
        self.timeout_seconds = timeout_seconds


class RateLimitExceededError(NomadException):
    """Raised when a client exceeds the configured rate limit."""
    def __init__(self, endpoint: str, limit: int, window_seconds: int, retry_after: int = 60):
        super().__init__(
            f"Rate limit exceeded on [{endpoint}]. "
            f"Maximum {limit} requests per {window_seconds} seconds.",
            code="RATE_LIMIT_EXCEEDED",
            http_status=429
        )
        self.endpoint = endpoint
        self.limit = limit
        self.retry_after = retry_after


class TripNotFoundError(NomadException):
    """Raised when a requested trip does not exist."""
    def __init__(self, trip_id: str):
        super().__init__(
            f"Trip [{trip_id}] not found.",
            code="TRIP_NOT_FOUND",
            http_status=404
        )
        self.trip_id = trip_id


class ValidationFailedError(NomadException):
    """Raised when input validation fails with a human-readable message."""
    def __init__(self, field: str, reason: str):
        super().__init__(
            f"Validation failed for '{field}': {reason}",
            code="VALIDATION_FAILED",
            http_status=422
        )
        self.field = field


class FloodProtectionError(NomadException):
    """Raised when the server is under excessive load."""
    def __init__(self, retry_after: int = 10):
        super().__init__(
            "The server is experiencing high traffic. "
            "Your request has been queued but could not be processed in time. "
            "Please try again shortly.",
            code="SERVER_OVERLOADED",
            http_status=503
        )
        self.retry_after = retry_after


class GracefulDegradationError(NomadException):
    """Raised when non-essential features are disabled under heavy load."""
    def __init__(self, feature: str):
        super().__init__(
            f"The [{feature}] feature is temporarily unavailable due to high demand. "
            f"Core trip planning features remain fully operational.",
            code="GRACEFUL_DEGRADATION",
            http_status=503
        )
        self.feature = feature
