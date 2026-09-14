import { AlertTriangle, CheckCircle, ChevronRight, ClipboardList, FileSpreadsheet, Loader2, MapPin, Plus, Search } from "lucide-react";
import { useState } from "react";
import { Button, ButtonLink } from "../../components/Button";
import { PageHeader } from "../../components/Page";
import { useJourneys } from "../../lib/journey";
import {
  intakeApi,
  reviewReasonLabel,
  type FactsIn,
  type IntakeResult,
  type ParsedFactsOut,
} from "../../lib/intake";
import { ApiError } from "../../lib/api";
import { CsvTab } from "./CsvTab";

type Tab = "structured" | "url" | "paste" | "csv";
type Phase = "form" | "loading" | "result";

const TABS: { key: Tab; label: string; icon: React.ReactNode }[] = [
  { key: "structured", label: "Enter address", icon: <MapPin className="h-4 w-4" /> },
  { key: "url", label: "Paste from web", icon: <Search className="h-4 w-4" /> },
  { key: "paste", label: "Paste listing text", icon: <ClipboardList className="h-4 w-4" /> },
  { key: "csv", label: "Import CSV", icon: <FileSpreadsheet className="h-4 w-4" /> },
];

const AU_STATES = ["WA", "SA", "NT", "QLD", "NSW", "ACT", "VIC", "TAS"];
const PROPERTY_TYPES = [
  { value: "house", label: "House" },
  { value: "townhouse", label: "Townhouse" },
  { value: "villa", label: "Villa" },
  { value: "unit", label: "Unit" },
  { value: "apartment", label: "Apartment" },
  { value: "land", label: "Land" },
  { value: "acreage", label: "Acreage" },
];

// ── Shared field helpers ─────────────────────────────────────────────────────

function FieldLabel({ children, htmlFor }: { children: React.ReactNode; htmlFor?: string }) {
  return (
    <label htmlFor={htmlFor} className="block text-sm font-medium text-navy">
      {children}
    </label>
  );
}

function TextInput({
  id,
  value,
  onChange,
  placeholder,
  required,
  testId,
  maxLength,
}: {
  id?: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  required?: boolean;
  testId?: string;
  maxLength?: number;
}) {
  return (
    <input
      id={id}
      type="text"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      required={required}
      maxLength={maxLength}
      data-testid={testId}
      className="mt-1 h-10 w-full rounded-md border border-border bg-surface px-3 text-sm focus:border-navy focus:outline-none focus:ring-1 focus:ring-navy"
    />
  );
}

function IntInput({
  id,
  value,
  onChange,
  placeholder,
  testId,
  min = 0,
  max = 99,
}: {
  id?: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  testId?: string;
  min?: number;
  max?: number;
}) {
  return (
    <input
      id={id}
      type="number"
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder ?? "Unknown"}
      min={min}
      max={max}
      data-testid={testId}
      className="mt-1 h-10 w-full rounded-md border border-border bg-surface px-3 text-sm focus:border-navy focus:outline-none focus:ring-1 focus:ring-navy"
    />
  );
}

function Row({ children, cols = 2 }: { children: React.ReactNode; cols?: number }) {
  return (
    <div className={`grid gap-4 ${cols === 3 ? "sm:grid-cols-3" : "sm:grid-cols-2"}`}>
      {children}
    </div>
  );
}

// ── Address section (reused by structured + url tabs) ────────────────────────

interface AddressFields {
  address_line: string;
  suburb: string;
  state: string;
  postcode: string;
}

