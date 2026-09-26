import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../lib/AuthContext";
import { extractErrorMessage } from "../lib/api";
import { Button, Card, CardBody, ErrorText, Field, Input, Select } from "../components/ui";

export default function RegisterPage() {
  const { register } = useAuth();
  const navigate = useNavigate();
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [role, setRole] = useState("individual");
  const [firmName, setFirmName] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      await register({ email, password, full_name: fullName, role, firm_name: role === "firm_admin" ? firmName : undefined });
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
          <h1 className="text-xl font-semibold text-slate-900">Create your TaxTrin account</h1>
        </div>

        <Card>
          <CardBody>
            <form onSubmit={handleSubmit} className="space-y-4">
              <Field label="Full name">
                <Input value={fullName} onChange={(e) => setFullName(e.target.value)} required />
              </Field>
              <Field label="Email">
                <Input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
              </Field>
              <Field label="Password">
                <Input type="password" minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} required />
              </Field>
              <Field label="Account type">
                <Select value={role} onChange={(e) => setRole(e.target.value)}>
                  <option value="individual">Individual (Free / PAYE employee)</option>
                  <option value="sole_trader">Sole Trader / Small Business</option>
                  <option value="corporate">Corporate / Enterprise</option>
                  <option value="firm_admin">Accounting Firm (creates a new firm)</option>
                </Select>
              </Field>
              {role === "firm_admin" && (
                <Field label="Firm name">
                  <Input value={firmName} onChange={(e) => setFirmName(e.target.value)} required />
                </Field>
              )}
              <ErrorText message={error} />
              <Button type="submit" className="w-full" disabled={loading}>
                {loading ? "Creating account..." : "Create account"}
              </Button>
            </form>
            <p className="mt-4 text-center text-sm text-slate-500">
              Already have an account?{" "}
              <Link to="/login" className="font-medium text-brand-600 hover:underline">
                Sign in
              </Link>
            </p>
          </CardBody>
        </Card>
      </div>
    </div>
  );
}
