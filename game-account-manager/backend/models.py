from datetime import date, datetime

from sqlalchemy import String, Integer, Date, DateTime, ForeignKey, UniqueConstraint, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database import Base


class Account(Base):
    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_name: Mapped[str] = mapped_column(String(100), nullable=False)
    password: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    email: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    server: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    region: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    class_name: Mapped[str] = mapped_column("class", String(100), nullable=False, default="")
    pin_code: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    phone: Mapped[str] = mapped_column(String(50), nullable=False, default="")
    cloud_device: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    location: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    current_diamonds: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    verify_code_url: Mapped[str] = mapped_column(String(500), nullable=False, default="")
    recovery_code: Mapped[str] = mapped_column(String(100), nullable=False, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    records: Mapped[list["DiamondRecord"]] = relationship(
        "DiamondRecord", back_populates="account", cascade="all, delete-orphan"
    )
    snapshots: Mapped[list["DiamondSnapshot"]] = relationship(
        "DiamondSnapshot", back_populates="account", cascade="all, delete-orphan"
    )
    sales: Mapped[list["DiamondSale"]] = relationship(
        "DiamondSale", back_populates="account", cascade="all, delete-orphan"
    )


class DiamondRecord(Base):
    __tablename__ = "diamond_records"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(Integer, ForeignKey("accounts.id"), nullable=False)
    amount: Mapped[int] = mapped_column(Integer, nullable=False)
    location: Mapped[str] = mapped_column(String(200), nullable=False, default="")
    recorded_at: Mapped[date] = mapped_column(Date, nullable=False)

    account: Mapped["Account"] = relationship("Account", back_populates="records")


class DiamondSnapshot(Base):
    __tablename__ = "diamond_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(Integer, ForeignKey("accounts.id"), nullable=False)
    date: Mapped[date] = mapped_column(Date, nullable=False)
    diamonds: Mapped[int] = mapped_column(Integer, nullable=False)
    change: Mapped[int] = mapped_column(Integer, nullable=False, default=0)

    account: Mapped["Account"] = relationship("Account", back_populates="snapshots")

    __table_args__ = (
        UniqueConstraint("account_id", "date", name="uq_account_date_snapshot"),
    )


class DiamondSale(Base):
    __tablename__ = "diamond_sales"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    account_id: Mapped[int] = mapped_column(Integer, ForeignKey("accounts.id"), nullable=False)
    diamonds_sold: Mapped[int] = mapped_column(Integer, nullable=False)
    sale_date: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.now())

    account: Mapped["Account"] = relationship("Account", back_populates="sales")
