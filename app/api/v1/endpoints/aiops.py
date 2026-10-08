"""
AIOps Monitoring & AI Engineering Dashboard API for NomadOS.
Provides real-time observability into token consumption, cost analytics,
circuit breaker states, cache performance, rate limiting, and server load.

These endpoints are intended for the Engineering Mode view only.
"""
from fastapi import APIRouter
from app.core.circuit_breaker import circuit_registry
from app.core.response_cache import response_cache
from app.core.retry import retry_metrics
from app.core.rate_limit import rate_limiter
from app.core.persistence import persistence
from app.config import settings

router = APIRouter()


# ============================================================
# Aggregated real-time metrics store (populated by LLM service)
# ============================================================
class AIOpsMetricsStore:
    """In-memory aggregator for AI engineering metrics."""
    def __init__(self):
        self.total_llm_calls: int = 0
        self.total_prompt_tokens: int = 0
        self.total_completion_tokens: int = 0
        self.total_cost_usd: float = 0.0
        self.total_cost_if_single_model_usd: float = 0.0
        self.avg_latency_ms: float = 0.0
        self._latencies: list = []
        self.calls_by_provider: dict = {}
        self.calls_by_task: dict = {}
        self.recent_requests: list = []  # Last 20 requests for trend chart

    def record_call(self, telemetry: dict):
        """Records a single LLM call's telemetry."""
        self.total_llm_calls += 1
        self.total_prompt_tokens += telemetry.get("prompt_tokens", 0)
        self.total_completion_tokens += telemetry.get("completion_tokens", 0)
        self.total_cost_usd += telemetry.get("cost_usd", 0.0)

        # Track what a single-model approach would cost (always use Sonnet pricing)
        single_model_cost = (
            (telemetry.get("prompt_tokens", 0) / 1000.0) * settings.SONNET_INPUT_COST_PER_1K +
            (telemetry.get("completion_tokens", 0) / 1000.0) * settings.SONNET_OUTPUT_COST_PER_1K
        )
        self.total_cost_if_single_model_usd += single_model_cost

        # Track latency
        latency = telemetry.get("latency_ms", 0.0)
        self._latencies.append(latency)
        if len(self._latencies) > 100:
            self._latencies = self._latencies[-100:]
        self.avg_latency_ms = round(sum(self._latencies) / len(self._latencies), 2)

        # Track by provider
        provider = telemetry.get("provider", "unknown")
        self.calls_by_provider[provider] = self.calls_by_provider.get(provider, 0) + 1

        # Track by task type
        task = telemetry.get("task_type", "unknown")
        self.calls_by_task[task] = self.calls_by_task.get(task, 0) + 1

        # Recent requests for trend chart (keep last 20)
        self.recent_requests.append({
            "task_type": task,
            "provider": provider,
            "model_id": telemetry.get("model_id", ""),
            "prompt_tokens": telemetry.get("prompt_tokens", 0),
            "completion_tokens": telemetry.get("completion_tokens", 0),
            "cost_usd": telemetry.get("cost_usd", 0.0),
            "latency_ms": latency,
            "cache_hit": telemetry.get("cache_hit", False)
        })
        if len(self.recent_requests) > 20:
            self.recent_requests = self.recent_requests[-20:]

    def to_dict(self) -> dict:
        savings = round(self.total_cost_if_single_model_usd - self.total_cost_usd, 6)
        savings_pct = 0.0
        if self.total_cost_if_single_model_usd > 0:
            savings_pct = round(savings / self.total_cost_if_single_model_usd * 100, 1)

        return {
            "total_llm_calls": self.total_llm_calls,
            "total_prompt_tokens": self.total_prompt_tokens,
            "total_completion_tokens": self.total_completion_tokens,
            "total_tokens": self.total_prompt_tokens + self.total_completion_tokens,
            "total_cost_usd": round(self.total_cost_usd, 6),
            "total_cost_if_single_model_usd": round(self.total_cost_if_single_model_usd, 6),
            "cost_savings_usd": savings,
            "cost_savings_pct": savings_pct,
            "avg_latency_ms": self.avg_latency_ms,
            "calls_by_provider": self.calls_by_provider,
            "calls_by_task": self.calls_by_task,
        }


