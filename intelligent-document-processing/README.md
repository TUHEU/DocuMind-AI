# DocuMind AI (Intelligent Document Processing) — Phase 1 project folder

Contents of this Phase 1 folder:

- `backend/` : FastAPI backend foundation (settings, health checks, 4 passing tests, Dockerfile).
- `docker-compose.yml` : backend + MySQL 8 (written, not yet run on your machine).
- `docs/` : Phase 1 requirements specification and the full design document (PDF + LaTeX sources).

**How to run it (with and without Docker): see `RUNNING.md`.**

**Status:** Phase 1 documents are drafted and wait for supervisor decisions (see the last chapter of the Phase 1 PDF). The backend covers only the start of Phases 3--4. No OCR model has been trained.

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

Phase 2: SQLAlchemy models (users, documents, extracted fields, reviews, audit events) and Alembic migrations.
