"""Local ICS serialization only; no calendar provider is contacted."""
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

from app.core.config import get_settings
from app.db.models import PropertyTask


def _escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,").replace("\n", "\\n")


def task_ics(task: PropertyTask, property_address: str | None) -> str:
    if task.due_at is None:
        raise ValueError("A due time is required for calendar export")
    zone = ZoneInfo(task.timezone)
    local = task.due_at.astimezone(zone)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    due = local.strftime("%Y%m%dT%H%M%S")
    description = task.notes or ""
    if property_address:
        description = f"{description}\nRelated property: {property_address}".strip()
    link = f"{get_settings().app_base_url}/app/tasks?task={task.id}"
    return "\r\n".join([
        "BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//Property Acquisition//Tasks//EN", "CALSCALE:GREGORIAN",
        "BEGIN:VEVENT", f"UID:{task.id}@property-acquisition.local", f"DTSTAMP:{stamp}",
        f"DTSTART;TZID={task.timezone}:{due}", f"SUMMARY:{_escape(task.title)}",
        f"DESCRIPTION:{_escape(description)}", f"LOCATION:{_escape(property_address or '')}", f"URL:{link}",
        "STATUS:CONFIRMED", "END:VEVENT", "END:VCALENDAR", "",
    ])