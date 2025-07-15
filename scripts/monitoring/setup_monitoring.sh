#!/bin/bash
# Setup script for production monitoring stack

set -e

echo "Setting up AI Road Trip Storyteller Monitoring Stack..."

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print colored output
print_status() {
    echo -e "${GREEN}[✓]${NC} $1"
}

print_error() {
    echo -e "${RED}[✗]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[!]${NC} $1"
}

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    print_error "Docker is not installed. Please install Docker first."
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker-compose &> /dev/null; then
    print_error "Docker Compose is not installed. Please install Docker Compose first."
    exit 1
fi

# Create necessary directories
print_status "Creating monitoring directories..."
mkdir -p monitoring/prometheus
mkdir -p monitoring/grafana/dashboards
mkdir -p monitoring/grafana/provisioning/{dashboards,datasources}
mkdir -p monitoring/alertmanager
mkdir -p logs/monitoring

# Copy Prometheus configuration
print_status "Setting up Prometheus configuration..."
cat > monitoring/prometheus/prometheus.yml << 'EOF'
global:
  scrape_interval: 15s
  evaluation_interval: 15s
  external_labels:
    environment: '${ENVIRONMENT:-production}'
    service: 'roadtrip'

# Alertmanager configuration
alerting:
  alertmanagers:
    - static_configs:
        - targets:
            - alertmanager:9093

# Load rules
rule_files:
  - "alerts.yml"
  - "alerts-production.yml"

# Scrape configurations
scrape_configs:
  # Prometheus self-monitoring
  - job_name: 'prometheus'
    static_configs:
      - targets: ['localhost:9090']

  # Road Trip API
  - job_name: 'roadtrip-api'
    metrics_path: '/metrics'
    static_configs:
      - targets: ['api:8000']
    relabel_configs:
      - source_labels: [__address__]
        target_label: instance
        replacement: 'api'

  # PostgreSQL Exporter
  - job_name: 'postgres'
    static_configs:
      - targets: ['postgres-exporter:9187']

  # Redis Exporter
  - job_name: 'redis'
    static_configs:
      - targets: ['redis-exporter:9121']

  # Node Exporter (if running)
  - job_name: 'node'
    static_configs:
      - targets: ['node-exporter:9100']

  # Blackbox Exporter for endpoint monitoring
  - job_name: 'blackbox'
    metrics_path: /probe
    params:
      module: [http_2xx]
    static_configs:
      - targets:
          - http://api:8000/health
          - http://api:8000/health/ready
    relabel_configs:
      - source_labels: [__address__]
        target_label: __param_target
      - source_labels: [__param_target]
        target_label: instance
      - target_label: __address__
        replacement: blackbox-exporter:9115
EOF

# Copy Alertmanager configuration
print_status "Setting up Alertmanager configuration..."
cat > monitoring/alertmanager/config.yml << 'EOF'
global:
  resolve_timeout: 5m
  smtp_from: 'alerts@roadtrip.ai'
  smtp_smarthost: 'smtp.gmail.com:587'
  smtp_auth_username: '${ALERTMANAGER_EMAIL}'
  smtp_auth_password: '${ALERTMANAGER_EMAIL_PASSWORD}'

route:
  group_by: ['alertname', 'severity']
  group_wait: 10s
  group_interval: 10s
  repeat_interval: 1h
  receiver: 'default'
  routes:
    - match:
        severity: critical
      receiver: pagerduty
      continue: true
    - match:
        severity: critical
      receiver: email-critical
    - match:
        severity: warning
      receiver: email-warning

receivers:
  - name: 'default'
    
  - name: 'email-critical'
    email_configs:
      - to: '${ALERT_EMAIL_CRITICAL}'
        headers:
          Subject: '[CRITICAL] {{ .GroupLabels.alertname }} - Road Trip AI'
        
  - name: 'email-warning'
    email_configs:
      - to: '${ALERT_EMAIL_WARNING}'
        headers:
          Subject: '[WARNING] {{ .GroupLabels.alertname }} - Road Trip AI'
          
  - name: 'pagerduty'
    pagerduty_configs:
      - service_key: '${PAGERDUTY_SERVICE_KEY}'
        description: '{{ .GroupLabels.alertname }}: {{ .Annotations.summary }}'

