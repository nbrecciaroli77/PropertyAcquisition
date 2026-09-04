import { Database } from "lucide-react";
import { useState } from "react";
import { Button } from "../../components/Button";
import { propertyApi } from "../../lib/properties";

/** Development-only internal fixture creation. This is not the Add property intake (Milestone 4). */
export function LoadDemoButton({ journeyId, onLoaded }: { journeyId: string; onLoaded: () => void }) {
  const [busy, setBusy] = useState(false);
  const [message, setMessage] = useState<string | null>(null);
  const load = async () => {
    setBusy(true);
    setMessage(null);
    try {
      const r = await propertyApi.loadDemo(journeyId);
      setMessage(`${r.created} synthetic fixture properties loaded and evaluated against brief ${typeof r.evaluated_against === "number" ? `v${r.evaluated_against}` : `(${r.evaluated_against})`}.`);
      onLoaded();
    } catch (e) {
      setMessage(e instanceof Error ? e.message : "The fixture could not be loaded.");
    } finally {
      setBusy(false);
    }
  };
  return (
    <div className="flex flex-col items-start gap-2">
      <Button variant="secondary" size="sm" onClick={load} disabled={busy} icon={<Database className="h-4 w-4" aria-hidden="true" />} data-testid="load-demo-properties">
        {busy ? "Loading fixture…" : "Load synthetic demo properties"}
      </Button>
      <p className="text-xs text-muted">Development only · fixtures/demo-data.json · fictional addresses</p>
      {message && (
        <p className="text-sm" role="status" data-testid="load-demo-result">
          {message}
        </p>
      )}
    </div>
  );
}
