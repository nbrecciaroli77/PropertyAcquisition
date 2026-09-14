import { apiFetch } from "./api";

export interface Task {
  id: string; journey_id: string; property_id: string | null; property_address: string | null; title: string; notes: string | null;
  assignee_user_id: string | null; assignee_name: string | null; priority: "low" | "normal" | "high"; due_at: string | null;
  timezone: string; reminder_offset_minutes: number | null; status: "open" | "completed"; done: boolean; done_at: string | null;
  row_version: number; created_at: string; updated_at: string;
}
export interface WorkspaceMember { id: string; display_name: string; email: string; role: string; }
export interface TaskInput { property_id: string | null; title: string; notes: string | null; assignee_user_id: string | null; priority: "low" | "normal" | "high"; due_at: string | null; timezone: string; reminder_offset_minutes: number | null; }

export const taskApi = {
  list: (journeyId: string) => apiFetch<Task[]>(`/journeys/${journeyId}/tasks`),
  members: () => apiFetch<WorkspaceMember[]>("/workspaces/me/members"),
  create: (journeyId: string, body: TaskInput) => apiFetch<Task>(`/journeys/${journeyId}/tasks`, { method: "POST", body: JSON.stringify(body) }),
  update: (journeyId: string, taskId: string, body: Partial<TaskInput> & { expected_row_version: number; status?: "open" | "completed" }) =>
    apiFetch<Task>(`/journeys/${journeyId}/tasks/${taskId}`, { method: "PATCH", body: JSON.stringify(body) }),
  remove: (journeyId: string, taskId: string, expectedRowVersion: number) =>
    apiFetch<void>(`/journeys/${journeyId}/tasks/${taskId}?expected_row_version=${expectedRowVersion}`, { method: "DELETE" }),
  calendarUrl: (journeyId: string, taskId: string) => `${process.env.REACT_APP_BACKEND_URL}/api/journeys/${journeyId}/tasks/${taskId}/calendar.ics`,
};