import { useEffect, useState } from "react";
import { Pencil, Plus, Save, Trash2, X } from "lucide-react";
import { extractErrorMessage, getTaxConfig, updateTaxConfig } from "../lib/api";
import { Button, Card, CardBody, CardHeader, CardTitle, ErrorText, Field, Input } from "../components/ui";
import type { TaxYearConfig } from "../lib/types";

const TAX_YEAR = 2026;

type NumericConfigKey = keyof Pick<
  TaxYearConfig,
  | "personal_allowance"
  | "nis_deductible_fraction"
  | "business_levy_rate"
  | "business_levy_annual_threshold"
  | "green_fund_levy_rate"
  | "corporate_tax_rate_standard"
  | "corporate_tax_rate_banks_petrochemical"
  | "vat_standard_rate"
  | "vat_registration_threshold"
  | "health_surcharge_high_weekly"
  | "health_surcharge_low_weekly"
  | "health_surcharge_monthly_threshold"
>;

// `kind` controls how a value is displayed in read-only mode:
//   money   -> TT$ + thousands separators
//   percent -> value is a decimal fraction (0.25) shown as "25%"
//   number  -> shown as-is
const FIELDS: { key: NumericConfigKey; label: string; step?: string; kind: "money" | "percent" | "number" }[] = [
  { key: "personal_allowance", label: "Personal allowance (TT$/year)", kind: "money" },
  { key: "nis_deductible_fraction", label: "NIS deductible fraction (before PAYE)", step: "0.01", kind: "percent" },
  { key: "business_levy_rate", label: "Business Levy rate", step: "0.001", kind: "percent" },
  { key: "business_levy_annual_threshold", label: "Business Levy annual threshold (TT$)", kind: "money" },
  { key: "green_fund_levy_rate", label: "Green Fund Levy rate", step: "0.001", kind: "percent" },
  { key: "corporate_tax_rate_standard", label: "Corporate tax rate — standard", step: "0.01", kind: "percent" },
  { key: "corporate_tax_rate_banks_petrochemical", label: "Corporate tax rate — banks/petrochemical", step: "0.01", kind: "percent" },
  { key: "vat_standard_rate", label: "VAT standard rate", step: "0.001", kind: "percent" },
  { key: "vat_registration_threshold", label: "VAT registration threshold (TT$)", kind: "money" },
  { key: "health_surcharge_high_weekly", label: "Health Surcharge — high bracket (TT$/week)", step: "0.01", kind: "money" },
  { key: "health_surcharge_low_weekly", label: "Health Surcharge — low bracket (TT$/week)", step: "0.01", kind: "money" },
  { key: "health_surcharge_monthly_threshold", label: "Health Surcharge monthly threshold (TT$)", step: "0.01", kind: "money" },
];

