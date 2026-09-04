import userEvent from "@testing-library/user-event";
import { axe } from "jest-axe";
import { BRIEF, mockApi, renderAt, screen } from "../test/helpers";

describe("buying brief", () => {
  it("renders every criterion with its mode and the default weights", async () => {
    mockApi();
    const { container } = renderAt("/app/brief");
    expect(await screen.findByTestId("criterion-budget")).toBeInTheDocument();
    ["beds", "baths", "parking", "land-sqm", "floor-sqm", "renovation", "timing", "detached"].forEach((id) =>
      expect(screen.getByTestId(`criterion-${id}`)).toBeInTheDocument(),
    );
    expect(screen.getByTestId("weights-total")).toHaveTextContent("100");
    expect(screen.getByTestId("weight-price")).toHaveValue(30);
    expect(screen.getByTestId("weight-location")).toHaveValue(20);
    expect(await axe(container)).toHaveNoViolations();
  });

  it("explains what each mode means so Unknown is never read as a pass", async () => {
    mockApi();
    renderAt("/app/brief");
    expect(await screen.findByTestId("budget-mode-help")).toHaveTextContent(/known failure excludes/i);
    await userEvent.selectOptions(screen.getByTestId("beds-mode"), "unknown");
    expect(screen.getByTestId("beds-mode-help")).toHaveTextContent(/never treated as pass or fail/i);
  });

  it("blocks publication and lists field-linked blockers returned by the server", async () => {
    mockApi({
      "/api/journeys/33333333-3333-3333-3333-333333333333/brief": {
        body: {
          ...BRIEF,
          validation: [
            { field: "budget.preferred_max_minor", message: "The preferred maximum cannot exceed the budget ceiling." },
            { field: "weights", message: "At least one preference weight must be enabled with a value above zero." },
          ],
        },
      },
    });
    renderAt("/app/brief");
    expect(await screen.findByTestId("publish-blockers")).toBeInTheDocument();
    expect(screen.getByTestId("brief-publish")).toBeDisabled();
    expect(screen.getByTestId("blocker-weights")).toBeInTheDocument();
    expect(screen.getByTestId("budget-preferred-max-error")).toHaveTextContent(/cannot exceed the budget ceiling/i);
  });

  it("offers the locations screen with excluded areas and Unknown travel time", async () => {
    mockApi();
    renderAt("/app/brief/locations");
    expect(await screen.findByTestId("states-section")).toBeInTheDocument();
    expect(screen.getByTestId("state-WA")).toBeChecked();
    expect(screen.getByTestId("excluded-editor")).toBeInTheDocument();
    expect(screen.getByTestId("anchors-unknown-notice")).toHaveTextContent(/travel time stays/i);
  });

  it("shows guided setup steps and resumes at the saved step", async () => {
    const onboardingJourney = {
            id: "33333333-3333-3333-3333-333333333333",
            name: "Perth family home 2026",
            status: "onboarding",
            timezone: "Australia/Perth",
            onboarding_step: 3,
            onboarding_complete: false,
            row_version: 2,
            current_version_no: null,
            published_versions: 0,
            created_at: "2026-06-01T00:00:00+08:00",
      updated_at: "2026-06-18T00:00:00+08:00",
    } as const;
    mockApi({
      "/api/journeys": { body: [onboardingJourney] },
      "/api/journeys/33333333-3333-3333-3333-333333333333/brief": {
        body: { ...BRIEF, journey: onboardingJourney },
      },
    });
    renderAt("/app/journeys/new");
    expect(await screen.findByTestId("resume-notice")).toHaveTextContent(/resumed your setup at step 3/i);
    expect(screen.getByTestId("onboarding-step-title")).toHaveTextContent(/Step 3 of 6/);
    expect(screen.getByTestId("property-types")).toBeInTheDocument();
  });
});
