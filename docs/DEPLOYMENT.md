# Production Deployment Guide

## Prerequisites

- Docker & Docker Compose
- PostgreSQL database (optional, for scaling)
- Linux server (Ubuntu 22.04+ recommended)
- Domain name with SSL certificate

## Quick Start (Docker Compose)

### 1. Clone and Configure

```bash
git clone <repo-url>
cd grok-insights-backend
cp .env.example .env.production
```

### 2. Update Configuration

Edit `.env.production`:
```bash
export ENVIRONMENT=production
export DATABASE_URL=postgresql://<user>:<pass>@<host>:5432/grok_insights
export GROK_MODE=real
export GROK_API_KEY=<your-api-key>
export DEBUG=false
```

### 3. Deploy

```bash
docker-compose -f docker-compose.prod.yml up -d
```

### 4. Verify

```bash
curl http://localhost:8000/health
```

Expected response:
```json
{"status": "ok", "queue_size": 0, "worker_running": true, "db_ok": true}
```

## Production Architecture

### Recommended Stack

```
┌─────────────────────────────────────┐
│        Nginx / Load Balancer        │ (TLS termination)
├─────────────────────────────────────┤
│        FastAPI Container            │ (multiple replicas)
│  src.grok_insights.main:app         │
├─────────────────────────────────────┤
│        PostgreSQL Database          │ (RDS or managed)
├─────────────────────────────────────┤
│        Redis (optional)             │ (for distributed queue)
└─────────────────────────────────────┘
```

### Scaling Considerations

**Single Container (< 100 QPS):**
- 1 FastAPI container
- SQLite database (fine for dev)
- Local asyncio queue

**Multi-Container (100–1k QPS):**
- 3–5 FastAPI containers
- PostgreSQL database
- Redis queue (Celery)
- Load balancer (nginx)

**High Scale (> 1k QPS):**
- Auto-scaling FastAPI deployment (Kubernetes)
- PostgreSQL with read replicas
- Redis cluster
- Distributed worker pool (Celery)
- Message queue (RabbitMQ or Kafka)

## Database Setup

### PostgreSQL (Recommended for Production)

1. **Create database:**
```sql
CREATE DATABASE grok_insights;
CREATE USER grok_user WITH PASSWORD 'secure_password';
GRANT ALL PRIVILEGES ON DATABASE grok_insights TO grok_user;
```

2. **Update connection string:**
```bash
export DATABASE_URL=postgresql://grok_user:secure_password@postgres:5432/grok_insights
```

3. **Run migrations:**
```bash
docker-compose exec backend alembic upgrade head
```

### Amazon RDS

1. Create RDS PostgreSQL instance
2. Security group: Allow inbound port 5432 from app servers
3. Connection string:
```bash
DATABASE_URL=postgresql://admin:password@grok-insights.123456.us-east-1.rds.amazonaws.com:5432/grok_insights
```

## Web Server Setup

### Nginx Configuration

```nginx
upstream grok_backend {
    server backend:8000;
    # Add more servers for multiple containers
    # server backend_2:8000;
    # server backend_3:8000;
}

server {
    listen 443 ssl http2;
    server_name api.example.com;
    
    ssl_certificate     /etc/letsencrypt/live/api.example.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/api.example.com/privkey.pem;
    
    client_max_body_size 100M;
    
    location / {
        proxy_pass http://grok_backend;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /metrics {
        # Restrict metrics to internal IPs only
        allow 10.0.0.0/8;  # Internal network
        deny all;
        proxy_pass http://grok_backend;
    }
}

server {
    listen 80;
    server_name api.example.com;
    return 301 https://$server_name$request_uri;
}
```

Add to `docker-compose.prod.yml`:
```yaml
services:
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/conf.d/default.conf
      - /etc/letsencrypt/live/api.example.com:/etc/letsencrypt:ro
    depends_on:
      - backend
```

## SSL/TLS Certificates

### Using Let's Encrypt

```bash
certbot certonly --standalone -d api.example.com
# Generates certificates in /etc/letsencrypt/live/api.example.com/
```

### Using AWS Certificate Manager (Recommended)

1. Request certificate in ACM
2. Validate domain
3. Use certificate ARN in load balancer configuration

## Environment Variables

### Minimum Production Set

```bash
# Essential
ENVIRONMENT=production
DEBUG=false
DATABASE_URL=postgresql://...
GROK_MODE=real
GROK_API_KEY=your-api-key

# Security
CORS_ORIGINS=["https://app.example.com"]

# Performance
WORKERS=4
MAX_BATCH_SIZE=100
DATABASE_POOL_SIZE=30

# Monitoring
LOG_LEVEL=INFO
ENABLE_PROMETHEUS_METRICS=true
```

### Optional Advanced Settings

```bash
# Rate limiting (adjust for your use case)
RATE_LIMIT_REQUESTS=1000
RATE_LIMIT_WINDOW_SECONDS=60

# Database connection
DATABASE_MAX_OVERFLOW=20
DATABASE_ECHO=false

# Processing tune
START_BATCH_SIZE=20
CIRCUIT_BREAKER_COOLDOWN_SECONDS=30

# Cost control
GROK_COST_PER_1K=0.002
```

