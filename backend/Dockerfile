# Production Dockerfile for RoadTrip Backend Service
# Optimized for Google Cloud Run deployment with enhanced features
# Includes support for AR, Spatial Audio, Journey Tracking, and Advanced AI

# Stage 1: Build stage
FROM python:3.9-slim as builder

# Set working directory
WORKDIR /app

# Install system dependencies required for Python packages
# Added dependencies for audio processing and AR features
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    libpq-dev \
    libssl-dev \
    libffi-dev \
    build-essential \
    curl \
    ffmpeg \
    libsndfile1 \
    libportaudio2 \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements file
COPY requirements.txt .

# Install Python dependencies in a virtual environment
RUN python -m venv /opt/venv
ENV PATH="/opt/venv/bin:$PATH"

# Upgrade pip and install dependencies
RUN pip install --upgrade pip setuptools wheel && \
    pip install --no-cache-dir -r requirements.txt

# Stage 2: Runtime stage
FROM python:3.9-slim

# Install runtime dependencies only
# Added runtime dependencies for audio and AR features
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    curl \
    ca-certificates \
    ffmpeg \
    libsndfile1 \
    libportaudio2 \
    && rm -rf /var/lib/apt/lists/*

# Create non-root user for security
RUN groupadd -r appuser && useradd -r -g appuser appuser

# Set working directory
WORKDIR /app

# Copy virtual environment from builder
COPY --from=builder /opt/venv /opt/venv

# Set environment variables
ENV PATH="/opt/venv/bin:$PATH" \
    PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONPATH=/app \
    # Google Cloud Run expects PORT environment variable
    PORT=8080 \
    # Production environment
    ENVIRONMENT=production \
    # Optimize Python for containers
    PYTHONHASHSEED=1 \
    # Disable pip version check
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    # Don't buffer stdout/stderr
    PYTHONIOENCODING=utf-8

# Copy application code
COPY . .

# Create necessary directories and set permissions
# Added directories for new features
RUN mkdir -p /app/logs /app/tmp /app/uploads /app/audio_cache /app/ar_cache /app/memories && \
    chmod +x /app/start.sh && \
    chown -R appuser:appuser /app && \
    chmod -R 755 /app

# Security: Remove unnecessary files
RUN find /app -name "*.pyc" -delete && \
    find /app -name "__pycache__" -type d -exec rm -rf {} + 2>/dev/null || true && \
    rm -rf /app/tests /app/.pytest_cache /app/.coverage /app/htmlcov 2>/dev/null || true

# Switch to non-root user
USER appuser

# Expose port (Google Cloud Run will override this with PORT env var)
EXPOSE 8080

# Health check configuration
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:${PORT}/health || exit 1

# Use startup script with proper Gunicorn configuration
CMD ["/app/start.sh"]