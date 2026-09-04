import { axe } from "jest-axe";
import { mockApi, renderAt, screen, within } from "../test/helpers";

const authedRoutes: [string, string][] = [
  ["/app/today", "today-header"],
  ["/app/brief", "brief-header"],
  ["/app/journeys/new", "new-journey-header"],
  ["/app/discover", "discover-header"],
  ["/app/pipeline", "pipeline-header"],
  ["/app/compare", "compare-header"],
  ["/app/saved", "saved-header"],
  ["/app/tasks", "tasks-header"],
  ["/app/agents", "agents-header"],
  ["/app/sources", "sources-header"],
  ["/app/settings", "settings-header"],
];

describe("authenticated shell", () => {
  beforeEach(() => {
    mockApi();
  });

  it.each(authedRoutes)("%s renders inside the shell with a single h1 and the synthetic banner", async (path, testId) => {
    renderAt(path);
    expect(await screen.findByTestId(testId)).toBeInTheDocument();
    expect(screen.getByTestId("app-shell")).toBeInTheDocument();
    expect(screen.getByTestId("synthetic-data-banner")).toBeInTheDocument();
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(screen.getByRole("main")).toBeInTheDocument();
  });

  it("desktop rail lists the spec routes in order and bottom nav follows the tokens file", async () => {
    renderAt("/app/today");
    const rail = await screen.findByTestId("desktop-rail");
    const labels = within(rail)
      .getAllByRole("link")
      .map((a) => a.textContent?.replace("(current page)", "").trim())
      .filter((t) => t && t !== "Property Acquisition");
    expect(labels).toEqual([
      "Today",
      "Brief",
      "Discover",
      "Pipeline",
      "Compare",
      "Saved",
      "Tasks",
      "Agents",
      "Sources",
      "Settings",
    ]);

    const bottom = screen.getByTestId("bottom-nav");
    expect(within(bottom).getAllByRole("link").map((a) => a.textContent?.trim())).toEqual([
      "Today",
      "Properties",
      "Saved",
      "More",
    ]);
  });

  it("marks the current page for assistive tech", async () => {
    renderAt("/app/pipeline");
    expect(await screen.findByTestId("nav-pipeline")).toHaveAttribute("aria-current", "page");
    expect(screen.getByTestId("bottom-nav-properties")).toHaveAttribute("aria-current", "page");
  });

  it("/app lands on Today when a journey exists", async () => {
    renderAt("/app");
    expect(await screen.findByTestId("today-header")).toBeInTheDocument();
  });

  it("/app sends a brand new account to guided setup", async () => {
    mockApi({ "/api/journeys": { body: [] } });
    renderAt("/app");
    expect(await screen.findByTestId("new-journey-header")).toBeInTheDocument();
  });

  it("More hub lists the destinations missing from the bottom bar", async () => {
    renderAt("/app/more");
    const list = await screen.findByTestId("more-list");
    ["Brief", "Pipeline", "Compare", "Tasks", "Agents", "Sources", "Settings"].forEach((l) =>
      expect(within(list).getByText(l)).toBeInTheDocument(),
    );
    expect(screen.getByTestId("more-sign-out")).toBeInTheDocument();
  });

  it("Today shows the brief status for the active journey", async () => {
    renderAt("/app/today");
    expect(await screen.findByTestId("today-brief-status")).toHaveTextContent(/Brief version 1 is current/i);
  });

  it("Today passes axe", async () => {
    const { container } = renderAt("/app/today");
    await screen.findByTestId("today-header");
    expect(await axe(container)).toHaveNoViolations();
  });

  it("Discover passes axe", async () => {
    const { container } = renderAt("/app/discover");
    await screen.findByTestId("discover-header");
    expect(await axe(container)).toHaveNoViolations();
  });
});
