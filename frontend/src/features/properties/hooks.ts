import { useCallback, useEffect, useState } from "react";
import { useJourneys } from "../../lib/journey";
import { MAX_COMPARE, propertyApi, readCompare, writeCompare, type PropertySummary } from "../../lib/properties";

export interface ListState {
  status: "loading" | "ready" | "error" | "no-journey";
  items: PropertySummary[];
  message: string | null;
}

/** Loads the active journey's properties. Server filters are passed through; unknown is never coerced. */
export function useProperties(params: Record<string, string | undefined> = {}) {
  const { active, loading } = useJourneys();
  const [state, setState] = useState<ListState>({ status: "loading", items: [], message: null });
  const key = JSON.stringify(params);

  const reload = useCallback(async () => {
    if (loading) return;
    if (!active) {
      setState({ status: "no-journey", items: [], message: null });
      return;
    }
    setState((s) => ({ ...s, status: s.items.length ? s.status : "loading" }));
    try {
      const items = await propertyApi.list(active.id, JSON.parse(key) as Record<string, string | undefined>);
      setState({ status: "ready", items, message: null });
    } catch (e) {
      setState({ status: "error", items: [], message: e instanceof Error ? e.message : "Properties could not be loaded." });
    }
  }, [active, loading, key]);

  useEffect(() => {
    void reload();
  }, [reload]);

  return { ...state, journey: active, reload };
}

export function useCompareSelection() {
  const [ids, setIds] = useState<string[]>(() => readCompare());
  useEffect(() => {
    const sync = () => setIds(readCompare());
    window.addEventListener("pa.compare", sync);
    window.addEventListener("storage", sync);
    return () => {
      window.removeEventListener("pa.compare", sync);
      window.removeEventListener("storage", sync);
    };
  }, []);
  const toggle = useCallback((id: string) => {
    const current = readCompare();
    if (current.includes(id)) writeCompare(current.filter((x) => x !== id));
    else if (current.length < MAX_COMPARE) writeCompare([...current, id]);
  }, []);
  const remove = useCallback((id: string) => writeCompare(readCompare().filter((x) => x !== id)), []);
  return { ids, toggle, remove, full: ids.length >= MAX_COMPARE };
}
