"""Sources & Coverage API — provider-neutral connector catalogue with workspace state.

GET /api/sources/connectors        — list all connectors + workspace-specific instance state
GET /api/sources/connectors/{slug} — single connector detail

All entries are clearly labelled as synthetic / not connected.  No functional
connection controls are provided in this milestone.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import AuthContext, get_auth
from app.db.base import get_db
from app.db.models import ConnectorDefinition, ConnectorInstance, SourceReadiness

router = APIRouter(prefix="/sources", tags=["sources"])


def _connector_out(
    c: ConnectorDefinition,
    ci: ConnectorInstance | None,
    sr: SourceReadiness | None,
) -> dict:
    return {
        "id": str(c.id),
        "slug": c.slug,
        "display_name": c.display_name,
        "description": c.description,
        "acquisition_mechanism": c.acquisition_mechanism,
        "capabilities": c.capabilities,         # list[str]
        "jurisdiction_codes": c.jurisdiction_codes,  # list[str]
        "licence_kind": c.licence_kind,
        "licence_state": c.licence_state,
        "kill_switch": c.kill_switch,
        "version": c.version,
        # Workspace-specific connector instance (may be absent for new workspaces)
        "instance_id": str(ci.id) if ci else None,
        "enabled": ci.enabled if ci else False,
        "connector_readiness": ci.readiness_state if ci else "unconfigured",
        "health_checked_at": ci.health_checked_at.isoformat() if ci and ci.health_checked_at else None,
        "health_detail": ci.health_detail if ci else None,
        # Source readiness — requested vs effective filters, deviation reason
        "source_readiness": sr.readiness_state if sr else None,
        "requested_filters": sr.requested_filters if sr else {},
        "effective_filters": sr.effective_filters if sr else {},
        "deviation_reason": sr.deviation_reason if sr else None,
        "last_activity_at": (
            sr.status_checked_at.isoformat() if sr and sr.status_checked_at else None
        ),
        # Always shown — truthful synthetic label
        "status_label": "Not connected · Synthetic demonstration",
    }


@router.get("/connectors", summary="List all connector definitions")
async def list_connectors(
    jurisdiction: str | None = None,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
) -> dict:
    connectors = (await db.execute(select(ConnectorDefinition))).scalars().all()

    # Build workspace maps once
    ci_rows = (
        await db.execute(
            select(ConnectorInstance).where(ConnectorInstance.workspace_id == auth.workspace.id)
        )
    ).scalars().all()
    ci_map: dict = {ci.definition_id: ci for ci in ci_rows}

    sr_map: dict = {}
    if ci_rows:
        ci_ids = [ci.id for ci in ci_rows]
        sr_rows = (
            await db.execute(
                select(SourceReadiness).where(
                    SourceReadiness.connector_instance_id.in_(ci_ids)
                )
            )
        ).scalars().all()
        sr_map = {sr.connector_instance_id: sr for sr in sr_rows}

    items = []
    for c in connectors:
        if jurisdiction and jurisdiction.upper() not in [
            j.upper() for j in (c.jurisdiction_codes or [])
        ]:
            continue
        ci = ci_map.get(c.id)
        sr = sr_map.get(ci.id) if ci else None
        items.append(_connector_out(c, ci, sr))

    await db.commit()
    return {"items": items, "total": len(items)}


@router.get("/connectors/{slug}", summary="Get connector definition by slug")
async def get_connector(
    slug: str,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
) -> dict:
    c = (
        await db.execute(select(ConnectorDefinition).where(ConnectorDefinition.slug == slug))
    ).scalar_one_or_none()
    if c is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Connector not found")

    ci = (
        await db.execute(
            select(ConnectorInstance).where(
                ConnectorInstance.workspace_id == auth.workspace.id,
                ConnectorInstance.definition_id == c.id,
            )
        )
    ).scalar_one_or_none()

    sr = None
    if ci:
        sr = (
            await db.execute(
                select(SourceReadiness).where(
                    SourceReadiness.connector_instance_id == ci.id
                )
            )
        ).scalar_one_or_none()

    await db.commit()
    return _connector_out(c, ci, sr)
