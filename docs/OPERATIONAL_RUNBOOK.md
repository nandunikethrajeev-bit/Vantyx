# VANTYX — Operational Runbook

This runbook provides on-call engineers and operators with standard operating procedures for monitoring, incident triage, and routine maintenance of VANTYX.

---

## 1. System Health Telemetry

VANTYX exposes two diagnostic probes:

### Liveness Probe (`GET /api/v1/health`)
Returns HTTP 200 with runtime environment metadata:
```json
{
  "status": "ok",
  "app": "VANTYX",
  "version": "0.1.0",
  "environment": "production",
  "timestamp": "2026-11-21T18:30:00Z"
}
```

### Comprehensive Readiness Probe (`GET /api/v1/health/ready`)
Evaluates 6 subsystem boundaries:
```json
{
  "status": "ready",
  "timestamp": "2026-11-21T18:30:00Z",
  "components": {
    "database": {
      "status": "healthy",
      "message": "PostgreSQL connection active and responsive",
      "latency_ms": 1.45
    },
    "redis": {
      "status": "healthy",
      "message": "Redis broker online at redis://redis:6379/0",
      "latency_ms": 0.82
    },
    "celery_worker": {
      "status": "healthy",
      "message": "Active distributed Celery workers: 2",
      "latency_ms": null
    },
    "youtube_oauth": {
      "status": "healthy",
      "message": "OAuth credentials configured (Client ID active)",
      "latency_ms": null
    },
    "ai_provider": {
      "status": "healthy",
      "message": "Google Gemini Multimodal API active",
      "latency_ms": null
    },
    "storage": {
      "status": "healthy",
      "message": "Storage path /app/data: 142.5 GB free",
      "latency_ms": null
    }
  }
}
```

---

## 2. Common Incident Response Playbooks

### Incident A: Celery Worker Pool Offline
- **Symptom**: `/api/v1/health/ready` reports `celery_worker: unreachable`.
- **Diagnosis**:
  ```bash
  docker compose logs -n 100 celery_worker
  ```
- **Remediation**:
  ```bash
  # Check Redis connectivity
  docker compose exec redis redis-cli ping
  # Restart worker daemon
  docker compose restart celery_worker
  ```

### Incident B: Gemini API Rate Limit / Quota Exhaustion (HTTP 429)
- **Symptom**: Logs show `Gemini rate limited (HTTP 429). Backing off...`.
- **Behavior**: `GeminiAIProvider` automatically executes 3 retries with exponential backoff (1s, 2s, 4s). If quota remains exhausted, it gracefully falls back to `HeuristicAIProvider`, tagging scenes with `provider_used="heuristic_fallback"`.
- **Remediation**:
  - The pipeline continues executing without crashing.
  - Review Google Cloud Console quota for Gemini 2.5 Flash.

### Incident C: Storage Capacity Degraded (< 1.0 GB Free)
- **Symptom**: Readiness probe reports `storage: degraded`.
- **Diagnosis**: Check disk usage in container volume:
  ```bash
  docker compose exec backend df -h /app/data
  ```
- **Remediation**:
  Run storage cleanup to purge temporary exports older than 7 days:
  ```bash
  docker compose exec backend python -c "import asyncio; from app.modules.production.service import ProductionService; asyncio.run(ProductionService.cleanup_expired_storage(max_age_days=7))"
  ```

### Incident D: YouTube Account Disconnection or Revocation
- **Action**:
  To disconnect and revoke channel access cleanly:
  Call `POST /api/v1/distribution/disconnect`. The service issues a token revocation request to `https://oauth2.googleapis.com/revoke` and purges encrypted tokens from PostgreSQL.
