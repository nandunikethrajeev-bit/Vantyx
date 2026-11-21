# VANTYX

> *"The intelligence behind every moment."*

VANTYX is an autonomous media intelligence platform designed to discover, analyze, select, produce, and publish high-impact vertical video content from approved GTA 6 gameplay creators and sources.

Milestones 01 through 08 are fully implemented and verified:
- **Milestone 01**: Engineering Foundation & Modular Monolith
- **Milestone 02**: Video Source Discovery & Legal Rights Intelligence
- **Milestone 03**: Multimodal AI Intelligence Engine (Gemini / Heuristic)
- **Milestone 04**: Moment Selection & Multi-Factor Ranking
- **Milestone 05**: Video Production Engine (FFmpeg 9:16 Vertical Video Synthesis)
- **Milestone 06**: Distribution Engine & Official YouTube Publishing Integration (Astro Rebel)
- **Milestone 07**: Autonomous Orchestration & End-to-End Workflow Engine
- **Milestone 08**: Analytics Intelligence & Performance Feedback Engine

---

## 1. Product Identity

- **Aesthetic**: Obsidian black (`#090909`), charcoal surfaces (`#171717`), muted amber accents (`#D49A45`), warm neutral typography.
- **Tone**: Dark, mysterious, cinematic, technically sophisticated, minimal and deliberate.
- **Target Channel**: Astro Rebel (4 quality Shorts/day at 09:00, 13:00, 17:00, 21:00 IST).

---

## 2. Technology Stack

### Frontend
- **Framework**: React 18 + TypeScript + Vite
- **Styling**: Tailwind CSS (custom VANTYX palette and typography)
- **Icons**: Lucide React
- **Testing**: Vitest + React Testing Library + jsdom

### Backend
- **Language**: Python 3.12+
- **Framework**: FastAPI (modular monolith routing)
- **Settings**: Pydantic Settings (strict environment validation)
- **Database ORM**: SQLAlchemy 2.0 (asyncpg / psycopg2)
- **Migrations**: Alembic
- **Testing**: Pytest + Pytest-Asyncio + HTTPX

### Infrastructure & Tooling
- **Database**: PostgreSQL 16 (configured via Docker Compose in `infrastructure/`)
- **CI/CD**: GitHub Actions workflow (`.github/workflows/ci.yml`)

---

## 3. Repository Structure

```
VANTYX/
├── frontend/                     # React + Vite + TypeScript application
│   ├── src/
│   │   ├── app/                  # App shell & layout coordination
│   │   ├── components/
│   │   │   ├── layout/           # Sidebar, Header
│   │   │   └── ui/               # BrandMark, StatusBadge
│   │   ├── features/
│   │   │   ├── overview/         # Platform Foundation telemetry view
│   │   │   └── placeholders/     # Domain module boundary placeholders
│   │   ├── hooks/                # useSystemHealth telemetry hook
│   │   ├── lib/                  # Fetch API client
│   │   ├── styles/               # Tailwind stylesheet
│   │   ├── types/                # TypeScript interface contracts
│   │   └── main.tsx              # DOM entrypoint
│   ├── tests/                    # Vitest test suite
│   ├── package.json
│   ├── tsconfig.json
│   └── vite.config.ts
│
├── backend/                      # FastAPI Modular Monolith
│   ├── app/
│   │   ├── api/v1/               # Versioned REST endpoints (/health, /health/ready)
│   │   ├── core/                 # Config (Pydantic Settings), Logging, Security
│   │   ├── db/                   # SQLAlchemy Base, session manager, connectivity probe
│   │   ├── modules/              # Domain boundaries (discovery, intelligence, etc.)
│   │   ├── schemas/              # Pydantic request/response schemas
│   │   ├── services/             # Shared orchestration services
│   │   └── main.py               # FastAPI application factory & lifespan
│   ├── alembic/                  # Database migration configuration & scripts
│   ├── tests/
│   │   ├── unit/                 # Unit tests (config, logging redaction, modules)
│   │   └── integration/          # Integration tests (health endpoints, CORS, errors)
│   ├── pyproject.toml
│   └── alembic.ini
│
├── infrastructure/
│   └── docker-compose.yml        # Local PostgreSQL container service
│
├── docs/
│   ├── ARCHITECTURE.md           # Modular monolith design & boundaries
│   ├── DEVELOPMENT.md            # Prerequisites & local setup guide
│   └── ROADMAP.md                # Multi-milestone execution plan
│
├── .github/workflows/ci.yml      # CI lint, test, and build pipeline
├── .env.example                  # Safe configuration defaults template
├── .gitignore                    # Secrets, caches, and build artifact exclusions
└── README.md                     # Platform overview
```

---

## 4. Quickstart Guide

### Prerequisites
- Python 3.12+
- Node.js 20+ and npm
- Docker / Docker Compose (optional for local PostgreSQL)

### 1. Environment Setup
Copy the template configuration into `.env`:

```bash
cp .env.example .env
```

### 2. Backend Initialization
Create a virtual environment, activate it, and install dependencies:

```bash
cd backend
python -m venv .venv

# On Windows:
.venv\Scripts\activate
# On Linux/macOS:
source .venv/bin/activate

pip install -e ".[dev]"
```

Start the backend API server:
```bash
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
The API is available at `http://127.0.0.1:8000`. Interactive OpenAPI documentation is accessible at `http://127.0.0.1:8000/docs`.

### 3. Frontend Initialization
In a separate terminal:

```bash
cd frontend
npm install
npm run dev
```
The frontend application will start on `http://127.0.0.1:5173`.

### 4. Database Setup (Optional)
To launch a local PostgreSQL container:

```bash
cd infrastructure
docker compose up -d
```
When Docker is not available or PostgreSQL is not running, the platform operates in a graceful degraded mode: `/api/v1/health` reports `status: ok` and `/api/v1/health/ready` reports `status: degraded` with an informative message.

---

## 5. Verification Commands

### Run Backend Tests
```bash
cd backend
pytest tests -v
```

### Run Frontend Tests
```bash
cd frontend
npm test
```

### Build Frontend Production Artifact
```bash
cd frontend
npm run build
```

---

## 6. Architecture & Security Highlights

- **Zero Hardcoded Secrets**: All configuration is parsed and validated via Pydantic Settings.
- **Log Masking**: Custom logging formatter redacts passwords, tokens, API keys, cookies, and bearer tokens.
- **Centralized Error Envelope**: Consistent `{ success: false, error: { code, message } }` schema for all HTTP and validation exceptions.
- **Genuine System Status**: The frontend queries the backend `/api/v1/health` and `/api/v1/health/ready` endpoints in real time, displaying actual system latency and database connectivity.
