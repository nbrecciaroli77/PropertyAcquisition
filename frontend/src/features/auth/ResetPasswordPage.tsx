import { useState, type FormEvent } from "react";
import { useSearchParams } from "react-router-dom";
import { Button, ButtonLink } from "../../components/Button";
import { FormNotice, TextField } from "../../components/Form";
import { ApiError, authApi } from "../../lib/api";
import { AuthLayout } from "./AuthLayout";

export default function ResetPasswordPage() {
  const [params] = useSearchParams();
  const token = params.get("token") ?? "";
  const [password, setPassword] = useState("");
  const [confirm, setConfirm] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [fieldError, setFieldError] = useState<string | undefined>();
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setError(null);
    setFieldError(undefined);
    if (password !== confirm) {
      setFieldError("Both passwords must match.");
      return;
    }
    setBusy(true);
    try {
      await authApi.resetPassword(token, password);
      setDone(true);
    } catch (e) {
      if (e instanceof ApiError && e.fieldErrors.length > 0) {
        setFieldError(e.fieldErrors.find((f) => f.field === "password")?.message ?? e.message);
      } else {
        setError(e instanceof Error ? e.message : "This link is invalid or has expired.");
      }
    } finally {
      setBusy(false);
    }
  };

  if (done) {
    return (
      <AuthLayout eyebrow="Password recovery" title="Password changed" testId="reset-password-page">
        <div className="card space-y-4 p-5">
          <FormNotice tone="success" testId="reset-password-success">
            Your password is updated and every existing session was signed out.
          </FormNotice>
          <ButtonLink to="/" variant="success" data-testid="reset-sign-in-link">
            Go to sign in
          </ButtonLink>
        </div>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout
      eyebrow="Password recovery"
      title="Choose a new password"
      description="Setting a new password signs out every device."
      testId="reset-password-page"
    >
      <form onSubmit={onSubmit} noValidate className="space-y-4" data-testid="reset-password-form">
        <TextField
          id="reset-password"
          label="New password"
          type="password"
          value={password}
          onChange={setPassword}
          autoComplete="new-password"
          required
          helper="At least 10 characters, including a letter and a number."
          error={fieldError}
        />
        <TextField
          id="reset-password-confirm"
          label="Confirm new password"
          type="password"
          value={confirm}
          onChange={setConfirm}
          autoComplete="new-password"
          required
        />
        {!token && (
          <FormNotice tone="error" testId="reset-token-missing">
            This link is missing its token. Prepare a new reset link.
          </FormNotice>
        )}
        {error && (
          <FormNotice tone="error" testId="reset-password-form-error">
            {error}
          </FormNotice>
        )}
        <Button type="submit" size="lg" className="w-full" disabled={busy || !token} data-testid="reset-password-submit">
          {busy ? "Updating…" : "Set new password"}
        </Button>
      </form>
    </AuthLayout>
  );
}
