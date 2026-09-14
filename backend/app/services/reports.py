"""Deterministic, application-generated report previews. No email, calendar, portal or other
external service is contacted here. Unknown values are preserved; nothing is invented when
evidence is missing, and small/zero denominators never produce a fabricated percentage."""
from __future__ import annotations

import uuid
from datetime import date, datetime, time, timedelta, timezone
from typing import Any
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import now_utc
from app.db.models import (
    ActivityEvent,
    BuyerProperty,
    ConnectorInstance,
    DiscoveryEvent,
    DuplicateProposal,
    EnrichmentRecord,
    IntakeEvent,
    Journey,
    ListingCampaign,
    MatchEvaluation,
    Property,
    PropertyTask,
    ReportRun,
    SourceReadiness,
)
from app.services.notifications import create_notification_event
from app.services.properties import freshness_band

GENERATION_VERSIONS = {"daily": "digest_v1", "weekly": "weekly_v1", "monthly": "monthly_v1"}
REPORT_CATEGORY = {"daily": "digest_ready", "weekly": "weekly_report_ready", "monthly": "monthly_report_ready"}
REPORT_TITLE = {
    "daily": "Property Acquisition – Your Daily Digest",
    "weekly": "Property Acquisition – Your Weekly Effectiveness Report",
    "monthly": "Property Acquisition – Your Monthly Assessment",
}
ACTIVE_BUYER_STATES_EXCLUDED = ("rejected", "archived", "settled")
UNVERIFIED_PRICE_KINDS = ("contact_agent", "expressions_of_interest", "conflicting")
CANDIDATE_LIMIT = 5


def _period_for(
    report_type: str, tz_name: str, now: datetime, *, year: int | None, month: int | None, week_start: str | None
) -> tuple[datetime, datetime, datetime, bool]:
    tz = ZoneInfo(tz_name)
    local_now = now.astimezone(tz)
    if report_type == "daily":
        start_local = datetime.combine(local_now.date(), time.min, tzinfo=tz)
        end_local = start_local + timedelta(days=1)
        cutoff_local = min(local_now, end_local)
        return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc), cutoff_local.astimezone(timezone.utc), False
    if report_type == "weekly":
        start_date = date.fromisoformat(week_start) if week_start else local_now.date() - timedelta(days=7)
        start_local = datetime.combine(start_date, time.min, tzinfo=tz)
        end_local = start_local + timedelta(days=7)
        return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc), False
    if year is not None and month is not None:
        y, m = year, month
    else:
        first_of_this_month = local_now.replace(day=1)
        prev = first_of_this_month - timedelta(days=1)
        y, m = prev.year, prev.month
    start_local = datetime(y, m, 1, tzinfo=tz)
    end_local = datetime(y + 1, 1, 1, tzinfo=tz) if m == 12 else datetime(y, m + 1, 1, tzinfo=tz)
    return start_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc), end_local.astimezone(timezone.utc), False


async def _candidate_view(db: AsyncSession, journey: Journey) -> list[dict[str, Any]]:
    rows = (
        await db.execute(
            select(Property, BuyerProperty)
            .join(BuyerProperty, BuyerProperty.property_id == Property.id)
            .where(BuyerProperty.journey_id == journey.id, BuyerProperty.buyer_state.notin_(ACTIVE_BUYER_STATES_EXCLUDED))
        )
    ).all()
    if not rows:
        return []
    ids = [p.id for p, _ in rows]
    campaigns = {
        c.property_id: c
        for c in (
            await db.execute(
                select(ListingCampaign).where(ListingCampaign.property_id.in_(ids), ListingCampaign.is_current.is_(True))
            )
        ).scalars().all()
    }
    evaluations: dict[uuid.UUID, MatchEvaluation] = {}
    if journey.current_version_id is not None:
        for ev in (
            await db.execute(
                select(MatchEvaluation).where(
                    MatchEvaluation.property_id.in_(ids), MatchEvaluation.brief_version_id == journey.current_version_id
                )
            )
        ).scalars().all():
            evaluations[ev.property_id] = ev
    travel: dict[uuid.UUID, list[EnrichmentRecord]] = {}
    for rec in (
        await db.execute(
            select(EnrichmentRecord).where(
                EnrichmentRecord.property_id.in_(ids), EnrichmentRecord.kind == "travel", EnrichmentRecord.value_state == "known"
            )
        )
    ).scalars().all():
        travel.setdefault(rec.property_id, []).append(rec)
    return [
        {"property": prop, "buyer_property": bp, "campaign": campaigns.get(prop.id), "evaluation": evaluations.get(prop.id), "travel": travel.get(prop.id, [])}
        for prop, bp in rows
    ]


