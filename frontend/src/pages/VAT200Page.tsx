import { useEffect, useState } from "react";
import { useClients } from "../lib/ClientContext";
import {
  createVAT200Return,
  downloadVAT200Pdf,
  exportVAT200Csv,
  extractErrorMessage,
  extractErrorMessageAsync,
  listVAT200Returns,
} from "../lib/api";
import { Badge, Button, Card, CardBody, CardHeader, CardTitle, ErrorText, Field, Input } from "../components/ui";
import { formatMoney, titleCase } from "../lib/format";
import type { VAT200Return } from "../lib/types";

function defaultPeriod(): { start: string; end: string } {
  const now = new Date();
  const month = now.getMonth(); // 0-indexed
  const bimonthlyStartMonth = month - (month % 2);
  const start = new Date(now.getFullYear(), bimonthlyStartMonth, 1);
  const end = new Date(now.getFullYear(), bimonthlyStartMonth + 2, 0);
  const fmt = (d: Date) => d.toISOString().slice(0, 10);
  return { start: fmt(start), end: fmt(end) };
}

export default function VAT200Page() {
  const { selectedClient } = useClients();
  const [returns, setReturns] = useState<VAT200Return[]>([]);
  const [periodStart, setPeriodStart] = useState(defaultPeriod().start);
  const [periodEnd, setPeriodEnd] = useState(defaultPeriod().end);
  const [standardSales, setStandardSales] = useState("");
  const [zeroRatedSales, setZeroRatedSales] = useState("");
  const [exemptSales, setExemptSales] = useState("");
  const [inputVat, setInputVat] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  useEffect(() => {
    if (!selectedClient) return;
    listVAT200Returns(selectedClient.id).then(setReturns).catch(() => setReturns([]));
  }, [selectedClient]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!selectedClient) return;
    setSubmitting(true);
    setError(null);
    try {
      await createVAT200Return({
        client_id: selectedClient.id,
        period_start: periodStart,
        period_end: periodEnd,
        standard_rated_sales: Number(standardSales) || 0,
        zero_rated_sales: Number(zeroRatedSales) || 0,
        exempt_sales: Number(exemptSales) || 0,
        input_vat_paid: Number(inputVat) || 0,
      });
      const refreshed = await listVAT200Returns(selectedClient.id);
      setReturns(refreshed);
      setStandardSales("");
      setZeroRatedSales("");
      setExemptSales("");
      setInputVat("");
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDownloadPdf(returnId: number) {
    setActionError(null);
    try {
      await downloadVAT200Pdf(returnId);
    } catch (err) {
      setActionError(await extractErrorMessageAsync(err));
    }
  }

  async function handleExportCsv(returnId: number) {
    setActionError(null);
    try {
      await exportVAT200Csv(returnId);
    } catch (err) {
      setActionError(await extractErrorMessageAsync(err));
    }
  }

  if (!selectedClient) {
    return <p className="text-sm text-slate-500">Select a client to file a VAT 200 return.</p>;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">VAT 200 — Bimonthly Return</h1>
        <p className="text-sm text-slate-500">{selectedClient.display_name}</p>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>New VAT 200 period</CardTitle>
        </CardHeader>
        <CardBody>
          <form onSubmit={handleSubmit} className="grid grid-cols-1 gap-4 md:grid-cols-3">
            <Field label="Period start">
              <Input type="date" value={periodStart} onChange={(e) => setPeriodStart(e.target.value)} required />
            </Field>
            <Field label="Period end">
              <Input type="date" value={periodEnd} onChange={(e) => setPeriodEnd(e.target.value)} required />
            </Field>
            <div />
            <Field label="Standard-rated sales (12.5%)">
              <Input type="number" min={0} value={standardSales} onChange={(e) => setStandardSales(e.target.value)} />
            </Field>
            <Field label="Zero-rated sales">
              <Input type="number" min={0} value={zeroRatedSales} onChange={(e) => setZeroRatedSales(e.target.value)} />
            </Field>
            <Field label="Exempt sales">
              <Input type="number" min={0} value={exemptSales} onChange={(e) => setExemptSales(e.target.value)} />
            </Field>
            <Field label="Input VAT paid (on purchases)">
              <Input type="number" min={0} value={inputVat} onChange={(e) => setInputVat(e.target.value)} />
            </Field>
            <div className="md:col-span-3">
              <ErrorText message={error} />
              <Button type="submit" disabled={submitting}>
                {submitting ? "Calculating..." : "Calculate & save return"}
              </Button>
            </div>
          </form>
        </CardBody>
      </Card>

      <Card>
        <CardHeader>
          <CardTitle>Filed periods</CardTitle>
        </CardHeader>
        <CardBody className="p-0">
          {actionError && (
            <div className="px-5 pt-4">
              <ErrorText message={actionError} />
            </div>
          )}
          <table className="w-full text-sm">
            <thead className="border-b border-slate-100 bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-5 py-3">Period</th>
                <th className="px-5 py-3">Output VAT</th>
                <th className="px-5 py-3">Input VAT</th>
                <th className="px-5 py-3">Net</th>
                <th className="px-5 py-3">Status</th>
                <th className="px-5 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {returns.map((r) => (
                <tr key={r.id}>
                  <td className="px-5 py-3 text-slate-700">
                    {r.period_start} → {r.period_end}
                  </td>
                  <td className="px-5 py-3">{formatMoney(r.output_vat)}</td>
                  <td className="px-5 py-3">{formatMoney(r.input_vat)}</td>
                  <td className="px-5 py-3 font-medium">
                    {formatMoney(Math.abs(r.net_vat_payable))} {r.net_vat_payable < 0 ? "(refund)" : "payable"}
                  </td>
                  <td className="px-5 py-3">
                    <Badge>{titleCase(r.status)}</Badge>
                  </td>
                  <td className="px-5 py-3 text-right">
                    <div className="flex justify-end gap-2">
                      <Button variant="secondary" onClick={() => handleDownloadPdf(r.id)}>
                        PDF
                      </Button>
                      <Button variant="secondary" onClick={() => handleExportCsv(r.id)}>
                        e-Tax CSV
                      </Button>
                    </div>
                  </td>
                </tr>
              ))}
              {returns.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-5 py-8 text-center text-slate-400">
                    No VAT 200 returns filed yet.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </CardBody>
      </Card>
    </div>
  );
}
