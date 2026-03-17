"""Pydantic スキーマ（API リクエスト・レスポンス）"""
from datetime import date

from pydantic import BaseModel, Field


# ----- PaymentSource -----


class PaymentSourceItem(BaseModel):
    """支出元 1件（id, name, closing_day, pay_month_diff, pay_day）"""
    id: int
    name: str
    closing_day: int = Field(..., description="締日")
    pay_month_diff: int = Field(..., description="支払月差分")
    pay_day: int = Field(..., description="支払日")


class PaymentSourceListResponse(BaseModel):
    """1) 支出情報取得 レスポンス"""
    items: list[PaymentSourceItem]


class PaymentSourceCreate(BaseModel):
    """2) 支出情報登録 入力"""
    name: str = Field(..., description="名称")
    closing_day: int = Field(..., description="締日")
    pay_month_diff: int = Field(..., description="支払月差分")
    pay_day: int = Field(..., description="支払日")


class PaymentSourceCreateResponse(BaseModel):
    """2) 支出情報登録 レスポンス"""
    id: int
    name: str
    closing_day: int
    pay_month_diff: int
    pay_day: int


# ----- 支払日算出 -----


class PaidDateCalcRequest(BaseModel):
    """3) 支払日算出 入力"""
    used_date: date = Field(..., description="利用日")
    payment_source_id: int = Field(..., description="支出元ID")


class PaidDateCalcResponse(BaseModel):
    """3) 支払日算出 レスポンス"""
    paid_date: date


# ----- Transaction -----


class TransactionCreate(BaseModel):
    """4) 収支登録 入力"""
    used_date: date = Field(..., description="日付（利用日）")
    purpose: str = Field(..., description="目的")
    memo: str = Field("", description="メモ")
    amount: int = Field(..., description="金額")
    payment_source_id: int = Field(..., description="支出元ID")
    paid_date: date = Field(..., description="支出日")
    budget_name: str | None = Field(None, description="予算名（未指定時は未分類）")


class TransactionCreateResponse(BaseModel):
    """4) 収支登録 レスポンス"""
    id: int
    used_date: date
    purpose: str
    memo: str
    amount: int
    payment_source_id: int
    paid_date: date
    budget_name: str


class TransactionUpdate(BaseModel):
    """5) 収支更新 入力（ID必須、他は任意）"""
    id: int = Field(..., description="transactionsのID")
    used_date: date | None = None
    purpose: str | None = None
    memo: str | None = None
    amount: int | None = None
    payment_source_id: int | None = None
    paid_date: date | None = None
    budget_name: str | None = None


class TransactionDetailResponse(BaseModel):
    """6) 収支1件検索 レスポンス"""
    id: int
    used_date: date
    purpose: str
    memo: str
    amount: int
    payment_source_id: int
    paid_date: date
    budget_name: str
    payment_source_name: str


class TransactionListItem(BaseModel):
    """7)(8) リスト検索 1件"""
    id: int
    used_date: date
    purpose: str
    amount: int
    payment_source_id: int
    paid_date: date
    budget_name: str
    payment_source_name: str


class TransactionListResponse(BaseModel):
    """7)(8) リスト検索 レスポンス"""
    items: list[TransactionListItem]


class TransactionListByDateRequest(BaseModel):
    """7) 収支利用日期間リスト検索 入力"""
    date_from: date = Field(..., description="期間（自）")
    date_to: date = Field(..., description="期間（至）")


class TransactionListByPaidDateRequest(BaseModel):
    """8) 収支支払日期間リスト検索 入力"""
    date_from: date = Field(..., description="期間（自）")
    date_to: date = Field(..., description="期間（至）")
