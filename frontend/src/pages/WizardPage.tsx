import { useEffect, useMemo, useState } from "react";
import { CheckCircle2, HelpCircle, Sparkles, Trash2, UploadCloud } from "lucide-react";
import { useClients } from "../lib/ClientContext";
import {
  createIndividualReturn,
  createTD4,
  deleteTD4,
  downloadForm440Pdf,
  exportTD4Csv,
  extractErrorMessage,
  extractErrorMessageAsync,
  listTD4,
  previewIndividualReturn,
} from "../lib/api";
import { Badge, Button, Card, CardBody, CardHeader, CardTitle, ErrorText, Field, Input } from "../components/ui";
import TD4OCRUpload from "../components/TD4OCRUpload";
import { formatMoney } from "../lib/format";
import type { IndividualReturnComputed, TD4Input } from "../lib/types";

const TAX_YEAR = 2026;

interface WizardAnswers {
  hasTD4: boolean;
  boughtHome: boolean;
  homeInterest: number;
  hasPension: boolean;
  pensionContribution: number;
  tertiaryEducation: number;
  charitableDonations: number;
  selfEmployedIncome: number;
  payeAlreadyDeducted: number;
}

const INITIAL_ANSWERS: WizardAnswers = {
  hasTD4: true,
  boughtHome: false,
  homeInterest: 0,
  hasPension: false,
  pensionContribution: 0,
  tertiaryEducation: 0,
  charitableDonations: 0,
  selfEmployedIncome: 0,
  payeAlreadyDeducted: 0,
};

function useDebouncedValue<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const handle = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(handle);
  }, [value, delayMs]);
  return debounced;
}

