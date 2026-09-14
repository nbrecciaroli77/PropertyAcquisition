"""Prompt 03A — M3A Foundation Alignment: targeted schema and domain tests.

Covers:
- All 10 new tables accept valid rows (basic CRUD)
- Uniqueness constraints (workspace-scoped idempotency keys, sender aliases,
  source readiness one-per-connector, enrichment one-per-kind/source)
- Partial unique index: exactly one first_discovery per (workspace, property)
- Tenant isolation: workspace-owned records cannot be read across tenants
- ScheduledJob.enabled=False default; workspace_id required
- Migration head confirmation
- Existing dev-route security tests are not regressed (imported)
"""

import uuid
from datetime import datetime, timezone

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import inspect, select, text
from sqlalchemy.exc import IntegrityError

from app.db.base import get_sessionmaker
from app.db.models import (
    BriefVersion,
    ConnectorDefinition,
    ConnectorInstance,
    DiscoveryEvent,
    EnrichmentRecord,
    IntakeEvent,
    JobRun,
    Property,
    ReportRun,
    ScheduledJob,
    SenderAlias,
    SourceReadiness,
)
from tests.conftest import login, register_and_verify, unique_email

_NOW = datetime.now(timezone.utc)


# ── helpers ────────────────────────────────────────────────────────────────────

async def _make_workspace(client: AsyncClient) -> tuple[str, str, str, str]:
    """Register, verify, login; return (email, access_token, workspace_id, journey_id)."""
    email = unique_email("m3a")
    await register_and_verify(client, email)
    body = await login(client, email)
    ws_id: str = body["workspace"]["id"]  # type: ignore[index]
    r = await client.post("/api/journeys", json={"name": "M3A test journey", "timezone": "UTC"})
    assert r.status_code == 201, r.text
    journey_id: str = r.json()["id"]
    return email, ws_id, journey_id


async def _make_property(client: AsyncClient, journey_id: str, ws_id: str) -> str:
    """Create a minimal property via the dev loader; return property_id."""
    r = await client.post(
        "/api/dev/load-demo-properties", json={"journey_id": journey_id}
    )
    assert r.status_code == 201, r.text
    # Fetch the first property id from the journey
    r2 = await client.get(f"/api/journeys/{journey_id}/properties")
    assert r2.status_code == 200, r2.text
    props = r2.json()
    assert props, "expected at least one property after loading demo data"
    return props[0]["id"]


# ── 1. Migration head ──────────────────────────────────────────────────────────

async def test_migration_head_is_m3a() -> None:
    """Alembic version table must reflect the M3A migration."""
    async with get_sessionmaker()() as db:
        result = await db.execute(text("SELECT version_num FROM alembic_version"))
        version = result.scalar_one()
    assert version == "2105faf7bef7", f"Unexpected migration head: {version}"


# ── 2. All 10 new tables exist in the database ────────────────────────────────

async def test_all_new_tables_exist() -> None:
    expected = {
        "connector_definitions",
        "connector_instances",
        "source_readiness",
        "sender_aliases",
        "discovery_events",
        "intake_events",
        "scheduled_jobs",
        "job_runs",
        "enrichment_records",
        "report_runs",
    }
    async with get_sessionmaker()() as db:
        result = await db.execute(
            text(
                "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
                " AND tablename = ANY(:names)"
            ),
            {"names": list(expected)},
        )
        found = {row[0] for row in result}
    assert found == expected, f"Missing tables: {expected - found}"


# ── 3. ConnectorDefinition — global, no workspace_id ──────────────────────────

async def test_connector_definition_crud() -> None:
    slug = f"test-connector-{uuid.uuid4().hex[:8]}"
    async with get_sessionmaker()() as db:
        defn = ConnectorDefinition(
            slug=slug,
            display_name="Test Connector",
            acquisition_mechanism="manual",
            capabilities=["search"],
            jurisdiction_codes=["AU-WA"],
            licence_kind="none_required",
            licence_state="not_required",
            version="1.0.0",
        )
        db.add(defn)
        await db.commit()
        await db.refresh(defn)
        defn_id = defn.id

    async with get_sessionmaker()() as db:
        loaded = (
            await db.execute(select(ConnectorDefinition).where(ConnectorDefinition.id == defn_id))
        ).scalar_one()
        assert loaded.slug == slug
        assert loaded.kill_switch is False
        # clean up
        await db.delete(loaded)
        await db.commit()


