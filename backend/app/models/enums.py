"""Shared enums used across models, schemas, and services.

Using str-backed Enums keeps values readable in the database (SQLite/Postgres)
and JSON-serializable for the API without a translation layer.
"""
from enum import StrEnum


class UserRole(StrEnum):
    SYSTEM_ADMIN = "system_admin"
    FIRM_ADMIN = "firm_admin"
    FIRM_STAFF = "firm_staff"
    INDIVIDUAL = "individual"
    SOLE_TRADER = "sole_trader"
    CORPORATE = "corporate"


class SubscriptionTier(StrEnum):
    FREE = "free"
    PRO = "pro"
    ENTERPRISE = "enterprise"
    FIRM = "firm"


class ClientType(StrEnum):
    INDIVIDUAL = "individual"
    SOLE_TRADER = "sole_trader"
    PARTNERSHIP = "partnership"
    CORPORATE = "corporate"


class ReturnStatus(StrEnum):
    DRAFT = "draft"
    PENDING_REVIEW = "pending_review"
    APPROVED = "approved"
    EXPORTED = "exported"
    FILED = "filed"


class TD4Type(StrEnum):
    INCOME = "Income"
    PENSION = "Pension"
    SEVERANCE = "Severance"


class TD4Source(StrEnum):
    MANUAL = "manual"
    OCR_UPLOAD = "ocr_upload"
    CSV_IMPORT = "csv_import"


class PayFrequency(StrEnum):
    WEEKLY = "weekly"
    FORTNIGHTLY = "fortnightly"
    MONTHLY = "monthly"


class ScheduleType(StrEnum):
    SCHEDULE_A_CAPITAL_ALLOWANCES = "schedule_a_capital_allowances"
    SCHEDULE_B_EXEMPT_INCOME = "schedule_b_exempt_income"
    WEAR_AND_TEAR = "wear_and_tear"
    VEHICLE_DEPRECIATION = "vehicle_depreciation"


class LinkedReturnType(StrEnum):
    INDIVIDUAL = "individual_return"
    CORPORATE = "corporate_return"


class ETaxExportType(StrEnum):
    TD4_SUPPLEMENTARY_CSV = "td4_supplementary_csv"
    VAT200_UPLOAD_CSV = "vat200_upload_csv"
    NON_LOGGED_IN_RETURN_XML = "non_logged_in_return_xml"
    NON_LOGGED_IN_RETURN_JSON = "non_logged_in_return_json"
    FORM_440_PDF = "form_440_pdf"
    FORM_500_PDF = "form_500_pdf"
    VAT200_PDF = "vat200_pdf"
    PAYMENT_VOUCHER_PDF = "payment_voucher_pdf"
    PAYROLL_SUMMARY_PDF = "payroll_summary_pdf"


class ValidationStatus(StrEnum):
    PENDING = "pending"
    PASSED = "passed"
    FAILED = "failed"
    UNVERIFIED_FORMAT = "unverified_format"
