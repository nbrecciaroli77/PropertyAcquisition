import { History } from "lucide-react";
import { formatDate } from "../../lib/format";
import { INHERIT, SETTING_KEYS, type ConfigVersion } from "../../lib/campaigns";
import { SETTING_LABELS } from "./settingFormat";

/** Immutable configuration history, newest first. */
export function VersionHistory({ title, versions, testId }: { title: string; versions: ConfigVersion[]; testId: string }) {
  return (
    <section aria-label={title} className="card min-w-0 p-5" data-testid={testId}>
      <h2 className="flex items-center gap-2 text-h3 font-semibold">
        <History className="h-5 w-5 text-eucalyptus-deep" aria-hidden="true" /> {title}
      </h2>
      {versions.length === 0 ? (
        <p className="mt-2 text-sm text-muted" data-testid={`${testId}-empty`}>No versions yet — everything is inherited.</p>
      ) : (
        <ol className="mt-3 space-y-2">
          {versions.map((v) => {
            const set = SETTING_KEYS.filter((k) => k in v.settings && v.settings[k] !== INHERIT).map((k) => SETTING_LABELS[k]);
            return (
              <li key={v.id} className="rounded-md border border-border bg-canvas p-3 text-sm" data-testid={`${testId}-v${v.version_no}`}>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <span className="font-semibold text-navy">Version {v.version_no}</span>
                  <span className="text-xs text-muted">{formatDate(v.created_at)}</span>
                </div>
                <p className="mt-1 text-charcoal">{v.reason}</p>
                <p className="mt-1 text-xs text-muted">{set.length ? `Sets: ${set.join(", ")}` : "Sets nothing — all inherited"}</p>
              </li>
            );
          })}
        </ol>
      )}
    </section>
  );
}
