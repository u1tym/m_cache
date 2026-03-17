"""pytest 共通フィクスチャ（実DB接続）"""
from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from app.database import SessionLocal, get_db
from app.main import app


def override_get_db() -> Generator[Session, None, None]:
    """実DBのセッションをそのまま返す（テスト用）"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(scope="module")
def client() -> Generator[TestClient, None, None]:
    """FastAPI TestClient（実DBに接続）"""
    with TestClient(app) as c:
        yield c


@pytest.fixture
def db_session() -> Generator[Session, None, None]:
    """テスト用にDBセッションを取得（手動でデータ投入・確認したい場合）"""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
