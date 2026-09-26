"""Composes the low-level tax_engine primitives into full return calculations.

This is the layer the API routers call: given a TaxYearConfig and a bag of
taxpayer inputs, produce the complete computed breakdown that gets stored on
IndividualReturn.computed / CorporateReturn.computed / VAT200Return.computed
and displayed in the wizard's "live refund/balance indicator".
"""
from decimal import Decimal

from app.models.tax_config import TaxYearConfig
from app.services.tax_engine import (
    CorporateTaxResult,
    LeviesResult,
    PAYEResult,
    VATResult,
    compute_business_and_green_fund_levy,
    compute_corporate_tax,
    compute_deduction_totals,
    compute_paye,
    compute_vat,
    d,
    money,
)


def _paye_result_to_dict(paye: PAYEResult) -> dict:
    return {
        "gross_income": money(paye.gross_income),
        "personal_allowance": money(paye.personal_allowance),
        "nis_deductible_portion": money(paye.nis_deductible_portion),
        "other_deductions": money(paye.other_deductions),
        "chargeable_income": money(paye.chargeable_income),
        "tax_by_band": paye.tax_by_band,
        "total_tax": money(paye.total_tax),
    }


def _levies_result_to_dict(levies: LeviesResult) -> dict:
    return {
        "business_levy_gross": money(levies.business_levy_gross),
        "business_levy_payable": money(levies.business_levy_payable),
        "business_levy_exempt": levies.business_levy_exempt,
        "green_fund_levy": money(levies.green_fund_levy),
    }


def compute_individual_return(config: TaxYearConfig, inputs: dict) -> dict:
    """Full Form 440 / Form 400 ITR style computation.

    Expected `inputs` keys (all optional, default 0 unless noted):
      emolument_income: sum of TD4 gross earnings for the year
      employee_nis_paid: sum of NIS deducted per TD4(s)
      paye_already_deducted: sum of PAYE already withheld per TD4(s)
      self_employed_income: net profit from sole trader activity, if any
      gross_receipts: gross receipts/income for Business Levy & Green Fund Levy
        (defaults to emolument_income + self_employed_income if omitted)
      years_in_business: int, for the Business Levy new-business exemption
      deductions: dict passed straight to compute_deduction_totals, plus
        `total_income_for_pct_caps` used for the percentage-of-income caps
    """
    emolument_income = d(inputs.get("emolument_income"))
    self_employed_income = d(inputs.get("self_employed_income"))
    total_income = emolument_income + self_employed_income

    deductions = dict(inputs.get("deductions") or {})
    deductions.setdefault("total_income_for_pct_caps", float(total_income))
    other_deductions, deduction_notes = compute_deduction_totals(config, deductions)

    paye = compute_paye(
        config,
        annual_gross_income=total_income,
        annual_employee_nis=inputs.get("employee_nis_paid"),
        other_deductions=other_deductions,
    )

    gross_receipts = inputs.get("gross_receipts")
    if gross_receipts is None:
        gross_receipts = total_income
    levies = compute_business_and_green_fund_levy(
        config,
        gross_receipts=gross_receipts,
        income_tax_liability=paye.total_tax,
        years_in_business=inputs.get("years_in_business"),
    )

    paye_already_deducted = d(inputs.get("paye_already_deducted"))
    total_liability = paye.total_tax + levies.business_levy_payable
    balance = total_liability - paye_already_deducted  # positive = owe BIR, negative = refund

    return {
        "total_income": money(total_income),
        "deduction_notes": deduction_notes,
        "paye": _paye_result_to_dict(paye),
        "levies": _levies_result_to_dict(levies),
        "paye_already_deducted": money(paye_already_deducted),
        "total_tax_liability": money(total_liability),
        "refund_or_balance_due": money(balance),
        "is_refund": balance < 0,
    }


def _corporate_result_to_dict(result: CorporateTaxResult) -> dict:
    return {
        "chargeable_profits": money(result.chargeable_profits),
        "rate_applied": float(result.rate_applied),
        "corporation_tax": money(result.corporation_tax),
        "business_levy": _levies_result_to_dict(result.business_levy),
        "total_statutory_liability": money(result.total_statutory_liability),
    }


def compute_corporate_return(config: TaxYearConfig, inputs: dict) -> dict:
    """Full Form 500 style computation.

    Expected `inputs` keys:
      chargeable_profits, gross_receipts, company_category
      ("standard" | "bank_or_petrochemical" | "sme_stock_exchange"),
      quarterly_installments_paid (sum already remitted this year),
      dividend_paid, dividend_wht_rate (for withholding tax on dividends,
        default 0.10 non-treaty portfolio rate per PwC summary)
    """
    result = compute_corporate_tax(
        config,
        chargeable_profits=inputs.get("chargeable_profits"),
        gross_receipts=inputs.get("gross_receipts"),
        company_category=inputs.get("company_category", "standard"),
    )

    dividend_paid = d(inputs.get("dividend_paid"))
    dividend_wht_rate = d(inputs.get("dividend_wht_rate", "0.10"))
    dividend_wht = dividend_paid * dividend_wht_rate

    installments_paid = d(inputs.get("quarterly_installments_paid"))
    balance = result.total_statutory_liability - installments_paid

    payload = _corporate_result_to_dict(result)
    payload.update(
        {
            "dividend_paid": money(dividend_paid),
            "dividend_withholding_tax_rate": float(dividend_wht_rate),
            "dividend_withholding_tax": money(dividend_wht),
            "quarterly_installments_paid": money(installments_paid),
            "refund_or_balance_due": money(balance),
            "is_refund": balance < 0,
        }
    )
    return payload


def compute_vat200_return(config: TaxYearConfig, inputs: dict) -> dict:
    """Full VAT 200 bimonthly computation.

    Expected `inputs` keys: standard_rated_sales, zero_rated_sales,
    exempt_sales, input_vat_paid, output_vat_override (optional).
    """
    vat: VATResult = compute_vat(
        config,
        standard_rated_sales=inputs.get("standard_rated_sales"),
        input_vat_paid=inputs.get("input_vat_paid"),
        output_vat_override=inputs.get("output_vat_override"),
    )
    return {
        "standard_rated_sales": money(d(inputs.get("standard_rated_sales"))),
        "zero_rated_sales": money(d(inputs.get("zero_rated_sales"))),
        "exempt_sales": money(d(inputs.get("exempt_sales"))),
        "output_vat": money(vat.output_vat),
        "input_vat": money(vat.input_vat),
        "net_vat_payable": money(vat.net_vat_payable),
        "is_refund": vat.net_vat_payable < 0,
    }
