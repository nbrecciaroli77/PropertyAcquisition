import { useEffect, useRef, useState } from "react";
import { useSearchParams } from "react-router-dom";
import { ButtonLink } from "../../components/Button";
import { FormNotice } from "../../components/Form";
import { authApi } from "../../lib/api";
import { AuthLayout } from "./AuthLayout";

type State = { kind: "checking" } | { kind: "verified"; email: string } | { kind: "failed"; message: string };

export default function VerifyEmailPage() {
  const [params] = useSearchParams();
  const token = params.get("token") ?? "";
  const [state, setState] = useState<State>({ kind: "checking" });
  const started = useRef(false);

  useEffect(() => {
    if (started.current) return;
    started.current = true;
    if (!token) {
      setState({ kind: "failed", message: "This link is missing its token." });
      return;
    }
    authApi
      .verifyEmail(token)
      .then((r) => setState({ kind: "verified", email: r.email }))
      .catch((error: unknown) =>
        setState({
          kind: "failed",
          message: error instanceof Error ? error.message : "This link is invalid or has expired.",
        }),
      );
  }, [token]);

  return (
    <AuthLayout eyebrow="Email verification" title="Confirming your address" testId="verify-email-page">
      {state.kind === "checking" && (
        <FormNotice tone="info" testId="verify-email-checking">
          Checking your link…
        </FormNotice>
      )}
      {state.kind === "verified" && (
        <div className="card space-y-4 p-5">
          <FormNotice tone="success" testId="verify-email-success">
            <strong className="font-semibold">{state.email} is confirmed.</strong> You can sign in now.
          </FormNotice>
          <ButtonLink to="/" variant="success" data-testid="verified-sign-in-link">
            Go to sign in
          </ButtonLink>
        </div>
      )}
      {state.kind === "failed" && (
        <div className="card space-y-4 p-5">
          <FormNotice tone="error" testId="verify-email-failed">
            {state.message}
          </FormNotice>
          <ButtonLink to="/verify-pending" variant="secondary" data-testid="verify-retry-link">
            Prepare a new link
          </ButtonLink>
        </div>
      )}
    </AuthLayout>
  );
}
