import userEvent from "@testing-library/user-event";
import { axe } from "jest-axe";
import { mockAnonymous, mockApi, renderAt, screen } from "../test/helpers";

describe("account screens", () => {
  it("sign-up collects name, email, password and workspace", async () => {
    mockAnonymous();
    const { container } = renderAt("/signup");
    expect(screen.getByTestId("sign-up-form")).toBeInTheDocument();
    expect(screen.getByLabelText(/your name/i)).toBeInTheDocument();
    expect(screen.getByLabelText(/^password$/i)).toBeInTheDocument();
    expect(screen.getByText(/at least 10 characters/i)).toBeInTheDocument();
    expect(await axe(container)).toHaveNoViolations();
  });

  it("verification pending states that delivery is suppressed and offers a re-issue button", () => {
    mockAnonymous();
    renderAt("/verify-pending?email=owner@propertyacquisition-demo.com");
    expect(screen.getByTestId("delivery-suppressed-notice")).toHaveTextContent(/no email is delivered/i);
    // outbox link has been removed; the re-issue button must remain
    expect(screen.queryByTestId("open-outbox-link")).not.toBeInTheDocument();
    expect(screen.getByTestId("reissue-verification")).toBeInTheDocument();
  });

  it("a missing verification token is reported instead of pretending to succeed", async () => {
    mockAnonymous();
    renderAt("/verify-email");
    expect(await screen.findByTestId("verify-email-failed")).toHaveTextContent(/missing its token/i);
  });

  it("reset password cannot be submitted without a token", () => {
    mockAnonymous();
    renderAt("/reset-password");
    expect(screen.getByTestId("reset-token-missing")).toBeInTheDocument();
    expect(screen.getByTestId("reset-password-submit")).toBeDisabled();
  });

  it("reset password catches mismatched confirmations before calling the API", async () => {
    const fetchMock = mockAnonymous();
    renderAt("/reset-password?token=abcdefghijkl");
    await userEvent.type(screen.getByTestId("reset-password"), "Prototype2026pass");
    await userEvent.type(screen.getByTestId("reset-password-confirm"), "Prototype2026pas");
    await userEvent.click(screen.getByTestId("reset-password-submit"));
    expect(await screen.findByTestId("reset-password-error")).toHaveTextContent(/must match/i);
    expect(fetchMock.calls.some((url) => url.includes("/auth/reset-password"))).toBe(false);
  });

  it("/dev/outbox serves the application 404 page — not a dev mailbox", async () => {
    mockAnonymous();
    renderAt("/dev/outbox");
    // The genuine NotFoundPage must render; the old OutboxPage must not
    expect(await screen.findByTestId("not-found-page")).toBeInTheDocument();
    expect(screen.queryByTestId("outbox-scope-notice")).not.toBeInTheDocument();
    expect(screen.queryByTestId("outbox-empty")).not.toBeInTheDocument();
  });

  it("settings lists sessions and offers sign out of all devices", async () => {
    mockApi({
      "/api/auth/sessions": {
        body: [
          {
            id: "44444444-4444-4444-4444-444444444444",
            user_agent: "Chrome on macOS",
            created_at: "2026-06-18T00:00:00+08:00",
            last_seen_at: "2026-06-18T01:00:00+08:00",
            expires_at: "2026-06-25T00:00:00+08:00",
            current: true,
          },
        ],
      },
    });
    renderAt("/app/settings");
    expect(await screen.findByTestId("sessions-list")).toHaveTextContent(/Chrome on macOS/);
    expect(screen.getByTestId("logout-all-devices")).toBeInTheDocument();
  });
});
