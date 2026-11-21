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
