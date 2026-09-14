"""Focused acceptance verification for Milestone 4.2.

These tests run only with a disposable database selected through
M4_2_VERIFY_ISOLATED_DB.  They cover CSV intake, duplicate review, source
tracking, tenancy boundaries, seeded synthetic fixtures, and existing security
regressions without changing production data.
"""
from __future__ import annotations

import csv
import io
import os
import uuid
from unittest.mock import patch

import pytest
import pytest_asyncio
from httpx import AsyncClient
from sqlalchemy import func, select

from app.db.base import get_sessionmaker
from app.db.models import DiscoveryEvent, IntakeEvent, Observation, Property, PropertyNote
from app.services.csv_intake import preview_csv


pytestmark = pytest.mark.asyncio


def _csv_bytes(rows: list[dict[str, str]]) -> bytes:
    columns = ["address_line", "suburb", "state", "postcode", "beds", "notes"]
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=columns)
    writer.writeheader()
    writer.writerows(rows)
    return output.getvalue().encode()


async def _login(client: AsyncClient, email: str) -> None:
    response = await client.post(
        "/api/auth/login",
        json={"email": email, "password": "Prototype2026pass"},
    )
    assert response.status_code == 200, response.text


async def _journey_id(client: AsyncClient) -> str:
    response = await client.get("/api/journeys")
    assert response.status_code == 200, response.text
    return response.json()[0]["id"]


async def _upload(client: AsyncClient, journey_id: str, rows: list[dict[str, str]]) -> dict:
    response = await client.post(
        f"/api/journeys/{journey_id}/intake/csv-import",
        files={"file": ("m4_2_acceptance.csv", _csv_bytes(rows), "text/csv")},
    )
    assert response.status_code == 200, response.text
    return response.json()


async def _proposal_for_number(client: AsyncClient, number: str) -> dict:
    response = await client.get("/api/workspaces/me/duplicates")
    assert response.status_code == 200, response.text
    return next(item for item in response.json()["items"] if item["evidence"].get("street_number") == number)


@pytest_asyncio.fixture(autouse=True)
async def _require_isolated_database() -> None:
    assert os.environ.get("M4_2_VERIFY_ISOLATED_DB") == "1", (
        "M4.2 verification must run against a disposable isolated database."
    )


@pytest_asyncio.fixture
async def owner(async_client: AsyncClient) -> tuple[AsyncClient, str]:
    await _login(async_client, "owner@propertyacquisition-demo.com")
    return async_client, await _journey_id(async_client)


async def test_csv_preview_and_import_revalidate_server_side(owner: tuple[AsyncClient, str]) -> None:
    client, journey_id = owner
    valid = _csv_bytes([
        {"address_line": "901 Preview Road", "suburb": "Subiaco", "state": "WA", "postcode": "6008", "beds": "3", "notes": ""}
    ])
    preview = await client.post(
        f"/api/journeys/{journey_id}/intake/csv-preview",
        files={"file": ("valid.csv", valid, "text/csv")},
    )
    assert preview.status_code == 200, preview.text
    assert preview.json()["valid_rows"] == 1

    # Import is deliberately attempted without a preview and with invalid bytes.
    # The endpoint must independently parse and reject the bad row.
    invalid = _csv_bytes([
        {"address_line": "", "suburb": "Subiaco", "state": "WA", "postcode": "6008", "beds": "3", "notes": ""}
    ])
    imported = await client.post(
        f"/api/journeys/{journey_id}/intake/csv-import",
        files={"file": ("invalid.csv", invalid, "text/csv")},
    )
    assert imported.status_code == 200, imported.text
    body = imported.json()
    assert body["failed"] == 1 and body["created"] == 0
    assert body["row_results"][0]["outcome"] == "failed"


