# -----------------------------------------------------------------------------
# Hardened Production Dockerfile for Datheon Enterprise FDE Platform
# Designed for Client VPC deployment (AWS ECS, EKS, GCP Cloud Run / GKE)
# -----------------------------------------------------------------------------
FROM python:3.11-slim AS runtime

# Set security and performance environment flags
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1 \
    APP_ENV=production \
    API_PORT=8000 \
    API_HOST=0.0.0.0

WORKDIR /app

# Install minimal OS dependencies for healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Create non-privileged system user for VPC container security (non-root)
RUN groupadd -g 10001 datheon && \
    useradd -u 10001 -g datheon -s /bin/bash -m datheon

# Copy application source tree and pre-generate mock data
COPY src/ /app/src/
COPY configs/ /app/configs/
COPY scripts/ /app/scripts/
COPY data/ /app/data/
COPY docs/ /app/docs/

# Fix permissions for runtime non-root execution
RUN chown -R datheon:datheon /app

USER datheon

EXPOSE 8000

# Container liveness health check
HEALTHCHECK --interval=15s --timeout=5s --start-period=10s --retries=3 \
    CMD curl -f http://localhost:8000/healthz || exit 1

# Launch uvicorn production server
CMD ["uvicorn", "src.api.app:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2", "--access-log"]

