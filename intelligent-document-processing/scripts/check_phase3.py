r"""Phase 3 environment check. Run it with the backend virtual environment's Python:

    cd backend
    .\.venv\Scripts\python.exe ..\scripts\check_phase3.py

It only reads things; it changes nothing. Each line is PASS, FAIL or SKIP.
"""
import importlib
import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
results = []


def record(story, name, status, detail=""):
    results.append((story, name, status, detail))
    print(f"[{status:4}] {story}  {name}" + (f"  -> {detail}" if detail else ""))


def run(cmd):
    try:
        out = subprocess.run(cmd, capture_output=True, text=True, timeout=20, shell=False)
        return out.returncode, (out.stdout or out.stderr).strip()
    except Exception as exc:  # command missing or not runnable
        return 1, str(exc)


def can_import(mod):
    try:
        m = importlib.import_module(mod)
        return True, getattr(m, "__version__", "")
    except Exception as exc:
        return False, str(exc).splitlines()[0][:80]


# US-12 Python backend
v = sys.version_info
record("US-12", "Python 3.13 or newer", "PASS" if v >= (3, 13) else "FAIL", f"{v.major}.{v.minor}.{v.micro}")
for mod in ("fastapi", "uvicorn", "pydantic_settings", "sqlalchemy", "pymysql"):
    ok, info = can_import(mod)
    record("US-12", f"import {mod}", "PASS" if ok else "FAIL", info)
sys.path.insert(0, str(BACKEND))
try:
    from fastapi.testclient import TestClient
    from app.main import app

    r = TestClient(app).get("/api/v1/health")
    record("US-12", "GET /api/v1/health", "PASS" if r.status_code == 200 else "FAIL", f"HTTP {r.status_code}")
except Exception as exc:
    record("US-12", "GET /api/v1/health", "FAIL", str(exc).splitlines()[0][:80])

# US-13 MySQL
if not (BACKEND / ".env").exists():
    record("US-13", "backend/.env exists", "FAIL", "copy .env.example to .env and fill it in")
else:
    record("US-13", "backend/.env exists", "PASS")
    try:
        from fastapi.testclient import TestClient
        from app.main import app

        r = TestClient(app).get("/api/v1/health/db")
        record("US-13", "GET /api/v1/health/db", "PASS" if r.status_code == 200 else "FAIL",
               "connected" if r.status_code == 200 else "check DB_USER, DB_PASSWORD, DB_NAME in .env and that MySQL is running")
    except Exception as exc:
        record("US-13", "GET /api/v1/health/db", "FAIL", str(exc).splitlines()[0][:80])

# US-14 OCR dependencies (needed from Phase 6, so SKIP rather than FAIL when absent)
for mod, label in (("numpy", "NumPy"), ("cv2", "OpenCV"), ("fitz", "PyMuPDF"), ("torch", "PyTorch"), ("torchvision", "Torchvision")):
    ok, info = can_import(mod)
    record("US-14", f"import {label}", "PASS" if ok else "SKIP", info if ok else "not installed yet (backend/requirements-ocr.txt)")
ok, _ = can_import("torch")
if ok:
    import torch

    record("US-14", "PyTorch tensor operation", "PASS" if float(torch.ones(2, 2).sum()) == 4.0 else "FAIL")

# US-15 React frontend
for tool in ("node", "npm"):
    path = shutil.which(tool) or shutil.which(tool + ".cmd")
    if path:
        code, out = run([path, "--version"])
        record("US-15", f"{tool} installed", "PASS" if code == 0 else "FAIL", out)
    else:
        record("US-15", f"{tool} installed", "FAIL", "install Node.js LTS")
record("US-15", "frontend/package.json exists", "PASS" if (ROOT / "frontend" / "package.json").exists() else "FAIL")
record("US-15", "frontend dependencies installed", "PASS" if (ROOT / "frontend" / "node_modules").exists() else "FAIL", "" if (ROOT / "frontend" / "node_modules").exists() else "run npm install in frontend")

# US-16 Git and documentation
git = shutil.which("git")
if git:
    code, out = run([git, "--version"])
    record("US-16", "git installed", "PASS" if code == 0 else "FAIL", out)
    code, out = run([git, "-C", str(ROOT), "rev-parse", "--is-inside-work-tree"])
    record("US-16", "repository initialised", "PASS" if out == "true" else "FAIL", "git init" if out != "true" else "")
    for f in ("backend/.env", "backend/.venv/x", "frontend/node_modules/x"):
        code, out = run([git, "-C", str(ROOT), "check-ignore", "-q", f])
        record("US-16", f"{f} is ignored by git", "PASS" if code == 0 else "FAIL")
else:
    record("US-16", "git installed", "FAIL")
record("US-16", "RUNNING.md and README.md exist", "PASS" if (ROOT / "RUNNING.md").exists() and (ROOT / "README.md").exists() else "FAIL")

fails = [r for r in results if r[2] == "FAIL"]
skips = [r for r in results if r[2] == "SKIP"]
print(f"\n{len(results) - len(fails) - len(skips)} passed, {len(fails)} failed, {len(skips)} skipped")
sys.exit(1 if fails else 0)
