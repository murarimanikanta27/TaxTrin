"""Unit tests for app.services.tax_engine against known/verified T&T figures.

Where a figure is independently confirmed against a named source (see
app/seed_data.py docstring), the test says so. Where a figure is DERIVED
(the 15 non-XVI NIS classes), the test checks internal consistency
(employee + employer == published combined amount) rather than an
independent third-party figure.
"""
from decimal import Decimal

from app.services.tax_engine import (
    compute_business_and_green_fund_levy,
    compute_corporate_tax,
    compute_deduction_totals,
    compute_health_surcharge,
    compute_nis,
    compute_paye,
    compute_vat,
    compute_wear_and_tear,
    find_nis_class,
    money,
)


class TestNIS:
    def test_class_xvi_matches_pwc_published_split(self, config_2026):
        """PwC: top class combined $508.50/wk = $339.00 employer + $169.50 employee."""
        result = compute_nis(config_2026, weekly_earnings=5000, weeks=1)
        assert result.class_name == "XVI"
        assert money(result.weekly_employee) == 169.50
        assert money(result.weekly_employer) == 339.00
        assert money(result.weekly_total) == 508.50

    def test_class_i_lower_boundary(self, config_2026):
        result = compute_nis(config_2026, weekly_earnings=200, weeks=1)
        assert result.class_name == "I"
        assert money(result.weekly_employee) == 14.60
        assert money(result.weekly_employer) == 29.20

    def test_class_i_upper_boundary(self, config_2026):
        # 339.99 must still resolve to class I, not class II
        result = compute_nis(config_2026, weekly_earnings=Decimal("339.99"), weeks=1)
        assert result.class_name == "I"

    def test_class_boundary_rolls_to_next_class(self, config_2026):
        result = compute_nis(config_2026, weekly_earnings=340, weeks=1)
        assert result.class_name == "II"

    def test_every_class_employee_plus_employer_is_internally_consistent(self, config_2026):
        # Cross-check: employee + employer should reconstruct the combined
        # weekly figure originally published in Legal Notice No. 487/2025 for
        # every one of the 16 classes (not just XVI).
        published_combined = {
            "I": 43.80, "II": 63.90, "III": 85.80, "IV": 111.00, "V": 136.80,
            "VI": 166.20, "VII": 195.90, "VIII": 225.90, "IX": 259.20, "X": 293.10,
            "XI": 328.20, "XII": 366.00, "XIII": 405.90, "XIV": 449.70, "XV": 490.80,
            "XVI": 508.50,
        }
        for row in config_2026.nis_earnings_classes:
            combined = row["employee_weekly"] + row["employer_weekly"]
            assert round(combined, 2) == published_combined[row["class_name"]], row["class_name"]

    def test_annualization_over_52_weeks(self, config_2026):
        result = compute_nis(config_2026, weekly_earnings=5000, weeks=52)
        assert money(result.employee_total) == round(169.50 * 52, 2)
        assert money(result.employer_total) == round(339.00 * 52, 2)

    def test_earnings_below_lowest_class_returns_none(self, config_2026):
        row = find_nis_class(config_2026, Decimal("50"))
        assert row is None
        result = compute_nis(config_2026, weekly_earnings=50, weeks=1)
        assert result.class_name is None
        assert money(result.employee_total) == 0.0


class TestHealthSurcharge:
    def test_high_bracket_matches_bir_published_rate(self, config_2026):
        """ird.gov.tt/health-surcharge: >$469.99/mo => $8.25/wk."""
        result = compute_health_surcharge(config_2026, monthly_emoluments=5000, weeks=1)
        assert money(result.weekly_rate) == 8.25
        assert money(result.employee_total) == 8.25
        assert money(result.employer_total) == 8.25  # employer match

    def test_low_bracket_matches_bir_published_rate(self, config_2026):
        """ird.gov.tt/health-surcharge: <=$469.99/mo => $4.80/wk."""
        result = compute_health_surcharge(config_2026, monthly_emoluments=400, weeks=1)
        assert money(result.weekly_rate) == 4.80

    def test_threshold_boundary_is_inclusive_of_low_rate(self, config_2026):
        result = compute_health_surcharge(config_2026, monthly_emoluments=Decimal("469.99"), weeks=1)
        assert money(result.weekly_rate) == 4.80

    def test_just_above_threshold_is_high_rate(self, config_2026):
        result = compute_health_surcharge(config_2026, monthly_emoluments=Decimal("470.00"), weeks=1)
        assert money(result.weekly_rate) == 8.25

    def test_annualized_52_weeks(self, config_2026):
        result = compute_health_surcharge(config_2026, monthly_emoluments=5000, weeks=52)
        assert money(result.employee_total) == round(8.25 * 52, 2)


