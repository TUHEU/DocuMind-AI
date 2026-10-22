# DocuMind AI (Intelligent Document Processing) — project folder (Phases 1 to 4)

Contents:

- `backend/` : FastAPI backend: health checks, MySQL models and Alembic migration (16 tables), sign-up, login, roles, audit, e-mail service. 67 tests.
- `frontend/` : React + Vite starter that shows API and database status.
- `docs/` : Phase 1 and Phase 2 specifications, the project design document, the phase map and the API contract.
- `scripts/` : `check_phase3.py` (environment) and `check_phase4.py` (database and auth).
- `docker-compose.yml` : backend + MySQL 8 (written, not yet run on your machine).

**How to run it:** `RUNNING.md` (Phase 1 start), `PHASE3_SETUP.md` (environment), `PHASE4_GUIDE.md` (database and login).

**Status:** Phases 1 to 4 are built. Phase 4 is tested in a MariaDB test environment, not yet on your MySQL 8. No OCR model has been trained yet (Phase 7 onward).

## Structure

```
intelligent-document-processing/
├── backend/
│   ├── app/
│   │   ├── main.py            # FastAPI application
│   │   ├── api/health.py      # /api/v1/health and /api/v1/health/db
│   │   ├── core/config.py     # settings from environment / .env
│   │   └── database/connection.py
│   ├── tests/
│   ├── Dockerfile
│   └── requirements.txt
├── docker-compose.yml
├── .env.example
└── README.md
```

## Run locally on Windows (PowerShell, no Docker)

```powershell
cd backend
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m pytest
uvicorn app.main:app --reload
```

Python 3.13 is recommended. If `py -3.13` is not found, check `py --list`.
Avoid `uvicorn[standard]` and `fastapi[standard]` for now: they pull in extra packages (such as PyYAML) that may not have prebuilt wheels for newer Python versions.

Open:
- http://127.0.0.1:8000/
- http://127.0.0.1:8000/api/v1/health
- http://127.0.0.1:8000/docs

`/api/v1/health/db` returns 503 until MySQL is reachable. That is expected at this stage.

## Run with Docker Compose

```powershell
copy .env.example .env
docker compose up --build
```

Then open http://127.0.0.1:8000/api/v1/health/db: it should report `connected`.

## Next phase

Phase 5: secure document upload and storage, listing and application endpoints (see `PHASE4_GUIDE.md` for what Phase 4 added).
