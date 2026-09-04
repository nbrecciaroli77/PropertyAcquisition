import clsx from "clsx";
import { Link, useLocation } from "react-router-dom";
import { bottomItems, propertiesRoutes } from "../nav";

export function BottomNav() {
  const { pathname } = useLocation();
  const isActive = (item: (typeof bottomItems)[number]) =>
    item.label === "Properties" ? propertiesRoutes.some((r) => pathname.startsWith(r)) : pathname.startsWith(item.to);

  return (
    <nav
      aria-label="Primary, phone"
      data-testid="bottom-nav"
      className="fixed inset-x-0 bottom-0 z-30 border-t border-border bg-surface shadow-[0_-1px_0_rgba(0,0,0,0.04)] md:hidden"
      style={{ paddingBottom: "env(safe-area-inset-bottom)" }}
    >
      <ul className="grid grid-cols-4">
        {bottomItems.map((item) => {
          const active = isActive(item);
          return (
            <li key={item.to}>
              <Link
                to={item.to}
                data-testid={item.testId}
                aria-current={active ? "page" : undefined}
                className={clsx(
                  "flex min-h-[56px] flex-col items-center justify-center gap-1 px-1 text-[11px] font-medium",
                  active ? "text-eucalyptus-deep" : "text-muted",
                )}
              >
                <span
                  className={clsx(
                    "inline-flex h-7 w-11 items-center justify-center rounded-full transition-colors duration-150",
                    active && "bg-eucalyptus-soft",
                  )}
                >
                  <item.icon className="h-5 w-5" aria-hidden="true" strokeWidth={active ? 2.2 : 1.8} />
                </span>
                {item.label}
              </Link>
            </li>
          );
        })}
      </ul>
    </nav>
  );
}