class TestPAYE:
    def test_income_below_personal_allowance_is_untaxed(self, config_2026):
        result = compute_paye(config_2026, annual_gross_income=80000, annual_employee_nis=0)
        assert money(result.chargeable_income) == 0.0
        assert money(result.total_tax) == 0.0

    def test_personal_allowance_is_90000(self, config_2026):
        """PwC: 'A personal allowance of TTD 90,000 is available to resident taxpayers.'"""
        assert money(Decimal(str(config_2026.personal_allowance))) == 90000.00

    def test_low_band_rate_is_25_percent(self, config_2026):
        # 90,000 allowance + 40,000 chargeable => tax at 25% = 10,000
        result = compute_paye(config_2026, annual_gross_income=130000, annual_employee_nis=0)
        assert money(result.chargeable_income) == 40000.00
        assert money(result.total_tax) == 10000.00

    def test_high_band_rate_is_30_percent_above_1_million_chargeable(self, config_2026):
        # personal allowance 90,000 + chargeable 1,000,000 (all at 25%) + 100,000 (at 30%)
        gross = 90000 + 1_000_000 + 100_000
        result = compute_paye(config_2026, annual_gross_income=gross, annual_employee_nis=0)
        assert money(result.chargeable_income) == 1_100_000.00
        expected = 1_000_000 * 0.25 + 100_000 * 0.30
        assert money(result.total_tax) == round(expected, 2)
        assert len(result.tax_by_band) == 2
        assert result.tax_by_band[0]["rate"] == 0.25
        assert result.tax_by_band[1]["rate"] == 0.30

    def test_seventy_percent_nis_deduction_reduces_chargeable_income(self, config_2026):
        """Workzoom/PwC: 70% of employee NIS is deductible before PAYE applies."""
        without_nis = compute_paye(config_2026, annual_gross_income=200000, annual_employee_nis=0)
        with_nis = compute_paye(config_2026, annual_gross_income=200000, annual_employee_nis=10000)
        # 70% of 10,000 = 7,000 less chargeable income than the no-NIS case
        assert money(without_nis.chargeable_income) - money(with_nis.chargeable_income) == 7000.00
        assert money(with_nis.nis_deductible_portion) == 7000.00

    def test_other_deductions_reduce_chargeable_income(self, config_2026):
        result = compute_paye(config_2026, annual_gross_income=200000, annual_employee_nis=0, other_deductions=50000)
        assert money(result.chargeable_income) == 200000 - 90000 - 50000

    def test_negative_chargeable_income_floors_at_zero(self, config_2026):
        result = compute_paye(config_2026, annual_gross_income=10000, annual_employee_nis=0, other_deductions=50000)
        assert money(result.chargeable_income) == 0.0
        assert money(result.total_tax) == 0.0


class TestDeductionCaps:
    def test_tertiary_education_capped_at_72000(self, config_2026):
        """ird.gov.tt: tertiary education deduction cap is $72,000 (since 2019)."""
        total, notes = compute_deduction_totals(config_2026, {"tertiary_education": 100000})
        assert total == Decimal("72000")
        assert notes  # a capping note should be recorded

    def test_tertiary_education_under_cap_is_unchanged(self, config_2026):
        total, notes = compute_deduction_totals(config_2026, {"tertiary_education": 30000})
        assert total == Decimal("30000")
        assert notes == []

    def test_pension_annuity_nis_aggregate_capped_at_60000(self, config_2026):
        total, _ = compute_deduction_totals(config_2026, {"pension_annuity_nis_voluntary": 90000})
        assert total == Decimal("60000")

    def test_charitable_donations_capped_at_15_pct_of_income(self, config_2026):
        total, notes = compute_deduction_totals(
            config_2026,
            {"charitable_donations": 50000, "total_income_for_pct_caps": 100000},
        )
        assert total == Decimal("15000")
        assert notes

    def test_animal_shelter_capped_at_lower_of_pct_or_absolute(self, config_2026):
        # 20% of 500,000 = 100,000, but absolute cap is 20,000 -> lower wins
        total, notes = compute_deduction_totals(
            config_2026,
            {"animal_shelter_donations": 50000, "total_income_for_pct_caps": 500000},
        )
        assert total == Decimal("20000")
        assert notes


