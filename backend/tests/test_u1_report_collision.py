"""U1 regression: two buyer campaigns (journeys) in one workspace must never share a report run."""
from httpx import AsyncClient

from tests.conftest import login, register_and_verify, unique_email


async def _campaign(client: AsyncClient, name: str) -> str:
    r = await client.post("/api/journeys", json={"name": name, "timezone": "Australia/Perth"})
    assert r.status_code == 201, r.text
    return r.json()["id"]


async def test_same_workspace_same_period_reports_do_not_collide(client: AsyncClient) -> None:
    email = unique_email("collision")
    await register_and_verify(client, email)
    await login(client, email)
    house = await _campaign(client, "Synthetic house campaign")
    land = await _campaign(client, "Synthetic land campaign")
    for report_type in ("daily", "weekly", "monthly"):
        a = await client.post(f"/api/journeys/{house}/reports/{report_type}/generate", json={"release_kind": "preview"})
        b = await client.post(f"/api/journeys/{land}/reports/{report_type}/generate", json={"release_kind": "preview"})
        assert a.status_code == 200, a.text
        assert b.status_code == 200, b.text
        assert b.json()["journey_id"] == land, f"{report_type}: land campaign received another campaign's run"
        assert a.json()["id"] != b.json()["id"], f"{report_type}: both campaigns share one report run"
