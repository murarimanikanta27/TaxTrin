"""Tests for the BIR e-Tax file generation engine.

TD4 Supplementary CSV tests check strict conformance to the BIR-verified
schema (field order, no header row, digit padding, comma stripping). The
VAT200 / Non-Logged-In tests only check that the UNVERIFIED_FORMAT status and
warning are always surfaced, since there is no official spec to conform to.
"""
import csv
import io
import json
import xml.etree.ElementTree as ET

from app.models.enums import TD4Type, ValidationStatus
from app.models.td4 import TD4Input
from app.services.etax_export import (
    TD4_SUPPLEMENTARY_FIELD_ORDER,
    generate_non_logged_in_return_json,
    generate_non_logged_in_return_xml,
    generate_td4_supplementary_csv,
    generate_vat200_upload_csv,
    validate_td4_rows,
)


def make_td4(**overrides) -> TD4Input:
    defaults = dict(
        client_id=1,
        income_year=2026,
        td4_type=TD4Type.INCOME,
        employer_bir_number="9999990",  # 7 digits -> must be zero-padded to 10
        employer_paye_number="PYE-123456",
        employer_name="Acme Ltd",
        employee_bir_number="1234567",
        employee_name="John, Smith",  # comma must be stripped
        employee_address="Building 1, 5th Street, Port-of-Spain",  # commas must be stripped
        employee_nis_number="123456789",
        total_deductions=1000,
        weeks_employed=52,
        remuneration=60000,
        commission=0,
        allowance_it76=0,
        travel_allowance=0,
        other_allowance=0,
        previous_income=0,
        savings_plan=0,
        gross_earnings=60000,
        employer_contributions=0,
        travel_dispensation=0,
        employee_contributions=0,
        nis_deducted=2000,
        income_tax=3000,
        total_health_surcharge_weeks=52,
        health_surcharge_weeks_at_high=52,
        health_surcharge_weeks_at_low=0,
        health_surcharge_amount=429.00,
    )
    defaults.update(overrides)
    return TD4Input(**defaults)


class TestTD4SupplementaryCSV:
    def test_field_order_has_27_fields(self):
        assert len(TD4_SUPPLEMENTARY_FIELD_ORDER) == 27

    def test_no_header_row_is_written(self):
        result = generate_td4_supplementary_csv([make_td4()], income_year=2026)
        text = result.content_bytes.decode("utf-8")
        first_field = text.split(",")[0]
        # first field is income_year (a 4-digit number), not a header word
        assert first_field.strip() == "2026"

    def test_bir_numbers_are_zero_padded_to_10_digits(self):
        result = generate_td4_supplementary_csv([make_td4()], income_year=2026)
        reader = csv.reader(io.StringIO(result.content_bytes.decode("utf-8")))
        row = next(reader)
        row_dict = dict(zip(TD4_SUPPLEMENTARY_FIELD_ORDER, row))
        assert row_dict["employer_bir_number"] == "0009999990"
        assert row_dict["employee_bir_number"] == "0001234567"
        assert len(row_dict["employer_bir_number"]) == 10
        assert len(row_dict["employee_bir_number"]) == 10

    def test_commas_are_stripped_from_text_fields(self):
        result = generate_td4_supplementary_csv([make_td4()], income_year=2026)
        reader = csv.reader(io.StringIO(result.content_bytes.decode("utf-8")))
        row = next(reader)
        row_dict = dict(zip(TD4_SUPPLEMENTARY_FIELD_ORDER, row))
        assert "," not in row_dict["employee_name"]
        assert "," not in row_dict["employee_address"]
        assert row_dict["employee_name"] == "John  Smith"

    def test_amounts_have_exactly_two_decimal_places_no_symbols(self):
        result = generate_td4_supplementary_csv([make_td4(gross_earnings=60000)], income_year=2026)
        reader = csv.reader(io.StringIO(result.content_bytes.decode("utf-8")))
        row = next(reader)
        row_dict = dict(zip(TD4_SUPPLEMENTARY_FIELD_ORDER, row))
        assert row_dict["gross_earnings"] == "60000.00"
        assert "$" not in row_dict["gross_earnings"]

    def test_td4_type_is_one_of_three_values(self):
        for td4_type in (TD4Type.INCOME, TD4Type.PENSION, TD4Type.SEVERANCE):
            result = generate_td4_supplementary_csv([make_td4(td4_type=td4_type)], income_year=2026)
            reader = csv.reader(io.StringIO(result.content_bytes.decode("utf-8")))
            row = next(reader)
            row_dict = dict(zip(TD4_SUPPLEMENTARY_FIELD_ORDER, row))
            assert row_dict["td4_type"] == td4_type.value

    def test_multiple_records_produce_multiple_rows(self):
        td4s = [make_td4(employee_name=f"Employee {i}") for i in range(5)]
        result = generate_td4_supplementary_csv(td4s, income_year=2026)
        assert result.row_count == 5
        rows = list(csv.reader(io.StringIO(result.content_bytes.decode("utf-8"))))
        assert len(rows) == 5

    def test_valid_batch_is_marked_passed(self):
        result = generate_td4_supplementary_csv([make_td4()], income_year=2026)
        assert result.validation_status == ValidationStatus.PASSED

    def test_empty_batch_is_marked_failed(self):
        result = generate_td4_supplementary_csv([], income_year=2026)
        assert result.validation_status == ValidationStatus.FAILED

    def test_repeated_digit_bir_number_is_flagged_invalid(self):
        problems = validate_td4_rows([make_td4(employee_bir_number="0000000000")])
        assert any("looks invalid" in p for p in problems)

    def test_income_type_with_zero_weeks_is_flagged(self):
        problems = validate_td4_rows([make_td4(td4_type=TD4Type.INCOME, weeks_employed=0)])
        assert any("Weeks Employed must be > 0" in p for p in problems)

    def test_missing_employee_name_is_flagged(self):
        problems = validate_td4_rows([make_td4(employee_name="")])
        assert any("Employee Name is required" in p for p in problems)


