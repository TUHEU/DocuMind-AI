# How to run the Phase 1 backend

Two ways. **Method A (no Docker)** is the simplest and is the one I could test.
**Method B (Docker)** is optional: the files are written but have **not** been built or run yet.

| | Method A: no Docker | Method B: Docker |
|---|---|---|
| Uses your installed MySQL | Yes | No: it starts its own MySQL container |
| Needs | Python 3.13, MySQL | Docker Desktop |
| Config file | `backend/.env` | `.env` (next to `docker-compose.yml`) |
| Tested | 7 automated tests passed and the server ran in my test environment; not yet confirmed on your PC | Not built or run yet |

---

## Method A: without Docker (Windows, PowerShell)

### 1. Create the database (once)
Open MySQL Workbench (or the `mysql` command line) and run:
```sql
CREATE DATABASE idp_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```
No tables are needed yet.

### 2. Configure the backend
```powershell
cd backend
copy .env.example .env
notepad .env
```
Edit `.env`: set `DB_USER` and `DB_PASSWORD` to your own MySQL login. No quotes, no spaces around `=`.
A password containing `@` is supported.

### 3. Install and test
```powershell
py -3.13 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements.txt
python -m pytest
```
Expected: all tests pass.

If PowerShell refuses to run the activation script, run this once and try again:
`Set-ExecutionPolicy -Scope CurrentUser RemoteSigned`

### 4. Start the server
```powershell
uvicorn app.main:app --reload
```
Open:
- http://127.0.0.1:8000/ : status message
- http://127.0.0.1:8000/docs : interactive API documentation
- http://127.0.0.1:8000/api/v1/health : liveness (always works)
- http://127.0.0.1:8000/api/v1/health/db : MySQL check. `"database": "connected"` means your `.env` is right.
  `503 unreachable` means wrong password/user/database name or MySQL is not running.

Stop the server with `Ctrl + C`.

---

## Method B: with Docker

### 1. Install Docker Desktop and start it
Check: `docker --version` and `docker compose version`.

### 2. Configure
In the project root (where `docker-compose.yml` is):
```powershell
copy .env.example .env
notepad .env
```
Choose passwords. These create a **new** MySQL inside Docker; it is separate from the MySQL installed on your PC.

### 3. Build and start
```powershell
docker compose up --build
```
First start takes a few minutes. Open http://127.0.0.1:8000/api/v1/health/db : it should say `connected`.

Useful commands:
```powershell
docker compose up -d        # start in the background
docker compose logs -f backend
docker compose down         # stop (keeps database data)
docker compose down -v      # stop and DELETE the database data
```

### Notes
- Both methods use port 8000. Stop one before starting the other.
- Docker's MySQL is not published on your PC, so it does not clash with your installed MySQL on port 3306.
- If something fails, copy the exact error text.

---

## Troubleshooting

| Problem | Likely cause and fix |
|---|---|
| `pip install` fails compiling PyYAML or similar | Wrong Python version. Use `py -3.13`, not 3.15. |
| `health/db` returns 503 | Wrong `DB_USER`/`DB_PASSWORD`/`DB_NAME` in `backend/.env`, MySQL stopped, or database not created. |
| `Access denied for user` | Password wrong. Reset it in MySQL, or create a dedicated user. |
| Changes to `.env` ignored | Restart uvicorn. Settings are read at startup. |
| `address already in use` on 8000 | Another server is running. Stop it or use `--port 8001`. |
