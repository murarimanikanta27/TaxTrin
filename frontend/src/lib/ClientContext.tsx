import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { listClients } from "./api";
import type { Client } from "./types";

interface ClientContextValue {
  clients: Client[];
  selectedClient: Client | null;
  selectClient: (clientId: number) => void;
  loading: boolean;
  error: string | null;
  refresh: () => Promise<void>;
}

const ClientContext = createContext<ClientContextValue | undefined>(undefined);

const STORAGE_KEY = "taxtrin.selectedClientId";

export function ClientProvider({ children }: { children: ReactNode }) {
  const [clients, setClients] = useState<Client[]>([]);
  const [selectedId, setSelectedId] = useState<number | null>(() => {
    const stored = localStorage.getItem(STORAGE_KEY);
    return stored ? Number(stored) : null;
  });
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await listClients();
      setClients(data);
      setSelectedId((current) => {
        if (current && data.some((c) => c.id === current)) return current;
        return data[0]?.id ?? null;
      });
    } catch (err) {
      setError(err instanceof Error ? err.message : "Failed to load clients");
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  useEffect(() => {
    if (selectedId) localStorage.setItem(STORAGE_KEY, String(selectedId));
  }, [selectedId]);

  const selectClient = useCallback((clientId: number) => setSelectedId(clientId), []);

  const selectedClient = useMemo(() => clients.find((c) => c.id === selectedId) ?? null, [clients, selectedId]);

  const value = useMemo(
    () => ({ clients, selectedClient, selectClient, loading, error, refresh }),
    [clients, selectedClient, selectClient, loading, error, refresh]
  );

  return <ClientContext.Provider value={value}>{children}</ClientContext.Provider>;
}

export function useClients(): ClientContextValue {
  const ctx = useContext(ClientContext);
  if (!ctx) throw new Error("useClients must be used within a ClientProvider");
  return ctx;
}
