"""Canonical Trinidad & Tobago tax year 2026 statutory figures.

Centralized here (rather than inline in scripts/seed.py) so both the seed
script and the test suite can build a real TaxYearConfig from the same
source data.

SOURCES (see NOTES.md for the full citation list and confidence notes):
  - NIS earnings classes + rates: National Insurance (Contribution)
    (Amendment) Regulations, 2025, Legal Notice No. 487 of 2025, effective
    5 January 2026 (16.2% combined contribution rate table).
  - PAYE bands, personal allowance, NIS-deductible fraction: PwC Worldwide
    Tax Summaries - Trinidad and Tobago (Individual: Taxes on personal
    income, Other taxes; accessed 2026).
  - Health Surcharge thresholds: ird.gov.tt/health-surcharge and PwC Tax
    Summaries (Individual: Other taxes).
  - Business Levy / Green Fund Levy: PwC Tax Summaries (Corporate: Other
    taxes; Individual: Other taxes).
  - Corporate tax rates: PwC Tax Summaries (Corporate: Taxes on corporate
    income).
  - VAT rate & registration threshold: PwC Tax Summaries (Corporate: Other
    taxes) and ird.gov.tt/VAT/registration.
  - Deduction caps (tertiary education, pension/annuity/NIS aggregate,
    charitable donations, animal shelter): PwC Tax Summaries (Individual:
    Deductions) and ird.gov.tt/deductions/tertiary-education-expenses.
  - First-time homeowner mortgage interest cap ($30,000): stated in the
    original TaxTrin spec; NOT independently re-verified against a primary
    BIR source in this pass -- flagged UNVERIFIED in NOTES.md.
  - Wear-and-tear (capital allowance) classes A-D: PwC Tax Summaries
    (Corporate: Deductions).
"""

