import os
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session
from sqlalchemy.pool import StaticPool
from app.core.config import settings

db_url = settings.DATABASE_URL

connect_args = {}
poolclass = None

if db_url.startswith("sqlite"):
    connect_args = {"check_same_thread": False}
    if ":memory:" in db_url:
        poolclass = StaticPool

engine = create_engine(
    db_url,
    connect_args=connect_args,
    poolclass=poolclass if poolclass else None,
    future=True,
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine, future=True)

Base = declarative_base()


def get_db():
    db: Session = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    from app.models import entities  # noqa: F401
    Base.metadata.create_all(bind=engine)
