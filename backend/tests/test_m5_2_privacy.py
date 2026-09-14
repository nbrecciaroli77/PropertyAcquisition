"""Targeted acceptance coverage for M5.2: report previews, exports and deletion.
Runs against the live application database using disposable synthetic accounts under a
dedicated test email domain; the demo owner/other accounts and their workspaces are never
mutated destructively. All test users/workspaces are torn down at the end of the session."""
from __future__ import annotations

import io
import uuid
import zipfile
from datetime import datetime, timedelta, timezone

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import delete, func, select

from app.core.security import hash_password
from app.db.base import get_sessionmaker
from app.db.models import (
    AuditEvent,
    AuthSession,
    AuthToken,
    BriefVersion,
    DataExport,
    DeletionRequest,
    Journey,
    LoginAttempt,
    Membership,
    NotificationEvent,
    OutboxMessage,
    RecipientNotification,
    ReportPreference,
    ReportRun,
    User,
    Workspace,
)
from app.services.deletion import process_due_deletions

pytestmark = pytest.mark.asyncio

TEST_DOMAIN = "m52tests.pa-prototype.com"
PASSWORD = "Prototype2026pass"
_created_user_ids: list[uuid.UUID] = []
_created_workspace_ids: list[uuid.UUID] = []


@pytest_asyncio.fixture(autouse=True, scope="session")
async def _module_cleanup():
    yield
    async with get_sessionmaker()() as db:
        ids = _created_user_ids
        ws_ids = _created_workspace_ids
        if ws_ids:
            await db.execute(delete(BriefVersion).where(BriefVersion.workspace_id.in_(ws_ids)))
            await db.execute(delete(Journey).where(Journey.workspace_id.in_(ws_ids)))
        if ids:
            await db.execute(delete(AuditEvent).where(AuditEvent.actor_user_id.in_(ids)))
            await db.execute(delete(AuthSession).where(AuthSession.user_id.in_(ids)))
            await db.execute(delete(AuthToken).where(AuthToken.user_id.in_(ids)))
            await db.execute(delete(Membership).where(Membership.user_id.in_(ids)))
        if ws_ids:
            await db.execute(delete(Workspace).where(Workspace.id.in_(ws_ids)))
        await db.execute(delete(OutboxMessage).where(OutboxMessage.to_email.like(f"%@{TEST_DOMAIN}")))
        await db.execute(delete(LoginAttempt).where(LoginAttempt.identifier.like(f"%{TEST_DOMAIN}%")))
        if ids:
            await db.execute(delete(User).where(User.id.in_(ids)))
        await db.commit()


async def _register(client: AsyncClient, prefix: str) -> tuple[str, uuid.UUID, uuid.UUID]:
    email = f"{prefix}-{uuid.uuid4().hex[:8]}@{TEST_DOMAIN}"
    r = await client.post("/api/auth/signup", json={"email": email, "password": PASSWORD, "display_name": prefix})
    assert r.status_code == 201, r.text
    outbox = (await client.get("/api/dev/outbox", params={"email": email})).json()
    token = next(m for m in outbox if m["kind"] == "verify_email")["action_url"].split("token=")[1]
    assert (await client.post("/api/auth/verify-email", json={"token": token})).status_code == 200
    await _login(client, email)
    me = (await client.get("/api/auth/me")).json()
    user_id, workspace_id = uuid.UUID(me["user"]["id"]), uuid.UUID(me["workspace"]["id"])
    _created_user_ids.append(user_id)
    _created_workspace_ids.append(workspace_id)
    return email, user_id, workspace_id


async def _login(client: AsyncClient, email: str) -> None:
    r = await client.post("/api/auth/login", json={"email": email, "password": PASSWORD})
    assert r.status_code == 200, r.text


