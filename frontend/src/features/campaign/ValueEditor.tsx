import type { Cadence, SettingKey } from "../../lib/campaigns";
import { TIMEZONE_OPTIONS } from "../../lib/briefOptions";
import { CadenceEditor } from "./CadenceEditor";

export interface EditorOptions {
  profiles: { value: string; label: string }[];
  connections: { value: string; label: string }[];
  recipients: { value: string; label: string }[];
}

const control = "h-10 w-full max-w-md rounded-md border border-border bg-surface px-3 text-sm";

const pad = (n: number) => String(n).padStart(2, "0");
const toLocalInput = (iso: string): string => {
  const d = new Date(iso);
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`;
};

function Select({ id, label, value, options, onChange }: { id: string; label: string; value: string; options: { value: string; label: string }[]; onChange: (v: string) => void }) {
  return (
    <select id={id} aria-label={label} value={value} onChange={(e) => onChange(e.target.value)} className={control} data-testid={id}>
      {options.map((o) => <option key={o.value} value={o.value}>{o.label}</option>)}
    </select>
  );
}

/** The value control for one setting; only rendered when the layer sets a value. */
export function ValueEditor({ id, settingKey, value, onChange, options }: {
  id: string; settingKey: SettingKey; value: unknown; onChange: (v: unknown) => void; options: EditorOptions;
}) {
  switch (settingKey) {
    case "assessment_profile":
      return <Select id={id} label="Assessment profile" value={String(value)} options={options.profiles} onChange={onChange} />;
    case "timezone":
      return <Select id={id} label="Timezone" value={String(value)} options={TIMEZONE_OPTIONS} onChange={onChange} />;
    case "recipient_user_id":
      return <Select id={id} label="Report recipient" value={String(value)} options={options.recipients} onChange={onChange} />;
    case "delivery_mode":
      return (
        <Select id={id} label="Delivery mode" value={String(value)} onChange={onChange}
          options={[{ value: "separate", label: "Separate report per campaign" }, { value: "combined", label: "Combined (arrives in U6 — delivered separately until then)" }]} />
      );
    case "intake_connection_ref":
      return (
        <Select id={id} label="Intake connection" value={value === null ? "none" : String(value)} onChange={(v) => onChange(v === "none" ? null : v)}
          options={[{ value: "none", label: "None" }, ...options.connections]} />
      );
    case "activation_at":
      return (
        <div className="flex flex-wrap items-center gap-2">
          <Select id={`${id}-mode`} label="Activation" value={value === null ? "none" : "at"} onChange={(v) => onChange(v === "none" ? null : new Date().toISOString())}
            options={[{ value: "none", label: "Not activated" }, { value: "at", label: "Activate at…" }]} />
          {value !== null && (
            <input type="datetime-local" aria-label="Activation date and time" value={toLocalInput(String(value))} className={control}
              onChange={(e) => e.target.value && onChange(new Date(e.target.value).toISOString())} data-testid={`${id}-at`} />
          )}
        </div>
      );
    case "cadence":
      return <CadenceEditor id={id} value={value as Cadence} onChange={onChange} />;
  }
}
