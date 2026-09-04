import { useCallback, useEffect, useRef, useState } from "react";
import { ApiError, journeyApi, type BriefPayload, type BriefResponse, type FieldError } from "../../lib/api";
import { deepClone } from "../../lib/clone";
import { useJourneys } from "../../lib/journey";

export interface BriefState {
  status: "loading" | "ready" | "no-journey" | "error";
  data: BriefResponse | null;
  draft: BriefPayload | null;
  message: string | null;
  publishErrors: FieldError[];
  busy: boolean;
  dirty: boolean;
  notice: string | null;
}

export function useBrief() {
  const { active, loading, reload } = useJourneys();
  const [state, setState] = useState<BriefState>({
    status: "loading",
    data: null,
    draft: null,
    message: null,
    publishErrors: [],
    busy: false,
    dirty: false,
    notice: null,
  });

  const fetchedFor = useRef<string | null>(null);

  const load = useCallback(async () => {
    if (loading) return;
    if (active === null) {
      setState((s) => ({ ...s, status: "no-journey", data: null, draft: null }));
      return;
    }
    try {
      const data = await journeyApi.brief(active.id);
      setState((s) => ({ ...s, status: "ready", data, draft: data.draft, dirty: false, message: null }));
    } catch (e) {
      setState((s) => ({
        ...s,
        status: "error",
        message: e instanceof Error ? e.message : "The brief could not be loaded.",
      }));
    }
  }, [active, loading]);

  useEffect(() => {
    if (loading) return;
    const key = active?.id ?? "none";
    if (fetchedFor.current === key) return;
    fetchedFor.current = key;
    void load();
  }, [load, loading, active]);

  const setDraft = useCallback((updater: (current: BriefPayload) => BriefPayload) => {
    setState((s) =>
      s.draft === null ? s : { ...s, draft: updater(deepClone(s.draft)), dirty: true, notice: null },
    );
  }, []);

  const apply = (data: BriefResponse, notice: string | null) =>
    setState((s) => ({
      ...s,
      status: "ready",
      data,
      draft: data.draft,
      dirty: false,
      busy: false,
      message: null,
      publishErrors: [],
      notice,
    }));

  const save = useCallback(
    async (notice = "Draft saved. Publish when you are ready.") => {
      if (!state.data || !state.draft) return;
      setState((s) => ({ ...s, busy: true, message: null }));
      try {
        const data = await journeyApi.saveDraft(
          state.data.journey.id,
          state.draft,
          state.data.journey.row_version,
        );
        apply(data, notice);
      } catch (e) {
        if (e instanceof ApiError && e.status === 409) {
          await load();
          setState((s) => ({
            ...s,
            busy: false,
            message: "This brief changed in another session, so we reloaded the latest version. Reapply your edits.",
          }));
          return;
        }
        setState((s) => ({
          ...s,
          busy: false,
          message: e instanceof Error ? e.message : "The draft could not be saved.",
        }));
      }
    },
    [state.data, state.draft, load],
  );

  const resetWeights = useCallback(async () => {
    if (!state.data) return;
    setState((s) => ({ ...s, busy: true }));
    try {
      apply(await journeyApi.resetWeights(state.data.journey.id), "Weights reset to 30 / 30 / 20 / 20.");
    } catch (e) {
      setState((s) => ({
        ...s,
        busy: false,
        message: e instanceof Error ? e.message : "Weights could not be reset.",
      }));
    }
  }, [state.data]);

  const publish = useCallback(
    async (reason: string) => {
      if (!state.data || !state.draft) return false;
      setState((s) => ({ ...s, busy: true, message: null, publishErrors: [] }));
      try {
        const saved = await journeyApi.saveDraft(
          state.data.journey.id,
          state.draft,
          state.data.journey.row_version,
        );
        const published = await journeyApi.publish(
          saved.journey.id,
          reason,
          saved.journey.row_version,
        );
        apply(published, `Version ${published.current_version?.version_no} published. Re-evaluation is queued.`);
        await reload();
        return true;
      } catch (e) {
        if (e instanceof ApiError && e.code === "brief_invalid") {
          const apiError: ApiError = e;
          setState((s) => ({ ...s, busy: false, message: apiError.message, publishErrors: apiError.fieldErrors }));
        } else {
          setState((s) => ({
            ...s,
            busy: false,
            message: e instanceof Error ? e.message : "The brief could not be published.",
          }));
        }
        return false;
      }
    },
    [state.data, state.draft, reload],
  );

  return { ...state, setDraft, save, publish, resetWeights, reload: load };
}

export function errorLookup(errors: FieldError[]): (field: string) => string | undefined {
  const map = new Map(errors.map((e) => [e.field, e.message]));
  return (field: string) => map.get(field);
}
