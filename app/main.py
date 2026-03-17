"""FastAPI アプリケーション"""
import calendar
from datetime import date

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.models import PaymentSource, Transaction
from app.schemas import (
    PaidDateCalcRequest,
    PaidDateCalcResponse,
    PaymentSourceCreate,
    PaymentSourceCreateResponse,
    PaymentSourceListResponse,
    PaymentSourceItem,
    TransactionCreate,
    TransactionCreateResponse,
    TransactionDetailResponse,
    TransactionListByDateRequest,
    TransactionListByPaidDateRequest,
    TransactionListItem,
    TransactionListResponse,
    TransactionUpdate,
)

app = FastAPI(title="収支API", description="収支・支出元管理API")


# ---------- 支払日算出ロジック（3で使用） ----------


def _last_day_of_month(y: int, m: int) -> int:
    """指定年月の最終日"""
    return calendar.monthrange(y, m)[1]


def calc_paid_date(used_date: date, closing_day: int, pay_month_diff: int, pay_day: int) -> date:
    """
    利用日・締日・支払月差分・支払日から支払日を算出する。
    - closing_day=0 → 利用日をそのまま返す
    - 利用日の日 <= 締日 → 月 = 利用日の月 + pay_month_diff, 日 = pay_day
    - 利用日の日 > 締日 → 月 = 利用日の月 + pay_month_diff + 1, 日 = pay_day
    """
    if closing_day == 0:
        return used_date
    day = used_date.day
    year = used_date.year
    month = used_date.month
    if day <= closing_day:
        new_month = month + pay_month_diff
    else:
        new_month = month + pay_month_diff + 1
    while new_month > 12:
        new_month -= 12
        year += 1
    while new_month < 1:
        new_month += 12
        year -= 1
    last = _last_day_of_month(year, new_month)
    actual_day = min(pay_day, last)
    return date(year, new_month, actual_day)


# ---------- 1) 支出情報取得 ----------


@app.get(
    "/payment-sources",
    response_model=PaymentSourceListResponse,
    summary="支出情報取得",
    description="payment_sources を検索し、id・name・締日・支払月差分・支払日のリストを返す",
)
def get_payment_sources(db: Session = Depends(get_db)) -> PaymentSourceListResponse:
    sources = db.query(PaymentSource).order_by(PaymentSource.id).all()
    return PaymentSourceListResponse(
        items=[
            PaymentSourceItem(
                id=s.id,
                name=s.name,
                closing_day=s.closing_day,
                pay_month_diff=s.pay_month_diff,
                pay_day=s.pay_day,
            )
            for s in sources
        ]
    )


# ---------- 2) 支出情報登録 ----------


@app.post(
    "/payment-sources",
    response_model=PaymentSourceCreateResponse,
    summary="支出情報登録",
    description="payment_sources に名称・締日・支払月差分・支払日で登録する",
)
def create_payment_source(
    body: PaymentSourceCreate,
    db: Session = Depends(get_db),
) -> PaymentSourceCreateResponse:
    entity = PaymentSource(
        name=body.name,
        closing_day=body.closing_day,
        pay_month_diff=body.pay_month_diff,
        pay_day=body.pay_day,
    )
    db.add(entity)
    db.commit()
    db.refresh(entity)
    return PaymentSourceCreateResponse(
        id=entity.id,
        name=entity.name,
        closing_day=entity.closing_day,
        pay_month_diff=entity.pay_month_diff,
        pay_day=entity.pay_day,
    )


# ---------- 3) 支払日算出 ----------


@app.post(
    "/calc-paid-date",
    response_model=PaidDateCalcResponse,
    summary="支払日算出",
    description="利用日と支出元IDから支払日を算出する",
)
def calc_paid_date_endpoint(
    body: PaidDateCalcRequest,
    db: Session = Depends(get_db),
) -> PaidDateCalcResponse:
    ps = db.query(PaymentSource).filter(PaymentSource.id == body.payment_source_id).first()
    if ps is None:
        raise HTTPException(status_code=404, detail="指定された支出元IDが見つかりません")
    paid = calc_paid_date(
        body.used_date,
        ps.closing_day,
        ps.pay_month_diff,
        ps.pay_day,
    )
    return PaidDateCalcResponse(paid_date=paid)


# ---------- 4) 収支登録 ----------


