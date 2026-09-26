import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../lib/AuthContext";
import { extractErrorMessage } from "../lib/api";
import { Button, Card, CardBody, ErrorText, Field, Input } from "../components/ui";

const DEMO_ACCOUNTS = [
  { email: "employee@example.tt", role: "Individual (Free)" },
  { email: "soletrader@example.tt", role: "Sole Trader (Pro)" },
  { email: "corporate@example.tt", role: "Corporate (Enterprise)" },
  { email: "firmadmin@ctap.tt", role: "Firm Admin" },
  { email: "staff@ctap.tt", role: "Firm Staff" },
  { email: "admin@taxtrin.tt", role: "System Admin" },
];

export default function LoginPage() {
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState("employee@example.tt");
  const [password, setPassword] = useState("TaxTrin2026!");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await login(email, password);
      navigate("/");
    } catch (err) {
      setError(extractErrorMessage(err));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-slate-50 px-4">
      <div className="w-full max-w-md">
        <div className="mb-6 text-center">
          <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-xl bg-brand-600 text-lg font-bold text-white">
            TT
          </div>
          <h1 className="text-xl font-semibold text-slate-900">Sign in to TaxTrin</h1>
          <p className="text-sm text-slate-500">Trinidad &amp; Tobago tax preparation proof of concept</p>
        </div>

        <Card>
          <CardBody>
            <form onSubmit={handleSubmit} className="space-y-4">
              <Field label="Email">
                <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
              </Field>
              <Field label="Password">
                <Input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
              </Field>
              <ErrorText message={error} />
              <Button type="submit" className="w-full" disabled={loading}>
                {loading ? "Signing in..." : "Sign in"}
              </Button>
            </form>
            <p className="mt-4 text-center text-sm text-slate-500">
              No account?{" "}
              <Link to="/register" className="font-medium text-brand-600 hover:underline">
                Register
              </Link>
            </p>
          </CardBody>
        </Card>

        <Card className="mt-4">
          <CardBody>
            <p className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Demo accounts</p>
            <p className="mb-3 text-xs text-slate-500">Password for all: TaxTrin2026!</p>
            <div className="space-y-1.5">
              {DEMO_ACCOUNTS.map((acct) => (
                <button
                  key={acct.email}
                  type="button"
                  onClick={() => {
                    setEmail(acct.email);
                    setPassword("TaxTrin2026!");
                  }}
                  className="flex w-full items-center justify-between rounded-lg px-2 py-1.5 text-left text-xs hover:bg-slate-50"
                >
                  <span className="font-mono text-slate-700">{acct.email}</span>
                  <span className="text-slate-400">{acct.role}</span>
                </button>
              ))}
            </div>
          </CardBody>
        </Card>
      </div>
    </div>
  );
}
