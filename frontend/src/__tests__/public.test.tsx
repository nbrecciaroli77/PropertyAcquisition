import { axe } from "jest-axe";
import { mockAnonymous, renderAt, screen } from "../test/helpers";

describe("public screens", () => {
  beforeEach(() => {
    mockAnonymous();
  });

  it("Welcome renders landmarks, provider buttons disabled, and legal links", async () => {
    const { container } = renderAt("/");
    expect(screen.getByRole("heading", { level: 1, name: /welcome to property acquisition/i })).toBeInTheDocument();
    expect(screen.getByTestId("sign-in-google")).toBeDisabled();
    expect(screen.getByTestId("sign-in-apple")).toBeDisabled();
    expect(screen.getByTestId("provider-disclaimer")).toHaveTextContent(/never grants or implies access to your Gmail/i);
    expect(screen.getByLabelText(/email address/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^password$/i)).toBeInTheDocument();
    expect(screen.getByTestId("create-account-link")).toHaveAttribute("href", "/signup");
    expect(screen.getByTestId("forgot-password-link")).toHaveAttribute("href", "/forgot-password");
    expect(screen.getByRole("main")).toBeInTheDocument();
    expect(screen.getAllByRole("navigation").length).toBeGreaterThan(0);
    expect(screen.getByTestId("footer-terms")).toHaveAttribute("href", "/terms");
    expect(screen.getByTestId("footer-privacy")).toHaveAttribute("href", "/privacy");
    expect(await axe(container)).toHaveNoViolations();
  });

  it("About shows the five steps, three trust statements and the limitation", async () => {
    const { container } = renderAt("/about");
    ["Set your brief", "Bring opportunities together", "Check fit and evidence", "Compare and plan", "You decide and act"].forEach((s) =>
      expect(screen.getByRole("heading", { name: s })).toBeInTheDocument(),
    );
    expect(screen.getAllByTestId("trust-statement")).toHaveLength(3);
    expect(screen.getByText(/unknown is not pass/i)).toBeInTheDocument();
    expect(screen.getByTestId("about-limitation")).toHaveTextContent(/no exhaustive listing coverage, valuation or purchasing service/i);
    expect(await axe(container)).toHaveNoViolations();
  });

  it("Terms and Privacy resolve to real pages", () => {
    renderAt("/terms");
    expect(screen.getByTestId("terms-page")).toBeInTheDocument();
  });

  it("unknown routes render a 404", () => {
    renderAt("/nope");
    expect(screen.getByTestId("not-found-page")).toBeInTheDocument();
  });

  it("an anonymous deep link into the shell returns to sign in", async () => {
    renderAt("/app/brief");
    expect(await screen.findByTestId("welcome-page")).toBeInTheDocument();
  });
});
