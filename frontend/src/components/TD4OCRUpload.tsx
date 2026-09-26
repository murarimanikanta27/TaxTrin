import { useRef, useState } from "react";
import { AlertTriangle, CheckCircle2, FileText, Loader2, UploadCloud } from "lucide-react";
import { createTD4, extractErrorMessage, ocrTD4Certificate } from "../lib/api";
import { Badge, Button, ErrorText, Field, Input } from "./ui";
import type { TD4OCRResponse } from "../lib/types";

interface CorrectionFields {
  employer_name: string;
  employer_bir_number: string;
  employee_name: string;
  employee_bir_number: string;
  employee_address: string;
  employee_nis_number: string;
  gross_earnings: string;
  nis_deducted: string;
  income_tax: string;
  health_surcharge_amount: string;
}

const EMPTY_FIELDS: CorrectionFields = {
  employer_name: "",
  employer_bir_number: "",
  employee_name: "",
  employee_bir_number: "",
  employee_address: "",
  employee_nis_number: "",
  gross_earnings: "",
  nis_deducted: "",
  income_tax: "",
  health_surcharge_amount: "",
};

function toCorrectionFields(ocr: TD4OCRResponse): CorrectionFields {
  return {
    employer_name: ocr.fields.employer_name ?? "",
    employer_bir_number: ocr.fields.employer_bir_number ?? "",
    employee_name: ocr.fields.employee_name ?? "",
    employee_bir_number: ocr.fields.employee_bir_number ?? "",
    employee_address: ocr.fields.employee_address ?? "",
    employee_nis_number: ocr.fields.employee_nis_number ?? "",
    gross_earnings: ocr.fields.gross_earnings != null ? String(ocr.fields.gross_earnings) : "",
    nis_deducted: ocr.fields.nis_deducted != null ? String(ocr.fields.nis_deducted) : "",
    income_tax: ocr.fields.income_tax != null ? String(ocr.fields.income_tax) : "",
    health_surcharge_amount: ocr.fields.health_surcharge_amount != null ? String(ocr.fields.health_surcharge_amount) : "",
  };
}

/**
 * Drag-and-drop TD4 certificate upload: sends the image to the backend's
 * Tesseract-based OCR endpoint, then shows the extracted fields side-by-side
 * with editable inputs so the user can correct anything before saving.
 * Nothing is persisted as a TD4Input until "Save corrected TD4" is clicked.
 */
