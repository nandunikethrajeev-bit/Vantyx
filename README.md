# VANTYX

> **The intelligence behind every moment.**

VANTYX is an autonomous media intelligence platform designed to discover authorized gaming content, analyze long-form gameplay videos using multimodal AI, extract high-energy narrative moments, synthesize broadcast-grade 9:16 vertical Shorts, and publish them to YouTube on an automated daily schedule.

---

## System Architecture

VANTYX is structured as a **modular monolith** with clean, decoupled domain boundaries:

```
VANTYX Modular Architecture
├── Discovery: GTA 6 video feed monitoring & creator permission validation
├── Intelligence: Multimodal AI scene segmentation & audio energy scoring
├── Selection: Hook detection, retention ranking & candidate filtering
├── Production: 9:16 vertical synthesis, dynamic aspect ratios, EBU R128 audio
├── Distribution: YouTube OAuth 2.0 authorization, token encryption & release slots
├── Orchestration: Redis/Celery queue coordination, 7-step pipeline & Beat scheduler
└── Analytics: YouTube Analytics ingestion, lag handling & closed-loop feedback
```

---

## Security & Operational Safeguards

- **Strict PostgreSQL Persistence**: In production environments (`APP_ENV=production`), silent fallback to SQLite is blocked.
- **Token Encryption at Rest**: YouTube OAuth access and refresh tokens are encrypted using AES/Fernet encryption (`cryptography`).
- **Path Traversal Protection**: Media streaming endpoints enforce strict containment within authorized export directories.
- **Synthetic Media Gate**: Test placeholders generated during development are strictly rejected from YouTube distribution queues.
- **Log Credential Redaction**: All API keys, bearer tokens, cookies, and secret headers are automatically filtered from log outputs.
- **Bounded Feedback Multipliers**: Closed-loop analytics feedback is capped to $\pm 15\%$ with minimum sample size ($N \ge 3$) safeguards.

---

## Quickstart (Development)

### Backend
```bash
cd backend
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -e .
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

### Frontend
```bash
cd frontend
npm install
npm run dev
```

---

## Cloud Deployment (Docker Compose)

```bash
# Build and run the entire stack (Postgres, Redis, API, Worker, Beat, Frontend)
docker compose -f infrastructure/docker-compose.yml -f infrastructure/docker-compose.prod.yml up -d --build

# Run database migrations
docker compose exec backend alembic upgrade head

# Verify system readiness
curl http://localhost:8000/api/v1/health/ready
```

---

## Verification Test Suites

```bash
# Backend unit & integration test suites (74 tests)
cd backend && pytest -v

# Frontend test suites (25 tests) & build verification
cd frontend && npm test -- --run && npm run build
```