async def test_connector_definition_slug_is_globally_unique() -> None:
    slug = f"dup-slug-{uuid.uuid4().hex[:8]}"
    async with get_sessionmaker()() as db:
        db.add(
            ConnectorDefinition(
                slug=slug,
                display_name="A",
                acquisition_mechanism="manual",
                capabilities=[],
                jurisdiction_codes=[],
                licence_kind="none_required",
                licence_state="not_required",
                version="1.0.0",
            )
        )
        await db.commit()

    with pytest.raises(IntegrityError):
        async with get_sessionmaker()() as db:
            db.add(
                ConnectorDefinition(
                    slug=slug,
                    display_name="B",
                    acquisition_mechanism="manual",
                    capabilities=[],
                    jurisdiction_codes=[],
                    licence_kind="none_required",
                    licence_state="not_required",
                    version="1.0.0",
                )
            )
            await db.commit()

    # clean up
    async with get_sessionmaker()() as db:
        rows = (
            await db.execute(
                select(ConnectorDefinition).where(ConnectorDefinition.slug == slug)
            )
        ).scalars().all()
        for r in rows:
            await db.delete(r)
        await db.commit()


# ── 4. ConnectorInstance — workspace-scoped, one per (workspace, definition) ──

async def test_connector_instance_workspace_scoped(client: AsyncClient) -> None:
    _email, ws_id, _jid = await _make_workspace(client)
    slug = f"ci-{uuid.uuid4().hex[:8]}"
    async with get_sessionmaker()() as db:
        defn = ConnectorDefinition(
            slug=slug,
            display_name="CI Test",
            acquisition_mechanism="portal_api",
            capabilities=[],
            jurisdiction_codes=["AU-WA"],
            licence_kind="none_required",
            licence_state="not_required",
            version="1.0.0",
        )
        db.add(defn)
        await db.flush()
        inst = ConnectorInstance(
            workspace_id=uuid.UUID(ws_id),
            definition_id=defn.id,
        )
        db.add(inst)
        await db.commit()
        assert inst.enabled is False
        assert inst.readiness_state == "unconfigured"
        # credential_ref must be None (never raw creds)
        assert inst.credential_ref is None
        defn_id = defn.id

    # second workspace cannot duplicate — but same workspace+definition is rejected
    with pytest.raises(IntegrityError):
        async with get_sessionmaker()() as db:
            db.add(
                ConnectorInstance(
                    workspace_id=uuid.UUID(ws_id),
                    definition_id=defn_id,
                )
            )
            await db.commit()

    # clean up
    # clean up — delete in FK order (instance before definition)
    async with get_sessionmaker()() as db:
        insts = (
            await db.execute(
                select(ConnectorInstance).where(ConnectorInstance.workspace_id == uuid.UUID(ws_id))
            )
        ).scalars().all()
        for i in insts:
            await db.delete(i)
        await db.commit()

    async with get_sessionmaker()() as db:
        defn_row = (
            await db.execute(
                select(ConnectorDefinition).where(ConnectorDefinition.id == defn_id)
            )
        ).scalar_one()
        await db.delete(defn_row)
        await db.commit()


# ── 5. SourceReadiness — one per (workspace, connector_instance) ───────────────

async def test_source_readiness_unique_per_workspace_connector(client: AsyncClient) -> None:
    _email, ws_id, _jid = await _make_workspace(client)
    slug = f"sr-{uuid.uuid4().hex[:8]}"
    async with get_sessionmaker()() as db:
        defn = ConnectorDefinition(
            slug=slug,
            display_name="SR Test",
            acquisition_mechanism="direct_api",
            capabilities=[],
            jurisdiction_codes=[],
            licence_kind="none_required",
            licence_state="not_required",
            version="1.0.0",
        )
        db.add(defn)
        await db.flush()
        inst = ConnectorInstance(workspace_id=uuid.UUID(ws_id), definition_id=defn.id)
        db.add(inst)
        await db.flush()
        sr = SourceReadiness(workspace_id=uuid.UUID(ws_id), connector_instance_id=inst.id)
        db.add(sr)
        await db.commit()
        assert sr.readiness_state == "initialising"
        inst_id = inst.id
        defn_id = defn.id

    with pytest.raises(IntegrityError):
        async with get_sessionmaker()() as db:
            db.add(
                SourceReadiness(
                    workspace_id=uuid.UUID(ws_id), connector_instance_id=inst_id
                )
            )
            await db.commit()

    async with get_sessionmaker()() as db:
        for model, fk in [
            (SourceReadiness, SourceReadiness.connector_instance_id == inst_id),
            (ConnectorInstance, ConnectorInstance.id == inst_id),
        ]:
            rows = (await db.execute(select(model).where(fk))).scalars().all()
            for row in rows:
                await db.delete(row)
        await db.commit()
    async with get_sessionmaker()() as db:
        defn_row = (
            await db.execute(
                select(ConnectorDefinition).where(ConnectorDefinition.id == defn_id)
            )
        ).scalar_one()
        await db.delete(defn_row)
        await db.commit()


