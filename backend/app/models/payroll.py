from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import DateTime, ForeignKey, Integer, JSON, Numeric, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import PayFrequency


class PayrollRun(Base):
    """One payroll cycle for a corporate/sole-trader employer client.

    Drives the "full payroll reconciliation (PAYE, NIS, Health Surcharge)"
    requirement and the monthly PAYE/NIS/Health Surcharge summary report.
    Each run has many PayrollLine rows, one per employee.
    """

    __tablename__ = "payroll_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), nullable=False)  # the employer
    pay_period_start: Mapped[str] = mapped_column(String(10), nullable=False)
    pay_period_end: Mapped[str] = mapped_column(String(10), nullable=False)
    frequency: Mapped[PayFrequency] = mapped_column(
        SAEnum(PayFrequency, native_enum=False, length=32), default=PayFrequency.MONTHLY, nullable=False
    )

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    client: Mapped["Client"] = relationship()
    lines: Mapped[list["PayrollLine"]] = relationship(back_populates="run", cascade="all, delete-orphan")


class PayrollLine(Base):
    """One employee's pay + statutory deductions within a PayrollRun."""

    __tablename__ = "payroll_lines"

    id: Mapped[int] = mapped_column(primary_key=True)
    run_id: Mapped[int] = mapped_column(ForeignKey("payroll_runs.id"), nullable=False)
    employee_client_id: Mapped[Optional[int]] = mapped_column(ForeignKey("clients.id"), nullable=True)
    employee_name: Mapped[str] = mapped_column(String(255), nullable=False)

    gross_pay: Mapped[float] = mapped_column(Numeric(14, 2), default=0)

    nis_class_name: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    nis_employee: Mapped[float] = mapped_column(Numeric(10, 2), default=0)
    nis_employer: Mapped[float] = mapped_column(Numeric(10, 2), default=0)

    health_surcharge_employee: Mapped[float] = mapped_column(Numeric(8, 2), default=0)
    health_surcharge_employer: Mapped[float] = mapped_column(Numeric(8, 2), default=0)

    paye_deducted: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    net_pay: Mapped[float] = mapped_column(Numeric(14, 2), default=0)

    computed: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False, default=dict)

    run: Mapped["PayrollRun"] = relationship(back_populates="lines")