@app.post(
    "/transactions",
    response_model=TransactionCreateResponse,
    summary="収支登録",
    description="transactions にレコードを追加。予算名未指定時は「未分類」",
)
def create_transaction(
    body: TransactionCreate,
    db: Session = Depends(get_db),
) -> TransactionCreateResponse:
    budget_name = body.budget_name if body.budget_name is not None and body.budget_name != "" else "未分類"
    entity = Transaction(
        used_date=body.used_date,
        purpose=body.purpose,
        memo=body.memo or "",
        amount=body.amount,
        payment_source_id=body.payment_source_id,
        paid_date=body.paid_date,
        budget_name=budget_name,
    )
    db.add(entity)
    db.commit()
    db.refresh(entity)
    return TransactionCreateResponse(
        id=entity.id,
        used_date=entity.used_date,
        purpose=entity.purpose,
        memo=entity.memo,
        amount=entity.amount,
        payment_source_id=entity.payment_source_id,
        paid_date=entity.paid_date,
        budget_name=entity.budget_name,
    )


# ---------- 5) 収支更新 ----------


@app.put(
    "/transactions",
    summary="収支更新",
    description="指定IDの transactions を指定値で更新する（必須はIDのみ、他は任意）",
)
def update_transaction(
    body: TransactionUpdate,
    db: Session = Depends(get_db),
) -> dict[str, str]:
    entity = db.query(Transaction).filter(Transaction.id == body.id).first()
    if entity is None:
        raise HTTPException(status_code=404, detail="指定された収支IDが見つかりません")
    if body.used_date is not None:
        entity.used_date = body.used_date
    if body.purpose is not None:
        entity.purpose = body.purpose
    if body.memo is not None:
        entity.memo = body.memo
    if body.amount is not None:
        entity.amount = body.amount
    if body.payment_source_id is not None:
        entity.payment_source_id = body.payment_source_id
    if body.paid_date is not None:
        entity.paid_date = body.paid_date
    if body.budget_name is not None:
        entity.budget_name = body.budget_name
    db.commit()
    return {"message": "updated"}


# ---------- 6) 収支1件検索 ----------


@app.get(
    "/transactions/{transaction_id}",
    response_model=TransactionDetailResponse,
    summary="収支1件検索",
    description="transactions の ID で1件取得し、支出元名付きで返す",
)
def get_transaction(
    transaction_id: int,
    db: Session = Depends(get_db),
) -> TransactionDetailResponse:
    entity = (
        db.query(Transaction)
        .filter(Transaction.id == transaction_id)
        .first()
    )
    if entity is None:
        raise HTTPException(status_code=404, detail="指定された収支IDが見つかりません")
    return TransactionDetailResponse(
        id=entity.id,
        used_date=entity.used_date,
        purpose=entity.purpose,
        memo=entity.memo,
        amount=entity.amount,
        payment_source_id=entity.payment_source_id,
        paid_date=entity.paid_date,
        budget_name=entity.budget_name,
        payment_source_name=entity.payment_source.name,
    )


# ---------- 7) 収支利用日期間リスト検索 ----------


@app.post(
    "/transactions/search-by-used-date",
    response_model=TransactionListResponse,
    summary="収支利用日期間リスト検索",
    description="期間（自）<= used_date <= 期間（至）で検索",
)
def search_transactions_by_used_date(
    body: TransactionListByDateRequest,
    db: Session = Depends(get_db),
) -> TransactionListResponse:
    q = (
        db.query(Transaction)
        .join(PaymentSource, Transaction.payment_source_id == PaymentSource.id)
        .filter(
            Transaction.used_date >= body.date_from,
            Transaction.used_date <= body.date_to,
        )
        .order_by(Transaction.used_date, Transaction.id)
    )
    rows = q.all()
    items = [
        TransactionListItem(
            id=t.id,
            used_date=t.used_date,
            purpose=t.purpose,
            amount=t.amount,
            payment_source_id=t.payment_source_id,
            paid_date=t.paid_date,
            budget_name=t.budget_name,
            payment_source_name=t.payment_source.name,
        )
        for t in rows
    ]
    return TransactionListResponse(items=items)


# ---------- 8) 収支支払日期間リスト検索 ----------


@app.post(
    "/transactions/search-by-paid-date",
    response_model=TransactionListResponse,
    summary="収支支払日期間リスト検索",
    description="期間（自）<= paid_date <= 期間（至）で検索",
)
def search_transactions_by_paid_date(
    body: TransactionListByPaidDateRequest,
    db: Session = Depends(get_db),
) -> TransactionListResponse:
    q = (
        db.query(Transaction)
        .join(PaymentSource, Transaction.payment_source_id == PaymentSource.id)
        .filter(
            Transaction.paid_date >= body.date_from,
            Transaction.paid_date <= body.date_to,
        )
        .order_by(Transaction.paid_date, Transaction.id)
    )
    rows = q.all()
    items = [
        TransactionListItem(
            id=t.id,
            used_date=t.used_date,
            purpose=t.purpose,
            amount=t.amount,
            payment_source_id=t.payment_source_id,
            paid_date=t.paid_date,
            budget_name=t.budget_name,
            payment_source_name=t.payment_source.name,
        )
        for t in rows
    ]
    return TransactionListResponse(items=items)
