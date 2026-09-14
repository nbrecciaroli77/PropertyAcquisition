import {
  Bookmark,
  Columns3,
  Database,
  FileText,
  GitMerge,
  Inbox,
  KanbanSquare,
  ListChecks,
  MoreHorizontal,
  Settings,
  Sunrise,
  Users,
  type LucideIcon,
} from "lucide-react";

export interface NavItem {
  to: string;
  label: string;
  icon: LucideIcon;
  testId: string;
}

/** Desktop rail + tablet rail. Order follows the Build Specification route list. */
export const railItems: NavItem[] = [
  { to: "/app/today", label: "Today", icon: Sunrise, testId: "nav-today" },
  { to: "/app/brief", label: "Brief", icon: FileText, testId: "nav-brief" },
  { to: "/app/discover", label: "Discover", icon: Inbox, testId: "nav-discover" },
  { to: "/app/pipeline", label: "Pipeline", icon: KanbanSquare, testId: "nav-pipeline" },
  { to: "/app/duplicates", label: "Duplicates", icon: GitMerge, testId: "nav-duplicates" },
  { to: "/app/compare", label: "Compare", icon: Columns3, testId: "nav-compare" },
  { to: "/app/saved", label: "Saved", icon: Bookmark, testId: "nav-saved" },
  { to: "/app/tasks", label: "Tasks", icon: ListChecks, testId: "nav-tasks" },
  { to: "/app/agents", label: "Agents", icon: Users, testId: "nav-agents" },
  { to: "/app/sources", label: "Sources", icon: Database, testId: "nav-sources" },
  { to: "/app/settings", label: "Settings", icon: Settings, testId: "nav-settings" },
];

/** Phone bottom navigation — fixed by design-tokens.json layout.phoneBottomNavigation. */
export const bottomItems: NavItem[] = [
  { to: "/app/today", label: "Today", icon: Sunrise, testId: "bottom-nav-today" },
  { to: "/app/discover", label: "Properties", icon: Inbox, testId: "bottom-nav-properties" },
  { to: "/app/saved", label: "Saved", icon: Bookmark, testId: "bottom-nav-saved" },
  { to: "/app/more", label: "More", icon: MoreHorizontal, testId: "bottom-nav-more" },
];

/** Routes that light up "Properties" on the phone. */
export const propertiesRoutes = ["/app/discover", "/app/pipeline", "/app/properties", "/app/compare"];
