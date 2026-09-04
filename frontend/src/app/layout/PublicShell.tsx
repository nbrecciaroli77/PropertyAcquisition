import { Link, Outlet } from "react-router-dom";
import { ConceptBadge, Wordmark } from "../../components/Brand";
import { ButtonLink } from "../../components/Button";

export function PublicShell() {
  return (
    <div className="flex min-h-screen flex-col" data-testid="public-shell">
      <a href="#main" className="skip-link">
        Skip to main content
      </a>
      <header className="border-b border-border bg-canvas">
        <div className="mx-auto flex h-16 w-full max-w-[1400px] items-center gap-6 px-4 md:px-8">
          <Wordmark />
          <nav aria-label="Public" className="ml-auto flex items-center gap-2 sm:gap-4">
            <Link to="/about" className="rounded-md px-2 py-1 text-sm font-medium text-navy hover:underline underline-offset-4" data-testid="public-nav-about">
              How it works
            </Link>
            <Link to="/" className="hidden rounded-md px-2 py-1 text-sm font-medium text-navy hover:underline underline-offset-4 sm:inline" data-testid="public-nav-sign-in">
              Sign in
            </Link>
            <ButtonLink to="/" variant="success" size="sm" data-testid="public-nav-start">
              <span className="sm:hidden">Start</span>
              <span className="hidden sm:inline">Start a buying journey</span>
            </ButtonLink>
          </nav>
        </div>
      </header>
      <main id="main" tabIndex={-1} className="flex-1 outline-none">
        <Outlet />
      </main>
      <footer className="border-t border-border">
        <div className="mx-auto flex w-full max-w-[1400px] flex-col gap-3 px-4 py-6 text-xs text-muted md:flex-row md:items-center md:justify-between md:px-8">
          <div className="flex items-center gap-3">
            <ConceptBadge />
            <span>Private prototype. No exhaustive listing coverage, valuation or purchasing service is implied.</span>
          </div>
          <nav aria-label="Legal" className="flex gap-4">
            <Link to="/terms" className="hover:underline underline-offset-4" data-testid="footer-terms">
              Terms
            </Link>
            <Link to="/privacy" className="hover:underline underline-offset-4" data-testid="footer-privacy">
              Privacy
            </Link>
          </nav>
        </div>
      </footer>
    </div>
  );
}
