"""
LRU + TTL In-Memory Response Cache for NomadOS.
Caches LLM responses to avoid redundant API calls for identical/similar queries.
Provides cache hit/miss metrics for the AIOps dashboard.
"""
import time
import hashlib
import threading
from typing import Dict, Any, Optional, Tuple
from collections import OrderedDict
from dataclasses import dataclass
from app.core.logging import logger


@dataclass
class CacheEntry:
    """A single cached response with TTL."""
    key: str
    response: Dict[str, Any]
    telemetry: Dict[str, Any]
    created_at: float
    ttl_seconds: float
    hit_count: int = 0

    @property
    def is_expired(self) -> bool:
        return (time.time() - self.created_at) > self.ttl_seconds


class CacheMetrics:
    """Tracks cache performance for AIOps dashboard."""
    def __init__(self):
        self.total_lookups: int = 0
        self.total_hits: int = 0
        self.total_misses: int = 0
        self.total_evictions: int = 0
        self.total_expired: int = 0
        self.total_inserts: int = 0
        self.estimated_tokens_saved: int = 0
        self.estimated_cost_saved_usd: float = 0.0

    @property
    def hit_rate(self) -> float:
        if self.total_lookups == 0:
            return 0.0
        return round(self.total_hits / self.total_lookups * 100, 2)

    def to_dict(self) -> dict:
        return {
            "total_lookups": self.total_lookups,
            "total_hits": self.total_hits,
            "total_misses": self.total_misses,
            "hit_rate_pct": self.hit_rate,
            "total_evictions": self.total_evictions,
            "total_expired": self.total_expired,
            "total_inserts": self.total_inserts,
            "estimated_tokens_saved": self.estimated_tokens_saved,
            "estimated_cost_saved_usd": round(self.estimated_cost_saved_usd, 6)
        }


# TTL presets per task type (seconds)
TTL_BY_TASK_TYPE = {
    "context_parsing": 120,         # Intent extraction — short TTL
    "discovery_filtering": 300,     # Discovery results — moderate TTL
    "enrichment_extraction": 300,   # Enrichment tips — moderate TTL
    "booking_reasoning": 0,         # Never cache — always fresh itineraries
}


class ResponseCache:
    """
    Thread-safe LRU + TTL in-memory response cache.
    Max entries enforced via LRU eviction.
    """

    def __init__(self, max_entries: int = 500):
        self.max_entries = max_entries
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._lock = threading.Lock()
        self.metrics = CacheMetrics()

    @staticmethod
    def _make_key(system_prompt: str, user_prompt: str, task_type: str) -> str:
        """
        Generates a deterministic cache key from prompt content.
        Uses SHA-256 hash of the combined prompts + task type.
        """
        content = f"{task_type}::{system_prompt.strip()}::{user_prompt.strip()}"
        return hashlib.sha256(content.encode("utf-8")).hexdigest()[:32]

    def get(
        self, 
        system_prompt: str, 
        user_prompt: str, 
        task_type: str
    ) -> Optional[Tuple[Dict[str, Any], Dict[str, Any]]]:
        """
        Looks up a cached response.
        Returns (response, telemetry) if hit, None if miss.
        """
        # Never cache booking_reasoning
        if TTL_BY_TASK_TYPE.get(task_type, 0) == 0:
            self.metrics.total_lookups += 1
            self.metrics.total_misses += 1
            return None

        key = self._make_key(system_prompt, user_prompt, task_type)

        with self._lock:
            self.metrics.total_lookups += 1

            if key in self._cache:
                entry = self._cache[key]

                if entry.is_expired:
                    # Expired entry — remove and count as miss
                    del self._cache[key]
                    self.metrics.total_expired += 1
                    self.metrics.total_misses += 1
                    logger.debug(f"Cache EXPIRED for key={key[:12]}... task={task_type}")
                    return None

                # Cache HIT — move to end (most recently used)
                self._cache.move_to_end(key)
                entry.hit_count += 1
                self.metrics.total_hits += 1

                # Track token savings
                cached_tokens = (
                    entry.telemetry.get("prompt_tokens", 0) +
                    entry.telemetry.get("completion_tokens", 0)
                )
                self.metrics.estimated_tokens_saved += cached_tokens
                self.metrics.estimated_cost_saved_usd += entry.telemetry.get("cost_usd", 0.0)

                # Return cached response with modified telemetry
                cached_telemetry = {**entry.telemetry, "cache_hit": True, "cache_key": key[:12]}
                logger.info(
                    f"Cache HIT for task={task_type} key={key[:12]}... "
                    f"(hit_count={entry.hit_count}, tokens_saved={cached_tokens})"
                )
                return entry.response, cached_telemetry

            # Cache MISS
            self.metrics.total_misses += 1
            return None

    def put(
        self,
        system_prompt: str,
        user_prompt: str,
        task_type: str,
        response: Dict[str, Any],
        telemetry: Dict[str, Any]
    ):
        """Stores a response in the cache with appropriate TTL."""
        ttl = TTL_BY_TASK_TYPE.get(task_type, 0)
        if ttl == 0:
            return  # Don't cache booking_reasoning

        key = self._make_key(system_prompt, user_prompt, task_type)

        with self._lock:
            # Evict LRU entries if at capacity
            while len(self._cache) >= self.max_entries:
                evicted_key, _ = self._cache.popitem(last=False)
                self.metrics.total_evictions += 1
                logger.debug(f"Cache LRU eviction: key={evicted_key[:12]}...")

            self._cache[key] = CacheEntry(
                key=key,
                response=response,
                telemetry=telemetry,
                created_at=time.time(),
                ttl_seconds=ttl
            )
            self.metrics.total_inserts += 1
            logger.debug(f"Cache INSERT for task={task_type} key={key[:12]}... ttl={ttl}s")

    def invalidate(self, system_prompt: str, user_prompt: str, task_type: str):
        """Explicitly invalidates a specific cache entry."""
        key = self._make_key(system_prompt, user_prompt, task_type)
        with self._lock:
            if key in self._cache:
                del self._cache[key]

    def clear(self):
        """Clears the entire cache."""
        with self._lock:
            self._cache.clear()

    def cleanup_expired(self):
        """Removes all expired entries. Called periodically."""
        with self._lock:
            expired_keys = [
                k for k, v in self._cache.items() if v.is_expired
            ]
            for k in expired_keys:
                del self._cache[k]
                self.metrics.total_expired += 1
            if expired_keys:
                logger.debug(f"Cache cleanup: removed {len(expired_keys)} expired entries")

    @property
    def size(self) -> int:
        return len(self._cache)

    def get_stats(self) -> dict:
        """Returns cache stats for AIOps dashboard."""
        stats = self.metrics.to_dict()
        stats["current_entries"] = self.size
        stats["max_entries"] = self.max_entries
        stats["utilization_pct"] = round(self.size / max(1, self.max_entries) * 100, 1)
        return stats


# Global singleton
response_cache = ResponseCache(max_entries=500)
