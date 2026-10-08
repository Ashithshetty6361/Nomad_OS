"""
Abstract Base Agent interface for all specialized NomadOS agents.
"""
from abc import ABC, abstractmethod
from typing import Dict, Any, Tuple
from app.models.state import OrchestrationState
from app.core.logging import logger
from app.core.metrics import Timer
from app.core.exceptions import AgentExecutionError


class BaseAgent(ABC):
    """
    Standard interface for modular AI agents.
    Enforces strict Pydantic state contracts, error isolation, and telemetry collection.
    """
    def __init__(self, name: str, task_type: str):
        self.name = name
        self.task_type = task_type

    @abstractmethod
    async def run(self, state: OrchestrationState) -> OrchestrationState:
        """Executes the specialized agent logic and updates the shared state."""
        pass

    async def execute(self, state: OrchestrationState) -> OrchestrationState:
        """
        Wrapper handling structured logging, latency measurement, and failure isolation.
        """
        logger.info(f"Agent [{self.name}] starting execution for trace_id={state.trace_id}", extra={"agent": self.name})
        
        with Timer() as timer:
            try:
                updated_state = await self.run(state)
                updated_state.completed_steps.append(self.name)
                updated_state.step_latencies[self.name] = timer.latency_ms
                logger.info(
                    f"Agent [{self.name}] completed successfully in {timer.latency_ms}ms",
                    extra={"agent": self.name, "latency_ms": timer.latency_ms}
                )
                return updated_state
            except Exception as e:
                logger.error(f"Agent [{self.name}] failed: {str(e)}", extra={"agent": self.name})
                state.errors.append(f"{self.name}: {str(e)}")
                raise AgentExecutionError(self.name, str(e))
