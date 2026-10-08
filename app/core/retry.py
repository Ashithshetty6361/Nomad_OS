"""
Exponential Backoff Retry with Jitter for NomadOS.
Retries transient failures (5xx, timeouts, connection errors) with
exponentially increasing delays and random jitter to prevent thundering herd.

Integrates with the circuit breaker — skips retry if circuit is OPEN.
"""
import asyncio
import random
import functools
import time
from typing import Optional, Tuple, Type, Set
from app.core.logging import logger


class RetryConfig:
    """Configuration for retry behavior."""
    def __init__(
        self,
        max_retries: int = 3,
        base_delay_s: float = 0.5,
        max_delay_s: float = 8.0,
        backoff_factor: float = 2.0,
        jitter_range: float = 0.2,
        retryable_exceptions: Optional[Tuple[Type[Exception], ...]] = None
    ):
        self.max_retries = max_retries
        self.base_delay_s = base_delay_s
        self.max_delay_s = max_delay_s
        self.backoff_factor = backoff_factor
        self.jitter_range = jitter_range
        # Default retryable exceptions
        self.retryable_exceptions = retryable_exceptions or (
            ConnectionError,
            TimeoutError,
            OSError,
        )


class RetryMetrics:
    """Tracks retry statistics for AIOps observability."""
    def __init__(self):
        self.total_attempts: int = 0
        self.total_retries: int = 0
        self.total_successes_after_retry: int = 0
        self.total_exhausted: int = 0  # All retries failed
        self.total_skipped_circuit_open: int = 0

    def to_dict(self) -> dict:
        return {
            "total_attempts": self.total_attempts,
            "total_retries": self.total_retries,
            "total_successes_after_retry": self.total_successes_after_retry,
            "total_exhausted": self.total_exhausted,
            "total_skipped_circuit_open": self.total_skipped_circuit_open,
            "retry_success_rate": (
                round(self.total_successes_after_retry / max(1, self.total_retries) * 100, 1)
            )
        }


# Global retry metrics
retry_metrics = RetryMetrics()


def calculate_delay(attempt: int, config: RetryConfig) -> float:
    """
    Calculates delay with exponential backoff + jitter.
    attempt=0: base_delay * 1.0 ± jitter
    attempt=1: base_delay * 2.0 ± jitter
    attempt=2: base_delay * 4.0 ± jitter
    """
    delay = config.base_delay_s * (config.backoff_factor ** attempt)
    delay = min(delay, config.max_delay_s)
    # Apply jitter: ±20% randomization
    jitter = delay * config.jitter_range
    delay = delay + random.uniform(-jitter, jitter)
    return max(0.1, delay)


def retry_async(config: Optional[RetryConfig] = None, circuit_name: Optional[str] = None):
    """
    Decorator for async functions with exponential backoff retry.
    
    Usage:
        @retry_async(config=RetryConfig(max_retries=3), circuit_name="llm_service")
        async def call_llm(...):
            ...
    """
    if config is None:
        config = RetryConfig()

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            last_exception = None
            retry_metrics.total_attempts += 1

            # Check circuit breaker if specified
            if circuit_name:
                from app.core.circuit_breaker import circuit_registry
                circuit = circuit_registry.get_circuit(circuit_name)
                if circuit:
                    allowed, reason = circuit.allow_request()
                    if not allowed:
                        retry_metrics.total_skipped_circuit_open += 1
                        logger.warning(
                            f"Retry skipped for {func.__name__}: circuit [{circuit_name}] is {reason}"
                        )
                        from app.core.exceptions import CircuitOpenError
                        raise CircuitOpenError(circuit_name)

            for attempt in range(config.max_retries + 1):
                try:
                    result = await func(*args, **kwargs)

                    # Record success with circuit breaker
                    if circuit_name:
                        from app.core.circuit_breaker import circuit_registry
                        circuit = circuit_registry.get_circuit(circuit_name)
                        if circuit:
                            circuit.record_success()

                    if attempt > 0:
                        retry_metrics.total_successes_after_retry += 1
                        logger.info(
                            f"✅ {func.__name__} succeeded after {attempt} retries"
                        )
                    return result

                except config.retryable_exceptions as e:
                    last_exception = e

                    # Record failure with circuit breaker
                    if circuit_name:
                        from app.core.circuit_breaker import circuit_registry
                        circuit = circuit_registry.get_circuit(circuit_name)
                        if circuit:
                            circuit.record_failure()

                    if attempt < config.max_retries:
                        delay = calculate_delay(attempt, config)
                        retry_metrics.total_retries += 1
                        logger.warning(
                            f"⚠️ {func.__name__} failed (attempt {attempt + 1}/{config.max_retries + 1}): "
                            f"{type(e).__name__}: {e}. Retrying in {delay:.2f}s..."
                        )
                        await asyncio.sleep(delay)

                        # Re-check circuit before retry
                        if circuit_name:
                            from app.core.circuit_breaker import circuit_registry
                            circuit = circuit_registry.get_circuit(circuit_name)
                            if circuit:
                                allowed, reason = circuit.allow_request()
                                if not allowed:
                                    retry_metrics.total_skipped_circuit_open += 1
                                    logger.warning(
                                        f"Retry aborted: circuit [{circuit_name}] opened during retry"
                                    )
                                    from app.core.exceptions import CircuitOpenError
                                    raise CircuitOpenError(circuit_name)
                    else:
                        retry_metrics.total_exhausted += 1
                        logger.error(
                            f"❌ {func.__name__} exhausted all {config.max_retries + 1} attempts. "
                            f"Last error: {type(e).__name__}: {e}"
                        )

                except Exception as e:
                    # Non-retryable exception — fail immediately
                    if circuit_name:
                        from app.core.circuit_breaker import circuit_registry
                        circuit = circuit_registry.get_circuit(circuit_name)
                        if circuit:
                            circuit.record_failure()
                    raise

            # All retries exhausted
            raise last_exception

        return wrapper
    return decorator


def retry_sync(config: Optional[RetryConfig] = None):
    """
    Decorator for synchronous functions with exponential backoff retry.
    """
    if config is None:
        config = RetryConfig()

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None

            for attempt in range(config.max_retries + 1):
                try:
                    return func(*args, **kwargs)
                except config.retryable_exceptions as e:
                    last_exception = e
                    if attempt < config.max_retries:
                        delay = calculate_delay(attempt, config)
                        logger.warning(
                            f"⚠️ {func.__name__} failed (attempt {attempt + 1}): "
                            f"{type(e).__name__}. Retrying in {delay:.2f}s..."
                        )
                        time.sleep(delay)
                    else:
                        logger.error(
                            f"❌ {func.__name__} exhausted all retries. Last: {e}"
                        )
                except Exception:
                    raise

            raise last_exception

        return wrapper
    return decorator
