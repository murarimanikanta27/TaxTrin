"""Trinidad & Tobago statutory tax calculation engine.

Every function here takes a `TaxYearConfig` row as an argument and reads
every rate/threshold/table from it. Nothing statutory is a Python literal in
this module -- if a rate changes, a system_admin edits the TaxYearConfig row
(see app/routers/admin.py) and every calculation picks it up immediately.

All money math uses `Decimal` (never `float`) to avoid floating-point cent
drift, and rounds to 2dp with ROUND_HALF_UP at the point a figure is reported
(intermediate values stay full-precision until the final rounding step of
each function) which matches how BIR/NIBTT round monetary amounts.
"""
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal

from app.models.tax_config import TaxYearConfig

TWO_PLACES = Decimal("0.01")


def d(value) -> Decimal:
    """Coerce any numeric (float, int, str, Decimal, None) to Decimal safely."""
    if value is None:
        return Decimal("0")
    if isinstance(value, Decimal):
        return value
    return Decimal(str(value))


def money(value: Decimal) -> float:
    """Round a Decimal to 2dp (half-up) and return as float for JSON output."""
    return float(value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP))


# ---------------------------------------------------------------------------
# NIS (National Insurance)
# ---------------------------------------------------------------------------


@dataclass
class NISResult:
    class_name: str | None
    weekly_employee: Decimal
    weekly_employer: Decimal
    weekly_total: Decimal
    weeks: Decimal
    employee_total: Decimal
    employer_total: Decimal
    combined_total: Decimal


def find_nis_class(config: TaxYearConfig, weekly_earnings: Decimal) -> dict | None:
    """Look up the NIBTT earnings class a given weekly wage falls into.

    Classes are contiguous [weekly_min, weekly_max] bands except the top
    class, whose `weekly_max` is None (open-ended, "3138 and over").
    Earnings below the lowest class's minimum return None (not insurable
    under the standard employed-person table).
    """
    classes = sorted(config.nis_earnings_classes, key=lambda c: d(c["weekly_min"]))
    if not classes or weekly_earnings < d(classes[0]["weekly_min"]):
        return None
    for row in classes:
        lo = d(row["weekly_min"])
        hi = row.get("weekly_max")
        if weekly_earnings < lo:
            continue
        if hi is None or weekly_earnings <= d(hi):
            return row
    # Above the highest defined max (shouldn't happen if the table's top
    # class has weekly_max = None, but guards against a misconfigured table).
    return classes[-1]


def compute_nis(config: TaxYearConfig, weekly_earnings, weeks: float = 52) -> NISResult:
    """Compute NIS contributions for an employee over a number of weeks.

    `weekly_earnings` should be the employee's average insurable weekly wage.
    Returns per-week employee/employer amounts (straight from the NIBTT
    table, which is NOT a flat percentage of earnings) plus totals scaled by
    `weeks`.
    """
    earnings = d(weekly_earnings)
    weeks_d = d(weeks)
    row = find_nis_class(config, earnings)
    if row is None:
        zero = Decimal("0")
        return NISResult(None, zero, zero, zero, weeks_d, zero, zero, zero)

    weekly_employee = d(row["employee_weekly"])
    weekly_employer = d(row["employer_weekly"])
    weekly_total = weekly_employee + weekly_employer

    return NISResult(
        class_name=row["class_name"],
        weekly_employee=weekly_employee,
        weekly_employer=weekly_employer,
        weekly_total=weekly_total,
        weeks=weeks_d,
        employee_total=weekly_employee * weeks_d,
        employer_total=weekly_employer * weeks_d,
        combined_total=weekly_total * weeks_d,
    )


# ---------------------------------------------------------------------------
# Health Surcharge
# ---------------------------------------------------------------------------


@dataclass
class HealthSurchargeResult:
    weekly_rate: Decimal
    weeks: Decimal
    employee_total: Decimal
    employer_total: Decimal
    combined_total: Decimal