class TestVAT200UploadUnverified:
    def test_always_flagged_unverified_format(self):
        result = generate_vat200_upload_csv(
            "1234567",
            "VAT-001",
            {
                "period_start": "2026-01-01",
                "period_end": "2026-02-28",
                "standard_rated_sales": 100000,
                "zero_rated_sales": 0,
                "exempt_sales": 0,
                "output_vat": 12500,
                "input_vat": 5000,
                "net_vat_payable": 7500,
            },
        )
        assert result.validation_status == ValidationStatus.UNVERIFIED_FORMAT
        assert any("UNVERIFIED FORMAT" in m for m in result.validation_messages)

    def test_amounts_render_with_two_decimals(self):
        result = generate_vat200_upload_csv(
            "1234567",
            "VAT-001",
            {"period_start": "2026-01-01", "period_end": "2026-02-28", "output_vat": 12500, "net_vat_payable": 7500},
        )
        text = result.content_bytes.decode("utf-8")
        assert "12500.00" in text
        assert "7500.00" in text


class TestNonLoggedInReturnUnverified:
    def test_json_export_is_flagged_unverified_and_well_formed(self):
        result = generate_non_logged_in_return_json(
            "individual_return",
            2026,
            {"bir_number": "1234567", "tin": "", "display_name": "Jane Doe", "address": "1 Main St"},
            {"total_tax_liability": 5000},
        )
        assert result.validation_status == ValidationStatus.UNVERIFIED_FORMAT
        parsed = json.loads(result.content_bytes.decode("utf-8"))
        assert parsed["schema"]["version"] == "0.1-unverified"
        assert parsed["taxpayer"]["bir_number"] == "0001234567"

    def test_xml_export_is_flagged_unverified_and_well_formed(self):
        result = generate_non_logged_in_return_xml(
            "individual_return",
            2026,
            {"bir_number": "1234567", "tin": "", "display_name": "Jane Doe", "address": "1 Main St"},
            {"total_tax_liability": 5000},
        )
        assert result.validation_status == ValidationStatus.UNVERIFIED_FORMAT
        # must be parseable, well-formed XML
        root = ET.fromstring(result.content_bytes.decode("utf-8"))
        assert root.tag == "NonLoggedInReturn"