async def _journey(client: AsyncClient) -> str:
    r = await client.post("/api/journeys", json={"name": "Test journey", "timezone": "Australia/Perth"})
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def test_report_generation_deterministic_idempotent_and_notification_dedup(async_client: AsyncClient) -> None:
    email, user_id, workspace_id = await _register(async_client, "reportgen")
    journey_id = await _journey(async_client)
    first = await async_client.post(f"/api/journeys/{journey_id}/reports/daily/generate", json={"release_kind": "preview"})
    second = await async_client.post(f"/api/journeys/{journey_id}/reports/daily/generate", json={"release_kind": "preview"})
    assert first.status_code == second.status_code == 200
    assert first.json()["id"] == second.json()["id"], "identical requests must not create duplicate report runs"
    async with get_sessionmaker()() as db:
        run_count = (await db.execute(select(func.count()).select_from(ReportRun).where(ReportRun.workspace_id == workspace_id))).scalar_one()
        notif_count = (
            await db.execute(
                select(func.count()).select_from(RecipientNotification).join(NotificationEvent)
                .where(NotificationEvent.workspace_id == workspace_id, NotificationEvent.category == "digest_ready", RecipientNotification.recipient_user_id == user_id)
            )
        ).scalar_one()
    assert run_count == 1
    assert notif_count == 1, "identical requests must not create duplicate report-ready notifications"


async def test_weekly_and_monthly_period_boundaries_perth_timezone(async_client: AsyncClient) -> None:
    await _register(async_client, "periods")
    journey_id = await _journey(async_client)
    weekly = (await async_client.post(f"/api/journeys/{journey_id}/reports/weekly/generate", json={"release_kind": "preview"})).json()
    monthly = (await async_client.post(f"/api/journeys/{journey_id}/reports/monthly/generate", json={"release_kind": "preview"})).json()
    w_start, w_end = datetime.fromisoformat(weekly["period_start"]), datetime.fromisoformat(weekly["period_end"])
    assert (w_end - w_start) == timedelta(days=7)
    assert weekly["timezone"] == "Australia/Perth"
    m_start, m_end = datetime.fromisoformat(monthly["period_start"]), datetime.fromisoformat(monthly["period_end"])
    assert m_start < m_end and m_start.astimezone(timezone(timedelta(hours=8))).day == 1


async def test_daily_quiet_day_and_unknown_preservation_with_no_properties(async_client: AsyncClient) -> None:
    await _register(async_client, "quietday")
    journey_id = await _journey(async_client)
    run = (await async_client.post(f"/api/journeys/{journey_id}/reports/daily/generate", json={"release_kind": "preview"})).json()
    snap = run["snapshot"]
    assert snap["quiet_day"] is True
    assert snap["current_candidates"] == []
    assert all(c.get("travel_line") is None for c in snap["current_candidates"])
    assert "not yet tracked" in snap["upcoming_home_opens_note"]


async def test_monthly_partial_period_labeled_for_fresh_journey(async_client: AsyncClient) -> None:
    await _register(async_client, "partial")
    journey_id = await _journey(async_client)
    run = (await async_client.post(f"/api/journeys/{journey_id}/reports/monthly/generate", json={"release_kind": "preview"})).json()
    assert run["is_partial_period"] is True
    assert run["snapshot"]["is_partial_period"] is True
    assert run["snapshot"]["actual_coverage_start"] is not None


async def test_report_cross_tenant_isolation(async_client: AsyncClient) -> None:
    await _register(async_client, "tenanta")
    journey_a = await _journey(async_client)
    run_a = (await async_client.post(f"/api/journeys/{journey_a}/reports/daily/generate", json={"release_kind": "preview"})).json()
    await _register(async_client, "tenantb")
    leaked = await async_client.get(f"/api/journeys/{journey_a}/reports/{run_a['id']}")
    assert leaked.status_code == 404
    leaked_list = await async_client.get(f"/api/journeys/{journey_a}/reports")
    assert leaked_list.status_code == 404


async def test_report_channel_requested_vs_effective(async_client: AsyncClient) -> None:
    await _register(async_client, "channel")
    in_app = await async_client.put("/api/reports/preferences/daily", json={"enabled": True, "local_time": "07:00", "weekdays": [0, 1, 2, 3, 4, 5, 6], "day_of_week": None, "day_of_month": None, "timezone": "Australia/Perth", "requested_channel": "in_app"})
    assert in_app.status_code == 200
    assert in_app.json()["requested_channel"] == "in_app" and in_app.json()["effective_channel"] == "in_app"
    for channel in ("email", "both"):
        rejected = await async_client.put("/api/reports/preferences/daily", json={"enabled": True, "local_time": "07:00", "weekdays": [], "day_of_week": None, "day_of_month": None, "timezone": "Australia/Perth", "requested_channel": channel})
        assert rejected.status_code == 422
        assert rejected.json()["detail"]["code"] == "email_provider_not_connected"
    async with get_sessionmaker()() as db:
        pref = (await db.execute(select(ReportPreference).where(ReportPreference.report_type == "daily").order_by(ReportPreference.created_at.desc()))).scalars().first()
        assert pref.requested_channel == "in_app" and pref.effective_channel == "in_app"


