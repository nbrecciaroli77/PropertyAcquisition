import type { ChipTone } from "../components/StatusChip";
import type { EvaluationOut, LandAssessment } from "./properties";
import { formatMinor } from "./money";

export const landStatusText = (land: LandAssessment): string =>
  land.status === "SUPPORTED" ? "Priority 1 · supported" : land.status === "PROVISIONAL" ? "Priority 2 · provisional" : "Excluded";

export const landTone = (land: LandAssessment): ChipTone =>
  land.status === "SUPPORTED" ? "pass" : land.status === "PROVISIONAL" ? "unknown" : "fail";

/** Chip text for any evaluation: land shows its research priority, house keeps its gate verdict text. */
export const evaluationChip = (e: EvaluationOut | null, houseText: (v: EvaluationOut["verdict"]) => string): string =>
  e === null ? "Not evaluated" : e.land ? landStatusText(e.land) : houseText(e.verdict);

const CEILING: Record<string, string> = {
  confirmed: "Confirmed by the seller",
  unverified: "Unverified",
  opening_guide_unverified: "Opening guide — not a ceiling",
};

const VERIFY: Record<string, string> = {
  LAND_COMPONENT_UNKNOWN: "Package or advertised amount without a supported land component",
  PRICE_ANOMALOUS_VERIFY: "Anomalous amount — verify; not treated as rent or a land price",
  OPENING_GUIDE_NOT_CEILING: "Opening guide — the seller ceiling is unverified",
  UNPRICED: "No price yet",
};

export const ceilingText = (key: string): string => CEILING[key] ?? key;
export const verificationText = (key: string | null): string | null => (key ? VERIFY[key] ?? key : null);
export const sqm = (value: number | null): string => (value === null ? "Unknown" : `${value.toLocaleString("en-AU")} m²`);
export const money = (minor: number | null): string => formatMinor(minor);
