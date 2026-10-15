# Intelligent Document Processing (IDP) — Phase 1: Backend foundation

FastAPI backend with settings, health checks, tests, Dockerfile and a Docker Compose stack with MySQL 8.

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
