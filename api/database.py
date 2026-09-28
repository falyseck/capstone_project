"""
Database connection setup.

Defaults to a local SQLite file so the app runs with zero external setup during
development and demos. In Chapter Three, the system is specified to use PostgreSQL in
production — to switch, just set the DATABASE_URL environment variable, e.g.:

    export DATABASE_URL="postgresql://user:password@host:5432/ppd_db"

No other code needs to change; SQLAlchemy handles both the same way.
"""
import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

DATABASE_URL = os.environ.get("DATABASE_URL", "sqlite:///./ppd.db")

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
engine = create_engine(DATABASE_URL, connect_args=connect_args)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db():
    """FastAPI dependency that yields a DB session and always closes it."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
