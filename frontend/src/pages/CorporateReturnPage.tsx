import { useEffect, useMemo, useState } from "react";
import { useClients } from "../lib/ClientContext";
import {
  createCorporateReturn,
  downloadForm500Pdf,
  extractErrorMessage,
  extractErrorMessageAsync,
  listCorporateReturns,
  previewCorporateReturn,
} from "../lib/api";
import { Badge, Button, Card, CardBody, CardHeader, CardTitle, ErrorText, Field, Input, Select } from "../components/ui";
import { formatMoney, titleCase } from "../lib/format";
import type { CorporateReturn, CorporateReturnComputed } from "../lib/types";

const TAX_YEAR = 2026;

function useDebouncedValue<T>(value: T, delayMs: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const handle = setTimeout(() => setDebounced(value), delayMs);
    return () => clearTimeout(handle);
  }, [value, delayMs]);
  return debounced;
}

export default function CorporateReturnPage() {
  const { selectedClient } = useClients();
  const [returns, setReturns] = useState<CorporateReturn[]>([]);
  const [chargeableProfits, setChargeableProfits] = useState("");
  const [grossReceipts, setGrossReceipts] = useState("");
  const [companyCategory, setCompanyCategory] = useState("standard");
  const [dividendPaid, setDividendPaid] = useState("");
  const [installmentsPaid, setInstallmentsPaid] = useState("");
  const [computed, setComputed] = useState<CorporateReturnComputed | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  const debounced = useDebouncedValue(
    { chargeableProfits, grossReceipts, companyCategory, dividendPaid, installmentsPaid },
    350
  );

  useEffect(() => {
    if (!selectedClient) return;
    listCorporateReturns(selectedClient.id).then(setReturns).catch(() => setReturns([]));
  }, [selectedClient]);

  const inputs = useMemo(
    () => ({
      chargeable_profits: Number(debounced.chargeableProfits) || 0,
      gross_receipts: Number(debounced.grossReceipts) || 0,
      company_category: debounced.companyCategory,
      dividend_paid: Number(debounced.dividendPaid) || 0,
      quarterly_installments_paid: Number(debounced.installmentsPaid) || 0,
    }),
    [debounced]
  );

  useEffect(() => {
    previewCorporateReturn({ tax_year: TAX_YEAR, inputs })
      .then(setComputed)
      .catch(() => setComputed(null));
  }, [inputs]);

  async function handleSave() {
    if (!selectedClient) return;
    setSubmitting(true);
    setError(null);
    try {
      await createCorporateReturn({ client_id: selectedClient.id, tax_year: TAX_YEAR, inputs });
      const refreshed = await listCorporateReturns(selectedClient.id);
      setReturns(refreshed);
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDownloadPdf(returnId: number) {
    setError(null);
    try {
      await downloadForm500Pdf(returnId);
    } catch (err) {
      setError(await extractErrorMessageAsync(err));
    }
  }

  if (!selectedClient) {
    return <p className="text-sm text-slate-500">Select a client to prepare a Form 500 corporation tax return.</p>;
  }

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
      <div className="space-y-6 lg:col-span-2">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Form 500 — Corporation Tax Return</h1>
          <p className="text-sm text-slate-500">{selectedClient.display_name} &middot; Tax Year {TAX_YEAR}</p>
        </div>

        <Card>
          <CardHeader>
            <CardTitle>Income &amp; category</CardTitle>
          </CardHeader>
          <CardBody className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <Field label="Chargeable profits (TT$)">
              <Input type="number" value={chargeableProfits} onChange={(e) => setChargeableProfits(e.target.value)} />
            </Field>
            <Field label="Gross receipts (for Business/Green Fund Levy)">
              <Input type="number" value={grossReceipts} onChange={(e) => setGrossReceipts(e.target.value)} />
            </Field>
            <Field label="Company category">
              <Select value={companyCategory} onChange={(e) => setCompanyCategory(e.target.value)}>
                <option value="standard">Standard (30%)</option>
                <option value="bank_or_petrochemical">Bank / Petrochemical (35%)</option>
                <option value="sme_stock_exchange">SME listed on stock exchange</option>
              </Select>
            </Field>
          </CardBody>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Dividends &amp; instalments</CardTitle>
          </CardHeader>
          <CardBody className="grid grid-cols-1 gap-4 md:grid-cols-2">
            <Field label="Dividends paid this year (TT$)">
              <Input type="number" value={dividendPaid} onChange={(e) => setDividendPaid(e.target.value)} />
            </Field>
            <Field label="Quarterly instalments already paid (TT$)">
              <Input type="number" value={installmentsPaid} onChange={(e) => setInstallmentsPaid(e.target.value)} />
            </Field>
          </CardBody>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Filed returns</CardTitle>
          </CardHeader>
          <CardBody className="p-0">
            <table className="w-full text-sm">
              <thead className="border-b border-slate-100 bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
                <tr>
                  <th className="px-5 py-3">Tax year</th>
                  <th className="px-5 py-3">Corp. tax</th>
                  <th className="px-5 py-3">Balance</th>
                  <th className="px-5 py-3">Status</th>
                  <th className="px-5 py-3" />
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100">
                {returns.map((r) => (
                  <tr key={r.id}>
                    <td className="px-5 py-3">{r.tax_year}</td>
                    <td className="px-5 py-3">{formatMoney(r.computed.corporation_tax)}</td>
                    <td className="px-5 py-3 font-medium">
                      {formatMoney(Math.abs(r.refund_or_balance_due))} {r.computed.is_refund ? "(refund)" : "due"}
                    </td>
                    <td className="px-5 py-3">
                      <Badge>{titleCase(r.status)}</Badge>
                    </td>
                    <td className="px-5 py-3 text-right">
                      <Button variant="secondary" onClick={() => handleDownloadPdf(r.id)}>
                        PDF
                      </Button>
                    </td>
                  </tr>
                ))}
                {returns.length === 0 && (
                  <tr>
                    <td colSpan={5} className="px-5 py-6 text-center text-slate-400">
                      No corporate returns filed yet.
                    </td>
                  </tr>
                )}
              </tbody>
            </table>
          </CardBody>
        </Card>
      </div>

      <div>
        <Card className="sticky top-6">
          <CardHeader>
            <CardTitle>Live estimate</CardTitle>
          </CardHeader>
          <CardBody>
            {computed ? (
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
                    <dt className="text-slate-500">Corporation tax ({(computed.rate_applied * 100).toFixed(0)}%)</dt>
                    <dd className="font-medium text-slate-800">{formatMoney(computed.corporation_tax)}</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-slate-500">Business Levy</dt>
                    <dd className="font-medium text-slate-800">
                      {computed.business_levy.business_levy_exempt ? "Exempt" : formatMoney(computed.business_levy.business_levy_payable)}
                    </dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-slate-500">Green Fund Levy</dt>
                    <dd className="font-medium text-slate-800">{formatMoney(computed.business_levy.green_fund_levy)}</dd>
                  </div>
                  <div className="flex justify-between">
                    <dt className="text-slate-500">Dividend withholding tax</dt>
                    <dd className="font-medium text-slate-800">{formatMoney(computed.dividend_withholding_tax)}</dd>
                  </div>
                  <div className="flex justify-between border-t border-slate-100 pt-2">
                    <dt className="text-slate-500">Total statutory liability</dt>
                    <dd className="font-medium text-slate-800">{formatMoney(computed.total_statutory_liability)}</dd>
                  </div>
                </dl>
              </>
            ) : (
              <p className="text-sm text-slate-500">Enter figures to see your estimate.</p>
            )}
            <ErrorText message={error} />
            <Button className="mt-4 w-full" onClick={handleSave} disabled={submitting}>
              {submitting ? "Saving..." : "Save this return"}
            </Button>
          </CardBody>
        </Card>
      </div>
    </div>
  );
}
