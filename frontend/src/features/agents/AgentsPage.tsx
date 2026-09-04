import { Copy, Mail, Phone } from "lucide-react";
import { Button } from "../../components/Button";
import { ConfirmDialog } from "../../components/ConfirmDialog";
import { MilestoneNote, PageHeader } from "../../components/Page";
import { StatusChip } from "../../components/StatusChip";
import { properties } from "../../lib/synthetic";

export default function AgentsPage() {
  const p = properties[0];
  return (
    <>
      <PageHeader eyebrow="Agents" title="Agents and drafts" description="Public contact evidence is kept apart from your private notes. There is no send button in this app." testId="agents-header" />

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.4fr)]">
        <section aria-labelledby="agent-heading" className="card p-5">
          <h2 id="agent-heading" className="text-h3 font-semibold">
            Sample Agent (synthetic)
          </h2>
          <p className="text-sm text-muted">Example Realty · listing agent for {p.address}</p>
          <dl className="mt-4 space-y-2 text-sm">
            <div className="flex items-center gap-2">
              <dt className="text-muted">
                <Mail className="h-4 w-4" aria-hidden="true" />
                <span className="sr-only">Email</span>
              </dt>
              <dd>agent@example.invalid</dd>
              <dd className="ml-auto text-xs text-muted">Public listing · 18 Jun</dd>
            </div>
            <div className="flex items-center gap-2">
              <dt className="text-muted">
                <Phone className="h-4 w-4" aria-hidden="true" />
                <span className="sr-only">Phone</span>
              </dt>
              <dd>0400 000 000</dd>
              <dd className="ml-auto text-xs text-muted">Public listing · 18 Jun</dd>
            </div>
          </dl>
          <h3 className="mt-6 text-sm font-semibold">Private notes</h3>
          <p className="mt-1 rounded-md bg-canvas px-3 py-2 text-sm text-charcoal">Responsive on email; mentioned vendor is flexible on settlement. (Your note — never shared.)</p>
        </section>

        <section aria-labelledby="draft-heading" className="card p-5" data-testid="draft-card">
          <div className="flex flex-wrap items-center justify-between gap-2">
            <h2 id="draft-heading" className="text-h3 font-semibold">
              Enquiry draft
            </h2>
            <StatusChip tone="warning" data-testid="draft-unsent-chip">
              Unsent
            </StatusChip>
          </div>
          <p className="mt-1 text-sm text-muted">
            To: agent@example.invalid · Re: {p.address}, {p.suburb}
          </p>
          <label htmlFor="draft-body" className="sr-only">
            Draft body
          </label>
          <textarea
            id="draft-body"
            data-testid="draft-body"
            className="mt-3 h-40 w-full rounded-md border border-border bg-surface p-3 text-sm"
            defaultValue={`Hello,\n\nI'm interested in ${p.address}. Could you confirm the land size on title and whether a building report is available?\n\nThank you.`}
          />
          <div className="mt-3 flex flex-wrap items-center gap-2">
            <ConfirmDialog
              title="Copy draft to clipboard?"
              description="This copies the text so you can paste it into your own mail client. Property Acquisition does not send anything to anyone."
              confirmLabel="Copy text"
              onConfirm={() => undefined}
              trigger={
                <Button variant="secondary" size="sm" icon={<Copy className="h-4 w-4" aria-hidden="true" />} data-testid="draft-copy">
                  Copy to my mail client
                </Button>
              }
            />
            <span className="text-xs text-muted">No send pathway exists in this application.</span>
          </div>
        </section>
      </div>

      <MilestoneNote milestone={5}>Editable drafts with persisted UNSENT state, contact evidence history and copy/export arrive in Milestone 5.</MilestoneNote>
    </>
  );
}
