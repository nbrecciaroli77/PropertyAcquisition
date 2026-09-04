export type PriceKind =
  | "Exact"
  | "Range"
  | "From"
  | "Offers over"
  | "Auction"
  | "Contact agent"
  | "Expressions of interest"
  | "Conflicting";

export type MarketState = "Active" | "Under offer" | "Withdrawn" | "Sold" | "Unknown";

export type BuyerState =
  | "Reviewing"
  | "Shortlisted"
  | "Inspection considered"
  | "Inspected"
  | "Due diligence"
  | "Offer preparation"
  | "Offer submitted"
  | "Under contract"
  | "Settled"
  | "Rejected"
  | "Archived";

export type GateOutcome = "Pass" | "Fail" | "Unknown";

export type EvidenceKind = "original-source" | "partial" | "conflict" | "manual";

/** Tri-state numeric: never coerce unknown to zero. */
export type Tri<T> = { state: "known"; value: T } | { state: "unknown" } | { state: "not-applicable" };

export interface SyntheticProperty {
  id: string;
  legacyRef: string;
  address: string;
  suburb: string;
  state: string;
  priceKind: PriceKind;
  rawPrice: string;
  lowerPrice?: number;
  upperPrice?: number;
  beds: Tri<number>;
  baths: Tri<number>;
  cars: Tri<number>;
  landSqm: Tri<number>;
  marketState: MarketState;
  buyerState: BuyerState;
  condition: string | null;
  locationTier: string;
  evidence: EvidenceKind;
  /** Display-only synthetic evaluation. Real evaluation arrives in Milestone 3. */
  fit: Tri<number>;
  coverage: Tri<number>;
  gate: GateOutcome;
  gateReason: string;
  lastChecked: string;
  sourceLabel: string;
  saved: boolean;
}
