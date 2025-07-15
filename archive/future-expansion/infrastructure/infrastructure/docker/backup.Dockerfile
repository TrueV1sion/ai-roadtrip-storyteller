# Backup container for AI Road Trip Storyteller
FROM python:3.9-slim

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    postgresql-client \
    redis-tools \
    curl \
    ca-certificates \
    gnupg \
    && echo "deb [signed-by=/usr/share/keyrings/cloud.google.gpg] https://packages.cloud.google.com/apt cloud-sdk main" | tee -a /etc/apt/sources.list.d/google-cloud-sdk.list \
    && curl https://packages.cloud.google.com/apt/doc/apt-key.gpg | apt-key --keyring /usr/share/keyrings/cloud.google.gpg add - \
    && apt-get update && apt-get install -y google-cloud-sdk \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
RUN pip install --no-cache-dir \
    google-cloud-storage \
    psycopg2-binary \
    redis

# Create app directory
WORKDIR /app

# Copy backup scripts
COPY scripts/backup/ /app/scripts/backup/

# Make scripts executable
RUN chmod +x /app/scripts/backup/*.sh /app/scripts/backup/*.py

# Create non-root user
RUN useradd -m -u 1000 backup && chown -R backup:backup /app
USER backup

# Default command
CMD ["/app/scripts/backup/automated_backup.sh"]