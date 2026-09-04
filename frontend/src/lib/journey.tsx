import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
  type ReactNode,
} from "react";
import { journeyApi, type Journey } from "./api";
import { useAuth } from "./auth";

interface JourneyValue {
  journeys: Journey[];
  active: Journey | null;
  loading: boolean;
  error: string | null;
  reload: () => Promise<void>;
  setActiveId: (id: string) => void;
}

const JourneyContext = createContext<JourneyValue | null>(null);

export function JourneyProvider({ children }: { children: ReactNode }) {
  const { status } = useAuth();
  const [journeys, setJourneys] = useState<Journey[]>([]);
  const [activeId, setActiveId] = useState<string | null>(() => localStorage.getItem("pa.journey") ?? null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const loaded = useRef(false);

  const reload = useCallback(async () => {
    if (status !== "authenticated") return;
    setLoading(true);
    try {
      const list = await journeyApi.list();
      setJourneys(list);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : "Journeys could not be loaded.");
    } finally {
      setLoading(false);
    }
  }, [status]);

  useEffect(() => {
    if (loaded.current || status !== "authenticated") return;
    loaded.current = true;
    void reload();
  }, [reload, status]);

  const active = useMemo(() => {
    if (journeys.length === 0) return null;
    return journeys.find((j) => j.id === activeId) ?? journeys.find((j) => j.status !== "archived") ?? journeys[0];
  }, [journeys, activeId]);

  const value = useMemo<JourneyValue>(
    () => ({
      journeys,
      active,
      loading,
      error,
      reload,
      setActiveId: (id: string) => {
        localStorage.setItem("pa.journey", id);
        setActiveId(id);
      },
    }),
    [journeys, active, loading, error, reload],
  );

  return <JourneyContext.Provider value={value}>{children}</JourneyContext.Provider>;
}

export function useJourneys(): JourneyValue {
  const value = useContext(JourneyContext);
  if (!value) throw new Error("useJourneys must be used inside JourneyProvider");
  return value;
}
