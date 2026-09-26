import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { ArrowRight, FileText, Receipt, UploadCloud, Wallet } from "lucide-react";
import { useAuth } from "../lib/AuthContext";
import { useClients } from "../lib/ClientContext";
import { listExportLogs, listIndividualReturns } from "../lib/api";
import { Badge, Card, CardBody, CardHeader, CardTitle } from "../components/ui";
import { formatMoney, titleCase } from "../lib/format";
import type { ETaxExportLog, IndividualReturn } from "../lib/types";

const TIER_FEATURES: Record<string, string[]> = {
  free: ["1 TD4 slip / year", "Form 440 preview on screen", "e-Tax export locked"],
  pro: ["Unlimited TD4 processing", "VAT 200 filing", "Business Levy vs Income Tax compare", "e-Tax export unlocked"],
  enterprise: ["Everything in Pro", "Form 500 corporate filing", "Payroll reconciliation", "Bulk TD4 supplementary export"],
  firm: ["Multi-client dashboard", "Staff assignment workflows", "Bulk export for all clients", "Client sign-off tracking"],
};

export default function DashboardPage() {
  const { user } = useAuth();
  const { selectedClient, clients } = useClients();
  const [returns, setReturns] = useState<IndividualReturn[]>([]);
  const [logs, setLogs] = useState<ETaxExportLog[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!selectedClient) {
      setLoading(false);
      return;
    }
    setLoading(true);
    Promise.all([listIndividualReturns(selectedClient.id).catch(() => []), listExportLogs(selectedClient.id).catch(() => [])])
      .then(([r, l]) => {
        setReturns(r);
        setLogs(l);
      })
      .finally(() => setLoading(false));
  }, [selectedClient]);

  const latestReturn = returns[returns.length - 1];
  const tier = user?.subscription_tier ?? "free";

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">Welcome, {user?.full_name}</h1>
        <p className="text-sm text-slate-500">
          {clients.length > 1 ? `Managing ${clients.length} clients` : selectedClient?.display_name ?? "No client selected"}
        </p>
      </div>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <Card>
          <CardBody>
            <div className="flex items-center gap-3">
              <div className="rounded-lg bg-brand-50 p-2 text-brand-600">
                <Receipt size={20} />
              </div>
              <div>
                <p className="text-xs text-slate-500">Latest refund / balance</p>
                <p className="text-lg font-semibold text-slate-900">
                  {latestReturn ? formatMoney(Math.abs(latestReturn.refund_or_balance_due)) : "—"}
                </p>
                {latestReturn && (
                  <Badge tone={latestReturn.computed.is_refund ? "green" : "amber"}>
                    {latestReturn.computed.is_refund ? "Refund due" : "Balance due"}
                  </Badge>
                )}
              </div>
            </div>
          </CardBody>
        </Card>

        <Card>
          <CardBody>
            <div className="flex items-center gap-3">
              <div className="rounded-lg bg-blue-50 p-2 text-blue-600">
                <UploadCloud size={20} />
              </div>
              <div>
                <p className="text-xs text-slate-500">e-Tax exports generated</p>
                <p className="text-lg font-semibold text-slate-900">{logs.length}</p>
              </div>
            </div>
          </CardBody>
        </Card>

        <Card>
          <CardBody>
            <div className="flex items-center gap-3">
              <div className="rounded-lg bg-amber-50 p-2 text-amber-600">
                <Wallet size={20} />
              </div>
              <div>
                <p className="text-xs text-slate-500">Subscription tier</p>
                <p className="text-lg font-semibold text-slate-900">{titleCase(tier)}</p>
              </div>
            </div>
          </CardBody>
        </Card>
      </div>

      <div className="grid grid-cols-1 gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader>
            <CardTitle>Recent activity</CardTitle>
          </CardHeader>
          <CardBody>
            {loading ? (
              <p className="text-sm text-slate-500">Loading...</p>
            ) : logs.length === 0 ? (
              <p className="text-sm text-slate-500">No e-Tax exports generated yet.</p>
            ) : (
              <ul className="divide-y divide-slate-100">
                {logs.slice(0, 6).map((log) => (
                  <li key={log.id} className="flex items-center justify-between py-2.5 text-sm">
                    <div className="flex items-center gap-2">
                      <FileText size={16} className="text-slate-400" />
                      <span className="text-slate-700">{log.file_name}</span>
                    </div>
                    <Badge tone={log.validation_status === "passed" ? "green" : log.validation_status === "failed" ? "red" : "amber"}>
                      {titleCase(log.validation_status)}
                    </Badge>
                  </li>
                ))}
              </ul>
            )}
            <Link to="/export-center" className="mt-3 inline-flex items-center gap-1 text-sm font-medium text-brand-600 hover:underline">
              Go to Export Center <ArrowRight size={14} />
            </Link>
          </CardBody>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Your plan includes</CardTitle>
          </CardHeader>
          <CardBody>
            <ul className="space-y-2 text-sm text-slate-700">
              {TIER_FEATURES[tier].map((feature) => (
                <li key={feature} className="flex items-start gap-2">
                  <span className="mt-1 h-1.5 w-1.5 flex-shrink-0 rounded-full bg-brand-500" />
                  {feature}
                </li>
              ))}
            </ul>
            <Link to="/wizard" className="mt-4 inline-flex items-center gap-1 text-sm font-medium text-brand-600 hover:underline">
              Start / continue tax wizard <ArrowRight size={14} />
            </Link>
          </CardBody>
        </Card>
      </div>
    </div>
  );
}
