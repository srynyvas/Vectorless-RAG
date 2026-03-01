"""SQLAlchemy engine, session, and database initialisation for PostgreSQL.

Usage::

    from backend.db.database import get_db, init_db

    # FastAPI dependency injection
    @app.get("/items")
    def read_items(db: Session = Depends(get_db)):
        ...

    # Application startup
    init_db()
"""

from __future__ import annotations

import os
from collections.abc import Generator
from typing import TYPE_CHECKING

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

if TYPE_CHECKING:
    from sqlalchemy.engine import Engine

# ---------------------------------------------------------------------------
# Declarative base – imported by models.py to define ORM classes
# ---------------------------------------------------------------------------
Base = declarative_base()

# ---------------------------------------------------------------------------
# Database URL
# ---------------------------------------------------------------------------
DATABASE_URL: str = os.getenv(
    "DATABASE_URL",
    "postgresql://pageindex:changeme@localhost:5432/pageindex",
)

# ---------------------------------------------------------------------------
# Engine
# ---------------------------------------------------------------------------
_engine_kwargs: dict = {}

# SQLite requires ``check_same_thread=False`` when used with FastAPI;
# PostgreSQL does not need (or accept) that argument.
if DATABASE_URL.startswith("sqlite"):
    _engine_kwargs["connect_args"] = {"check_same_thread": False}

engine: Engine = create_engine(DATABASE_URL, pool_pre_ping=True, **_engine_kwargs)

# ---------------------------------------------------------------------------
# Session factory
# ---------------------------------------------------------------------------
SessionLocal: sessionmaker[Session] = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
)


# ---------------------------------------------------------------------------
# FastAPI dependency
# ---------------------------------------------------------------------------
def get_db() -> Generator[Session, None, None]:
    """Yield a SQLAlchemy session and guarantee it is closed afterwards.

    Intended for use as a FastAPI ``Depends()`` dependency::

        db: Session = Depends(get_db)
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


# ---------------------------------------------------------------------------
# Table creation helper
# ---------------------------------------------------------------------------
def init_db() -> None:
    """Create all tables that are registered on :pydata:`Base`.

    This imports :mod:`backend.db.models` so that every ORM model is
    registered on ``Base.metadata`` before ``create_all`` is called.
    """
    # Import models so they are registered with Base.metadata before we
    # attempt to create the tables.
    import backend.db.models  # noqa: F401

    Base.metadata.create_all(bind=engine)
