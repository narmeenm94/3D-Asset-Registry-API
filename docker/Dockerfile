# METRO 3D Asset Registry API - Dockerfile
# Multi-stage build for optimized production image

# ===================
# Build Stage
# ===================
FROM python:3.11-slim as builder

# Set working directory
WORKDIR /app

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .

# Create virtual environment and install dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# ===================
# Runtime Stage
# ===================
FROM python:3.11-slim as runtime

# Set labels
LABEL maintainer="METRO WP9 Team <wp9@metropolia.fi>"
LABEL description="METRO 3D Asset Registry API for DTRIP4H Project"
LABEL version="1.0.0"

# Create non-root user for security
RUN groupadd -r metro && useradd -r -g metro metro

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Copy application code
COPY app/ ./app/
COPY migrations/ ./migrations/
COPY alembic.ini .

# Create storage directory
RUN mkdir -p /app/storage && chown -R metro:metro /app

# Switch to non-root user
USER metro

# Set environment variables
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PORT=8000

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import httpx; httpx.get('http://localhost:8000/api/v1/health')" || exit 1

# Run the application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