export default function WizardPage() {
  const { selectedClient } = useClients();
  const [answers, setAnswers] = useState<WizardAnswers>(INITIAL_ANSWERS);
  const [td4s, setTd4s] = useState<TD4Input[]>([]);
  const [td4EntryMode, setTd4EntryMode] = useState<"scan" | "manual" | null>(null);
  const [computed, setComputed] = useState<IndividualReturnComputed | null>(null);
  const [previewLoading, setPreviewLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [savedReturnId, setSavedReturnId] = useState<number | null>(null);

  const debouncedAnswers = useDebouncedValue(answers, 350);

  useEffect(() => {
    if (!selectedClient) return;
    listTD4(selectedClient.id, TAX_YEAR).then(setTd4s).catch(() => setTd4s([]));
  }, [selectedClient]);

  const emolumentIncome = useMemo(() => td4s.reduce((sum, t) => sum + t.gross_earnings, 0), [td4s]);
  const employeeNisPaid = useMemo(() => td4s.reduce((sum, t) => sum + t.nis_deducted, 0), [td4s]);
  const payeFromTd4 = useMemo(() => td4s.reduce((sum, t) => sum + t.income_tax, 0), [td4s]);

  const inputs = useMemo(
    () => ({
      emolument_income: debouncedAnswers.hasTD4 ? emolumentIncome : 0,
      employee_nis_paid: debouncedAnswers.hasTD4 ? employeeNisPaid : 0,
      paye_already_deducted: debouncedAnswers.payeAlreadyDeducted || payeFromTd4,
      self_employed_income: debouncedAnswers.selfEmployedIncome,
      deductions: {
        tertiary_education: debouncedAnswers.tertiaryEducation,
        pension_annuity_nis_voluntary: debouncedAnswers.hasPension ? debouncedAnswers.pensionContribution : 0,
        first_time_homeowner_interest: debouncedAnswers.boughtHome ? debouncedAnswers.homeInterest : 0,
        charitable_donations: debouncedAnswers.charitableDonations,
      },
    }),
    [debouncedAnswers, emolumentIncome, employeeNisPaid, payeFromTd4]
  );

  useEffect(() => {
    setPreviewLoading(true);
    setError(null);
    previewIndividualReturn({ tax_year: TAX_YEAR, inputs })
      .then(setComputed)
      .catch((err) => setError(extractErrorMessage(err)))
      .finally(() => setPreviewLoading(false));
  }, [inputs]);

  function update<K extends keyof WizardAnswers>(key: K, value: WizardAnswers[K]) {
    setAnswers((prev) => ({ ...prev, [key]: value }));
    setSavedReturnId(null);
  }

  async function handleSaveReturn() {
    if (!selectedClient) return;
    setSubmitting(true);
    setError(null);
    try {
      const result = await createIndividualReturn({
        client_id: selectedClient.id,
        tax_year: TAX_YEAR,
        inputs,
        td4_input_ids: td4s.map((t) => t.id),
      });
      setSavedReturnId(result.id);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDownloadForm440() {
    if (!savedReturnId) return;
    setError(null);
    try {
      await downloadForm440Pdf(savedReturnId);
    } catch (err) {
      setError(await extractErrorMessageAsync(err));
    }
  }

  async function handleExportTd4Csv() {
    if (!selectedClient) return;
    setError(null);
    try {
      await exportTD4Csv(selectedClient.id, TAX_YEAR, td4s.map((t) => t.id));
    } catch (err) {
      setError(await extractErrorMessageAsync(err));
    }
  }

  if (!selectedClient) {
    return <p className="text-sm text-slate-500">Select a client to begin the tax wizard.</p>;
  }

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
      <div className="space-y-6 lg:col-span-2">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Guided Tax Wizard — {TAX_YEAR}</h1>
          <p className="text-sm text-slate-500">Answer a few plain-English questions for {selectedClient.display_name}.</p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Did you receive a TD4 slip?</CardTitle>
          </CardHeader>
          <CardBody className="space-y-4">
            <div className="flex gap-3">
              <Button variant={answers.hasTD4 ? "primary" : "secondary"} onClick={() => update("hasTD4", true)}>
                Yes
              </Button>
              <Button variant={!answers.hasTD4 ? "primary" : "secondary"} onClick={() => update("hasTD4", false)}>
                No
              </Button>
            </div>

            {answers.hasTD4 && (
              <div className="rounded-lg border border-slate-100 bg-slate-50 p-4">
                <div className="mb-3 flex items-center justify-between">
                  <p className="text-sm font-medium text-slate-700">TD4 certificates on file for {TAX_YEAR}</p>
                  <div className="flex gap-2">
                    <Button
                      variant={td4EntryMode === "scan" ? "primary" : "secondary"}
                      onClick={() => setTd4EntryMode(td4EntryMode === "scan" ? null : "scan")}
                    >
                      <Sparkles size={14} /> Scan certificate
                    </Button>
                    <Button
                      variant={td4EntryMode === "manual" ? "primary" : "secondary"}
                      onClick={() => setTd4EntryMode(td4EntryMode === "manual" ? null : "manual")}
                    >
                      <UploadCloud size={14} /> Add manually
                    </Button>
                  </div>
                </div>

                {td4s.length === 0 ? (
                  <p className="text-sm text-slate-500">No TD4 records yet. Add one to include it in this return.</p>
                ) : (
                  <ul className="space-y-2">
                    {td4s.map((t) => (
                      <li key={t.id} className="flex items-center justify-between rounded-md bg-white px-3 py-2 text-sm shadow-sm">
                        <div>
                          <div className="flex items-center gap-2">
                            <p className="font-medium text-slate-800">{t.employer_name || "Employer"}</p>
                            {t.source === "ocr_upload" && <Badge tone="blue">Scanned</Badge>}
                          </div>
                          <p className="text-xs text-slate-500">
                            Gross {formatMoney(t.gross_earnings)} &middot; NIS {formatMoney(t.nis_deducted)} &middot; PAYE{" "}
                            {formatMoney(t.income_tax)}
                          </p>
                        </div>
                        <button
                          onClick={() => deleteTD4(t.id).then(() => listTD4(selectedClient.id, TAX_YEAR).then(setTd4s))}
                          className="text-slate-400 hover:text-red-600"
                        >
                          <Trash2 size={16} />
                        </button>
                      </li>
                    ))}
                  </ul>
                )}

                {td4EntryMode === "scan" && (
                  <div className="mt-3">
                    <TD4OCRUpload
                      clientId={selectedClient.id}
                      incomeYear={TAX_YEAR}
                      onSaved={() => {
                        setTd4EntryMode(null);
                        listTD4(selectedClient.id, TAX_YEAR).then(setTd4s);
                      }}
                    />
                  </div>
                )}

                {td4EntryMode === "manual" && (
                  <TD4QuickAddForm
                    clientId={selectedClient.id}
                    onAdded={() => {
                      setTd4EntryMode(null);
                      listTD4(selectedClient.id, TAX_YEAR).then(setTd4s);
                    }}
                  />
                )}
              </div>
            )}
          </CardBody>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Did you buy a home this year?</CardTitle>
          </CardHeader>
          <CardBody className="space-y-3">
            <div className="flex gap-3">
              <Button variant={answers.boughtHome ? "primary" : "secondary"} onClick={() => update("boughtHome", true)}>
                Yes
              </Button>
              <Button variant={!answers.boughtHome ? "primary" : "secondary"} onClick={() => update("boughtHome", false)}>
                No
              </Button>
            </div>
            {answers.boughtHome && (
              <Field label="Mortgage interest paid this year (capped at TT$30,000)">
                <Input
                  type="number"
                  min={0}
                  value={answers.homeInterest || ""}
                  onChange={(e) => update("homeInterest", Number(e.target.value))}
                />
              </Field>
            )}
          </CardBody>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Do you contribute to an approved pension, annuity, or voluntary NIS?</CardTitle>
          </CardHeader>
          <CardBody className="space-y-3">
            <div className="flex gap-3">
              <Button variant={answers.hasPension ? "primary" : "secondary"} onClick={() => update("hasPension", true)}>
                Yes
              </Button>
              <Button variant={!answers.hasPension ? "primary" : "secondary"} onClick={() => update("hasPension", false)}>
                No
              </Button>
            </div>
            {answers.hasPension && (
              <Field label="Total contributions this year (capped at TT$60,000 aggregate)">
                <Input
                  type="number"
                  min={0}
                  value={answers.pensionContribution || ""}
                  onChange={(e) => update("pensionContribution", Number(e.target.value))}
                />
              </Field>
            )}
          </CardBody>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Other deductions</CardTitle>
          </CardHeader>
          <CardBody className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <Field label="Tertiary education expenses (cap TT$72,000)">
              <Input
                type="number"
                min={0}
                value={answers.tertiaryEducation || ""}
                onChange={(e) => update("tertiaryEducation", Number(e.target.value))}
              />
            </Field>
            <Field label="Charitable donations (cap 15% of income)">
              <Input
                type="number"
                min={0}
                value={answers.charitableDonations || ""}
                onChange={(e) => update("charitableDonations", Number(e.target.value))}
              />
            </Field>
            <Field label="Self-employed / sole trader net income">
              <Input
                type="number"
                min={0}
                value={answers.selfEmployedIncome || ""}
                onChange={(e) => update("selfEmployedIncome", Number(e.target.value))}
              />
            </Field>
            <Field label="Override PAYE already deducted (optional)">
              <Input
                type="number"
                min={0}
                placeholder={formatMoney(payeFromTd4)}
                value={answers.payeAlreadyDeducted || ""}
                onChange={(e) => update("payeAlreadyDeducted", Number(e.target.value))}
              />
            </Field>
          </CardBody>
        </Card>
      </div>

      <div className="space-y-4">
        <Card className="sticky top-6">
          <CardHeader>
            <CardTitle>Live estimate</CardTitle>
          </CardHeader>
          <CardBody>
            {previewLoading && !computed ? (
              <p className="text-sm text-slate-500">Calculating...</p>
            ) : computed ? (
              <>
                <div className={`rounded-lg p-4 ${computed.is_refund ? "bg-emerald-50" : "bg-amber-50"}`}>
                  <p className="text-xs font-medium uppercase tracking-wide text-slate-500">
                    {computed.is_refund ? "Estimated refund" : "Estimated balance due"}
                  </p>
                  <p className={`text-2xl font-bold ${computed.is_refund ? "text-emerald-700" : "text-amber-700"}`}>
                    {formatMoney(Math.abs(computed.refund_or_balance_due))}
                  </p>
                </div>

                <dl className="mt-4 space-y-2 text-sm">
                  <div className="flex justify-between">
                    <dt className="text-slate-500">Total income</dt>
                    <dd className="font-medium text-slate-800">{formatMoney(computed.total_income)}</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-slate-500">Personal allowance</dt>
                    <dd className="font-medium text-slate-800">{formatMoney(computed.paye.personal_allowance)}</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-slate-500">Chargeable income</dt>
                    <dd className="font-medium text-slate-800">{formatMoney(computed.paye.chargeable_income)}</dd>
                  </div>
                  <div className="flex justify-between border-t border-slate-100 pt-2">
                    <dt className="text-slate-500">PAYE tax</dt>
                    <dd className="font-medium text-slate-800">{formatMoney(computed.paye.total_tax)}</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-slate-500">Business Levy</dt>
                    <dd className="font-medium text-slate-800">
                      {computed.levies.business_levy_exempt ? "Exempt" : formatMoney(computed.levies.business_levy_payable)}
                    </dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-slate-500">PAYE already deducted</dt>
                    <dd className="font-medium text-slate-800">{formatMoney(computed.paye_already_deducted)}</dd>
                  </div>
                </dl>

                {computed.deduction_notes.length > 0 && (
                  <div className="mt-4 space-y-1 rounded-lg bg-slate-50 p-3">
                    {computed.deduction_notes.map((note, idx) => (
                      <p key={idx} className="flex items-start gap-1.5 text-xs text-slate-500">
                        <HelpCircle size={12} className="mt-0.5 flex-shrink-0" /> {note}
                      </p>
                    ))}
                  </div>
                )}
              </>
            ) : (
              <p className="text-sm text-slate-500">Answer the questions to see your estimate.</p>
            )}

            <ErrorText message={error} />

            <div className="mt-4 space-y-2">
              <Button className="w-full" onClick={handleSaveReturn} disabled={submitting}>
                {submitting ? "Saving..." : "Save this return"}
              </Button>
              {savedReturnId && (
                <>
                  <div className="flex items-center gap-1.5 text-sm text-emerald-600">
                    <CheckCircle2 size={16} /> Return #{savedReturnId} saved
                  </div>
                  <Button variant="secondary" className="w-full" onClick={handleDownloadForm440}>
                    Download Form 440 PDF
                  </Button>
                  <Button variant="secondary" className="w-full" onClick={handleExportTd4Csv}>
                    Export TD4 Supplementary CSV
                  </Button>
                </>
              )}
            </div>
          </CardBody>
        </Card>
      </div>
    </div>
  );
}

function TD4QuickAddForm({ clientId, onAdded }: { clientId: number; onAdded: () => void }) {
  const [employerName, setEmployerName] = useState("");
  const [grossEarnings, setGrossEarnings] = useState("");
  const [nisDeducted, setNisDeducted] = useState("");
  const [incomeTax, setIncomeTax] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleAdd(e: React.FormEvent) {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      await createTD4({
        client_id: clientId,
        income_year: TAX_YEAR,
        td4_type: "Income",
        employer_name: employerName,
        gross_earnings: Number(grossEarnings) || 0,
        remuneration: Number(grossEarnings) || 0,
        nis_deducted: Number(nisDeducted) || 0,
        employee_contributions: Number(nisDeducted) || 0,
        income_tax: Number(incomeTax) || 0,
        weeks_employed: 52,
        total_health_surcharge_weeks: 52,
      });
      onAdded();
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <form onSubmit={handleAdd} className="mt-3 grid grid-cols-2 gap-3 rounded-lg border border-dashed border-slate-300 p-3">
      <Field label="Employer name">
        <Input value={employerName} onChange={(e) => setEmployerName(e.target.value)} required />
      </Field>
      <Field label="Gross earnings">
        <Input type="number" value={grossEarnings} onChange={(e) => setGrossEarnings(e.target.value)} required />
      </Field>
      <Field label="NIS deducted">
        <Input type="number" value={nisDeducted} onChange={(e) => setNisDeducted(e.target.value)} />
      </Field>
      <Field label="PAYE income tax deducted">
        <Input type="number" value={incomeTax} onChange={(e) => setIncomeTax(e.target.value)} />
      </Field>
      <div className="col-span-2">
        <ErrorText message={error} />
        <Button type="submit" disabled={saving}>
          {saving ? "Adding..." : "Add TD4"}
        </Button>
      </div>
    </form>
  );
}
