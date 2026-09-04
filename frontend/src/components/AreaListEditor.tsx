import { Plus, Trash2 } from "lucide-react";
import { useState } from "react";
import type { Area, StateTerritory } from "../lib/api";
import { Button } from "./Button";
import { SelectField, TextField } from "./Form";

export const STATE_OPTIONS: { value: StateTerritory; label: string }[] = [
  { value: "WA", label: "Western Australia" },
  { value: "SA", label: "South Australia" },
  { value: "NT", label: "Northern Territory" },
  { value: "QLD", label: "Queensland" },
  { value: "NSW", label: "New South Wales" },
  { value: "ACT", label: "Australian Capital Territory" },
  { value: "VIC", label: "Victoria" },
  { value: "TAS", label: "Tasmania" },
];

export function AreaListEditor({
  idPrefix,
  legend,
  description,
  areas,
  onChange,
  defaultState = "WA",
  error,
}: {
  idPrefix: string;
  legend: string;
  description: string;
  areas: Area[];
  onChange: (areas: Area[]) => void;
  defaultState?: StateTerritory;
  error?: string;
}) {
  const [suburb, setSuburb] = useState("");
  const [postcode, setPostcode] = useState("");
  const [state, setState] = useState<StateTerritory>(defaultState);

  const add = () => {
    const trimmed = suburb.trim();
    if (!trimmed) return;
    onChange([...areas, { suburb: trimmed, state, postcode: postcode.trim() || null }]);
    setSuburb("");
    setPostcode("");
  };

  return (
    <fieldset className="min-w-0" data-testid={`${idPrefix}-editor`}>
      <legend className="text-sm font-semibold">{legend}</legend>
      <p className="mt-1 text-xs text-muted">{description}</p>

      {areas.length > 0 && (
        <ul className="mt-3 space-y-2" data-testid={`${idPrefix}-list`}>
          {areas.map((area, index) => (
            <li
              key={`${area.suburb}-${area.state}-${index}`}
              className="flex items-center justify-between gap-3 rounded-md border border-border bg-surface px-3 py-2 text-sm"
              data-testid={`${idPrefix}-item-${index}`}
            >
              <span className="min-w-0 truncate">
                <strong className="font-semibold">{area.suburb}</strong>, {area.state}
                {area.postcode ? ` ${area.postcode}` : ""}
              </span>
              <Button
                variant="tertiary"
                size="sm"
                onClick={() => onChange(areas.filter((_, i) => i !== index))}
                aria-label={`Remove ${area.suburb}, ${area.state}`}
                data-testid={`${idPrefix}-remove-${index}`}
                icon={<Trash2 className="h-4 w-4" aria-hidden="true" />}
              >
                Remove
              </Button>
            </li>
          ))}
        </ul>
      )}

      <div className="mt-3 grid gap-3 sm:grid-cols-[minmax(0,2fr)_minmax(0,1fr)_minmax(0,1.4fr)_auto] sm:items-end">
        <TextField id={`${idPrefix}-suburb`} label="Suburb" value={suburb} onChange={setSuburb} />
        <TextField
          id={`${idPrefix}-postcode`}
          label="Postcode"
          value={postcode}
          onChange={setPostcode}
          inputMode="numeric"
        />
        <SelectField id={`${idPrefix}-state`} label="State" value={state} onChange={setState} options={STATE_OPTIONS} />
        <Button
          variant="secondary"
          onClick={add}
          icon={<Plus className="h-4 w-4" aria-hidden="true" />}
          data-testid={`${idPrefix}-add`}
        >
          Add
        </Button>
      </div>
      {error && (
        <p className="mt-2 text-xs font-semibold text-risk" data-testid={`${idPrefix}-error`}>
          {error}
        </p>
      )}
    </fieldset>
  );
}
