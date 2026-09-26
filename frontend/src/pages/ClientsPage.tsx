import { useState } from "react";
import { Users, Plus } from "lucide-react";
import { useClients } from "../lib/ClientContext";
import { createClient, extractErrorMessage } from "../lib/api";
import { Badge, Button, Card, CardBody, CardHeader, CardTitle, ErrorText, Field, Input, Select } from "../components/ui";
import { titleCase } from "../lib/format";
import type { ClientType } from "../lib/types";

const STATUS_TONE: Record<string, "slate" | "green" | "amber" | "red" | "blue"> = {
  draft: "slate",
  pending_review: "amber",
  approved: "blue",
  exported: "blue",
  filed: "green",
};

export default function ClientsPage() {
  const { clients, selectedClient, selectClient, refresh } = useClients();
  const [showForm, setShowForm] = useState(false);
  const [displayName, setDisplayName] = useState("");
  const [clientType, setClientType] = useState<ClientType>("individual");
  const [birNumber, setBirNumber] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function handleCreate(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setSaving(true);
    try {
      await createClient({ display_name: displayName, client_type: clientType, bir_number: birNumber || undefined });
      setDisplayName("");
      setBirNumber("");
      setShowForm(false);
      await refresh();
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setSaving(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">Client Portfolio</h1>
          <p className="text-sm text-slate-500">Manage clients, filing status, and staff assignments.</p>
        </div>
        <Button onClick={() => setShowForm((v) => !v)}>
          <Plus size={16} /> Add client
        </Button>
      </div>

      {showForm && (
        <Card>
          <CardHeader>
            <CardTitle>New client</CardTitle>
          </CardHeader>
          <CardBody>
            <form onSubmit={handleCreate} className="grid grid-cols-1 gap-4 md:grid-cols-3">
              <Field label="Display name">
                <Input value={displayName} onChange={(e) => setDisplayName(e.target.value)} required />
              </Field>
              <Field label="Client type">
                <Select value={clientType} onChange={(e) => setClientType(e.target.value as ClientType)}>
                  <option value="individual">Individual</option>
                  <option value="sole_trader">Sole Trader</option>
                  <option value="partnership">Partnership</option>
                  <option value="corporate">Corporate</option>
                </Select>
              </Field>
              <Field label="BIR number (optional)">
                <Input value={birNumber} onChange={(e) => setBirNumber(e.target.value)} placeholder="e.g. 1234567" />
              </Field>
              <div className="md:col-span-3">
                <ErrorText message={error} />
                <Button type="submit" disabled={saving}>
                  {saving ? "Saving..." : "Create client"}
                </Button>
              </div>
            </form>
          </CardBody>
        </Card>
      )}

      <Card>
        <CardBody className="p-0">
          <table className="w-full text-sm">
            <thead className="border-b border-slate-100 bg-slate-50 text-left text-xs uppercase tracking-wide text-slate-500">
              <tr>
                <th className="px-5 py-3">Client</th>
                <th className="px-5 py-3">Type</th>
                <th className="px-5 py-3">BIR #</th>
                <th className="px-5 py-3">Filing status</th>
                <th className="px-5 py-3">Sign-off</th>
                <th className="px-5 py-3" />
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {clients.map((client) => (
                <tr key={client.id} className={client.id === selectedClient?.id ? "bg-brand-50/40" : undefined}>
                  <td className="flex items-center gap-2 px-5 py-3 font-medium text-slate-900">
                    <Users size={14} className="text-slate-400" />
                    {client.display_name}
                  </td>
                  <td className="px-5 py-3 text-slate-600">{titleCase(client.client_type)}</td>
                  <td className="px-5 py-3 font-mono text-xs text-slate-500">{client.bir_number ?? "—"}</td>
                  <td className="px-5 py-3">
                    <Badge tone={STATUS_TONE[client.filing_status] ?? "slate"}>{titleCase(client.filing_status)}</Badge>
                  </td>
                  <td className="px-5 py-3">{client.client_signed_off ? <Badge tone="green">Signed off</Badge> : <Badge>Pending</Badge>}</td>
                  <td className="px-5 py-3 text-right">
                    <Button variant="secondary" onClick={() => selectClient(client.id)}>
                      {client.id === selectedClient?.id ? "Active" : "Switch to"}
                    </Button>
                  </td>
                </tr>
              ))}
              {clients.length === 0 && (
                <tr>
                  <td colSpan={6} className="px-5 py-8 text-center text-slate-400">
                    No clients yet. Add your first client above.
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
