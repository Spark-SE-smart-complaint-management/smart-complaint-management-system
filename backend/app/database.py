import os

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

from app.config import DATABASE_URL

connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
DATABASE_POOL_SIZE = max(1, int(os.getenv("DATABASE_POOL_SIZE", "40")))
DATABASE_MAX_OVERFLOW = max(0, int(os.getenv("DATABASE_MAX_OVERFLOW", "20")))
pool_options = {}
if DATABASE_URL not in {"sqlite://", "sqlite:///:memory:"}:
    pool_options = {
        "pool_size": DATABASE_POOL_SIZE,
        "max_overflow": DATABASE_MAX_OVERFLOW,
    }
engine = create_engine(
    DATABASE_URL, connect_args=connect_args, pool_pre_ping=True, **pool_options
)
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)
Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
