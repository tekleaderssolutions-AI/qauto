"""
Qatar AI Platform - Database connection (PostgreSQL only).
Set DATABASE_URL or DB_HOST/DB_PORT/DB_NAME/DB_USER/DB_PASSWORD in .env
"""
import os
from pathlib import Path

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent / ".env")
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine
from urllib.parse import quote_plus

def get_database_url() -> str:
    url = os.environ.get("DATABASE_URL", "").strip()
    if url:
        if url.startswith("postgresql://") and "psycopg2" not in url:
            url = url.replace("postgresql://", "postgresql+psycopg2://", 1)
        return url
    host = os.environ.get("DB_HOST", "").strip()
    if host:
        user = os.environ.get("DB_USER", "").strip() or "postgres"
        password = os.environ.get("DB_PASSWORD", "").strip()
        port = os.environ.get("DB_PORT", "").strip() or "5432"
        name = os.environ.get("DB_NAME", "").strip() or "qauto"
        sslmode = os.environ.get("DB_SSLMODE", "").strip()
        auth = f"{quote_plus(user)}:{quote_plus(password)}@" if password else f"{quote_plus(user)}@"
        base = f"postgresql+psycopg2://{auth}{host}:{port}/{name}"
        return f"{base}?sslmode={quote_plus(sslmode)}" if sslmode else base
    raise RuntimeError(
        "PostgreSQL required. Set DATABASE_URL (e.g. postgresql://user:password@host:5432/qauto) "
        "or DB_HOST, DB_USER, DB_PASSWORD, DB_NAME (and optionally DB_PORT, DB_SSLMODE)."
    )

_engine: Engine | None = None

def get_engine() -> Engine:
    global _engine
    if _engine is None:
        url = get_database_url()
        _engine = create_engine(
            url,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
            pool_recycle=300,
        )
    return _engine

def is_postgres() -> bool:
    return True
