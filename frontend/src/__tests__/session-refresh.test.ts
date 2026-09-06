import { SESSION_EXPIRED_EVENT, apiFetch } from "../lib/api";

type Call = { url: string; method: string };

function installFetch(script: Array<{ status: number; body?: unknown }>, calls: Call[]) {
  const queue = [...script];
  global.fetch = jest.fn(async (url: RequestInfo | URL, init?: RequestInit) => {
    calls.push({ url: String(url), method: init?.method ?? "GET" });
    const next = queue.shift() ?? { status: 500, body: { detail: "unexpected" } };
    return {
      ok: next.status < 400,
      status: next.status,
      json: async () => next.body ?? {},
    } as unknown as Response;
  }) as unknown as typeof fetch;
}

describe("apiFetch session refresh", () => {
  const original = global.fetch;
  afterEach(() => {
    global.fetch = original;
  });

  it("refreshes once and replays the original request after an expired access token", async () => {
    const calls: Call[] = [];
    installFetch(
      [
        { status: 401, body: { detail: "Not authenticated" } },
        { status: 200, body: { user: {} } },
        { status: 201, body: { id: "j1" } },
      ],
      calls,
    );
    const out = await apiFetch<{ id: string }>("/journeys", { method: "POST", body: "{}" });
    expect(out).toEqual({ id: "j1" });
    expect(calls.map((c) => `${c.method} ${c.url.split("/api")[1]}`)).toEqual([
      "POST /journeys",
      "POST /auth/refresh",
      "POST /journeys",
    ]);
  });

  it("signals session expiry and surfaces the 401 when the refresh fails", async () => {
    const calls: Call[] = [];
    installFetch(
      [
        { status: 401, body: { detail: "Not authenticated" } },
        { status: 401, body: { detail: "Session expired" } },
      ],
      calls,
    );
    const expired = jest.fn();
    window.addEventListener(SESSION_EXPIRED_EVENT, expired);
    await expect(apiFetch("/journeys")).rejects.toMatchObject({ status: 401 });
    expect(expired).toHaveBeenCalledTimes(1);
    expect(calls).toHaveLength(2);
    window.removeEventListener(SESSION_EXPIRED_EVENT, expired);
  });

  it("never tries to refresh a failed login", async () => {
    const calls: Call[] = [];
    installFetch([{ status: 401, body: { detail: "Invalid email or password" } }], calls);
    await expect(apiFetch("/auth/login", { method: "POST", body: "{}" })).rejects.toMatchObject({ status: 401 });
    expect(calls).toHaveLength(1);
  });
});
