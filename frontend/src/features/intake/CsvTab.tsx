/**
 * M4.2 CSV batch import tab.
 *
 * Flow: Select file → backend preview → review rows (skip errors) → confirm import → result.
 * The browser parsing is for display/preview only.  The backend independently re-parses
 * and re-validates the raw file bytes before writing any records.
 *
 * Formula-injection cells (=, +, -, @) are flagged visually and stored as inert text.
 */
import { AlertTriangle, CheckCircle, Download, FileSpreadsheet, Loader2, X } from "lucide-react";
import { useRef, useState } from "react";
import { Button } from "../../components/Button";
import { csvIntakeApi, type CsvBatchResult, type CsvPreviewResponse, type CsvPreviewRow } from "../../lib/csvIntake";
import { ApiError } from "../../lib/api";

type Phase = "pick" | "previewing" | "preview" | "importing" | "done";

const STATUS_COLOR: Record<string, string> = {
  ok: "text-eucalyptus-deep",
  warning: "text-ochre-deep",
  error: "text-risk",
};

function FormulaFlag({ cols }: { cols: string[] }) {
  if (!cols.length) return null;
  return (
    <span
      className="inline-flex items-center gap-1 rounded bg-ochre-soft px-1.5 py-0.5 text-xs text-ochre-deep"
      title="Cell begins with = + - or @ — stored as inert text, never executed"
    >
      <AlertTriangle className="h-3 w-3" />
      Formula-like: {cols.join(", ")}
    </span>
  );
}

function PreviewRowCard({
  row,
  skipped,
  onToggle,
}: {
  row: CsvPreviewRow;
  skipped: boolean;
  onToggle: (idx: number) => void;
}) {
  const addr = [row.address_line, row.suburb, row.state].filter(Boolean).join(", ") || "(no address)";
  return (
    <tr
      className={`border-b border-border text-sm transition-opacity ${skipped ? "opacity-40" : ""}`}
      data-testid={`csv-row-${row.row_index}`}
    >
      <td className="py-2 pr-3 text-center">
        {row.skippable ? (
          <span className="text-xs text-muted">—</span>
        ) : (
          <input
            type="checkbox"
            checked={!skipped}
            onChange={() => onToggle(row.row_index)}
            aria-label={`Include row ${row.row_index + 1}`}
            data-testid={`csv-row-check-${row.row_index}`}
            className="h-4 w-4 accent-navy"
          />
        )}
      </td>
      <td className="py-2 pr-3 font-mono text-xs text-muted">{row.row_index + 1}</td>
      <td className="py-2 pr-4 font-medium">{addr}</td>
      <td className="py-2 pr-4">
        <span className={`font-medium ${STATUS_COLOR[row.status] ?? ""}`}>
          {row.status === "ok" ? "OK" : row.status === "warning" ? "Warning" : "Error"}
        </span>
        {row.errors.length > 0 && (
          <ul className="mt-0.5 list-disc pl-4 text-xs text-risk">
            {row.errors.map((e, i) => <li key={i}>{e}</li>)}
          </ul>
        )}
        {row.warnings.length > 0 && (
          <ul className="mt-0.5 list-disc pl-4 text-xs text-ochre-deep">
            {row.warnings.slice(0, 2).map((w, i) => <li key={i}>{w}</li>)}
          </ul>
        )}
        {row.formula_flags.length > 0 && (
          <div className="mt-0.5">
            <FormulaFlag cols={row.formula_flags} />
          </div>
        )}
      </td>
    </tr>
  );
}

