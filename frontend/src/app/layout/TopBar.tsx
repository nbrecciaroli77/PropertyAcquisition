import * as DropdownMenu from "@radix-ui/react-dropdown-menu";
import { Bell, ChevronDown, CircleHelp, LogOut, Plus, Search, Settings, UserRound } from "lucide-react";
import { Link, useNavigate } from "react-router-dom";
import { Wordmark } from "../../components/Brand";
import { Button } from "../../components/Button";
import { useAuth } from "../../lib/auth";

const initialsOf = (name: string): string =>
  name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part[0]?.toUpperCase() ?? "")
    .join("") || "?";

export function TopBar() {
  const navigate = useNavigate();
  const { me, signOut } = useAuth();
  const displayName = me?.user.display_name ?? "Account";
  const initials = initialsOf(displayName);
  return (
    <header className="sticky top-0 z-20 border-b border-border bg-canvas md:bg-canvas/95 md:backdrop-blur-[2px]" data-testid="top-bar">
      <div className="flex h-14 items-center gap-3 px-4 md:h-16 md:px-6 lg:px-8">
        <span className="md:hidden">
          <Wordmark to="/app/today" compact />
        </span>

        <form
          role="search"
          className="ml-auto hidden max-w-xl flex-1 sm:flex"
          onSubmit={(e) => {
            e.preventDefault();
            navigate("/app/discover");
          }}
        >
          <label htmlFor="global-search" className="sr-only">
            Search properties, suburbs or criteria
          </label>
          <div className="relative w-full">
            <Search className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted" aria-hidden="true" />
            <input
              id="global-search"
              data-testid="global-search"
              type="search"
              placeholder="Search properties, suburbs or criteria"
              className="h-10 w-full rounded-md border border-border bg-surface pl-9 pr-3 text-sm placeholder:text-muted"
            />
          </div>
        </form>

        <div className="ml-auto flex items-center gap-1 sm:ml-0 sm:gap-2">
          <Button
            variant="secondary"
            size="sm"
            className="hidden md:inline-flex"
            icon={<Plus className="h-4 w-4" aria-hidden="true" />}
            onClick={() => navigate("/app/sources")}
            data-testid="top-bar-add-property"
          >
            Add property
          </Button>
          <Link
            to="/app/tasks"
            className="relative inline-flex h-10 w-10 items-center justify-center rounded-md text-navy hover:bg-canvas-deep"
            aria-label="Notifications, 3 unread"
            data-testid="top-bar-notifications"
          >
            <Bell className="h-5 w-5" aria-hidden="true" />
            <span className="absolute right-1.5 top-1.5 inline-flex h-4 min-w-4 items-center justify-center rounded-full bg-ochre px-1 text-[10px] font-bold text-white" aria-hidden="true">
              3
            </span>
          </Link>
          <Link
            to="/about"
            className="hidden h-10 items-center gap-1 rounded-md px-2 text-sm text-navy hover:bg-canvas-deep lg:inline-flex"
            data-testid="top-bar-help"
          >
            <CircleHelp className="h-4 w-4" aria-hidden="true" /> Help
          </Link>

          <DropdownMenu.Root>
            <DropdownMenu.Trigger asChild>
              <button
                type="button"
                className="inline-flex h-10 items-center gap-1 rounded-md pl-1 pr-2 hover:bg-canvas-deep"
                aria-label={`Account menu for ${displayName}`}
                data-testid="top-bar-account"
              >
                <span className="inline-flex h-8 w-8 items-center justify-center rounded-full bg-navy text-xs font-semibold text-white" aria-hidden="true">
                  {initials}
                </span>
                <ChevronDown className="h-4 w-4 text-muted" aria-hidden="true" />
              </button>
            </DropdownMenu.Trigger>
            <DropdownMenu.Portal>
              <DropdownMenu.Content align="end" sideOffset={6} className="z-50 min-w-[220px] rounded-md border border-border bg-surface p-1 shadow-raised" data-testid="account-menu">
                <div className="px-3 py-2">
                  <div className="text-sm font-semibold">{displayName}</div>
                  <div className="text-xs text-muted" data-testid="account-menu-email">
                    {me?.user.email}
                  </div>
                  <div className="text-xs text-muted">
                    {me?.workspace.name} · {me?.workspace.role}
                  </div>
                </div>
                <DropdownMenu.Separator className="my-1 h-px bg-border" />
                <MenuLink to="/app/settings" icon={<UserRound className="h-4 w-4" aria-hidden="true" />}>
                  Profile
                </MenuLink>
                <MenuLink to="/app/settings" icon={<Settings className="h-4 w-4" aria-hidden="true" />}>
                  Settings
                </MenuLink>
                <DropdownMenu.Separator className="my-1 h-px bg-border" />
                <DropdownMenu.Item asChild>
                  <button
                    type="button"
                    onClick={async () => {
                      await signOut();
                      navigate("/", { replace: true });
                    }}
                    className="flex w-full items-center gap-2 rounded-sm px-3 py-2 text-sm text-navy outline-none hover:bg-canvas-deep focus:bg-canvas-deep"
                    data-testid="account-menu-sign-out"
                  >
                    <LogOut className="h-4 w-4" aria-hidden="true" />
                    Sign out
                  </button>
                </DropdownMenu.Item>
              </DropdownMenu.Content>
            </DropdownMenu.Portal>
          </DropdownMenu.Root>
        </div>
      </div>
    </header>
  );
}

function MenuLink({ to, icon, children }: { to: string; icon: JSX.Element; children: string }) {
  return (
    <DropdownMenu.Item asChild>
      <Link to={to} className="flex items-center gap-2 rounded-sm px-3 py-2 text-sm text-navy outline-none hover:bg-canvas-deep focus:bg-canvas-deep">
        {icon}
        {children}
      </Link>
    </DropdownMenu.Item>
  );
}