def _verdict_rank(ev: MatchEvaluation | None) -> int:
    return {"pass": 0, "unknown": 1, "fail": 2}[ev.verdict] if ev else 1


def _fit_pct(ev: MatchEvaluation | None) -> int:
    if ev is None:
        return -1
    pct = ev.result.get("fit", {}).get("pct")
    return pct if pct is not None else -1


def _travel_line(records: list[EnrichmentRecord]) -> str | None:
    parts = []
    for rec in records:
        payload = rec.payload or {}
        minutes, km = payload.get("duration_minutes"), payload.get("distance_km")
        if minutes is None or km is None:
            continue
        label = payload.get("label") or (rec.subject_key or "Destination").replace("_", " ").title()
        parts.append(f"{label} ~{minutes} min / {km} km")
    return " · ".join(parts) if parts else None


def _why_fits(ev: MatchEvaluation | None) -> str:
    if ev is None:
        return "Fit is unavailable — no enabled preference could be assessed yet."
    reasons = [c["reason"] for c in ev.result.get("components", []) if c.get("assessed") and (c.get("score") or 0) >= 70]
    return " ".join(reasons[:2]) if reasons else "No strong preference match recorded yet."


def _main_risk(ev: MatchEvaluation | None) -> str:
    if ev is None:
        return "Match evidence is unavailable for this property."
    for gate in ev.result.get("gates", []):
        if gate["outcome"] in ("fail", "unknown"):
            return gate["reason"]
    for comp in ev.result.get("components", []):
        if comp.get("enabled") and not comp.get("assessed"):
            return comp["reason"]
    return "No material risk or evidence gap identified from current evidence."


def _candidate_out(item: dict[str, Any]) -> dict[str, Any]:
    prop, campaign, ev = item["property"], item["campaign"], item["evaluation"]
    fit = ev.result.get("fit") if ev else {"state": "unavailable", "pct": None}
    coverage = ev.result.get("coverage") if ev else {"state": "unknown", "pct": None}
    return {
        "property_id": str(prop.id),
        "address": f"{prop.address_line}, {prop.suburb} {prop.state}",
        "image_url": prop.image_url,
        "image_attribution": prop.image_attribution,
        "raw_price": campaign.raw_price if campaign else "Unknown",
        "price_kind": campaign.price_kind if campaign else "unknown",
        "fit": fit,
        "coverage": coverage,
        "why_fits": _why_fits(ev),
        "main_risk": _main_risk(ev),
        "freshness": freshness_band(campaign.last_checked_at) if campaign else "unknown",
        "travel_line": _travel_line(item["travel"]),
        "property_link": f"/app/properties/{prop.id}",
        "evidence_link": f"/app/properties/{prop.id}?view=match",
    }


