import axios, { type AxiosResponse } from "axios";
import type {
  Client,
  CorporateReturn,
  CorporateReturnComputed,
  ETaxExportLog,
  IndividualReturn,
  IndividualReturnComputed,
  PayrollRun,
  TaxYearConfig,
  TD4Input,
  TD4OCRResponse,
  TokenResponse,
  User,
  VAT200Return,
} from "./types";

// In dev, Vite's proxy (see vite.config.ts) forwards /api/* to the FastAPI
// backend at 127.0.0.1:8000, sidestepping CORS entirely for local work.
const api = axios.create({ baseURL: "/api" });

const TOKEN_KEY = "taxtrin.token";

export function getToken(): string | null {
  return localStorage.getItem(TOKEN_KEY);
}

export function setToken(token: string | null): void {
  if (token) localStorage.setItem(TOKEN_KEY, token);
  else localStorage.removeItem(TOKEN_KEY);
}

api.interceptors.request.use((config) => {
  const token = getToken();
  if (token) {
    config.headers = config.headers ?? {};
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export interface ApiErrorShape {
  detail?: string | { msg: string }[];
}

function detailToMessage(data: ApiErrorShape | undefined): string | null {
  if (!data?.detail) return null;
  return typeof data.detail === "string" ? data.detail : data.detail.map((d) => d.msg).join(", ");
}

/**
 * Extracts a human-readable message from an API error.
 *
 * Requests that use `responseType: "blob"` (every file-download helper in
 * this module) get their error body back as a Blob too, not parsed JSON --
 * axios doesn't know the error is JSON until it's read. This synchronously
 * peeks at the Blob's already-buffered text via a FileReader-free trick
 * (Blob.text() is async, so callers needing the *exact* server detail from a
 * blob error should await `extractErrorMessageAsync` instead; this sync
 * version falls back to a generic message for blob errors so callers that
 * can't await still get something reasonable instead of "[object Blob]").
 */
export function extractErrorMessage(err: unknown): string {
  if (axios.isAxiosError(err)) {
    if (err.response?.data instanceof Blob) {
      return `Request failed (${err.response.status})`;
    }
    const message = detailToMessage(err.response?.data as ApiErrorShape | undefined);
    return message ?? err.message;
  }
  return err instanceof Error ? err.message : "Unexpected error";
}

/**
 * Same as `extractErrorMessage`, but also unpacks the real `detail` message
 * out of a blob-shaped error response (see note above). Prefer this in any
 * `catch` block wrapping a blob-download call (the export/download helpers
 * below that pass `responseType: "blob"`).
 */
export async function extractErrorMessageAsync(err: unknown): Promise<string> {
  if (axios.isAxiosError(err) && err.response?.data instanceof Blob) {
    try {
      const text = await err.response.data.text();
      const parsed = JSON.parse(text) as ApiErrorShape;
      const message = detailToMessage(parsed);
      if (message) return message;
    } catch {
      // fall through to the generic message below
    }
    return `Request failed (${err.response.status})`;
  }
  return extractErrorMessage(err);
}

// --- Auth ---

export async function login(email: string, password: string): Promise<TokenResponse> {
  const { data } = await api.post<TokenResponse>("/auth/login", { email, password });
  return data;
}

export async function register(payload: {
  email: string;
  password: string;
  full_name: string;
  role: string;
  firm_name?: string;
}): Promise<TokenResponse> {
  const { data } = await api.post<TokenResponse>("/auth/register", payload);
  return data;
}

export async function fetchMe(): Promise<User> {
  const { data } = await api.get<User>("/auth/me");
  return data;
}

// --- Clients ---

export async function listClients(): Promise<Client[]> {
  const { data } = await api.get<Client[]>("/clients");
  return data;
}

export async function getClient(clientId: number): Promise<Client> {
  const { data } = await api.get<Client>(`/clients/${clientId}`);
  return data;
}

export async function createClient(
  payload: Partial<Client> & { client_type: Client["client_type"]; display_name: string }
): Promise<Client> {
  const { data } = await api.post<Client>("/clients", payload);
  return data;
}

export async function updateClient(clientId: number, payload: Partial<Client>): Promise<Client> {
  const { data } = await api.patch<Client>(`/clients/${clientId}`, payload);
  return data;
}

// --- Admin tax config ---

export async function listTaxConfigs(): Promise<TaxYearConfig[]> {
  const { data } = await api.get<TaxYearConfig[]>("/admin/tax-config");
  return data;
}

export async function getTaxConfig(taxYear: number): Promise<TaxYearConfig> {
  const { data } = await api.get<TaxYearConfig>(`/admin/tax-config/${taxYear}`);
  return data;
}

export async function updateTaxConfig(taxYear: number, payload: Partial<TaxYearConfig>): Promise<TaxYearConfig> {
  const { data } = await api.patch<TaxYearConfig>(`/admin/tax-config/${taxYear}`, payload);
  return data;
}

// --- TD4 ---

export async function listTD4(clientId: number, incomeYear?: number): Promise<TD4Input[]> {
  const { data } = await api.get<TD4Input[]>("/td4", { params: { client_id: clientId, income_year: incomeYear } });
  return data;
}

export async function createTD4(payload: Partial<TD4Input> & { client_id: number; income_year: number }): Promise<TD4Input> {
  const { data } = await api.post<TD4Input>("/td4", payload);
  return data;
}

export async function deleteTD4(td4Id: number): Promise<void> {
  await api.delete(`/td4/${td4Id}`);
}

/** Drag-and-drop TD4 certificate OCR: uploads an image, returns raw text plus
 * best-effort extracted fields to pre-fill a manual-correction form. Does not
 * save a TD4Input itself -- call createTD4 afterward with the (possibly
 * edited) fields once the user has reviewed them. */
export async function ocrTD4Certificate(clientId: number, file: File): Promise<TD4OCRResponse> {
  const formData = new FormData();
  formData.append("file", file);
  // Deliberately no explicit Content-Type here: the browser/axios sets
  // "multipart/form-data; boundary=..." automatically for a FormData body,
  // and overriding it manually drops the boundary the server needs to parse it.
  const { data } = await api.post<TD4OCRResponse>(`/td4/ocr?client_id=${clientId}`, formData);
  return data;
}

// --- Returns ---

export async function previewIndividualReturn(payload: {
  tax_year: number;
  inputs: Record<string, unknown>;
}): Promise<IndividualReturnComputed> {
  const { data } = await api.post("/returns/individual/preview", payload);
  return data;
}

export async function createIndividualReturn(payload: {
  client_id: number;
  tax_year: number;
  inputs: Record<string, unknown>;
  td4_input_ids?: number[];
}): Promise<IndividualReturn> {
  const { data } = await api.post<IndividualReturn>("/returns/individual", payload);
  return data;
}

export async function listIndividualReturns(clientId: number): Promise<IndividualReturn[]> {
  const { data } = await api.get<IndividualReturn[]>(`/clients/${clientId}/returns/individual`);
  return data;
}

export async function previewCorporateReturn(payload: {
  tax_year: number;
  inputs: Record<string, unknown>;
}): Promise<CorporateReturnComputed> {
  const { data } = await api.post("/returns/corporate/preview", payload);
  return data;
}

export async function createCorporateReturn(payload: {
  client_id: number;
  tax_year: number;
  accounting_period_start?: string;
  accounting_period_end?: string;
  inputs: Record<string, unknown>;
}): Promise<CorporateReturn> {
  const { data } = await api.post<CorporateReturn>("/returns/corporate", payload);
  return data;
}

export async function listCorporateReturns(clientId: number): Promise<CorporateReturn[]> {
  const { data } = await api.get<CorporateReturn[]>(`/clients/${clientId}/returns/corporate`);
  return data;
}

export async function createVAT200Return(payload: {
  client_id: number;
  period_start: string;
  period_end: string;
  standard_rated_sales?: number;
  zero_rated_sales?: number;
  exempt_sales?: number;
  input_vat_paid?: number;
}): Promise<VAT200Return> {
  const { data } = await api.post<VAT200Return>("/returns/vat200", payload);
  return data;
}

export async function listVAT200Returns(clientId: number): Promise<VAT200Return[]> {
  const { data } = await api.get<VAT200Return[]>(`/clients/${clientId}/returns/vat200`);
  return data;
}

// --- Payroll ---

export async function createPayrollRun(payload: {
  client_id: number;
  pay_period_start: string;
  pay_period_end: string;
  frequency: string;
  lines: { employee_name: string; gross_pay: number }[];
}): Promise<PayrollRun> {
  const { data } = await api.post<PayrollRun>("/payroll/runs", payload);
  return data;
}

export async function listPayrollRuns(clientId: number): Promise<PayrollRun[]> {
  const { data } = await api.get<PayrollRun[]>(`/payroll/clients/${clientId}/runs`);
  return data;
}

// --- e-Tax export ---

export async function listExportLogs(clientId: number): Promise<ETaxExportLog[]> {
  const { data } = await api.get<ETaxExportLog[]>("/etax-export/logs", { params: { client_id: clientId } });
  return data;
}

function downloadBlob(response: AxiosResponse<Blob>, fallbackName: string) {
  const disposition = response.headers["content-disposition"] as string | undefined;
  const match = disposition?.match(/filename="?([^"]+)"?/);
  const fileName = match?.[1] ?? fallbackName;

  const url = window.URL.createObjectURL(response.data);
  const link = document.createElement("a");
  link.href = url;
  link.download = fileName;
  document.body.appendChild(link);
  link.click();
  link.remove();
  window.URL.revokeObjectURL(url);
}

export async function exportTD4Csv(clientId: number, incomeYear: number, td4InputIds: number[] = []): Promise<void> {
  const response = await api.post(
    "/etax-export/td4-supplementary-csv",
    { client_id: clientId, income_year: incomeYear, td4_input_ids: td4InputIds },
    { responseType: "blob" }
  );
  downloadBlob(response as AxiosResponse<Blob>, `TD4_Supplementary_${incomeYear}.csv`);
}

export async function exportVAT200Csv(vat200ReturnId: number): Promise<void> {
  const response = await api.post(
    "/etax-export/vat200-upload-csv",
    { vat200_return_id: vat200ReturnId },
    { responseType: "blob" }
  );
  downloadBlob(response as AxiosResponse<Blob>, "VAT200_Upload.csv");
}

export async function exportNonLoggedInReturn(
  returnType: "individual_return" | "corporate_return",
  returnId: number,
  format: "xml" | "json"
): Promise<void> {
  const response = await api.post(
    "/etax-export/non-logged-in-return",
    { return_type: returnType, return_id: returnId, format },
    { responseType: "blob" }
  );
  downloadBlob(response as AxiosResponse<Blob>, `NonLoggedInReturn.${format}`);
}

export async function downloadForm440Pdf(returnId: number): Promise<void> {
  const response = await api.get(`/etax-export/pdf/form-440/${returnId}`, { responseType: "blob" });
  downloadBlob(response as AxiosResponse<Blob>, "Form440.pdf");
}

export async function downloadForm500Pdf(returnId: number): Promise<void> {
  const response = await api.get(`/etax-export/pdf/form-500/${returnId}`, { responseType: "blob" });
  downloadBlob(response as AxiosResponse<Blob>, "Form500.pdf");
}

export async function downloadVAT200Pdf(returnId: number): Promise<void> {
  const response = await api.get(`/etax-export/pdf/vat200/${returnId}`, { responseType: "blob" });
  downloadBlob(response as AxiosResponse<Blob>, "VAT200.pdf");
}

export async function downloadPayrollSummaryPdf(runId: number): Promise<void> {
  const response = await api.get(`/etax-export/pdf/payroll-summary/${runId}`, { responseType: "blob" });
  downloadBlob(response as AxiosResponse<Blob>, "PayrollSummary.pdf");
}

export async function downloadPaymentVoucherPdf(
  clientId: number,
  params: { payment_type: string; quarter_label: string; tax_year: number; due_date: string; amount: number }
): Promise<void> {
  const response = await api.get(`/etax-export/pdf/payment-voucher/${clientId}`, {
    params,
    responseType: "blob",
  });
  downloadBlob(response as AxiosResponse<Blob>, "PaymentVoucher.pdf");
}

export default api;
