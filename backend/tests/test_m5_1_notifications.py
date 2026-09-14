"""Focused acceptance coverage for M5.1. Must run on a disposable verification database."""
from __future__ import annotations

import asyncio
import os
import uuid
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import func, select

from app.db.base import get_sessionmaker
from app.db.models import (
    NotificationDeliveryAttempt,
    NotificationEvent,
    NotificationPreference,
    PropertyTask,
    RecipientNotification,
    User,
    Workspace,
)
from app.services.ics import task_ics
from app.services.notifications import create_notification_event
from app.services.reminders import process_workspace_reminders


pytestmark = pytest.mark.asyncio


async def _login(client: AsyncClient, email: str) -> None:
    response = await client.post("/api/auth/login", json={"email": email, "password": "Prototype2026pass"})
    assert response.status_code == 200, response.text


async def _journey(client: AsyncClient) -> str:
    response = await client.get("/api/journeys")
    assert response.status_code == 200, response.text
    return response.json()[0]["id"]


async def _owner_context() -> tuple[uuid.UUID, User]:
    async with get_sessionmaker()() as db:
        user = (await db.execute(select(User).where(User.email == "owner@propertyacquisition-demo.com"))).scalar_one()
        workspace_id = (await db.execute(select(Workspace.id).where(Workspace.owner_user_id == user.id))).scalar_one()
        return workspace_id, user


@pytest_asyncio.fixture(autouse=True)
async def disposable_database_only() -> None:
    assert os.environ.get("M5_1_VERIFY_ISOLATED_DB") == "1"


async def test_event_fingerprint_is_workspace_idempotent_and_concurrent() -> None:
    workspace_id, user = await _owner_context()
    fingerprint = "m5-test:concurrent-fingerprint"

    async def worker() -> None:
        async with get_sessionmaker()() as db:
            await create_notification_event(
                db, workspace_id=workspace_id, category="new_property", fingerprint=fingerprint,
                title="A property was added", message="Deterministic test event.", safe_deep_link="/app/discover",
                recipient_ids={user.id},
            )
            await db.commit()

    await asyncio.gather(worker(), worker())
    async with get_sessionmaker()() as db:
        events = (await db.execute(select(func.count()).select_from(NotificationEvent).where(NotificationEvent.workspace_id == workspace_id, NotificationEvent.event_fingerprint == fingerprint))).scalar_one()
        inbox = (await db.execute(select(func.count()).select_from(RecipientNotification).join(NotificationEvent).where(NotificationEvent.event_fingerprint == fingerprint))).scalar_one()
        deliveries = (await db.execute(select(func.count()).select_from(NotificationDeliveryAttempt).join(RecipientNotification).join(NotificationEvent).where(NotificationEvent.event_fingerprint == fingerprint))).scalar_one()
    assert (events, inbox, deliveries) == (1, 1, 1)


async def test_preferences_email_unavailable_quiet_hours_and_critical_override(async_client: AsyncClient) -> None:
    await _login(async_client, "owner@propertyacquisition-demo.com")
    email = await async_client.put("/api/notifications/preferences/price_change", json={"requested_channel": "email"})
    both = await async_client.put("/api/notifications/preferences/price_change", json={"requested_channel": "both"})
    assert email.status_code == both.status_code == 422
    assert email.json()["detail"]["code"] == "email_provider_not_connected"
    global_saved = await async_client.put("/api/notifications/preferences/global", json={"in_app_enabled": True, "quiet_hours_start": "21:00", "quiet_hours_end": "07:00", "timezone": "Australia/Perth", "due_soon_minutes": 60, "report_daily_enabled": False, "report_weekly_enabled": False, "report_monthly_enabled": False})
    assert global_saved.status_code == 200
    workspace_id, user = await _owner_context()
    quiet = datetime(2026, 9, 15, 13, 30, tzinfo=timezone.utc)  # 21:30 Australia/Perth
    async with get_sessionmaker()() as db:
        event = await create_notification_event(db, workspace_id=workspace_id, category="price_change", fingerprint="m5-test:quiet-price", title="Price changed", message="Quiet event.", safe_deep_link="/app/discover", recipient_ids={user.id}, now=quiet)
        await db.commit()
        suppressed = (await db.execute(select(func.count()).select_from(RecipientNotification).where(RecipientNotification.notification_event_id == event.id))).scalar_one()
        critical = await create_notification_event(db, workspace_id=workspace_id, category="critical_service", fingerprint="m5-test:critical", title="Service notice", message="Critical event.", safe_deep_link="/app/settings", recipient_ids={user.id}, now=quiet)
        await db.commit()
        critical_count = (await db.execute(select(func.count()).select_from(RecipientNotification).where(RecipientNotification.notification_event_id == critical.id))).scalar_one()
        await create_notification_event(db, workspace_id=workspace_id, category="price_change", fingerprint="m5-test:quiet-price", title="Price changed", message="Quiet event.", safe_deep_link="/app/discover", recipient_ids={user.id}, now=datetime(2026, 9, 15, 23, 1, tzinfo=timezone.utc))
        await db.commit()
        replayed = (await db.execute(select(func.count()).select_from(RecipientNotification).where(RecipientNotification.notification_event_id == event.id))).scalar_one()
        email_deliveries = (await db.execute(select(func.count()).select_from(NotificationDeliveryAttempt).where(NotificationDeliveryAttempt.channel == "email"))).scalar_one()
    assert (suppressed, critical_count, replayed, email_deliveries) == (0, 1, 1, 0)


