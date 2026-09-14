import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.deps import AuthContext, get_auth, require_writer, scoped_journey
from app.core.security import now_utc
from app.db.base import get_db
from app.db.models import (
    ActivityEvent,
    BuyerProperty,
    Fact,
    GateWaiver,
    Journey,
    ListingCampaign,
    MatchEvaluation,
    Observation,
    Property,
    PropertyNote,
    PropertyTask,
    User,
)
from app.schemas.properties import (
    ActivityOut,
    CampaignOut,
    EvaluationOut,
    FactOut,
    InspectionChange,
    NoteCreate,
    NoteOut,
    NoteUpdate,
    ObservationOut,
    PropertyDetail,
    PropertySummary,
    SavedChange,
    StageChange,
    TaskCreate,
    TaskOut,
    TaskUpdate,
    TodayOut,
    WaiverCreate,
    WaiverOut,
)
from app.services.properties import (
    ALLOWED_TRANSITIONS,
    active_waivers,
    check_row_version,
    check_transition,
    current_evaluation,
    freshness_band,
)

router = APIRouter(prefix="/journeys/{journey_id}", tags=["properties"])


async def _emails(db: AsyncSession, ids: set[uuid.UUID | None]) -> dict[uuid.UUID, str]:
    wanted = {i for i in ids if i is not None}
    if not wanted:
        return {}
    rows = (await db.execute(select(User.id, User.email).where(User.id.in_(wanted)))).all()
    return {uid: email for uid, email in rows}


async def _scoped_property(
    db: AsyncSession, journey: Journey, property_id: uuid.UUID
) -> tuple[Property, BuyerProperty]:
    row = (
        await db.execute(
            select(Property, BuyerProperty)
            .join(BuyerProperty, BuyerProperty.property_id == Property.id)
            .where(
                Property.id == property_id,
                Property.workspace_id == journey.workspace_id,
                BuyerProperty.journey_id == journey.id,
            )
        )
    ).first()
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Property not found")
    return row[0], row[1]


def _eval_out(ev: MatchEvaluation | None) -> EvaluationOut | None:
    if ev is None:
        return None
    r = ev.result
    return EvaluationOut(
        id=ev.id,
        brief_version_no=r["brief_version_no"],
        evaluation_version=ev.evaluation_version,
        input_hash=ev.input_hash,
        verdict=ev.verdict,
        route=r["route"],
        fit=r["fit"],
        coverage=r["coverage"],
        gates=r["gates"],
        components=r["components"],
        computed_at=ev.computed_at,
    )


def _campaign_out(c: ListingCampaign) -> CampaignOut:
    return CampaignOut(
        id=c.id,
        source_label=c.source_label,
        market_state=c.market_state,
        price_kind=c.price_kind,
        raw_price=c.raw_price,
        lower_minor=c.lower_minor,
        upper_minor=c.upper_minor,
        currency=c.currency,
        price_source=c.price_source,
        last_checked_at=c.last_checked_at,
        freshness=freshness_band(c.last_checked_at),
    )


def _fact_out(f: Fact, o: Observation) -> FactOut:
    return FactOut(
        key=f.key,
        value_state=f.value_state,
        value_int=f.value_int,
        value_text=f.value_text,
        value_bool=f.value_bool,
        source_kind=o.source_kind,
        source_label=o.source_label,
        observed_at=o.observed_at,
        checked_at=o.checked_at,
        freshness=freshness_band(o.checked_at),
        confidence=f.confidence,
        conflict_note=f.conflict_note,
    )


