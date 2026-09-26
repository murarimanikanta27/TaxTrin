"""Per-employee payroll line computation: NIS + Health Surcharge + PAYE.

Used by the PayrollRun API (monthly reconciliation) and by the monthly
PAYE/NIS/Health Surcharge summary PDF.
"""
from decimal import Decimal

from app.models.tax_config import TaxYearConfig
from app.services.tax_engine import compute_health_surcharge, compute_nis, compute_paye, d, money

_FREQUENCY_TO_WEEKS = {
    "weekly": Decimal("1"),
    "fortnightly": Decimal("2"),
    "monthly": Decimal("52") / Decimal("12"),  # ~4.333 contribution weeks/month, matches NIBTT monthly averaging
}


def compute_payroll_line(config: TaxYearConfig, gross_pay, frequency: str = "monthly") -> dict:
    """Compute one employee's statutory deductions for one pay period.

    `gross_pay` is the amount for THIS pay period (not annualized).
    `frequency`: "weekly" | "fortnightly" | "monthly".
    """
    gross = d(gross_pay)
    weeks_in_period = _FREQUENCY_TO_WEEKS.get(frequency, Decimal("1"))

    weekly_equivalent = gross / weeks_in_period if weeks_in_period else gross
    nis = compute_nis(config, weekly_earnings=weekly_equivalent, weeks=weeks_in_period)

    monthly_equivalent = gross if frequency == "monthly" else weekly_equivalent * (Decimal("52") / Decimal("12"))
    hs = compute_health_surcharge(config, monthly_emoluments=monthly_equivalent, weeks=weeks_in_period)

    # Annualize gross pay to run it through the progressive PAYE bands, then
    # take this period's pro-rata share -- the standard PAYE-withholding
    # approximation (actual annual reconciliation happens at TD4/Form 440 time).
    periods_per_year = Decimal("52") / weeks_in_period if weeks_in_period else Decimal("1")
    annual_gross = gross * periods_per_year
    annual_nis_employee = nis.employee_total * periods_per_year / max(weeks_in_period, Decimal("1"))
    # nis.employee_total already covers `weeks_in_period`; annualize by periods_per_year directly:
    annual_nis_employee = nis.employee_total * periods_per_year

    paye = compute_paye(config, annual_gross_income=annual_gross, annual_employee_nis=annual_nis_employee)
    period_paye = paye.total_tax / periods_per_year if periods_per_year else paye.total_tax

    net_pay = gross - nis.employee_total - hs.employee_total - period_paye

    return {
        "gross_pay": money(gross),
        "nis_class_name": nis.class_name,
        "nis_employee": money(nis.employee_total),
        "nis_employer": money(nis.employer_total),
        "health_surcharge_employee": money(hs.employee_total),
        "health_surcharge_employer": money(hs.employer_total),
        "paye_deducted": money(period_paye),
        "net_pay": money(net_pay),
        "annualized": {
            "annual_gross": money(annual_gross),
            "annual_employee_nis": money(annual_nis_employee),
            "annual_paye": money(paye.total_tax),
            "chargeable_income": money(paye.chargeable_income),
        },
    }
