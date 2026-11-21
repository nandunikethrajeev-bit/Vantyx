# VANTYX Architectural & Technical Decisions Log (ADR)

## ADR-001: Resilient Database Strategy (PostgreSQL with Local SQLite Fallback)
- **Context**: In production and containerized environments, PostgreSQL 16 is the required database. In local development or isolated sandbox workstations where Docker or a system-level PostgreSQL service is offline, hardcoding a PostgreSQL requirement would crash the local server and block independent feature development.
- **Decision**: Implemented `DB_DIALECT: str = "auto"` in `app.core.config.Settings`. In `auto` mode, the application probes TCP port 5432 with a 0.2s timeout. If PostgreSQL is active, it connects via `asyncpg`. If PostgreSQL is offline, it automatically initializes a persistent local SQLite store via `aiosqlite` at `./data/vantyx.db`.
- **Consequences**: Zero code drift between local development and cloud deployment. 100% of SQLAlchemy 2.0 async queries, relationships, and transaction lifecycles remain identical.

## ADR-002: Zero-Credential Ingestion Engine via YouTube Atom XML Feeds
- **Context**: The YouTube Data API v3 enforces strict daily quota limits (10,000 units/day) and requires developer credentials. In local or newly provisioned instances without pre-configured API keys, creator channel monitoring would fail.
- **Decision**: Implemented a dual-path discovery engine in `DiscoveryService`. When `YOUTUBE_API_KEY` is present, it uses the official API. When not set, it queries YouTube's official public Atom XML feeds (`https://www.youtube.com/feeds/videos.xml?channel_id={channel_id}`).
- **Consequences**: Autonomous discovery works out of the box with zero external API credentials or cost, consuming zero YouTube Data API quota units.

## ADR-003: Strict Pipeline Legal Eligibility Gate
- **Context**: Public availability on YouTube does not confer permission to download, clip, or republish content. VANTYX must protect the Astro Rebel channel against copyright strikes and legal liability.
- **Decision**: Created a strict gating service (`DiscoveryService.evaluate_eligibility`) backed by the `RightsRecord` entity. Media is strictly blocked from the AI intelligence and video production queues unless:
  1. `permission_status` is explicitly `"authorized"` or `"own_gameplay"`.
  2. `commercial_use_allowed` is `True`.
  3. `allowed_editing_scope` is not `"restricted"`.
  4. The permission has not passed its `expires_at` timestamp.
- **Consequences**: Guarantees zero unauthorized media can accidentally progress to video production or publishing.

## ADR-004: Self-Contained FFmpeg Engine via `imageio-ffmpeg`
- **Context**: Windows workstations often lack a global `ffmpeg.exe` installed in system `PATH`. Requiring manual system PATH modifications introduces external environment brittleness.
- **Decision**: Added `imageio-ffmpeg` to project dependencies, providing a standalone, tested, bundled 64-bit FFmpeg executable directly within the Python environment.
- **Consequences**: Video clipping, 9:16 re-framing, and audio processing can execute immediately on any workstation without external OS package managers.

## ADR-005: Strict Synthetic Media Gate at Publishing Queue
- **Context**: During development and testing of video processing pipelines, synthetic test media (e.g. FFmpeg `testsrc2` or `sine` audio) is generated to verify rendering without downloading multi-gigabyte remote gameplay files. If synthetic test media accidentally reached the publishing queue, placeholder test videos would be uploaded to the official Astro Rebel YouTube channel.
- **Decision**: Added `is_synthetic: bool = False` to `VideoSource` and `RenderJob`. The Distribution module's `verify_publishing_eligibility` strictly enforces that both `job.is_synthetic` and `source.is_synthetic` are `False`. Any attempt to schedule or upload synthetic media raises `PublishingEligibilityError` and is rejected with HTTP 400.
- **Consequences**: Impossible for test placeholders to ever enter the Astro Rebel YouTube publishing queue or be uploaded to YouTube.

## ADR-006: Resilient Timezone Handling for Asia/Kolkata Cadence
- **Context**: VANTYX targets publishing 4 Shorts per day across fixed daily slots (09:00, 13:00, 17:00, 21:00) in the `Asia/Kolkata` timezone (IST, UTC+05:30). Windows operating systems often lack system IANA timezone databases, causing `ZoneInfoNotFoundError: 'No time zone found with key Asia/Kolkata'`.
- **Decision**: Added `tzdata` to backend dependencies and encapsulated all timezone operations in `TimezoneHelper`. If `zoneinfo.ZoneInfo("Asia/Kolkata")` is available, it uses the IANA database; otherwise, it automatically falls back to `timezone(timedelta(hours=5, minutes=30), name="Asia/Kolkata")`.
- **Consequences**: 100% resilient timezone calculations across Windows, macOS, Linux, and Docker containers without crashes or external timezone dependencies.

## ADR-007: Safe Verified Mock Publishing Provider
- **Context**: Google OAuth 2.0 authorization requires external user consent and Google Cloud Console developer credentials. In CI/CD pipelines, automated testing, or offline sandbox environments, external YouTube network calls cannot and should not be made.
- **Decision**: Implemented `MockPublishingProvider` in `DistributionService`. When `MOCK_YOUTUBE_PUBLISHING=True` or `force_mock=True`, the publishing engine simulates the full chunked upload lifecycle, records telemetry in `UploadJob`, generates a clearly flagged `mock_yt_{id}` identifier, marks `is_mock=True`, and sets the schedule status to `published`.
- **Consequences**: Full end-to-end integration testing and automated verification without making external network calls or requiring active Google OAuth credentials.

## ADR-008: Persistent Multi-Stage Orchestration Architecture with Eager Queue Fallback
- **Context**: Autonomous orchestration coordinates 6 subsystems across 7 sequential stages (Discovery, Rights, Intelligence, Selection, Production, Distribution, Monitoring). If a broker like Redis is offline during local development or unit testing, asynchronous queue operations must not fail or stall.
- **Decision**: Implemented Celery worker integration (`app.core.celery_app`) with dynamic broker detection. If Redis responds on port 6379, it uses Redis. If Redis is unavailable or `CELERY_ALWAYS_EAGER=True`, Celery operates in eager synchronous mode (`task_always_eager=True`). All execution state is persisted directly in PostgreSQL/SQLite (`WorkflowRun`, `WorkflowStep`, `BackgroundJob`, `JobAttempt`, `JobExecutionLog`, `DailyPublishingPlan`) rather than relying on in-memory queue state.
- **Consequences**: Complete pipeline resiliency. Workflows survive process restarts, can be paused/cancelled/recovered deterministically, and test suites execute with zero daemon dependencies.

## ADR-009: Production Throttling and Resource Safeguards
- **Context**: 9:16 vertical video synthesis (FFmpeg scaling, boxblur background filtering, EBU R128 audio normalization) is compute and disk intensive. Unconstrained rendering could exhaust system memory or disk space.
- **Decision**: Implemented strict resource limits in `OrchestrationService`:
  1. `MAX_CONCURRENT_RENDERS: int = 2` throttles simultaneous render jobs.
  2. Free disk space is verified before render operations using `shutil.disk_usage` (minimum 1.0 GB required).
  3. Master automation kill-switch (`ORCHESTRATION_ENABLED: bool = False`) defaults to disabled, requiring explicit operator enablement.
- **Consequences**: Prevents CPU spikes, memory exhaustion, and out-of-disk failures during autonomous batches.

