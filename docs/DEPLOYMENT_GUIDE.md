# VANTYX — Production Deployment Guide

This guide details the deployment of VANTYX in containerized production environments using Docker Compose, Kubernetes, or standalone cloud VMs.

---

## 1. System Requirements

| Component | Minimum Specification | Recommended Specification |
| :--- | :--- | :--- |
| **CPU** | 4 vCPUs | 8 vCPUs (FFmpeg encoding) |
| **RAM** | 8 GB | 16 GB |
| **Disk** | 50 GB SSD | 200 GB NVMe (video storage) |
| **OS** | Ubuntu 22.04 LTS / Debian 12 | Ubuntu 24.04 LTS |
| **Docker** | Docker Engine 24.0+ & Compose v2 | Docker Engine 27.0+ |

---

## 2. Architecture Overview

```
                      Internet / Operator
                               │
                               ▼
               ┌─────────────────────────────────┐
               │  Frontend Container (Port 80)   │
               │  Nginx Reverse Proxy & Vite SPA │
               └────────────────┬────────────────┘
                                │
               ┌────────────────┴────────────────┐
               │
               ▼ /api/*
┌────────────────────────────────────────────────────────┐
│              Backend API (Port 8000)                   │
│             FastAPI 0.115+ Modular Monolith            │
└───────┬───────────────────────┬────────────────────────┘
        │                       │
        ▼                       ▼
┌──────────────┐        ┌──────────────┐
│  PostgreSQL  │        │ Redis Broker │
│  Port 5432   │        │  Port 6379   │
└──────────────┘        └───────┬──────┘
                                │
                        ┌───────┴────────┐
                        │                │
                        ▼                ▼
               ┌────────────────┐ ┌──────────────┐
               │ Celery Worker  │ │ Celery Beat  │
               │ FFmpeg & AI    │ │ 06:00 IST    │
               └────────────────┘ └──────────────┘
```

---

## 3. Environment Configuration (`.env`)

Create `.env` in the project root:

```ini
# Core Configuration
ENVIRONMENT=production
APP_ENV=production
DEBUG=false
SECRET_KEY=<generate-secure-random-64-character-string>
TOKEN_ENCRYPTION_KEY=<generate-fernet-urlsafe-base64-32byte-key>

# Database (Strict PostgreSQL in production)
DB_DIALECT=postgresql
POSTGRES_SERVER=postgres
POSTGRES_PORT=5432
POSTGRES_USER=vantyx_user
POSTGRES_PASSWORD=<strong-database-password>
POSTGRES_DB=vantyx

# Redis & Background Workers
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/1
CELERY_ALWAYS_EAGER=false
ORCHESTRATION_ENABLED=true
DAILY_PIPELINE_RUN_TIME=06:00
MAX_CONCURRENT_RENDERS=2

# YouTube Channel & Publishing
PRIMARY_CHANNEL_NAME=Astro Rebel
YOUTUBE_CLIENT_ID=<google-cloud-oauth-client-id>.apps.googleusercontent.com
YOUTUBE_CLIENT_SECRET=<google-cloud-oauth-client-secret>
YOUTUBE_REDIRECT_URI=https://app.vantyx.ai/distribution/oauth/callback
MOCK_YOUTUBE_PUBLISHING=false

# AI Multimodal Intelligence
GEMINI_API_KEY=<google-gemini-api-key>

# Storage & Timezone
DATA_DIR=/app/data
MEDIA_DIR=/app/data/media
EXPORT_DIR=/app/data/exports
TIMEZONE=Asia/Kolkata
```

---

## 4. Single-Command Deployment

```bash
# Clone the repository
git clone https://github.com/organization/vantyx.git
cd vantyx

# Build and start all services in detached mode
docker compose -f infrastructure/docker-compose.yml -f infrastructure/docker-compose.prod.yml up -d --build

# Run database migrations
docker compose exec backend alembic upgrade head

# Verify system readiness probe
curl http://localhost:8000/api/v1/health/ready
```

---

## 5. Storage Pruning & Retention Maintenance

Rendered video files are automatically retained for 30 days. To execute manual or scheduled storage pruning:

```bash
# Execute storage cleanup via backend CLI/curl
docker compose exec backend python -c "import asyncio; from app.modules.production.service import ProductionService; asyncio.run(ProductionService.cleanup_expired_storage(max_age_days=30))"
```
