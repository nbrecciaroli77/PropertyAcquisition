import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { Button } from "../../components/Button";
import { FormNotice, TextField } from "../../components/Form";
import { authApi } from "../../lib/api";
import { AuthLayout } from "./AuthLayout";

export default function ForgotPasswordPage() {
  const [email, setEmail] = useState("");
  const [sent, setSent] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const onSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setBusy(true);
    try {
      const response = await authApi.forgotPassword(email.trim());
      setSent(response.message);
    } catch {
      setSent("If that address has an account, a reset link has been prepared.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthLayout
      eyebrow="Password recovery"
      title="Reset your password"
      description="We never confirm whether an address has an account."
      testId="forgot-password-page"
      footer={
        <Link to="/" className="font-semibold text-eucalyptus-deep hover:underline underline-offset-4">
          Back to sign in
        </Link>
      }
    >
      <form onSubmit={onSubmit} noValidate className="space-y-4" data-testid="forgot-password-form">
        <TextField
          id="forgot-email"
          label="Email address"
          type="email"
          inputMode="email"
          value={email}
          onChange={setEmail}
          autoComplete="username"
          required
        />
        <Button type="submit" size="lg" className="w-full" disabled={busy} data-testid="forgot-password-submit">
          {busy ? "Preparing your link…" : "Prepare a reset link"}
        </Button>
        {sent && (
          <FormNotice tone="success" testId="forgot-password-notice">
            {sent}
          </FormNotice>
        )}
      </form>
    </AuthLayout>
  );
}
