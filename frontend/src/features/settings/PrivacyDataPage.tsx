import { PageHeader } from "../../components/Page";
import { DeletionSection } from "./DeletionSection";
import { ExportsSection } from "./ExportsSection";

export default function PrivacyDataPage() {
  return (
    <>
      <PageHeader
        eyebrow="Settings"
        title="Data & privacy"
        description="What this prototype stores, what it doesn't connect to, and how export and deletion work."
        testId="privacy-header"
      />

      <section aria-labelledby="privacy-copy-heading" className="card mb-6 min-w-0 p-5" data-testid="privacy-copy">
        <h2 id="privacy-copy-heading" className="text-h3 font-semibold">How your data is handled</h2>
        <ul className="mt-3 space-y-2 text-sm text-charcoal">
          <li>Postgres (Supabase) is this application's only system of record. There is no separate reporting database.</li>
          <li>Google Drive and Gmail are not connected. Any URL you add is stored as text and never fetched automatically.</li>
          <li>Property source connectors are currently synthetic/demo fixtures — no live portal, agent or listing feed is connected.</li>
          <li>Email delivery and native push notifications are unavailable. Every notification and report stays in-app.</li>
          <li>Personal and workspace exports contain your application data as JSON/CSV inside a ZIP — never passwords, session tokens, reset tokens or credential references.</li>
          <li>Deletion requests need a fresh password check and a typed confirmation, then wait through a 72-hour cooling-off period before anything is removed, and can be cancelled at any time before that.</li>
          <li>This is a private prototype. Nothing here is a certified legal or compliance statement about data handling.</li>
        </ul>
      </section>

      <div className="grid gap-6 lg:grid-cols-2">
        <ExportsSection />
        <DeletionSection />
      </div>
    </>
  );
}
