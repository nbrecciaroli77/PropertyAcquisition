/** Draft editing works on a copy so a failed save never leaves half-applied edits. */
export const deepClone = <T,>(value: T): T =>
  typeof structuredClone === "function" ? structuredClone(value) : (JSON.parse(JSON.stringify(value)) as T);
