import { LayoutDashboard, LogOut, Receipt, Settings, Users, FileSpreadsheet, Wallet, UploadCloud, Building2 } from "lucide-react";
import type { LucideIcon } from "lucide-react";
import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../lib/AuthContext";
import { useClients } from "../lib/ClientContext";
import { titleCase } from "../lib/format";
import { Select } from "./ui";

interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  roles?: string[];
}

const NAV_ITEMS: NavItem[] = [
  { to: "/", label: "Dashboard", icon: LayoutDashboard },
  { to: "/clients", label: "Clients", icon: Users, roles: ["firm_admin", "firm_staff", "system_admin"] },
  { to: "/wizard", label: "Tax Wizard", icon: Receipt },
  { to: "/corporate", label: "Form 500 (Corporate)", icon: Building2, roles: ["corporate", "firm_admin", "firm_staff", "system_admin"] },
  { to: "/vat200", label: "VAT 200", icon: FileSpreadsheet },
  { to: "/payroll", label: "Payroll", icon: Wallet },
  { to: "/export-center", label: "e-Tax Export Center", icon: UploadCloud },
  { to: "/admin/tax-config", label: "Tax Configuration", icon: Settings, roles: ["system_admin"] },
];

export default function AppShell() {
  const { user, logout } = useAuth();
  const { clients, selectedClient, selectClient } = useClients();
  const isFirmUser = user?.role === "firm_admin" || user?.role === "firm_staff" || user?.role === "system_admin";

  const visibleItems = NAV_ITEMS.filter((item) => !item.roles || (user && item.roles.includes(user.role)));

  return (
    <div className="flex h-screen overflow-hidden">
      <aside className="flex h-full w-64 flex-shrink-0 flex-col overflow-y-auto border-r border-slate-200 bg-white">
        <div className="flex items-center gap-2 border-b border-slate-100 px-5 py-4">
          <div className="flex h-8 w-8 items-center justify-center rounded-lg bg-brand-600 text-sm font-bold text-white">TT</div>
          <div>
            <p className="text-sm font-semibold text-slate-900">TaxTrin</p>
            <p className="text-xs text-slate-500">Trinidad &amp; Tobago POC</p>
          </div>
        </div>

        {isFirmUser && clients.length > 0 && (
          <div className="border-b border-slate-100 px-4 py-3">
            <label className="mb-1 block text-xs font-medium text-slate-500">Active client</label>
            <Select value={selectedClient?.id ?? ""} onChange={(e) => selectClient(Number(e.target.value))}>
              {clients.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.display_name}
                </option>
              ))}
            </Select>
          </div>
        )}

        <nav className="flex-1 space-y-1 px-3 py-4">
          {visibleItems.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              className={({ isActive }) =>
                `flex items-center gap-3 rounded-lg px-3 py-2 text-sm font-medium transition-colors ${
                  isActive ? "bg-brand-50 text-brand-700" : "text-slate-600 hover:bg-slate-100"
                }`
              }
            >
              <item.icon size={18} />
              {item.label}
            </NavLink>
          ))}
        </nav>

        <div className="border-t border-slate-100 px-4 py-4">
          <p className="truncate text-sm font-medium text-slate-900">{user?.full_name}</p>
          <p className="text-xs text-slate-500">
            {user ? titleCase(user.role) : ""} &middot; {user ? titleCase(user.subscription_tier) : ""} tier
          </p>
          <button
            onClick={logout}
            className="mt-3 flex items-center gap-2 text-sm font-medium text-slate-500 hover:text-red-600"
          >
            <LogOut size={16} /> Sign out
          </button>
        </div>
      </aside>

      <main className="h-full flex-1 overflow-y-auto bg-slate-50 p-8">
        <Outlet />
      </main>
    </div>
  );
}
