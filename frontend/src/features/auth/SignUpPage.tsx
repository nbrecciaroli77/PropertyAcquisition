import { useState, type FormEvent } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Button } from "../../components/Button";
import { FormNotice, TextField } from "../../components/Form";
import { ApiError, authApi } from "../../lib/api";
import { AuthLayout } from "./AuthLayout";

export default function SignUpPage() {
  const navigate = useNavigate();
  const [displayName, setDisplayName] = useState("");
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [workspaceName, setWorkspaceName] = useState("");
  const [errors, setErrors] = useState<Record<string, string>>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setBusy(true);
    setErrors({});
    setFormError(null);
    try {
      await authApi.signup({
        email: email.trim(),
        password,
        display_name: displayName.trim(),
        workspace_name: workspaceName.trim() || undefined,
      });
      navigate(`/verify-pending?email=${encodeURIComponent(email.trim())}`);
    } catch (error) {
      if (error instanceof ApiError && error.fieldErrors.length > 0) {
        setErrors(Object.fromEntries(error.fieldErrors.map((e) => [e.field, e.message])));
        setFormError("Check the highlighted fields.");
      } else {
        setFormError(error instanceof Error ? error.message : "Sign-up failed. Try again.");
      }
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthLayout
      eyebrow="Create an account"
      title="Start a buying journey"
      description="Your workspace is private. Email and password only — no mailbox, portal or Drive is connected."
      testId="sign-up-page"
      footer={
        <>
          Already have an account?{" "}
          <Link to="/" className="font-semibold text-eucalyptus-deep hover:underline underline-offset-4" data-testid="sign-up-to-sign-in">
            Sign in
          </Link>
        </>
      }
    >
      <form onSubmit={onSubmit} noValidate className="space-y-4" data-testid="sign-up-form">
        <TextField
          id="signup-name"
          label="Your name"
          value={displayName}
          onChange={setDisplayName}
          autoComplete="name"
          required
          error={errors["display_name"]}
        />
        <TextField
          id="signup-email"
          label="Email address"
          type="email"
          inputMode="email"
          value={email}
          onChange={setEmail}
          autoComplete="username"
          required
          error={errors["email"]}
        />
        <TextField
          id="signup-password"
          label="Password"
          type="password"
          value={password}
          onChange={setPassword}
          autoComplete="new-password"
          required
          helper="At least 10 characters, including a letter and a number."
          error={errors["password"]}
        />
        <TextField
          id="signup-workspace"
          label="Workspace name (optional)"
          value={workspaceName}
          onChange={setWorkspaceName}
          helper="Your household or project name. You can change it later."
          error={errors["workspace_name"]}
        />

        {formError && (
          <FormNotice tone="error" testId="sign-up-error">
            {formError}
          </FormNotice>
        )}

        <Button type="submit" size="lg" className="w-full" disabled={busy} data-testid="sign-up-submit">
          {busy ? "Creating your account…" : "Create account"}
        </Button>
        <p className="text-xs text-muted">
          By continuing you agree to the{" "}
          <Link to="/terms" className="font-semibold text-eucalyptus-deep hover:underline underline-offset-4">
            Terms
          </Link>{" "}
          and{" "}
          <Link to="/privacy" className="font-semibold text-eucalyptus-deep hover:underline underline-offset-4">
            Privacy Policy
          </Link>
          . This is a private prototype: no exhaustive listing coverage, valuation or purchasing service is implied.
        </p>
      </form>
    </AuthLayout>
  );
}