async def _daily_snapshot(db: AsyncSession, journey: Journey, *, period_start: datetime, cutoff_at: datetime) -> tuple[dict[str, Any], dict[str, Any]]:
    candidates = await _candidate_view(db, journey)
    candidates.sort(key=lambda item: (_verdict_rank(item["evaluation"]), -_fit_pct(item["evaluation"])))
    passing = [c for c in candidates if _verdict_rank(c["evaluation"]) == 0]
    top = candidates[:CANDIDATE_LIMIT]
    beyond = max(0, len(passing) - sum(1 for c in top if _verdict_rank(c["evaluation"]) == 0))
    changes = (
        await db.execute(
            select(ActivityEvent).where(ActivityEvent.journey_id == journey.id, ActivityEvent.created_at >= period_start, ActivityEvent.created_at < cutoff_at)
        )
    ).scalars().all()
    new_leads = (
        await db.execute(
            select(DiscoveryEvent).where(
                DiscoveryEvent.journey_id == journey.id, DiscoveryEvent.event_type == "first_discovery",
                DiscoveryEvent.discovered_at >= period_start, DiscoveryEvent.discovered_at < cutoff_at,
            )
        )
    ).scalars().all()
    price_verification = [c for c in candidates if c["campaign"] and c["campaign"].price_kind in UNVERIFIED_PRICE_KINDS]
    deadlines = (
        await db.execute(
            select(PropertyTask).where(
                PropertyTask.journey_id == journey.id, PropertyTask.done.is_(False), PropertyTask.deleted_at.is_(None),
                PropertyTask.due_at.is_not(None), PropertyTask.due_at < cutoff_at + timedelta(days=14),
            )
        )
    ).scalars().all()
    connectors = (
        await db.execute(
            select(SourceReadiness).join(ConnectorInstance, ConnectorInstance.id == SourceReadiness.connector_instance_id)
            .where(ConnectorInstance.workspace_id == journey.workspace_id)
        )
    ).scalars().all()
    health_counts: dict[str, int] = {}
    for sr in connectors:
        health_counts[sr.readiness_state] = health_counts.get(sr.readiness_state, 0) + 1
    quiet_day = len(changes) == 0 and len(new_leads) == 0
    snapshot = {
        "title": REPORT_TITLE["daily"],
        "quiet_day": quiet_day,
        "quiet_day_message": "No material changes were recorded in this period." if quiet_day else None,
        "material_changes_count": len(changes),
        "current_candidates": [_candidate_out(c) for c in top],
        "matching_beyond_top_count": beyond,
        "new_leads": [
            {"property_id": str(e.property_id), "channel": e.channel, "discovered_at": e.discovered_at.isoformat(), "source_label": e.source_label}
            for e in new_leads
        ],
        "price_verification_opportunities": [
            {
                "property_id": str(c["property"].id),
                "address": f"{c['property'].address_line}, {c['property'].suburb} {c['property'].state}",
                "price_kind": c["campaign"].price_kind,
                "raw_price": c["campaign"].raw_price,
            }
            for c in price_verification
        ],
        "upcoming_home_opens": [],
        "upcoming_home_opens_note": "Home-open evidence is not yet tracked in this prototype.",
        "upcoming_deadlines": [
            {"task_id": str(t.id), "title": t.title, "due_at": t.due_at.isoformat(), "property_id": str(t.property_id) if t.property_id else None}
            for t in deadlines
        ],
        "source_evidence_health": {"connector_states": health_counts, "total_connectors": len(connectors)},
    }
    coverage_summary = {
        "candidates_considered": len(candidates),
        "candidates_with_known_fit": sum(1 for c in candidates if c["evaluation"] and c["evaluation"].result.get("fit", {}).get("state") == "known"),
    }
    return snapshot, coverage_summary