## ADR-010: Audience Performance Intelligence & Calibrated Closed-Loop Feedback Engine
- **Context**: Autonomous moment selection initially relies on heuristic or multimodal AI scores (hook velocity, action density, audio quality). Without empirical audience retention data, scoring algorithms cannot learn from real-world viewer behavior. However, unconstrained automated feedback risks amplifying noisy or small-sample statistical artifacts (e.g., declaring a random 3 AM publishing slot or single outlier clip superior).
- **Decision**: Implemented a multi-tier analytics and feedback architecture:
  1. **Historical Snapshot Persistence**: `VideoAnalyticsSnapshot` and `ChannelAnalyticsSnapshot` store time-series metrics with date-based deduplication and explicit tracking of YouTube's 24-48h reporting lag (`is_delayed_reporting=True`).
  2. **Correlation vs Causation Guardrails**: Insights explicitly compute sample size $N$ and confidence levels (`low` for $N < 3$, `medium` for $3 \le N < 10$, `high` for $N \ge 10$), warning that time-of-day variations reflect platform distribution surfaces rather than inherent content quality.
  3. **Strict Bounded Feedback Multipliers**: Feedback multipliers for content categories, duration buckets, and hook velocity are strictly clamped to $[1.0 - \text{max\_impact}, 1.0 + \text{max\_impact}]$ (default $\pm 15\%$) and require $N \ge 3$ samples.
  4. **Fail-Safe & Explainable**: The feedback engine defaults to disabled (`ANALYTICS_FEEDBACK_ENABLED=False`) and every adjusted score is transparently recorded in `CandidateClip.rationale`.
- **Consequences**: Enables data-driven optimization without risking model drift, runaway biases, or small-sample distortions.

## ADR-011: Production Hardening, Token Encryption at Rest, Multi-Aspect FFmpeg & Cloud Deployment
- **Context**: Transitioning VANTYX into an operational platform required eliminating development shortcuts:
  1. Silent fallback to SQLite allowed development without PostgreSQL, but in production, SQLite would lose concurrency, durability, and multi-worker safety.
  2. OAuth refresh and access tokens stored in plaintext exposed credentials in database dumps.
  3. Video inputs may arrive in various aspect ratios (16:9 widescreen, 21:9 ultra-wide, 4:3, or native 9:16 vertical); hardcoded 16:9 scaling distorted non-standard aspect ratios.
  4. Background jobs required discrete worker task declarations and a persistent Beat scheduler rather than in-process execution.
  5. Containerization required multi-service orchestration with proper health checks and persistent volume management.
- **Decision**:
  1. **Strict Persistence Enforcement**: `Settings.async_database_url` and `Settings.sync_database_url` enforce strict PostgreSQL validation. In production (`APP_ENV="production"` or `ENVIRONMENT="production"`), SQLite and in-memory configurations immediately raise `RuntimeError`.
  2. **AES/Fernet Token Encryption at Rest**: Implemented `encrypt_token` and `decrypt_token` using `cryptography.fernet.Fernet`. All YouTube OAuth access and refresh tokens are encrypted before database persistence. Legacy and mock tokens are handled gracefully with zero breaking changes.
  3. **Universal Aspect-Ratio Agnostic Filtergraph**: Implemented dynamic scaling: background scales with `force_original_aspect_ratio=increase` cropped to 1080x1920 with boxblur, foreground scales with `force_original_aspect_ratio=decrease`, and native 9:16 vertical skips blur. Implemented `cleanup_expired_storage` purging renders older than 30 days.
  4. **Celery Worker & Scheduler Hardening**: Registered Celery background tasks in `app.tasks.*`, added daily Beat schedule at 06:00 IST (`DAILY_PIPELINE_RUN_TIME`), and enforced distributed Redis broker requirement in production.
  5. **Readiness Telemetry**: Upgraded `/api/v1/health/ready` probe to evaluate 6 distinct subsystems: PostgreSQL, Redis broker, Celery worker heartbeat, YouTube OAuth, AI provider, and disk capacity.
  6. **Multi-Service Cloud Containerization**: Authored production `backend/Dockerfile` (multi-stage Python 3.12-slim, system FFmpeg, non-root user `vantyx`), `frontend/Dockerfile` (Node 22 builder + Nginx Alpine reverse proxy), `infrastructure/docker-compose.yml`, and `infrastructure/docker-compose.prod.yml`.
- **Consequences**: The platform is hardened against credential leaks, aspect ratio distortions, silent persistence degradations, and queue failures, fully ready for containerized cloud deployment.
