"""BIR e-Tax file generation engine.

Produces the file formats a taxpayer/employer/firm downloads from the
"e-Tax File Export Center" and then uploads by hand into etax.ird.gov.tt.

CONFIDENCE LEVELS (see NOTES.md for full detail):
  - TD4_SUPPLEMENTARY: format is BIR-VERIFIED. The field order, required-ness,
    and formatting rules below are transcribed directly from the official
    guide at https://ird.gov.tt/PAYE/AnnualReturn/Guide/file/supplemental
    (fetched during this build). This is the one export in the system safe
    to describe as matching the real BIR upload format.
  - VAT200_UPLOAD: UNVERIFIED FORMAT. No public BIR VAT200 e-Tax upload file
    layout was found. The columns below are a reasonable reconstruction from
    the VAT200 return's own line items (standard/zero-rated/exempt sales,
    output/input VAT, net payable) but have NOT been checked against a real
    BIR-accepted file. Treat as a structural placeholder pending a sample
    file or spec from IRD.
  - NON_LOGGED_IN_RETURN (XML/JSON): UNVERIFIED FORMAT. No public schema for
    e-Tax's "Prepare Return Offline" / "Non-Logged In Return" submission was
    found. The XML/JSON below is an original, clearly-labelled best-effort
    schema (tags named after the return's own fields) so the export center
    UI and downstream integration code have something concrete to build
    against, NOT a claim that etax.ird.gov.tt will accept this file as-is.

Every export this module produces also goes through `_write_export_log`,
which sets `validation_status` to PASSED only for TD4_SUPPLEMENTARY (the one
verified format) and UNVERIFIED_FORMAT for everything else, and stamps a
`validation_messages` note explaining why -- so the confidence level is
visible in the API/UI, not just in this docstring.
"""
import csv
import hashlib
import io
import json
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from xml.dom import minidom

from app.config import get_settings
from app.models.enums import ETaxExportType, ValidationStatus
from app.models.td4 import TD4Input

settings = get_settings()


# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


@dataclass
class GeneratedFile:
    file_name: str
    content_bytes: bytes
    row_count: int | None
    validation_status: ValidationStatus
    validation_messages: list[str]


def _digits_only(value: str | None, length: int) -> str:
    """Zero-pad a numeric identifier to `length` digits, per BIR spec
    ("Leading zeros must be included e.g. 0009999990")."""
    if not value:
        return "0" * length
    digits = re.sub(r"\D", "", str(value))
    return digits.zfill(length)[-length:] if digits else "0" * length


def _clean_text_field(value: str | None) -> str:
    """Strip commas (BIR CSV forbids them; no quoting is used) and collapse
    newlines, per the "No commas allowed within any field" / "Do not select
    enter or insert a carriage return" rules."""
    if not value:
        return ""
    return str(value).replace(",", " ").replace("\r", " ").replace("\n", " ").strip()


def _amount(value) -> str:
    """Format a monetary amount to the nearest cent, no currency symbol or
    thousands separator, per the BIR spec."""
    try:
        return f"{float(value or 0):.2f}"
    except (TypeError, ValueError):
        return "0.00"


def content_hash(content_bytes: bytes) -> str:
    return hashlib.sha256(content_bytes).hexdigest()


def save_export_file(client_id: int, generated: GeneratedFile) -> Path:
    """Persist a generated export's bytes to storage/exports/{client_id}/."""
    export_dir = Path(settings.storage_dir) / "exports" / str(client_id)
    export_dir.mkdir(parents=True, exist_ok=True)
    path = export_dir / generated.file_name
    path.write_bytes(generated.content_bytes)
    return path


# ---------------------------------------------------------------------------
# A. TD4 Supplementary CSV (BIR-verified format)
# ---------------------------------------------------------------------------