async def test_export_personal_contents_excludes_secrets(async_client: AsyncClient) -> None:
    await _register(async_client, "exportme")
    created = await async_client.post("/api/exports/personal")
    assert created.status_code == 201
    export_id = created.json()["id"]
    downloaded = await async_client.get(f"/api/exports/{export_id}/download")
    assert downloaded.status_code == 200 and downloaded.headers["content-type"] == "application/zip"
    with zipfile.ZipFile(io.BytesIO(downloaded.content)) as zf:
        names = zf.namelist()
        assert "manifest.json" in names and "profile.json" in names
        for name in names:
            content = zf.read(name).decode("utf-8")
            assert "password_hash" not in content and "refresh_token_hash" not in content and "token_hash" not in content


async def test_export_workspace_requires_owner_and_isolated(async_client: AsyncClient) -> None:
    owner_email, owner_id, workspace_id = await _register(async_client, "wsowner")
    editor_email = f"wseditor-{uuid.uuid4().hex[:8]}@{TEST_DOMAIN}"
    async with get_sessionmaker()() as db:
        editor = User(email=editor_email, password_hash=hash_password(PASSWORD), display_name="editor", email_verified_at=datetime.now(timezone.utc))
        db.add(editor)
        await db.flush()
        db.add(Membership(workspace_id=workspace_id, user_id=editor.id, role="editor"))
        await db.commit()
        _created_user_ids.append(editor.id)
    await _login(async_client, editor_email)
    forbidden = await async_client.post("/api/exports/workspace")
    assert forbidden.status_code == 403
    await _login(async_client, owner_email)
    allowed = await async_client.post("/api/exports/workspace")
    assert allowed.status_code == 201
    manifest = allowed.json()["manifest"]
    assert "credential" in " ".join(manifest["excludes"]).lower()
    await _login(async_client, editor_email)
    isolated = await async_client.get("/api/exports")
    assert isolated.json() == [], "another member's export request must not be visible to this requester"


async def test_export_expiry_blocks_download(async_client: AsyncClient) -> None:
    await _register(async_client, "expiry")
    created = (await async_client.post("/api/exports/personal")).json()
    async with get_sessionmaker()() as db:
        export = (await db.execute(select(DataExport).where(DataExport.id == uuid.UUID(created["id"])))).scalar_one()
        export.expires_at = datetime.now(timezone.utc) - timedelta(hours=1)
        await db.commit()
    expired = await async_client.get(f"/api/exports/{created['id']}/download")
    assert expired.status_code == 410


async def test_deletion_reauth_and_typed_confirmation_required(async_client: AsyncClient) -> None:
    await _register(async_client, "reauth")
    wrong_password = await async_client.post("/api/account/deletion-requests", json={"request_type": "delete_account", "password": "wrong-password", "typed_confirmation": "DELETE"})
    assert wrong_password.status_code == 401 and wrong_password.json()["detail"]["code"] == "reauthentication_failed"
    wrong_confirmation = await async_client.post("/api/account/deletion-requests", json={"request_type": "delete_account", "password": PASSWORD, "typed_confirmation": "delete please"})
    assert wrong_confirmation.status_code == 422 and wrong_confirmation.json()["detail"]["code"] == "confirmation_mismatch"


