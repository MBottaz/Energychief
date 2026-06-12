"""
SQLAlchemy engine & session factory.

Usage:
    from shared.engine import SessionLocal
    with SessionLocal() as session:
        ...

The DATABASE_URL env var selects the backend:
    sqlite:///db/energychief.db   →  SQLite (local dev)
    postgresql://user:pass@host/db →  PostgreSQL (Docker/production)
"""

import os
from pathlib import Path
from urllib.parse import urlparse

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///db/energychief.db")

# SQLite needs check_same_thread=False for FastAPI's async usage
connect_args = {}
if DATABASE_URL.startswith("sqlite"):
    connect_args["check_same_thread"] = False
    # Ensure the database directory exists (e.g. after a fresh deploy)
    parsed = urlparse(DATABASE_URL)
    db_path = Path(parsed.path.lstrip("/"))
    db_path.parent.mkdir(parents=True, exist_ok=True)

engine = create_engine(DATABASE_URL, connect_args=connect_args)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)