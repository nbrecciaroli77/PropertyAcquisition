import clsx from "clsx";
import { ChevronLeft, ChevronRight } from "lucide-react";
import { NavLink } from "react-router-dom";
import { Wordmark } from "../../components/Brand";
import { useAuth } from "../../lib/auth";
import { railItems } from "../nav";

/**
 * Desktop (lg+) full rail with labels and collapse toggle.
 * Tablet (md–lg) icon rail with labels under icons (adaptive).
 */
export function DesktopRail({ collapsed, onToggle }: { collapsed: boolean; onToggle: () => void }) {
  const { me } = useAuth();
  const name = me?.user.display_name ?? "Account";
  const initials =
    name
      .split(/\s+/)
      .filter(Boolean)
      .slice(0, 2)
      .map((p) => p[0]?.toUpperCase() ?? "")
      .join("") || "?";
  return (
    <nav
      aria-label="Primary"
      data-testid="desktop-rail"
      data-collapsed={collapsed}
      className={clsx(
        "hidden md:flex md:flex-col bg-navy text-white shrink-0 transition-[width] duration-200",
        "md:w-[84px]",
        collapsed ? "lg:w-[84px]" : "lg:w-[236px]",
      )}
    >
      <div className={clsx("flex h-16 items-center px-4", collapsed ? "justify-center" : "justify-start")}>
        <span className="hidden lg:block">
          <Wordmark to="/app/today" light compact={collapsed} />
        </span>
        <span className="lg:hidden">
          <Wordmark to="/app/today" light compact />
        </span>
      </div>

      <ul className="mt-2 flex flex-1 flex-col gap-1 px-2">
        {railItems.map((item) => (
          <li key={item.to}>
            <NavLink
              to={item.to}
              data-testid={item.testId}
              className={({ isActive }) =>
                clsx(
                  "group flex items-center rounded-md text-[15px] font-medium transition-colors duration-150",
                  "flex-col gap-1 py-2 text-[11px] lg:text-[15px]",
                  collapsed ? "lg:flex-col lg:gap-1 lg:py-2 lg:text-[11px]" : "lg:flex-row lg:gap-3 lg:px-3 lg:py-2.5",
                  isActive ? "bg-white/12 text-white" : "text-white/75 hover:bg-white/8 hover:text-white",
                )
              }
            >
              {({ isActive }) => (
                <>
                  <item.icon className="h-5 w-5" aria-hidden="true" strokeWidth={isActive ? 2.2 : 1.8} />
                  <span className={clsx(collapsed && "lg:text-[11px]")}>{item.label}</span>
                  {isActive && <span className="sr-only">(current page)</span>}
                </>
              )}
            </NavLink>
          </li>
        ))}
      </ul>

      <div className="border-t border-white/10 p-2">
        <button
          type="button"
          onClick={onToggle}
          data-testid="rail-collapse-toggle"
          aria-pressed={collapsed}
          className={clsx(
            "hidden lg:flex w-full items-center gap-3 rounded-md px-3 py-2.5 text-sm text-white/75 hover:bg-white/8 hover:text-white",
            collapsed && "justify-center px-0",
          )}
        >
          {collapsed ? <ChevronRight className="h-5 w-5" aria-hidden="true" /> : <ChevronLeft className="h-5 w-5" aria-hidden="true" />}
          <span className={clsx(collapsed && "sr-only")}>{collapsed ? "Expand navigation" : "Collapse"}</span>
        </button>
        <div className={clsx("mt-1 flex items-center gap-3 rounded-md px-2 py-2", collapsed && "lg:justify-center lg:px-0", "justify-center lg:justify-start")}>
          <span
            className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-white/15 text-sm font-semibold"
            aria-hidden="true"
          >
            {initials}
          </span>
          <span className={clsx("hidden min-w-0 leading-tight", !collapsed && "lg:block")}>
            <span className="block truncate text-sm font-semibold">{name}</span>
            <span className="block truncate text-xs text-white/60">{me?.workspace.name ?? "Workspace"}</span>
          </span>
        </div>
      </div>
    </nav>
  );
}
