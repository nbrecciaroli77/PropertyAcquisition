import { useEffect, useRef, useState } from "react";
import { Outlet, useLocation } from "react-router-dom";
import { SyntheticBanner } from "../../components/Page";
import { useJourneys } from "../../lib/journey";
import { BottomNav } from "./BottomNav";
import { CampaignNotice, CampaignParamSync } from "./CampaignShell";
import { DesktopRail } from "./DesktopRail";
import { TopBar } from "./TopBar";

const RAIL_KEY = "pa.rail.collapsed";

/** Increments only when the active campaign changes from one campaign to another (not on first load). */
function useCampaignEpoch(activeId: string | null): number {
  const [seen, setSeen] = useState<{ id: string | null; epoch: number }>({ id: activeId, epoch: 0 });
  if (activeId && activeId !== seen.id) setSeen({ id: activeId, epoch: seen.id ? seen.epoch + 1 : seen.epoch });
  return seen.epoch;
}

export function AppShell() {
  const [collapsed, setCollapsed] = useState<boolean>(() => localStorage.getItem(RAIL_KEY) === "1");
  const { pathname } = useLocation();
  const { active } = useJourneys();
  const campaignEpoch = useCampaignEpoch(active?.id ?? null);

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
        <CampaignParamSync />
        <CampaignNotice />
        <main id="main" tabIndex={-1} className="flex-1 px-4 pb-24 pt-6 outline-none md:px-6 md:pb-10 md:pt-8 lg:px-8" data-testid="main-content">
          {/* Remount on campaign switch so no page state or selection carries over between campaigns. */}
          <div key={`${campaignEpoch}:${pathname}`} className="rise-in mx-auto w-full max-w-[1400px]">
            <Outlet />
          </div>
        </main>
      </div>
      <BottomNav />
    </div>
  );
}
