# Phase 3: Development environment setup (Windows, no Docker, no admin rights)

Folder layout: `backend/` (FastAPI), `frontend/` (React + Vite), `scripts/check_phase3.py` (checks everything), `docs/phase2/db/` (database file).

## 1. Backend (US-12)
```powershell
cd backend
py -3.13 -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```
Use `.\.venv\Scripts\python.exe` directly. You never need `Activate.ps1`, so the execution-policy block does not matter.
If pip cannot reach pypi.org, add `--default-timeout 100 --retries 10`, or try another network (for example a phone hotspot).

## 2. MySQL (US-13)
1. Run `docs/phase2/db/documind_phase2_fresh.sql` in MySQL Workbench (already done on your PC).
2. `copy .env.example .env` in `backend`, then edit `.env`: set `DB_USER`, `DB_PASSWORD`, `DB_NAME=idp_db`. No quotes, no spaces around `=`.
3. Start the server and open http://127.0.0.1:8000/api/v1/health/db : it must say `connected`.

## 3. OCR dependencies (US-14)
Only needed from Phase 6. When you reach it:
```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-ocr.txt
.\.venv\Scripts\python.exe -m pip install torch torchvision --index-url https://download.pytorch.org/whl/cpu
```
PyTorch is a large download. The check script shows SKIP (not FAIL) until then.

## 4. React frontend (US-15)
Install Node.js LTS (the user installer needs no admin rights), reopen PowerShell, then:
```powershell
cd frontend
npm install
npm run dev
```
Open http://localhost:5173 . The page shows two status lines (Backend API, MySQL database) that turn green when the backend is running.
Run the backend in a second terminal.

## 5. Git (US-16)
The repository already exists on your PC. Check that `backend/.env` is NOT listed by `git status` before every commit.

## Check everything
```powershell
cd backend
.\.venv\Scripts\python.exe ..\scripts\check_phase3.py
```
Every line must be PASS (SKIP is fine for OCR libraries). Send me the output if a line says FAIL.
