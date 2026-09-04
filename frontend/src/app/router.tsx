import { createBrowserRouter, Navigate } from "react-router-dom";
import { AppShell } from "./layout/AppShell";
import { PublicShell } from "./layout/PublicShell";
import AboutPage from "../features/public/AboutPage";
import { LegalPage, NotFoundPage } from "../features/public/LegalPage";
import WelcomePage from "../features/public/WelcomePage";
import TodayPage from "../features/today/TodayPage";
import DiscoverPage from "../features/discover/DiscoverPage";
import PipelinePage from "../features/pipeline/PipelinePage";
import ComparePage from "../features/compare/ComparePage";
import SavedPage from "../features/saved/SavedPage";
import TasksPage from "../features/tasks/TasksPage";
import AgentsPage from "../features/agents/AgentsPage";
import SourcesPage from "../features/sources/SourcesPage";
import SettingsPage from "../features/settings/SettingsPage";
import MorePage from "../features/more/MorePage";
import PropertyDetailPage from "../features/property/PropertyDetailPage";

export const routes = [
  {
    element: <PublicShell />,
    children: [
      { path: "/", element: <WelcomePage /> },
      { path: "/about", element: <AboutPage /> },
      { path: "/terms", element: <LegalPage kind="terms" /> },
      { path: "/privacy", element: <LegalPage kind="privacy" /> },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
  {
    path: "/app",
    element: <AppShell />,
    children: [
      { index: true, element: <Navigate to="/app/today" replace /> },
      { path: "today", element: <TodayPage /> },
      { path: "discover", element: <DiscoverPage /> },
      { path: "pipeline", element: <PipelinePage /> },
      { path: "compare", element: <ComparePage /> },
      { path: "saved", element: <SavedPage /> },
      { path: "tasks", element: <TasksPage /> },
      { path: "agents", element: <AgentsPage /> },
      { path: "sources", element: <SourcesPage /> },
      { path: "settings", element: <SettingsPage /> },
      { path: "more", element: <MorePage /> },
      { path: "properties/:id", element: <PropertyDetailPage /> },
    ],
  },
];

export const router = createBrowserRouter(routes);
