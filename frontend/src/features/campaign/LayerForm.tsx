import { useState } from "react";
import { Button } from "../../components/Button";
import { FormNotice, TextField } from "../../components/Form";
import { ApiError } from "../../lib/api";
import { INHERIT, SETTING_KEYS, type CampaignLayer, type SettingKey } from "../../lib/campaigns";
import { LayerRow } from "./LayerRow";
import { SETTING_LABELS } from "./settingFormat";
import { ValueEditor, type EditorOptions } from "./ValueEditor";

const HINTS: Partial<Record<SettingKey, string>> = {
  activation_at: "Production reports are blocked until activation and never cover a period before it. Previews are unaffected.",
  intake_connection_ref: "Recorded as a reference only — live intake connectors are disabled in this build.",
  delivery_mode: "Nothing is emailed in this build; delivery mode only shapes future report packaging.",
};

/** Edits one immutable configuration layer. Each save appends a version with a reason. */
export function LayerForm({ prefix, initial, seeds, version, options, inheritLabel, onSave }: {
  prefix: string;
  initial: CampaignLayer;
  seeds: Record<SettingKey, unknown>;
  version: number;
  options: EditorOptions;
  inheritLabel: string;
  onSave: (layer: CampaignLayer, reason: string, expectedVersion: number) => Promise<string>;
}) {
  const [layer, setLayer] = useState<CampaignLayer>(initial);
  const [reason, setReason] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const set = (key: SettingKey, value: unknown) => setLayer((current) => ({ ...current, [key]: value }));

  const save = async () => {
    setBusy(true);
    setError(null);
    setNotice(null);
    try {
      setNotice(await onSave(layer, reason.trim(), version));
      setReason("");
    } catch (e) {
      setError(e instanceof ApiError && e.code === "stale_configuration" ? "These settings changed in another session. Reload the page before saving again." : e instanceof Error ? e.message : "Settings could not be saved.");
    } finally {
      setBusy(false);
    }
  };

  return (
    <form className="mt-2" onSubmit={(e) => { e.preventDefault(); void save(); }} data-testid={`${prefix}-form`}>
      {SETTING_KEYS.map((key) => (
        <LayerRow key={key} id={`${prefix}-${key}`} label={SETTING_LABELS[key]} inherited={layer[key] === INHERIT} inheritLabel={inheritLabel} setLabel="Set here"
          onInherit={() => set(key, INHERIT)} onSet={() => layer[key] === INHERIT && set(key, seeds[key])} hint={HINTS[key]}>
          <ValueEditor id={`${prefix}-${key}-value`} settingKey={key} value={layer[key]} onChange={(v) => set(key, v)} options={options} />
        </LayerRow>
      ))}
      <div className="mt-4 space-y-3 border-t border-border pt-4">
        <TextField id={`${prefix}-reason`} label="Reason for this change" value={reason} onChange={setReason} helper="Saved with the new version, your name and the time." />
        {error && <FormNotice tone="error" testId={`${prefix}-error`}>{error}</FormNotice>}
        {notice && <FormNotice tone="success" testId={`${prefix}-notice`}>{notice}</FormNotice>}
        <Button type="submit" disabled={busy || reason.trim().length < 3} data-testid={`${prefix}-save`}>
          {busy ? "Saving…" : `Save as version ${version + 1}`}
        </Button>
      </div>
    </form>
  );
}
