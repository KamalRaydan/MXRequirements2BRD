"""SQLite engine + session setup. Sync SQLAlchemy, create_all at startup (no Alembic in MVP)."""
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

import config


class Base(DeclarativeBase):
    pass


def _db_url() -> str:
    config.APP_DATA_DIR.mkdir(parents=True, exist_ok=True)
    db_path = config.APP_DATA_DIR / "app.db"
    return f"sqlite:///{db_path}"


# check_same_thread=False: FastAPI runs sync endpoints in a threadpool
engine = create_engine(_db_url(), connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


def init_db() -> None:
    # Import models so their tables are registered on Base before create_all
    from db import models  # noqa: F401

    Base.metadata.create_all(engine)


def get_db():
    """FastAPI dependency that yields a session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
