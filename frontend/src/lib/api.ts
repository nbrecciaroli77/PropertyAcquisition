const base = process.env.REACT_APP_BACKEND_URL;

export interface Meta {
  app_name: string;
  working_name_status: string;
  gate: string;
  milestone: number;
  synthetic_data_only: boolean;
  flags: Record<string, "off" | "on" | "locked_off">;
}

export async function fetchMeta(): Promise<Meta> {
  const res = await fetch(`${base}/api/meta`);
  if (!res.ok) throw new Error(`meta ${res.status}`);
  return res.json() as Promise<Meta>;
}
