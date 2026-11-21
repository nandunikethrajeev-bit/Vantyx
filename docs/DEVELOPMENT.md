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

## 4. Google Cloud Console & YouTube OAuth Setup

To enable live autonomous publishing to the **Astro Rebel** YouTube channel:

1. **Open Google Cloud Console**: Navigate to [Google Cloud Console](https://console.cloud.google.com/).
2. **Enable YouTube Data API v3**:
   - Go to *APIs & Services > Library*.
   - Search for **YouTube Data API v3** and click **Enable**.
3. **Configure OAuth Consent Screen**:
   - Go to *APIs & Services > OAuth consent screen*.
   - Select User Type: **External**.
   - Add Test Users: Include the Google account associated with the **Astro Rebel** channel.
   - Add Scopes: `https://www.googleapis.com/auth/youtube.upload`.
4. **Create OAuth 2.0 Credentials**:
   - Go to *APIs & Services > Credentials*.
   - Click **Create Credentials > OAuth Client ID**.
   - Application Type: **Web application**.
   - Authorized Redirect URI:
     ```
     http://localhost:8000/api/v1/distribution/oauth/callback
     ```
5. **Add Credentials to `.env`**:
   ```env
   YOUTUBE_CLIENT_ID="your_client_id.apps.googleusercontent.com"
   YOUTUBE_CLIENT_SECRET="your_client_secret"
   YOUTUBE_REDIRECT_URI="http://localhost:8000/api/v1/distribution/oauth/callback"
   MOCK_YOUTUBE_PUBLISHING=False
   ```

*Note: If credentials are not set, VANTYX operates safely in verified Mock Publishing mode without network errors.*

---

## 5. Background Workers & Autonomous Orchestration

VANTYX uses Celery for background asynchronous execution and Redis for transient queue coordination.

### Celery Eager Execution vs Redis Worker
- By default or when Redis is offline, `CELERY_ALWAYS_EAGER=True` executes tasks in-process synchronously. Zero external daemons are required for development, CI/CD, or automated testing.
- For production multi-process execution:
  ```bash
  # Start Celery worker in backend directory
  cd backend
  celery -A app.core.celery_app worker --loglevel=info --concurrency=2
  ```

### Master Automation Switch
Automation is disabled by default for safety (`ORCHESTRATION_ENABLED=False`).
- Enable via UI: Toggle the master switch in the **Orchestration** workspace.
- Enable via API:
  ```bash
  curl -X PATCH http://127.0.0.1:8000/api/v1/orchestration/config \
       -H "Content-Type: application/json" \
       -d '{"orchestration_enabled": true}'
  ```

---

## 6. Testing & Verification

### Run Backend Unit & Integration Tests
```bash
# Run full suite (58 tests across all modules)
backend\.venv\Scripts\pytest -v backend/tests/
```

### Run Frontend Unit Tests & Production Build
```bash
# Run unit tests (25 tests across 10 suites)
npm test --prefix frontend -- --run

# Run TypeScript production build
npm run build --prefix frontend
```
