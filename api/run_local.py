"""Local dev launcher (no Docker): loads ../.env, SQLite dev.db, runs wsgi.

Usage:  .venv/Scripts/python.exe run_local.py
"""
import os
import sys
from pathlib import Path

API_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(API_DIR))
os.chdir(API_DIR)

# Load key=value pairs from the repo .env (comments/blank lines skipped).
env_path = API_DIR.parent / ".env"
if env_path.exists():
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if key == "DATABASE_URL" or not value:
            continue
        os.environ.setdefault(key, value)

os.environ["DATABASE_URL"] = f"sqlite+pysqlite:///{(API_DIR / 'dev.db').as_posix()}"
os.environ["APP_ENV"] = ""
os.environ.setdefault("FLASK_DEBUG", "0")

from flask import Flask  # noqa: E402
from app import create_app  # noqa: E402

app: Flask = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("API_PORT", "5050"))
    # Werkzeug dev server — localhost convenience only (never production).
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False)
