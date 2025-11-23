# ADPA Containerized Deployment
# Multi-stage build for optimized production image

# Stage 1: Build stage
FROM python:3.11-slim as builder

WORKDIR /build

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Stage 2: Production stage  
FROM python:3.11-slim

LABEL maintainer="ADPA Team"
LABEL description="Autonomous Data Pipeline Agent - Containerized"
LABEL version="1.0.0"

WORKDIR /app

# Install runtime system dependencies
RUN apt-get update && apt-get install -y \
    curl \
    && rm -rf /var/lib/apt/lists/* \
    && groupadd -r adpa \
    && useradd -r -g adpa adpa

# Copy Python packages from builder
COPY --from=builder /root/.local /home/adpa/.local

# Copy application code
COPY . .

# Create necessary directories
RUN mkdir -p data/logs data/experience_memory data/reports \
    && chown -R adpa:adpa /app \
    && chmod +x deploy.sh deploy/aws-deploy.sh deploy/make-global.sh

# Set Python path to include user packages
ENV PATH=/home/adpa/.local/bin:$PATH
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Environment configuration
ENV ADPA_ENVIRONMENT=container
ENV ADPA_LOG_LEVEL=INFO
ENV ADPA_DATA_DIR=/app/data
ENV ADPA_PORT=8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Switch to non-root user
USER adpa

# Expose ports
EXPOSE 8000 8001 8002

# Default command - can be overridden
CMD ["python", "-m", "src.api.main"]