TAX_YEAR_2026 = {
    "tax_year": 2026,
    "is_active": True,
    "label": "Trinidad & Tobago - Tax Year 2026",
    # --- Personal income tax ---
    "personal_allowance": 90000.00,
    "paye_bands": [
        {"upto": 1_000_000, "rate": 0.25},
        {"upto": None, "rate": 0.30},
    ],
    "nis_deductible_fraction": 0.70,
    # --- Business Levy / Green Fund Levy ---
    "business_levy_rate": 0.006,
    "business_levy_annual_threshold": 360_000.00,
    "business_levy_exempt_years": 3,
    "green_fund_levy_rate": 0.003,
    # --- Corporate tax ---
    "corporate_tax_rate_standard": 0.30,
    "corporate_tax_rate_banks_petrochemical": 0.35,
    "corporate_tax_rate_sme_stock_exchange": 0.0,
    # --- VAT ---
    "vat_standard_rate": 0.125,
    "vat_registration_threshold": 600_000.00,
    # --- Health Surcharge ---
    "health_surcharge_high_weekly": 8.25,
    "health_surcharge_low_weekly": 4.80,
    "health_surcharge_monthly_threshold": 469.99,
    # --- NIS: 16 earnings classes, effective 5 Jan 2026 (16.2% combined rate) ---
    #
    # Source: National Insurance (Contribution) (Amendment) Regulations, 2025
    # (Legal Notice No. 487/2025) publishes only the COMBINED weekly
    # contribution per class (the amount a *voluntary* contributor, who pays
    # both portions themselves, remits). It does not publish an
    # employer/employee split table directly.
    #
    # The employer:employee split is independently confirmed as an exact 2:1
    # ratio (employer 10.8% / employee 5.4% of the 16.2% combined rate) by:
    #   - PwC Worldwide Tax Summaries (T&T, Individual > Other taxes): class
    #     XVI (top band) combined $508.50/wk = "$339.00 by the employer and
    #     $169.50 by the employee" -- exactly 2/3 : 1/3.
    #   - Workzoom NIS glossary/calculator: "employee contributes 5.4 percent
    #     and the employer contributes 10.8 percent" of the 16.2% combined
    #     rate -- also exactly 1/3 : 2/3.
    # Applying employee = combined / 3 to every class below divides evenly to
    # the cent with zero rounding residue for all 16 classes (verified), and
    # reproduces the confirmed class XVI split exactly (169.50 / 339.00) --
    # strong evidence this is the correct per-class derivation, not just a
    # top-class coincidence. Still, only class XVI is independently confirmed
    # against a named published source; classes I-XV are DERIVED. See
    # NOTES.md.
    "nis_combined_rate": 0.162,
    "nis_earnings_classes": [
        {"class_name": "I", "weekly_min": 200, "weekly_max": 339.99, "assumed_avg_weekly": 270.00, "employee_weekly": 14.60, "employer_weekly": 29.20},
        {"class_name": "II", "weekly_min": 340, "weekly_max": 449.99, "assumed_avg_weekly": 395.00, "employee_weekly": 21.30, "employer_weekly": 42.60},
        {"class_name": "III", "weekly_min": 450, "weekly_max": 609.99, "assumed_avg_weekly": 530.00, "employee_weekly": 28.60, "employer_weekly": 57.20},
        {"class_name": "IV", "weekly_min": 610, "weekly_max": 759.99, "assumed_avg_weekly": 685.00, "employee_weekly": 37.00, "employer_weekly": 74.00},
        {"class_name": "V", "weekly_min": 760, "weekly_max": 929.99, "assumed_avg_weekly": 845.00, "employee_weekly": 45.60, "employer_weekly": 91.20},
        {"class_name": "VI", "weekly_min": 930, "weekly_max": 1119.99, "assumed_avg_weekly": 1025.00, "employee_weekly": 55.40, "employer_weekly": 110.80},
        {"class_name": "VII", "weekly_min": 1120, "weekly_max": 1299.99, "assumed_avg_weekly": 1210.00, "employee_weekly": 65.30, "employer_weekly": 130.60},
        {"class_name": "VIII", "weekly_min": 1300, "weekly_max": 1489.99, "assumed_avg_weekly": 1395.00, "employee_weekly": 75.30, "employer_weekly": 150.60},
        {"class_name": "IX", "weekly_min": 1490, "weekly_max": 1709.99, "assumed_avg_weekly": 1600.00, "employee_weekly": 86.40, "employer_weekly": 172.80},
        {"class_name": "X", "weekly_min": 1710, "weekly_max": 1909.99, "assumed_avg_weekly": 1810.00, "employee_weekly": 97.70, "employer_weekly": 195.40},
        {"class_name": "XI", "weekly_min": 1910, "weekly_max": 2139.99, "assumed_avg_weekly": 2025.00, "employee_weekly": 109.40, "employer_weekly": 218.80},
        {"class_name": "XII", "weekly_min": 2140, "weekly_max": 2379.99, "assumed_avg_weekly": 2260.00, "employee_weekly": 122.00, "employer_weekly": 244.00},
        {"class_name": "XIII", "weekly_min": 2380, "weekly_max": 2629.99, "assumed_avg_weekly": 2505.00, "employee_weekly": 135.30, "employer_weekly": 270.60},
        {"class_name": "XIV", "weekly_min": 2630, "weekly_max": 2919.99, "assumed_avg_weekly": 2775.00, "employee_weekly": 149.90, "employer_weekly": 299.80},
        {"class_name": "XV", "weekly_min": 2920, "weekly_max": 3137.99, "assumed_avg_weekly": 3029.00, "employee_weekly": 163.60, "employer_weekly": 327.20},
        {"class_name": "XVI", "weekly_min": 3138, "weekly_max": None, "assumed_avg_weekly": 3138.00, "employee_weekly": 169.50, "employer_weekly": 339.00},
    ],
    # --- Deduction caps ---
    "deduction_caps": {
        "tertiary_education_cap": 72_000.00,
        "pension_annuity_nis_aggregate_cap": 60_000.00,
        "first_time_homeowner_interest_cap": 30_000.00,
        "charitable_donation_pct_of_income": 0.15,
        "animal_shelter_individual_pct": 0.20,
        "animal_shelter_individual_cap": 20_000.00,
        "animal_shelter_company_pct": 0.15,
        "animal_shelter_company_cap": 100_000.00,
    },
    # --- Wear and tear classes ---
    "wear_and_tear_classes": {
        "A": 0.10,
        "B": 0.30,
        "C": 0.333,
        "D": 0.40,
    },
    # --- Filing administration ---
    "individual_filing_deadline": "2027-04-30",
    "corporate_filing_deadline": "2027-04-30",
    "individual_late_penalty_per_6mo": 100.00,
    "corporate_late_penalty_per_6mo": 1000.00,
}

def normalize_nis_classes(raw_classes: list[dict]) -> list[dict]:
    """Defensive copy/whitelist of NIS class rows before DB insertion.

    Keeps only the fields the tax engine (app.services.tax_engine.find_nis_class)
    actually reads, in case seed data ever carries extra scratch fields.
    """
    normalized = []
    for row in raw_classes:
        normalized.append(
            {
                "class_name": row["class_name"],
                "weekly_min": row["weekly_min"],
                "weekly_max": row["weekly_max"],
                "assumed_avg_weekly": row["assumed_avg_weekly"],
                "employee_weekly": row["employee_weekly"],
                "employer_weekly": row["employer_weekly"],
            }
        )
    return normalized
