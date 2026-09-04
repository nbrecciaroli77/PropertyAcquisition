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
import { Navigate, useLocation } from "react-router-dom";
import { ApiError, authApi, type MeResponse } from "./api";

type Status = "checking" | "authenticated" | "anonymous";

interface AuthValue {
  status: Status;
  me: MeResponse | null;
  signIn: (email: string, password: string) => Promise<MeResponse>;
  signOut: () => Promise<void>;
  signOutEverywhere: () => Promise<void>;
  reload: () => Promise<void>;
}

const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<Status>("checking");
  const [me, setMe] = useState<MeResponse | null>(null);
  const bootstrapped = useRef(false);

  const load = useCallback(async () => {
    // A signed-out visitor never pays for a bootstrap request, and never logs an expected 401.
    if (!document.cookie.split("; ").some((c) => c.startsWith("pa_signed_in="))) {
      setMe(null);
      setStatus("anonymous");
      return;
    }
    try {
      setMe(await authApi.me());
      setStatus("authenticated");
      return;
    } catch (error) {
      if (!(error instanceof ApiError) || error.status !== 401) {
        setMe(null);
        setStatus("anonymous");
        return;
      }
    }
    try {
      setMe(await authApi.refresh());
      setStatus("authenticated");
    } catch {
      setMe(null);
      setStatus("anonymous");
    }
  }, []);

  useEffect(() => {
    if (bootstrapped.current) return;
    bootstrapped.current = true;
    void load();
  }, [load]);

  const value = useMemo<AuthValue>(
    () => ({
      status,
      me,
      signIn: async (email, password) => {
        const next = await authApi.login(email, password);
        setMe(next);
        setStatus("authenticated");
        return next;
      },
      signOut: async () => {
        await authApi.logout().catch(() => undefined);
        setMe(null);
        setStatus("anonymous");
      },
      signOutEverywhere: async () => {
        await authApi.logoutAll().catch(() => undefined);
        setMe(null);
        setStatus("anonymous");
      },
      reload: load,
    }),
    [status, me, load],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used inside AuthProvider");
  return value;
}

export function RequireAuth({ children }: { children: ReactNode }) {
  const { status } = useAuth();
  const location = useLocation();

  if (status === "checking") {
    return (
      <div className="flex min-h-screen items-center justify-center px-4" data-testid="auth-checking">
        <p role="status" aria-live="polite" className="text-sm text-muted">
          Checking your session…
        </p>
      </div>
    );
  }
  if (status === "anonymous") {
    return <Navigate to={`/?next=${encodeURIComponent(location.pathname + location.search)}`} replace />;
  }
  return <>{children}</>;
}