async def test_deletion_ownership_transfer_blocks_shared_workspace(async_client: AsyncClient) -> None:
    owner_email, owner_id, workspace_id = await _register(async_client, "sharedowner")
    _, editor_id, _ = await _register(async_client, "sharededitor")
    async with get_sessionmaker()() as db:
        db.add(Membership(workspace_id=workspace_id, user_id=editor_id, role="editor"))
        await db.commit()
    await _login(async_client, owner_email)
    blocked = await async_client.post("/api/account/deletion-requests", json={"request_type": "delete_account", "password": PASSWORD, "typed_confirmation": "DELETE"})
    assert blocked.status_code == 422 and blocked.json()["detail"]["code"] == "ownership_transfer_required"
    leave_blocked = await async_client.post("/api/account/deletion-requests", json={"request_type": "leave_workspace", "password": PASSWORD, "typed_confirmation": "DELETE", "target_workspace_id": str(workspace_id)})
    assert leave_blocked.status_code == 422 and leave_blocked.json()["detail"]["code"] == "ownership_transfer_required"


async def test_deletion_cancel_pending_request(async_client: AsyncClient) -> None:
    await _register(async_client, "cancelme")
    created = await async_client.post("/api/account/deletion-requests", json={"request_type": "delete_account", "password": PASSWORD, "typed_confirmation": "DELETE"})
    assert created.status_code == 201 and created.json()["state"] == "pending_cooloff"
    request_id = created.json()["id"]
    cancelled = await async_client.post(f"/api/account/deletion-requests/{request_id}/cancel")
    assert cancelled.status_code == 200 and cancelled.json()["state"] == "cancelled"
    already = await async_client.post(f"/api/account/deletion-requests/{request_id}/cancel")
    assert already.status_code == 422


async def test_deletion_execution_revokes_sessions_and_deletes_workspace_isolated(async_client: AsyncClient) -> None:
    _, target_user_id, target_workspace_id = await _register(async_client, "deleteme")
    _, other_user_id, other_workspace_id = await _register(async_client, "untouched")
    async with get_sessionmaker()() as db:
        target_user = (await db.execute(select(User).where(User.id == target_user_id))).scalar_one()
        target_email = target_user.email
    await _login(async_client, target_email)
    created = await async_client.post("/api/account/deletion-requests", json={"request_type": "delete_account", "password": PASSWORD, "typed_confirmation": "DELETE"})
    assert created.status_code == 201
    async with get_sessionmaker()() as db:
        request = (await db.execute(select(DeletionRequest).where(DeletionRequest.id == uuid.UUID(created.json()["id"])))).scalar_one()
        request.scheduled_execute_at = datetime.now(timezone.utc) - timedelta(hours=1)
        await db.commit()
        outcome = await process_due_deletions(db)
        await db.commit()
        assert outcome["processed"] >= 1
        deleted_workspace = (await db.execute(select(Workspace).where(Workspace.id == target_workspace_id))).scalar_one_or_none()
        assert deleted_workspace is None, "solely owned workspace must be deleted"
        untouched_workspace = (await db.execute(select(Workspace).where(Workspace.id == other_workspace_id))).scalar_one_or_none()
        assert untouched_workspace is not None, "other workspaces must never be affected"
        target_user_after = (await db.execute(select(User).where(User.id == target_user_id))).scalar_one()
        assert target_user_after.deleted_at is not None
        assert target_user_after.email != target_email
        live_sessions = (await db.execute(select(func.count()).select_from(AuthSession).where(AuthSession.user_id == target_user_id, AuthSession.revoked_at.is_(None)))).scalar_one()
        assert live_sessions == 0


async def test_no_email_queued_for_reports_exports_or_deletion(async_client: AsyncClient) -> None:
    email, _, _ = await _register(async_client, "noemail")
    journey_id = await _journey(async_client)
    async with get_sessionmaker()() as db:
        before = (await db.execute(select(func.count()).select_from(OutboxMessage).where(OutboxMessage.to_email == email, OutboxMessage.kind.notin_(("verify_email",))))).scalar_one()
    await async_client.post(f"/api/journeys/{journey_id}/reports/daily/generate", json={"release_kind": "preview"})
    await async_client.post("/api/exports/personal")
    await async_client.post("/api/account/deletion-requests", json={"request_type": "delete_account", "password": PASSWORD, "typed_confirmation": "DELETE"})
    async with get_sessionmaker()() as db:
        after = (await db.execute(select(func.count()).select_from(OutboxMessage).where(OutboxMessage.to_email == email, OutboxMessage.kind.notin_(("verify_email",))))).scalar_one()
    assert before == after == 0
