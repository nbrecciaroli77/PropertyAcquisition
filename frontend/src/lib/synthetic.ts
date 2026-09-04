import demo from "../data/demo-data.json";
import { known, unknown } from "./format";
import type { GateOutcome, SyntheticProperty, Tri } from "./types";

type RawProperty = (typeof demo)["properties"][number];

const tri = (v: number | null | undefined): Tri<number> => (typeof v === "number" ? known(v) : unknown());

/** Display-only evaluation placeholders keyed by legacyRef. Milestone 3 replaces these with gates_v1/scoring_v1. */
const displayEval: Record<
  string,
  { fit: Tri<number>; coverage: Tri<number>; gate: GateOutcome; gateReason: string; lastChecked: string; saved: boolean }
> = {
  "DEMO-001": { fit: known(82), coverage: known(90), gate: "Pass", gateReason: "All hard rules pass on original-source facts", lastChecked: "2026-06-18T07:42:00+08:00", saved: true },
  "DEMO-002": { fit: unknown(), coverage: known(45), gate: "Unknown", gateReason: "Price unpriced (Contact agent) and condition unknown — verification required", lastChecked: "2026-06-17T18:10:00+08:00", saved: false },
  "DEMO-003": { fit: known(74), coverage: known(88), gate: "Fail", gateReason: "Land 318 m² is below the 400 m² hard rule", lastChecked: "2026-06-16T09:00:00+08:00", saved: false },
  "DEMO-004": { fit: unknown(), coverage: known(60), gate: "Unknown", gateReason: "Price guide conflicts between index and detail — verification required", lastChecked: "2026-06-18T06:18:00+08:00", saved: false },
  "DEMO-005": { fit: known(77), coverage: known(72), gate: "Pass", gateReason: "All hard rules pass on manual entry", lastChecked: "2026-06-15T12:30:00+08:00", saved: true },
  "DEMO-006": { fit: unknown(), coverage: known(38), gate: "Unknown", gateReason: "Land size unknown — cannot assess land rule", lastChecked: "2026-06-15T12:31:00+08:00", saved: false },
  "DEMO-007": { fit: known(80), coverage: known(86), gate: "Pass", gateReason: "All hard rules pass; market state is Under offer (not your offer)", lastChecked: "2026-06-12T08:05:00+08:00", saved: false },
};

const sourceLabel: Record<RawProperty["evidence"], string> = {
  "original-source": "Original listing (synthetic)",
  partial: "Partial listing (synthetic)",
  conflict: "Two sources in conflict (synthetic)",
  manual: "Manual entry",
};

export const workspace = demo.workspace;
export const brief = demo.brief;

export const properties: SyntheticProperty[] = demo.properties.map((p) => {
  const e = displayEval[p.legacyRef];
  return {
    id: p.legacyRef.toLowerCase(),
    legacyRef: p.legacyRef,
    address: p.address,
    suburb: p.suburb,
    state: p.state,
    priceKind: p.priceKind as SyntheticProperty["priceKind"],
    rawPrice: p.rawPrice,
    lowerPrice: "lowerPrice" in p ? (p as { lowerPrice?: number }).lowerPrice : undefined,
    upperPrice: "upperPrice" in p ? (p as { upperPrice?: number }).upperPrice : undefined,
    beds: tri(p.beds),
    baths: tri(p.baths),
    cars: tri(p.cars),
    landSqm: tri(p.landSqm),
    marketState: p.marketState as SyntheticProperty["marketState"],
    buyerState: p.buyerState as SyntheticProperty["buyerState"],
    condition: p.condition,
    locationTier: p.locationTier,
    evidence: p.evidence as SyntheticProperty["evidence"],
    sourceLabel: sourceLabel[p.evidence as RawProperty["evidence"]],
    ...e,
  };
});

export const findProperty = (id: string): SyntheticProperty | undefined => properties.find((p) => p.id === id);

export const displayUser = { name: "Nick", initials: "NB", email: "owner@example.invalid" };
