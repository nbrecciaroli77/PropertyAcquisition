import { useCallback, useEffect, useState } from "react";
import { ApiError } from "../../lib/api";
import { useJourneys } from "../../lib/journey";
import { propertyApi, type PropertyDetail } from "../../lib/properties";

export interface DetailState {
  status: "loading" | "ready" | "not-found" | "error" | "no-journey";
  data: PropertyDetail | null;
  message: string | null;
  busy: boolean;
  notice: string | null;
}

/** Loads one property and exposes a `mutate` wrapper that surfaces 409 conflicts as reload-able notices. */
export function usePropertyDetail(id: string) {
  const { active, loading } = useJourneys();
  const [state, setState] = useState<DetailState>({ status: "loading", data: null, message: null, busy: false, notice: null });

  const load = useCallback(async () => {
    if (loading) return;
    if (!active) {
      setState((s) => ({ ...s, status: "no-journey" }));
      return;
    }
    try {
      const data = await propertyApi.get(active.id, id);
      setState((s) => ({ ...s, status: "ready", data, message: null }));
    } catch (e) {
      if (e instanceof ApiError && e.status === 404) setState((s) => ({ ...s, status: "not-found", data: null }));
      else setState((s) => ({ ...s, status: "error", message: e instanceof Error ? e.message : "Could not load." }));
    }
  }, [active, loading, id]);

  useEffect(() => {
    void load();
  }, [load]);

  const mutate = useCallback(
    async (fn: (journeyId: string) => Promise<PropertyDetail>, successNotice?: string) => {
      if (!active) return;
      setState((s) => ({ ...s, busy: true, notice: null }));
      try {
        const data = await fn(active.id);
        setState((s) => ({ ...s, data, busy: false, notice: successNotice ?? null }));
      } catch (e) {
        const stale = e instanceof ApiError && e.status === 409 && e.code === "stale_write";
        setState((s) => ({ ...s, busy: false, notice: e instanceof Error ? e.message : "The change was not saved." }));
        if (stale) void load();
      }
    },
    [active, load],
  );

  return { ...state, journeyId: active?.id ?? null, reload: load, mutate };
}
