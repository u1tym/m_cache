"""DB接続・セッション管理"""
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, declarative_base, sessionmaker

from app.config import get_db_url

engine = create_engine(get_db_url(), echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """FastAPI の Depends 用：リクエストごとのセッションを返す"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
