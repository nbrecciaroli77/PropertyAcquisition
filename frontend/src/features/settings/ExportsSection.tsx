import { Download, RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";
import { Button } from "../../components/Button";
import { FormNotice } from "../../components/Form";
import { Skeleton } from "../../components/States";
import { StatusChip } from "../../components/StatusChip";
import { formatDate } from "../../lib/format";
import { useAuth } from "../../lib/auth";
import { exportApi, type DataExport } from "../../lib/privacy";

export function ExportsSection() {
  const { me } = useAuth();
  const [exports, setExports] = useState<DataExport[] | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState<"personal" | "workspace" | null>(null);

  const load = async () => {
    try {
      setExports(await exportApi.list());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Exports could not be loaded.");
      setExports([]);
    }
  };
  useEffect(() => { void load(); }, []);

  const request = async (kind: "personal" | "workspace") => {
    setBusy(kind);
    setError(null);
    try {
      if (kind === "personal") await exportApi.requestPersonal();
      else await exportApi.requestWorkspace();
      await load();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Export could not be generated.");
    } finally {
      setBusy(null);
    }
  };

  return (
    <section aria-labelledby="exports-heading" className="card min-w-0 p-5" data-testid="exports-section">
      <h2 id="exports-heading" className="text-h3 font-semibold">Export your data</h2>
      <p className="mt-2 text-sm text-muted">
        Exports are generated on demand and stored here for 24 hours. No object storage or external service is used; the file
        never leaves this database until you download it.
      </p>
      {error && <FormNotice tone="error" testId="exports-error">{error}</FormNotice>}
      <div className="mt-4 flex flex-wrap gap-2">
        <Button size="sm" variant="secondary" onClick={() => void request("personal")} disabled={busy !== null} icon={<RefreshCw className={`h-4 w-4 ${busy === "personal" ? "animate-spin" : ""}`} />} data-testid="export-personal-button">
          {busy === "personal" ? "Generating…" : "Export my data"}
        </Button>
        {me?.workspace.role === "owner" && (
          <Button size="sm" variant="secondary" onClick={() => void request("workspace")} disabled={busy !== null} icon={<RefreshCw className={`h-4 w-4 ${busy === "workspace" ? "animate-spin" : ""}`} />} data-testid="export-workspace-button">
            {busy === "workspace" ? "Generating…" : "Export workspace data"}
          </Button>
        )}
      </div>

      {exports === null && <Skeleton className="mt-4 h-16" label="Loading exports" />}
      {exports && exports.length === 0 && <p className="mt-4 text-sm text-muted">No exports requested yet.</p>}
      {exports && exports.length > 0 && (
        <ul className="mt-4 divide-y divide-border" data-testid="exports-list">
          {exports.map((exp) => (
            <li key={exp.id} className="flex flex-wrap items-center justify-between gap-2 py-3" data-testid={`export-${exp.id}`}>
              <div className="min-w-0">
                <div className="font-semibold capitalize">{exp.export_type} export</div>
                <div className="text-xs text-muted">
                  Requested {formatDate(exp.created_at)} · {Math.round(exp.file_size_bytes / 1024)} KB · expires {formatDate(exp.expires_at)}
                </div>
              </div>
              <div className="flex items-center gap-2">
                <StatusChip tone={exp.state === "ready" ? "pass" : exp.state === "expired" ? "neutral" : "fail"} hideIcon>{exp.state}</StatusChip>
                {exp.state === "ready" && (
                  <a href={exportApi.downloadUrl(exp.id)} target="_blank" rel="noopener noreferrer" className="inline-flex h-9 items-center gap-1.5 rounded-md border border-border px-3 text-sm font-semibold hover:border-navy" data-testid={`export-download-${exp.id}`}>
                    <Download className="h-3.5 w-3.5" />Download
                  </a>
                )}
              </div>
            </li>
          ))}
        </ul>
      )}
    </section>
  );
}
