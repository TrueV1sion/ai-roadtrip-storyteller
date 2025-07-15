FROM python:3.9-alpine

# Install dependencies
RUN apk add --no-cache \
    redis \
    bash \
    curl \
    gzip \
    dcron \
    supervisor

# Install Python packages
RUN pip install --no-cache-dir \
    redis \
    google-cloud-storage \
    google-cloud-monitoring

# Create app directory
WORKDIR /app

# Copy backup script
COPY backup.sh /app/
COPY redis_backup.py /app/
RUN chmod +x /app/backup.sh /app/redis_backup.py

# Copy cron configuration
COPY crontab /etc/crontabs/root

# Copy supervisor config
COPY supervisord.conf /etc/supervisord.conf

# Create backup directory
RUN mkdir -p /tmp/backups

# Health check script
COPY healthcheck.sh /app/
RUN chmod +x /app/healthcheck.sh

# Run supervisor
CMD ["/usr/bin/supervisord", "-c", "/etc/supervisord.conf"]