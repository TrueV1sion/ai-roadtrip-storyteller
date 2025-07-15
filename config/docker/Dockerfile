# Cloud Run optimized Dockerfile
FROM python:3.9-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1
ENV PORT=8000
ENV PYTHONPATH=/app/backend

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy and install Python dependencies
COPY requirements.prod.txt requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire backend directory
COPY backend ./backend

# Copy other necessary files
COPY healthcheck.sh ./healthcheck.sh
RUN chmod +x ./healthcheck.sh

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD ./healthcheck.sh || exit 1

# Expose port
EXPOSE 8000

# Use the PORT environment variable from Cloud Run
CMD exec gunicorn -w 2 -k uvicorn.workers.UvicornWorker backend.app.main:app --bind 0.0.0.0:${PORT}