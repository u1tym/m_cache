"""アプリケーション設定（.env から読み込み）"""
import os
from pathlib import Path

from dotenv import load_dotenv

# .env をプロジェクトルートから読み込む
env_path = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=env_path)


def get_db_url() -> str:
    """PostgreSQL 接続URLを組み立てる"""
    server: str = os.getenv("DB_SERVER", "localhost")
    database: str = os.getenv("DB_NAME", "tamtdb")
    port: str = os.getenv("DB_PORT", "5432")
    user: str = os.getenv("DB_USER", "tamtuser")
    password: str = os.getenv("DB_PASSWORD", "TAMTTAMT")
    return f"postgresql://{user}:{password}@{server}:{port}/{database}"
