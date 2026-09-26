import { Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./lib/AuthContext";
import { ClientProvider } from "./lib/ClientContext";
import AppShell from "./components/AppShell";
import ProtectedRoute from "./components/ProtectedRoute";
import LoginPage from "./pages/LoginPage";
import RegisterPage from "./pages/RegisterPage";
import DashboardPage from "./pages/DashboardPage";
import ClientsPage from "./pages/ClientsPage";
import WizardPage from "./pages/WizardPage";
import CorporateReturnPage from "./pages/CorporateReturnPage";
import VAT200Page from "./pages/VAT200Page";
import PayrollPage from "./pages/PayrollPage";
import ExportCenterPage from "./pages/ExportCenterPage";
import AdminTaxConfigPage from "./pages/AdminTaxConfigPage";

function ShellWithClientContext() {
  // ClientProvider fetches /clients on mount, so it must only ever render
  // once ProtectedRoute has confirmed a logged-in user -- otherwise it fires
  // an authenticated API call before a token exists.
  return (
    <ClientProvider>
      <AppShell />
    </ClientProvider>
  );
}

function AuthenticatedApp() {
  return (
    <Routes>
      <Route element={<ProtectedRoute />}>
        <Route element={<ShellWithClientContext />}>
          <Route index element={<DashboardPage />} />
          <Route path="clients" element={<ClientsPage />} />
          <Route path="wizard" element={<WizardPage />} />
          <Route path="corporate" element={<CorporateReturnPage />} />
          <Route path="vat200" element={<VAT200Page />} />
          <Route path="payroll" element={<PayrollPage />} />
          <Route path="export-center" element={<ExportCenterPage />} />
          <Route path="admin/tax-config" element={<AdminTaxConfigPage />} />
        </Route>
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route path="/*" element={<AuthenticatedApp />} />
      </Routes>
    </AuthProvider>
  );
}
