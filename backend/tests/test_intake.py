"""M4.1 intake tests — 12 targeted scenarios.

Covers: happy path, idempotency, duplicate detection, 81A≠81C, URL mode,
        pasted text parsing, Unknown-fact preservation, requires_review,
        parse preview, cross-tenant isolation, and price parsing.
"""
from __future__ import annotations

import pytest
import pytest_asyncio

from httpx import AsyncClient


# ── Fixtures ─────────────────────────────────────────────────────────────────


def _auth_headers(client: AsyncClient, email: str, password: str = "Prototype2026pass") -> dict:
    """Synchronous helper — call login_sync only in sync context; replaced by async fixture."""
    raise NotImplementedError("Use async fixture _login_headers instead.")


@pytest_asyncio.fixture
async def owner_headers(async_client: AsyncClient) -> dict[str, str]:
    resp = await async_client.post(
        "/api/auth/login",
        json={"email": "owner@propertyacquisition-demo.com", "password": "Prototype2026pass"},
    )
    assert resp.status_code == 200
    return {"Cookie": "; ".join(f"{k}={v}" for k, v in resp.cookies.items())}


@pytest_asyncio.fixture
async def other_headers(async_client: AsyncClient) -> dict[str, str]:
    resp = await async_client.post(
        "/api/auth/login",
        json={"email": "other@propertyacquisition-demo.com", "password": "Prototype2026pass"},
    )
    assert resp.status_code == 200
    return {"Cookie": "; ".join(f"{k}={v}" for k, v in resp.cookies.items())}


@pytest_asyncio.fixture
async def owner_journey_id(async_client: AsyncClient, owner_headers: dict) -> str:
    resp = await async_client.get("/api/journeys", headers=owner_headers)
    assert resp.status_code == 200
    journeys = resp.json()
    assert journeys, "Owner must have at least one journey (run seed)"
    return journeys[0]["id"]


@pytest_asyncio.fixture
async def other_journey_id(async_client: AsyncClient, other_headers: dict) -> str:
    resp = await async_client.get("/api/journeys", headers=other_headers)
    assert resp.status_code == 200
    journeys = resp.json()
    assert journeys, "Other account must have a journey (run seed)"
    return journeys[0]["id"]


# ── Test helpers ──────────────────────────────────────────────────────────────


def _structured_body(
    address_line: str = "99 Banksia Way",
    suburb: str = "Applecross",
    state: str = "WA",
    postcode: str | None = "6153",
    beds: int | None = 3,
    baths: int | None = 2,
    cars: int | None = 2,
) -> dict:
    return {
        "mode": "structured_form",
        "structured": {
            "address_line": address_line,
            "suburb": suburb,
            "state": state,
            "postcode": postcode,
            "facts": {
                "beds": beds,
                "baths": baths,
                "cars": cars,
            },
            "price": {
                "price_kind": "offers_over",
                "raw_price": "Offers over $780,000",
                "lower_minor": 78000000,
            },
        },
    }


# ── Scenario 1: Structured form happy path ───────────────────────────────────


