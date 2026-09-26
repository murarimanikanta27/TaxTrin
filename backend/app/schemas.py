"""Pydantic request/response schemas.

Kept in one module for a POC of this size; a larger app would split this per
router/domain (schemas/user.py, schemas/td4.py, etc).
"""
from typing import Any, Optional

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from app.models.enums import (
    ClientType,
    ETaxExportType,
    PayFrequency,
    ReturnStatus,
    SubscriptionTier,
    TD4Source,
    TD4Type,
    UserRole,
    ValidationStatus,
)


# --- Auth ---


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8)
    full_name: str
    role: UserRole = UserRole.INDIVIDUAL
    firm_name: Optional[str] = None  # if role is firm_admin, creates a new Firm


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: "UserOut"


class UserOut(BaseModel):
    id: int
    email: str
    full_name: str
    role: UserRole
    subscription_tier: SubscriptionTier
    firm_id: Optional[int] = None

    model_config = ConfigDict(from_attributes=True)


# --- Firm / Client ---


class FirmOut(BaseModel):
    id: int
    name: str
    bir_number: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class ClientCreate(BaseModel):
    client_type: ClientType
    display_name: str
    bir_number: Optional[str] = None
    tin: Optional[str] = None
    nis_number: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    assigned_staff_user_id: Optional[int] = None


class ClientUpdate(BaseModel):
    display_name: Optional[str] = None
    bir_number: Optional[str] = None
    tin: Optional[str] = None
    nis_number: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    assigned_staff_user_id: Optional[int] = None
    filing_status: Optional[ReturnStatus] = None
    client_signed_off: Optional[bool] = None


class ClientOut(BaseModel):
    id: int
    firm_id: Optional[int] = None
    owner_user_id: Optional[int] = None
    assigned_staff_user_id: Optional[int] = None
    client_type: ClientType
    display_name: str
    bir_number: Optional[str] = None
    tin: Optional[str] = None
    nis_number: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    address: Optional[str] = None
    filing_status: ReturnStatus
    client_signed_off: bool

    model_config = ConfigDict(from_attributes=True)


# --- Tax config (admin) ---


class TaxYearConfigOut(BaseModel):
    id: int
    tax_year: int
    is_active: bool
    label: Optional[str] = None
    personal_allowance: float
    paye_bands: list[dict[str, Any]]
    nis_deductible_fraction: float
    business_levy_rate: float
    business_levy_annual_threshold: float
    business_levy_exempt_years: int
    green_fund_levy_rate: float
    corporate_tax_rate_standard: float
    corporate_tax_rate_banks_petrochemical: float
    corporate_tax_rate_sme_stock_exchange: float
    vat_standard_rate: float
    vat_registration_threshold: float
    health_surcharge_high_weekly: float
    health_surcharge_low_weekly: float
    health_surcharge_monthly_threshold: float
    nis_combined_rate: float
    nis_earnings_classes: list[dict[str, Any]]
    deduction_caps: dict[str, Any]
    wear_and_tear_classes: dict[str, Any]
    individual_filing_deadline: Optional[str] = None
    corporate_filing_deadline: Optional[str] = None
    individual_late_penalty_per_6mo: float
    corporate_late_penalty_per_6mo: float

    model_config = ConfigDict(from_attributes=True)


class TaxYearConfigUpdate(BaseModel):
    """All fields optional -- a system_admin can PATCH just the constants
    that changed (e.g. only `personal_allowance`) without resending the
    entire config."""

    is_active: Optional[bool] = None
    label: Optional[str] = None
    personal_allowance: Optional[float] = None
    paye_bands: Optional[list[dict[str, Any]]] = None
    nis_deductible_fraction: Optional[float] = None
    business_levy_rate: Optional[float] = None
    business_levy_annual_threshold: Optional[float] = None
    business_levy_exempt_years: Optional[int] = None
    green_fund_levy_rate: Optional[float] = None
    corporate_tax_rate_standard: Optional[float] = None
    corporate_tax_rate_banks_petrochemical: Optional[float] = None
    corporate_tax_rate_sme_stock_exchange: Optional[float] = None
    vat_standard_rate: Optional[float] = None
    vat_registration_threshold: Optional[float] = None
    health_surcharge_high_weekly: Optional[float] = None
    health_surcharge_low_weekly: Optional[float] = None
    health_surcharge_monthly_threshold: Optional[float] = None
    nis_combined_rate: Optional[float] = None
    nis_earnings_classes: Optional[list[dict[str, Any]]] = None
    deduction_caps: Optional[dict[str, Any]] = None
    wear_and_tear_classes: Optional[dict[str, Any]] = None
    individual_filing_deadline: Optional[str] = None
    corporate_filing_deadline: Optional[str] = None
    individual_late_penalty_per_6mo: Optional[float] = None
    corporate_late_penalty_per_6mo: Optional[float] = None


# --- TD4 ---