inhibit_rules:
  - source_match:
      severity: 'critical'
    target_match:
      severity: 'warning'
    equal: ['alertname', 'instance']
EOF

# Create docker-compose override for monitoring
print_status "Creating Docker Compose monitoring configuration..."
cat > docker-compose.monitoring.prod.yml << 'EOF'
version: '3.8'

services:
  prometheus:
    image: prom/prometheus:latest
    container_name: roadtrip-prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=30d'
      - '--web.console.libraries=/usr/share/prometheus/console_libraries'
      - '--web.console.templates=/usr/share/prometheus/consoles'
      - '--web.enable-lifecycle'
    ports:
      - "9090:9090"
    volumes:
      - ./monitoring/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - ./monitoring/prometheus/alerts.yml:/etc/prometheus/alerts.yml:ro
      - ./monitoring/prometheus/alerts-production.yml:/etc/prometheus/alerts-production.yml:ro
      - prometheus_data:/prometheus
    networks:
      - roadtrip-network
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    container_name: roadtrip-grafana
    environment:
      GF_SECURITY_ADMIN_USER: ${GRAFANA_USER:-admin}
      GF_SECURITY_ADMIN_PASSWORD: ${GRAFANA_PASSWORD:-admin}
      GF_USERS_ALLOW_SIGN_UP: "false"
      GF_SERVER_ROOT_URL: "%(protocol)s://%(domain)s:%(http_port)s/grafana/"
      GF_SERVER_SERVE_FROM_SUB_PATH: "true"
    ports:
      - "3000:3000"
    volumes:
      - grafana_data:/var/lib/grafana
      - ./monitoring/grafana/provisioning:/etc/grafana/provisioning:ro
      - ./monitoring/grafana/dashboards:/etc/grafana/provisioning/dashboards:ro
    depends_on:
      - prometheus
    networks:
      - roadtrip-network
    restart: unless-stopped

  alertmanager:
    image: prom/alertmanager:latest
    container_name: roadtrip-alertmanager
    command:
      - '--config.file=/etc/alertmanager/config.yml'
      - '--storage.path=/alertmanager'
    ports:
      - "9093:9093"
    volumes:
      - ./monitoring/alertmanager/config.yml:/etc/alertmanager/config.yml:ro
      - alertmanager_data:/alertmanager
    networks:
      - roadtrip-network
    restart: unless-stopped

  blackbox-exporter:
    image: prom/blackbox-exporter:latest
    container_name: roadtrip-blackbox-exporter
    ports:
      - "9115:9115"
    command:
      - '--config.file=/etc/blackbox_exporter/config.yml'
    volumes:
      - ./monitoring/blackbox/config.yml:/etc/blackbox_exporter/config.yml:ro
    networks:
      - roadtrip-network
    restart: unless-stopped

  node-exporter:
    image: prom/node-exporter:latest
    container_name: roadtrip-node-exporter
    ports:
      - "9100:9100"
    command:
      - '--path.procfs=/host/proc'
      - '--path.rootfs=/rootfs'
      - '--path.sysfs=/host/sys'
      - '--collector.filesystem.mount-points-exclude=^/(sys|proc|dev|host|etc)($$|/)'
    volumes:
      - /proc:/host/proc:ro
      - /sys:/host/sys:ro
      - /:/rootfs:ro
    networks:
      - roadtrip-network
    restart: unless-stopped

volumes:
  prometheus_data:
  grafana_data:
  alertmanager_data:

networks:
  roadtrip-network:
    external: true
EOF

# Create blackbox exporter config
print_status "Setting up Blackbox Exporter configuration..."
mkdir -p monitoring/blackbox
cat > monitoring/blackbox/config.yml << 'EOF'
modules:
  http_2xx:
    prober: http
    timeout: 5s
    http:
      valid_http_versions: ["HTTP/1.1", "HTTP/2.0"]
      valid_status_codes: [200, 201, 202, 204]
      method: GET
      preferred_ip_protocol: "ip4"
      ip_protocol_fallback: false
  
  http_post_2xx:
    prober: http
    timeout: 5s
    http:
      valid_http_versions: ["HTTP/1.1", "HTTP/2.0"]
      valid_status_codes: [200, 201, 202, 204]
      method: POST
      headers:
        Content-Type: application/json
      body: '{}'