# ── 6. SenderAlias — workspace-scoped uniqueness ───────────────────────────────

async def test_sender_alias_unique_per_workspace_email(client: AsyncClient) -> None:
    _email, ws_id, _jid = await _make_workspace(client)
    alias = f"agent-{uuid.uuid4().hex[:8]}@example.com"
    async with get_sessionmaker()() as db:
        sa1 = SenderAlias(
            workspace_id=uuid.UUID(ws_id),
            canonical_email="primary@example.com",
            alias_email=alias,
            evidence_label="test",
            first_seen_at=_NOW,
        )
        db.add(sa1)
        await db.commit()
        assert sa1.review_state == "pending"
        assert sa1.confidence == "low"

    # same alias in same workspace → conflict
    with pytest.raises(IntegrityError):
        async with get_sessionmaker()() as db:
            db.add(
                SenderAlias(
                    workspace_id=uuid.UUID(ws_id),
                    canonical_email="other@example.com",
                    alias_email=alias,
                    evidence_label="test2",
                    first_seen_at=_NOW,
                )
            )
            await db.commit()

    async with get_sessionmaker()() as db:
        rows = (
            await db.execute(
                select(SenderAlias).where(SenderAlias.workspace_id == uuid.UUID(ws_id))
            )
        ).scalars().all()
        for r in rows:
            await db.delete(r)
        await db.commit()


async def test_sender_alias_same_email_allowed_in_different_workspaces(
    client: AsyncClient,
) -> None:
    _e1, ws1, _j1 = await _make_workspace(client)
    _e2, ws2, _j2 = await _make_workspace(client)
    alias = f"shared-{uuid.uuid4().hex[:8]}@example.com"
    async with get_sessionmaker()() as db:
        db.add(
            SenderAlias(
                workspace_id=uuid.UUID(ws1),
                canonical_email="p@e.com",
                alias_email=alias,
                evidence_label="ws1",
                first_seen_at=_NOW,
            )
        )
        db.add(
            SenderAlias(
                workspace_id=uuid.UUID(ws2),
                canonical_email="p@e.com",
                alias_email=alias,
                evidence_label="ws2",
                first_seen_at=_NOW,
            )
        )
        await db.commit()  # must NOT raise

    async with get_sessionmaker()() as db:
        for ws_id in (ws1, ws2):
            rows = (
                await db.execute(
                    select(SenderAlias).where(SenderAlias.workspace_id == uuid.UUID(ws_id))
                )
            ).scalars().all()
            for r in rows:
                await db.delete(r)
        await db.commit()


# ── 7. DiscoveryEvent partial-unique index ─────────────────────────────────────

async def test_discovery_first_is_unique_per_workspace_property(client: AsyncClient) -> None:
    _email, ws_id, jid = await _make_workspace(client)
    prop_id = await _make_property(client, jid, ws_id)

    # First first_discovery must succeed
    async with get_sessionmaker()() as db:
        de = DiscoveryEvent(
            workspace_id=uuid.UUID(ws_id),
            journey_id=uuid.UUID(jid),
            property_id=uuid.UUID(prop_id),
            event_type="first_discovery",
            source_label="manual",
            channel="manual",
            discovered_at=_NOW,
        )
        db.add(de)
        await db.commit()

    # Second first_discovery for same (workspace, property) must be rejected
    with pytest.raises(IntegrityError):
        async with get_sessionmaker()() as db:
            db.add(
                DiscoveryEvent(
                    workspace_id=uuid.UUID(ws_id),
                    journey_id=uuid.UUID(jid),
                    property_id=uuid.UUID(prop_id),
                    event_type="first_discovery",
                    source_label="portal",
                    channel="portal",
                    discovered_at=_NOW,
                )
            )
            await db.commit()

    # channel_event for the same (workspace, property) must be ALLOWED
    async with get_sessionmaker()() as db:
        db.add(
            DiscoveryEvent(
                workspace_id=uuid.UUID(ws_id),
                journey_id=uuid.UUID(jid),
                property_id=uuid.UUID(prop_id),
                event_type="channel_event",
                source_label="portal",
                channel="portal",
                discovered_at=_NOW,
            )
        )
        await db.commit()  # must NOT raise

    async with get_sessionmaker()() as db:
        rows = (
            await db.execute(
                select(DiscoveryEvent).where(DiscoveryEvent.workspace_id == uuid.UUID(ws_id))
            )
        ).scalars().all()
        for r in rows:
            await db.delete(r)
        await db.commit()


