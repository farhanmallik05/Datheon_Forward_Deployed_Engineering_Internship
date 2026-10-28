---
document_id: ENG-ARCH-VPC-002
department: engineering
clearance: L2_RESTRICTED
author: Staff Cloud Infrastructure Architect
date: 2026-09-30
title: Datheon VPC Multi-Region Deployment Architecture
---

# Enterprise VPC Network Architecture Specification v2.0

## 1. Network Topology & CIDR Allocation
The corporate cloud environment is deployed inside AWS `us-east-1` and Google Cloud `us-central1` using dual-hub Transit Gateway interconnection.
Primary VPC CIDR block is allocated as `10.180.0.0/16`, partitioned across three availability zones:
- `10.180.10.0/24`: Public Subnet AZ-A (ALB / Ingress Gateways)
- `10.180.20.0/24`: Private Application Subnet AZ-A (FastAPI Microservices)
- `10.180.30.0/24`: Isolated Data Subnet AZ-A (Qdrant Vector Cluster & PostgreSQL)

## 2. Ingress & Egress Security Rules
Strict security group isolation prohibits inbound ingress directly from the public internet into private application subnets.
All ingress must terminate at the hardened Envoy reverse proxy with Mutual TLS (mTLS) enforcement.
Outbound egress to external APIs requires routing through dual NAT Gateways with static Elastic IP whitelisting.

## 3. Bastion Host & SecOps Auditing
SSH access to private instances is strictly mediated through AWS Systems Manager (SSM) Session Manager.
Direct SSH port 22 is disabled at the security group perimeter. All shell sessions are logged to CloudWatch Logs with immutable KMS encryption.
