import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { Button } from "../../components/Button";
import { FormNotice } from "../../components/Form";
import { authApi } from "../../lib/api";
import { AuthLayout } from "./AuthLayout";

export default function VerifyPendingPage() {
  const [params] = useSearchParams();
  const email = params.get("email") ?? "";
  const [notice, setNotice] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);

  const reissue = async () => {
    setBusy(true);
    try {
      const response = await authApi.reissueVerification(email);
      setNotice(response.message);
    } catch {
      setNotice("That link could not be reissued. Check the address and try again.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <AuthLayout
      eyebrow="Verification pending"
      title="Confirm your email address"
      description={
        email ? (
          <>
            We prepared a confirmation link for <strong className="font-semibold text-navy">{email}</strong>.
          </>
        ) : (
          "We prepared a confirmation link for your account."
        )
      }
      testId="verify-pending-page"
      footer={
        <>
          Wrong address?{" "}
          <Link to="/signup" className="font-semibold text-eucalyptus-deep hover:underline underline-offset-4">
            Create the account again
          </Link>
          .
        </>
      }
    >
      <div className="card space-y-4 p-5">
        <FormNotice tone="info" testId="delivery-suppressed-notice">
          <strong className="font-semibold">Email delivery is not active in this release.</strong>{" "}
          Contact the workspace owner or administrator to obtain your confirmation link.
        </FormNotice>
        <Button variant="secondary" onClick={reissue} disabled={busy || !email} data-testid="reissue-verification">
          {busy ? "Preparing a new link…" : "Prepare a new link"}
        </Button>
        {notice && (
          <FormNotice tone="success" testId="verify-pending-notice">
            {notice}
          </FormNotice>
        )}
        <p className="text-xs text-muted">
          Links expire after 24 hours and can be used once. Signing in before confirming will bring you back here.
        </p>
      </div>
    </AuthLayout>
  );
}
