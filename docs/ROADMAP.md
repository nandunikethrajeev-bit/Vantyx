# VANTYX Product Roadmap

```
                       VANTYX PLATFORM ROADMAP
                                  │
┌─────────────────────────────────┴─────────────────────────────────┐
│                                                                   │
▼                                                                   ▼
PHASE 1: FOUNDATION & INGESTION                     PHASE 2: PRODUCTION & SCALE
M01: Engineering Foundation  [COMPLETE]             M05: Video Production
M02: Source Discovery                               M06: Scheduling & Publishing
M03: AI Intelligence                                M07: Cloud & Analytics
M04: Clip Selection
```

---

## Milestone 01: Engineering Foundation & Modular Architecture (Current)
**Objective**: Establish a clean, isolated, maintainable production-conscious modular monolith with zero external coupling.
- [x] Project structure initialization and dependency isolation
- [x] FastAPI modular monolith entrypoint and lifecycle management
- [x] Pydantic Settings configuration with strict validation and safe defaults
- [x] Structured logging with automatic sensitive credential redaction
- [x] SQLAlchemy 2.0 async/sync database session manager and Alembic migrations setup
- [x] API health probes (`/api/v1/health` and `/api/v1/health/ready`) with graceful degradation
- [x] Modular domain boundary packages (`discovery`, `intelligence`, `selection`, `production`, `distribution`, `analytics`)
- [x] Dark, cinematic, minimal React + Vite + TypeScript frontend shell with genuine backend telemetry
- [x] Comprehensive test suites (Pytest backend, Vitest + React Testing Library frontend)
- [x] CI workflow configuration (`.github/workflows/ci.yml`)

---

## Milestone 02: Source Discovery & Permission Rights (Complete)
**Objective**: Autonomous ingestion of approved GTA 6 gameplay creators with strict licensing and attribution controls.
- [x] Creator channel registry and whitelisting engine (`Creator` model and API)
- [x] Commercial-use rights verification and licensing proof storage (`RightsRecord` model)
- [x] Video metadata ingestion (title, description, duration, upload date, thumbnails)
- [x] Resilient dual-path discovery engine (YouTube Data API v3 + zero-credential public Atom feeds)
- [x] Candidate video queue with legal eligibility validation gate (`evaluate_eligibility`)
- [x] Interactive Discovery workspace in frontend with real-time sweep actions, modals, and tables
- [x] Persistent database schema supporting PostgreSQL and resilient SQLite fallback

---

## Milestone 03: Multimodal Media Intelligence (Complete)
**Objective**: Deep AI understanding of ingested gameplay videos.
- [x] Visual scene boundary detection and shot transitions
- [x] High-accuracy transcript extraction and timestamp alignment
- [x] Audio dynamic range analysis (speech vs gameplay sound vs excitement)
- [x] Gameplay event classification (high-speed pursuits, missions, funny glitches)
- [x] Pluggable provider architecture (Gemini + zero-cost Heuristic engine)
- [x] Legal rights gating and idempotent analysis caching
- [x] Interactive Intelligence workspace with scene cards, intensity meters, and tags

---

## Milestone 04: Clip Selection & Viral Scoring
**Objective**: Algorithmic ranking and boundary optimization for candidate moments.
- [ ] Hook potential scoring (first 3-second retention signals)
- [ ] Narrative cohesion and climax boundary determination
- [ ] Duration targeting (ideal 30s to 58s vertical Shorts formats)
- [ ] Duplicate and redundant segment suppression
- [ ] Candidate ranking pipeline prioritizing high-engagement segments

---

## Milestone 05: Vertical Video Production & Rendering
**Objective**: High-fidelity automated rendering pipeline converting horizontal gameplay to cinematic vertical Shorts.
- [ ] Dynamic 9:16 re-framing with intelligent subject tracking
- [ ] Typographic subtitle generation with stylized font rendering and word-level highlighting
- [ ] Audio mastering: speech equalization, music ducking, and loudness normalization (-14 LUFS)
- [ ] Cinematic color grading and subtle vignette styling
- [ ] Isolated render task execution and media caching

---

## Milestone 06: Distribution & Channel Publishing
**Objective**: Secure, automated publishing pipeline to authorized YouTube channel.
- [ ] YouTube Data API v3 OAuth2 authorization and token rotation service
- [ ] Editorial release calendar and publishing schedule queue
- [ ] Algorithmic metadata generation (optimized titles, descriptions, hashtags)
- [ ] Thumbnail extraction and preview generation
- [ ] Automated upload dispatch with rate limit safeguards and rollback protection

---

## Milestone 07: Cloud Deployment & Closed-Loop Analytics
**Objective**: Channel telemetry ingestion and feedback loop calibration for continuous performance enhancement.
- [ ] Cloud deployment (containerization and background worker isolation)
- [ ] YouTube Analytics API ingestion (views, APV, retention curves, click-through rates)
- [ ] Closed-loop feedback: calibrate Milestone 04 selection weights using empirical retention data
- [ ] Executive performance dashboard and channel health telemetry
