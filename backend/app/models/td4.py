from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Integer, Numeric, String
from sqlalchemy import Enum as SAEnum
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base
from app.models.enums import TD4Source, TD4Type


class TD4Input(Base):
    """One TD4 certificate's worth of data for one employee, for one income year.

    Fields mirror the BIR TD4 Supplementary CSV schema 1:1 (see
    app.services.etax_export.TD4_SUPPLEMENTARY_FIELD_ORDER) so a batch of these
    rows can be serialized straight into the official upload format, and a
    single row also feeds the individual tax engine calculation for the
    employee who owns it.

    `client_id` is the *employee* (or pensioner) this TD4 belongs to. For a
    corporate/firm bulk upload, many TD4Inputs share the same
    `employer_bir_number` / `employer_paye_number` but different `client_id`s.
    """

    __tablename__ = "td4_inputs"

    id: Mapped[int] = mapped_column(primary_key=True)
    client_id: Mapped[int] = mapped_column(ForeignKey("clients.id"), nullable=False)
    income_year: Mapped[int] = mapped_column(Integer, nullable=False)

    source: Mapped[TD4Source] = mapped_column(
        SAEnum(TD4Source, native_enum=False, length=32), default=TD4Source.MANUAL, nullable=False
    )
    td4_type: Mapped[TD4Type] = mapped_column(
        SAEnum(TD4Type, native_enum=False, length=32), default=TD4Type.INCOME, nullable=False
    )

    # --- Employer identification (fields 2-3 of the BIR schema) ---
    employer_bir_number: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    employer_paye_number: Mapped[Optional[str]] = mapped_column(String(12), nullable=True)
    employer_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # --- Employee identification (fields 4-7) ---
    employee_bir_number: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    employee_name: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    employee_address: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    employee_nis_number: Mapped[Optional[str]] = mapped_column(String(9), nullable=True)

    # --- Amount fields (8-26), all "amount to the nearest cent" per BIR spec ---
    total_deductions: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    weeks_employed: Mapped[int] = mapped_column(Integer, default=52)
    remuneration: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    commission: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    allowance_it76: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    travel_allowance: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    other_allowance: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    previous_income: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    savings_plan: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    gross_earnings: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    employer_contributions: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    travel_dispensation: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    employee_contributions: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    nis_deducted: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    income_tax: Mapped[float] = mapped_column(Numeric(14, 2), default=0)
    total_health_surcharge_weeks: Mapped[int] = mapped_column(Integer, default=0)
    health_surcharge_weeks_at_high: Mapped[int] = mapped_column(Integer, default=0)
    health_surcharge_weeks_at_low: Mapped[int] = mapped_column(Integer, default=0)
    health_surcharge_amount: Mapped[float] = mapped_column(Numeric(14, 2), default=0)

    # OCR/manual-correction bookkeeping (drag-and-drop TD4 parsing interface)
    ocr_raw_text: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    ocr_confidence: Mapped[Optional[float]] = mapped_column(Numeric(5, 4), nullable=True)
    manually_corrected: Mapped[bool] = mapped_column(default=False)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))

    client: Mapped["Client"] = relationship()
