@echo off
rem Local dev launcher (no Docker): loads .env, runs API on SQLite dev.db
cd /d "%~dp0"
for /f "usebackq eol=# tokens=1,* delims==" %%A in (`findstr /b /r "^[A-Z_]*=" "%~dp0..\.env"`) do (
  if /i not "%%A"=="DATABASE_URL" if not "%%B"=="" set "%%A=%%B"
)
set "DATABASE_URL=sqlite+pysqlite:///E:/Project app/aruora/api/dev.db"
set "APP_ENV="
set "FLASK_DEBUG=0"
.venv\Scripts\python.exe wsgi.py > api.log 2>&1