async def test_csv_full_file_and_row_level_replay_are_idempotent(owner: tuple[AsyncClient, str]) -> None:
    client, journey_id = owner
    first_rows = [
        {"address_line": "902 Replay Road", "suburb": "Subiaco", "state": "WA", "postcode": "6008", "beds": "3", "notes": ""},
        {"address_line": "903 Replay Road", "suburb": "Subiaco", "state": "WA", "postcode": "6008", "beds": "4", "notes": ""},
    ]
    first = await _upload(client, journey_id, first_rows)
    replay = await _upload(client, journey_id, first_rows)
    assert first["created"] == 2
    assert replay["batch_id"] == first["batch_id"]
    assert replay["row_results"] == []

    # A changed file is a new batch, but its previously imported row must not create a second property.
    changed = await _upload(client, journey_id, first_rows[:1] + [
        {"address_line": "904 Replay Road", "suburb": "Subiaco", "state": "WA", "postcode": "6008", "beds": "2", "notes": ""}
    ])
    assert changed["total_rows"] == 2
    async with get_sessionmaker()() as db:
        properties = (
            await db.execute(
                select(func.count()).select_from(Property).where(
                    Property.journey_id == journey_id,
                    Property.address_line.in_(["902 Replay Road", "903 Replay Road", "904 Replay Road"]),
                )
            )
        ).scalar_one()
        events = (
            await db.execute(
                select(func.count()).select_from(IntakeEvent).where(
                    IntakeEvent.journey_id == journey_id,
                    IntakeEvent.intake_mechanism == "csv_import",
                )
            )
        ).scalar_one()
    assert properties == 3
    assert events == 3


async def test_formula_cells_stay_inert_and_csv_urls_never_fetch(owner: tuple[AsyncClient, str]) -> None:
    client, journey_id = owner
    formula_rows = [
        {
            "address_line": "905 Inert Road",
            "suburb": "Subiaco",
            "state": "WA",
            "postcode": "6008",
            "beds": "3",
            "notes": "=2+2",
        }
    ]
    raw = _csv_bytes(formula_rows)
    with patch("socket.create_connection", side_effect=AssertionError("outbound request attempted")):
        preview = preview_csv(raw, uuid.uuid4(), "formula.csv")
    assert preview.preview_rows[0].formula_flags == ["notes"]
    assert preview.preview_rows[0].notes == "=2+2"

    imported = await _upload(client, journey_id, formula_rows)
    assert imported["row_results"][0]["formula_flags"] == ["notes"]
    property_id = imported["row_results"][0]["property_id"]
    async with get_sessionmaker()() as db:
        note = (
            await db.execute(
                select(PropertyNote).where(PropertyNote.property_id == property_id)
            )
        ).scalar_one_or_none()
        observation_note = (
            await db.execute(
                select(Observation.note).where(Observation.property_id == property_id)
            )
        ).scalar_one()
    assert note is None
    assert observation_note == "=2+2"


