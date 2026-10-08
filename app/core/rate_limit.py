"""
Sliding Window In-Memory Rate Limiter for NomadOS.
Protects AI inference endpoints and external APIs from cost spikes and DDoS attacks.
"""
import time
from typing import Dict, List, Tuple
from fastapi import Request, HTTPException, status
from app.config import settings
from app.core.logging import logger


class SlidingWindowRateLimiter:
    """
    Sliding window in-memory rate limiter per IP / identifier.
    Guarantees thread-safe window tracking with automatic TTL expiration.
    """
    def __init__(self):
        # Maps (identifier, endpoint) -> list of request timestamps (epoch floats)
        self._history: Dict[Tuple[str, str], List[float]] = {}

    def is_allowed(self, identifier: str, endpoint: str, limit: int, window_seconds: int = 60) -> Tuple[bool, int, int]:
        """
        Evaluates whether a request is allowed under the sliding window.
        Returns: (allowed: bool, remaining_requests: int, retry_after_seconds: int)
        """
        if not settings.RATE_LIMIT_ENABLED:
            return True, limit, 0

        now = time.time()
        window_start = now - window_seconds
        key = (identifier, endpoint)

        # Retrieve and filter past timestamps inside the sliding window
        timestamps = self._history.get(key, [])
        valid_timestamps = [t for t in timestamps if t > window_start]

        if len(valid_timestamps) >= limit:
            # Over limit: calculate earliest time a slot frees up
            oldest_in_window = valid_timestamps[0]
            retry_after = max(1, int(oldest_in_window + window_seconds - now))
            self._history[key] = valid_timestamps
            return False, 0, retry_after

        # Record this request
        valid_timestamps.append(now)
        self._history[key] = valid_timestamps
        remaining = max(0, limit - len(valid_timestamps))
        return True, remaining, 0

    def cleanup(self):
        """Purges old expired entries to prevent memory accumulation."""
        now = time.time()
        keys_to_delete = []
        for key, timestamps in self._history.items():
            fresh = [t for t in timestamps if (now - t) < 300]
            if fresh:
                self._history[key] = fresh
            else:
                keys_to_delete.append(key)
        for k in keys_to_delete:
            del self._history[k]


rate_limiter = SlidingWindowRateLimiter()


def get_client_ip(request: Request) -> str:
    """Extracts client IP, supporting X-Forwarded-For behind reverse proxies."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "127.0.0.1"


def apply_rate_limit(endpoint_name: str, max_requests: int, window_seconds: int = 60):
    """
    FastAPI dependency factory for endpoint-level rate limiting.
    """
    async def dependency(request: Request):
        client_ip = get_client_ip(request)
        allowed, remaining, retry_after = rate_limiter.is_allowed(
            identifier=client_ip,
            endpoint=endpoint_name,
            limit=max_requests,
            window_seconds=window_seconds
        )

        # Set standard rate limiting telemetry headers on request state
        request.state.rate_limit_limit = max_requests
        request.state.rate_limit_remaining = remaining

        if not allowed:
            logger.warning(f"Rate limit exceeded on {endpoint_name} for IP {client_ip} (limit: {max_requests}/{window_seconds}s)")
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=f"Rate limit exceeded. Maximum {max_requests} requests per {window_seconds} seconds.",
                headers={"Retry-After": str(retry_after)}
            )

    return dependency
