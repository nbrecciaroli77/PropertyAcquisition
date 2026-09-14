import { createBrowserRouter, Navigate } from "react-router-dom";
import { AppShell } from "./layout/AppShell";
import { PublicShell } from "./layout/PublicShell";
import { RequireAuth } from "../lib/auth";
import { JourneyProvider, useJourneys } from "../lib/journey";
import { Skeleton } from "../components/States";
import AboutPage from "../features/public/AboutPage";
import { LegalPage, NotFoundPage } from "../features/public/LegalPage";
import WelcomePage from "../features/public/WelcomePage";
import SignUpPage from "../features/auth/SignUpPage";
import VerifyPendingPage from "../features/auth/VerifyPendingPage";
import VerifyEmailPage from "../features/auth/VerifyEmailPage";
import ForgotPasswordPage from "../features/auth/ForgotPasswordPage";
import ResetPasswordPage from "../features/auth/ResetPasswordPage";
import NewJourneyPage from "../features/journeys/NewJourneyPage";
import BriefPage from "../features/brief/BriefPage";
import BriefLocationsPage from "../features/brief/BriefLocationsPage";
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
import AddPropertyPage from "../features/intake/AddPropertyPage";
import DuplicatesPage from "../features/duplicates/DuplicatesPage";

/** Sends a signed-in owner to setup when no journey exists yet. */
function AppLanding() {
  const { journeys, loading } = useJourneys();
  if (loading) return <Skeleton className="h-40" label="Opening your workspace" />;
  if (journeys.length === 0) return <Navigate to="/app/journeys/new" replace />;
  return <Navigate to="/app/today" replace />;
}

export const routes = [
  {
    element: <PublicShell />,
    children: [
      { path: "/", element: <WelcomePage /> },
      { path: "/signup", element: <SignUpPage /> },
      { path: "/verify-pending", element: <VerifyPendingPage /> },
      { path: "/verify-email", element: <VerifyEmailPage /> },
      { path: "/forgot-password", element: <ForgotPasswordPage /> },
      { path: "/reset-password", element: <ResetPasswordPage /> },
      { path: "/about", element: <AboutPage /> },
      { path: "/terms", element: <LegalPage kind="terms" /> },
      { path: "/privacy", element: <LegalPage kind="privacy" /> },
      { path: "*", element: <NotFoundPage /> },
    ],
  },
  {
    path: "/app",
    element: (
      <RequireAuth>
        <JourneyProvider>
          <AppShell />
        </JourneyProvider>
      </RequireAuth>
    ),
    children: [
      { index: true, element: <AppLanding /> },
      { path: "today", element: <TodayPage /> },
      { path: "journeys/new", element: <NewJourneyPage /> },
      { path: "brief", element: <BriefPage /> },
      { path: "brief/locations", element: <BriefLocationsPage /> },
      { path: "discover", element: <DiscoverPage /> },
      { path: "pipeline", element: <PipelinePage /> },
      { path: "compare", element: <ComparePage /> },
      { path: "saved", element: <SavedPage /> },
      { path: "tasks", element: <TasksPage /> },
      { path: "agents", element: <AgentsPage /> },
      { path: "sources", element: <SourcesPage /> },
      { path: "settings", element: <SettingsPage /> },
      { path: "more", element: <MorePage /> },
      { path: "properties/add", element: <AddPropertyPage /> },
      { path: "properties/:id", element: <PropertyDetailPage /> },
      { path: "duplicates", element: <DuplicatesPage /> },
    ],
  },
];

export const router = createBrowserRouter(routes);
