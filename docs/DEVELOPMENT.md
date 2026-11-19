# VANTYX Development Guide

## 1. Prerequisites

Ensure the following tools are installed on your workstation:
- **Python**: Version 3.12 or newer.
- **Node.js**: Version 20.x or newer (v22+ recommended).
- **npm**: Version 10.x or newer.
- **Git**: Version 2.40 or newer.
- **Docker & Docker Compose**: (Optional, for local PostgreSQL container).

---

## 2. Environment Setup

### 1. Clone & Configuration
Ensure you are inside the `VANTYX` root directory:

```bash
cp .env.example .env
```

Review `.env` to customize local bind ports, database names, or CORS allowed origins.

### 2. Backend Environment
```bash
# Navigate to backend directory
cd backend

# Create dedicated virtual environment
python -m venv .venv

# Activate virtual environment
# Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Windows (cmd):
.venv\Scripts\activate.bat
# Linux / macOS:
source .venv/bin/activate

# Install backend dependencies in editable mode
pip install -e ".[dev]"
```

### 3. Frontend Environment
```bash
# Navigate to frontend directory
cd frontend

# Install npm dependencies
npm install
```

### 4. Database Setup (Optional)
If Docker is installed:
```bash
cd infrastructure
docker compose up -d
```
Verify the container is healthy:
```bash
docker compose ps
```

---

## 3. Running Locally

### Start Backend Development Server
```bash
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```
Endpoints:
- API Root: `http://127.0.0.1:8000/`
- Interactive OpenAPI Docs: `http://127.0.0.1:8000/docs`
- Liveness Probe: `http://127.0.0.1:8000/api/v1/health`
- Readiness Probe: `http://127.0.0.1:8000/api/v1/health/ready`

### Start Frontend Development Server
```bash
cd frontend
npm run dev
```
Open `http://127.0.0.1:5173` in your browser.

---

## 4. Testing & Verification

### Run Backend Unit & Integration Tests
```bash
cd backend
python -m pytest tests -v
```

### Run Frontend Unit Tests
```bash
cd frontend
npm test
```

### Build Frontend Production Bundle
```bash
cd frontend
npm run build
```

---

## 5. Troubleshooting

### Problem: PostgreSQL is offline or Docker is not installed
- **Behavior**: `/api/v1/health/ready` reports `status: degraded` and `components.database.status: unreachable`.
- **Resolution**: This is expected when PostgreSQL is not running. The application handles database disconnects gracefully. If you need local database persistence, install PostgreSQL 16 locally or start the Docker container in `infrastructure/`.

### Problem: CORS errors in browser console
- **Behavior**: `Access to fetch at ... from origin 'http://localhost:5173' has been blocked by CORS policy`.
- **Resolution**: Verify that `CORS_ORIGINS` in your `.env` file includes your frontend origin (e.g., `http://localhost:5173,http://127.0.0.1:5173`).

### Problem: Sensitive credentials appear in log output
- **Resolution**: All logs passed through `app.core.logging.logger` automatically apply regex masking. Ensure you never bypass the configured logger by using bare `print()` statements for secret data.