def compute_health_surcharge(config: TaxYearConfig, monthly_emoluments, weeks: float = 52) -> HealthSurchargeResult:
    """TT$8.25/wk if monthly emoluments exceed the threshold (currently
    $469.99), else TT$4.80/wk. The employer matches the employee's
    contribution (both remitted together to the BIR).
    """
    monthly = d(monthly_emoluments)
    threshold = d(config.health_surcharge_monthly_threshold)
    weekly_rate = (
        d(config.health_surcharge_high_weekly) if monthly > threshold else d(config.health_surcharge_low_weekly)
    )
    weeks_d = d(weeks)
    employee_total = weekly_rate * weeks_d
    employer_total = weekly_rate * weeks_d  # employer match
    return HealthSurchargeResult(
        weekly_rate=weekly_rate,
        weeks=weeks_d,
        employee_total=employee_total,
        employer_total=employer_total,
        combined_total=employee_total + employer_total,
    )


# ---------------------------------------------------------------------------
# PAYE / Chargeable income
# ---------------------------------------------------------------------------


@dataclass
class PAYEResult:
    gross_income: Decimal
    personal_allowance: Decimal
    nis_deductible_portion: Decimal
    other_deductions: Decimal
    chargeable_income: Decimal
    tax_by_band: list[dict]
    total_tax: Decimal


def compute_deduction_totals(config: TaxYearConfig, deductions: dict) -> tuple[Decimal, list[str]]:
    """Sum an individual's claimed deductions, applying each statutory cap.

    `deductions` keys (all optional, default 0):
      tertiary_education, pension_annuity_nis_voluntary,
      first_time_homeowner_interest, charitable_donations,
      animal_shelter_donations, total_income_for_pct_caps
    Returns (capped_total, list_of_notes) where notes explain any capping
    applied (useful to surface in the UI / audit trail).
    """
    caps = config.deduction_caps
    notes: list[str] = []
    total = Decimal("0")

    tertiary = d(deductions.get("tertiary_education"))
    tertiary_cap = d(caps.get("tertiary_education_cap"))
    if tertiary > tertiary_cap:
        notes.append(f"Tertiary education expenses capped at ${tertiary_cap}")
        tertiary = tertiary_cap
    total += tertiary

    pension = d(deductions.get("pension_annuity_nis_voluntary"))
    pension_cap = d(caps.get("pension_annuity_nis_aggregate_cap"))
    if pension > pension_cap:
        notes.append(f"Pension/annuity/NIS aggregate capped at ${pension_cap}")
        pension = pension_cap
    total += pension

    homeowner = d(deductions.get("first_time_homeowner_interest"))
    homeowner_cap = d(caps.get("first_time_homeowner_interest_cap"))
    if homeowner > homeowner_cap:
        notes.append(f"First-time homeowner mortgage interest capped at ${homeowner_cap}")
        homeowner = homeowner_cap
    total += homeowner

    income_base = d(deductions.get("total_income_for_pct_caps"))
    charitable = d(deductions.get("charitable_donations"))
    charitable_cap = income_base * d(caps.get("charitable_donation_pct_of_income"))
    if charitable > charitable_cap:
        notes.append(
            f"Charitable donations capped at {d(caps.get('charitable_donation_pct_of_income')) * 100}% of income"
            f" (${money(charitable_cap)})"
        )
        charitable = charitable_cap
    total += charitable

    animal = d(deductions.get("animal_shelter_donations"))
    animal_pct_cap = income_base * d(caps.get("animal_shelter_individual_pct"))
    animal_abs_cap = d(caps.get("animal_shelter_individual_cap"))
    animal_cap = min(animal_pct_cap, animal_abs_cap) if income_base > 0 else animal_abs_cap
    if animal > animal_cap:
        notes.append(f"Animal shelter donation capped at ${money(animal_cap)}")
        animal = animal_cap
    total += animal

    return total, notes


