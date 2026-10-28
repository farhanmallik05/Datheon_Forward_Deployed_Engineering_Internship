---
document_id: ENG-SPEC-RATE-001
department: engineering
clearance: L1_PUBLIC
author: Senior API Platform Engineer
date: 2026-10-01
title: Enterprise API Gateway Rate Limiting Policy
---

# API Gateway Rate Limiting & Quota Specifications

## 1. Rate Limiting Algorithm
The Datheon API Gateway employs the Token Bucket algorithm backed by distributed Redis key-value storage.
Bursts are permitted up to 1.5x of the sustained transactions-per-second (TPS) ceiling.

## 2. Tiered Clearance Quotas
Rate limits are enforced at the API key level based on employee clearance tier:
- Tier L1 (Public / General): 500 requests per minute. Maximum burst: 750 requests.
- Tier L2 (Restricted Departmental): 2,000 requests per minute. Maximum burst: 3,000 requests.
- Tier L3 (Confidential / SecOps): 5,000 requests per minute. Maximum burst: 7,500 requests.

## 3. Rate Limit Exceeded Headers
When a client exceeds the threshold, the gateway returns HTTP 429 Too Many Requests with headers:
- `X-RateLimit-Limit`: Maximum requests permitted in window.
- `X-RateLimit-Remaining`: Remaining capacity.
- `Retry-After`: Seconds until quota replenishment.
