"""Personal and workspace data export. Files are generated on demand and stored as bytes in
Postgres; no object storage or other external service is connected. Downloads require the
requesting user's own authenticated session and expire after a fixed window."""
from __future__ import annotations

import io
import json
import zipfile
from datetime import timedelta
from typing import Any

from sqlalchemy import inspect, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import now_utc
from app.db.models import (
    ActivityEvent,
    AuditEvent,
    BriefVersion,
    BuyerProperty,
    ConnectorInstance,
    CsvImportBatch,
    DataExport,
    DiscoveryEvent,
    DuplicateProposal,
    Fact,
    GateWaiver,
    IntakeEvent,
    Journey,
    ListingCampaign,
    MatchEvaluation,
    Membership,
    NotificationEvent,
    Observation,
    Property,
    PropertyNote,
    PropertyTask,
    RecipientNotification,
    ReportRun,
    SenderAlias,
    SourceReadiness,
    User,
    Workspace,
)

EXPORT_EXPIRY_HOURS = 24
_EXCLUDED_COLUMNS = {"password_hash", "refresh_token_hash", "token_hash", "credential_ref"}


def _row_dict(obj: Any) -> dict[str, Any]:
    mapper = inspect(obj).mapper
    out: dict[str, Any] = {}
    for column in mapper.columns:
        if column.key in _EXCLUDED_COLUMNS:
            continue
        value = getattr(obj, column.key)
        out[column.key] = str(value) if value is not None else None
    return out


def _write_json(zf: zipfile.ZipFile, name: str, payload: Any) -> None:
    zf.writestr(name, json.dumps(payload, default=str, indent=2))


