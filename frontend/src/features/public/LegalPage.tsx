import { ButtonLink } from "../../components/Button";

export function LegalPage({ kind }: { kind: "terms" | "privacy" }) {
  const isTerms = kind === "terms";
  return (
    <article className="mx-auto w-full max-w-3xl px-4 py-12 md:px-8" data-testid={`${kind}-page`}>
      <p className="label mb-3 text-ochre-deep">Working concept · placeholder</p>
      <h1 className="text-display">{isTerms ? "Terms of Use" : "Privacy Policy"}</h1>
      <p className="mt-4 text-muted">
        {isTerms
          ? "This is a private prototype for the owner's own use. It is not a public service, does not provide valuation, legal or financial advice, and does not act on your behalf."
          : "This prototype stores only synthetic fixture data in Milestone 1. No live listings, mailboxes, drives or portals are connected. Nothing is sent to agents or third parties."}
      </p>
      <ul className="mt-6 list-disc space-y-2 pl-5 text-sm text-charcoal">
        <li>Your brief, notes and shortlist are private to your workspace.</li>
        <li>Unknown facts are shown as unknown — never as pass, fail or zero.</li>
        <li>Drafts do not send. Reminders do not book. Advertised inspections are not confirmed attendance.</li>
        <li>Final wording will be reviewed before any private preview beyond the owner.</li>
      </ul>
      <ButtonLink to="/" variant="secondary" className="mt-8" data-testid={`${kind}-back`}>
        Back to sign in
      </ButtonLink>
    </article>
  );
}

export function NotFoundPage() {
  return (
    <div className="mx-auto w-full max-w-xl px-4 py-16 text-center" data-testid="not-found-page">
      <p className="label text-muted">404</p>
      <h1 className="mt-2 text-display">This page doesn't exist</h1>
      <p className="mt-3 text-muted">Check the address, or return to the start.</p>
      <ButtonLink to="/" className="mt-6" data-testid="not-found-home">
        Go to Welcome
      </ButtonLink>
    </div>
  );
}
