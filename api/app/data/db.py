"""WS08-03 — SQLAlchemy engine/pool management.

Connection management invariants:
- ``pool_pre_ping`` drops connections killed by NAT/idle timeouts instead of
  surfacing them as random 500s.
- Pool size/overflow are env-configurable and MODEST by default: multiply
  processes x (pool_size + max_overflow) and keep the total inside the
  database connection budget BEFORE scaling API replicas (see
  docs/runbooks/DATABASE_BACKUP_RESTORE.md).
- connect_timeout bounds how long a worker blocks when Postgres is saturated.
- Optional server-side ``statement_timeout`` (DB_STATEMENT_TIMEOUT_MS, 0=off)
  so a single runaway query cannot pin a pool slot forever. Alembic
  migrations connect through migrations/env.py and are NOT affected.
"""
import os
from contextlib import contextmanager

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

_engine = None
_Session = None


def _int_env(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


def engine_kwargs(url: str) -> dict:
    """Build create_engine kwargs for the given URL (WS08-03)."""
    if url.startswith("sqlite"):
        # Dev/test: keep SQLite defaults (file locking + shared cache make
        # aggressive pooling counterproductive).
        return {"pool_pre_ping": True}
    kwargs = {
        "pool_pre_ping": True,
        "pool_size": _int_env("DB_POOL_SIZE", 5),
        "max_overflow": _int_env("DB_MAX_OVERFLOW", 10),
        "pool_recycle": _int_env("DB_POOL_RECYCLE_S", 1800),
        "pool_timeout": _int_env("DB_POOL_TIMEOUT_S", 30),
    }
    connect_args = {"connect_timeout": _int_env("DB_CONNECT_TIMEOUT_S", 10)}
    stmt_ms = _int_env("DB_STATEMENT_TIMEOUT_MS", 0)
    if stmt_ms > 0:
        connect_args["options"] = f"-c statement_timeout={stmt_ms}"
    kwargs["connect_args"] = connect_args
    return kwargs


def make_engine(url, **overrides):
    kwargs = engine_kwargs(url)
    kwargs.update(overrides)
    return create_engine(url, **kwargs)


def init_engine(url):
    global _engine, _Session
    _engine = make_engine(url)
    _Session = sessionmaker(bind=_engine)
    return _engine


def dispose_engine():
    """Dispose the process-global engine (test harness teardown helper)."""
    global _engine, _Session
    if _engine is not None:
        _engine.dispose()
    _engine = None
    _Session = None


@contextmanager
def get_session():
    s = _Session()
    try:
        yield s
        s.commit()
    except Exception:
        s.rollback()
        raise
    finally:
        s.close()
