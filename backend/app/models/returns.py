from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, Numeric, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import ReturnStatus


class IndividualReturn(Base):
    """A Form 440 (emolument income) / Form 400 ITR style individual return.

    `inputs` and `computed` are JSON snapshots produced by
    app.services.tax_engine.compute_individual_tax so the exact figures a
    taxpayer saw/approved are preserved even if the underlying TaxYearConfig
    is edited later. `td4_input_ids` records which TD4Input rows fed this
    return, for traceability into the e-Tax export.
    """

    __tablename__ = "individual_returns"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), nullable=False)
    tax_year: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[ReturnStatus] = mapped_column(
        SAEnum(ReturnStatus, native_enum=False, length=32), default=ReturnStatus.DRAFT, nullable=False
    )

    inputs: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    computed: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    td4_input_ids: Mapped[list[int]] = mapped_column(JSON, nullable=False, default=list)

    refund_or_balance_due: Mapped[float] = mapped_column(Numeric(14, 2), default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    client: Mapped["Client"] = relationship()


class CorporateReturn(Base):
    """A Form 500 corporation tax return for one accounting period."""

    __tablename__ = "corporate_returns"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), nullable=False)
    tax_year: Mapped[int] = mapped_column(Integer, nullable=False)
    accounting_period_start: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    accounting_period_end: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    status: Mapped[ReturnStatus] = mapped_column(
        SAEnum(ReturnStatus, native_enum=False, length=32), default=ReturnStatus.DRAFT, nullable=False
    )

    inputs: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)
    computed: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    refund_or_balance_due: Mapped[float] = mapped_column(Numeric(14, 2), default=0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    client: Mapped["Client"] = relationship()


class VAT200Return(Base):
    """A bimonthly VAT 200 return."""

    __tablename__ = "vat200_returns"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), nullable=False)
    period_start: Mapped[str] = mapped_column(String(10), nullable=False)  # "YYYY-MM-DD"
    period_end: Mapped[str] = mapped_column(String(10), nullable=False)
    status: Mapped[ReturnStatus] = mapped_column(
        SAEnum(ReturnStatus, native_enum=False, length=32), default=ReturnStatus.DRAFT, nullable=False
    )

    standard_rated_sales: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    zero_rated_sales: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    exempt_sales: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    output_vat: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    input_vat: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    net_vat_payable: Mapped[float] = mapped_column(Numeric(14, 2), default=0)  # negative == refund due

    computed: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    client: Mapped["Client"] = relationship()