async def build_personal_export(db: AsyncSession, *, user: User) -> tuple[bytes, dict[str, Any]]:
    memberships = (
        await db.execute(
            select(Membership, Workspace.name).join(Workspace, Workspace.id == Membership.workspace_id).where(Membership.user_id == user.id)
        )
    ).all()
    notifications = (
        await db.execute(
            select(RecipientNotification, NotificationEvent)
            .join(NotificationEvent, NotificationEvent.id == RecipientNotification.notification_event_id)
            .where(RecipientNotification.recipient_user_id == user.id)
        )
    ).all()
    tasks = (
        await db.execute(select(PropertyTask).where((PropertyTask.assignee_user_id == user.id) | (PropertyTask.created_by == user.id)))
    ).scalars().all()
    audit = (
        await db.execute(select(AuditEvent).where(AuditEvent.actor_user_id == user.id).order_by(AuditEvent.created_at.desc()).limit(500))
    ).scalars().all()
    manifest = {
        "export_type": "personal",
        "generated_at": now_utc().isoformat(),
        "user_id": str(user.id),
        "contents": ["profile.json", "memberships.json", "notifications.json", "tasks.json", "audit_events.json"],
        "excludes": ["password hashes", "session/refresh tokens", "verification/reset tokens", "other users' or workspaces' data"],
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        _write_json(zf, "manifest.json", manifest)
        _write_json(
            zf, "profile.json",
            {
                "id": str(user.id), "email": user.email, "display_name": user.display_name, "timezone": user.timezone,
                "locale": user.locale, "email_verified": user.email_verified_at is not None, "created_at": user.created_at.isoformat(),
            },
        )
        _write_json(zf, "memberships.json", [{"workspace_id": str(m.workspace_id), "workspace_name": name, "role": m.role} for m, name in memberships])
        _write_json(
            zf, "notifications.json",
            [
                {"category": e.category, "title": e.title, "message": e.message, "created_at": r.created_at.isoformat(), "read_at": r.read_at.isoformat() if r.read_at else None}
                for r, e in notifications
            ],
        )
        _write_json(zf, "tasks.json", [_row_dict(t) for t in tasks])
        _write_json(zf, "audit_events.json", [_row_dict(a) for a in audit])
    return buffer.getvalue(), manifest


async def build_workspace_export(db: AsyncSession, *, workspace: Workspace) -> tuple[bytes, dict[str, Any]]:
    async def rows(model: Any, *filters: Any) -> list[Any]:
        return list((await db.execute(select(model).where(*filters))).scalars().all())

    journeys = await rows(Journey, Journey.workspace_id == workspace.id)
    brief_versions = await rows(BriefVersion, BriefVersion.workspace_id == workspace.id)
    properties = await rows(Property, Property.workspace_id == workspace.id)
    buyer_properties = await rows(BuyerProperty, BuyerProperty.workspace_id == workspace.id)
    campaigns = await rows(ListingCampaign, ListingCampaign.workspace_id == workspace.id)
    observations = await rows(Observation, Observation.workspace_id == workspace.id)
    facts = await rows(Fact, Fact.workspace_id == workspace.id)
    evaluations = await rows(MatchEvaluation, MatchEvaluation.workspace_id == workspace.id)
    waivers = await rows(GateWaiver, GateWaiver.workspace_id == workspace.id)
    notes = await rows(PropertyNote, PropertyNote.workspace_id == workspace.id)
    tasks = await rows(PropertyTask, PropertyTask.workspace_id == workspace.id)
    activity_events = await rows(ActivityEvent, ActivityEvent.workspace_id == workspace.id)
    intake_events = await rows(IntakeEvent, IntakeEvent.workspace_id == workspace.id)
    csv_batches = await rows(CsvImportBatch, CsvImportBatch.workspace_id == workspace.id)
    discovery_events = await rows(DiscoveryEvent, DiscoveryEvent.workspace_id == workspace.id)
    duplicate_proposals = await rows(DuplicateProposal, DuplicateProposal.workspace_id == workspace.id)
    notification_events = await rows(NotificationEvent, NotificationEvent.workspace_id == workspace.id)
    report_runs = await rows(ReportRun, ReportRun.workspace_id == workspace.id)
    connector_instances = await rows(ConnectorInstance, ConnectorInstance.workspace_id == workspace.id)
    source_readiness = await rows(SourceReadiness, SourceReadiness.workspace_id == workspace.id)
    sender_aliases = await rows(SenderAlias, SenderAlias.workspace_id == workspace.id)
    audit_events = await rows(AuditEvent, AuditEvent.workspace_id == workspace.id)

    manifest = {
        "export_type": "workspace",
        "generated_at": now_utc().isoformat(),
        "workspace_id": str(workspace.id),
        "workspace_name": workspace.name,
        "contents": [
            "journeys.json", "brief_versions.json", "properties.json", "buyer_properties.json", "listing_campaigns.json",
            "observations.json", "facts.json", "match_evaluations.json", "gate_waivers.json", "property_notes.json",
            "property_tasks.json", "activity_events.json", "intake_events.json", "csv_import_batches.json",
            "discovery_events.json", "duplicate_proposals.json", "notification_events.json", "report_runs.json",
            "connector_instances.json", "source_readiness.json", "sender_aliases.json", "audit_events.json",
        ],
        "excludes": ["password hashes", "session/refresh tokens", "verification/reset tokens", "credential references", "other workspaces' data"],
    }
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        _write_json(zf, "manifest.json", manifest)
        _write_json(zf, "journeys.json", [_row_dict(j) for j in journeys])
        _write_json(zf, "brief_versions.json", [_row_dict(b) for b in brief_versions])
        _write_json(zf, "properties.json", [_row_dict(p) for p in properties])
        _write_json(zf, "buyer_properties.json", [_row_dict(b) for b in buyer_properties])
        _write_json(zf, "listing_campaigns.json", [_row_dict(c) for c in campaigns])
        _write_json(zf, "observations.json", [_row_dict(o) for o in observations])
        _write_json(zf, "facts.json", [_row_dict(f) for f in facts])
        _write_json(zf, "match_evaluations.json", [_row_dict(e) for e in evaluations])
        _write_json(zf, "gate_waivers.json", [_row_dict(w) for w in waivers])
        _write_json(zf, "property_notes.json", [_row_dict(n) for n in notes])
        _write_json(zf, "property_tasks.json", [_row_dict(t) for t in tasks])
        _write_json(zf, "activity_events.json", [_row_dict(a) for a in activity_events])
        _write_json(zf, "intake_events.json", [_row_dict(i) for i in intake_events])
        _write_json(zf, "csv_import_batches.json", [_row_dict(c) for c in csv_batches])
        _write_json(zf, "discovery_events.json", [_row_dict(d) for d in discovery_events])
        _write_json(zf, "duplicate_proposals.json", [_row_dict(d) for d in duplicate_proposals])
        _write_json(zf, "notification_events.json", [_row_dict(n) for n in notification_events])
        _write_json(zf, "report_runs.json", [_row_dict(r) for r in report_runs])
        _write_json(zf, "connector_instances.json", [_row_dict(c) for c in connector_instances])
        _write_json(zf, "source_readiness.json", [_row_dict(s) for s in source_readiness])
        _write_json(zf, "sender_aliases.json", [_row_dict(s) for s in sender_aliases])
        _write_json(zf, "audit_events.json", [_row_dict(a) for a in audit_events])
    return buffer.getvalue(), manifest


async def create_export(db: AsyncSession, *, requested_by: User, workspace: Workspace, export_type: str) -> DataExport:
    if export_type == "personal":
        data, manifest = await build_personal_export(db, user=requested_by)
    else:
        data, manifest = await build_workspace_export(db, workspace=workspace)
    export = DataExport(
        workspace_id=workspace.id, requested_by_user_id=requested_by.id, export_type=export_type, state="ready",
        manifest=manifest, file_data=data, file_size_bytes=len(data), expires_at=now_utc() + timedelta(hours=EXPORT_EXPIRY_HOURS),
    )
    db.add(export)
    await db.flush()
    return export


async def purge_expired_exports(db: AsyncSession) -> int:
    now = now_utc()
    rows = (await db.execute(select(DataExport).where(DataExport.state == "ready", DataExport.expires_at <= now))).scalars().all()
    for row in rows:
        row.state = "expired"
        row.file_data = None
    return len(rows)


async def purge_exports_for_user(db: AsyncSession, user_id: Any) -> int:
    rows = (await db.execute(select(DataExport).where(DataExport.requested_by_user_id == user_id))).scalars().all()
    for row in rows:
        row.state = "expired"
        row.file_data = None
    return len(rows)