async def test_duplicate_reject_confirm_undo_and_split_preserve_snapshot_relationships(
    owner: tuple[AsyncClient, str],
) -> None:
    client, journey_id = owner
    await _upload(client, journey_id, [
        {"address_line": "911 Reject One Street", "suburb": "Fremantle", "state": "WA", "postcode": "6160", "beds": "3", "notes": ""},
        {"address_line": "911 Reject Two Street", "suburb": "Fremantle", "state": "WA", "postcode": "6160", "beds": "3", "notes": ""},
        {"address_line": "912 Merge One Street", "suburb": "Fremantle", "state": "WA", "postcode": "6160", "beds": "3", "notes": ""},
        {"address_line": "912 Merge Two Street", "suburb": "Fremantle", "state": "WA", "postcode": "6160", "beds": "3", "notes": ""},
        {"address_line": "913 Split One Street", "suburb": "Fremantle", "state": "WA", "postcode": "6160", "beds": "3", "notes": ""},
        {"address_line": "913 Split Two Street", "suburb": "Fremantle", "state": "WA", "postcode": "6160", "beds": "3", "notes": ""},
    ])
    scanned = await client.post("/api/workspaces/me/duplicates/scan")
    assert scanned.status_code == 200, scanned.text

    rejected = await _proposal_for_number(client, "911")
    response = await client.post(
        f"/api/workspaces/me/duplicates/{rejected['id']}/reject",
        json={"reason": "Different homes", "row_version": rejected["row_version"]},
    )
    assert response.status_code == 200 and response.json()["state"] == "rejected"

    merge = await _proposal_for_number(client, "912")
    survivor, duplicate = merge["property_a"]["id"], merge["property_b"]["id"]
    pre_note = await client.post(
        f"/api/journeys/{journey_id}/properties/{duplicate}/notes",
        json={"body": "Move only this original relationship."},
    )
    assert pre_note.status_code == 201, pre_note.text
    confirmed = await client.post(
        f"/api/workspaces/me/duplicates/{merge['id']}/confirm",
        json={"primary_property_id": survivor, "reason": "Confirmed review", "row_version": merge["row_version"]},
    )
    assert confirmed.status_code == 200, confirmed.text
    confirmed_body = confirmed.json()
    assert confirmed_body["state"] == "confirmed"

    post_note = await client.post(
        f"/api/journeys/{journey_id}/properties/{survivor}/notes",
        json={"body": "Post-merge activity must remain with survivor."},
    )
    assert post_note.status_code == 201, post_note.text

    undone = await client.post(
        f"/api/workspaces/me/duplicates/{merge['id']}/undo",
        json={"reason": "Restore reviewed pair", "row_version": confirmed_body["row_version"]},
    )
    assert undone.status_code == 200 and undone.json()["state"] == "undone"
    async with get_sessionmaker()() as db:
        notes = (
            await db.execute(
                select(PropertyNote.body, PropertyNote.property_id).where(
                    PropertyNote.body.in_([
                        "Move only this original relationship.",
                        "Post-merge activity must remain with survivor.",
                    ])
                )
            )
        ).all()
        first_discoveries = (
            await db.execute(
                select(DiscoveryEvent.property_id, func.count())
                .where(
                    DiscoveryEvent.property_id.in_([survivor, duplicate]),
                    DiscoveryEvent.event_type == "first_discovery",
                )
                .group_by(DiscoveryEvent.property_id)
            )
        ).all()
    assert dict(notes)["Move only this original relationship."] == uuid.UUID(duplicate)
    assert dict(notes)["Post-merge activity must remain with survivor."] == uuid.UUID(survivor)
    assert dict(first_discoveries) == {uuid.UUID(survivor): 1, uuid.UUID(duplicate): 1}

    split = await _proposal_for_number(client, "913")
    confirmed_split = await client.post(
        f"/api/workspaces/me/duplicates/{split['id']}/confirm",
        json={"primary_property_id": split["property_a"]["id"], "reason": None, "row_version": split["row_version"]},
    )
    assert confirmed_split.status_code == 200, confirmed_split.text
    split_response = await client.post(
        f"/api/workspaces/me/duplicates/{split['id']}/split",
        json={"reason": "Separate again", "row_version": confirmed_split.json()["row_version"]},
    )
    assert split_response.status_code == 200 and split_response.json()["state"] == "undone"


