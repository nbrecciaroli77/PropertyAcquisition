import { axe } from "jest-axe";
import { renderAt, screen, within } from "../test/helpers";

const authedRoutes: [string, string][] = [
  ["/app/today", "today-header"],
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
  it.each(authedRoutes)("%s renders inside the shell with a single h1 and the synthetic banner", (path, testId) => {
    renderAt(path);
    expect(screen.getByTestId("app-shell")).toBeInTheDocument();
    expect(screen.getByTestId("synthetic-data-banner")).toBeInTheDocument();
    expect(screen.getByTestId(testId)).toBeInTheDocument();
    expect(screen.getAllByRole("heading", { level: 1 })).toHaveLength(1);
    expect(screen.getByRole("main")).toBeInTheDocument();
  });

  it("desktop rail lists all nine spec routes in order and bottom nav follows the tokens file", () => {
    renderAt("/app/today");
    const rail = screen.getByTestId("desktop-rail");
    const labels = within(rail)
      .getAllByRole("link")
      .map((a) => a.textContent?.replace("(current page)", "").trim())
      .filter((t) => t && t !== "Property Acquisition");
    expect(labels).toEqual(["Today", "Discover", "Pipeline", "Compare", "Saved", "Tasks", "Agents", "Sources", "Settings"]);

    const bottom = screen.getByTestId("bottom-nav");
    expect(within(bottom).getAllByRole("link").map((a) => a.textContent?.trim())).toEqual(["Today", "Properties", "Saved", "More"]);
  });

  it("marks the current page for assistive tech", () => {
    renderAt("/app/pipeline");
    expect(screen.getByTestId("nav-pipeline")).toHaveAttribute("aria-current", "page");
    expect(screen.getByTestId("bottom-nav-properties")).toHaveAttribute("aria-current", "page");
  });

  it("/app redirects to Today", () => {
    renderAt("/app");
    expect(screen.getByTestId("today-header")).toBeInTheDocument();
  });

  it("More hub lists the destinations missing from the bottom bar", () => {
    renderAt("/app/more");
    const list = screen.getByTestId("more-list");
    ["Pipeline", "Compare", "Tasks", "Agents", "Sources", "Settings"].forEach((l) => expect(within(list).getByText(l)).toBeInTheDocument());
  });

  it("Today passes axe", async () => {
    const { container } = renderAt("/app/today");
    expect(await axe(container)).toHaveNoViolations();
  });

  it("Discover passes axe", async () => {
    const { container } = renderAt("/app/discover");
    expect(await axe(container)).toHaveNoViolations();
  });
});
