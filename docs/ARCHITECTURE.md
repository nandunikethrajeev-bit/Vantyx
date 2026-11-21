# VANTYX Architecture Documentation

## 1. Architectural Philosophy: The Modular Monolith

VANTYX is architected as a **Modular Monolith**. Rather than decomposing early into distributed microservices or Kubernetes-orchestrated fleets, all domain capabilities reside within a single cohesive Python/FastAPI codebase partitioned into isolated modules.

### Why Modular Monolith?
1. **Zero Network Latency Between Domains**: Domain interactions occur via in-memory Python interfaces rather than JSON-RPC or REST overhead.
2. **Atomic Consistency**: Transactional boundaries can be shared or segmented using SQLAlchemy sessions without distributed transaction sagas.
3. **Future Extraction Path**: Each module has a defined service interface and strict dependency boundaries. When resource-intensive video processing or asynchronous scheduling scales out in later milestones, individual modules can be extracted into background workers or independent services without rewriting domain logic.

---

## 2. Module Responsibilities & Boundaries

The backend application is divided into six core domain modules within `backend/app/modules/`:

| Module | Core Responsibility | Planned Milestone |
| :--- | :--- | :--- |
| **`discovery`** | Approved creator channel ingestion, commercial-use rights validation, origin metadata, and legal attribution tracking. | Milestone 02 (Complete) |
| **`intelligence`** | Multimodal AI analysis of long-form videos: scene boundary segmentation, speech transcript extraction, audio dynamics, and event tagging. | Milestone 03 (Complete) |
| **`selection`** | Moment scoring algorithms: hook candidate evaluation, viral retention potential estimation, and timestamp boundary optimization. | Milestone 04 (Complete) |
| **`production`** | Media synthesis: dynamic 9:16 vertical re-framing, typographic subtitle rendering, color grading, audio normalization, and encoding. | Milestone 05 (Complete) |
| **`distribution`** | Publishing orchestration: authorized YouTube Data API integration, release schedule queues, title/metadata generation, and release dispatch. | Milestone 06 (Complete) |
| **`orchestration`** | End-to-end autonomous pipeline, Celery background tasks, Redis/eager execution, daily 4-slot plan, and execution recovery. | Milestone 07 (Complete) |
| **`analytics`** | Audience telemetry: ingestion of YouTube performance metrics (APV, retention curves) and closed-loop feedback calibration for moment selection. | Milestone 08 |

---

## 2.1 The Autonomous 7-Step Orchestration Pipeline

```
[ Step 1: Discovery ]
       │  (Polls Atom feeds / YouTube API, registers approved gameplay sources)
       ▼
[ Step 2: Rights Gate ]
       │  (Strict check: commercial rights, non-restricted editing scope, valid license)
       ▼
[ Step 3: Intelligence ]
       │  (Scene segmentation, transcript extraction, action intensity & excitement scoring)
       ▼
[ Step 4: Selection ]
       │  (Hook strength, retention modeling, context completeness, duplicate rejection)
       ▼
[ Step 5: Production ]
       │  (FFmpeg 9:16 vertical synthesis, 20px blurred backdrop, EBU R128 audio normalization)
       ▼
[ Step 6: Distribution ]
       │  (Publishing gate, blocks synthetic media, schedules across 4 daily slots in Asia/Kolkata)
       ▼
[ Step 7: Monitoring ]
          (Audits slot fulfillment (4/4 daily quota), summarizes logs, tracks operational health)
```

### Interservice Communication Rules
- Modules must communicate through explicit service interfaces (`service.py`), not by querying foreign database tables directly.
- Cross-cutting utilities (logging, security, database session managers) reside in `app/core/` and `app/db/`.
- No module may introduce hard dependencies on cloud SDKs or video downloading tools before their designated milestone.

---

## 3. API Structure

All client-facing REST APIs are versioned under `/api/v1` via FastAPI routers.

```
/api/v1/
├── health          (GET) -> Liveness probe (app name, version, environment, UTC timestamp)
└── health/ready    (GET) -> Readiness probe (probes PostgreSQL connectivity with 2s timeout)
```

### Centralized Error Envelope
All error responses adhere to a uniform structure:

```json
{
  "success": false,
  "error": {
    "code": "HTTP_404 | VALIDATION_ERROR | INTERNAL_SERVER_ERROR",
    "message": "Human-readable explanation",
    "field": "optional_field_name"
  },
  "details": null
}
```

---

## 4. Database Architecture

- **ORM**: SQLAlchemy 2.0 with asynchronous engine (`postgresql+asyncpg://`) for high-throughput endpoint handlers and synchronous engine (`postgresql://`) for Alembic migration commands.
- **Connection Management**: Centralized pool in `app/db/session.py` with pre-ping validation, customizable pool size, overflow limits, and non-blocking timeout handling.
- **Degraded Execution Mode**: If PostgreSQL is unreachable, the API continues to operate gracefully. The readiness probe captures the connection exception, logs the event with credential masking, and surfaces a degraded status code instead of crashing.
- **Migrations**: Alembic is initialized in `backend/alembic/` and configured to dynamically read connection settings from `app.core.config.settings.sync_database_url`.

---

## 5. Security & Isolation Safeguards

1. **Strict Credential Redaction**: Application logging intercepts log records and masks passwords, bearer tokens, API keys, cookies, and authorization parameters.
2. **CORS Governance**: Configurable allowed origin lists with validation.
3. **Pydantic Validation**: All environment variables and HTTP payloads are typed and validated on entry.
4. **Isolated Project Directory**: VANTYX operates exclusively within its own directory boundaries with zero external repository coupling.
