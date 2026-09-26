from datetime import datetime, timezone
from typing import Any, Optional

from sqlalchemy import Boolean, DateTime, Integer, JSON, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class TaxYearConfig(Base):
    """Admin-configurable statutory tax constants for a single tax year.

    This is the "Tax Configuration Service" the spec calls for: nothing in
    app.services.tax_engine hardcodes a rate or threshold. Every number here
    can be edited by a system_admin (see app/routers/admin.py) without a code
    change or redeploy, and every calculation in the tax engine looks up the
    active TaxYearConfig for the year it is computing.

    Simple scalars use dedicated columns so they're easy to query/validate.
    Structured tables (NIS earnings classes, PAYE bands, deduction caps,
    wear-and-tear rates) use JSON columns because their shape is inherently
    tabular/nested and the number of rows can change if the law changes
    (e.g. NIS added a 17th class), which a fixed set of columns can't absorb.

    Figures seeded for tax year 2026 are sourced from:
      - National Insurance (Contribution) (Amendment) Regulations, 2025
        (Legal Notice No. 487, effective 5 Jan 2026) for the NIS table.
      - PwC Worldwide Tax Summaries (Trinidad & Tobago, individual/corporate)
        for PAYE bands, personal allowance, Business Levy, Green Fund Levy,
        Health Surcharge, VAT, corporate tax, wear-and-tear classes, and
        deduction caps.
      - ird.gov.tt PAYE Annual Return guide for the TD4 CSV schema (used by
        the export engine, not this table, but same research pass).
    See NOTES.md at the repo root for full citations and anything still
    unverified against an official BIR source.
    """

    __tablename__ = "tax_year_configs"

    id: Mapped[int] = mapped_column(primary_key=True)
    tax_year: Mapped[int] = mapped_column(Integer, unique=True, index=True, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    label: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)

    # --- Personal income tax ---
    personal_allowance: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    # Ordered list of {"upto": <chargeable income ceiling or null for open-ended>, "rate": <decimal>}
    # e.g. [{"upto": 1000000, "rate": 0.25}, {"upto": null, "rate": 0.30}]
    paye_bands: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)
    # Fraction of the employee's NIS contribution that is deductible before PAYE (currently 0.70)
    nis_deductible_fraction: Mapped[float] = mapped_column(Numeric(5, 4), nullable=False, default=0.70)

    # --- Business Levy / Green Fund Levy ---
    business_levy_rate: Mapped[float] = mapped_column(Numeric(6, 4), nullable=False)
    business_levy_annual_threshold: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    business_levy_exempt_years: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    green_fund_levy_rate: Mapped[float] = mapped_column(Numeric(6, 4), nullable=False)

    # --- Corporate tax ---
    corporate_tax_rate_standard: Mapped[float] = mapped_column(Numeric(6, 4), nullable=False)
    corporate_tax_rate_banks_petrochemical: Mapped[float] = mapped_column(Numeric(6, 4), nullable=False)
    corporate_tax_rate_sme_stock_exchange: Mapped[float] = mapped_column(Numeric(6, 4), nullable=False, default=0.0)

    # --- VAT ---
    vat_standard_rate: Mapped[float] = mapped_column(Numeric(6, 4), nullable=False)
    vat_registration_threshold: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)

    # --- Health Surcharge ---
    health_surcharge_high_weekly: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    health_surcharge_low_weekly: Mapped[float] = mapped_column(Numeric(8, 2), nullable=False)
    health_surcharge_monthly_threshold: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False)

    # --- NIS ---
    nis_combined_rate: Mapped[float] = mapped_column(Numeric(6, 4), nullable=False)
    # List of 16 (or more, if the law changes) rows:
    # {"class_name": "I", "weekly_min": 200, "weekly_max": 339.99, "assumed_avg_weekly": 270.00,
    #  "employee_weekly": 43.80, "employer_weekly": 189.80, "total_weekly": 233.60}
    nis_earnings_classes: Mapped[list[dict[str, Any]]] = mapped_column(JSON, nullable=False)

    # --- Deduction caps (individual & corporate) ---
    # {
    #   "tertiary_education_cap": 72000,
    #   "pension_annuity_nis_aggregate_cap": 60000,
    #   "first_time_homeowner_interest_cap": 30000,
    #   "charitable_donation_pct_of_income": 0.15,
    #   "animal_shelter_individual_pct": 0.20, "animal_shelter_individual_cap": 20000,
    #   "animal_shelter_company_pct": 0.15, "animal_shelter_company_cap": 100000
    # }
    deduction_caps: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    # --- Wear and tear / capital allowance classes (Schedule A) ---
    # {"A": 0.10, "B": 0.30, "C": 0.333, "D": 0.40}
    wear_and_tear_classes: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)

    # --- Filing administration ---
    individual_filing_deadline: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)  # "YYYY-04-30"
    corporate_filing_deadline: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    individual_late_penalty_per_6mo: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=100.0)
    corporate_late_penalty_per_6mo: Mapped[float] = mapped_column(Numeric(10, 2), nullable=False, default=1000.0)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.now(timezone.utc))
    updated_at: Mapped[datetime] = mapped_column(
        DateTime, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )
