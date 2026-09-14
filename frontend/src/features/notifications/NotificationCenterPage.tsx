import { Bell, CheckCheck, CircleAlert, ExternalLink, FileWarning, ListChecks, Trash2 } from "lucide-react";
import { useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Button } from "../../components/Button";
import { PageHeader } from "../../components/Page";
import { EmptyState, Skeleton } from "../../components/States";
import { formatDate } from "../../lib/format";
import { notificationApi, type NotificationItem } from "../../lib/notifications";

const iconFor = (category: string) => category.includes("task") || category === "reminder" ? ListChecks : category.includes("duplicate") || category.includes("evidence") ? FileWarning : CircleAlert;

export default function NotificationCenterPage() {
  const navigate = useNavigate();
  const [items, setItems] = useState<NotificationItem[] | null>(null);
  const [unreadOnly, setUnreadOnly] = useState(false);
  const [category, setCategory] = useState("");
  const [error, setError] = useState<string | null>(null);
  const load = async () => { setError(null); try { setItems((await notificationApi.list({ unread_only: unreadOnly, category: category || undefined })).items); } catch (e) { setError(e instanceof Error ? e.message : "Notifications could not be loaded."); } };
  useEffect(() => { void load(); }, [unreadOnly, category]);
  const update = async (item: NotificationItem, body: { read?: boolean; dismissed?: boolean }, open = false) => { const result = await notificationApi.update(item.id, body); setItems(result.items); if (open) navigate(item.safe_deep_link); };
  return <>
    <PageHeader eyebrow="Notifications" title="Your inbox" description="Property, task and reminder updates stay in this workspace. Nothing is sent externally." actions={<Button size="sm" variant="secondary" icon={<CheckCheck className="h-4 w-4" />} onClick={() => void notificationApi.markAllRead().then((result) => setItems(result.items))} data-testid="notifications-mark-all-read">Mark all read</Button>} testId="notifications-header" />
    <div className="mb-5 flex flex-wrap items-end gap-3" data-testid="notification-filters">
      <div className="flex rounded-md border border-border bg-surface p-1" aria-label="Notification visibility">
        <button type="button" className={`rounded px-3 py-1.5 text-sm ${!unreadOnly ? "bg-canvas-deep font-semibold" : "text-muted"}`} onClick={() => setUnreadOnly(false)} data-testid="notification-filter-all">All</button>
        <button type="button" className={`rounded px-3 py-1.5 text-sm ${unreadOnly ? "bg-canvas-deep font-semibold" : "text-muted"}`} onClick={() => setUnreadOnly(true)} data-testid="notification-filter-unread">Unread</button>
      </div>
      <label className="text-sm font-semibold">Category<select value={category} onChange={(e) => setCategory(e.target.value)} className="ml-2 h-9 rounded-md border border-border bg-surface px-2 text-sm" data-testid="notification-category-filter"><option value="">All categories</option><option value="new_property">New property</option><option value="duplicate_review">Duplicate review</option><option value="task_assigned">Task assigned</option><option value="task_due_soon">Task due soon</option><option value="task_overdue">Task overdue</option><option value="reminder">Reminder</option></select></label>
    </div>
    {items === null && <Skeleton className="h-48" label="Loading notifications" />}
    {error && <div role="alert" className="rounded-md border border-risk/40 bg-risk-soft p-4 text-sm text-risk" data-testid="notifications-error">{error}</div>}
    {items && !error && items.length === 0 && <EmptyState icon={<Bell className="h-6 w-6" />} title="No notifications here" description="New property, task and reminder updates will appear when they need your attention." data-testid="notifications-empty" />}
    {items && !error && <ul className="divide-y divide-border border-y border-border bg-surface" data-testid="notifications-list">{items.map((item) => { const Icon = iconFor(item.category); return <li key={item.id} className={`flex gap-3 p-4 ${item.read_at ? "" : "bg-eucalyptus-soft/30"}`} data-testid={`notification-${item.id}`}><span className="mt-0.5 inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-canvas-deep text-eucalyptus-deep"><Icon className="h-4 w-4" /></span><div className="min-w-0 flex-1"><div className="flex flex-wrap items-center gap-2"><h2 className="font-semibold">{item.title}</h2>{item.is_expired && <span className="text-xs text-muted" data-testid={`notification-expired-${item.id}`}>Expired</span>}</div><p className="mt-1 text-sm text-charcoal">{item.message}</p>{item.property_address && <p className="mt-1 text-xs text-muted">{item.property_address}</p>}<p className="mt-2 text-xs text-muted">{formatDate(item.created_at)}</p><div className="mt-3 flex flex-wrap gap-2"><Button size="sm" variant="secondary" onClick={() => void update(item, { read: !item.read_at })} data-testid={`notification-read-${item.id}`}>{item.read_at ? "Mark unread" : "Mark read"}</Button><Button size="sm" variant="tertiary" icon={<ExternalLink className="h-3.5 w-3.5" />} onClick={() => void update(item, { read: true }, true)} disabled={item.is_expired} data-testid={`notification-open-${item.id}`}>Open</Button><Button size="sm" variant="tertiary" icon={<Trash2 className="h-3.5 w-3.5" />} onClick={() => void update(item, { dismissed: true })} data-testid={`notification-dismiss-${item.id}`}>Dismiss</Button></div></div></li>; })}</ul>}
  </>;
}