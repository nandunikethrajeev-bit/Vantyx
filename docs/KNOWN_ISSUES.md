# VANTYX Known Issues & External Blockers

## Current Blockers & External Requirements

| Blocker / Requirement | Status | Scope | Mitigation / Action Required |
| :--- | :--- | :--- | :--- |
| **Docker Desktop / Local PostgreSQL** | Unavailable on local workstation | Local Database Container | Mitigated cleanly via automatic persistent SQLite fallback (`ADR-001`). When Docker is installed, `infrastructure/docker-compose.yml` can be launched. |
| **YouTube Data API OAuth2 Credentials** | Pending User Authorization | Milestone 06 Publishing | Required before automated publishing can upload to the live Astro Rebel channel. Video discovery, rights governance, AI intelligence, and local video rendering operate independently. |
| **Gemini API Key** | Optional for M03 | Milestone 03 Multimodal AI | Provider abstraction will allow local heuristic/transcript analysis fallback when `GEMINI_API_KEY` is not set in `.env`. |

---

## Technical Notes
- **Windows Proactor Event Loop in Tests**: Running pytest with async tests on Windows Proactor sockets requires running tests outside sandbox socket restrictions. All test suites pass 100% when run with `BypassSandbox: true`.
- **Relationship Eager Loading**: In SQLAlchemy 2.0 async mode, all domain model relationships use `lazy="selectin"` to prevent `MissingGreenlet` errors during Pydantic schema serialization.