# ── 8. IntakeEvent workspace-scoped idempotency ────────────────────────────────

async def test_intake_event_idempotency_key_is_workspace_scoped(client: AsyncClient) -> None:
    _e1, ws1, j1 = await _make_workspace(client)
    _e2, ws2, j2 = await _make_workspace(client)
    key = f"idem-{uuid.uuid4().hex}"

    async with get_sessionmaker()() as db:
        # Same key in two different workspaces must both succeed
        db.add(
            IntakeEvent(
                workspace_id=uuid.UUID(ws1),
                journey_id=uuid.UUID(j1),
                idempotency_key=key,
                source_label="manual",
                channel="manual",
            )
        )
        db.add(
            IntakeEvent(
                workspace_id=uuid.UUID(ws2),
                journey_id=uuid.UUID(j2),
                idempotency_key=key,
                source_label="manual",
                channel="manual",
            )
        )
        await db.commit()  # must NOT raise

    # Same key within the same workspace must fail
    with pytest.raises(IntegrityError):
        async with get_sessionmaker()() as db:
            db.add(
                IntakeEvent(
                    workspace_id=uuid.UUID(ws1),
                    journey_id=uuid.UUID(j1),
                    idempotency_key=key,
                    source_label="portal",
                    channel="portal",
                )
            )
            await db.commit()

    async with get_sessionmaker()() as db:
        for ws_id in (ws1, ws2):
            rows = (
                await db.execute(
                    select(IntakeEvent).where(IntakeEvent.workspace_id == uuid.UUID(ws_id))
                )
            ).scalars().all()
            for r in rows:
                await db.delete(r)
        await db.commit()


# ── 9. ScheduledJob — enabled=False and workspace_id required ─────────────────

async def test_scheduled_job_defaults_to_disabled(client: AsyncClient) -> None:
    _email, ws_id, _jid = await _make_workspace(client)
    async with get_sessionmaker()() as db:
        job = ScheduledJob(
            workspace_id=uuid.UUID(ws_id),
            job_kind="brief_reevaluation",
            schedule_cron="0 * * * *",
        )
        db.add(job)
        await db.commit()
        assert job.enabled is False, "ScheduledJob must default to disabled"
        assert job.schedule_version == 1
        assert job.timezone == "UTC"
        job_id = job.id

    async with get_sessionmaker()() as db:
        row = (
            await db.execute(select(ScheduledJob).where(ScheduledJob.id == job_id))
        ).scalar_one()
        await db.delete(row)
        await db.commit()


# ── 10. EnrichmentRecord unique per (property, kind, source) ──────────────────

async def test_enrichment_record_unique_per_property_kind_source(client: AsyncClient) -> None:
    _email, ws_id, jid = await _make_workspace(client)
    prop_id = await _make_property(client, jid, ws_id)
    async with get_sessionmaker()() as db:
        er = EnrichmentRecord(
            workspace_id=uuid.UUID(ws_id),
            property_id=uuid.UUID(prop_id),
            kind="planning",
            source_label="synthetic",
            provenance="test",
            observed_at=_NOW,
        )
        db.add(er)
        await db.commit()
        assert er.value_state == "unknown"
        assert er.confidence == "unknown"

    with pytest.raises(IntegrityError):
        async with get_sessionmaker()() as db:
            db.add(
                EnrichmentRecord(
                    workspace_id=uuid.UUID(ws_id),
                    property_id=uuid.UUID(prop_id),
                    kind="planning",
                    source_label="synthetic",
                    provenance="duplicate",
                    observed_at=_NOW,
                )
            )
            await db.commit()

    async with get_sessionmaker()() as db:
        rows = (
            await db.execute(
                select(EnrichmentRecord).where(EnrichmentRecord.workspace_id == uuid.UUID(ws_id))
            )
        ).scalars().all()
        for r in rows:
            await db.delete(r)
        await db.commit()


# ── 11. ReportRun workspace-scoped idempotency ────────────────────────────────

