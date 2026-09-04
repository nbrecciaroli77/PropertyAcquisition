import { Check, CircleHelp, Leaf, Lock, Search, ShieldCheck } from "lucide-react";
import { ButtonLink } from "../../components/Button";
import { FitRing } from "../../components/FitRing";
import { known } from "../../lib/format";

const steps = [
  { n: 1, title: "Set your brief", body: "Capture needs, preferences and deal-breakers." },
  { n: 2, title: "Bring opportunities together", body: "Save properties and add notes from the sources you choose." },
  { n: 3, title: "Check fit and evidence", body: "See what matches, what conflicts and what is still unknown." },
  { n: 4, title: "Compare and plan", body: "Compare options and organise the next checks." },
  { n: 5, title: "You decide and act", body: "Nothing is sent, offered or committed without your action." },
];

const trust = [
  { icon: ShieldCheck, title: "Your brief stays yours", body: "Your brief, notes and shortlist are private by default. You control what, if anything, you share." },
  { icon: Search, title: "Unknown is not Pass", body: "We call out unknowns clearly so you can decide what to check next." },
  { icon: Lock, title: "Nothing is sent without your action", body: "We never contact agents, request information or send anything on your behalf." },
];

const checklist: { label: string; state: "found" | "some" | "unknown" }[] = [
  { label: "Location", state: "found" },
  { label: "Land size", state: "found" },
  { label: "Flood risk", state: "some" },
  { label: "Building condition", state: "found" },
  { label: "Future development", state: "unknown" },
];

export default function AboutPage() {
  return (
    <div className="mx-auto w-full max-w-[1400px] px-4 py-10 md:px-8 md:py-14" data-testid="about-page">
      <section className="grid gap-10 lg:grid-cols-[minmax(0,1fr)_minmax(0,1.1fr)] lg:items-center" aria-labelledby="about-heading">
        <div className="rise-in">
          <p className="label mb-3 text-ochre-deep">Working concept</p>
          <h1 id="about-heading" className="text-4xl font-semibold tracking-tight sm:text-5xl lg:text-6xl lg:leading-[1.05]">
            A clearer way to buy property
          </h1>
          <p className="mt-5 max-w-lg text-lg text-muted">
            Turn a scattered search into a calm, evidence-led buying journey — while keeping every important decision yours.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <ButtonLink to="/" variant="success" size="lg" data-testid="about-start">
              Start a buying journey
            </ButtonLink>
            <ButtonLink to="/app/today" variant="secondary" size="lg" data-testid="about-example">
              See an example
            </ButtonLink>
          </div>
        </div>

        <div className="card grid gap-0 overflow-hidden sm:grid-cols-2 rise-in" style={{ animationDelay: "80ms" }} data-testid="about-example-panel">
          <div className="border-b border-border p-5 sm:border-r">
            <h2 className="text-base font-semibold md:text-lg">Example brief</h2>
            <p className="mt-2 text-sm text-charcoal">Northside, Perth WA</p>
            <p className="text-sm text-charcoal">3+ bed · Detached house · Land ≥ 400 m²</p>
            <p className="text-sm text-charcoal">Budget ceiling $1.3m · Prefer ≤ $1.2m</p>
            <p className="mt-3 text-xs text-muted">Synthetic example — not a real brief.</p>
          </div>
          <div className="border-b border-border p-5">
            <h2 className="text-base font-semibold md:text-lg">Provisional fit</h2>
            <div className="mt-3">
              <FitRing value={known(82)} label="Provisional fit" size={72} />
            </div>
            <p className="mt-2 text-xs text-muted">Fit is never a valuation. Coverage is shown separately.</p>
          </div>
          <div className="p-5 sm:col-span-2">
            <h2 className="text-base font-semibold md:text-lg">Evidence checklist</h2>
            <ul className="mt-3 divide-y divide-border">
              {checklist.map((c) => (
                <li key={c.label} className="flex items-center justify-between py-2 text-sm">
                  <span className="inline-flex items-center gap-2">
                    {c.state === "found" ? (
                      <Check className="h-4 w-4 text-eucalyptus-deep" aria-hidden="true" />
                    ) : c.state === "some" ? (
                      <span className="inline-block h-4 w-4 rounded-full border-2 border-ochre" aria-hidden="true" />
                    ) : (
                      <CircleHelp className="h-4 w-4 text-muted" aria-hidden="true" />
                    )}
                    {c.label}
                  </span>
                  <span className={c.state === "unknown" ? "italic text-muted" : "text-charcoal"}>
                    {c.state === "found" ? "Evidence found" : c.state === "some" ? "Some unknowns" : "Unknown"}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        </div>
      </section>

      <section className="mt-16 md:mt-24" aria-labelledby="how-heading">
        <h2 id="how-heading" className="text-h2 md:text-3xl">
          How it works
        </h2>
        <ol className="mt-6 grid gap-4 sm:grid-cols-2 lg:grid-cols-5">
          {steps.map((s, i) => (
            <li key={s.n} className="card rise-in p-5" style={{ animationDelay: `${i * 60}ms` }} data-testid={`how-step-${s.n}`}>
              <span className="inline-flex h-9 w-9 items-center justify-center rounded-full bg-eucalyptus-deep text-sm font-bold text-white" aria-hidden="true">
                {s.n}
              </span>
              <h3 className="mt-4 text-base font-semibold md:text-lg">{s.title}</h3>
              <p className="mt-1 text-sm text-muted">{s.body}</p>
            </li>
          ))}
        </ol>
      </section>

      <section className="mt-12 grid gap-4 md:grid-cols-3" aria-label="Trust statements">
        {trust.map((t) => (
          <div key={t.title} className="card flex gap-4 p-5" data-testid="trust-statement">
            <span className="inline-flex h-12 w-12 shrink-0 items-center justify-center rounded-full bg-eucalyptus-soft text-eucalyptus-deep">
              <t.icon className="h-5 w-5" aria-hidden="true" />
            </span>
            <div>
              <h3 className="text-base font-semibold md:text-lg">{t.title}</h3>
              <p className="mt-1 text-sm text-muted">{t.body}</p>
            </div>
          </div>
        ))}
      </section>

      <section className="card mt-12 flex flex-col items-start gap-4 border-eucalyptus/40 bg-eucalyptus-tint p-6 md:flex-row md:items-center md:justify-between" aria-label="Call to action">
        <div className="flex items-center gap-3">
          <Leaf className="h-6 w-6 text-eucalyptus-deep" aria-hidden="true" />
          <p className="text-h3 font-semibold">Ready to make the search feel manageable?</p>
        </div>
        <ButtonLink to="/" variant="success" data-testid="about-cta">
          Start a buying journey
        </ButtonLink>
      </section>

      <p className="mt-6 text-center text-xs text-muted" data-testid="about-limitation">
        Concept interface — no exhaustive listing coverage, valuation or purchasing service is implied.
      </p>
    </div>
  );
}