async def test_duplicate_cycle_unit_suffix_and_concurrency_protection(owner: tuple[AsyncClient, str]) -> None:
    client, journey_id = owner
    await _upload(client, journey_id, [
        {"address_line": "921 Cycle One Street", "suburb": "Nedlands", "state": "WA", "postcode": "6009", "beds": "3", "notes": ""},
        {"address_line": "921 Cycle Two Street", "suburb": "Nedlands", "state": "WA", "postcode": "6009", "beds": "3", "notes": ""},
        {"address_line": "921 Cycle Three Street", "suburb": "Nedlands", "state": "WA", "postcode": "6009", "beds": "3", "notes": ""},
        {"address_line": "81A Verification Street", "suburb": "Nedlands", "state": "WA", "postcode": "6009", "beds": "3", "notes": ""},
        {"address_line": "81C Verification Street", "suburb": "Nedlands", "state": "WA", "postcode": "6009", "beds": "3", "notes": ""},
    ])
    assert (await client.post("/api/workspaces/me/duplicates/scan")).status_code == 200
    proposals = (await client.get("/api/workspaces/me/duplicates")).json()["items"]
    cycle = [p for p in proposals if p["evidence"].get("street_number") == "921"]
    assert len(cycle) == 3
    first = cycle[0]
    merged = await client.post(
        f"/api/workspaces/me/duplicates/{first['id']}/confirm",
        json={"primary_property_id": first["property_a"]["id"], "reason": None, "row_version": first["row_version"]},
    )
    assert merged.status_code == 200, merged.text
    blocked = next(p for p in cycle[1:] if first["property_b"]["id"] in {p["property_a"]["id"], p["property_b"]["id"]})
    cycle_attempt = await client.post(
        f"/api/workspaces/me/duplicates/{blocked['id']}/confirm",
        json={"primary_property_id": first["property_b"]["id"], "reason": None, "row_version": blocked["row_version"]},
    )
    assert cycle_attempt.status_code == 409

    suffix = next(p for p in proposals if p["evidence"].get("street_number") == "81")
    assert suffix["unit_suffix_warning"] is True
    assert suffix["property_a"]["id"] != suffix["property_b"]["id"]

    stale = await client.post(
        f"/api/workspaces/me/duplicates/{suffix['id']}/reject",
        json={"reason": "keep separate", "row_version": suffix["row_version"] + 1},
    )
    assert stale.status_code == 409


async def test_aliases_are_demo_only_and_cross_tenant_reads_are_404(async_client: AsyncClient) -> None:
    await _login(async_client, "owner@propertyacquisition-demo.com")
    owner_aliases = await async_client.get("/api/workspaces/me/aliases")
    assert owner_aliases.status_code == 200
    owner_items = owner_aliases.json()["items"]
    assert len(owner_items) == 4
    alias_id = owner_items[0]["id"]

    await _login(async_client, "other@propertyacquisition-demo.com")
    other_aliases = await async_client.get("/api/workspaces/me/aliases")
    assert other_aliases.status_code == 200 and other_aliases.json()["items"] == []
    denied = await async_client.patch(
        f"/api/workspaces/me/aliases/{alias_id}", json={"action": "confirm"}
    )
    assert denied.status_code == 404


async def test_duplicate_and_batch_reads_are_404_across_tenants(async_client: AsyncClient) -> None:
    await _login(async_client, "owner@propertyacquisition-demo.com")
    owner_journey = await _journey_id(async_client)
    batch = await _upload(async_client, owner_journey, [
        {"address_line": "931 Tenant One Street", "suburb": "Subiaco", "state": "WA", "postcode": "6008", "beds": "3", "notes": ""},
        {"address_line": "931 Tenant Two Street", "suburb": "Subiaco", "state": "WA", "postcode": "6008", "beds": "3", "notes": ""},
    ])
    assert (await async_client.post("/api/workspaces/me/duplicates/scan")).status_code == 200
    proposal = await _proposal_for_number(async_client, "931")

    await _login(async_client, "other@propertyacquisition-demo.com")
    other_journey = await _journey_id(async_client)
    proposal_denied = await async_client.get(f"/api/workspaces/me/duplicates/{proposal['id']}")
    batch_denied = await async_client.get(
        f"/api/journeys/{other_journey}/intake/batches/{batch['batch_id']}"
    )
    assert proposal_denied.status_code == 404
    assert batch_denied.status_code == 404


async def test_existing_auth_and_dev_route_security_regression(async_client: AsyncClient) -> None:
    from tests.test_security_dev_surface import dev_routes_disabled

    with dev_routes_disabled():
        anonymous = await async_client.get("/api/dev/outbox")
    assert anonymous.status_code == 404
    await _login(async_client, "owner@propertyacquisition-demo.com")
    with dev_routes_disabled():
        authenticated = await async_client.post(
            "/api/dev/load-demo-properties", json={"journey_id": await _journey_id(async_client)}
        )
    assert authenticated.status_code == 404