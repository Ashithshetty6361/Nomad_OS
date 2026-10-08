"""
Observability metrics: Latency tracking timers and AWS Bedrock token cost calculators.
"""
import time
from typing import Dict, Any, Optional
from pydantic import BaseModel, Field
from app.config import settings


class ExecutionMetrics(BaseModel):
    """Execution telemetry captured across agent runs."""
    trace_id: str
    total_latency_ms: float = 0.0
    step_latencies: Dict[str, float] = Field(default_factory=dict)
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0
    models_used: Dict[str, int] = Field(default_factory=dict)
    savings_vs_single_model_usd: float = 0.0


def calculate_bedrock_cost(model_id: str, prompt_tokens: int, completion_tokens: int) -> float:
    """
    Calculates estimated cost in USD based on AWS Bedrock pricing tiers.
    """
    if "haiku" in model_id.lower() or "micro" in model_id.lower():
        input_cost = (prompt_tokens / 1000.0) * settings.HAIKU_INPUT_COST_PER_1K
        output_cost = (completion_tokens / 1000.0) * settings.HAIKU_OUTPUT_COST_PER_1K
    else:
        # Default to Claude 3.5 Sonnet / Reasoning model
        input_cost = (prompt_tokens / 1000.0) * settings.SONNET_INPUT_COST_PER_1K
        output_cost = (completion_tokens / 1000.0) * settings.SONNET_OUTPUT_COST_PER_1K
        
    return round(input_cost + output_cost, 6)


class Timer:
    """Context manager for accurate latency tracking in milliseconds."""
    def __init__(self):
        self.start = time.perf_counter()
        self.end = None
        self._latency_ms = 0.0

    def __enter__(self):
        self.start = time.perf_counter()
        return self

    def __exit__(self, *args):
        self.end = time.perf_counter()
        self._latency_ms = round((self.end - self.start) * 1000.0, 2)

    @property
    def latency_ms(self) -> float:
        if self.end is not None:
            return self._latency_ms
        return round((time.perf_counter() - self.start) * 1000.0, 2)

    @property
    def elapsed_ms(self) -> float:
        return self.latency_ms
