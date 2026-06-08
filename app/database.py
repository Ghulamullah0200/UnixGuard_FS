"""
database.py — SQLAlchemy engine and session configuration for UnixGuard FS.
Uses a local SQLite file (unixguard.db) stored alongside the application.
"""

import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, declarative_base

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# On Vercel serverless, the filesystem is read-only except for /tmp.
# Detect the VERCEL environment variable to switch the DB path accordingly.
if os.environ.get("VERCEL"):
    DB_PATH = os.path.join("/tmp", "unixguard.db")
else:
    DB_PATH = os.path.join(BASE_DIR, "unixguard.db")

DATABASE_URL = f"sqlite:///{DB_PATH}"

engine = create_engine(
    DATABASE_URL,
    connect_args={"check_same_thread": False},
    echo=False,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db():
    """FastAPI dependency — yields a DB session and ensures it is closed."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Create all tables defined by the ORM models."""
    from app import models  # noqa: F401 — side-effect import registers models
    Base.metadata.create_all(bind=engine)
