import type { Mode, PolicyChoice, PropertyType, RenovationLevel, TimingHorizon } from "./api";

export const MODE_OPTIONS: { value: Mode; label: string }[] = [
  { value: "hard", label: "Hard rule" },
  { value: "preference", label: "Preference" },
  { value: "disabled", label: "Disabled" },
  { value: "unknown", label: "Unknown" },
];

export const MODE_HELP: Record<Mode, string> = {
  hard: "A known failure excludes the property. Unknown facts route to verification.",
  preference: "Scored against your weights. Never excludes on its own.",
  disabled: "Ignored entirely by matching.",
  unknown: "You have not decided yet. Unknown is never treated as pass or fail.",
};

export const PROPERTY_TYPE_OPTIONS: { value: PropertyType; label: string }[] = [
  { value: "house", label: "House" },
  { value: "townhouse", label: "Townhouse" },
  { value: "villa", label: "Villa" },
  { value: "unit", label: "Unit" },
  { value: "apartment", label: "Apartment" },
  { value: "land", label: "Land" },
  { value: "acreage", label: "Acreage" },
];

export const TIMING_OPTIONS: { value: TimingHorizon; label: string }[] = [
  { value: "asap", label: "As soon as the right property appears" },
  { value: "3_months", label: "Within 3 months" },
  { value: "6_months", label: "Within 6 months" },
  { value: "12_months", label: "Within 12 months" },
  { value: "exploring", label: "Exploring, no timeline" },
];

export const RENOVATION_OPTIONS: { value: RenovationLevel; label: string }[] = [
  { value: "none", label: "Move-in ready only" },
  { value: "cosmetic", label: "Cosmetic work accepted" },
  { value: "moderate", label: "Moderate renovation accepted" },
  { value: "structural", label: "Structural work accepted" },
];

export const POLICY_OPTIONS: { value: PolicyChoice; label: string }[] = [
  { value: "include", label: "Include normally" },
  { value: "exclude", label: "Exclude" },
  { value: "flag", label: "Include and flag for review" },
];

export const TIMEZONE_OPTIONS = [
  { value: "Australia/Perth", label: "Australia/Perth (AWST)" },
  { value: "Australia/Adelaide", label: "Australia/Adelaide (ACST)" },
  { value: "Australia/Darwin", label: "Australia/Darwin (ACST)" },
  { value: "Australia/Brisbane", label: "Australia/Brisbane (AEST)" },
  { value: "Australia/Sydney", label: "Australia/Sydney (AEST/AEDT)" },
  { value: "Australia/Melbourne", label: "Australia/Melbourne (AEST/AEDT)" },
  { value: "Australia/Hobart", label: "Australia/Hobart (AEST/AEDT)" },
];

export const labelFor = <T extends string>(options: { value: T; label: string }[], value: T | null): string =>
  value === null ? "Unknown" : (options.find((o) => o.value === value)?.label ?? "Unknown");
