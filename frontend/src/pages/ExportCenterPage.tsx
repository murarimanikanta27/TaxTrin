import { useEffect, useState } from "react";
import { AlertTriangle, CheckCircle2, FileDown, Info } from "lucide-react";
import { useClients } from "../lib/ClientContext";
import { exportTD4Csv, extractErrorMessageAsync, listExportLogs, listTD4 } from "../lib/api";
import { Badge, Button, Card, CardBody, CardHeader, CardTitle, ErrorText } from "../components/ui";
import { titleCase } from "../lib/format";
import type { ETaxExportLog } from "../lib/types";

const TAX_YEAR = 2026;

const STATUS_META: Record<string, { tone: "green" | "amber" | "red" | "slate"; icon: typeof CheckCircle2 }> = {
  passed: { tone: "green", icon: CheckCircle2 },
  unverified_format: { tone: "amber", icon: AlertTriangle },
  failed: { tone: "red", icon: AlertTriangle },
  pending: { tone: "slate", icon: Info },
};

export default function ExportCenterPage() {
  const { selectedClient } = useClients();
  const [logs, setLogs] = useState<ETaxExportLog[]>([]);
  const [td4Count, setTd4Count] = useState(0);
  const [error, setError] = useState<string | null>(null);
  const [exporting, setExporting] = useState(false);

  useEffect(() => {
    if (!selectedClient) return;
    listExportLogs(selectedClient.id).then(setLogs).catch(() => setLogs([]));
    listTD4(selectedClient.id, TAX_YEAR)
      .then((t) => setTd4Count(t.length))
      .catch(() => setTd4Count(0));
  }, [selectedClient]);

  async function handleExportTd4() {
    if (!selectedClient) return;
    setExporting(true);
    setError(null);
    try {
      await exportTD4Csv(selectedClient.id, TAX_YEAR);
      const refreshed = await listExportLogs(selectedClient.id);
      setLogs(refreshed);
    } catch (err) {
      setError(await extractErrorMessageAsync(err));
    } finally {
      setExporting(false);
    }
  }

  if (!selectedClient) {
    return <p className="text-sm text-slate-500">Select a client to view their e-Tax export history.</p>;
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold text-slate-900">e-Tax File Export Center</h1>
        <p className="text-sm text-slate-500">{selectedClient.display_name}</p>
      </div>

      <Card className="border-amber-200 bg-amber-50">
        <CardBody className="flex items-start gap-3">
          <AlertTriangle size={18} className="mt-0.5 flex-shrink-0 text-amber-600" />
          <div className="text-sm text-amber-800">
            <p className="font-medium">About format confidence</p>
            <p className="mt-1">
              The TD4 Supplementary CSV format below is transcribed directly from IRD&apos;s published guide and matches
              the real e-Tax upload schema. VAT 200 uploads and Non-Logged-In Return XML/JSON are best-effort
              placeholders — no public BIR specification for those formats was found, so they are flagged{" "}
              <Badge tone="amber">Unverified format</Badge> until confirmed against a real sample file from IRD.
            </p>
          </div>
        </CardBody>
      </Card>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <Card>
          <CardHeader>
            <CardTitle>TD4 Supplementary CSV</CardTitle>
          </CardHeader>
          <CardBody>
            <p className="text-sm text-slate-600">
              {td4Count} TD4 record{td4Count === 1 ? "" : "s"} on file for {TAX_YEAR}. Generates the exact 27-field,
              no-header CSV format for e-Tax&apos;s PAYE Annual Return supplementary upload.
            </p>
            <Badge tone="green" className="mt-2">
              BIR format verified
            </Badge>
            <ErrorText message={error} />
            <Button className="mt-4" onClick={handleExportTd4} disabled={exporting || td4Count === 0}>
              <FileDown size={16} /> {exporting ? "Generating..." : "Export TD4 CSV"}
            </Button>
          </CardBody>
        </Card>

        <Card>
          <CardHeader>
            <CardTitle>Step-by-step e-Tax upload instructions</CardTitle>
          </CardHeader>
          <CardBody>
            <ol className="list-decimal space-y-1.5 pl-4 text-sm text-slate-600">
              <li>
                Log in to <span className="font-mono text-xs">etax.ird.gov.tt</span> with your ttconnect ID.
              </li>
              <li>Navigate to PAYE Annual Return → TD4 Supplementary Records.</li>
              <li>Choose &quot;Add by file upload&quot; and attach the downloaded .csv file.</li>
              <li>Review the record count matches what you expect, then submit.</li>
            </ol>
          </CardBody>
        </Card>
      </div>

      <Card>
        <CardHeader>
          <CardTitle>Export history</CardTitle>
        </CardHeader>
        <CardBody className="p-0">
          <table className="w-full text-sm">
            <thead className="border-b border-slate-100 bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-5 py-3">File</th>
                <th className="px-5 py-3">Type</th>
                <th className="px-5 py-3">Rows</th>
                <th className="px-5 py-3">Validation</th>
                <th className="px-5 py-3">Generated</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {logs.map((log) => {
                const meta = STATUS_META[log.validation_status] ?? STATUS_META.pending;
                const Icon = meta.icon;
                return (
                  <tr key={log.id}>
                    <td className="px-5 py-3 font-mono text-xs text-slate-700">{log.file_name}</td>
                    <td className="px-5 py-3 text-slate-600">{titleCase(log.export_type)}</td>
                    <td className="px-5 py-3">{log.row_count ?? "—"}</td>
                    <td className="px-5 py-3">
                      <Badge tone={meta.tone}>
                        <span className="inline-flex items-center gap-1">
                          <Icon size={12} /> {titleCase(log.validation_status)}
                        </span>
                      </Badge>
                    </td>
                    <td className="px-5 py-3 text-slate-500">{new Date(log.created_at).toLocaleString()}</td>
                  </tr>
                );
              })}
              {logs.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-5 py-8 text-center text-slate-400">
                    No exports generated yet.
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
