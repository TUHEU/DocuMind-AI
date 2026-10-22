r"""Phase 4 check (database and backend foundation). Run from the backend folder with the venv Python:

    cd backend
    .\.venv\Scripts\python.exe ..\scripts\check_phase4.py

Read-only: it changes nothing and prints no password or key. Each line is PASS, FAIL or WARN.
"""
import sys
from pathlib import Path

BACKEND = Path(__file__).resolve().parent.parent / "backend"
sys.path.insert(0, str(BACKEND))
fails = 0


def show(status, name, detail=""):
    global fails
    fails += status == "FAIL"
    print(f"[{status:4}] {name}" + (f"  -> {detail}" if detail else ""))


try:
    from sqlalchemy import inspect, text
    from app.core.config import get_settings
    from app.database.connection import get_engine
    from app.models import Base
    show("PASS", "backend code imports")
except Exception as exc:
    show("FAIL", "backend code imports", f"{type(exc).__name__}: {exc}")
    sys.exit(1)

s = get_settings()
(show("WARN", "JWT_SECRET is still the default", "set your own long random value in backend/.env")
 if s.jwt_secret.startswith("dev-only") else show("PASS", "JWT_SECRET is customised"))
show("PASS" if s.email_backend in ("console", "smtp") else "FAIL", f"EMAIL_BACKEND = {s.email_backend}")
if s.email_backend == "smtp" and not (s.smtp_login and s.smtp_key and s.email_from):
    show("FAIL", "smtp selected but SMTP_LOGIN / SMTP_KEY / EMAIL_FROM is empty in .env")

try:
    engine = get_engine()
    with engine.connect() as c:
        c.execute(text("SELECT 1"))
        show("PASS", "MySQL reachable")
        tables = set(inspect(c).get_table_names())
        expected = set(Base.metadata.tables)
        missing = sorted(expected - tables)
        show("PASS" if not missing else "FAIL", f"{len(expected)} application tables exist", f"missing: {missing}" if missing else "")
        if "alembic_version" in tables:
            v = c.execute(text("SELECT version_num FROM alembic_version")).scalar()
            show("PASS" if v == "0001" else "WARN", f"Alembic version = {v}")
        else:
            show("WARN", "no alembic_version table", "run: .\\.venv\\Scripts\\python.exe -m alembic upgrade head   (on an EMPTY idp_db)")
        if "users" in tables:
            n = c.execute(text("SELECT COUNT(*) FROM users WHERE role='ADMIN' AND is_active=1")).scalar()
            show("PASS" if n else "WARN", f"active administrators: {n}", "" if n else "run: python -m app.cli create-admin --email ... --name ...")
        if "audit_events" in tables:
            n = c.execute(text("SELECT COUNT(*) FROM information_schema.triggers WHERE trigger_schema = DATABASE() AND event_object_table='audit_events'")).scalar()
            show("PASS" if n == 2 else "FAIL", f"audit append-only triggers: {n} of 2")
except Exception as exc:
    show("FAIL", "MySQL reachable", f"{type(exc).__name__}: start MySQL and check backend/.env")

print("\nAll good." if not fails else f"\n{fails} check(s) failed.")
sys.exit(1 if fails else 0)
