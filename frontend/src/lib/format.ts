import { displayNow } from "./clock";
import type { Tri } from "./types";

const aud = new Intl.NumberFormat("en-AU", { style: "currency", currency: "AUD", maximumFractionDigits: 0 });

export const formatAud = (value: number): string => aud.format(value);

export const formatSqm = (value: number): string => `${new Intl.NumberFormat("en-AU").format(value)} m²`;

export const triText = <T,>(t: Tri<T>, render: (v: T) => string): string => {
  if (t.state === "known") return render(t.value);
  if (t.state === "not-applicable") return "Not applicable";
  return "Unknown";
};

const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/** Deterministic "1 Jun 2026" regardless of ICU build; rendered in the workspace timezone. */
export const formatDate = (iso: string, timeZone = "Australia/Perth"): string => {
  const parts = new Intl.DateTimeFormat("en-AU", { day: "numeric", month: "numeric", year: "numeric", timeZone }).formatToParts(new Date(iso));
  const get = (t: string) => parts.find((p) => p.type === t)?.value ?? "";
  return `${Number(get("day"))} ${MONTHS[Number(get("month")) - 1]} ${get("year")}`;
};

export const relativeDays = (iso: string, now: Date = displayNow()): string => {
  const days = Math.round((now.getTime() - new Date(iso).getTime()) / 86_400_000);
  if (days <= 0) return "today";
  if (days === 1) return "1 day ago";
  return `${days} days ago`;
};

export const known = <T,>(value: T): Tri<T> => ({ state: "known", value });
export const unknown = <T,>(): Tri<T> => ({ state: "unknown" });