function formatValue(value: number, kind: "money" | "percent" | "number"): string {
  if (kind === "money") return `TT$${value.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
  if (kind === "percent") return `${(value * 100).toLocaleString("en-US", { maximumFractionDigits: 2 })}%`;
  return String(value);
}

// --- PAYE bands: backend stores rate as a fraction (0.25) + upto as
// number|null; the UI edits rate as a whole-number percent and upto as text. ---
interface EditableBand {
  uptoText: string;
  ratePercent: string;
}

function toEditableBands(bands: TaxYearConfig["paye_bands"]): EditableBand[] {
  return bands.map((b) => ({
    uptoText: b.upto == null ? "" : String(b.upto),
    ratePercent: String(Math.round(b.rate * 1000) / 10),
  }));
}

function toApiBands(editable: EditableBand[]): TaxYearConfig["paye_bands"] {
  return editable.map((b) => ({
    upto: b.uptoText.trim() === "" ? null : Number(b.uptoText),
    rate: (Number(b.ratePercent) || 0) / 100,
  }));
}

// --- NIS earnings classes ---
interface EditableNisClass {
  class_name: string;
  weekly_min: string;
  weekly_max: string; // "" means "and over" (open-ended top class)
  employee_weekly: string;
  employer_weekly: string;
}

function toEditableNis(rows: Record<string, unknown>[]): EditableNisClass[] {
  return rows.map((r) => ({
    class_name: String(r.class_name ?? ""),
    weekly_min: r.weekly_min == null ? "" : String(r.weekly_min),
    weekly_max: r.weekly_max == null ? "" : String(r.weekly_max),
    employee_weekly: r.employee_weekly == null ? "" : String(r.employee_weekly),
    employer_weekly: r.employer_weekly == null ? "" : String(r.employer_weekly),
  }));
}

function toApiNis(rows: EditableNisClass[]): Record<string, unknown>[] {
  return rows.map((r) => ({
    class_name: r.class_name,
    weekly_min: Number(r.weekly_min) || 0,
    weekly_max: r.weekly_max.trim() === "" ? null : Number(r.weekly_max),
    employee_weekly: Number(r.employee_weekly) || 0,
    employer_weekly: Number(r.employer_weekly) || 0,
  }));
}

export default function AdminTaxConfigPage() {
  const [config, setConfig] = useState<TaxYearConfig | null>(null);
  // Draft copies edited while in edit mode; committed to `config` only on save.
  const [draftScalars, setDraftScalars] = useState<Partial<Record<NumericConfigKey, number>>>({});
  const [bands, setBands] = useState<EditableBand[]>([]);
  const [nisClasses, setNisClasses] = useState<EditableNisClass[]>([]);

  const [editing, setEditing] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [validationError, setValidationError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);

  useEffect(() => {
    getTaxConfig(TAX_YEAR)
      .then((cfg) => {
        setConfig(cfg);
      })
      .catch((err) => setError(extractErrorMessage(err)));
  }, []);

  function beginEdit() {
    if (!config) return;
    setDraftScalars(Object.fromEntries(FIELDS.map((f) => [f.key, config[f.key]])) as Record<NumericConfigKey, number>);
    setBands(toEditableBands(config.paye_bands));
    setNisClasses(toEditableNis(config.nis_earnings_classes));
    setValidationError(null);
    setSaved(false);
    setEditing(true);
  }

  function cancelEdit() {
    setEditing(false);
    setValidationError(null);
    setError(null);
  }

  function updateScalar(key: NumericConfigKey, value: number) {
    setDraftScalars((prev) => ({ ...prev, [key]: value }));
  }

  function updateBand(index: number, patch: Partial<EditableBand>) {
    setBands((prev) => prev.map((b, i) => (i === index ? { ...b, ...patch } : b)));
  }

  function updateNis(index: number, patch: Partial<EditableNisClass>) {
    setNisClasses((prev) => prev.map((r, i) => (i === index ? { ...r, ...patch } : r)));
  }

  function validate(): string | null {
    if (bands.length === 0) return "There must be at least one PAYE band.";
    for (let i = 0; i < bands.length; i++) {
      const rate = Number(bands[i].ratePercent);
      if (bands[i].ratePercent.trim() === "" || Number.isNaN(rate) || rate < 0 || rate > 100) {
        return `PAYE band ${i + 1}: rate must be a percentage between 0 and 100.`;
      }
      const isLast = i === bands.length - 1;
      if (!isLast && (bands[i].uptoText.trim() === "" || Number(bands[i].uptoText) <= 0)) {
        return `PAYE band ${i + 1}: "up to" must be a positive amount (only the last band may be open-ended).`;
      }
    }
    return null;
  }

  async function handleSave() {
    if (!config) return;
    const problem = validate();
    if (problem) {
      setValidationError(problem);
      return;
    }
    setSaving(true);
    setError(null);
    setValidationError(null);
    try {
      const updated = await updateTaxConfig(TAX_YEAR, {
        ...draftScalars,
        paye_bands: toApiBands(bands),
        nis_earnings_classes: toApiNis(nisClasses),
      });
      setConfig(updated);
      setEditing(false);
      setSaved(true);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  if (!config) {
    return <p className="text-sm text-slate-500">{error ? <ErrorText message={error} /> : "Loading tax configuration..."}</p>;
  }

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Tax Configuration — {TAX_YEAR}</h1>
          <p className="text-sm text-slate-500">
            {editing
              ? "Editing statutory constants. Changes apply immediately to all new calculations once saved."
              : "View-only. Click Edit to change any statutory rate, threshold, PAYE band, or NIS class."}
          </p>
        </div>
        {!editing ? (
          <Button onClick={beginEdit}>
            <Pencil size={16} /> Edit
          </Button>
        ) : (
          <div className="flex items-center gap-2">
            {saved && <span className="text-sm text-emerald-600">Saved.</span>}
            <Button variant="secondary" onClick={cancelEdit} disabled={saving}>
              <X size={16} /> Cancel
            </Button>
            <Button onClick={handleSave} disabled={saving}>
              <Save size={16} /> {saving ? "Saving..." : "Save changes"}
            </Button>
          </div>
        )}
      </div>

      {saved && !editing && <span className="inline-block text-sm text-emerald-600">Configuration saved.</span>}

      <Card>
        <CardHeader>
          <CardTitle>Statutory rates &amp; thresholds</CardTitle>
        </CardHeader>
        <CardBody className="grid grid-cols-1 gap-4 md:grid-cols-2">
          {FIELDS.map((field) => (
            <Field key={field.key} label={field.label}>
              {editing ? (
                <Input
                  type="number"
                  step={field.step ?? "1"}
                  value={draftScalars[field.key] ?? config[field.key]}
                  onChange={(e) => updateScalar(field.key, Number(e.target.value))}
                />
              ) : (
                <p className="rounded-lg bg-slate-50 px-3 py-2 text-sm font-medium text-slate-800">
                  {formatValue(config[field.key], field.kind)}
                </p>
              )}
            </Field>
          ))}
        </CardBody>
      </Card>

      <Card>
        <CardHeader className="flex items-center justify-between">
          <CardTitle>PAYE bands</CardTitle>
          {editing && (
            <Button variant="secondary" onClick={() => setBands((prev) => [...prev, { uptoText: "", ratePercent: "" }])}>
              <Plus size={14} /> Add band
            </Button>
          )}
        </CardHeader>
        <CardBody>
          {editing ? (
            <div className="space-y-3">
              <p className="text-xs text-slate-500">
                Each band taxes only the slice of chargeable income within it. Leave &quot;up to&quot; blank on the
                final band for &quot;no upper limit&quot;.
              </p>
              <div className="grid grid-cols-[1fr_120px_40px] gap-3 text-xs font-medium uppercase tracking-wide text-slate-500">
                <span>Chargeable income up to (TT$)</span>
                <span>Rate (%)</span>
                <span />
              </div>
              {bands.map((band, idx) => {
                const isLast = idx === bands.length - 1;
                return (
                  <div key={idx} className="grid grid-cols-[1fr_120px_40px] items-center gap-3">
                    <Input
                      type="number"
                      min={0}
                      placeholder={isLast ? "No upper limit" : "e.g. 1000000"}
                      value={band.uptoText}
                      onChange={(e) => updateBand(idx, { uptoText: e.target.value })}
                    />
                    <Input
                      type="number"
                      min={0}
                      max={100}
                      step="0.1"
                      placeholder="25"
                      value={band.ratePercent}
                      onChange={(e) => updateBand(idx, { ratePercent: e.target.value })}
                    />
                    <button
                      type="button"
                      onClick={() => setBands((prev) => prev.filter((_, i) => i !== idx))}
                      disabled={bands.length === 1}
                      className="flex justify-center text-slate-400 hover:text-red-600 disabled:cursor-not-allowed disabled:opacity-40"
                      title={bands.length === 1 ? "At least one band is required" : "Remove band"}
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                );
              })}
              <ErrorText message={validationError} />
            </div>
          ) : (
            <table className="w-full text-sm">
              <thead className="text-left text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="pb-2">Chargeable income up to</th>
                  <th className="pb-2">Rate</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {config.paye_bands.map((band, idx) => (
                  <tr key={idx}>
                    <td className="py-2 text-slate-700">
                      {band.upto === null ? "No limit" : `TT$${band.upto.toLocaleString()}`}
                    </td>
                    <td className="py-2 text-slate-700">{(band.rate * 100).toFixed(band.rate * 100 % 1 === 0 ? 0 : 1)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </CardBody>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>NIS earnings classes ({config.nis_earnings_classes.length})</CardTitle>
        </CardHeader>
        <CardBody className="p-0">
          <table className="w-full text-xs">
            <thead className="border-b border-slate-100 bg-slate-50 text-left uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-4 py-2">Class</th>
                <th className="px-4 py-2">Weekly min</th>
                <th className="px-4 py-2">Weekly max</th>
                <th className="px-4 py-2">Employee</th>
                <th className="px-4 py-2">Employer</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {editing
                ? nisClasses.map((row, idx) => (
                    <tr key={idx}>
                      <td className="px-2 py-1">
                        <Input value={row.class_name} onChange={(e) => updateNis(idx, { class_name: e.target.value })} />
                      </td>
                      <td className="px-2 py-1">
                        <Input type="number" value={row.weekly_min} onChange={(e) => updateNis(idx, { weekly_min: e.target.value })} />
                      </td>
                      <td className="px-2 py-1">
                        <Input
                          type="number"
                          placeholder="and over"
                          value={row.weekly_max}
                          onChange={(e) => updateNis(idx, { weekly_max: e.target.value })}
                        />
                      </td>
                      <td className="px-2 py-1">
                        <Input type="number" step="0.01" value={row.employee_weekly} onChange={(e) => updateNis(idx, { employee_weekly: e.target.value })} />
                      </td>
                      <td className="px-2 py-1">
                        <Input type="number" step="0.01" value={row.employer_weekly} onChange={(e) => updateNis(idx, { employer_weekly: e.target.value })} />
                      </td>
                    </tr>
                  ))
                : config.nis_earnings_classes.map((row) => (
                    <tr key={row.class_name as string}>
                      <td className="px-4 py-2 font-medium text-slate-700">{row.class_name as string}</td>
                      <td className="px-4 py-2 text-slate-600">${row.weekly_min as number}</td>
                      <td className="px-4 py-2 text-slate-600">{row.weekly_max ? `$${row.weekly_max}` : "and over"}</td>
                      <td className="px-4 py-2 text-slate-600">${(row.employee_weekly as number).toFixed(2)}</td>
                      <td className="px-4 py-2 text-slate-600">${(row.employer_weekly as number).toFixed(2)}</td>
                    </tr>
                  ))}
            </tbody>
          </table>
        </CardBody>
      </Card>

      <ErrorText message={error} />
    </div>
  );
}
