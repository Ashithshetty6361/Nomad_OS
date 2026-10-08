"""
Production Circuit Breaker for NomadOS.
Prevents cascading failures by detecting repeated external service failures
and short-circuiting requests until the service recovers.

States:
  CLOSED    → Normal operation, requests pass through
  OPEN      → Service failing, requests immediately rejected with fallback
  HALF_OPEN → Recovery probe: limited requests allowed to test if service is back
"""
import time
import threading
from enum import Enum
from typing import Dict, Optional, Tuple
from dataclasses import dataclass, field
from app.core.logging import logger


class CircuitState(str, Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"


@dataclass
class CircuitMetrics:
    """Tracks circuit breaker metrics for observability / AIOps dashboard."""
    total_requests: int = 0
    total_failures: int = 0
    total_successes: int = 0
    total_rejected: int = 0
    total_circuit_opens: int = 0
    total_circuit_closes: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    last_state_change_time: Optional[float] = None


@dataclass
class CircuitBreakerConfig:
    """Configuration for a single circuit breaker instance."""
    failure_threshold: int = 5          # Consecutive failures before opening
    recovery_timeout_s: float = 60.0    # Seconds before attempting half-open probe
    success_threshold: int = 2          # Successes in half-open before closing
    half_open_max_calls: int = 3        # Max concurrent calls allowed in half-open


class ServiceCircuit:
    """
    Circuit breaker for a single external service.
    Thread-safe via a reentrant lock.
    """

    def __init__(self, service_name: str, config: Optional[CircuitBreakerConfig] = None):
        self.service_name = service_name
        self.config = config or CircuitBreakerConfig()
        self._state = CircuitState.CLOSED
        self._consecutive_failures = 0
        self._half_open_successes = 0
        self._half_open_calls = 0
        self._last_failure_time: float = 0.0
        self._lock = threading.RLock()
        self.metrics = CircuitMetrics()

    @property
    def state(self) -> CircuitState:
        with self._lock:
            if self._state == CircuitState.OPEN:
                # Check if recovery timeout has elapsed → transition to HALF_OPEN
                if time.time() - self._last_failure_time >= self.config.recovery_timeout_s:
                    self._transition_to(CircuitState.HALF_OPEN)
            return self._state

    def _transition_to(self, new_state: CircuitState):
        """Internal state transition with logging and metrics."""
        old_state = self._state
        self._state = new_state
        self.metrics.last_state_change_time = time.time()

        if new_state == CircuitState.OPEN:
            self.metrics.total_circuit_opens += 1
            logger.warning(
                f"🔴 Circuit OPENED for [{self.service_name}] after "
                f"{self._consecutive_failures} consecutive failures. "
                f"Recovery probe in {self.config.recovery_timeout_s}s."
            )
        elif new_state == CircuitState.HALF_OPEN:
            self._half_open_successes = 0
            self._half_open_calls = 0
            logger.info(
                f"🟡 Circuit HALF-OPEN for [{self.service_name}]. "
                f"Allowing {self.config.half_open_max_calls} probe requests."
            )
        elif new_state == CircuitState.CLOSED:
            self._consecutive_failures = 0
            self._half_open_successes = 0
            self.metrics.total_circuit_closes += 1
            logger.info(f"🟢 Circuit CLOSED for [{self.service_name}]. Service recovered.")

    def allow_request(self) -> Tuple[bool, str]:
        """
        Determines if the request should be allowed through.
        Returns: (allowed: bool, reason: str)
        """
        with self._lock:
            current = self.state  # Triggers OPEN→HALF_OPEN check
            self.metrics.total_requests += 1

            if current == CircuitState.CLOSED:
                return True, "circuit_closed"

            elif current == CircuitState.OPEN:
                self.metrics.total_rejected += 1
                retry_after = max(
                    1,
                    int(self._last_failure_time + self.config.recovery_timeout_s - time.time())
                )
                return False, f"circuit_open:retry_after={retry_after}"

            elif current == CircuitState.HALF_OPEN:
                if self._half_open_calls < self.config.half_open_max_calls:
                    self._half_open_calls += 1
                    return True, "circuit_half_open_probe"
                else:
                    self.metrics.total_rejected += 1
                    return False, "circuit_half_open_at_capacity"

        return False, "unknown_state"

    def record_success(self):
        """Records a successful response from the external service."""
        with self._lock:
            self.metrics.total_successes += 1
            self.metrics.last_success_time = time.time()

            if self._state == CircuitState.HALF_OPEN:
                self._half_open_successes += 1
                if self._half_open_successes >= self.config.success_threshold:
                    self._transition_to(CircuitState.CLOSED)
            elif self._state == CircuitState.CLOSED:
                # Reset consecutive failure counter on success
                self._consecutive_failures = 0

    def record_failure(self):
        """Records a failed response from the external service."""
        with self._lock:
            self._consecutive_failures += 1
            self._last_failure_time = time.time()
            self.metrics.total_failures += 1
            self.metrics.last_failure_time = time.time()

            if self._state == CircuitState.HALF_OPEN:
                # Probe failed → reopen circuit
                self._transition_to(CircuitState.OPEN)
            elif self._state == CircuitState.CLOSED:
                if self._consecutive_failures >= self.config.failure_threshold:
                    self._transition_to(CircuitState.OPEN)

    def get_status(self) -> Dict:
        """Returns current status for the AIOps dashboard."""
        current = self.state
        return {
            "service": self.service_name,
            "state": current.value,
            "consecutive_failures": self._consecutive_failures,
            "config": {
                "failure_threshold": self.config.failure_threshold,
                "recovery_timeout_s": self.config.recovery_timeout_s,
                "success_threshold": self.config.success_threshold
            },
            "metrics": {
                "total_requests": self.metrics.total_requests,
                "total_failures": self.metrics.total_failures,
                "total_successes": self.metrics.total_successes,
                "total_rejected": self.metrics.total_rejected,
                "total_circuit_opens": self.metrics.total_circuit_opens,
                "total_circuit_closes": self.metrics.total_circuit_closes,
                "last_failure_time": self.metrics.last_failure_time,
                "last_success_time": self.metrics.last_success_time
            }
        }

    def force_open(self):
        """Manually opens circuit (useful for maintenance windows)."""
        with self._lock:
            self._last_failure_time = time.time()
            self._transition_to(CircuitState.OPEN)

    def force_close(self):
        """Manually closes circuit (useful after maintenance)."""
        with self._lock:
            self._transition_to(CircuitState.CLOSED)


class CircuitBreakerRegistry:
    """
    Central registry of all circuit breakers.
    One circuit per external service.
    """

    def __init__(self):
        self._circuits: Dict[str, ServiceCircuit] = {}
        self._lock = threading.Lock()

    def get_or_create(
        self, 
        service_name: str, 
        config: Optional[CircuitBreakerConfig] = None
    ) -> ServiceCircuit:
        with self._lock:
            if service_name not in self._circuits:
                self._circuits[service_name] = ServiceCircuit(
                    service_name, config or CircuitBreakerConfig()
                )
            return self._circuits[service_name]

    def get_all_status(self) -> list:
        """Returns status of all registered circuits for AIOps."""
        with self._lock:
            return [circuit.get_status() for circuit in self._circuits.values()]

    def get_circuit(self, service_name: str) -> Optional[ServiceCircuit]:
        return self._circuits.get(service_name)


# Global singleton registry
circuit_registry = CircuitBreakerRegistry()

# Pre-register known service circuits with tuned configs
llm_circuit = circuit_registry.get_or_create("llm_service", CircuitBreakerConfig(
    failure_threshold=5,
    recovery_timeout_s=60.0,
    success_threshold=2,
    half_open_max_calls=3
))

gemini_circuit = circuit_registry.get_or_create("gemini_api", CircuitBreakerConfig(
    failure_threshold=3,
    recovery_timeout_s=45.0,
    success_threshold=2,
    half_open_max_calls=2
))

ollama_circuit = circuit_registry.get_or_create("ollama_local", CircuitBreakerConfig(
    failure_threshold=3,
    recovery_timeout_s=30.0,
    success_threshold=2,
    half_open_max_calls=2
))

uber_circuit = circuit_registry.get_or_create("uber_api", CircuitBreakerConfig(
    failure_threshold=5,
    recovery_timeout_s=90.0,
    success_threshold=3,
    half_open_max_calls=2
))

