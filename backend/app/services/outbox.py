"""Durable outbox and audit helpers. No email provider is configured: delivery is suppressed."""

import uuid
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import get_settings
from app.db.models import AuditEvent, OutboxMessage


async def queue_email(
    db: AsyncSession,
    *,
    to_email: str,
    kind: str,
    subject: str,
    body_text: str,
    action_url: str | None = None,
    workspace_id: uuid.UUID | None = None,
) -> OutboxMessage:
    message = OutboxMessage(
        workspace_id=workspace_id,
        to_email=to_email,
        kind=kind,
        subject=subject,
        body_text=body_text,
        action_url=action_url,
        delivery_state="suppressed_no_provider",
    )
    db.add(message)
    return message


def action_url(path: str) -> str:
    return f"{get_settings().app_base_url}{path}"


async def record_audit(
    db: AsyncSession,
    *,
    action: str,
    actor_user_id: uuid.UUID | None = None,
    workspace_id: uuid.UUID | None = None,
    subject: str = "",
    detail: dict[str, Any] | None = None,
) -> None:
    db.add(
        AuditEvent(
            action=action,
            actor_user_id=actor_user_id,
            workspace_id=workspace_id,
            subject=subject,
            detail=detail or {},
        )
    )
