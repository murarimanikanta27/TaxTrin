import { useEffect, useState } from "react";
import { Plus, Trash2 } from "lucide-react";
import { useClients } from "../lib/ClientContext";
import {
  createPayrollRun,
  downloadPayrollSummaryPdf,
  extractErrorMessage,
  extractErrorMessageAsync,
  listPayrollRuns,
} from "../lib/api";
import { Button, Card, CardBody, CardHeader, CardTitle, ErrorText, Field, Input, Select } from "../components/ui";
import { formatMoney } from "../lib/format";
import type { PayrollRun } from "../lib/types";

interface DraftLine {
  employee_name: string;
  gross_pay: string;
}

export default function PayrollPage() {
  const { selectedClient } = useClients();
  const [runs, setRuns] = useState<PayrollRun[]>([]);
  const [periodStart, setPeriodStart] = useState("2026-01-01");
  const [periodEnd, setPeriodEnd] = useState("2026-01-31");
  const [frequency, setFrequency] = useState("monthly");
  const [lines, setLines] = useState<DraftLine[]>([{ employee_name: "", gross_pay: "" }]);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedClient) return;
    listPayrollRuns(selectedClient.id).then(setRuns).catch(() => setRuns([]));
  }, [selectedClient]);

  async function handleDownloadSummary(runId: number) {
    setActionError(null);
    try {
      await downloadPayrollSummaryPdf(runId);
    } catch (err) {
      setActionError(await extractErrorMessageAsync(err));
    }
  }

  function updateLine(index: number, field: keyof DraftLine, value: string) {
    setLines((prev) => prev.map((line, i) => (i === index ? { ...line, [field]: value } : line)));
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedClient) return;
    setSubmitting(true);
    setError(null);
    try {
      await createPayrollRun({
        client_id: selectedClient.id,
        pay_period_start: periodStart,
        pay_period_end: periodEnd,
        frequency,
        lines: lines
          .filter((l) => l.employee_name && l.gross_pay)
          .map((l) => ({ employee_name: l.employee_name, gross_pay: Number(l.gross_pay) })),
      });
      const refreshed = await listPayrollRuns(selectedClient.id);
      setRuns(refreshed);
      setLines([{ employee_name: "", gross_pay: "" }]);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  if (!selectedClient) {
    return <p className="text-sm text-slate-500">Select a client to run payroll.</p>;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Payroll Reconciliation</h1>
        <p className="text-sm text-slate-500">
          {selectedClient.display_name} &middot; PAYE, NIS &amp; Health Surcharge computed automatically per employee
        </p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>New payroll run</CardTitle>
        </CardHeader>
        <CardBody>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
              <Field label="Period start">
                <Input type="date" value={periodStart} onChange={(e) => setPeriodStart(e.target.value)} required />
              </Field>
              <Field label="Period end">
                <Input type="date" value={periodEnd} onChange={(e) => setPeriodEnd(e.target.value)} required />
              </Field>
              <Field label="Frequency">
                <Select value={frequency} onChange={(e) => setFrequency(e.target.value)}>
                  <option value="monthly">Monthly</option>
                  <option value="fortnightly">Fortnightly</option>
                  <option value="weekly">Weekly</option>
                </Select>
              </Field>
            </div>

            <div className="space-y-2">
              <p className="text-xs font-medium text-slate-600">Employees</p>
              {lines.map((line, idx) => (
                <div key={idx} className="flex gap-2">
                  <Input
                    placeholder="Employee name"
                    value={line.employee_name}
                    onChange={(e) => updateLine(idx, "employee_name", e.target.value)}
                  />
                  <Input
                    type="number"
                    placeholder="Gross pay"
                    value={line.gross_pay}
                    onChange={(e) => updateLine(idx, "gross_pay", e.target.value)}
                  />
                  <button
                    type="button"
                    onClick={() => setLines((prev) => prev.filter((_, i) => i !== idx))}
                    className="text-slate-400 hover:text-red-600"
                  >
                    <Trash2 size={18} />
                  </button>
                </div>
              ))}
              <Button
                type="button"
                variant="secondary"
                onClick={() => setLines((prev) => [...prev, { employee_name: "", gross_pay: "" }])}
              >
                <Plus size={14} /> Add employee
              </Button>
            </div>

            <ErrorText message={error} />
            <Button type="submit" disabled={submitting}>
              {submitting ? "Calculating..." : "Run payroll"}
            </Button>
          </form>
        </CardBody>
      </Card>

      <ErrorText message={actionError} />

      {runs.map((run) => (
        <Card key={run.id}>
          <CardHeader className="flex items-center justify-between">
            <CardTitle>
              {run.pay_period_start} → {run.pay_period_end} ({run.frequency})
            </CardTitle>
            <Button variant="secondary" onClick={() => handleDownloadSummary(run.id)}>
              Download summary PDF
            </Button>
          </CardHeader>
          <CardBody className="p-0">
            <table className="w-full text-sm">
              <thead className="border-b border-slate-100 bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-5 py-3">Employee</th>
                  <th className="px-5 py-3">NIS class</th>
                  <th className="px-5 py-3">Gross</th>
                  <th className="px-5 py-3">NIS (Ee)</th>
                  <th className="px-5 py-3">Health Surch. (Ee)</th>
                  <th className="px-5 py-3">PAYE</th>
                  <th className="px-5 py-3">Net pay</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {run.lines.map((line) => (
                  <tr key={line.id}>
                    <td className="px-5 py-3 font-medium text-slate-800">{line.employee_name}</td>
                    <td className="px-5 py-3 text-slate-500">{line.nis_class_name ?? "—"}</td>
                    <td className="px-5 py-3">{formatMoney(line.gross_pay)}</td>
                    <td className="px-5 py-3">{formatMoney(line.nis_employee)}</td>
                    <td className="px-5 py-3">{formatMoney(line.health_surcharge_employee)}</td>
                    <td className="px-5 py-3">{formatMoney(line.paye_deducted)}</td>
                    <td className="px-5 py-3 font-medium">{formatMoney(line.net_pay)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </CardBody>
        </Card>
      ))}
    </div>
  );
}
