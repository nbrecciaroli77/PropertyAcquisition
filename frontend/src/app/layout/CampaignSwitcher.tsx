import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import { Check, ChevronsUpDown, House, LandPlot, Plus, SlidersHorizontal } from "lucide-react";
import type { ReactNode } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import type { CampaignKind, Journey } from "../../lib/api";
import { useJourneys } from "../../lib/journey";

export const campaignKindLabel = (kind: CampaignKind): string => (kind === "land" ? "Land" : "House");

export function CampaignKindIcon({ kind, className }: { kind: CampaignKind; className?: string }) {
  const Icon = kind === "land" ? LandPlot : House;
  return <Icon className={className} aria-hidden="true" />;
}

/** Entity pages that belong to the previous campaign are never kept open after a switch. */
export const pathAfterSwitch = (pathname: string): string =>
  /^\/app\/properties\/(?!add$)[^/]+/.test(pathname) ? "/app/pipeline" : pathname;

const statusLine = (j: Journey): string => {
  if (j.status === "archived") return "Archived";
  if (!j.campaign_enabled) return "Paused · intake and production reports blocked";
  return j.assessment_available ? "Assessment available" : "Assessment not yet available (U2)";
};

export function CampaignSwitcher() {
  const { journeys, active, setActiveId } = useJourneys();
  const navigate = useNavigate();
  const { pathname } = useLocation();
  if (!active) return null;

  const choose = (id: string) => {
    if (id === active.id) return;
    // Drop query state (?run=, ?task=, ?campaign=) so nothing from the old campaign is reopened.
    navigate(pathAfterSwitch(pathname));
    setActiveId(id);
  };

  return (
    <DropdownMenu.Root>
      <DropdownMenu.Trigger asChild>
        <button
          type="button"
          data-testid="campaign-switcher"
          aria-label={`Buyer campaign: ${active.name}. Switch campaign`}
          className="inline-flex h-10 min-w-0 max-w-[48vw] items-center gap-2 rounded-md border border-border bg-surface px-2.5 text-left text-sm transition-colors duration-150 hover:border-navy sm:max-w-[300px]"
        >
          <CampaignKindIcon kind={active.campaign_kind} className="h-4 w-4 shrink-0 text-eucalyptus-deep" />
          <span className="min-w-0 leading-tight">
            <span className="hidden text-[10px] font-semibold uppercase tracking-wide text-muted sm:block" data-testid="campaign-switcher-kind">
              {campaignKindLabel(active.campaign_kind)} campaign
            </span>
            <span className="block truncate font-semibold text-navy" data-testid="campaign-switcher-active-name">
              {active.name}
            </span>
          </span>
          <ChevronsUpDown className="h-4 w-4 shrink-0 text-muted" aria-hidden="true" />
        </button>
      </DropdownMenu.Trigger>
      <DropdownMenu.Portal>
        <DropdownMenu.Content
          align="start"
          sideOffset={6}
          className="z-50 w-[320px] max-w-[calc(100vw-1rem)] rounded-md border border-border bg-surface p-1 shadow-raised"
          data-testid="campaign-switcher-menu"
        >
          <DropdownMenu.Label className="px-3 pb-1 pt-2 text-[11px] font-semibold uppercase tracking-wide text-muted">
            Buyer campaigns
          </DropdownMenu.Label>
          {journeys.map((j) => (
            <CampaignOption key={j.id} journey={j} current={j.id === active.id} onSelect={() => choose(j.id)} />
          ))}
          <DropdownMenu.Separator className="my-1 h-px bg-border" />
          <MenuAction to="/app/campaign" testId="campaign-switcher-settings" icon={<SlidersHorizontal className="h-4 w-4" aria-hidden="true" />}>
            Campaign settings
          </MenuAction>
          <MenuAction to="/app/journeys/new" testId="campaign-switcher-new" icon={<Plus className="h-4 w-4" aria-hidden="true" />}>
            New campaign
          </MenuAction>
        </DropdownMenu.Content>
      </DropdownMenu.Portal>
    </DropdownMenu.Root>
  );
}

function CampaignOption({ journey, current, onSelect }: { journey: Journey; current: boolean; onSelect: () => void }) {
  return (
    <DropdownMenu.Item
      onSelect={onSelect}
      data-testid={`campaign-option-${journey.id}`}
      data-current={current}
      className="flex cursor-pointer items-start gap-3 rounded-sm px-3 py-2 text-sm outline-none hover:bg-canvas-deep focus:bg-canvas-deep"
    >
      <CampaignKindIcon kind={journey.campaign_kind} className="mt-0.5 h-4 w-4 shrink-0 text-eucalyptus-deep" />
      <span className="min-w-0 flex-1">
        <span className="block truncate font-semibold text-navy">{journey.name}</span>
        <span className="block text-xs text-muted">
          {campaignKindLabel(journey.campaign_kind)} · {statusLine(journey)}
        </span>
      </span>
      {current && <Check className="mt-0.5 h-4 w-4 shrink-0 text-eucalyptus-deep" aria-label="Current campaign" />}
    </DropdownMenu.Item>
  );
}

function MenuAction({ to, icon, testId, children }: { to: string; icon: ReactNode; testId: string; children: string }) {
  return (
    <DropdownMenu.Item asChild>
      <Link to={to} data-testid={testId} className="flex items-center gap-2 rounded-sm px-3 py-2 text-sm text-navy outline-none hover:bg-canvas-deep focus:bg-canvas-deep">
        {icon}
        {children}
      </Link>
    </DropdownMenu.Item>
  );
}
