# MVP Dockerfile for Google Cloud Run
FROM python:3.9-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    postgresql-client \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt requirements.prod.txt ./
RUN pip install --no-cache-dir -r requirements.prod.txt

# Copy backend application code
COPY backend/ ./backend/
COPY alembic.ini ./
COPY alembic/ ./alembic/

# Set Python path
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Set MVP mode
ENV MVP_MODE=true

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Expose port (Cloud Run uses PORT env variable)
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
  CMD curl -f http://localhost:8080/health || exit 1

# Start command using gunicorn with uvicorn workers
CMD exec gunicorn backend.app.main_mvp:app \
    --bind :${PORT:-8080} \
    --workers 2 \
    --worker-class uvicorn.workers.UvicornWorker \
    --timeout 120 \
    --access-logfile - \
    --error-logfile -