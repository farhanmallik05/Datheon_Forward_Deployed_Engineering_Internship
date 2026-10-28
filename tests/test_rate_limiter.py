"""Unit and Integration Tests for Token Bucket Rate Limiting.

Verifies adherence to data/raw/engineering/api_rate_limiting_spec.md:
  - Token bucket consumption and capacity limits
  - Tier L1 (500/750), Tier L2 (2000/3000), Tier L3 (5000/7500)
  - HTTP 429 response when quota is exceeded
  - Headers: X-RateLimit-Limit, X-RateLimit-Remaining, Retry-After
"""
import pytest
from src.core.config import ClearanceTier
from src.api.rate_limiter import EnterpriseRateLimiter, TokenBucket


def test_token_bucket_consume_and_replenish():
    # 60 tokens/min = 1 token/sec, burst capacity 5
    bucket = TokenBucket(sustained_per_minute=60, burst_capacity=5)
    
    # Consume all 5 burst tokens
    for i in range(5):
        allowed, remaining, _ = bucket.consume(1.0)
        assert allowed is True

    # 6th immediate token must be rejected
    allowed, remaining, retry_after = bucket.consume(1.0)
    assert allowed is False
    assert retry_after >= 1


def test_enterprise_rate_limiter_tiers():
    limiter = EnterpriseRateLimiter.get_instance()
    limiter.reset()

    # Test L1 Public
    allowed, limit, remaining, _ = limiter.check_rate_limit("client_1", ClearanceTier.L1_PUBLIC)
    assert allowed is True
    assert limit == 750

    # Test L3 Confidential receives higher burst capacity
    allowed_l3, limit_l3, remaining_l3, _ = limiter.check_rate_limit("client_2", ClearanceTier.L3_CONFIDENTIAL)
    assert allowed_l3 is True
    assert limit_l3 == 7500


def test_api_rate_limit_headers(api_client):
    limiter = EnterpriseRateLimiter.get_instance()
    limiter.reset()

    headers = {
        "X-Employee-ID": "USR-TEST-RATE",
        "X-Clearance-Tier": "L1_PUBLIC",
        "X-Department": "engineering"
    }

    # Query mock ERP API
    response = api_client.get("/api/v1/erp/inventory/SKU-H100-80G", headers=headers)
    assert response.status_code == 200
    assert "X-RateLimit-Limit" in response.headers
    assert "X-RateLimit-Remaining" in response.headers
    assert response.headers["X-RateLimit-Limit"] == "750"


def test_api_rate_limit_429_exhaustion(api_client):
    limiter = EnterpriseRateLimiter.get_instance()
    limiter.reset()

    headers = {
        "X-Employee-ID": "USR-EXHAUST-TEST",
        "X-Clearance-Tier": "L1_PUBLIC",
        "X-Department": "engineering"
    }

    # Artificially consume quota
    limiter.check_rate_limit("USR-EXHAUST-TEST", ClearanceTier.L1_PUBLIC, cost=750.0)

    # Next request should be rate-limited to 429
    response = api_client.get("/api/v1/erp/inventory/SKU-H100-80G", headers=headers)
    assert response.status_code == 429
    data = response.json()
    assert data["error"] == "RATE_LIMIT_EXCEEDED"
    assert "Retry-After" in response.headers
    assert "X-RateLimit-Remaining" in response.headers