# Exact order transcribed from ird.gov.tt/PAYE/AnnualReturn/Guide/file/supplemental.
# "The file should not contain a header row." -- so this list is documentation
# for developers, not something written into the output file itself.
TD4_SUPPLEMENTARY_FIELD_ORDER = [
    "income_year",                       # 1  Required, 4 digits
    "employer_bir_number",                # 2  Required, 10 digits
    "employer_paye_number",               # 3  Required, 12 chars, starts "PYE-"
    "employee_bir_number",                # 4  Required, 10 digits
    "employee_name",                      # 5  Required, text
    "employee_address",                   # 6  Required, text
    "employee_nis_number",                # 7  9 digits
    "total_deductions",                   # 8  amount
    "weeks_employed",                     # 9  0-52, >0 if TD4 type is Income
    "remuneration",                       # 10 amount
    "commission",                         # 11 amount
    "allowance_it76",                     # 12 amount
    "travel_allowance",                   # 13 amount
    "other_allowance",                    # 14 amount
    "previous_income",                    # 15 amount
    "savings_plan",                       # 16 amount
    "gross_earnings",                     # 17 Required, amount
    "employer_contributions",             # 18 amount
    "travel_dispensation",                # 19 amount
    "employee_contributions",             # 20 amount
    "nis_deducted",                       # 21 amount
    "income_tax",                         # 22 amount
    "total_health_surcharge_weeks",       # 23 0-52
    "health_surcharge_weeks_at_high",     # 24 0-52 (@ $8.25)
    "health_surcharge_weeks_at_low",      # 25 0-52 (@ $4.80)
    "health_surcharge_amount",            # 26 amount
    "td4_type",                           # 27 Required: Income | Pension | Severance
]

TD4_REQUIRED_FIELDS = {
    "income_year",
    "employer_bir_number",
    "employer_paye_number",
    "employee_bir_number",
    "employee_name",
    "employee_address",
    "gross_earnings",
    "td4_type",
}


def _td4_to_row(td4: TD4Input) -> list[str]:
    row_map = {
        "income_year": str(td4.income_year),
        "employer_bir_number": _digits_only(td4.employer_bir_number, 10),
        "employer_paye_number": (td4.employer_paye_number or "PYE-").strip()[:12],
        "employee_bir_number": _digits_only(td4.employee_bir_number, 10),
        "employee_name": _clean_text_field(td4.employee_name),
        "employee_address": _clean_text_field(td4.employee_address),
        "employee_nis_number": _digits_only(td4.employee_nis_number, 9) if td4.employee_nis_number else "",
        "total_deductions": _amount(td4.total_deductions),
        "weeks_employed": str(int(td4.weeks_employed or 0)),
        "remuneration": _amount(td4.remuneration),
        "commission": _amount(td4.commission),
        "allowance_it76": _amount(td4.allowance_it76),
        "travel_allowance": _amount(td4.travel_allowance),
        "other_allowance": _amount(td4.other_allowance),
        "previous_income": _amount(td4.previous_income),
        "savings_plan": _amount(td4.savings_plan),
        "gross_earnings": _amount(td4.gross_earnings),
        "employer_contributions": _amount(td4.employer_contributions),
        "travel_dispensation": _amount(td4.travel_dispensation),
        "employee_contributions": _amount(td4.employee_contributions),
        "nis_deducted": _amount(td4.nis_deducted),
        "income_tax": _amount(td4.income_tax),
        "total_health_surcharge_weeks": str(int(td4.total_health_surcharge_weeks or 0)),
        "health_surcharge_weeks_at_high": str(int(td4.health_surcharge_weeks_at_high or 0)),
        "health_surcharge_weeks_at_low": str(int(td4.health_surcharge_weeks_at_low or 0)),
        "health_surcharge_amount": _amount(td4.health_surcharge_amount),
        "td4_type": td4.td4_type.value if hasattr(td4.td4_type, "value") else str(td4.td4_type),
    }
    return [row_map[field] for field in TD4_SUPPLEMENTARY_FIELD_ORDER]