function AddressSection({
  fields,
  onChange,
}: {
  fields: AddressFields;
  onChange: (f: Partial<AddressFields>) => void;
}) {
  return (
    <div className="space-y-4">
      <h3 className="text-sm font-semibold uppercase tracking-wide text-muted">Address</h3>
      <div>
        <FieldLabel htmlFor="addr-line">Street address *</FieldLabel>
        <TextInput
          id="addr-line"
          value={fields.address_line}
          onChange={(v) => onChange({ address_line: v })}
          placeholder="e.g. 81A Smith Street"
          required
          testId="intake-address-line"
          maxLength={200}
        />
      </div>
      <Row cols={3}>
        <div className="sm:col-span-1">
          <FieldLabel htmlFor="addr-suburb">Suburb *</FieldLabel>
          <TextInput
            id="addr-suburb"
            value={fields.suburb}
            onChange={(v) => onChange({ suburb: v })}
            placeholder="Suburb"
            required
            testId="intake-suburb"
            maxLength={80}
          />
        </div>
        <div>
          <FieldLabel htmlFor="addr-state">State *</FieldLabel>
          <select
            id="addr-state"
            value={fields.state}
            onChange={(e) => onChange({ state: e.target.value })}
            data-testid="intake-state"
            className="mt-1 h-10 w-full rounded-md border border-border bg-surface px-3 text-sm focus:border-navy focus:outline-none focus:ring-1 focus:ring-navy"
          >
            <option value="">Select…</option>
            {AU_STATES.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        </div>
        <div>
          <FieldLabel htmlFor="addr-postcode">Postcode</FieldLabel>
          <TextInput
            id="addr-postcode"
            value={fields.postcode}
            onChange={(v) => onChange({ postcode: v })}
            placeholder="0000"
            testId="intake-postcode"
            maxLength={4}
          />
        </div>
      </Row>
    </div>
  );
}

// ── Facts section ────────────────────────────────────────────────────────────

function FactsSection({
  facts,
  onChange,
  previewFill,
}: {
  facts: FactsIn;
  onChange: (f: Partial<FactsIn>) => void;
  previewFill?: ParsedFactsOut | null;
}) {
  const hint = previewFill
    ? "Parsed values shown. Leave blank to keep Unknown."
    : "Leave any field blank to keep it Unknown.";

  return (
    <div className="space-y-4">
      <h3 className="text-sm font-semibold uppercase tracking-wide text-muted">
        Property facts <span className="font-normal normal-case">(all optional)</span>
      </h3>
      <p className="text-xs text-muted">{hint}</p>
      <Row>
        <div>
          <FieldLabel htmlFor="f-beds">Bedrooms</FieldLabel>
          <IntInput
            id="f-beds"
            value={facts.beds != null ? String(facts.beds) : ""}
            onChange={(v) => onChange({ beds: v === "" ? null : Number(v) })}
            testId="intake-beds"
            max={30}
          />
        </div>
        <div>
          <FieldLabel htmlFor="f-baths">Bathrooms</FieldLabel>
          <IntInput
            id="f-baths"
            value={facts.baths != null ? String(facts.baths) : ""}
            onChange={(v) => onChange({ baths: v === "" ? null : Number(v) })}
            testId="intake-baths"
            max={20}
          />
        </div>
      </Row>
      <Row>
        <div>
          <FieldLabel htmlFor="f-cars">Parking spaces</FieldLabel>
          <IntInput
            id="f-cars"
            value={facts.cars != null ? String(facts.cars) : ""}
            onChange={(v) => onChange({ cars: v === "" ? null : Number(v) })}
            testId="intake-cars"
            max={20}
          />
        </div>
        <div>
          <FieldLabel htmlFor="f-type">Property type</FieldLabel>
          <select
            id="f-type"
            value={facts.property_type ?? ""}
            onChange={(e) =>
              onChange({ property_type: e.target.value ? (e.target.value as FactsIn["property_type"]) : null })
            }
            data-testid="intake-property-type"
            className="mt-1 h-10 w-full rounded-md border border-border bg-surface px-3 text-sm focus:border-navy focus:outline-none focus:ring-1 focus:ring-navy"
          >
            <option value="">Unknown</option>
            {PROPERTY_TYPES.map((t) => (
              <option key={t.value} value={t.value}>{t.label}</option>
            ))}
          </select>
        </div>
      </Row>
      <Row>
        <div>
          <FieldLabel htmlFor="f-land">Land area (m²)</FieldLabel>
          <IntInput
            id="f-land"
            value={facts.land_sqm != null ? String(facts.land_sqm) : ""}
            onChange={(v) => onChange({ land_sqm: v === "" ? null : Number(v) })}
            testId="intake-land-sqm"
            max={99999}
          />
        </div>
        <div>
          <FieldLabel htmlFor="f-floor">Floor area (m²)</FieldLabel>
          <IntInput
            id="f-floor"
            value={facts.floor_sqm != null ? String(facts.floor_sqm) : ""}
            onChange={(v) => onChange({ floor_sqm: v === "" ? null : Number(v) })}
            testId="intake-floor-sqm"
            max={9999}
          />
        </div>
      </Row>
    </div>
  );
}

// ── Result display ────────────────────────────────────────────────────────────

function ResultPanel({ result, onAddAnother }: { result: IntakeResult; onAddAnother: () => void }) {
  const propUrl = result.property_id
    ? `/app/properties/${result.property_id}`
    : result.duplicate_property_id
    ? `/app/properties/${result.duplicate_property_id}`
    : null;

  if (result.state === "completed") {
    return (
      <div className="space-y-6 text-center" data-testid="intake-result-completed">
        <div className="mx-auto flex h-16 w-16 items-center justify-center rounded-full bg-eucalyptus-soft">
          <CheckCircle className="h-8 w-8 text-eucalyptus-deep" />
        </div>
        <div>
          <h2 className="text-h2 font-semibold text-navy">Property added</h2>
          <p className="mt-1 text-sm text-muted">
            Added to your review queue with all facts recorded.
          </p>
        </div>
        <div className="flex flex-wrap justify-center gap-3">
          {propUrl && (
            <ButtonLink to={propUrl} variant="primary" size="sm" data-testid="intake-view-property">
              View property <ChevronRight className="h-4 w-4" />
            </ButtonLink>
          )}
          <Button variant="secondary" size="sm" onClick={onAddAnother} data-testid="intake-add-another">
            Add another
          </Button>
        </div>
      </div>
    );
  }

  if (result.state === "duplicate") {
    return (
      <div className="space-y-6" data-testid="intake-result-duplicate">
        <div className="rounded-lg border border-ochre/40 bg-ochre-soft p-4">
          <div className="flex gap-3">
            <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-ochre-deep" />
            <div>
              <p className="font-semibold text-ochre-deep">Already in your workspace</p>
              <p className="mt-1 text-sm text-ochre-deep/80">
                {result.duplicate_address
                  ? `${result.duplicate_address} is already recorded.`
                  : "This property already exists in your workspace."}
              </p>
            </div>
          </div>
        </div>
        <div className="flex flex-wrap gap-3">
          {propUrl && (
            <ButtonLink to={propUrl} variant="primary" size="sm" data-testid="intake-view-duplicate">
              View existing property
            </ButtonLink>
          )}
          <Button variant="secondary" size="sm" onClick={onAddAnother} data-testid="intake-add-another">
            Add a different property
          </Button>
        </div>
      </div>
    );
  }

  if (result.state === "requires_review") {
    return (
      <div className="space-y-6" data-testid="intake-result-review">
        <div className="rounded-lg border border-border bg-navy-soft p-4">
          <p className="font-semibold text-navy">Added — flagged for review</p>
          <p className="mt-1 text-sm text-muted">
            The property was created but some details need your attention.
          </p>
          {result.review_reasons.length > 0 && (
            <ul className="mt-3 list-inside list-disc space-y-1 text-sm text-muted">
              {result.review_reasons.map((r) => (
                <li key={r}>{reviewReasonLabel(r)}</li>
              ))}
            </ul>
          )}
        </div>
        <div className="flex flex-wrap gap-3">
          {propUrl && (
            <ButtonLink to={propUrl} variant="primary" size="sm" data-testid="intake-view-review">
              Review property
            </ButtonLink>
          )}
          <Button variant="secondary" size="sm" onClick={onAddAnother} data-testid="intake-add-another">
            Add another
          </Button>
        </div>
      </div>
    );
  }

  return (
    <div data-testid="intake-result-failed">
      <p className="text-sm text-risk">An unexpected error occurred. Please try again.</p>
      <Button variant="secondary" size="sm" onClick={onAddAnother} className="mt-4">
        Try again
      </Button>
    </div>
  );
}

// ── Tab: Structured form ──────────────────────────────────────────────────────

function StructuredTab({
  journeyId,
  onResult,
}: {
  journeyId: string;
  onResult: (r: IntakeResult) => void;
}) {
  const [addr, setAddr] = useState<AddressFields>({
    address_line: "",
    suburb: "",
    state: "",
    postcode: "",
  });
  const [facts, setFacts] = useState<FactsIn>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canSubmit =
    addr.address_line.trim().length >= 2 &&
    addr.suburb.trim().length >= 1 &&
    addr.state.length >= 2;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;
    setError(null);
    setLoading(true);
    try {
      const result = await intakeApi.submit(journeyId, {
        mode: "structured_form",
        structured: {
          address_line: addr.address_line.trim(),
          suburb: addr.suburb.trim(),
          state: addr.state,
          postcode: addr.postcode.trim() || null,
          facts,
        },
      });
      onResult(result);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Submission failed. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6" data-testid="intake-structured-form">
      <AddressSection fields={addr} onChange={(f) => setAddr((s) => ({ ...s, ...f }))} />
      <hr className="border-border" />
      <FactsSection facts={facts} onChange={(f) => setFacts((s) => ({ ...s, ...f }))} />
      {error && (
        <p className="rounded-md bg-risk-soft p-3 text-sm text-risk" data-testid="intake-error">
          {error}
        </p>
      )}
      <Button
        type="submit"
        disabled={!canSubmit || loading}
        data-testid="intake-submit-structured"
        icon={loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
      >
        {loading ? "Adding…" : "Add property"}
      </Button>
    </form>
  );
}

// ── Tab: URL + facts ──────────────────────────────────────────────────────────

function UrlTab({
  journeyId,
  onResult,
}: {
  journeyId: string;
  onResult: (r: IntakeResult) => void;
}) {
  const [url, setUrl] = useState("");
  const [addr, setAddr] = useState<AddressFields>({
    address_line: "",
    suburb: "",
    state: "",
    postcode: "",
  });
  const [facts, setFacts] = useState<FactsIn>({});
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const canSubmit =
    url.trim().length > 0 &&
    addr.address_line.trim().length >= 2 &&
    addr.suburb.trim().length >= 1 &&
    addr.state.length >= 2;

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!canSubmit) return;
    setError(null);
    setLoading(true);
    try {
      const result = await intakeApi.submit(journeyId, {
        mode: "url_with_facts",
        url_with_facts: {
          source_url: url.trim(),
          address_line: addr.address_line.trim(),
          suburb: addr.suburb.trim(),
          state: addr.state,
          postcode: addr.postcode.trim() || null,
          facts,
        },
      });
      onResult(result);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Submission failed. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-6" data-testid="intake-url-form">
      <div>
        <FieldLabel htmlFor="url-src">Listing URL (saved as reference only — not fetched)</FieldLabel>
        <TextInput
          id="url-src"
          value={url}
          onChange={setUrl}
          placeholder="https://realestate.com.au/…"
          required
          testId="intake-url-input"
          maxLength={2000}
        />
        <p className="mt-1 text-xs text-muted">
          Stored as attribution. The URL is never visited or scraped.
        </p>
      </div>
      <hr className="border-border" />
      <AddressSection fields={addr} onChange={(f) => setAddr((s) => ({ ...s, ...f }))} />
      <hr className="border-border" />
      <FactsSection facts={facts} onChange={(f) => setFacts((s) => ({ ...s, ...f }))} />
      {error && (
        <p className="rounded-md bg-risk-soft p-3 text-sm text-risk" data-testid="intake-error">
          {error}
        </p>
      )}
      <Button
        type="submit"
        disabled={!canSubmit || loading}
        data-testid="intake-submit-url"
        icon={loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
      >
        {loading ? "Adding…" : "Add property"}
      </Button>
    </form>
  );
}

// ── Tab: Paste text ───────────────────────────────────────────────────────────

function PasteTab({
  journeyId,
  onResult,
}: {
  journeyId: string;
  onResult: (r: IntakeResult) => void;
}) {
  const [text, setText] = useState("");
  const [preview, setPreview] = useState<ParsedFactsOut | null>(null);
  const [overrides, setOverrides] = useState<FactsIn>({});
  const [stage, setStage] = useState<"input" | "preview">("input");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleParse() {
    if (!text.trim()) return;
    setError(null);
    setLoading(true);
    try {
      const pf = await intakeApi.parsePreview(journeyId, text);
      setPreview(pf);
      // Pre-fill overrides with parsed facts so fields show extracted values
      setOverrides({
        beds: pf.beds,
        baths: pf.baths,
        cars: pf.cars,
        land_sqm: pf.land_sqm,
        floor_sqm: pf.floor_sqm,
        property_type: pf.property_type as FactsIn["property_type"] ?? null,
      });
      setStage("preview");
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Parsing failed. Try again.");
    } finally {
      setLoading(false);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    setLoading(true);
    try {
      const result = await intakeApi.submit(journeyId, {
        mode: "pasted_text",
        pasted_text: { raw_text: text, overrides },
      });
      onResult(result);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Submission failed. Please try again.");
    } finally {
      setLoading(false);
    }
  }

  if (stage === "input") {
    return (
      <div className="space-y-4" data-testid="intake-paste-input">
        <p className="text-sm text-muted">
          Paste a listing snippet — address, bed/bath/car count, land size, price. The parser
          extracts what it can. You can review and correct before saving.
        </p>
        <div>
          <FieldLabel htmlFor="paste-text">Listing text</FieldLabel>
          <textarea
            id="paste-text"
            value={text}
            onChange={(e) => setText(e.target.value)}
            rows={8}
            maxLength={10000}
            placeholder={"3 bed 2 bath 2 car\n81A Smith Street, Fremantle WA 6160\nLand: 450m²\nOffers over $820,000"}
            data-testid="intake-paste-text"
            className="mt-1 w-full rounded-md border border-border bg-surface px-3 py-2.5 font-mono text-sm focus:border-navy focus:outline-none focus:ring-1 focus:ring-navy"
          />
          <p className="mt-1 text-xs text-muted">{text.length}/10000 characters</p>
        </div>
        {error && (
          <p className="rounded-md bg-risk-soft p-3 text-sm text-risk" data-testid="intake-error">
            {error}
          </p>
        )}
        <Button
          onClick={handleParse}
          disabled={text.trim().length < 5 || loading}
          data-testid="intake-parse-btn"
          icon={loading ? <Loader2 className="h-4 w-4 animate-spin" /> : undefined}
        >
          {loading ? "Parsing…" : "Parse and preview"}
        </Button>
      </div>
    );
  }

  // Preview stage
  return (
    <form onSubmit={handleSubmit} className="space-y-6" data-testid="intake-paste-preview">
      {preview && (
        <div className="rounded-md border border-border bg-canvas-deep/50 p-4 text-sm">
          <p className="mb-2 font-semibold text-navy">Extracted address</p>
          {preview.address_line ? (
            <p className="text-muted">
              {preview.address_line}, {preview.suburb} {preview.state} {preview.postcode}
            </p>
          ) : (
            <p className="text-ochre-deep">
              Address not found — you will need to add it manually after saving.
            </p>
          )}
          {preview.review_reasons.length > 0 && (
            <ul className="mt-2 list-inside list-disc space-y-0.5 text-xs text-muted">
              {preview.review_reasons.map((r) => (
                <li key={r}>{reviewReasonLabel(r)}</li>
              ))}
            </ul>
          )}
        </div>
      )}
      <FactsSection
        facts={overrides}
        onChange={(f) => setOverrides((s) => ({ ...s, ...f }))}
        previewFill={preview}
      />
      {error && (
        <p className="rounded-md bg-risk-soft p-3 text-sm text-risk" data-testid="intake-error">
          {error}
        </p>
      )}
      <div className="flex flex-wrap gap-3">
        <Button
          type="submit"
          disabled={loading}
          data-testid="intake-submit-paste"
          icon={loading ? <Loader2 className="h-4 w-4 animate-spin" /> : <Plus className="h-4 w-4" />}
        >
          {loading ? "Adding…" : "Confirm and add"}
        </Button>
        <Button
          type="button"
          variant="secondary"
          onClick={() => setStage("input")}
          data-testid="intake-back-to-text"
        >
          Edit text
        </Button>
      </div>
    </form>
  );
}

// ── Page ─────────────────────────────────────────────────────────────────────

export default function AddPropertyPage() {
  const { active, loading: journeyLoading } = useJourneys();
  const [tab, setTab] = useState<Tab>("structured");
  const [phase, setPhase] = useState<Phase>("form");
  const [result, setResult] = useState<IntakeResult | null>(null);
  const [formKey, setFormKey] = useState(0);

  function handleResult(r: IntakeResult) {
    setResult(r);
    setPhase("result");
  }

  function handleAddAnother() {
    setResult(null);
    setPhase("form");
    setFormKey((k) => k + 1);
  }

  if (journeyLoading) {
    return (
      <>
        <PageHeader eyebrow="Add property" title="Add a property" testId="intake-header" />
        <div className="flex items-center gap-2 text-sm text-muted">
          <Loader2 className="h-4 w-4 animate-spin" />
          Loading your journey…
        </div>
      </>
    );
  }

  if (!active) {
    return (
      <>
        <PageHeader eyebrow="Add property" title="Add a property" testId="intake-header" />
        <div className="card max-w-md p-6 text-center">
          <p className="text-muted">You need a buying journey before adding properties.</p>
          <ButtonLink to="/app/journeys/new" variant="primary" size="sm" className="mt-4">
            Create a journey
          </ButtonLink>
        </div>
      </>
    );
  }

  return (
    <>
      <PageHeader
        eyebrow="Add property"
        title="Add a property"
        description="Enter an address, paste a listing URL, or drop in listing text for the parser to extract facts."
        testId="intake-header"
        actions={
          <ButtonLink to="/app/discover" variant="secondary" size="sm" data-testid="intake-back-discover">
            Back to Discover
          </ButtonLink>
        }
      />

      <div className="mx-auto max-w-2xl">
        {/* Tab bar */}
        {phase === "form" && (
          <div
            className="mb-6 flex rounded-lg border border-border bg-surface p-1"
            role="tablist"
            aria-label="Intake mode"
            data-testid="intake-tab-bar"
          >
            {TABS.map((t) => (
              <button
                key={t.key}
                type="button"
                role="tab"
                aria-selected={tab === t.key}
                onClick={() => setTab(t.key)}
                data-testid={`intake-tab-${t.key}`}
                className={`flex flex-1 items-center justify-center gap-1.5 rounded-md px-3 py-2 text-sm font-medium transition-colors duration-150 ${
                  tab === t.key
                    ? "bg-navy text-white shadow-sm"
                    : "text-muted hover:text-navy"
                }`}
              >
                {t.icon}
                <span className="hidden sm:inline">{t.label}</span>
              </button>
            ))}
          </div>
        )}

        <div className="card p-6" data-testid="intake-card">
          {phase === "result" && result ? (
            <ResultPanel result={result} onAddAnother={handleAddAnother} />
          ) : tab === "structured" ? (
            <StructuredTab key={`s-${formKey}`} journeyId={active.id} onResult={handleResult} />
          ) : tab === "url" ? (
            <UrlTab key={`u-${formKey}`} journeyId={active.id} onResult={handleResult} />
          ) : tab === "csv" ? (
            <CsvTab key={`c-${formKey}`} journeyId={active.id} />
          ) : (
            <PasteTab key={`p-${formKey}`} journeyId={active.id} onResult={handleResult} />
          )}
        </div>
      </div>
    </>
  );
}
