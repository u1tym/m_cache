# 収支API (FastAPI + PostgreSQL)

## 環境

- Python 3.10+
- PostgreSQL（既存DB `tamtdb`、テーブル `payment_sources` / `transactions` を利用）

## 設定

接続情報は `.env` で指定（未設定時は以下が初期値）。

| 変数 | 初期値 |
|------|--------|
| DB_SERVER | localhost |
| DB_NAME | tamtdb |
| DB_PORT | 5432 |
| DB_USER | tamtuser |
| DB_PASSWORD | TAMTTAMT |

## セットアップ

プロジェクト直下の `env` フォルダに仮想環境がある想定です。

```bash
# Windows (PowerShell / コマンドプロンプト)
.\env\Scripts\activate
pip install -r requirements.txt
```

## 起動

```bash
.\env\Scripts\activate
uvicorn app.main:app --reload
```

## テスト

実 PostgreSQL に接続し、DB への更新が発生します。

```bash
.\env\Scripts\activate
pytest tests/ -v
```

- API: http://127.0.0.1:8000
- Swagger UI: http://127.0.0.1:8000/docs

## API 一覧

| # | 概要 | メソッド | パス |
|---|------|----------|------|
| 1 | 支出情報取得 | GET | /payment-sources |
| 2 | 支出情報登録 | POST | /payment-sources |
| 3 | 支払日算出 | POST | /calc-paid-date |
| 4 | 収支登録 | POST | /transactions |
| 5 | 収支更新 | PUT | /transactions |
| 6 | 収支1件検索 | GET | /transactions/{id} |
| 7 | 収支利用日期間リスト検索 | POST | /transactions/search-by-used-date |
| 8 | 収支支払日期間リスト検索 | POST | /transactions/search-by-paid-date |
