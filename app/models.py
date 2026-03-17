"""SQLAlchemy ORM モデル"""
from sqlalchemy import Column, Date, DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import relationship

from app.database import Base


class PaymentSource(Base):
    """支払元マスタ"""
    __tablename__ = "payment_sources"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String, nullable=False)
    closing_day = Column(Integer, nullable=False)
    pay_month_diff = Column(Integer, nullable=False)
    pay_day = Column(Integer, nullable=False)

    transactions = relationship("Transaction", back_populates="payment_source")

    def __repr__(self) -> str:
        return f"<PaymentSource(id={self.id}, name={self.name})>"


class Transaction(Base):
    """取引（収支）"""
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    used_date = Column(Date, nullable=False)
    purpose = Column(String, nullable=False)
    memo = Column(String, nullable=False)
    amount = Column(Integer, nullable=False)
    payment_source_id = Column(Integer, ForeignKey("payment_sources.id"), nullable=False)
    paid_date = Column(Date, nullable=False)
    budget_name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=False), nullable=False, server_default=func.now())
    updated_at = Column(DateTime(timezone=False), nullable=False, server_default=func.now(), onupdate=func.now())

    payment_source = relationship("PaymentSource", back_populates="transactions")

    def __repr__(self) -> str:
        return f"<Transaction(id={self.id}, used_date={self.used_date})>"