def validate_td4_rows(td4_inputs: list[TD4Input]) -> list[str]:
    """Pre-flight validation mirroring the BIR "Document Guidelines" section.
    Returns a list of human-readable problems (empty list == clean)."""
    messages: list[str] = []
    if not td4_inputs:
        messages.append("No TD4 records supplied.")
        return messages

    for idx, td4 in enumerate(td4_inputs, start=1):
        bir = _digits_only(td4.employee_bir_number, 10)
        if bir == "0000000000" or len(set(bir)) == 1:
            messages.append(f"Row {idx}: Employee BIR number '{bir}' looks invalid (all repeated digits).")
        if not td4.employee_name:
            messages.append(f"Row {idx}: Employee Name is required.")
        if not td4.employee_address:
            messages.append(f"Row {idx}: Employee Address is required.")
        if td4.td4_type is None:
            messages.append(f"Row {idx}: TD4 Type is required (Income, Pension, or Severance).")
        weeks = int(td4.weeks_employed or 0)
        if td4.td4_type and str(td4.td4_type).endswith("Income") and weeks <= 0:
            messages.append(f"Row {idx}: Weeks Employed must be > 0 when TD4 Type is 'Income'.")
        if not (0 <= weeks <= 52):
            messages.append(f"Row {idx}: Weeks Employed must be between 0 and 52.")
    return messages


def generate_td4_supplementary_csv(td4_inputs: list[TD4Input], income_year: int) -> GeneratedFile:
    """Build the exact TD4 Supplementary CSV file for upload to e-Tax.

    Per BIR spec: no header row, no quoted fields, comma is a hard field
    delimiter (already stripped from every value in `_clean_text_field`).
    """
    problems = validate_td4_rows(td4_inputs)

    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\r\n")
    for td4 in td4_inputs:
        writer.writerow(_td4_to_row(td4))
    content = buffer.getvalue().encode("utf-8")

    status = ValidationStatus.FAILED if problems else ValidationStatus.PASSED
    if not problems:
        problems = [
            "Format verified against ird.gov.tt/PAYE/AnnualReturn/Guide/file/supplemental "
            "(27-field order, no header row, digit-padding rules)."
        ]

    return GeneratedFile(
        file_name=f"TD4_Supplementary_{income_year}.csv",
        content_bytes=content,
        row_count=len(td4_inputs),
        validation_status=status,
        validation_messages=problems,
    )


# ---------------------------------------------------------------------------
# B. VAT 200 upload file (UNVERIFIED FORMAT - best-effort reconstruction)
# ---------------------------------------------------------------------------

VAT200_UPLOAD_FIELD_ORDER = [
    "bir_number",
    "vat_registration_number",
    "period_start",
    "period_end",
    "standard_rated_sales",
    "zero_rated_sales",
    "exempt_sales",
    "output_vat",
    "input_vat",
    "net_vat_payable",
]


def generate_vat200_upload_csv(client_bir_number: str, vat_registration_number: str, vat_return: dict) -> GeneratedFile:
    """Best-effort VAT200 upload CSV.

    UNVERIFIED FORMAT: no public BIR VAT200 e-Tax upload layout exists. This
    reconstructs a plausible column set from the VAT200 return's own fields,
    following the same "no header row, no thousands separators, 2dp amounts"
    conventions confirmed for the TD4 file (the one format IRD *has*
    published), on the theory that e-Tax's other bulk-upload formats are
    likely to share those conventions -- but that is an inference, not a
    confirmed BIR rule for this specific file.
    """
    row = [
        _digits_only(client_bir_number, 10),
        _clean_text_field(vat_registration_number),
        vat_return.get("period_start", ""),
        vat_return.get("period_end", ""),
        _amount(vat_return.get("standard_rated_sales")),
        _amount(vat_return.get("zero_rated_sales")),
        _amount(vat_return.get("exempt_sales")),
        _amount(vat_return.get("output_vat")),
        _amount(vat_return.get("input_vat")),
        _amount(vat_return.get("net_vat_payable")),
    ]
    buffer = io.StringIO()
    writer = csv.writer(buffer, lineterminator="\r\n")
    writer.writerow(row)
    content = buffer.getvalue().encode("utf-8")

    return GeneratedFile(
        file_name=f"VAT200_Upload_{vat_return.get('period_start', 'period')}.csv",
        content_bytes=content,
        row_count=1,
        validation_status=ValidationStatus.UNVERIFIED_FORMAT,
        validation_messages=[
            "UNVERIFIED FORMAT: no public BIR VAT200 e-Tax bulk-upload schema was found. "
            "This file is a structural placeholder (column order inferred from the VAT200 "
            "return's own fields) and has not been validated against a real IRD-accepted file. "
            "Confirm the exact required layout with IRD / a sample file before relying on this "
            "for a live filing."
        ],
    )


