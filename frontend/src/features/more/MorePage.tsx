import { ChevronRight, CircleHelp, LogOut } from "lucide-react";
import { Link } from "react-router-dom";
import { PageHeader } from "../../components/Page";
import { displayUser } from "../../lib/synthetic";
import { railItems } from "../../app/nav";

/** Phone-only hub reached from the bottom "More" tab. Lists every rail destination not in the bottom bar. */
export default function MorePage() {
  const items = railItems.filter((i) => !["/app/today", "/app/discover", "/app/saved"].includes(i.to));
  return (
    <>
      <PageHeader eyebrow="More" title="Everything else" testId="more-header" />
      <div className="card mb-4 flex items-center gap-3 p-4">
        <span className="inline-flex h-10 w-10 items-center justify-center rounded-full bg-navy text-sm font-semibold text-white" aria-hidden="true">
          {displayUser.initials}
        </span>
        <div>
          <div className="font-semibold">{displayUser.name}</div>
          <div className="text-xs text-muted">Synthetic account · no sign-in yet</div>
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
            <Link to="/" className="flex min-h-[52px] items-center gap-3 px-4 text-[15px] font-medium hover:bg-canvas" data-testid="more-leave">
              <LogOut className="h-5 w-5 text-muted" aria-hidden="true" />
              Leave preview
            </Link>
          </li>
        </ul>
      </nav>
    </>
  );
}
