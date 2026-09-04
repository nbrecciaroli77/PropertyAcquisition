import { CheckSquare, Square } from "lucide-react";
import { useState } from "react";
import { Button } from "../../components/Button";
import { formatDate } from "../../lib/format";
import { propertyApi, type PropertyDetail } from "../../lib/properties";

interface Props {
  p: PropertyDetail;
  busy: boolean;
  mutate: (fn: (journeyId: string) => Promise<PropertyDetail>, notice?: string) => Promise<void>;
}

export function Notes({ p, busy, mutate }: Props) {
  const [body, setBody] = useState("");
  const [editing, setEditing] = useState<{ id: string; body: string; row_version: number } | null>(null);
  return (
    <section aria-labelledby="notes-heading" className="card p-5" data-testid="notes-panel">
      <h2 id="notes-heading" className="text-h3 font-semibold">
        Notes
      </h2>
      <form
        className="mt-3 flex flex-col gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          if (!body.trim()) return;
          void mutate((j) => propertyApi.addNote(j, p.id, body.trim()), "Note added.").then(() => setBody(""));
        }}
      >
        <label htmlFor="note-body" className="sr-only">
          New note
        </label>
        <textarea id="note-body" value={body} onChange={(e) => setBody(e.target.value)} rows={2} placeholder="Private household note…" className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm" data-testid="note-input" />
        <Button type="submit" size="sm" variant="secondary" disabled={busy || !body.trim()} className="self-start" data-testid="note-submit">
          Add note
        </Button>
      </form>
      <ul className="mt-3 divide-y divide-border" data-testid="note-list">
        {p.notes.length === 0 && <li className="py-2 text-sm italic text-muted">No notes yet.</li>}
        {p.notes.map((n) => (
          <li key={n.id} className="py-3 text-sm" data-testid={`note-${n.id}`}>
            {editing?.id === n.id ? (
              <form
                className="flex flex-col gap-2"
                onSubmit={(e) => {
                  e.preventDefault();
                  void mutate((j) => propertyApi.editNote(j, p.id, n.id, editing.body.trim(), editing.row_version), "Note updated.").then(() => setEditing(null));
                }}
              >
                <textarea value={editing.body} onChange={(e) => setEditing({ ...editing, body: e.target.value })} rows={2} className="w-full rounded-md border border-border bg-surface px-3 py-2 text-sm" aria-label="Edit note" data-testid="note-edit-input" />
                <div className="flex gap-2">
                  <Button type="submit" size="sm" disabled={busy} data-testid="note-edit-save">
                    Save
                  </Button>
                  <Button type="button" size="sm" variant="tertiary" onClick={() => setEditing(null)}>
                    Cancel
                  </Button>
                </div>
              </form>
            ) : (
              <>
                <p className="whitespace-pre-wrap">{n.body}</p>
                <div className="mt-1 flex flex-wrap gap-x-3 text-xs text-muted">
                  <span>{n.author_email}</span>
                  <span>{formatDate(n.updated_at)}</span>
                  <span>v{n.row_version}</span>
                  <button type="button" onClick={() => setEditing({ id: n.id, body: n.body, row_version: n.row_version })} className="font-semibold text-eucalyptus-deep hover:underline underline-offset-4" data-testid={`note-edit-${n.id}`}>
                    Edit
                  </button>
                </div>
              </>
            )}
          </li>
        ))}
      </ul>
    </section>
  );
}

export function Tasks({ p, busy, mutate }: Props) {
  const [title, setTitle] = useState("");
  return (
    <section aria-labelledby="tasks-heading" className="card p-5" data-testid="tasks-panel">
      <h2 id="tasks-heading" className="text-h3 font-semibold">
        Tasks
      </h2>
      <p className="mt-1 text-xs text-muted">Simple to-dos for this property. Due dates, owners and reminders arrive in Milestone 5. Creating a task contacts nobody.</p>
      <form
        className="mt-3 flex gap-2"
        onSubmit={(e) => {
          e.preventDefault();
          if (!title.trim()) return;
          void mutate((j) => propertyApi.addTask(j, p.id, title.trim()), "Task added.").then(() => setTitle(""));
        }}
      >
        <label htmlFor="task-title" className="sr-only">
          New task
        </label>
        <input id="task-title" value={title} onChange={(e) => setTitle(e.target.value)} placeholder="e.g. Ask agent for the land survey" className="h-10 min-w-0 flex-1 rounded-md border border-border bg-surface px-3 text-sm" data-testid="task-input" />
        <Button type="submit" size="sm" variant="secondary" disabled={busy || !title.trim()} data-testid="task-submit">
          Add
        </Button>
      </form>
      <ul className="mt-3 divide-y divide-border" data-testid="task-list">
        {p.tasks.length === 0 && <li className="py-2 text-sm italic text-muted">No tasks yet.</li>}
        {p.tasks.map((t) => (
          <li key={t.id} className="flex items-start gap-2 py-2 text-sm" data-testid={`task-${t.id}`} data-done={t.done}>
            <button type="button" onClick={() => void mutate((j) => propertyApi.updateTask(j, p.id, t.id, !t.done, t.row_version), t.done ? "Task reopened." : "Task completed.")} disabled={busy} aria-pressed={t.done} aria-label={t.done ? `Reopen task ${t.title}` : `Complete task ${t.title}`} className="mt-0.5 text-eucalyptus-deep" data-testid={`task-toggle-${t.id}`}>
              {t.done ? <CheckSquare className="h-5 w-5" aria-hidden="true" /> : <Square className="h-5 w-5 text-muted" aria-hidden="true" />}
            </button>
            <span className={t.done ? "line-through text-muted" : ""}>{t.title}</span>
          </li>
        ))}
      </ul>
    </section>
  );
}

export function Activity({ p }: { p: PropertyDetail }) {
  return (
    <section aria-labelledby="activity-heading" className="card p-5" data-testid="activity-panel">
      <h2 id="activity-heading" className="text-h3 font-semibold">
        Activity
      </h2>
      <ol className="mt-3 space-y-2 border-l border-border pl-4 text-sm" aria-label="Activity history">
        {p.activity.length === 0 && <li className="italic text-muted">No activity recorded.</li>}
        {p.activity.map((a) => (
          <li key={a.id} className="relative" data-testid={`activity-${a.kind}`}>
            <span className="absolute -left-[21px] top-1.5 h-2 w-2 rounded-full bg-eucalyptus-deep ring-4 ring-surface" aria-hidden="true" />
            <div>{a.summary}</div>
            <div className="text-xs text-muted">
              {a.actor_email ?? "System"} · {formatDate(a.created_at)}
            </div>
          </li>
        ))}
      </ol>
    </section>
  );
}