class TD4Create(BaseModel):
    client_id: int
    income_year: int
    source: TD4Source = TD4Source.MANUAL
    td4_type: TD4Type = TD4Type.INCOME
    employer_bir_number: Optional[str] = None
    employer_paye_number: Optional[str] = None
    employer_name: Optional[str] = None
    employee_bir_number: Optional[str] = None
    employee_name: Optional[str] = None
    employee_address: Optional[str] = None
    employee_nis_number: Optional[str] = None
    total_deductions: float = 0
    weeks_employed: int = 52
    remuneration: float = 0
    commission: float = 0
    allowance_it76: float = 0
    travel_allowance: float = 0
    other_allowance: float = 0
    previous_income: float = 0
    savings_plan: float = 0
    gross_earnings: float = 0
    employer_contributions: float = 0
    travel_dispensation: float = 0
    employee_contributions: float = 0
    nis_deducted: float = 0
    income_tax: float = 0
    total_health_surcharge_weeks: int = 0
    health_surcharge_weeks_at_high: int = 0
    health_surcharge_weeks_at_low: int = 0
    health_surcharge_amount: float = 0
    # OCR bookkeeping (populated when source == ocr_upload; see app.services.ocr)
    ocr_raw_text: Optional[str] = None
    ocr_confidence: Optional[float] = None
    manually_corrected: bool = False


class TD4Out(TD4Create):
    id: int

    model_config = ConfigDict(from_attributes=True)


class TD4OCRResponse(BaseModel):
    """Result of running OCR/text-extraction on an uploaded TD4 certificate
    file (image or PDF).

    `fields` is a best-effort suggestion (see app.services.ocr) meant to
    pre-fill the manual-correction form, not a final answer -- the frontend
    should let the user review/edit every value before saving a TD4Input.
    """

    raw_text: str
    confidence: float
    fields: dict[str, Any]
    page_count: int = 1


# --- Returns ---


class IndividualReturnPreviewRequest(BaseModel):
    """Same shape as IndividualReturnCreate but without client_id -- used by
    the wizard's live refund/balance indicator, which recomputes on every
    keystroke and must NOT create a database row each time."""

    tax_year: int
    inputs: dict[str, Any]


class IndividualReturnCreate(BaseModel):
    client_id: int
    tax_year: int
    inputs: dict[str, Any]
    td4_input_ids: list[int] = Field(default_factory=list)


class IndividualReturnOut(BaseModel):
    id: int
    client_id: int
    tax_year: int
    status: ReturnStatus
    inputs: dict[str, Any]
    computed: dict[str, Any]
    refund_or_balance_due: float

    model_config = ConfigDict(from_attributes=True)


class CorporateReturnPreviewRequest(BaseModel):
    tax_year: int
    inputs: dict[str, Any]


class CorporateReturnCreate(BaseModel):
    client_id: int
    tax_year: int
    accounting_period_start: Optional[str] = None
    accounting_period_end: Optional[str] = None
    inputs: dict[str, Any]


class CorporateReturnOut(BaseModel):
    id: int
    client_id: int
    tax_year: int
    status: ReturnStatus
    inputs: dict[str, Any]
    computed: dict[str, Any]
    refund_or_balance_due: float

    model_config = ConfigDict(from_attributes=True)


class VAT200ReturnCreate(BaseModel):
    client_id: int
    period_start: str
    period_end: str
    standard_rated_sales: float = 0
    zero_rated_sales: float = 0
    exempt_sales: float = 0
    input_vat_paid: float = 0
    output_vat_override: Optional[float] = None


class VAT200ReturnOut(BaseModel):
    id: int
    client_id: int
    period_start: str
    period_end: str
    status: ReturnStatus
    standard_rated_sales: float
    zero_rated_sales: float
    exempt_sales: float
    output_vat: float
    input_vat: float
    net_vat_payable: float
    computed: dict[str, Any]

    model_config = ConfigDict(from_attributes=True)


# --- Payroll ---


class PayrollLineIn(BaseModel):
    employee_name: str
    employee_client_id: Optional[int] = None
    gross_pay: float


class PayrollRunCreate(BaseModel):
    client_id: int
    pay_period_start: str
    pay_period_end: str
    frequency: PayFrequency = PayFrequency.MONTHLY
    lines: list[PayrollLineIn]


class PayrollLineOut(BaseModel):
    id: int
    employee_name: str
    employee_client_id: Optional[int] = None
    gross_pay: float
    nis_class_name: Optional[str] = None
    nis_employee: float
    nis_employer: float
    health_surcharge_employee: float
    health_surcharge_employer: float
    paye_deducted: float
    net_pay: float

    model_config = ConfigDict(from_attributes=True)


class PayrollRunOut(BaseModel):
    id: int
    client_id: int
    pay_period_start: str
    pay_period_end: str
    frequency: PayFrequency
    lines: list[PayrollLineOut]

    model_config = ConfigDict(from_attributes=True)


# --- e-Tax export ---


class ETaxExportLogOut(BaseModel):
    id: int
    client_id: int
    export_type: ETaxExportType
    tax_year: Optional[int] = None
    file_name: str
    row_count: Optional[int] = None
    validation_status: ValidationStatus
    validation_messages: list[str]
    created_at: str

    model_config = ConfigDict(from_attributes=True)


class TD4CsvExportRequest(BaseModel):
    client_id: int
    income_year: int
    td4_input_ids: list[int] = Field(default_factory=list, description="If empty, all TD4s for the client+year are used")


class VAT200ExportRequest(BaseModel):
    vat200_return_id: int


class NonLoggedInReturnExportRequest(BaseModel):
    return_type: str = Field(pattern="^(individual_return|corporate_return)$")
    return_id: int
    format: str = Field(pattern="^(xml|json)$", default="json")
