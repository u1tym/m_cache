"""収支API 統合テスト（実PostgreSQLに接続・更新あり）"""
import pytest
from fastapi.testclient import TestClient


# ---------- 1) 支出情報取得 ----------


def test_get_payment_sources_empty_or_list(client: TestClient) -> None:
    """GET /payment-sources は 200 で items リストを返す"""
    r = client.get("/payment-sources")
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    assert isinstance(data["items"], list)


# ---------- 2) 支出情報登録 ----------


def test_create_payment_source(client: TestClient) -> None:
    """POST /payment-sources で登録でき、GET で取得できる"""
    r = client.post(
        "/payment-sources",
        json={
            "name": "テスト用カード",
            "closing_day": 25,
            "pay_month_diff": 1,
            "pay_day": 10,
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["name"] == "テスト用カード"
    assert data["closing_day"] == 25
    assert data["pay_month_diff"] == 1
    assert data["pay_day"] == 10
    assert "id" in data
    ps_id = data["id"]

    r2 = client.get("/payment-sources")
    assert r2.status_code == 200
    items = r2.json()["items"]
    found = [x for x in items if x["id"] == ps_id]
    assert len(found) == 1
    assert found[0]["name"] == "テスト用カード"


# ---------- 3) 支払日算出 ----------


def test_calc_paid_date_not_found(client: TestClient) -> None:
    """存在しない支出元IDで 404"""
    r = client.post(
        "/calc-paid-date",
        json={"used_date": "2025-03-15", "payment_source_id": 999999},
    )
    assert r.status_code == 404


def test_calc_paid_date_closing_day_zero(client: TestClient) -> None:
    """締日=0 の支出元を登録し、利用日がそのまま支払日になることを確認"""
    # 締日0の支出元を登録
    r_ps = client.post(
        "/payment-sources",
        json={
            "name": "締日0テスト",
            "closing_day": 0,
            "pay_month_diff": 0,
            "pay_day": 1,
        },
    )
    assert r_ps.status_code == 200
    ps_id = r_ps.json()["id"]

    r = client.post(
        "/calc-paid-date",
        json={"used_date": "2025-03-17", "payment_source_id": ps_id},
    )
    assert r.status_code == 200
    assert r.json()["paid_date"] == "2025-03-17"


def test_calc_paid_date_used_day_le_closing(client: TestClient) -> None:
    """利用日の日 <= 締日 → 月 = 利用日+pay_month_diff, 日 = pay_day"""
    r_ps = client.post(
        "/payment-sources",
        json={
            "name": "締日25支払10テスト",
            "closing_day": 25,
            "pay_month_diff": 1,
            "pay_day": 10,
        },
    )
    assert r_ps.status_code == 200
    ps_id = r_ps.json()["id"]

    # 3月15日利用（15 <= 25）→ 4月10日支払
    r = client.post(
        "/calc-paid-date",
        json={"used_date": "2025-03-15", "payment_source_id": ps_id},
    )
    assert r.status_code == 200
    assert r.json()["paid_date"] == "2025-04-10"


def test_calc_paid_date_used_day_gt_closing(client: TestClient) -> None:
    """利用日の日 > 締日 → 月 = 利用日+pay_month_diff+1, 日 = pay_day"""
    r_ps = client.post(
        "/payment-sources",
        json={
            "name": "締日25支払10テスト2",
            "closing_day": 25,
            "pay_month_diff": 1,
            "pay_day": 10,
        },
    )
    assert r_ps.status_code == 200
    ps_id = r_ps.json()["id"]

    # 3月26日利用（26 > 25）→ 5月10日支払（3+1+1=5月）
    r = client.post(
        "/calc-paid-date",
        json={"used_date": "2025-03-26", "payment_source_id": ps_id},
    )
    assert r.status_code == 200
    assert r.json()["paid_date"] == "2025-05-10"


# ---------- 4) 収支登録 ----------


def test_create_transaction_with_budget_name(client: TestClient) -> None:
    """収支登録（予算名指定）→ そのまま保存"""
    # 支出元を1件取得 or 登録
    r_ps = client.get("/payment-sources")
    items = r_ps.json()["items"]
    if not items:
        r_new = client.post(
            "/payment-sources",
            json={
                "name": "収支テスト用",
                "closing_day": 0,
                "pay_month_diff": 0,
                "pay_day": 1,
            },
        )
        ps_id = r_new.json()["id"]
    else:
        ps_id = items[0]["id"]

    r = client.post(
        "/transactions",
        json={
            "used_date": "2025-03-01",
            "purpose": "食費",
            "memo": "テストメモ",
            "amount": 3000,
            "payment_source_id": ps_id,
            "paid_date": "2025-03-01",
            "budget_name": "食費予算",
        },
    )
    assert r.status_code == 200
    data = r.json()
    assert data["purpose"] == "食費"
    assert data["memo"] == "テストメモ"
    assert data["amount"] == 3000
    assert data["budget_name"] == "食費予算"
    assert "id" in data


def test_create_transaction_budget_name_default(client: TestClient) -> None:
    """収支登録で予算名未指定 → 「未分類」になる"""
    r_ps = client.get("/payment-sources")
    items = r_ps.json()["items"]
    assert items, "先に支出元が1件以上必要"
    ps_id = items[0]["id"]

    r = client.post(
        "/transactions",
        json={
            "used_date": "2025-03-10",
            "purpose": "未分類テスト",
            "amount": 1000,
            "payment_source_id": ps_id,
            "paid_date": "2025-03-10",
        },
    )
    assert r.status_code == 200
    assert r.json()["budget_name"] == "未分類"


# ---------- 5) 収支更新 ----------


def test_update_transaction(client: TestClient) -> None:
    """収支を登録し、PUT /transactions で更新できる"""
    r_ps = client.get("/payment-sources")
    items = r_ps.json()["items"]
    assert items
    ps_id = items[0]["id"]

    r_create = client.post(
        "/transactions",
        json={
            "used_date": "2025-03-05",
            "purpose": "更新前",
            "memo": "メモ前",
            "amount": 500,
            "payment_source_id": ps_id,
            "paid_date": "2025-03-05",
            "budget_name": "テスト",
        },
    )
    assert r_create.status_code == 200
    tx_id = r_create.json()["id"]

    r_update = client.put(
        "/transactions",
        json={
            "id": tx_id,
            "purpose": "更新後",
            "memo": "メモ後",
            "amount": 1500,
        },
    )
    assert r_update.status_code == 200

    r_get = client.get(f"/transactions/{tx_id}")
    assert r_get.status_code == 200
    data = r_get.json()
    assert data["purpose"] == "更新後"
    assert data["memo"] == "メモ後"
    assert data["amount"] == 1500
    assert data["used_date"] == "2025-03-05"  # 未指定はそのまま


def test_update_transaction_not_found(client: TestClient) -> None:
    """存在しないIDで更新 → 404"""
    r = client.put(
        "/transactions",
        json={"id": 999999, "purpose": "無効"},
    )
    assert r.status_code == 404


# ---------- 6) 収支1件検索 ----------


def test_get_transaction_not_found(client: TestClient) -> None:
    """存在しないIDで取得 → 404"""
    r = client.get("/transactions/999999")
    assert r.status_code == 404


def test_get_transaction_detail(client: TestClient) -> None:
    """登録した収支をIDで取得し、支出元名が含まれる"""
    r_ps = client.get("/payment-sources")
    items = r_ps.json()["items"]
    assert items
    ps_id = items[0]["id"]
    ps_name = items[0]["name"]

    r_create = client.post(
        "/transactions",
        json={
            "used_date": "2025-03-12",
            "purpose": "1件取得テスト",
            "memo": "memo",
            "amount": 2000,
            "payment_source_id": ps_id,
            "paid_date": "2025-03-12",
            "budget_name": "B",
        },
    )
    assert r_create.status_code == 200
    tx_id = r_create.json()["id"]

    r = client.get(f"/transactions/{tx_id}")
    assert r.status_code == 200
    data = r.json()
    assert data["id"] == tx_id
    assert data["purpose"] == "1件取得テスト"
    assert data["payment_source_name"] == ps_name


# ---------- 7) 収支利用日期間リスト検索 ----------


def test_search_by_used_date(client: TestClient) -> None:
    """期間（自）（至）で used_date 検索"""
    r_ps = client.get("/payment-sources")
    assert r_ps.json()["items"]
    ps_id = r_ps.json()["items"][0]["id"]

    # 期間内の1件を登録
    client.post(
        "/transactions",
        json={
            "used_date": "2025-03-20",
            "purpose": "期間内",
            "amount": 1111,
            "payment_source_id": ps_id,
            "paid_date": "2025-03-20",
            "budget_name": "X",
        },
    )

    r = client.post(
        "/transactions/search-by-used-date",
        json={"date_from": "2025-03-01", "date_to": "2025-03-31"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    in_range = [x for x in data["items"] if x["purpose"] == "期間内" and x["used_date"] == "2025-03-20"]
    assert len(in_range) >= 1
    assert in_range[0]["payment_source_name"]


def test_search_by_used_date_empty_period(client: TestClient) -> None:
    """該当なしの期間でも 200 で空リスト"""
    r = client.post(
        "/transactions/search-by-used-date",
        json={"date_from": "2030-01-01", "date_to": "2030-01-31"},
    )
    assert r.status_code == 200
    assert r.json()["items"] == []


# ---------- 8) 収支支払日期間リスト検索 ----------


def test_search_by_paid_date(client: TestClient) -> None:
    """期間（自）（至）で paid_date 検索"""
    r_ps = client.get("/payment-sources")
    assert r_ps.json()["items"]
    ps_id = r_ps.json()["items"][0]["id"]

    client.post(
        "/transactions",
        json={
            "used_date": "2025-02-01",
            "purpose": "支払日検索用",
            "amount": 2222,
            "payment_source_id": ps_id,
            "paid_date": "2025-03-25",
            "budget_name": "Y",
        },
    )

    r = client.post(
        "/transactions/search-by-paid-date",
        json={"date_from": "2025-03-01", "date_to": "2025-03-31"},
    )
    assert r.status_code == 200
    data = r.json()
    assert "items" in data
    found = [x for x in data["items"] if x["purpose"] == "支払日検索用"]
    assert len(found) >= 1
    assert found[0]["paid_date"] == "2025-03-25"


def test_search_by_paid_date_empty_period(client: TestClient) -> None:
    """該当なしの期間でも 200 で空リスト"""
    r = client.post(
        "/transactions/search-by-paid-date",
        json={"date_from": "2030-01-01", "date_to": "2030-01-31"},
    )
    assert r.status_code == 200
    assert r.json()["items"] == []