def compute_paye(
    config: TaxYearConfig,
    annual_gross_income,
    annual_employee_nis,
    other_deductions=0,
) -> PAYEResult:
    """Compute chargeable income and PAYE liability for a year.

    Sequence (per BIR/NIBTT guidance): take gross income, subtract the
    deductible fraction of the employee's annual NIS contribution, subtract
    other approved deductions, subtract the personal allowance, then apply
    the progressive PAYE bands to what remains.
    """
    gross = d(annual_gross_income)
    nis_annual = d(annual_employee_nis)
    nis_deductible = nis_annual * d(config.nis_deductible_fraction)
    other = d(other_deductions)
    allowance = d(config.personal_allowance)

    chargeable = gross - nis_deductible - other - allowance
    if chargeable < 0:
        chargeable = Decimal("0")

    tax_by_band = []
    remaining = chargeable
    lower_bound = Decimal("0")
    total_tax = Decimal("0")

    for band in config.paye_bands:
        rate = d(band["rate"])
        upto = band.get("upto")
        band_ceiling = d(upto) if upto is not None else None
        band_width = (band_ceiling - lower_bound) if band_ceiling is not None else remaining
        taxable_in_band = min(remaining, band_width) if band_width is not None else remaining
        if taxable_in_band < 0:
            taxable_in_band = Decimal("0")
        band_tax = taxable_in_band * rate
        if taxable_in_band > 0:
            tax_by_band.append(
                {
                    "from": money(lower_bound),
                    "to": money(band_ceiling) if band_ceiling is not None else None,
                    "rate": float(rate),
                    "taxable_amount": money(taxable_in_band),
                    "tax": money(band_tax),
                }
            )
        total_tax += band_tax
        remaining -= taxable_in_band
        lower_bound = band_ceiling if band_ceiling is not None else lower_bound
        if remaining <= 0:
            break

    return PAYEResult(
        gross_income=gross,
        personal_allowance=allowance,
        nis_deductible_portion=nis_deductible,
        other_deductions=other,
        chargeable_income=chargeable,
        tax_by_band=tax_by_band,
        total_tax=total_tax,
    )


# ---------------------------------------------------------------------------
# Business Levy / Green Fund Levy (individuals & sole traders)
# ---------------------------------------------------------------------------


@dataclass
class LeviesResult:
    business_levy_gross: Decimal
    business_levy_payable: Decimal
    business_levy_exempt: bool
    green_fund_levy: Decimal


def compute_business_and_green_fund_levy(
    config: TaxYearConfig,
    gross_receipts,
    income_tax_liability,
    years_in_business: int | None = None,
) -> LeviesResult:
    """Business Levy is only payable to the extent it exceeds the income tax
    liability, is exempt below the annual gross-receipts threshold, and is
    exempt for the first N years of the business (default 3, per statute).
    Green Fund Levy applies to gross income/receipts with no threshold and no
    income-tax offset, and is not deductible.
    """
    gross = d(gross_receipts)
    threshold = d(config.business_levy_annual_threshold)
    exempt_years = config.business_levy_exempt_years

    is_new_business_exempt = years_in_business is not None and years_in_business < exempt_years
    below_threshold = gross <= threshold
    exempt = is_new_business_exempt or below_threshold

    business_levy_gross = gross * d(config.business_levy_rate)
    if exempt:
        business_levy_payable = Decimal("0")
    else:
        excess = business_levy_gross - d(income_tax_liability)
        business_levy_payable = excess if excess > 0 else Decimal("0")

    green_fund_levy = gross * d(config.green_fund_levy_rate)

    return LeviesResult(
        business_levy_gross=business_levy_gross,
        business_levy_payable=business_levy_payable,
        business_levy_exempt=exempt,
        green_fund_levy=green_fund_levy,
    )


