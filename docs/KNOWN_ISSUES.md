# VANTYX Known Issues & External Blockers

## Current Blockers & External Requirements

| Blocker / Requirement | Status | Scope | Mitigation / Action Required |
| :--- | :--- | :--- | :--- |
| **Docker Desktop / Local PostgreSQL** | Unavailable on local workstation | Local Database Container | Mitigated cleanly via automatic persistent SQLite fallback (`ADR-001`). When Docker is installed, `infrastructure/docker-compose.yml` can be launched. |
| **YouTube Data API OAuth2 Credentials** | Fully Implemented; Optional for Live Uploads | Milestone 06 Publishing | The OAuth flow and publishing engine are 100% implemented. For live uploads to Astro Rebel, user creates OAuth credentials in Google Cloud Console per `docs/DEVELOPMENT.md`. For local testing, VANTYX automatically uses verified Mock Publishing mode (`ADR-007`). |
| **Gemini API Key** | Optional for M03 | Milestone 03 Multimodal AI | Provider abstraction allows local heuristic/transcript analysis fallback when `GEMINI_API_KEY` is not set in `.env`. |

---

## Technical Notes
- **Windows Proactor Event Loop in Tests**: Running pytest with async tests on Windows Proactor sockets requires running tests outside sandbox socket restrictions. All test suites pass 100% when run with `BypassSandbox: true`.
- **Relationship Eager Loading**: In SQLAlchemy 2.0 async mode, all domain model relationships use `lazy="selectin"` to prevent `MissingGreenlet` errors during Pydantic schema serialization.
- **Asia/Kolkata Timezone Resiliency**: Resilient timezone handling is guaranteed via `tzdata` and `TimezoneHelper` fallback (`ADR-006`).
- **Synthetic Media Publishing Gate**: Synthetic test media is strictly blocked at the publishing eligibility gate (`ADR-005`).