async def _weekly_snapshot(db: AsyncSession, journey: Journey, *, period_start: datetime, period_end: datetime) -> tuple[dict[str, Any], dict[str, Any]]:
    discoveries = (
        await db.execute(
            select(DiscoveryEvent).where(
                DiscoveryEvent.journey_id == journey.id, DiscoveryEvent.event_type == "first_discovery",
                DiscoveryEvent.discovered_at >= period_start, DiscoveryEvent.discovered_at < period_end,
            )
        )
    ).scalars().all()
    channel_events = (
        await db.execute(
            select(func.count()).select_from(DiscoveryEvent).where(
                DiscoveryEvent.journey_id == journey.id, DiscoveryEvent.event_type == "channel_event",
                DiscoveryEvent.discovered_at >= period_start, DiscoveryEvent.discovered_at < period_end,
            )
        )
    ).scalar_one()
    by_channel: dict[str, int] = {}
    for d in discoveries:
        by_channel[d.channel] = by_channel.get(d.channel, 0) + 1
    evaluations = (
        await db.execute(
            select(MatchEvaluation).where(MatchEvaluation.journey_id == journey.id, MatchEvaluation.computed_at >= period_start, MatchEvaluation.computed_at < period_end)
        )
    ).scalars().all()
    provisional = sum(1 for e in evaluations if e.verdict == "unknown")
    verified = sum(1 for e in evaluations if e.verdict == "pass" and e.coverage_pct == 100)
    high_priority = sum(1 for e in evaluations if e.verdict == "pass" and (e.fit_pct or 0) >= 80)
    hard_failures = sum(1 for e in evaluations if e.verdict == "fail")
    withdrawn = (
        await db.execute(
            select(func.count()).select_from(ListingCampaign).where(
                ListingCampaign.workspace_id == journey.workspace_id, ListingCampaign.market_state.in_(("withdrawn", "sold")),
                ListingCampaign.updated_at >= period_start, ListingCampaign.updated_at < period_end,
            )
        )
    ).scalar_one()
    completed_tasks = (
        await db.execute(
            select(func.count()).select_from(PropertyTask).where(
                PropertyTask.journey_id == journey.id, PropertyTask.done_at >= period_start, PropertyTask.done_at < period_end
            )
        )
    ).scalar_one()
    activity_actions = (
        await db.execute(
            select(func.count()).select_from(ActivityEvent).where(
                ActivityEvent.journey_id == journey.id, ActivityEvent.created_at >= period_start, ActivityEvent.created_at < period_end
            )
        )
    ).scalar_one()
    duplicates_detected = (
        await db.execute(
            select(func.count()).select_from(DuplicateProposal).where(
                DuplicateProposal.workspace_id == journey.workspace_id, DuplicateProposal.created_at >= period_start, DuplicateProposal.created_at < period_end
            )
        )
    ).scalar_one()
    duplicates_resolved = (
        await db.execute(
            select(func.count()).select_from(DuplicateProposal).where(
                DuplicateProposal.workspace_id == journey.workspace_id, DuplicateProposal.state.in_(("confirmed", "rejected", "undone")),
                DuplicateProposal.reviewed_at >= period_start, DuplicateProposal.reviewed_at < period_end,
            )
        )
    ).scalar_one()
    connectors = (
        await db.execute(
            select(SourceReadiness).join(ConnectorInstance, ConnectorInstance.id == SourceReadiness.connector_instance_id)
            .where(ConnectorInstance.workspace_id == journey.workspace_id)
        )
    ).scalars().all()
    readiness_counts: dict[str, int] = {}
    for sr in connectors:
        readiness_counts[sr.readiness_state] = readiness_counts.get(sr.readiness_state, 0) + 1
    intake_events = (
        await db.execute(
            select(IntakeEvent).where(
                IntakeEvent.journey_id == journey.id, IntakeEvent.completed_at.is_not(None),
                IntakeEvent.first_attempted_at >= period_start, IntakeEvent.first_attempted_at < period_end,
            )
        )
    ).scalars().all()
    latencies = [(e.completed_at - e.first_attempted_at).total_seconds() for e in intake_events if e.completed_at]
    avg_latency_seconds = round(sum(latencies) / len(latencies), 1) if latencies else None
    daily_trend = []
    cursor = period_start
    while cursor < period_end:
        day_end = cursor + timedelta(days=1)
        count = sum(1 for d in discoveries if cursor <= d.discovered_at < day_end)
        daily_trend.append({"date": cursor.date().isoformat(), "first_discoveries": count})
        cursor = day_end
    suburb_view: dict[str, dict[str, int]] = {}
    for e in evaluations:
        prop = (await db.execute(select(Property).where(Property.id == e.property_id))).scalar_one_or_none()
        if prop is None:
            continue
        bucket = suburb_view.setdefault(f"{prop.suburb} {prop.state}", {"pass": 0, "fail": 0, "unknown": 0})
        bucket[e.verdict] += 1
    funnel = []
    for channel, count in by_channel.items():
        converted = 0
        for d in discoveries:
            if d.channel != channel:
                continue
            passed = (await db.execute(select(MatchEvaluation.id).where(MatchEvaluation.property_id == d.property_id, MatchEvaluation.verdict == "pass"))).first()
            if passed is not None:
                converted += 1
        funnel.append({"channel": channel, "first_discoveries": count, "reached_pass": converted, "conversion_rate": round(100 * converted / count) if count else None})
    snapshot = {
        "title": REPORT_TITLE["weekly"],
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "unique_first_discoveries": {"total": len(discoveries), "by_channel": by_channel},
        "later_channel_material_changes": int(channel_events),
        "provisional_opportunities": provisional,
        "fully_verified_eligibility": verified,
        "high_priority_candidates": high_priority,
        "hard_failures": hard_failures,
        "unavailable_withdrawn_stock": int(withdrawn),
        "actions_replies_completed_tasks": {"activity_events": int(activity_actions), "completed_tasks": int(completed_tasks)},
        "duplicates": {"detected": int(duplicates_detected), "resolved": int(duplicates_resolved)},
        "source_coverage_readiness": readiness_counts,
        "processing_evidence_latency_seconds": avg_latency_seconds,
        "daily_trend": daily_trend,
        "source_channel_funnel": funnel,
        "suburb_outcome_view": suburb_view,
    }
    coverage_summary = {"evaluations_in_period": len(evaluations), "connectors_tracked": len(connectors)}
    return snapshot, coverage_summary