# ---------------------------------------------------------------------------
# Corporate tax
# ---------------------------------------------------------------------------


@dataclass
class CorporateTaxResult:
    chargeable_profits: Decimal
    rate_applied: Decimal
    corporation_tax: Decimal
    business_levy: LeviesResult
    total_statutory_liability: Decimal


def compute_corporate_tax(
    config: TaxYearConfig,
    chargeable_profits,
    gross_receipts,
    company_category: str = "standard",
) -> CorporateTaxResult:
    """Corporation tax + Business Levy + Green Fund Levy for a company.

    `company_category`: "standard" | "bank_or_petrochemical" | "sme_stock_exchange"
    """
    profits = d(chargeable_profits)
    if company_category == "bank_or_petrochemical":
        rate = d(config.corporate_tax_rate_banks_petrochemical)
    elif company_category == "sme_stock_exchange":
        rate = d(config.corporate_tax_rate_sme_stock_exchange)
    else:
        rate = d(config.corporate_tax_rate_standard)

    corp_tax = profits * rate if profits > 0 else Decimal("0")

    levies = compute_business_and_green_fund_levy(
        config, gross_receipts=gross_receipts, income_tax_liability=corp_tax
    )

    total = corp_tax + levies.business_levy_payable + levies.green_fund_levy

    return CorporateTaxResult(
        chargeable_profits=profits,
        rate_applied=rate,
        corporation_tax=corp_tax,
        business_levy=levies,
        total_statutory_liability=total,
    )


# ---------------------------------------------------------------------------
# VAT 200
# ---------------------------------------------------------------------------


@dataclass
class VATResult:
    output_vat: Decimal
    input_vat: Decimal
    net_vat_payable: Decimal  # negative => refund due to taxpayer


def compute_vat(
    config: TaxYearConfig,
    standard_rated_sales,
    input_vat_paid,
    output_vat_override=None,
) -> VATResult:
    """Compute output/input VAT and the net payable (or refundable) amount.

    If `output_vat_override` is given (e.g. VAT already itemised on
    invoices) it's used as-is; otherwise output VAT is derived from
    `standard_rated_sales * vat_standard_rate`.
    """
    sales = d(standard_rated_sales)
    output_vat = d(output_vat_override) if output_vat_override is not None else sales * d(config.vat_standard_rate)
    input_vat = d(input_vat_paid)
    net = output_vat - input_vat
    return VATResult(output_vat=output_vat, input_vat=input_vat, net_vat_payable=net)


# ---------------------------------------------------------------------------
# Wear and tear / capital allowances (Schedule A)
# ---------------------------------------------------------------------------


@dataclass
class WearAndTearLine:
    description: str
    asset_class: str
    rate: Decimal
    opening_wdv: Decimal
    additions: Decimal
    allowance: Decimal
    closing_wdv: Decimal


def compute_wear_and_tear(config: TaxYearConfig, assets: list[dict]) -> list[WearAndTearLine]:
    """Declining-balance wear-and-tear allowance per asset class.

    Each item in `assets`: {"description": str, "asset_class": "A"|"B"|"C"|"D",
    "opening_wdv": number, "additions": number}. Allowance is computed on
    (opening_wdv + additions) at the class rate, matching the "aggregate
    expenditure ... on a declining-balance basis" rule.
    """
    classes = config.wear_and_tear_classes
    lines: list[WearAndTearLine] = []
    for asset in assets:
        asset_class = asset["asset_class"]
        rate = d(classes.get(asset_class, 0))
        opening = d(asset.get("opening_wdv"))
        additions = d(asset.get("additions"))
        base = opening + additions
        allowance = base * rate
        closing = base - allowance
        lines.append(
            WearAndTearLine(
                description=asset.get("description", ""),
                asset_class=asset_class,
                rate=rate,
                opening_wdv=opening,
                additions=additions,
                allowance=allowance,
                closing_wdv=closing,
            )
        )
    return lines