function BatchResultPanel({ result, onReset }: { result: CsvBatchResult; onReset: () => void }) {
  const total = result.total_rows;
  const stats = [
    { label: "Created", value: result.created, color: "text-eucalyptus-deep" },
    { label: "Matched existing", value: result.matched_existing, color: "text-navy" },
    { label: "Needs review", value: result.requires_review, color: "text-ochre-deep" },
    { label: "Failed", value: result.failed, color: "text-risk" },
    { label: "Skipped", value: result.skipped, color: "text-muted" },
  ];
  const ok = result.state === "completed";
  return (
    <div className="space-y-5" data-testid="csv-batch-result">
      <div className="flex items-center gap-3">
        {ok ? (
          <CheckCircle className="h-6 w-6 text-eucalyptus-deep" />
        ) : (
          <AlertTriangle className="h-6 w-6 text-ochre-deep" />
        )}
        <div>
          <p className="font-semibold">
            Import {ok ? "complete" : "partial"} — {total} row{total !== 1 ? "s" : ""} processed
          </p>
          <p className="text-xs text-muted">{result.filename}</p>
        </div>
      </div>
      <dl className="grid grid-cols-2 gap-3 sm:grid-cols-5">
        {stats.map((s) => (
          <div key={s.label} className="rounded-md bg-canvas-deep p-3 text-center">
            <dd className={`text-2xl font-bold ${s.color}`}>{s.value}</dd>
            <dt className="mt-0.5 text-xs text-muted">{s.label}</dt>
          </div>
        ))}
      </dl>
      {result.row_results.length > 0 && (
        <div className="overflow-x-auto rounded-md border border-border">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-border bg-canvas-deep text-left text-xs font-semibold text-muted">
                <th className="px-3 py-2">#</th>
                <th className="px-3 py-2">Address</th>
                <th className="px-3 py-2">Outcome</th>
              </tr>
            </thead>
            <tbody>
              {result.row_results.map((r) => (
                <tr key={r.row_index} className="border-b border-border last:border-0" data-testid={`csv-result-row-${r.row_index}`}>
                  <td className="px-3 py-2 font-mono text-xs text-muted">{r.row_index + 1}</td>
                  <td className="px-3 py-2">{r.address ?? "—"}</td>
                  <td className="px-3 py-2">
                    <span className={{
                      created: "text-eucalyptus-deep",
                      matched_existing: "text-navy",
                      requires_review: "text-ochre-deep",
                      failed: "text-risk",
                      skipped: "text-muted",
                    }[r.outcome] ?? ""}>
                      {r.outcome.replace(/_/g, " ")}
                    </span>
                    {r.formula_flags && r.formula_flags.length > 0 && (
                      <FormulaFlag cols={r.formula_flags} />
                    )}
                    {r.error && <span className="ml-2 text-xs text-muted">{r.error}</span>}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <Button variant="secondary" size="sm" onClick={onReset} data-testid="csv-import-again">
        Import another file
      </Button>
    </div>
  );
}

export function CsvTab({ journeyId }: { journeyId: string }) {
  const [phase, setPhase] = useState<Phase>("pick");
  const [file, setFile] = useState<File | null>(null);
  const [preview, setPreview] = useState<CsvPreviewResponse | null>(null);
  const [skipSet, setSkipSet] = useState<Set<number>>(new Set());
  const [result, setResult] = useState<CsvBatchResult | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const handleFile = async (f: File) => {
    if (!f.name.toLowerCase().endsWith(".csv")) {
      setError("Please select a .csv file.");
      return;
    }
    setFile(f);
    setError(null);
    setPhase("previewing");
    try {
      const p = await csvIntakeApi.preview(journeyId, f);
      setPreview(p);
      // Pre-skip rows with fatal errors
      const autoSkip = new Set(p.preview_rows.filter((r) => r.skippable).map((r) => r.row_index));
      setSkipSet(autoSkip);
      setPhase("preview");
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : String(err);
      setError(`Preview failed: ${msg}`);
      setPhase("pick");
    }
  };

  const handleImport = async () => {
    if (!file || !preview) return;
    setPhase("importing");
    setError(null);
    try {
      const r = await csvIntakeApi.import(journeyId, file, [...skipSet]);
      setResult(r);
      setPhase("done");
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : String(err);
      setError(`Import failed: ${msg}`);
      setPhase("preview");
    }
  };

  const handleReset = () => {
    setPhase("pick");
    setFile(null);
    setPreview(null);
    setSkipSet(new Set());
    setResult(null);
    setError(null);
    if (fileRef.current) fileRef.current.value = "";
  };

  const toggleRow = (idx: number) => {
    setSkipSet((prev) => {
      const next = new Set(prev);
      if (next.has(idx)) next.delete(idx);
      else next.add(idx);
      return next;
    });
  };

  // ── Done ──────────────────────────────────────────────────────────────────
  if (phase === "done" && result) {
    return <BatchResultPanel result={result} onReset={handleReset} />;
  }

  // ── Importing ─────────────────────────────────────────────────────────────
  if (phase === "importing") {
    return (
      <div className="flex flex-col items-center gap-3 py-12 text-muted" data-testid="csv-importing">
        <Loader2 className="h-8 w-8 animate-spin text-navy" />
        <p className="text-sm">Importing {file?.name}…</p>
        <p className="text-xs">The server is re-validating every row independently.</p>
      </div>
    );
  }

  // ── Preview ───────────────────────────────────────────────────────────────
  if (phase === "preview" && preview) {
    const importableCount = preview.total_rows - skipSet.size;
    return (
      <div className="space-y-5" data-testid="csv-preview-panel">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="font-semibold">{preview.filename}</p>
            <p className="text-xs text-muted">
              {preview.total_rows} row{preview.total_rows !== 1 ? "s" : ""}
              {" · "}
              <span className="text-eucalyptus-deep">{preview.valid_rows} valid</span>
              {preview.warning_rows > 0 && (
                <span className="ml-1 text-ochre-deep">· {preview.warning_rows} warn</span>
              )}
              {preview.error_rows > 0 && (
                <span className="ml-1 text-risk">· {preview.error_rows} error</span>
              )}
            </p>
          </div>
          <button
            type="button"
            onClick={handleReset}
            className="flex items-center gap-1 text-xs text-muted hover:text-navy"
            data-testid="csv-cancel-preview"
          >
            <X className="h-3.5 w-3.5" />
            Change file
          </button>
        </div>

        {preview.headers_missing.length > 0 && (
          <div className="rounded-md border border-risk bg-risk-soft px-4 py-3 text-sm text-risk" data-testid="csv-missing-headers">
            <strong>Required columns missing:</strong> {preview.headers_missing.join(", ")}
          </div>
        )}

        {preview.total_rows > preview.preview_rows.length && (
          <p className="text-xs text-muted" data-testid="csv-truncated-note">
            Showing first {preview.preview_rows.length} of {preview.total_rows} rows. All rows will be processed on import.
          </p>
        )}

        <div className="overflow-x-auto rounded-md border border-border">
          <table className="w-full" data-testid="csv-preview-table">
            <thead>
              <tr className="border-b border-border bg-canvas-deep text-left text-xs font-semibold text-muted">
                <th className="py-2 pr-3 text-center">Include</th>
                <th className="py-2 pr-3">#</th>
                <th className="py-2 pr-4">Address</th>
                <th className="py-2">Validation</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-border">
              {preview.preview_rows.map((row) => (
                <PreviewRowCard
                  key={row.row_index}
                  row={row}
                  skipped={skipSet.has(row.row_index)}
                  onToggle={toggleRow}
                />
              ))}
            </tbody>
          </table>
        </div>

        {error && (
          <p className="rounded-md border border-risk bg-risk-soft px-4 py-2 text-sm text-risk" data-testid="csv-error">
            {error}
          </p>
        )}

        <div className="flex flex-wrap gap-3">
          <Button
            onClick={handleImport}
            disabled={importableCount === 0}
            data-testid="csv-confirm-import"
          >
            Import {importableCount} row{importableCount !== 1 ? "s" : ""}
          </Button>
          <Button variant="secondary" onClick={handleReset} data-testid="csv-cancel">
            Cancel
          </Button>
        </div>
        <p className="text-xs text-muted">
          The server will independently re-parse and re-validate the file before writing any records.
        </p>
      </div>
    );
  }

  // ── Pick file ─────────────────────────────────────────────────────────────
  return (
    <div className="space-y-6" data-testid="csv-pick-panel">
      {/* Template download */}
      <div className="rounded-md border border-border bg-canvas-deep p-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="font-medium">Download template</p>
            <p className="text-xs text-muted">
              Required columns: address_line, suburb, state. Optional: postcode, beds, baths, cars,
              land_sqm, floor_sqm, property_type, raw_price, price_kind, notes.
            </p>
          </div>
          <a
            href={csvIntakeApi.templateUrl(journeyId)}
            download="property_import_template.csv"
            className="flex items-center gap-2 rounded-md border border-border bg-surface px-3 py-1.5 text-sm font-medium hover:bg-canvas transition-colors"
            data-testid="csv-download-template"
          >
            <Download className="h-4 w-4" />
            Template.csv
          </a>
        </div>
      </div>

      {/* File pick */}
      <div>
        <label
          htmlFor="csv-file-input"
          className="block cursor-pointer rounded-lg border-2 border-dashed border-border bg-canvas-deep p-8 text-center transition-colors hover:border-navy hover:bg-surface"
          data-testid="csv-drop-zone"
        >
          <FileSpreadsheet className="mx-auto h-10 w-10 text-muted" />
          <p className="mt-2 font-medium">Choose a CSV file</p>
          <p className="mt-1 text-xs text-muted">Max 1 MB · 200 rows · UTF-8</p>
          <input
            id="csv-file-input"
            ref={fileRef}
            type="file"
            accept=".csv,text/csv"
            className="sr-only"
            data-testid="csv-file-input"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) handleFile(f);
            }}
          />
        </label>
      </div>

      {phase === "previewing" && (
        <div className="flex items-center gap-2 text-sm text-muted">
          <Loader2 className="h-4 w-4 animate-spin" />
          Validating file…
        </div>
      )}
      {error && (
        <p className="rounded-md border border-risk bg-risk-soft px-4 py-2 text-sm text-risk" data-testid="csv-error">
          {error}
        </p>
      )}

      <p className="text-xs text-muted">
        Cells starting with <code className="font-mono">=</code> <code className="font-mono">+</code>{" "}
        <code className="font-mono">-</code> <code className="font-mono">@</code> are treated as inert
        text and flagged for review — they are never evaluated.
      </p>
    </div>
  );
}