async def _summaries(
    db: AsyncSession, journey: Journey, rows: list[tuple[Property, BuyerProperty]]
) -> list[PropertySummary]:
    """Four batched queries for any number of properties; the pooler round-trip dominates latency."""
    if not rows:
        return []
    ids = [p.id for p, _ in rows]
    campaigns: dict[uuid.UUID, ListingCampaign] = {}
    for c in (
        (
            await db.execute(
                select(ListingCampaign)
                .where(ListingCampaign.property_id.in_(ids), ListingCampaign.is_current.is_(True))
                .order_by(ListingCampaign.created_at)
            )
        )
        .scalars()
        .all()
    ):
        campaigns[c.property_id] = c
    facts: dict[uuid.UUID, dict[str, FactOut]] = {i: {} for i in ids}
    for f, o in (
        await db.execute(
            select(Fact, Observation)
            .join(Observation, Observation.id == Fact.observation_id)
            .where(Fact.property_id.in_(ids))
        )
    ).all():
        facts[f.property_id][f.key] = _fact_out(f, o)
    evaluations: dict[uuid.UUID, MatchEvaluation] = {}
    if journey.current_version_id is not None:
        for ev in (
            (
                await db.execute(
                    select(MatchEvaluation).where(
                        MatchEvaluation.property_id.in_(ids),
                        MatchEvaluation.brief_version_id == journey.current_version_id,
                    )
                )
            )
            .scalars()
            .all()
        ):
            evaluations[ev.property_id] = ev
        for p, _ in rows:
            if p.id not in evaluations:
                found = await current_evaluation(db, p, journey)
                if found is not None:
                    evaluations[p.id] = found
    waived: dict[uuid.UUID, set[str]] = {i: set() for i in ids}
    for w in (
        (
            await db.execute(
                select(GateWaiver).where(
                    GateWaiver.property_id.in_(ids),
                    GateWaiver.journey_id == journey.id,
                    GateWaiver.revoked_at.is_(None),
                )
            )
        )
        .scalars()
        .all()
    ):
        waived[w.property_id].add(w.criterion)
    out = []
    for prop, bp in rows:
        campaign = campaigns.get(prop.id)
        out.append(
            PropertySummary(
                id=prop.id,
                legacy_ref=prop.legacy_ref,
                address_line=prop.address_line,
                unit=prop.unit,
                suburb=prop.suburb,
                state=prop.state,
                postcode=prop.postcode,
                synthetic=prop.synthetic,
                image_url=prop.image_url,
                image_attribution=prop.image_attribution,
                campaign=_campaign_out(campaign) if campaign else None,
                facts=facts[prop.id],
                buyer_state=bp.buyer_state,
                saved=bp.saved,
                buyer_row_version=bp.row_version,
                evaluation=_eval_out(evaluations.get(prop.id)),
                waived_criteria=sorted(waived[prop.id]),
                allowed_transitions=list(ALLOWED_TRANSITIONS[bp.buyer_state]),
                inspection_state=bp.inspection_state,
                inspection_note=bp.inspection_note,
                inspection_recorded_at=bp.inspection_recorded_at,
                updated_at=max(prop.updated_at, bp.updated_at),
            )
        )
    return out


def _activity_out(rows: list[ActivityEvent], emails: dict[uuid.UUID, str]) -> list[ActivityOut]:
    return [
        ActivityOut(
            id=a.id,
            kind=a.kind,
            summary=a.summary,
            detail=a.detail,
            actor_email=emails.get(a.actor_user_id) if a.actor_user_id else None,
            property_id=a.property_id,
            created_at=a.created_at,
        )
        for a in rows
    ]


