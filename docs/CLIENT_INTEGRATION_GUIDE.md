# Enterprise Client Integration & VPC Deployment Guide
### Datheon Forward Deployed Engineering (FDE) Handoff Manual

---

## 1. Scope & Purpose

This guide outlines deployment procedures, security architecture, network topology, role-based access control (RBAC), and monitoring configurations required for deploying the **Datheon Enterprise FDE Platform** into a client-managed Virtual Private Cloud (AWS VPC, GCP VPC, or Azure VNet).

---

## 2. Network Topology & VPC Segmentation

The solution is architected for zero-trust private subnet deployment with no direct inbound internet exposure.

```
       [ Client Corporate Transit Gateway / VPN ]
                           |
                           v
              +-------------------------+
              | Hardened Ingress Proxy  |  Subnet: 10.180.10.0/24 (AZ-A)
              |  (Envoy / AWS ALB)      |  Port: 443 (mTLS)
              +------------+------------+
                           |
                           v
              +-------------------------+
              | Datheon FDE Microservice|  Subnet: 10.180.20.0/24 (Private)
              |  (FastAPI + Agent)      |  Port: 8000
              +------------+------------+
                           |
            +--------------+--------------+
            |                             |
            v                             v
  +--------------------+        +--------------------+
  | Qdrant Vector DB   |        | Prometheus Scraper |
  | Subnet: 10.180.30/ |        | Port: 9090         |
  | Port: 6333         |        |                    |
  +--------------------+        +--------------------+
```

### Ingress & Egress Security Group Rules
| Source / Target | Port | Protocol | Purpose |
| :--- | :--- | :--- | :--- |
| ALB / Gateway Ingress | 8000 | TCP | Authenticated API requests (RBAC headers) |
| Internal Prometheus | 8000 | TCP | Telemetry scrape endpoint (`/metrics`) |
| Outbound NAT Gateway | 443 | TCP | Secure egress to enterprise IdP / external LLMs |
| Local Qdrant Storage | 6333 | TCP | Vector index RPC / REST transactions |

---

## 3. RBAC Clearance & Security Classification Matrix

The platform enforces strict role-based access control and tenant isolation across corporate departments.

| Clearance Tier | Numeric Rank | Description | Allowed Document Access |
| :--- | :---: | :--- | :--- |
| `L1_PUBLIC` | 1 | General employees, contractors, interns | Company-wide policies, public APIs, general specs |
| `L2_RESTRICTED` | 2 | Departmental staff, engineers, operations | Internal architecture, vendor invoices, legal NDAs |
| `L3_CONFIDENTIAL` | 3 | Officers, directors, compensation committee | Audit reports, executive payroll, M&A agreements |

### Department Tenancy Boundary Matrix
- **Engineering Employees**: Can access `Engineering` (up to clearance tier) + `Cross-Functional`. Cannot retrieve `Finance`, `HR`, or `Legal` assets.
- **Finance Employees**: Can access `Finance` (up to clearance tier) + `Cross-Functional`. Cannot retrieve `Engineering` VPC topologies or `HR` payroll records.
- **HR Officers**: Can access `HR` compensation and policy documents + `Cross-Functional`. Cannot retrieve `Engineering` private specs.
- **Executive Oversight (`EXECUTIVE` / `is_admin`)**: Permits cross-departmental auditing across all units, strictly bounded by the principal's numeric clearance level.

---

## 4. Environment Variables & Secrets Management

Store secrets in an enterprise KMS (AWS Secrets Manager, HashiCorp Vault, GCP Secret Manager). Mount them into the container runtime via environment variables:

| Variable | Type | Default | Description |
| :--- | :--- | :--- | :--- |
| `APP_ENV` | `string` | `production` | Environment tier (`development`, `staging`, `production`) |
| `API_HOST` | `string` | `0.0.0.0` | In-container bind address |
| `API_PORT` | `integer` | `8000` | Microservice listening port |
| `SECRET_KEY` | `string` | *[KMS Injected]* | Master cryptographic secret for internal signing |
| `ADMIN_API_KEY` | `string` | *[KMS Injected]* | High-clearance token for automated vector ETL ingestion |
| `HITL_HMAC_SECRET` | `string` | *[KMS Injected]* | Cryptographic secret used to sign HITL confirmation tokens |
| `VECTOR_STORE_BACKEND` | `string` | `memory` or `qdrant` | Vector storage implementation adapter |
| `QDRANT_HOST` | `string` | `qdrant` | Target hostname for Qdrant vector cluster |
| `STRICT_CITATION_GUARDRAIL` | `boolean` | `true` | When true, rejects or sanitizes ungrounded claims |
| `MIN_CITATION_CONFIDENCE` | `float` | `0.70` | Minimum groundedness ratio threshold |

---

## 5. Deployment Quickstart

### Method A: Docker Compose Deployment (Recommended for VPC Staging)
```bash
# 1. Clone repository
git clone https://github.com/your-username/Datheon_Forward_Deployed_Engineering_Internship.git
cd Datheon_Forward_Deployed_Engineering_Internship

# 2. Configure environment credentials
cp .env.example .env

# 3. Launch container stack
docker compose up --build -d

# 4. Verify deployment health
curl -f http://localhost:8000/healthz
curl -f http://localhost:8000/readyz
```

### Method B: Kubernetes / Amazon EKS Pod Specification
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: datheon-fde-api
  namespace: datheon-vpc
spec:
  replicas: 3
  selector:
    matchLabels:
      app: datheon-fde-api
  template:
    metadata:
      labels:
        app: datheon-fde-api
    spec:
      securityContext:
        runAsNonRoot: true
        runAsUser: 10001
      containers:
        - name: fde-service
          image: datheon/fde-microservice:1.0.0
          imagePullPolicy: IfNotPresent
          ports:
            - containerPort: 8000
          livenessProbe:
            httpGet:
              path: /healthz
              port: 8000
            initialDelaySeconds: 10
            periodSeconds: 15
          readinessProbe:
            httpGet:
              path: /readyz
              port: 8000
            initialDelaySeconds: 5
            periodSeconds: 10
          resources:
            limits:
              cpu: "2000m"
              memory: "4096Mi"
            requests:
              cpu: "500m"
              memory: "1024Mi"
```

---

## 6. Telemetry & Observability Integration

Prometheus automatically scrapes the microservice every 5 seconds.

### Essential Alerting Rules
- **High Request Latency**: `histogram_quantile(0.95, sum(rate(datheon_http_request_duration_seconds_bucket[5m])) by (le)) > 1.5`
- **Elevated Guardrail Rejections**: `rate(datheon_rag_guardrail_blocked_total[5m]) > 0.05`
- **Unresolved HITL Queue Stagnation**: `datheon_agent_hitl_pending_actions > 10`
- **High Ingestion Error Rate**: `rate(datheon_etl_documents_total{status="failure"}[5m]) > 0`