class TestBusinessAndGreenFundLevy:
    def test_business_levy_rate_is_0_6_pct(self, config_2026):
        assert money(Decimal(str(config_2026.business_levy_rate)) * Decimal("1000000")) == 6000.00

    def test_business_levy_exempt_below_360000_threshold(self, config_2026):
        result = compute_business_and_green_fund_levy(config_2026, gross_receipts=300000, income_tax_liability=0)
        assert result.business_levy_exempt is True
        assert money(result.business_levy_payable) == 0.0

    def test_business_levy_exempt_in_first_3_years(self, config_2026):
        result = compute_business_and_green_fund_levy(
            config_2026, gross_receipts=1_000_000, income_tax_liability=0, years_in_business=1
        )
        assert result.business_levy_exempt is True

    def test_business_levy_payable_only_if_exceeds_income_tax(self, config_2026):
        # gross 1,000,000 * 0.6% = 6,000 levy; income tax already 6,000 -> nothing extra payable
        result = compute_business_and_green_fund_levy(
            config_2026, gross_receipts=1_000_000, income_tax_liability=6000, years_in_business=10
        )
        assert money(result.business_levy_payable) == 0.0

    def test_business_levy_payable_when_it_exceeds_income_tax(self, config_2026):
        result = compute_business_and_green_fund_levy(
            config_2026, gross_receipts=1_000_000, income_tax_liability=1000, years_in_business=10
        )
        assert money(result.business_levy_payable) == 5000.00  # 6,000 levy - 1,000 tax

    def test_green_fund_levy_rate_is_0_3_pct_no_threshold(self, config_2026):
        result = compute_business_and_green_fund_levy(config_2026, gross_receipts=100000, income_tax_liability=0)
        assert money(result.green_fund_levy) == 300.00


class TestCorporateTax:
    def test_standard_rate_is_30_pct(self, config_2026):
        result = compute_corporate_tax(config_2026, chargeable_profits=1_000_000, gross_receipts=5_000_000)
        assert float(result.rate_applied) == 0.30
        assert money(result.corporation_tax) == 300000.00

    def test_bank_petrochemical_rate_is_35_pct(self, config_2026):
        result = compute_corporate_tax(
            config_2026,
            chargeable_profits=1_000_000,
            gross_receipts=5_000_000,
            company_category="bank_or_petrochemical",
        )
        assert float(result.rate_applied) == 0.35
        assert money(result.corporation_tax) == 350000.00

    def test_total_includes_levies(self, config_2026):
        result = compute_corporate_tax(config_2026, chargeable_profits=1_000_000, gross_receipts=5_000_000)
        # green fund levy always applies: 5,000,000 * 0.3% = 15,000
        assert money(result.business_levy.green_fund_levy) == 15000.00
        assert money(result.total_statutory_liability) == money(
            result.corporation_tax + result.business_levy.business_levy_payable + result.business_levy.green_fund_levy
        )


class TestVAT:
    def test_standard_rate_is_12_5_pct(self, config_2026):
        result = compute_vat(config_2026, standard_rated_sales=100000, input_vat_paid=0)
        assert money(result.output_vat) == 12500.00

    def test_net_payable_positive_when_output_exceeds_input(self, config_2026):
        result = compute_vat(config_2026, standard_rated_sales=100000, input_vat_paid=5000)
        assert money(result.net_vat_payable) == 7500.00

    def test_net_payable_negative_indicates_refund(self, config_2026):
        result = compute_vat(config_2026, standard_rated_sales=10000, input_vat_paid=5000)
        assert money(result.net_vat_payable) < 0


class TestWearAndTear:
    def test_class_b_vehicle_rate_is_30_pct(self, config_2026):
        lines = compute_wear_and_tear(
            config_2026,
            [{"description": "Delivery van", "asset_class": "B", "opening_wdv": 100000, "additions": 0}],
        )
        assert money(lines[0].allowance) == 30000.00
        assert money(lines[0].closing_wdv) == 70000.00

    def test_class_a_building_rate_is_10_pct(self, config_2026):
        lines = compute_wear_and_tear(
            config_2026,
            [{"description": "Warehouse", "asset_class": "A", "opening_wdv": 500000, "additions": 0}],
        )
        assert money(lines[0].allowance) == 50000.00

    def test_additions_are_included_in_the_allowance_base(self, config_2026):
        lines = compute_wear_and_tear(
            config_2026,
            [{"description": "New equipment", "asset_class": "C", "opening_wdv": 0, "additions": 90000}],
        )
        # class C = 33.3%
        assert money(lines[0].allowance) == round(90000 * 0.333, 2)