export default function TD4OCRUpload({
  clientId,
  incomeYear,
  onSaved,
}: {
  clientId: number;
  incomeYear: number;
  onSaved: () => void;
}) {
  const [dragActive, setDragActive] = useState(false);
  const [scanning, setScanning] = useState(false);
  const [ocrResult, setOcrResult] = useState<TD4OCRResponse | null>(null);
  const [fields, setFields] = useState<CorrectionFields>(EMPTY_FIELDS);
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const fileInputRef = useRef<HTMLInputElement>(null);

  async function handleFile(file: File) {
    setError(null);
    setScanning(true);
    setOcrResult(null);
    try {
      const result = await ocrTD4Certificate(clientId, file);
      setOcrResult(result);
      setFields(toCorrectionFields(result));
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setScanning(false);
    }
  }

  function handleDrop(e: React.DragEvent<HTMLDivElement>) {
    e.preventDefault();
    setDragActive(false);
    const file = e.dataTransfer.files?.[0];
    if (file) handleFile(file);
  }

  function updateField<K extends keyof CorrectionFields>(key: K, value: string) {
    setFields((prev) => ({ ...prev, [key]: value }));
  }

  async function handleSaveCorrected() {
    setSaving(true);
    setError(null);
    try {
      await createTD4({
        client_id: clientId,
        income_year: incomeYear,
        td4_type: "Income",
        source: "ocr_upload",
        employer_name: fields.employer_name || undefined,
        employer_bir_number: fields.employer_bir_number || undefined,
        employee_name: fields.employee_name || undefined,
        employee_bir_number: fields.employee_bir_number || undefined,
        employee_address: fields.employee_address || undefined,
        employee_nis_number: fields.employee_nis_number || undefined,
        gross_earnings: Number(fields.gross_earnings) || 0,
        remuneration: Number(fields.gross_earnings) || 0,
        nis_deducted: Number(fields.nis_deducted) || 0,
        employee_contributions: Number(fields.nis_deducted) || 0,
        income_tax: Number(fields.income_tax) || 0,
        health_surcharge_amount: Number(fields.health_surcharge_amount) || 0,
        weeks_employed: 52,
        total_health_surcharge_weeks: 52,
        ocr_raw_text: ocrResult?.raw_text,
        ocr_confidence: ocrResult?.confidence,
        manually_corrected: true,
      });
      setOcrResult(null);
      setFields(EMPTY_FIELDS);
      onSaved();
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  const confidenceTone = ocrResult
    ? ocrResult.confidence >= 0.85
      ? "green"
      : ocrResult.confidence >= 0.6
        ? "amber"
        : "red"
    : "slate";

  return (
    <div className="space-y-3">
      <div
        onDragOver={(e) => {
          e.preventDefault();
          setDragActive(true);
        }}
        onDragLeave={() => setDragActive(false)}
        onDrop={handleDrop}
        onClick={() => fileInputRef.current?.click()}
        className={`flex cursor-pointer flex-col items-center justify-center rounded-lg border-2 border-dashed p-6 text-center transition-colors ${
          dragActive ? "border-brand-500 bg-brand-50" : "border-slate-300 bg-white hover:border-slate-400"
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept="image/png,image/jpeg,image/webp,image/tiff,image/bmp,application/pdf,.pdf"
          className="hidden"
          onChange={(e) => {
            const file = e.target.files?.[0];
            if (file) handleFile(file);
            e.target.value = "";
          }}
        />
        {scanning ? (
          <>
            <Loader2 size={24} className="mb-2 animate-spin text-brand-600" />
            <p className="text-sm font-medium text-slate-700">Reading certificate...</p>
          </>
        ) : (
          <>
            <UploadCloud size={24} className="mb-2 text-slate-400" />
            <p className="text-sm font-medium text-slate-700">Drag &amp; drop a TD4 certificate here</p>
            <p className="text-xs text-slate-500">or click to browse &middot; PDF, PNG, JPEG, WEBP, TIFF, or BMP</p>
          </>
        )}
      </div>

      <ErrorText message={error} />

      {ocrResult && (
        <div className="space-y-3 rounded-lg border border-slate-200 bg-white p-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2">
              <FileText size={16} className="text-slate-400" />
              <p className="text-sm font-medium text-slate-700">
                Review &amp; correct extracted fields
                {ocrResult.page_count > 1 && (
                  <span className="ml-1 text-xs font-normal text-slate-400">({ocrResult.page_count} pages)</span>
                )}
              </p>
            </div>
            <Badge tone={confidenceTone}>
              <span className="inline-flex items-center gap-1">
                {confidenceTone === "green" ? <CheckCircle2 size={12} /> : <AlertTriangle size={12} />}
                {Math.round(ocrResult.confidence * 100)}% confidence
              </span>
            </Badge>
          </div>
          <p className="text-xs text-slate-500">
            These values were read automatically from the uploaded file. Correct anything that looks wrong before
            saving -- extraction is a starting point, not a guarantee.
          </p>

          <div className="grid grid-cols-1 gap-3 sm:grid-cols-2">
            <Field label="Employer name">
              <Input value={fields.employer_name} onChange={(e) => updateField("employer_name", e.target.value)} />
            </Field>
            <Field label="Employer BIR number">
              <Input
                value={fields.employer_bir_number}
                onChange={(e) => updateField("employer_bir_number", e.target.value)}
              />
            </Field>
            <Field label="Employee name">
              <Input value={fields.employee_name} onChange={(e) => updateField("employee_name", e.target.value)} />
            </Field>
            <Field label="Employee BIR number">
              <Input
                value={fields.employee_bir_number}
                onChange={(e) => updateField("employee_bir_number", e.target.value)}
              />
            </Field>
            <Field label="Employee address">
              <Input
                value={fields.employee_address}
                onChange={(e) => updateField("employee_address", e.target.value)}
              />
            </Field>
            <Field label="Employee NIS number">
              <Input
                value={fields.employee_nis_number}
                onChange={(e) => updateField("employee_nis_number", e.target.value)}
              />
            </Field>
            <Field label="Gross earnings">
              <Input
                type="number"
                value={fields.gross_earnings}
                onChange={(e) => updateField("gross_earnings", e.target.value)}
              />
            </Field>
            <Field label="NIS deducted">
              <Input
                type="number"
                value={fields.nis_deducted}
                onChange={(e) => updateField("nis_deducted", e.target.value)}
              />
            </Field>
            <Field label="PAYE income tax deducted">
              <Input type="number" value={fields.income_tax} onChange={(e) => updateField("income_tax", e.target.value)} />
            </Field>
            <Field label="Health surcharge amount">
              <Input
                type="number"
                value={fields.health_surcharge_amount}
                onChange={(e) => updateField("health_surcharge_amount", e.target.value)}
              />
            </Field>
          </div>

          <Button onClick={handleSaveCorrected} disabled={saving}>
            {saving ? "Saving..." : "Save corrected TD4"}
          </Button>
        </div>
      )}
    </div>
  );
}
