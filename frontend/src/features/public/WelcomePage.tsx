import { Check, Eye, EyeOff, Lock } from "lucide-react";
import { useState, type FormEvent } from "react";
import { Link } from "react-router-dom";
import { BrandMark, ConceptBadge } from "../../components/Brand";
import { Button, ButtonLink } from "../../components/Button";

export default function WelcomePage() {
  const [showPassword, setShowPassword] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);

  const onSubmit = (e: FormEvent<HTMLFormElement>) => {
    e.preventDefault();
    setNotice("Accounts arrive in Milestone 2. Nothing was sent or stored. You can preview the shell with synthetic data below.");
  };

  return (
    <div className="grid min-h-[calc(100vh-4rem)] lg:grid-cols-[minmax(0,1.05fr)_minmax(0,1fr)]" data-testid="welcome-page">
      <section
        aria-labelledby="welcome-hero-heading"
        className="relative hidden overflow-hidden bg-navy px-10 py-12 text-white lg:flex lg:flex-col lg:justify-end xl:px-16"
      >
        <BotanicalTexture />
        <div className="relative max-w-xl">
          <p className="label mb-6 text-eucalyptus">Working concept</p>
          <h2 id="welcome-hero-heading" className="text-[56px] font-semibold leading-[1.02] tracking-[-1.5px] text-white xl:text-[68px]">
            Find the right property.
            <br />
            Know why it fits.
          </h2>
          <p className="mt-6 max-w-md text-lg text-white/80">
            Property Acquisition brings your brief, the evidence and your next actions together — and keeps every decision yours.
          </p>
        </div>
      </section>

      <section aria-labelledby="sign-in-heading" className="flex min-w-0 items-center justify-center px-4 py-10 md:px-10">
        <div className="w-full max-w-[520px] rise-in">
          <div className="flex items-center gap-3">
            <BrandMark className="h-11 w-11" />
            <div>
              <div className="text-h2 leading-7">Property Acquisition</div>
              <ConceptBadge className="mt-1" />
            </div>
          </div>

          <h1 id="sign-in-heading" className="mt-8 text-display">
            Welcome to Property Acquisition
          </h1>
          <p className="mt-2 text-muted">Sign in to access your brief, evidence and next actions.</p>

          <div className="mt-6 grid gap-3 sm:grid-cols-2">
            <ProviderButton label="Continue with Google" testId="sign-in-google" />
            <ProviderButton label="Continue with Apple" testId="sign-in-apple" />
          </div>
          <p className="mt-2 text-xs text-muted" data-testid="provider-disclaimer">
            Provider sign-in is not enabled in this prototype. Signing in with Google would only ever identify you — it never grants or
            implies access to your Gmail.
          </p>

          <div className="my-6 flex items-center gap-3 text-xs text-muted" aria-hidden="true">
            <span className="h-px flex-1 bg-border" />
            or
            <span className="h-px flex-1 bg-border" />
          </div>

          <form onSubmit={onSubmit} noValidate data-testid="sign-in-form" className="space-y-4">
            <div>
              <label htmlFor="email" className="mb-1 block text-sm font-semibold">
                Email address
              </label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="username"
                placeholder="you@example.com"
                data-testid="sign-in-email"
                className="h-11 w-full rounded-md border border-border bg-surface px-3 text-sm placeholder:text-muted"
              />
            </div>
            <div>
              <div className="mb-1 flex items-center justify-between">
                <label htmlFor="password" className="block text-sm font-semibold">
                  Password
                </label>
                <Link to="/" className="text-xs font-semibold text-eucalyptus-deep hover:underline underline-offset-4" data-testid="forgot-password-link">
                  Forgot password?
                </Link>
              </div>
              <div className="relative">
                <input
                  id="password"
                  name="password"
                  type={showPassword ? "text" : "password"}
                  autoComplete="current-password"
                  placeholder="Enter your password"
                  data-testid="sign-in-password"
                  className="h-11 w-full rounded-md border border-border bg-surface px-3 pr-11 text-sm placeholder:text-muted"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword((s) => !s)}
                  className="absolute right-1 top-1/2 inline-flex h-9 w-9 -translate-y-1/2 items-center justify-center rounded-md text-muted hover:bg-canvas-deep"
                  aria-label={showPassword ? "Hide password" : "Show password"}
                  aria-pressed={showPassword}
                  data-testid="toggle-password-visibility"
                >
                  {showPassword ? <EyeOff className="h-4 w-4" aria-hidden="true" /> : <Eye className="h-4 w-4" aria-hidden="true" />}
                </button>
              </div>
            </div>
            <label className="inline-flex items-center gap-2 text-sm">
              <input type="checkbox" name="remember" className="h-4 w-4 rounded-sm border-border accent-[var(--color-eucalyptus-deep)]" data-testid="remember-me" />
              Remember me
            </label>

            {notice && (
              <p role="status" data-testid="sign-in-notice" className="rounded-md border border-ochre/40 bg-ochre-soft px-3 py-2 text-sm text-ochre-deep">
                {notice}
              </p>
            )}

            <Button type="submit" size="lg" className="w-full" data-testid="sign-in-submit">
              Continue
            </Button>
            <p className="text-center text-sm text-muted">
              New to Property Acquisition?{" "}
              <Link to="/about" className="font-semibold text-eucalyptus-deep hover:underline underline-offset-4" data-testid="create-account-link">
                Create an account
              </Link>
            </p>
          </form>

          <div className="card mt-8 p-5" data-testid="preview-panel">
            <p className="font-semibold">Your brief, evidence and next actions in one place.</p>
            <ul className="mt-3 space-y-2 text-sm text-charcoal">
              {["Track shortlisted properties and provisional fit", "See evidence coverage and what is still unknown", "Act with clarity — nothing is sent without you"].map((t) => (
                <li key={t} className="flex items-start gap-2">
                  <Check className="mt-0.5 h-4 w-4 shrink-0 text-eucalyptus-deep" aria-hidden="true" />
                  {t}
                </li>
              ))}
            </ul>
            <ButtonLink to="/app/today" variant="success" className="mt-4 h-auto w-full whitespace-normal py-3 text-center" data-testid="preview-shell-link">
              Preview the shell with synthetic data
            </ButtonLink>
          </div>

          <p className="mt-6 flex items-start gap-2 text-xs text-muted">
            <Lock className="mt-0.5 h-3.5 w-3.5 shrink-0" aria-hidden="true" />
            <span>
              Your brief stays yours. By continuing you agree to our{" "}
              <Link to="/privacy" className="font-semibold text-eucalyptus-deep hover:underline underline-offset-4">
                Privacy Policy
              </Link>{" "}
              and{" "}
              <Link to="/terms" className="font-semibold text-eucalyptus-deep hover:underline underline-offset-4">
                Terms of Use
              </Link>
              .
            </span>
          </p>
        </div>
      </section>
    </div>
  );
}

function ProviderButton({ label, testId }: { label: string; testId: string }) {
  return (
    <Button variant="secondary" disabled aria-describedby="provider-disabled-help" data-testid={testId} className="w-full">
      {label}
      <span className="sr-only" id="provider-disabled-help">
        Not enabled in this prototype
      </span>
    </Button>
  );
}

function BotanicalTexture() {
  return (
    <svg className="pointer-events-none absolute inset-0 h-full w-full opacity-[0.16]" aria-hidden="true" viewBox="0 0 800 800" preserveAspectRatio="xMidYMid slice">
      <defs>
        <pattern id="leaf" width="160" height="160" patternUnits="userSpaceOnUse" patternTransform="rotate(-18)">
          <path d="M40 120 C40 60 80 30 120 20 C120 80 80 110 40 120 Z" fill="none" stroke="#6F8F7A" strokeWidth="2" />
          <path d="M42 118 L118 22" stroke="#6F8F7A" strokeWidth="1.5" />
        </pattern>
      </defs>
      <rect width="800" height="800" fill="url(#leaf)" />
    </svg>
  );
}