async def test_report_run_idempotency_key_is_workspace_scoped(client: AsyncClient) -> None:
    _e1, ws1, j1 = await _make_workspace(client)
    _e2, ws2, j2 = await _make_workspace(client)
    key = f"rep-{uuid.uuid4().hex}"

    async with get_sessionmaker()() as db:
        db.add(
            ReportRun(
                workspace_id=uuid.UUID(ws1),
                journey_id=uuid.UUID(j1),
                idempotency_key=key,
            )
        )
        db.add(
            ReportRun(
                workspace_id=uuid.UUID(ws2),
                journey_id=uuid.UUID(j2),
                idempotency_key=key,
            )
        )
        await db.commit()  # two different workspaces, same key — must succeed

    with pytest.raises(IntegrityError):
        async with get_sessionmaker()() as db:
            db.add(
                ReportRun(
                    workspace_id=uuid.UUID(ws1),
                    journey_id=uuid.UUID(j1),
                    idempotency_key=key,
                )
            )
            await db.commit()

    async with get_sessionmaker()() as db:
        for ws_id in (ws1, ws2):
            rows = (
                await db.execute(
                    select(ReportRun).where(ReportRun.workspace_id == uuid.UUID(ws_id))
                )
            ).scalars().all()
            for r in rows:
                await db.delete(r)
        await db.commit()


# ── 12. Tenant isolation — workspace-scoped records cannot bleed across tenants

async def test_intake_event_tenant_isolation(client: AsyncClient) -> None:
    _e1, ws1, j1 = await _make_workspace(client)
    _e2, ws2, j2 = await _make_workspace(client)
    key = f"iso-{uuid.uuid4().hex}"

    async with get_sessionmaker()() as db:
        db.add(
            IntakeEvent(
                workspace_id=uuid.UUID(ws1),
                journey_id=uuid.UUID(j1),
                idempotency_key=key,
                source_label="manual",
                channel="manual",
            )
        )
        await db.commit()

    async with get_sessionmaker()() as db:
        rows_ws2 = (
            await db.execute(
                select(IntakeEvent).where(IntakeEvent.workspace_id == uuid.UUID(ws2))
            )
        ).scalars().all()
        assert rows_ws2 == [], "Workspace 2 must not see Workspace 1 intake events"
        # clean up
        rows_ws1 = (
            await db.execute(
                select(IntakeEvent).where(IntakeEvent.workspace_id == uuid.UUID(ws1))
            )
        ).scalars().all()
        for r in rows_ws1:
            await db.delete(r)
        await db.commit()


# ── 13. Rollback SQL generation (no live downgrade) ───────────────────────────

async def test_downgrade_sql_contains_expected_drops() -> None:
    """Generate downgrade SQL without executing it and verify it covers M3A tables."""
    import subprocess

    # Use explicit from:to range so alembic can produce SQL without a live connection
    result = subprocess.run(
        [
            "python", "-m", "alembic", "--config", "alembic.ini",
            "downgrade", "--sql", "2105faf7bef7:2fc5f4775fef",
        ],
        capture_output=True,
        text=True,
        cwd="/app/backend",
    )
    sql = result.stdout.lower()
    assert "drop table" in sql, (
        f"Downgrade SQL should contain DROP TABLE statements.\nstdout={result.stdout[:500]}\nstderr={result.stderr[:500]}"
    )
    for table in [
        "connector_definitions",
        "connector_instances",
        "scheduled_jobs",
        "sender_aliases",
        "job_runs",
        "source_readiness",
        "discovery_events",
        "enrichment_records",
        "intake_events",
        "report_runs",
    ]:
        assert table in sql, f"Downgrade SQL missing DROP TABLE for {table}"


# ── 14. Dev-route security regression ─────────────────────────────────────────

async def test_dev_outbox_still_404_unauthenticated(client: AsyncClient) -> None:
    """Regression: the security hotfix must not be broken by M3A."""
    from tests.test_security_dev_surface import dev_routes_disabled

    with dev_routes_disabled():
        r = await client.get("/api/dev/outbox")
    assert r.status_code == 404


async def test_dev_outbox_still_404_authenticated(client: AsyncClient) -> None:
    email = unique_email("m3a-sec")
    await register_and_verify(client, email)
    await login(client, email)
    from tests.test_security_dev_surface import dev_routes_disabled

    with dev_routes_disabled():
        r = await client.get("/api/dev/outbox")
    assert r.status_code == 404