async def _monthly_snapshot(
    db: AsyncSession, journey: Journey, *, period_start: datetime, period_end: datetime
) -> tuple[dict[str, Any], dict[str, Any]]:
    actual_start = max(period_start, journey.created_at)
    partial = actual_start > period_start
    properties_added = (
        await db.execute(
            select(func.count()).select_from(Property).where(Property.journey_id == journey.id, Property.created_at >= actual_start, Property.created_at < period_end)
        )
    ).scalar_one()
    discoveries = (
        await db.execute(
            select(DiscoveryEvent).where(
                DiscoveryEvent.journey_id == journey.id, DiscoveryEvent.event_type == "first_discovery",
                DiscoveryEvent.discovered_at >= actual_start, DiscoveryEvent.discovered_at < period_end,
            )
        )
    ).scalars().all()
    by_channel: dict[str, int] = {}
    for d in discoveries:
        by_channel[d.channel] = by_channel.get(d.channel, 0) + 1
    evaluations = (
        await db.execute(
            select(MatchEvaluation).where(MatchEvaluation.journey_id == journey.id, MatchEvaluation.computed_at >= actual_start, MatchEvaluation.computed_at < period_end)
        )
    ).scalars().all()
    verdict_counts = {"pass": 0, "fail": 0, "unknown": 0}
    for e in evaluations:
        verdict_counts[e.verdict] += 1
    stage_changes = (
        await db.execute(
            select(func.count()).select_from(ActivityEvent).where(
                ActivityEvent.journey_id == journey.id, ActivityEvent.kind == "stage_changed",
                ActivityEvent.created_at >= actual_start, ActivityEvent.created_at < period_end,
            )
        )
    ).scalar_one()
    duplicates = (
        await db.execute(
            select(func.count()).select_from(DuplicateProposal).where(
                DuplicateProposal.workspace_id == journey.workspace_id, DuplicateProposal.created_at >= actual_start, DuplicateProposal.created_at < period_end
            )
        )
    ).scalar_one()
    completed_tasks = (
        await db.execute(
            select(func.count()).select_from(PropertyTask).where(
                PropertyTask.journey_id == journey.id, PropertyTask.done_at >= actual_start, PropertyTask.done_at < period_end
            )
        )
    ).scalar_one()
    reports_generated = (
        await db.execute(
            select(func.count()).select_from(ReportRun).where(
                ReportRun.journey_id == journey.id, ReportRun.release_state == "ready",
                ReportRun.generated_at >= actual_start, ReportRun.generated_at < period_end,
            )
        )
    ).scalar_one()
    gate_failures: dict[str, int] = {}
    for e in evaluations:
        for gate in e.result.get("gates", []):
            if gate["outcome"] == "fail":
                gate_failures[gate["criterion"]] = gate_failures.get(gate["criterion"], 0) + 1
    top_constraints = sorted(gate_failures.items(), key=lambda kv: -kv[1])[:3]
    improvement_priorities = []
    if top_constraints:
        label, count = top_constraints[0]
        improvement_priorities.append(f"{label.replace('_', ' ').title()} was the most common hard-rule failure ({count} propert{'y' if count == 1 else 'ies'}).")
    if verdict_counts["unknown"] > 0:
        improvement_priorities.append(f"{verdict_counts['unknown']} evaluation(s) remained Unknown — verifying evidence would raise coverage.")
    if not improvement_priorities:
        improvement_priorities.append("Not enough recorded activity this period to identify a priority.")
    snapshot = {
        "title": REPORT_TITLE["monthly"],
        "period_start": period_start.isoformat(),
        "period_end": period_end.isoformat(),
        "actual_coverage_start": actual_start.isoformat(),
        "is_partial_period": partial,
        "overall_activity": {"properties_added": int(properties_added), "evaluations_run": len(evaluations)},
        "source_value_unique_discoveries": by_channel,
        "verdict_distribution": verdict_counts,
        "candidate_progression_stage_changes": int(stage_changes),
        "duplicate_and_intake_quality": {"duplicates_detected": int(duplicates)},
        "task_action_completion": {"completed_tasks": int(completed_tasks)},
        "report_notification_effectiveness": {"reports_generated": int(reports_generated)},
        "material_constraints": [{"criterion": k, "count": v} for k, v in top_constraints],
        "improvement_priorities": improvement_priorities,
    }
    coverage_summary = {"evaluations_in_period": len(evaluations), "partial_period": partial}
    return snapshot, coverage_summary