async def test_task_crud_concurrency_ics_and_cross_tenant_404(async_client: AsyncClient) -> None:
    await _login(async_client, "owner@propertyacquisition-demo.com")
    journey_id = await _journey(async_client)
    due = "2026-10-08T10:15:00"
    created = await async_client.post(f"/api/journeys/{journey_id}/tasks", json={"property_id": None, "title": "Request title search", "notes": "Bring the contract conditions.", "assignee_user_id": None, "priority": "high", "due_at": due, "timezone": "Australia/Perth", "reminder_offset_minutes": 60})
    assert created.status_code == 201, created.text
    task = created.json()
    stale = await async_client.patch(f"/api/journeys/{journey_id}/tasks/{task['id']}", json={"expected_row_version": task["row_version"] + 1, "title": "stale"})
    edited = await async_client.patch(f"/api/journeys/{journey_id}/tasks/{task['id']}", json={"expected_row_version": task["row_version"], "title": "Request title search and strata plan"})
    assert stale.status_code == 409 and edited.status_code == 200
    completed = await async_client.patch(f"/api/journeys/{journey_id}/tasks/{task['id']}", json={"expected_row_version": edited.json()["row_version"], "status": "completed"})
    reopened = await async_client.patch(f"/api/journeys/{journey_id}/tasks/{task['id']}", json={"expected_row_version": completed.json()["row_version"], "status": "open"})
    assert completed.json()["done"] is True and reopened.json()["done"] is False
    ics = await async_client.get(f"/api/journeys/{journey_id}/tasks/{task['id']}/calendar.ics")
    assert ics.status_code == 200 and "text/calendar" in ics.headers["content-type"]
    assert f"UID:{task['id']}@property-acquisition.local" in ics.text and "DTSTART;TZID=Australia/Perth:20261008T101500" in ics.text
    await _login(async_client, "other@propertyacquisition-demo.com")
    assert (await async_client.get(f"/api/journeys/{journey_id}/tasks/{task['id']}")).status_code == 404
    assert (await async_client.patch(f"/api/journeys/{journey_id}/tasks/{task['id']}", json={"expected_row_version": reopened.json()["row_version"], "status": "completed"})).status_code == 404
    await _login(async_client, "owner@propertyacquisition-demo.com")
    deleted = await async_client.delete(f"/api/journeys/{journey_id}/tasks/{task['id']}?expected_row_version={reopened.json()['row_version']}")
    assert deleted.status_code == 204


async def test_reminder_replay_due_soon_and_overdue_transitions() -> None:
    workspace_id, user = await _owner_context()
    now = datetime(2026, 9, 15, 8, 0, tzinfo=timezone.utc)
    async with get_sessionmaker()() as db:
        journey_id = (await db.execute(select(PropertyTask.journey_id).where(PropertyTask.workspace_id == workspace_id).limit(1))).scalar_one()
        soon = PropertyTask(workspace_id=workspace_id, journey_id=journey_id, title="Due soon test", assignee_user_id=user.id, priority="high", due_at=now + timedelta(minutes=30), timezone="Australia/Perth", reminder_offset_minutes=60, status="open", created_by=user.id)
        overdue = PropertyTask(workspace_id=workspace_id, journey_id=journey_id, title="Overdue test", assignee_user_id=user.id, priority="high", due_at=now - timedelta(minutes=15), timezone="Australia/Perth", reminder_offset_minutes=60, status="open", created_by=user.id)
        db.add_all([soon, overdue])
        await db.commit()
        first = await process_workspace_reminders(db, workspace_id, now=now)
        await db.commit()
        second = await process_workspace_reminders(db, workspace_id, now=now + timedelta(minutes=1))
        await db.commit()
        categories = (await db.execute(select(NotificationEvent.category).where(NotificationEvent.workspace_id == workspace_id, NotificationEvent.task_id.in_([soon.id, overdue.id])))).scalars().all()
    assert first["due_soon"] >= 1 and first["overdue"] >= 1 and first["reminder"] >= 1
    assert second["due_soon"] >= 1 and second["overdue"] >= 1
    assert categories.count("task_due_soon") == 1 and categories.count("task_overdue") == 1 and categories.count("reminder") == 1


async def test_inbox_deep_links_read_unread_dismiss_and_demo_only_seed(async_client: AsyncClient) -> None:
    await _login(async_client, "owner@propertyacquisition-demo.com")
    listed = await async_client.get("/api/notifications")
    assert listed.status_code == 200
    item = next(row for row in listed.json()["items"] if row["safe_deep_link"].startswith("/app/"))
    marked = await async_client.patch(f"/api/notifications/{item['id']}", json={"read": True})
    unread = await async_client.patch(f"/api/notifications/{item['id']}", json={"read": False})
    dismissed = await async_client.patch(f"/api/notifications/{item['id']}", json={"dismissed": True})
    assert marked.status_code == unread.status_code == dismissed.status_code == 200
    await _login(async_client, "other@propertyacquisition-demo.com")
    other = await async_client.get("/api/notifications")
    assert other.status_code == 200 and other.json()["items"] == []
    assert (await async_client.patch(f"/api/notifications/{item['id']}", json={"read": True})).status_code == 404


async def test_ics_and_notification_services_make_no_external_requests() -> None:
    workspace_id, user = await _owner_context()
    task = PropertyTask(id=uuid.uuid4(), workspace_id=workspace_id, journey_id=uuid.uuid4(), title="Offline calendar", timezone="Australia/Perth", due_at=datetime(2026, 9, 20, 2, tzinfo=timezone.utc), status="open", created_by=user.id)
    with patch("socket.create_connection", side_effect=AssertionError("external request attempted")):
        calendar = task_ics(task, "81C Example Street, Perth WA")
    assert "BEGIN:VCALENDAR" in calendar and "LOCATION:81C Example Street\\, Perth WA" in calendar