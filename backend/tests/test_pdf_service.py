"""Smoke tests for PDF generation: every generator must produce a well-formed,
non-trivial PDF (starts with the %PDF magic bytes, ends with %%EOF, has a
reasonable minimum size) without raising, across representative computed
payloads (including refund vs balance-due branches).
"""
import pytest

from app.services.pdf_service import (
    generate_form_440_pdf,
    generate_form_500_pdf,
    generate_payment_voucher_pdf,
    generate_payroll_summary_pdf,
    generate_vat200_pdf,
)


def assert_is_valid_pdf(content: bytes, min_size: int = 1000):
    assert content.startswith(b"%PDF-")
    assert content.rstrip().endswith(b"%%EOF")
    assert len(content) > min_size


CLIENT = {"display_name": "Jane Doe", "bir_number": "1234567"}

INDIVIDUAL_COMPUTED_BALANCE_DUE = {
    "total_income": 200000,
    "deduction_notes": ["Tertiary education expenses capped at $72000"],
    "paye": {
        "personal_allowance": 90000,
        "nis_deductible_portion": 3000,
        "other_deductions": 5000,
        "chargeable_income": 102000,
        "tax_by_band": [
            {"from": 0, "to": 1000000, "rate": 0.25, "taxable_amount": 102000, "tax": 25500},
        ],
        "total_tax": 25500,
    },
    "levies": {"business_levy_gross": 0, "business_levy_payable": 0, "business_levy_exempt": True, "green_fund_levy": 0},
    "paye_already_deducted": 20000,
    "total_tax_liability": 25500,
    "refund_or_balance_due": 5500,
    "is_refund": False,
}

INDIVIDUAL_COMPUTED_REFUND = {
    **INDIVIDUAL_COMPUTED_BALANCE_DUE,
    "paye_already_deducted": 30000,
    "refund_or_balance_due": -4500,
    "is_refund": True,
}

CORPORATE_COMPUTED = {
    "chargeable_profits": 1000000,
    "rate_applied": 0.30,
    "corporation_tax": 300000,
    "business_levy": {
        "business_levy_gross": 30000,
        "business_levy_payable": 0,
        "business_levy_exempt": False,
        "green_fund_levy": 15000,
    },
    "dividend_paid": 100000,
    "dividend_withholding_tax_rate": 0.10,
    "dividend_withholding_tax": 10000,
    "total_statutory_liability": 315000,
    "quarterly_installments_paid": 200000,
    "refund_or_balance_due": 115000,
    "is_refund": False,
}

VAT_COMPUTED = {
    "standard_rated_sales": 100000,
    "zero_rated_sales": 5000,
    "exempt_sales": 2000,
    "output_vat": 12500,
    "input_vat": 5000,
    "net_vat_payable": 7500,
    "is_refund": False,
}


class TestForm440PDF:
    def test_generates_valid_pdf_for_balance_due(self):
        content = generate_form_440_pdf(CLIENT, 2026, INDIVIDUAL_COMPUTED_BALANCE_DUE)
        assert_is_valid_pdf(content)

    def test_generates_valid_pdf_for_refund_case(self):
        content = generate_form_440_pdf(CLIENT, 2026, INDIVIDUAL_COMPUTED_REFUND)
        assert_is_valid_pdf(content)

    def test_handles_multiple_tax_bands(self):
        computed = dict(INDIVIDUAL_COMPUTED_BALANCE_DUE)
        computed["paye"] = dict(computed["paye"])
        computed["paye"]["tax_by_band"] = [
            {"from": 0, "to": 1000000, "rate": 0.25, "taxable_amount": 1000000, "tax": 250000},
            {"from": 1000000, "to": None, "rate": 0.30, "taxable_amount": 50000, "tax": 15000},
        ]
        content = generate_form_440_pdf(CLIENT, 2026, computed)
        assert_is_valid_pdf(content)

    def test_handles_no_deduction_notes(self):
        computed = dict(INDIVIDUAL_COMPUTED_BALANCE_DUE)
        computed["deduction_notes"] = []
        content = generate_form_440_pdf(CLIENT, 2026, computed)
        assert_is_valid_pdf(content)


class TestForm500PDF:
    def test_generates_valid_pdf(self):
        content = generate_form_500_pdf(CLIENT, 2026, CORPORATE_COMPUTED)
        assert_is_valid_pdf(content)

    def test_generates_valid_pdf_for_refund_case(self):
        computed = {**CORPORATE_COMPUTED, "is_refund": True, "refund_or_balance_due": -50000}
        content = generate_form_500_pdf(CLIENT, 2026, computed)
        assert_is_valid_pdf(content)


class TestVAT200PDF:
    def test_generates_valid_pdf(self):
        content = generate_vat200_pdf(CLIENT, "2026-01-01", "2026-02-28", VAT_COMPUTED)
        assert_is_valid_pdf(content)

    def test_generates_valid_pdf_for_refund_case(self):
        computed = {**VAT_COMPUTED, "is_refund": True, "net_vat_payable": -2500}
        content = generate_vat200_pdf(CLIENT, "2026-01-01", "2026-02-28", computed)
        assert_is_valid_pdf(content)


class TestPaymentVoucherPDF:
    def test_generates_valid_pdf(self):
        voucher = {
            "payment_type": "Quarterly Estimated Tax Payment",
            "quarter_label": "Q1 2026",
            "tax_year": 2026,
            "due_date": "2026-03-31",
            "amount": 15000,
            "bir_account_reference": "0001234567-2026-Q1",
        }
        content = generate_payment_voucher_pdf(CLIENT, voucher)
        assert_is_valid_pdf(content, min_size=800)


class TestPayrollSummaryPDF:
    def test_generates_valid_pdf_with_multiple_employees(self):
        lines = [
            {
                "employee_name": "Alice",
                "gross_pay": 8000,
                "nis_employee": 169.50,
                "nis_employer": 339.00,
                "health_surcharge_employee": 8.25,
                "health_surcharge_employer": 8.25,
                "paye_deducted": 500,
                "net_pay": 7322.25,
            },
            {
                "employee_name": "Bob",
                "gross_pay": 4000,
                "nis_employee": 75.30,
                "nis_employer": 150.60,
                "health_surcharge_employee": 8.25,
                "health_surcharge_employer": 8.25,
                "paye_deducted": 0,
                "net_pay": 3916.45,
            },
        ]
        content = generate_payroll_summary_pdf({"display_name": "Acme Ltd"}, "January 2026", lines)
        assert_is_valid_pdf(content)

    def test_generates_valid_pdf_with_zero_employees(self):
        content = generate_payroll_summary_pdf({"display_name": "Acme Ltd"}, "January 2026", [])
        assert_is_valid_pdf(content, min_size=500)
