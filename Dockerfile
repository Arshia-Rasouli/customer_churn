# =============================================================================
# Stage 1: Build & Dependencies
# =============================================================================
FROM python:3.11-slim AS builder

# Prevent Python from writing .pyc files and enable unbuffered output
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /build

# Install build dependencies if needed for packages compiling from source
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Create virtual environment and install dependencies
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt


# =============================================================================
# Stage 2: Production Runtime
# =============================================================================
FROM python:3.11-slim AS runner

# Set runtime environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/opt/venv/bin:$PATH"

WORKDIR /app

# Install minimal runtime system libraries (libgomp for scikit-learn / OpenMP support)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# Copy virtual environment from builder stage
COPY --from=builder /opt/venv /opt/venv

# Create a dedicated non-root system user and group for security
RUN groupadd -r appuser && \
    useradd -r -g appuser -d /app -s /sbin/nologin appuser

# Copy application source code and assets
COPY --chown=appuser:appuser . /app

# Ensure models, logs, data, and static directories exist with proper permissions
RUN mkdir -p /app/models /app/logs /app/data /app/static && \
    chown -R appuser:appuser /app/models /app/logs /app/data /app/static

# Declare mountable volumes for persistence
VOLUME ["/app/models", "/app/logs"]

# Expose FastAPI application port
EXPOSE 8000

# Switch to non-root user
USER appuser

# Healthcheck to verify service availability
HEALTHCHECK --interval=30s --timeout=5s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:8000/api/insights')" || exit 1

# Launch the FastAPI application with Uvicorn
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]