async def generate_report(
    db: AsyncSession,
    *,
    journey: Journey,
    report_type: str,
    release_kind: str,
    requested_by_user_id: uuid.UUID,
    now: datetime | None = None,
    year: int | None = None,
    month: int | None = None,
    week_start: str | None = None,
) -> ReportRun:
    """Idempotent per (workspace, report type, period, release kind). A replay of an
    identical request returns the existing ready run without a duplicate notification."""
    moment = now or now_utc()
    tz_name = journey.timezone or "Australia/Perth"
    period_start, period_end, cutoff_at, _ = _period_for(report_type, tz_name, moment, year=year, month=month, week_start=week_start)
    generation_version = GENERATION_VERSIONS[report_type]
    idem_key = f"{report_type}:{release_kind}:{period_start.isoformat()}:{period_end.isoformat()}:{generation_version}"
    existing = (
        await db.execute(select(ReportRun).where(ReportRun.workspace_id == journey.workspace_id, ReportRun.idempotency_key == idem_key))
    ).scalar_one_or_none()
    if existing is not None and existing.release_state == "ready":
        return existing
    run = existing
    if run is None:
        run = ReportRun(
            workspace_id=journey.workspace_id, journey_id=journey.id, idempotency_key=idem_key, kind=release_kind,
            report_type=report_type, release_state="generating", period_start=period_start, period_end=period_end,
            cutoff_at=cutoff_at, timezone=tz_name, generation_version=generation_version, detail={},
        )
        db.add(run)
        await db.flush()
    else:
        run.release_state = "generating"
    try:
        if report_type == "daily":
            snapshot, coverage = await _daily_snapshot(db, journey, period_start=period_start, cutoff_at=cutoff_at)
        elif report_type == "weekly":
            snapshot, coverage = await _weekly_snapshot(db, journey, period_start=period_start, period_end=period_end)
        else:
            snapshot, coverage = await _monthly_snapshot(db, journey, period_start=period_start, period_end=period_end)
    except Exception as exc:
        run.release_state = "failed"
        run.failure_reason = str(exc)[:400]
        await db.flush()
        raise
    run.snapshot = snapshot
    run.is_partial_period = bool(snapshot.get("is_partial_period", False))
    run.detail = {"evidence_coverage_summary": coverage}
    run.release_state = "ready"
    run.generated_at = moment
    await db.flush()
    await create_notification_event(
        db, workspace_id=journey.workspace_id, category=REPORT_CATEGORY[report_type], fingerprint=f"report:{run.id}",
        title=snapshot.get("title", "Report ready"), message="Your report preview is ready to view.",
        safe_deep_link=f"/app/reports?type={report_type}&run={run.id}", priority="normal", report_run_id=run.id, now=moment,
    )
    return run
