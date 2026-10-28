"""Token Bucket Rate Limiter implementing Enterprise API Gateway Policy.

Directly enforces specifications from data/raw/engineering/api_rate_limiting_spec.md:
  - L1_PUBLIC: 500 req/min (burst: 750)
  - L2_RESTRICTED: 2,000 req/min (burst: 3,000)
  - L3_CONFIDENTIAL: 5,000 req/min (burst: 7,500)
Returns HTTP 429 with standard headers: X-RateLimit-Limit, X-RateLimit-Remaining, Retry-After.
"""
import threading
import time
from typing import Dict, Tuple

from src.core.config import ClearanceTier


class TokenBucket:
    """Thread-safe single client token bucket state."""

    def __init__(self, sustained_per_minute: float, burst_capacity: float):
        self.capacity = float(burst_capacity)
        self.tokens = float(burst_capacity)
        self.fill_rate = float(sustained_per_minute) / 60.0  # tokens per second
        self.last_update = time.perf_counter()
        self.lock = threading.Lock()

    def consume(self, tokens: float = 1.0) -> Tuple[bool, int, int]:
        """Attempts to consume tokens.

        Returns (allowed, remaining_tokens, retry_after_seconds).
        """
        with self.lock:
            now = time.perf_counter()
            elapsed = now - self.last_update
            self.last_update = now

            # Replenish tokens based on elapsed time up to maximum burst capacity
            self.tokens = min(self.capacity, self.tokens + (elapsed * self.fill_rate))

            if self.tokens >= tokens:
                self.tokens -= tokens
                return True, int(self.tokens), 0

            # Quota exhausted: compute wait time until at least 1 token is available
            deficit = tokens - self.tokens
            retry_after = int(deficit / self.fill_rate) + 1 if self.fill_rate > 0 else 60
            return False, int(self.tokens), retry_after


class EnterpriseRateLimiter:
    """Multi-tenant clearance-aware rate limiting manager."""

    # Clearance quotas defined in api_rate_limiting_spec.md
    QUOTAS = {
        ClearanceTier.L1_PUBLIC: {"sustained": 500, "burst": 750},
        ClearanceTier.L2_RESTRICTED: {"sustained": 2000, "burst": 3000},
        ClearanceTier.L3_CONFIDENTIAL: {"sustained": 5000, "burst": 7500},
    }

    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        self._buckets: Dict[str, TokenBucket] = {}
        self._map_lock = threading.Lock()

    @classmethod
    def get_instance(cls) -> "EnterpriseRateLimiter":
        with cls._lock:
            if cls._instance is None:
                cls._instance = EnterpriseRateLimiter()
            return cls._instance

    def check_rate_limit(
        self,
        client_key: str,
        clearance: ClearanceTier = ClearanceTier.L1_PUBLIC,
        cost: float = 1.0,
    ) -> Tuple[bool, int, int, int]:
        """Evaluates rate limit for a client identifier.

        Returns (allowed, limit, remaining, retry_after).
        """
        config = self.QUOTAS.get(clearance, self.QUOTAS[ClearanceTier.L1_PUBLIC])
        sustained = config["sustained"]
        burst = config["burst"]

        bucket_key = f"{client_key}:{clearance.value}"

        with self._map_lock:
            if bucket_key not in self._buckets:
                self._buckets[bucket_key] = TokenBucket(sustained, burst)
            bucket = self._buckets[bucket_key]

        allowed, remaining, retry_after = bucket.consume(cost)
        return allowed, burst, remaining, retry_after

    def reset(self):
        """Clears all active client buckets (primarily for testing)."""
        with self._map_lock:
            self._buckets.clear()
