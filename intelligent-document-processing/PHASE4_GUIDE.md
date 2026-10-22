# Phase 4: Database and backend foundation

What is new (stories US-17 to US-21 and US-33):

| Story | What it adds | Where |
|---|---|---|
| US-17 Create schema | Alembic migration `0001` creates the 16 tables, CHECK rules, 2 audit triggers, 6 default settings | `backend/alembic/` |
| US-18 Models and migrations | SQLAlchemy models for all 16 tables | `backend/app/models/models.py` |
| US-19 Database connections | Engine, session per request (`get_db`) | `backend/app/database/` |
| US-20 Authentication and roles | Register, login, `/auth/me`, admin user management, lockout, role checks | `backend/app/api/auth.py`, `users.py`, `deps.py`, `core/security.py` |
| US-21 Errors, logging, status rules | One error format, request ids, audit service, allowed status changes | `backend/app/core/errors.py`, `logging.py`, `services/` |
| US-33 Tender roles | COMPANY and APPLICANT sign-up (a company creates its organisation) | `api/auth.py` |
| (extra) E-mail | `EmailService`: console mode or Brevo SMTP | `backend/app/services/email.py` |

## Endpoints now in the code
| Method and path | Who | Notes |
|---|---|---|
| `POST /api/v1/auth/register` | anyone | Roles COMPANY or APPLICANT only. A company must give `organization_name`. |
| `POST /api/v1/auth/login` | anyone | Returns a bearer token. 5 wrong passwords lock the account 15 minutes (429). |
| `GET /api/v1/auth/me` | signed in | Current profile. |
| `GET/POST /api/v1/users`, `PATCH /api/v1/users/{id}` | ADMIN | Create staff users, change role, deactivate. An admin cannot demote or deactivate themselves. |

`/auth/register` is an addition to the Phase 2 contract (the contract had no sign-up); add it to `openapi.yaml` when you next revise the contract.

## Run it on your PC (Windows, PowerShell, no admin needed)
Do these in order. Replace nothing except what is in `backend/.env`.

**1. MySQL must be running.** If `Get-Service MySQL80` says Stopped and you cannot start it, run this in its own PowerShell window and leave it open:
`& "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqld.exe" --defaults-file="C:\ProgramData\MySQL\MySQL Server 8.0\my.ini" --console`

**2. Update the packages** (alembic is new):
```powershell
cd backend
.\.venv\Scripts\python.exe -m pip install -r requirements.txt --default-timeout 100 --retries 10
```

**3. Edit `backend/.env`** (copy new lines from `.env.example`): set `JWT_SECRET` to your own long random text. Leave `EMAIL_BACKEND=console` for now.

**4. Create the tables. Choose ONE of two cases:**
- *Your `idp_db` is empty or you can wipe it* (recommended): in Workbench run
  `DROP DATABASE IF EXISTS idp_db; CREATE DATABASE idp_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;`
  then in PowerShell: `.\.venv\Scripts\python.exe -m alembic upgrade head`
- *You already ran `documind_phase2_fresh.sql` and it shows 16 tables*: do not run upgrade; run
  `.\.venv\Scripts\python.exe -m alembic stamp 0001` (it only records that the tables exist).
  If you still have the older 11-table version, wipe and use the first case.

**5. Create your administrator** (the password is typed hidden; it is not saved anywhere but the database, as a hash):
```powershell
.\.venv\Scripts\python.exe -m app.cli create-admin --email you@example.com --name "Your Name"
```

**6. Check, test, start:**
```powershell
.\.venv\Scripts\python.exe ..\scripts\check_phase4.py
.\.venv\Scripts\python.exe -m pytest
.\.venv\Scripts\python.exe -m uvicorn app.main:app --reload
```
Open http://127.0.0.1:8000/docs, click **POST /api/v1/auth/login**, Try it out, then **Authorize** with the token to try `/auth/me` and `/users`.
`pytest` runs 62 tests with no MySQL needed (an in-memory test database). 5 more tests need a real MySQL; they are skipped unless you opt in (see the top of `tests/test_mysql_integration.py`).

## E-mail with Brevo (when you want real e-mails)
In **your own** `backend/.env` only:
```
EMAIL_BACKEND=smtp
SMTP_LOGIN=<your Brevo SMTP login>
SMTP_KEY=<your Brevo SMTP key>
EMAIL_FROM=<a sender address you verified in Brevo>
```
Never put the key in code, in chat or in a zip. A key that was pasted in a chat should be replaced in Brevo (SMTP and API, Generate a new SMTP key). Sign-up sends a welcome e-mail in the background; if sending fails, sign-up still succeeds and the failure is logged without the key.

## Design choices you can defend
- Passwords: scrypt with a random salt (Python standard library). Tokens: HS256 JWT, 30 minutes; the user and role are re-read from the database on every request, so deactivation and role changes take effect at once.
- Same answer for a wrong password and an unknown e-mail, and equal work done in both cases (no user listing by timing).
- Errors never show stack traces or paths; every response carries `X-Request-ID`.
- Audit rows are written in the same transaction as the change and contain no passwords or tokens.

## Known limits (honest)
- Tested on MariaDB 10.11 in my environment, **not yet on your MySQL 8.0.46**. `check_phase4.py` and the integration tests tell you in one minute.
- Lockout counters live in the database, so they survive restarts, but there is no per-IP rate limit yet (Phase 15, security).
- No password reset or e-mail verification yet: the e-mail service exists, the flows do not.
- Documents, listings and applications have models and tables but no endpoints yet (Phase 5).
- The migration runs the tested SQL file rather than being auto-generated; later changes are ordinary Alembic revisions.