# Global singleton
aiops_metrics = AIOpsMetricsStore()


# ============================================================
# API Endpoints
# ============================================================

@router.get(
    "/aiops/metrics",
    summary="Real-Time AI Engineering Metrics",
    tags=["AIOps"]
)
async def get_aiops_metrics():
    """
    Returns comprehensive AI engineering metrics including:
    - Token consumption (prompt/completion/total)
    - Cost analytics with savings vs single-model approach
    - Average latency
    - Calls by provider and task type
    """
    return {
        "ai_metrics": aiops_metrics.to_dict(),
        "cache_stats": response_cache.get_stats(),
        "retry_stats": retry_metrics.to_dict(),
    }


@router.get(
    "/aiops/circuit-status",
    summary="Circuit Breaker Status for All Services",
    tags=["AIOps"]
)
async def get_circuit_status():
    """Returns current state of all circuit breakers."""
    return {
        "circuits": circuit_registry.get_all_status()
    }


@router.get(
    "/aiops/cache-stats",
    summary="Response Cache Performance",
    tags=["AIOps"]
)
async def get_cache_stats():
    """Returns cache hit/miss ratio, token savings, and utilization."""
    return response_cache.get_stats()


@router.get(
    "/aiops/cost-report",
    summary="Detailed Cost Analytics Report",
    tags=["AIOps"]
)
async def get_cost_report():
    """
    Detailed cost report showing:
    - Actual cost vs hypothetical single-model cost
    - Savings from multi-tier routing
    - Savings from response caching
    - Per-provider and per-task breakdown
    """
    cache_stats = response_cache.get_stats()
    metrics = aiops_metrics.to_dict()

    return {
        "cost_summary": {
            "actual_cost_usd": metrics["total_cost_usd"],
            "hypothetical_single_model_cost_usd": metrics["total_cost_if_single_model_usd"],
            "savings_from_routing_usd": metrics["cost_savings_usd"],
            "savings_from_routing_pct": metrics["cost_savings_pct"],
            "savings_from_caching_usd": round(cache_stats["estimated_cost_saved_usd"], 6),
            "tokens_saved_by_caching": cache_stats["estimated_tokens_saved"],
            "total_savings_usd": round(
                metrics["cost_savings_usd"] + cache_stats["estimated_cost_saved_usd"], 6
            ),
        },
        "breakdown_by_provider": metrics["calls_by_provider"],
        "breakdown_by_task": metrics["calls_by_task"],
        "recent_requests": aiops_metrics.recent_requests
    }


@router.get(
    "/aiops/health-deep",
    summary="Deep Health Check (LLM, DB, Vector Store)",
    tags=["AIOps"]
)
async def deep_health_check():
    """
    Deep health probe that checks:
    - LLM service connectivity (circuit status)
    - Database (SQLite) connectivity
    - Vector store (ChromaDB) status
    """
    # Check LLM circuits
    circuits = circuit_registry.get_all_status()
    llm_healthy = all(c["state"] != "open" for c in circuits)

    # Check SQLite
    db_healthy = False
    try:
        stats = persistence.get_stats()
        db_healthy = True
    except Exception:
        stats = {}

    # Check ChromaDB
    chroma_healthy = False
    try:
        from app.services.rag_service import rag_service
        chroma_count = rag_service.collection.count() if rag_service.collection else 0
        chroma_healthy = True
    except Exception:
        chroma_count = 0

    overall = llm_healthy and db_healthy and chroma_healthy

    return {
        "status": "healthy" if overall else "degraded",
        "components": {
            "llm_service": {
                "healthy": llm_healthy,
                "circuits": circuits
            },
            "database": {
                "healthy": db_healthy,
                "stats": stats
            },
            "vector_store": {
                "healthy": chroma_healthy,
                "document_count": chroma_count
            }
        }
    }


@router.get(
    "/aiops/trend",
    summary="Recent Request Trend Data",
    tags=["AIOps"]
)
async def get_trend_data():
    """Returns the last 20 LLM requests for the cost/token trend chart."""
    return {
        "recent_requests": aiops_metrics.recent_requests,
        "total_calls": aiops_metrics.total_llm_calls
    }
