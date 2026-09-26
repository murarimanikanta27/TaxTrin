// Mirrors backend/app/models/enums.py and backend/app/schemas.py.
// Kept as a hand-written mirror (no codegen) since the POC's schema surface
// is small and stable; a larger app would generate this from the FastAPI
// OpenAPI schema instead.

export type UserRole =
  | "system_admin"
  | "firm_admin"
  | "firm_staff"
  | "individual"
  | "sole_trader"
  | "corporate";

export type SubscriptionTier = "free" | "pro" | "enterprise" | "firm";

export type ClientType = "individual" | "sole_trader" | "partnership" | "corporate";

export type ReturnStatus = "draft" | "pending_review" | "approved" | "exported" | "filed";

export type TD4Type = "Income" | "Pension" | "Severance";

export type TD4Source = "manual" | "ocr_upload" | "csv_import";

export type PayFrequency = "weekly" | "fortnightly" | "monthly";

export type ValidationStatus = "pending" | "passed" | "failed" | "unverified_format";

export interface User {
  id: number;
  email: string;
  full_name: string;
  role: UserRole;
  subscription_tier: SubscriptionTier;
  firm_id: number | null;
}

export interface TokenResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface Client {
  id: number;
  firm_id: number | null;
  owner_user_id: number | null;
  assigned_staff_user_id: number | null;
  client_type: ClientType;
  display_name: string;
  bir_number: string | null;
  tin: string | null;
  nis_number: string | null;
  email: string | null;
  phone: string | null;
  address: string | null;
  filing_status: ReturnStatus;
  client_signed_off: boolean;
}

export interface TaxBand {
  from: number;
  to: number | null;
  rate: number;
  taxable_amount: number;
  tax: number;
}

export interface PayeComputed {
  gross_income: number;
  personal_allowance: number;
  nis_deductible_portion: number;
  other_deductions: number;
  chargeable_income: number;
  tax_by_band: TaxBand[];
  total_tax: number;
}

export interface LeviesComputed {
  business_levy_gross: number;
  business_levy_payable: number;
  business_levy_exempt: boolean;
  green_fund_levy: number;
}

export interface IndividualReturnComputed {
  total_income: number;
  deduction_notes: string[];
  paye: PayeComputed;
  levies: LeviesComputed;
  paye_already_deducted: number;
  total_tax_liability: number;
  refund_or_balance_due: number;
  is_refund: boolean;
}

export interface IndividualReturn {
  id: number;
  client_id: number;
  tax_year: number;
  status: ReturnStatus;
  inputs: Record<string, unknown>;
  computed: IndividualReturnComputed;
  refund_or_balance_due: number;
}

export interface CorporateReturnComputed {
  chargeable_profits: number;
  rate_applied: number;
  corporation_tax: number;
  business_levy: LeviesComputed;
  dividend_paid: number;
  dividend_withholding_tax_rate: number;
  dividend_withholding_tax: number;
  total_statutory_liability: number;
  quarterly_installments_paid: number;
  refund_or_balance_due: number;
  is_refund: boolean;
}

export interface CorporateReturn {
  id: number;
  client_id: number;
  tax_year: number;
  status: ReturnStatus;
  inputs: Record<string, unknown>;
  computed: CorporateReturnComputed;
  refund_or_balance_due: number;
}

export interface VAT200ReturnComputed {
  standard_rated_sales: number;
  zero_rated_sales: number;
  exempt_sales: number;
  output_vat: number;
  input_vat: number;
  net_vat_payable: number;
  is_refund: boolean;
}

export interface VAT200Return {
  id: number;
  client_id: number;
  period_start: string;
  period_end: string;
  status: ReturnStatus;
  standard_rated_sales: number;
  zero_rated_sales: number;
  exempt_sales: number;
  output_vat: number;
  input_vat: number;
  net_vat_payable: number;
  computed: VAT200ReturnComputed;
}

export interface TD4Input {
  id: number;
  client_id: number;
  income_year: number;
  source: TD4Source;
  td4_type: TD4Type;
  employer_bir_number: string | null;
  employer_paye_number: string | null;
  employer_name: string | null;
  employee_bir_number: string | null;
  employee_name: string | null;
  employee_address: string | null;
  employee_nis_number: string | null;
  total_deductions: number;
  weeks_employed: number;
  remuneration: number;
  commission: number;
  allowance_it76: number;
  travel_allowance: number;
  other_allowance: number;
  previous_income: number;
  savings_plan: number;
  gross_earnings: number;
  employer_contributions: number;
  travel_dispensation: number;
  employee_contributions: number;
  nis_deducted: number;
  income_tax: number;
  total_health_surcharge_weeks: number;
  health_surcharge_weeks_at_high: number;
  health_surcharge_weeks_at_low: number;
  health_surcharge_amount: number;
  ocr_raw_text: string | null;
  ocr_confidence: number | null;
  manually_corrected: boolean;
}

export interface PayrollLine {
  id: number;
  employee_name: string;
  employee_client_id: number | null;
  gross_pay: number;
  nis_class_name: string | null;
  nis_employee: number;
  nis_employer: number;
  health_surcharge_employee: number;
  health_surcharge_employer: number;
  paye_deducted: number;
  net_pay: number;
}

export interface PayrollRun {
  id: number;
  client_id: number;
  pay_period_start: string;
  pay_period_end: string;
  frequency: PayFrequency;
  lines: PayrollLine[];
}

export interface TD4OCRResponse {
  raw_text: string;
  confidence: number;
  page_count: number;
  fields: Partial<
    Pick<
      TD4Input,
      | "employer_name"
      | "employer_bir_number"
      | "employee_name"
      | "employee_bir_number"
      | "employee_address"
      | "employee_nis_number"
      | "remuneration"
      | "commission"
      | "gross_earnings"
      | "nis_deducted"
      | "income_tax"
      | "health_surcharge_amount"
      | "total_deductions"
    >
  >;
}

export interface ETaxExportLog {
  id: number;
  client_id: number;
  export_type: string;
  tax_year: number | null;
  file_name: string;
  row_count: number | null;
  validation_status: ValidationStatus;
  validation_messages: string[];
  created_at: string;
}

export interface TaxYearConfig {
  id: number;
  tax_year: number;
  is_active: boolean;
  label: string | null;
  personal_allowance: number;
  paye_bands: { upto: number | null; rate: number }[];
  nis_deductible_fraction: number;
  business_levy_rate: number;
  business_levy_annual_threshold: number;
  business_levy_exempt_years: number;
  green_fund_levy_rate: number;
  corporate_tax_rate_standard: number;
  corporate_tax_rate_banks_petrochemical: number;
  corporate_tax_rate_sme_stock_exchange: number;
  vat_standard_rate: number;
  vat_registration_threshold: number;
  health_surcharge_high_weekly: number;
  health_surcharge_low_weekly: number;
  health_surcharge_monthly_threshold: number;
  nis_combined_rate: number;
  nis_earnings_classes: Record<string, unknown>[];
  deduction_caps: Record<string, number>;
  wear_and_tear_classes: Record<string, number>;
  individual_filing_deadline: string | null;
  corporate_filing_deadline: string | null;
  individual_late_penalty_per_6mo: number;
  corporate_late_penalty_per_6mo: number;
}
