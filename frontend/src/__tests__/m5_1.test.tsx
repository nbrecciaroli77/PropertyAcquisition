import userEvent from "@testing-library/user-event";
import { mockApi, renderAt, screen, waitFor } from "../test/helpers";

const notification = {
  id: "inbox-1", event_id: "event-1", category: "task_due_soon", title: "Task due soon: Review contract", message: "This task is approaching its due time.", priority: "high", safe_deep_link: "/app/tasks?task=task-1", property_id: null, property_address: null, property_image_url: null, task_id: "task-1", source_event_id: null, report_run_id: null, evidence_ref: {}, created_at: "2026-09-15T08:00:00Z", read_at: null, dismissed_at: null, expires_at: null, is_expired: false,
};

describe("M5.1 notifications and tasks", () => {
  it("renders the responsive notification centre and allows an inbox read action", async () => {
    const mock = mockApi({
      "/api/notifications": { body: { items: [notification], unread_count: 1 } },
      "/api/notifications/inbox-1": { body: { items: [{ ...notification, read_at: "2026-09-15T08:05:00Z" }], unread_count: 0 } },
    });
    renderAt("/app/notifications");
    expect(await screen.findByTestId("notifications-list")).toBeInTheDocument();
    expect(screen.getByText("Task due soon: Review contract")).toBeInTheDocument();
    await userEvent.click(screen.getByTestId("notification-read-inbox-1"));
    await waitFor(() => expect(mock.calls.some((call) => call.includes("/api/notifications/inbox-1"))).toBe(true));
  });

  it("renders task creation controls with an explicit calendar download link", async () => {
    mockApi({
      "/api/journeys/33333333-3333-3333-3333-333333333333/tasks": { body: [{ id: "task-1", journey_id: "33333333-3333-3333-3333-333333333333", property_id: null, property_address: null, title: "Review contract", notes: null, assignee_user_id: null, assignee_name: null, priority: "high", due_at: "2026-09-16T10:00:00+08:00", timezone: "Australia/Perth", reminder_offset_minutes: 60, status: "open", done: false, done_at: null, row_version: 1, created_at: "2026-09-15T08:00:00Z", updated_at: "2026-09-15T08:00:00Z" }] },
      "/api/workspaces/me/members": { body: [] },
    });
    renderAt("/app/tasks");
    expect(await screen.findByTestId("task-form")).toBeInTheDocument();
    expect(screen.getByTestId("task-due-input")).toBeInTheDocument();
    expect(await screen.findByTestId("task-ics-task-1")).toHaveAttribute("href", expect.stringContaining("calendar.ics"));
  });
});