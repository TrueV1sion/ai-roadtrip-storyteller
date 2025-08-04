# Infrastructure Architecture

## 🏗️ System Architecture

### Overview
```
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│   Mobile App    │────▶│   API Gateway   │────▶│  Backend API    │
│  (React Native) │     │  (Cloud Load    │     │  (FastAPI)      │
└─────────────────┘     │   Balancer)     │     └────────┬────────┘
                        └─────────────────┘              │
                                                         ▼
┌─────────────────┐     ┌─────────────────┐     ┌─────────────────┐
│ Knowledge Graph │────▶│   PostgreSQL    │────▶│     Redis       │
│   (Python)      │     │   (Primary DB)  │     │    (Cache)      │
└─────────────────┘     └─────────────────┘     └─────────────────┘
                                                         │
                        ┌─────────────────┐              │
                        │  Google Cloud   │◀─────────────┘
                        │   Services      │
                        │ - Vertex AI     │
                        │ - Cloud Storage │
                        │ - Maps API      │
                        └─────────────────┘
```

### Service Components

#### 1. Backend API (Cloud Run)
- **Technology**: FastAPI + Python 3.9
- **Scaling**: 1-100 instances
- **Memory**: 2GB per instance
- **CPU**: 2 vCPU per instance
- **Endpoints**: 60+ RESTful APIs
- **Authentication**: JWT RS256

#### 2. Knowledge Graph Service
- **Technology**: Custom Python service
- **Port**: 8001
- **Features**: Semantic search, Impact analysis
- **Storage**: In-memory + PostgreSQL

#### 3. PostgreSQL Database
- **Version**: 15
- **Instance**: Cloud SQL
- **Tier**: db-n1-standard-4
- **Storage**: 100GB SSD
- **Backups**: Daily automated
- **High Availability**: Regional

#### 4. Redis Cache
- **Version**: 7
- **Instance**: Cloud Memorystore
- **Tier**: M1 (5GB)
- **Eviction**: LRU
- **Persistence**: RDB snapshots

#### 5. Mobile Application
- **Framework**: React Native + Expo
- **Platforms**: iOS, Android, Web
- **Features**: Voice, AR, Navigation
- **State Management**: Redux Toolkit

### Network Architecture

#### Security Groups
```yaml
backend-api:
  ingress:
    - port: 8000
      source: load-balancer
    - port: 22
      source: admin-ips
  egress:
    - all

database:
  ingress:
    - port: 5432
      source: backend-api
    - port: 5432
      source: knowledge-graph

redis:
  ingress:
    - port: 6379
      source: backend-api
```

#### Load Balancing
- **Type**: Application Load Balancer
- **Health Checks**: /health endpoint
- **SSL Termination**: At load balancer
- **WAF**: Enabled with OWASP rules

### Scaling Strategy

#### Horizontal Scaling
- **Metric**: CPU > 70% or Memory > 80%
- **Scale Up**: Add 2 instances
- **Scale Down**: Remove 1 instance
- **Cool Down**: 60 seconds

#### Database Scaling
- **Read Replicas**: 2 (different zones)
- **Connection Pooling**: 100 connections
- **Query Optimization**: Indexed

### Disaster Recovery

#### Backup Strategy
- **Database**: Daily full + hourly incremental
- **Code**: Git repository
- **Secrets**: Secret Manager with versioning
- **Media**: Cloud Storage with versioning

#### Recovery Targets
- **RTO**: 1 hour
- **RPO**: 15 minutes
- **Backup Retention**: 30 days
- **Geographic Redundancy**: Multi-region

### Cost Optimization

#### Resource Allocation
- **Development**: Minimal resources
- **Staging**: 50% of production
- **Production**: Auto-scaling based on load

#### Cost Controls
- **Budget Alerts**: At 50%, 80%, 100%
- **Auto-shutdown**: Dev/staging after hours
- **Reserved Instances**: For predictable load
