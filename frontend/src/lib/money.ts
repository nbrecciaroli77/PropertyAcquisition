/** Money is stored as integer minor units with a currency. Never guess a missing bound. */
export const minorToDollars = (minor: number | null): number | null => (minor === null ? null : Math.round(minor / 100));

export const dollarsToMinor = (dollars: number | null): number | null =>
  dollars === null ? null : Math.round(dollars * 100);

export const formatMinor = (minor: number | null): string =>
  minor === null
    ? "Unknown"
    : new Intl.NumberFormat("en-AU", { style: "currency", currency: "AUD", maximumFractionDigits: 0 }).format(
        minor / 100,
      );