# ---------------------------------------------------------------------------
# C. Non-Logged-In Return payload (XML / JSON) - UNVERIFIED FORMAT
# ---------------------------------------------------------------------------


def _prettify_xml(root: ET.Element) -> bytes:
    rough = ET.tostring(root, encoding="utf-8")
    return minidom.parseString(rough).toprettyxml(indent="  ", encoding="utf-8")


def _build_return_payload_dict(
    return_type: str,
    tax_year: int,
    client: dict,
    computed: dict,
) -> dict:
    return {
        "schema": {
            "name": "TaxTrinNonLoggedInReturn",
            "version": "0.1-unverified",
            "note": (
                "UNVERIFIED FORMAT: no public etax.ird.gov.tt schema for Non-Logged-In / "
                "Prepare-Return-Offline submissions was located. Field names below mirror "
                "TaxTrin's own return model, not a confirmed BIR tag set."
            ),
        },
        "return_type": return_type,
        "tax_year": tax_year,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "taxpayer": {
            "bir_number": _digits_only(client.get("bir_number"), 10),
            "tin": client.get("tin") or "",
            "name": _clean_text_field(client.get("display_name")),
            "address": _clean_text_field(client.get("address")),
        },
        "computed": computed,
    }


def generate_non_logged_in_return_json(return_type: str, tax_year: int, client: dict, computed: dict) -> GeneratedFile:
    payload = _build_return_payload_dict(return_type, tax_year, client, computed)
    content = json.dumps(payload, indent=2).encode("utf-8")
    return GeneratedFile(
        file_name=f"NonLoggedInReturn_{return_type}_{tax_year}.json",
        content_bytes=content,
        row_count=1,
        validation_status=ValidationStatus.UNVERIFIED_FORMAT,
        validation_messages=[
            "UNVERIFIED FORMAT: no public schema for e-Tax Non-Logged-In / offline return "
            "submissions was found. This JSON is an original best-effort structure for "
            "downstream integration/testing, not a confirmed BIR-accepted payload."
        ],
    )


def _dict_to_xml(parent: ET.Element, data) -> None:
    if isinstance(data, dict):
        for key, value in data.items():
            tag = re.sub(r"[^a-zA-Z0-9_]", "_", str(key)) or "field"
            child = ET.SubElement(parent, tag)
            _dict_to_xml(child, value)
    elif isinstance(data, list):
        for item in data:
            child = ET.SubElement(parent, "item")
            _dict_to_xml(child, item)
    else:
        parent.text = "" if data is None else str(data)


def generate_non_logged_in_return_xml(return_type: str, tax_year: int, client: dict, computed: dict) -> GeneratedFile:
    payload = _build_return_payload_dict(return_type, tax_year, client, computed)
    root = ET.Element("NonLoggedInReturn")
    _dict_to_xml(root, payload)
    content = _prettify_xml(root)
    return GeneratedFile(
        file_name=f"NonLoggedInReturn_{return_type}_{tax_year}.xml",
        content_bytes=content,
        row_count=1,
        validation_status=ValidationStatus.UNVERIFIED_FORMAT,
        validation_messages=[
            "UNVERIFIED FORMAT: no public XML schema for e-Tax Non-Logged-In / offline return "
            "submissions was found. This XML is an original best-effort structure for "
            "downstream integration/testing, not a confirmed BIR-accepted payload."
        ],
    )