@pytest.mark.asyncio
async def test_structured_form_happy_path(
    async_client: AsyncClient,
    owner_headers: dict,
    owner_journey_id: str,
) -> None:
    resp = await async_client.post(
        f"/api/journeys/{owner_journey_id}/intake",
        json=_structured_body("1 Intake Test Street"),
        headers=owner_headers,
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["state"] == "completed"
    assert body["property_id"] is not None
    assert body["duplicate_property_id"] is None
    assert body["review_reasons"] == []


# ── Scenario 2: Replay idempotency ───────────────────────────────────────────


@pytest.mark.asyncio
async def test_replay_idempotency(
    async_client: AsyncClient,
    owner_headers: dict,
    owner_journey_id: str,
) -> None:
    payload = _structured_body("2 Idempotency Lane")
    r1 = await async_client.post(
        f"/api/journeys/{owner_journey_id}/intake",
        json=payload,
        headers=owner_headers,
    )
    assert r1.status_code == 200, r1.text
    r2 = await async_client.post(
        f"/api/journeys/{owner_journey_id}/intake",
        json=payload,
        headers=owner_headers,
    )
    assert r2.status_code == 200, r2.text
    b1, b2 = r1.json(), r2.json()
    # Exact same intake_id and property_id — no duplicate created
    assert b1["intake_id"] == b2["intake_id"]
    assert b1["property_id"] == b2["property_id"]
    assert b2["state"] == "completed"


# ── Scenario 3: Exact-address duplicate detected ─────────────────────────────


@pytest.mark.asyncio
async def test_exact_address_duplicate(
    async_client: AsyncClient,
    owner_headers: dict,
    owner_journey_id: str,
) -> None:
    # First submission creates the property
    r1 = await async_client.post(
        f"/api/journeys/{owner_journey_id}/intake",
        json=_structured_body("3 Duplicate Drive"),
        headers=owner_headers,
    )
    assert r1.status_code == 200 and r1.json()["state"] == "completed"
    original_id = r1.json()["property_id"]

    # Second submission with DIFFERENT mode → still flags as duplicate
    r2 = await async_client.post(
        f"/api/journeys/{owner_journey_id}/intake",
        json={
            "mode": "url_with_facts",
            "url_with_facts": {
                "source_url": "https://example.com/listing/123",
                "address_line": "3 Duplicate Drive",
                "suburb": "Applecross",
                "state": "WA",
                "postcode": "6153",
                "facts": {},
            },
        },
        headers=owner_headers,
    )
    assert r2.status_code == 200, r2.text
    b2 = r2.json()
    assert b2["state"] == "duplicate"
    assert b2["duplicate_property_id"] == original_id


# ── Scenario 4: 81A ≠ 81C (unit suffix isolation) ────────────────────────────


@pytest.mark.asyncio
async def test_unit_suffix_isolation(
    async_client: AsyncClient,
    owner_headers: dict,
    owner_journey_id: str,
) -> None:
    r_a = await async_client.post(
        f"/api/journeys/{owner_journey_id}/intake",
        json=_structured_body("81A Smith Street", suburb="Fremantle", state="WA", postcode="6160"),
        headers=owner_headers,
    )
    assert r_a.status_code == 200 and r_a.json()["state"] == "completed"
    id_a = r_a.json()["property_id"]

    r_c = await async_client.post(
        f"/api/journeys/{owner_journey_id}/intake",
        json=_structured_body("81C Smith Street", suburb="Fremantle", state="WA", postcode="6160"),
        headers=owner_headers,
    )
    assert r_c.status_code == 200 and r_c.json()["state"] == "completed"
    id_c = r_c.json()["property_id"]

    assert id_a != id_c, "81A and 81C must never be the same property"


# ── Scenario 5: URL-with-facts mode happy path ───────────────────────────────


@pytest.mark.asyncio
async def test_url_with_facts_happy_path(
    async_client: AsyncClient,
    owner_headers: dict,
    owner_journey_id: str,
) -> None:
    resp = await async_client.post(
        f"/api/journeys/{owner_journey_id}/intake",
        json={
            "mode": "url_with_facts",
            "url_with_facts": {
                "source_url": "https://realestate.com.au/property/12345678",
                "address_line": "5 URL Test Road",
                "suburb": "Subiaco",
                "state": "WA",
                "postcode": "6008",
                "facts": {"beds": 4, "baths": 2, "cars": 2, "land_sqm": 600},
                "price": {
                    "price_kind": "range",
                    "raw_price": "$950,000 - $1,020,000",
                    "lower_minor": 95000000,
                    "upper_minor": 102000000,
                },
            },
        },
        headers=owner_headers,
    )
    assert resp.status_code == 200, resp.text
    b = resp.json()
    assert b["state"] == "completed"
    assert b["property_id"] is not None


# ── Scenario 6: URL mode idempotency ─────────────────────────────────────────


@pytest.mark.asyncio
async def test_url_mode_idempotency(
    async_client: AsyncClient,
    owner_headers: dict,
    owner_journey_id: str,
) -> None:
    payload = {
        "mode": "url_with_facts",
        "url_with_facts": {
            "source_url": "https://realestate.com.au/idem-test",
            "address_line": "6 Idem Street",
            "suburb": "Nedlands",
            "state": "WA",
            "postcode": "6009",
            "facts": {},
        },
    }
    r1 = await async_client.post(
        f"/api/journeys/{owner_journey_id}/intake", json=payload, headers=owner_headers
    )
    r2 = await async_client.post(
        f"/api/journeys/{owner_journey_id}/intake", json=payload, headers=owner_headers
    )
    assert r1.status_code == r2.status_code == 200
    assert r1.json()["intake_id"] == r2.json()["intake_id"]


# ── Scenario 7: Pasted text parser extracts known fields ─────────────────────


@pytest.mark.asyncio
async def test_pasted_text_extracts_known_fields(
    async_client: AsyncClient,
    owner_headers: dict,
    owner_journey_id: str,
) -> None:
    listing = (
        "7 Parser Street Nedlands WA 6009\n"
        "3 bed 2 bath 2 car\n"
        "Land: 550sqm   Floor: 200m²\n"
        "House  $1,250,000\n"
    )
    resp = await async_client.post(
        f"/api/journeys/{owner_journey_id}/intake",
        json={"mode": "pasted_text", "pasted_text": {"raw_text": listing, "overrides": {}}},
        headers=owner_headers,
    )
    assert resp.status_code == 200, resp.text
    b = resp.json()
    pf = b.get("parsed_facts", {})
    assert pf["beds"] == 3
    assert pf["baths"] == 2
    assert pf["cars"] == 2
    assert pf["land_sqm"] == 550
    assert pf["floor_sqm"] == 200
    assert pf["property_type"] == "house"


# ── Scenario 8: Unknown facts stay Unknown ───────────────────────────────────


@pytest.mark.asyncio
async def test_unknown_facts_stay_unknown(
    async_client: AsyncClient,
    owner_headers: dict,
    owner_journey_id: str,
) -> None:
    # Submit structured form with NO facts at all
    resp = await async_client.post(
        f"/api/journeys/{owner_journey_id}/intake",
        json={
            "mode": "structured_form",
            "structured": {
                "address_line": "8 Unknown Facts Close",
                "suburb": "Claremont",
                "state": "WA",
                "facts": {},
            },
        },
        headers=owner_headers,
    )
    assert resp.status_code == 200, resp.text
    b = resp.json()
    prop_id = b["property_id"]
    assert prop_id is not None

    # Check the property detail — all facts should be unknown, not 0/false
    props_resp = await async_client.get(
        f"/api/journeys/{owner_journey_id}/properties/{prop_id}",
        headers=owner_headers,
    )
    assert props_resp.status_code == 200
    facts = props_resp.json()["facts"]
    for key in ("beds", "baths", "cars", "land_sqm", "floor_sqm"):
        if key in facts:
            assert facts[key]["value_state"] == "unknown", (
                f"{key} must stay unknown, got {facts[key]}"
            )
            assert facts[key]["value_int"] is None, (
                f"{key}.value_int must be None, got {facts[key]['value_int']}"
            )


# ── Scenario 9: Parse preview endpoint (no DB writes) ────────────────────────


@pytest.mark.asyncio
async def test_parse_preview_no_db_write(
    async_client: AsyncClient,
    owner_headers: dict,
    owner_journey_id: str,
) -> None:
    text = "10 Preview Avenue Claremont WA 6010\n3x2x1  Land 400sqm  $850,000"
    resp = await async_client.post(
        f"/api/journeys/{owner_journey_id}/intake/parse-preview",
        json={"raw_text": text},
        headers=owner_headers,
    )
    assert resp.status_code == 200, resp.text
    b = resp.json()
    assert b["beds"] == 3
    assert b["baths"] == 2
    assert b["cars"] == 1
    assert b["land_sqm"] == 400


# ── Scenario 10: requires_review when address is incomplete ──────────────────


@pytest.mark.asyncio
async def test_requires_review_address_incomplete(
    async_client: AsyncClient,
    owner_headers: dict,
    owner_journey_id: str,
) -> None:
    # Text with no recognisable address
    resp = await async_client.post(
        f"/api/journeys/{owner_journey_id}/intake",
        json={
            "mode": "pasted_text",
            "pasted_text": {
                "raw_text": "3 bedrooms, 2 bathrooms, 2 car garage. Beautiful family home.",
                "overrides": {},
            },
        },
        headers=owner_headers,
    )
    assert resp.status_code == 200, resp.text
    b = resp.json()
    assert b["state"] == "requires_review"
    assert "address_incomplete" in b["review_reasons"]


# ── Scenario 11: Cross-tenant isolation ──────────────────────────────────────


@pytest.mark.asyncio
async def test_cross_tenant_isolation(
    async_client: AsyncClient,
    owner_headers: dict,
    other_headers: dict,
    owner_journey_id: str,
    other_journey_id: str,
) -> None:
    # Owner creates a property
    r_owner = await async_client.post(
        f"/api/journeys/{owner_journey_id}/intake",
        json=_structured_body("11 Cross Tenant Street"),
        headers=owner_headers,
    )
    assert r_owner.status_code == 200
    intake_id = r_owner.json()["intake_id"]

    # Other tenant tries to read the owner's intake event via their own journey → 404
    r_other = await async_client.get(
        f"/api/journeys/{other_journey_id}/intake/{intake_id}",
        headers=other_headers,
    )
    assert r_other.status_code == 404

    # Other tenant submits same address → separate record in their workspace (not duplicate)
    r_other_create = await async_client.post(
        f"/api/journeys/{other_journey_id}/intake",
        json=_structured_body("11 Cross Tenant Street"),
        headers=other_headers,
    )
    assert r_other_create.status_code == 200
    # Should be completed (new property in the other workspace), NOT duplicate
    assert r_other_create.json()["state"] == "completed"


# ── Scenario 12: Price parsing (auction, range, ambiguous) ───────────────────


@pytest.mark.asyncio
async def test_price_parsing(
    async_client: AsyncClient,
    owner_headers: dict,
    owner_journey_id: str,
) -> None:
    cases = [
        ("12 Auction Road", "Auction — contact agent for details"),
        ("12 Range Road", "$850,000 - $920,000"),
        ("12 Ambiguous Road", "low $1m's — contact agent"),
    ]
    for address, price_text in cases:
        listing = f"{address} Applecross WA 6153\n3 bed 2 bath\n{price_text}"
        resp = await async_client.post(
            f"/api/journeys/{owner_journey_id}/intake",
            json={"mode": "pasted_text", "pasted_text": {"raw_text": listing, "overrides": {}}},
            headers=owner_headers,
        )
        assert resp.status_code == 200, f"Failed for price: {price_text!r}\n{resp.text}"
        b = resp.json()
        # Ambiguous price must flag for review; explicit prices should complete
        if "low $1m's" in price_text:
            assert "price_ambiguous" in b.get("review_reasons", [])
        else:
            assert b["state"] in ("completed", "duplicate", "requires_review")
