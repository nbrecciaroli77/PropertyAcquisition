import { useEffect, useRef, useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { SyntheticBanner } from "../../components/Page";
import { BottomNav } from "./BottomNav";
import { DesktopRail } from "./DesktopRail";
import { TopBar } from "./TopBar";

const RAIL_KEY = "pa.rail.collapsed";

export function AppShell() {
  const [collapsed, setCollapsed] = useState<boolean>(() => localStorage.getItem(RAIL_KEY) === "1");
  const { pathname } = useLocation();

  useEffect(() => {
    localStorage.setItem(RAIL_KEY, collapsed ? "1" : "0");
  }, [collapsed]);

  const prevPath = useRef(pathname);
  useEffect(() => {
    if (prevPath.current === pathname) return;
    prevPath.current = pathname;
    document.getElementById("main")?.focus({ preventScroll: true });
  }, [pathname]);

  return (
    <div className="flex min-h-screen" data-testid="app-shell">
      <a href="#main" className="skip-link">
        Skip to main content
      </a>
      <DesktopRail collapsed={collapsed} onToggle={() => setCollapsed((c) => !c)} />
      <div className="flex min-w-0 flex-1 flex-col">
        <SyntheticBanner />
        <TopBar />
        <main id="main" tabIndex={-1} className="flex-1 px-4 pb-24 pt-6 outline-none md:px-6 md:pb-10 md:pt-8 lg:px-8" data-testid="main-content">
          <div key={pathname} className="rise-in mx-auto w-full max-w-[1400px]">
            <Outlet />
          </div>
        </main>
      </div>
      <BottomNav />
    </div>
  );
}
