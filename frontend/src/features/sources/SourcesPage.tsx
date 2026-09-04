import { FileSpreadsheet, Globe, Inbox, Mail, PencilLine } from "lucide-react";
import { MilestoneNote, PageHeader } from "../../components/Page";
import { StatusChip, type ChipTone } from "../../components/StatusChip";

type SourceStatus = "Not connected" | "Configured" | "Receiving" | "Degraded" | "Reauthorisation required" | "Unsupported";

const statusTone: Record<SourceStatus, ChipTone> = {
  "Not connected": "neutral",
  Configured: "info",
  Receiving: "pass",
  Degraded: "warning",
  "Reauthorisation required": "warning",
  Unsupported: "fail",
};

const sources: { name: string; type: string; region: string; status: SourceStatus; lastReceipt: string; limitation: string; recovery: string; icon: JSX.Element }[] = [
  { name: "Manual entry", type: "Structured form", region: "All AU states and territories", status: "Configured", lastReceipt: "15 Jun 2026 (synthetic)", limitation: "Facts are user-entered and labelled as such.", recovery: "None needed", icon: <PencilLine className="h-5 w-5" aria-hidden="true" /> },
  { name: "CSV import", type: "File import", region: "All AU states and territories", status: "Configured", lastReceipt: "Never (fixture only)", limitation: "Synthetic fixtures only in this prototype.", recovery: "Import a file (Milestone 4)", icon: <FileSpreadsheet className="h-5 w-5" aria-hidden="true" /> },
  { name: "Pasted listing text", type: "Untrusted text", region: "All AU states and territories", status: "Not connected", lastReceipt: "—", limitation: "Deterministic parser; text cannot instruct the system.", recovery: "Arrives in Milestone 4", icon: <Inbox className="h-5 w-5" aria-hidden="true" /> },
  { name: "Email forwarding", type: "Inbound email", region: "—", status: "Not connected", lastReceipt: "—", limitation: "No mailbox is connected. Gmail is never read.", recovery: "Separate later gate", icon: <Mail className="h-5 w-5" aria-hidden="true" /> },
  { name: "Property portals", type: "Portal connector", region: "—", status: "Unsupported", lastReceipt: "—", limitation: "Not connected — rights required. No scraping.", recovery: "Requires licensed access", icon: <Globe className="h-5 w-5" aria-hidden="true" /> },
];

export default function SourcesPage() {
  return (
    <>
      <PageHeader eyebrow="Sources" title="Source connections" description="Honest states only. A card never claims a successful sync that did not happen." testId="sources-header" />
      <ul className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
        {sources.map((s) => (
          <li key={s.name} className="card flex min-w-0 flex-col gap-3 p-5" data-testid={`source-card-${s.name.toLowerCase().replace(/\s+/g, "-")}`}>
            <div className="flex flex-wrap items-start justify-between gap-3">
              <div className="flex items-center gap-3">
                <span className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-md bg-canvas-deep text-navy">{s.icon}</span>
                <div className="min-w-0">
                  <h2 className="text-h3 font-semibold">{s.name}</h2>
                  <p className="text-xs text-muted">{s.type}</p>
                </div>
              </div>
              <StatusChip tone={statusTone[s.status]} data-testid={`source-status-${s.name.toLowerCase().replace(/\s+/g, "-")}`}>
                {s.status}
              </StatusChip>
            </div>
            <dl className="grid grid-cols-[auto_minmax(0,1fr)] gap-x-3 gap-y-1 text-sm">
              <dt className="text-muted">Region</dt>
              <dd className="break-words">{s.region}</dd>
              <dt className="text-muted">Last receipt</dt>
              <dd className="break-words">{s.lastReceipt}</dd>
              <dt className="text-muted">Limitation</dt>
              <dd className="break-words">{s.limitation}</dd>
              <dt className="text-muted">Recovery</dt>
              <dd className="break-words">{s.recovery}</dd>
            </dl>
          </li>
        ))}
      </ul>
      <MilestoneNote milestone={4}>Intake events, idempotent processing and duplicate review arrive in Milestone 4. No live source will be connected in this prototype.</MilestoneNote>
    </>
  );
}
