"""Cross-tenant isolation and negative deep-link tests. Build-failing by design."""

from httpx import ASGITransport, AsyncClient

from server import app
from tests.conftest import login, register_and_verify, unique_email

BASE = "https://property-find-1.preview.emergentagent.com"


async def _tenant(prefix: str) -> tuple[AsyncClient, str]:
    c = AsyncClient(transport=ASGITransport(app=app), base_url=BASE)
    email = unique_email(prefix)
    await register_and_verify(c, email)
    await login(c, email)
    journey = (await c.post("/api/journeys", json={"name": f"{prefix} journey"})).json()
    return c, str(journey["id"])


async def test_journeys_are_invisible_across_workspaces() -> None:
    a, a_journey = await _tenant("tenant-a")
    b, b_journey = await _tenant("tenant-b")
    try:
        a_list = (await a.get("/api/journeys")).json()
        assert [j["id"] for j in a_list] == [a_journey]

        assert (await a.get(f"/api/journeys/{b_journey}")).status_code == 404
        assert (await a.get(f"/api/journeys/{b_journey}/brief")).status_code == 404
        assert (await a.get(f"/api/journeys/{b_journey}/brief/versions")).status_code == 404
    finally:
        await a.aclose()
        await b.aclose()


async def test_cross_tenant_writes_and_publication_are_refused() -> None:
    a, _ = await _tenant("write-a")
    b, b_journey = await _tenant("write-b")
    try:
        brief = (await b.get(f"/api/journeys/{b_journey}/brief")).json()
        payload = brief["draft"]
        row_version = brief["journey"]["row_version"]

        blocked_save = await a.put(
            f"/api/journeys/{b_journey}/brief/draft",
            json={"payload": payload, "expected_row_version": row_version},
        )
        assert blocked_save.status_code == 404

        blocked_publish = await a.post(
            f"/api/journeys/{b_journey}/brief/publish",
            json={"reason": "attempted cross-tenant publish", "expected_row_version": row_version},
        )
        assert blocked_publish.status_code == 404

        blocked_patch = await a.patch(
            f"/api/journeys/{b_journey}", json={"name": "renamed", "expected_row_version": row_version}
        )
        assert blocked_patch.status_code == 404

        unchanged = (await b.get(f"/api/journeys/{b_journey}")).json()
        assert unchanged["name"] == "write-b journey"
    finally:
        await a.aclose()
        await b.aclose()


async def test_workspace_id_is_never_accepted_from_the_client() -> None:
    a, _ = await _tenant("scope-a")
    try:
        r = await a.post(
            "/api/journeys", json={"name": "spoofed", "workspace_id": "00000000-0000-0000-0000-000000000000"}
        )
        assert r.status_code == 422
    finally:
        await a.aclose()


async def test_anonymous_deep_links_are_rejected() -> None:
    a, a_journey = await _tenant("anon-a")
    anon = AsyncClient(transport=ASGITransport(app=app), base_url=BASE)
    try:
        assert (await anon.get(f"/api/journeys/{a_journey}")).status_code == 401
        assert (await anon.get(f"/api/journeys/{a_journey}/brief")).status_code == 401
        assert (await anon.get("/api/auth/sessions")).status_code == 401
    finally:
        await a.aclose()
        await anon.aclose()