## Monitoring & Logging

### Prometheus Metrics

Scrape endpoint: `http://backend:8001/metrics`

Add to Prometheus `prometheus.yml`:
```yaml
scrape_configs:
  - job_name: 'grok-insights'
    static_configs:
      - targets: ['localhost:8001']
```

### CloudWatch Logs (AWS)

Add to container:
```yaml
logging:
  driver: awslogs
  options:
    awslogs-group: /ecs/grok-insights
    awslogs-region: us-east-1
    awslogs-stream-prefix: ecs
```

### Grafana Dashboards

1. Add Prometheus data source
2. Create dashboards for:
   - Request latency (p50/p95/p99)
   - Grok API call count
   - Cache hit rate
   - Queue depth
   - Estimated cost

## Health Checks

### Kubernetes Liveness Probe

```yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8000
  initialDelaySeconds: 30
  periodSeconds: 10
```

### Docker Compose Health Check

```yaml
healthcheck:
  test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
  interval: 30s
  timeout: 10s
  retries: 3
  start_period: 40s
```

## Backup & Disaster Recovery

### Database Backups

With PostgreSQL on AWS RDS:
```bash
# Enable automated backups (35-day retention recommended)
# Enable enhanced monitoring
# Enable encryption at rest
```

Manual backup:
```bash
pg_dump postgresql://user:pass@host/grok_insights > backup.sql
```

### Restore

```bash
psql postgresql://user:pass@host/grok_insights < backup.sql
```

## Security Hardening

### 1. Secrets Management

Use AWS Secrets Manager or HashiCorp Vault:
```bash
# Don't put secrets in .env or docker-compose
# Load from secrets manager at runtime
export GROK_API_KEY=$(aws secretsmanager get-secret-value --secret-id grok-api-key --query SecretString --output text)
```

### 2. Network Security

- Run all containers on private network
- Use security groups/firewall rules
- Restrict metrics endpoints to internal IPs only
- Enable VPC endpoint for RDS access

### 3. Database Security

```bash
# PostgreSQL user permissions (least privilege)
CREATE ROLE grok_app WITH PASSWORD 'secure_password';
GRANT CONNECT ON DATABASE grok_insights TO grok_app;
GRANT USAGE ON SCHEMA public TO grok_app;
GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA public TO grok_app;
```

### 4. API Security

- Enable rate limiting (already configured)
- Add API key authentication (future enhancement)
- Enable CORS with specific origins only
- Add request logging & audit trails

### 5. Image Scanning

```bash
# Scan Docker image for vulnerabilities
docker scan grok-insights-backend:latest
trivy image grok-insights-backend:latest
```

## Performance Tuning

### Database Connection Pool

```bash
# For high concurrent connections
DATABASE_POOL_SIZE=30
DATABASE_MAX_OVERFLOW=20
```

### Batch Size Tuning

Start with:
```bash
START_BATCH_SIZE=5
MAX_BATCH_SIZE=100
```

Monitor and adjust based on CPU/memory usage.

### Worker Concurrency

Adjust based on available resources:
```bash
# For single container
WORKERS=4  # (number of CPU cores + 1)

# For container with 8 CPUs
WORKERS=9
```

## Troubleshooting

### High Queue Depth

1. Increase `MAX_BATCH_SIZE` (default 50)
2. Increase max `WORKERS`
3. Check Grok API latency
4. Scale to multiple containers

### High Memory Consumption

1. Reduce `MAX_BATCH_SIZE`
2. Reduce `RATE_LIMIT_REQUESTS`
3. Monitor for memory leaks
4. Check for long-running requests

### Slow Response Times

1. Check database query performance
2. Verify worker processing latency
3. Check Grok API latency
4. Review Prometheus metrics

## Monitoring Commands

```bash
# Check container health
docker-compose ps

# View logs
docker-compose logs -f backend

# Check metrics
curl http://localhost:8001/metrics | head -50

# Monitor queue status
curl http://localhost:8000/health | jq .

# Get summary statistics
curl http://localhost:8000/status/summary | jq .
```

## Upgrade Procedure

1. **Pull latest code:**
```bash
git pull origin main
```

2. **Build new image:**
```bash
docker-compose build
```

3. **Run database migrations:**
```bash
docker-compose exec backend alembic upgrade head
```

4. **Roll out gradually:**
```bash
# Update 1 container at a time
docker-compose up --no-deps -d backend
```

5. **Verify health:**
```bash
curl http://localhost:8000/health
```

## Rollback

If issues occur:
```bash
# Revert to previous image
git revert HEAD
docker-compose down
docker-compose build
docker-compose up -d
```

## Support

For deployment issues:
1. Check logs: `docker-compose logs backend`
2. Verify health: `curl http://localhost:8000/health`
3. Check metrics: `curl http://localhost:8000/metrics | grep errors`
4. Review troubleshooting guide
