import { ChevronRight, CircleHelp, LogOut } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { PageHeader } from "../../components/Page";
import { useAuth } from "../../lib/auth";
import { railItems } from "../../app/nav";

/** Phone-only hub reached from the bottom "More" tab. Lists every rail destination not in the bottom bar. */
export default function MorePage() {
  const items = railItems.filter((i) => !["/app/today", "/app/discover", "/app/saved"].includes(i.to));
  const { me, signOut } = useAuth();
  const navigate = useNavigate();
  const name = me?.user.display_name ?? "Account";
  const initials =
    name
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((p) => p[0]?.toUpperCase() ?? "")
      .join("") || "?";

  return (
    <>
      <PageHeader eyebrow="More" title="Everything else" testId="more-header" />
      <div className="card mb-4 flex items-center gap-3 p-4">
        <span className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-navy text-sm font-semibold text-white" aria-hidden="true">
          {initials}
        </span>
        <div className="min-w-0">
          <div className="font-semibold">{name}</div>
          <div className="truncate text-xs text-muted" data-testid="more-account-email">
            {me?.user.email} · {me?.workspace.role}
          </div>
        </div>
      </div>
      <nav aria-label="More destinations">
        <ul className="card divide-y divide-border" data-testid="more-list">
          {items.map((i) => (
            <li key={i.to}>
              <Link to={i.to} className="flex min-h-[52px] items-center gap-3 px-4 text-[15px] font-medium hover:bg-canvas" data-testid={`more-${i.label.toLowerCase()}`}>
                <i.icon className="h-5 w-5 text-eucalyptus-deep" aria-hidden="true" />
                {i.label}
                <ChevronRight className="ml-auto h-4 w-4 text-muted" aria-hidden="true" />
              </Link>
            </li>
          ))}
          <li>
            <Link to="/about" className="flex min-h-[52px] items-center gap-3 px-4 text-[15px] font-medium hover:bg-canvas" data-testid="more-help">
              <CircleHelp className="h-5 w-5 text-eucalyptus-deep" aria-hidden="true" />
              How it works
              <ChevronRight className="ml-auto h-4 w-4 text-muted" aria-hidden="true" />
            </Link>
          </li>
          <li>
            <button
              type="button"
              onClick={async () => {
                await signOut();
                navigate("/", { replace: true });
              }}
              className="flex min-h-[52px] w-full items-center gap-3 px-4 text-left text-[15px] font-medium hover:bg-canvas"
              data-testid="more-sign-out"
            >
              <LogOut className="h-5 w-5 text-muted" aria-hidden="true" />
              Sign out
            </button>
          </li>
        </ul>
      </nav>
    </>
  );
}
