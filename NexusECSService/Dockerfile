# Multi-stage Dockerfile for Nexus ECS Service
# GPU ML inference service for control mapping

# Stage 1: Builder - Install dependencies
FROM python:3.11-slim as builder

WORKDIR /build

# Install build dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    gcc \
    g++ \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Runtime - Minimal production image
FROM python:3.11-slim

WORKDIR /app

# Install runtime dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy Python packages from builder stage
COPY --from=builder /root/.local /root/.local

# Ensure scripts in .local are usable
ENV PATH=/root/.local/bin:$PATH

# Copy package source
COPY src/nexus_ecs_service/ ./nexus_ecs_service/

# Create directory for model storage
RUN mkdir -p /tmp/models

# Expose FastAPI port
EXPOSE 8000

# Health check for ALB/ECS
HEALTHCHECK --interval=30s --timeout=5s --start-period=120s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run FastAPI with uvicorn
# Single worker for GPU memory efficiency
CMD ["uvicorn", "nexus_ecs_service.app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "1"]