async def _detail(db: AsyncSession, journey: Journey, prop: Property, bp: BuyerProperty) -> PropertyDetail:
    summary = (await _summaries(db, journey, [(prop, bp)]))[0]
    observations = (
        (
            await db.execute(
                select(Observation)
                .where(Observation.property_id == prop.id)
                .order_by(Observation.checked_at.desc())
            )
        )
        .scalars()
        .all()
    )
    waivers = await active_waivers(db, prop, journey)
    notes = (
        (
            await db.execute(
                select(PropertyNote)
                .where(PropertyNote.property_id == prop.id, PropertyNote.journey_id == journey.id)
                .order_by(PropertyNote.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    tasks = (
        (
            await db.execute(
                select(PropertyTask)
                .where(PropertyTask.property_id == prop.id, PropertyTask.journey_id == journey.id)
                .order_by(PropertyTask.done, PropertyTask.created_at.desc())
            )
        )
        .scalars()
        .all()
    )
    activity = (
        (
            await db.execute(
                select(ActivityEvent)
                .where(ActivityEvent.property_id == prop.id, ActivityEvent.journey_id == journey.id)
                .order_by(ActivityEvent.created_at.desc())
                .limit(50)
            )
        )
        .scalars()
        .all()
    )
    actor_ids: set[uuid.UUID | None] = {w.actor_user_id for w in waivers}
    actor_ids |= {n.author_user_id for n in notes}
    actor_ids |= {a.actor_user_id for a in activity}
    emails = await _emails(db, actor_ids)
    return PropertyDetail(
        **summary.model_dump(),
        observations=[
            ObservationOut(
                id=o.id,
                source_kind=o.source_kind,
                source_label=o.source_label,
                observed_at=o.observed_at,
                checked_at=o.checked_at,
                freshness=freshness_band(o.checked_at),
                note=o.note,
            )
            for o in observations
        ],
        waivers=[
            WaiverOut(
                id=w.id,
                criterion=w.criterion,
                reason=w.reason,
                actor_email=emails.get(w.actor_user_id, ""),
                created_at=w.created_at,
            )
            for w in waivers
        ],
        notes=[
            NoteOut(
                id=n.id,
                body=n.body,
                author_email=emails.get(n.author_user_id, ""),
                row_version=n.row_version,
                created_at=n.created_at,
                updated_at=n.updated_at,
            )
            for n in notes
        ],
        tasks=[
            TaskOut(
                id=t.id,
                title=t.title,
                done=t.done,
                done_at=t.done_at,
                row_version=t.row_version,
                created_at=t.created_at,
            )
            for t in tasks
        ],
        activity=_activity_out(list(activity), emails),
        row_version=prop.row_version,
    )


def _log(
    db: AsyncSession,
    journey: Journey,
    prop: Property | None,
    actor: uuid.UUID,
    kind: str,
    summary: str,
    detail: dict[str, object] | None = None,
) -> None:
    db.add(
        ActivityEvent(
            workspace_id=journey.workspace_id,
            journey_id=journey.id,
            property_id=prop.id if prop else None,
            kind=kind,
            summary=summary,
            detail=detail or {},
            actor_user_id=actor,
        )
    )


@router.get("/properties", response_model=list[PropertySummary])
async def list_properties(
    journey_id: uuid.UUID,
    buyer_state: str | None = None,
    verdict: str | None = None,
    q: str | None = None,
    saved: bool | None = None,
    sort: str = Query("checked", pattern="^(checked|address|fit)$"),
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
) -> list[PropertySummary]:
    journey = await scoped_journey(journey_id, db, auth.workspace.id)
    rows = (
        await db.execute(
            select(Property, BuyerProperty)
            .join(BuyerProperty, BuyerProperty.property_id == Property.id)
            .where(BuyerProperty.journey_id == journey.id)
        )
    ).all()
    out = await _summaries(db, journey, [(p, bp) for p, bp in rows])
    if buyer_state:
        out = [s for s in out if s.buyer_state == buyer_state]
    if saved is not None:
        out = [s for s in out if s.saved == saved]
    if verdict:
        out = [s for s in out if (s.evaluation.verdict if s.evaluation else "unknown") == verdict]
    if q:
        needle = q.strip().lower()
        out = [
            s
            for s in out
            if needle
            in f"{s.address_line} {s.suburb} {s.legacy_ref or ''} "
            f"{s.campaign.raw_price if s.campaign else ''}".lower()
        ]
    if sort == "address":
        out.sort(key=lambda s: (s.suburb, s.address_line))
    elif sort == "fit":
        out.sort(
            key=lambda s: (
                s.evaluation is None or s.evaluation.fit["pct"] is None,
                -(s.evaluation.fit["pct"] or 0) if s.evaluation else 0,
            )
        )
    else:
        out.sort(key=lambda s: s.campaign.last_checked_at if s.campaign else s.updated_at, reverse=True)
    await db.commit()
    return out


@router.get("/properties/compare", response_model=list[PropertySummary])
async def compare_properties(
    journey_id: uuid.UUID,
    ids: str = Query(..., description="Comma-separated property ids, up to four"),
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
) -> list[PropertySummary]:
    journey = await scoped_journey(journey_id, db, auth.workspace.id)
    wanted: list[uuid.UUID] = []
    for raw in ids.split(","):
        raw = raw.strip()
        if not raw:
            continue
        try:
            wanted.append(uuid.UUID(raw))
        except ValueError as exc:
            raise HTTPException(status_code=422, detail="Invalid property id") from exc
    if len(wanted) > 4:
        raise HTTPException(status_code=422, detail="Compare up to four properties.")
    pairs = [await _scoped_property(db, journey, pid) for pid in wanted]
    out = await _summaries(db, journey, pairs)
    await db.commit()
    return out


@router.get("/today", response_model=TodayOut)
async def today(
    journey_id: uuid.UUID, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)
) -> TodayOut:
    journey = await scoped_journey(journey_id, db, auth.workspace.id)
    rows = (
        await db.execute(
            select(Property, BuyerProperty)
            .join(BuyerProperty, BuyerProperty.property_id == Property.id)
            .where(BuyerProperty.journey_id == journey.id)
        )
    ).all()
    summaries = await _summaries(db, journey, [(p, bp) for p, bp in rows])
    changes = (
        (
            await db.execute(
                select(ActivityEvent)
                .where(ActivityEvent.journey_id == journey.id)
                .order_by(ActivityEvent.created_at.desc())
                .limit(8)
            )
        )
        .scalars()
        .all()
    )
    open_tasks = int(
        (
            await db.execute(
                select(func.count())
                .select_from(PropertyTask)
                .where(PropertyTask.journey_id == journey.id, PropertyTask.done.is_(False))
            )
        ).scalar_one()
    )

    def verdict(s: PropertySummary) -> str:
        return s.evaluation.verdict if s.evaluation else "unknown"

    attention = [s for s in summaries if verdict(s) == "unknown" and s.buyer_state == "reviewing"][:3]
    await db.commit()
    return TodayOut(
        journey_id=journey.id,
        brief_version_no=summaries[0].evaluation.brief_version_no
        if summaries and summaries[0].evaluation
        else None,
        total_properties=len(summaries),
        eligible_reviewing=sum(1 for s in summaries if verdict(s) == "pass" and s.buyer_state == "reviewing"),
        verification_required=sum(1 for s in summaries if verdict(s) == "unknown"),
        known_failures=sum(1 for s in summaries if verdict(s) == "fail"),
        fit_available=sum(1 for s in summaries if s.evaluation and s.evaluation.fit["state"] == "known"),
        under_offer_market=sum(
            1 for s in summaries if s.campaign and s.campaign.market_state == "under_offer"
        ),
        changes=_activity_out(list(changes), await _emails(db, {c.actor_user_id for c in changes})),
        open_tasks=open_tasks,
        attention=attention,
    )


@router.get("/properties/{property_id}", response_model=PropertyDetail)
async def get_property(
    journey_id: uuid.UUID,
    property_id: uuid.UUID,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
) -> PropertyDetail:
    journey = await scoped_journey(journey_id, db, auth.workspace.id)
    prop, bp = await _scoped_property(db, journey, property_id)
    detail = await _detail(db, journey, prop, bp)
    await db.commit()
    return detail


@router.post("/properties/{property_id}/stage", response_model=PropertyDetail)
async def change_stage(
    journey_id: uuid.UUID,
    property_id: uuid.UUID,
    body: StageChange,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
) -> PropertyDetail:
    require_writer(auth)
    journey = await scoped_journey(journey_id, db, auth.workspace.id)
    prop, bp = await _scoped_property(db, journey, property_id)
    check_row_version(bp.row_version, body.expected_row_version, "property")
    ev = await current_evaluation(db, prop, journey)
    waived = {w.criterion for w in await active_waivers(db, prop, journey)}
    check_transition(bp, body.to_state, ev, waived)
    previous = bp.buyer_state
    bp.buyer_state = body.to_state
    bp.stage_changed_at = now_utc()
    bp.stage_changed_by = auth.user.id
    bp.row_version += 1
    _log(
        db,
        journey,
        prop,
        auth.user.id,
        "stage_changed",
        f"Moved from {previous.replace('_', ' ')} to {body.to_state.replace('_', ' ')}",
        {"from": previous, "to": body.to_state},
    )
    await db.commit()
    await db.refresh(bp)
    return await _detail(db, journey, prop, bp)


@router.post("/properties/{property_id}/saved", response_model=PropertyDetail)
async def set_saved(
    journey_id: uuid.UUID,
    property_id: uuid.UUID,
    body: SavedChange,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
) -> PropertyDetail:
    require_writer(auth)
    journey = await scoped_journey(journey_id, db, auth.workspace.id)
    prop, bp = await _scoped_property(db, journey, property_id)
    check_row_version(bp.row_version, body.expected_row_version, "property")
    bp.saved = body.saved
    bp.row_version += 1
    _log(
        db,
        journey,
        prop,
        auth.user.id,
        "saved" if body.saved else "unsaved",
        "Saved to shortlist" if body.saved else "Removed from shortlist",
    )
    await db.commit()
    await db.refresh(bp)
    return await _detail(db, journey, prop, bp)


@router.post("/properties/{property_id}/inspection", response_model=PropertyDetail)
async def set_inspection(
    journey_id: uuid.UUID,
    property_id: uuid.UUID,
    body: InspectionChange,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
) -> PropertyDetail:
    """Lightweight, manual, human-entered inspection feedback. Never read by the
    matching engine — see services/matching.py, which has no reference to these fields."""
    require_writer(auth)
    journey = await scoped_journey(journey_id, db, auth.workspace.id)
    prop, bp = await _scoped_property(db, journey, property_id)
    check_row_version(bp.row_version, body.expected_row_version, "property")
    bp.inspection_state = body.inspection_state
    bp.inspection_note = (body.inspection_note or "").strip() or None
    bp.inspection_recorded_at = now_utc()
    bp.inspection_recorded_by = auth.user.id
    bp.row_version += 1
    _log(
        db,
        journey,
        prop,
        auth.user.id,
        "inspection_feedback_recorded",
        f"Recorded inspection feedback: {body.inspection_state.replace('_', ' ')}",
        {"inspection_state": body.inspection_state},
    )
    await db.commit()
    await db.refresh(bp)
    return await _detail(db, journey, prop, bp)


@router.post("/properties/{property_id}/waivers", response_model=PropertyDetail, status_code=201)
async def add_waiver(
    journey_id: uuid.UUID,
    property_id: uuid.UUID,
    body: WaiverCreate,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
) -> PropertyDetail:
    require_writer(auth)
    journey = await scoped_journey(journey_id, db, auth.workspace.id)
    prop, bp = await _scoped_property(db, journey, property_id)
    ev = await current_evaluation(db, prop, journey)
    gate = next((g for g in (ev.result["gates"] if ev else []) if g["criterion"] == body.criterion), None)
    if gate is None or gate["outcome"] == "pass":
        raise HTTPException(
            status_code=422,
            detail={
                "code": "waiver_not_applicable",
                "message": "Only a Fail or Unknown hard rule can be waived for this property.",
            },
        )
    db.add(
        GateWaiver(
            workspace_id=journey.workspace_id,
            journey_id=journey.id,
            property_id=prop.id,
            criterion=body.criterion,
            reason=body.reason.strip(),
            actor_user_id=auth.user.id,
        )
    )
    _log(
        db,
        journey,
        prop,
        auth.user.id,
        "waiver_recorded",
        f"Waived the {gate['label'].lower()} rule for this property only (gate remains {gate['outcome']})",
        {"criterion": body.criterion, "reason": body.reason.strip(), "gate_outcome": gate["outcome"]},
    )
    await db.commit()
    return await _detail(db, journey, prop, bp)


@router.delete("/properties/{property_id}/waivers/{waiver_id}", response_model=PropertyDetail)
async def revoke_waiver(
    journey_id: uuid.UUID,
    property_id: uuid.UUID,
    waiver_id: uuid.UUID,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
) -> PropertyDetail:
    require_writer(auth)
    journey = await scoped_journey(journey_id, db, auth.workspace.id)
    prop, bp = await _scoped_property(db, journey, property_id)
    waiver = (
        await db.execute(
            select(GateWaiver).where(
                GateWaiver.id == waiver_id,
                GateWaiver.property_id == prop.id,
                GateWaiver.journey_id == journey.id,
            )
        )
    ).scalar_one_or_none()
    if waiver is None:
        raise HTTPException(status_code=404, detail="Waiver not found")
    waiver.revoked_at = now_utc()
    _log(
        db,
        journey,
        prop,
        auth.user.id,
        "waiver_revoked",
        f"Revoked the waiver on {waiver.criterion}",
        {"criterion": waiver.criterion},
    )
    await db.commit()
    return await _detail(db, journey, prop, bp)


@router.post("/properties/{property_id}/notes", response_model=PropertyDetail, status_code=201)
async def add_note(
    journey_id: uuid.UUID,
    property_id: uuid.UUID,
    body: NoteCreate,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
) -> PropertyDetail:
    require_writer(auth)
    journey = await scoped_journey(journey_id, db, auth.workspace.id)
    prop, bp = await _scoped_property(db, journey, property_id)
    db.add(
        PropertyNote(
            workspace_id=journey.workspace_id,
            journey_id=journey.id,
            property_id=prop.id,
            body=body.body.strip(),
            author_user_id=auth.user.id,
        )
    )
    _log(db, journey, prop, auth.user.id, "note_added", "Added a note")
    await db.commit()
    return await _detail(db, journey, prop, bp)


@router.patch("/properties/{property_id}/notes/{note_id}", response_model=PropertyDetail)
async def edit_note(
    journey_id: uuid.UUID,
    property_id: uuid.UUID,
    note_id: uuid.UUID,
    body: NoteUpdate,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
) -> PropertyDetail:
    require_writer(auth)
    journey = await scoped_journey(journey_id, db, auth.workspace.id)
    prop, bp = await _scoped_property(db, journey, property_id)
    note = (
        await db.execute(
            select(PropertyNote).where(
                PropertyNote.id == note_id,
                PropertyNote.property_id == prop.id,
                PropertyNote.journey_id == journey.id,
            )
        )
    ).scalar_one_or_none()
    if note is None:
        raise HTTPException(status_code=404, detail="Note not found")
    check_row_version(note.row_version, body.expected_row_version, "note")
    note.body = body.body.strip()
    note.row_version += 1
    _log(db, journey, prop, auth.user.id, "note_edited", "Edited a note")
    await db.commit()
    return await _detail(db, journey, prop, bp)


@router.post("/properties/{property_id}/tasks", response_model=PropertyDetail, status_code=201)
async def add_task(
    journey_id: uuid.UUID,
    property_id: uuid.UUID,
    body: TaskCreate,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
) -> PropertyDetail:
    require_writer(auth)
    journey = await scoped_journey(journey_id, db, auth.workspace.id)
    prop, bp = await _scoped_property(db, journey, property_id)
    db.add(
        PropertyTask(
            workspace_id=journey.workspace_id,
            journey_id=journey.id,
            property_id=prop.id,
            title=body.title.strip(),
            status="open",
            created_by=auth.user.id,
        )
    )
    _log(db, journey, prop, auth.user.id, "task_added", f"Added task: {body.title.strip()}")
    await db.commit()
    return await _detail(db, journey, prop, bp)


@router.patch("/properties/{property_id}/tasks/{task_id}", response_model=PropertyDetail)
async def update_task(
    journey_id: uuid.UUID,
    property_id: uuid.UUID,
    task_id: uuid.UUID,
    body: TaskUpdate,
    auth: AuthContext = Depends(get_auth),
    db: AsyncSession = Depends(get_db),
) -> PropertyDetail:
    require_writer(auth)
    journey = await scoped_journey(journey_id, db, auth.workspace.id)
    prop, bp = await _scoped_property(db, journey, property_id)
    task = (
        await db.execute(
            select(PropertyTask).where(
                PropertyTask.id == task_id,
                PropertyTask.property_id == prop.id,
                PropertyTask.journey_id == journey.id,
            )
        )
    ).scalar_one_or_none()
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    check_row_version(task.row_version, body.expected_row_version, "task")
    task.done = body.done
    task.done_at = now_utc() if body.done else None
    task.status = "completed" if body.done else "open"
    task.row_version += 1
    _log(
        db,
        journey,
        prop,
        auth.user.id,
        "task_done" if body.done else "task_reopened",
        f"{'Completed' if body.done else 'Reopened'} task: {task.title}",
    )
    await db.commit()
    return await _detail(db, journey, prop, bp)


@router.get("/activity", response_model=list[ActivityOut])
async def journey_activity(
    journey_id: uuid.UUID, auth: AuthContext = Depends(get_auth), db: AsyncSession = Depends(get_db)
) -> list[ActivityOut]:
    journey = await scoped_journey(journey_id, db, auth.workspace.id)
    rows = (
        (
            await db.execute(
                select(ActivityEvent)
                .where(ActivityEvent.journey_id == journey.id)
                .order_by(ActivityEvent.created_at.desc())
                .limit(100)
            )
        )
        .scalars()
        .all()
    )
    return _activity_out(list(rows), await _emails(db, {r.actor_user_id for r in rows}))