EOF

# Copy all dashboard files
print_status "Copying Grafana dashboards..."
cp monitoring/grafana/dashboards/*.json monitoring/grafana/provisioning/dashboards/ 2>/dev/null || print_warning "No dashboard files found"

# Create environment file template
print_status "Creating environment template..."
cat > .env.monitoring << 'EOF'
# Monitoring Configuration
ENVIRONMENT=production
GRAFANA_USER=admin
GRAFANA_PASSWORD=changeme
ALERTMANAGER_EMAIL=alerts@roadtrip.ai
ALERTMANAGER_EMAIL_PASSWORD=changeme
ALERT_EMAIL_CRITICAL=oncall@roadtrip.ai
ALERT_EMAIL_WARNING=devops@roadtrip.ai
PAGERDUTY_SERVICE_KEY=changeme
EOF

# Create monitoring start script
print_status "Creating monitoring start script..."
cat > start_monitoring.sh << 'EOF'
#!/bin/bash
set -e

# Load environment variables
if [ -f .env.monitoring ]; then
    export $(cat .env.monitoring | grep -v '^#' | xargs)
fi

echo "Starting monitoring stack..."

# Ensure network exists
docker network create roadtrip-network 2>/dev/null || true

# Start monitoring services
docker-compose -f docker-compose.monitoring.prod.yml up -d

# Wait for services to be ready
echo "Waiting for services to start..."
sleep 10

# Check service health
echo "Checking service health..."
curl -s http://localhost:9090/-/healthy > /dev/null && echo "✓ Prometheus is healthy" || echo "✗ Prometheus is not healthy"
curl -s http://localhost:3000/api/health > /dev/null && echo "✓ Grafana is healthy" || echo "✗ Grafana is not healthy"
curl -s http://localhost:9093/-/healthy > /dev/null && echo "✓ Alertmanager is healthy" || echo "✗ Alertmanager is not healthy"

echo ""
echo "Monitoring stack is running!"
echo "- Prometheus: http://localhost:9090"
echo "- Grafana: http://localhost:3000 (user: $GRAFANA_USER)"
echo "- Alertmanager: http://localhost:9093"
echo ""
echo "To view logs: docker-compose -f docker-compose.monitoring.prod.yml logs -f"
echo "To stop: docker-compose -f docker-compose.monitoring.prod.yml down"
EOF

chmod +x start_monitoring.sh

# Create monitoring stop script
print_status "Creating monitoring stop script..."
cat > stop_monitoring.sh << 'EOF'
#!/bin/bash
echo "Stopping monitoring stack..."
docker-compose -f docker-compose.monitoring.prod.yml down
echo "Monitoring stack stopped."
EOF

chmod +x stop_monitoring.sh

# Create health check script
print_status "Creating health check script..."
cat > check_monitoring_health.sh << 'EOF'
#!/bin/bash

echo "Checking monitoring stack health..."
echo ""

# Function to check service
check_service() {
    local name=$1
    local url=$2
    if curl -s -f "$url" > /dev/null; then
        echo "✓ $name is healthy"
        return 0
    else
        echo "✗ $name is not responding"
        return 1
    fi
}

# Check all services
check_service "Prometheus" "http://localhost:9090/-/healthy"
check_service "Grafana" "http://localhost:3000/api/health"
check_service "Alertmanager" "http://localhost:9093/-/healthy"
check_service "API Metrics" "http://localhost:8000/metrics"

echo ""
echo "Checking recent alerts..."
curl -s http://localhost:9093/api/v1/alerts | jq '.data[] | {alert: .labels.alertname, state: .state, severity: .labels.severity}'
EOF

chmod +x check_monitoring_health.sh

print_status "Monitoring setup complete!"
echo ""
echo "Next steps:"
echo "1. Update .env.monitoring with your configuration"
echo "2. Run ./start_monitoring.sh to start the monitoring stack"
echo "3. Access Grafana at http://localhost:3000"
echo "4. Import dashboards from monitoring/grafana/dashboards/"
echo ""
print_warning "Remember to configure alerting emails and PagerDuty in .env.monitoring"