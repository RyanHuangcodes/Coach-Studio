from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DbSession

from app.database import get_db
from app.models import (
    AttendanceRecord,
    CompletedSession,
    CompletedSessionDrill,
    CompletedSessionPlayer,
    Drill,
    Plan,
    Player,
    Practice,
    Tier,
    User,
)
from app.routers.practices import get_or_create_today_practice_row
from app.schemas import HistoryCreate, HistoryDetail, HistoryListItem
from app.security import get_current_user

router = APIRouter(prefix="/api/history", tags=["history"])


def _get_owned_session(db: DbSession, session_id: str, current_user: User) -> CompletedSession:
    session = (
        db.query(CompletedSession)
        .filter(CompletedSession.id == session_id, CompletedSession.user_id == current_user.id)
        .first()
    )
    if session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="History entry not found")
    return session


@router.get("", response_model=list[HistoryListItem])
def list_history(
    current_user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    sessions = (
        db.query(CompletedSession)
        .filter(CompletedSession.user_id == current_user.id)
        .order_by(CompletedSession.completed_at.desc())
        .all()
    )
    return [
        HistoryListItem(
            id=s.id,
            sport=s.sport,
            date=s.date,
            completed_at=s.completed_at,
            player_count=len(s.players),
            drill_count=len(s.drills),
        )
        for s in sessions
    ]


@router.get("/{session_id}", response_model=HistoryDetail)
def get_history(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    session = _get_owned_session(db, session_id, current_user)
    session.drills.sort(key=lambda d: d.position)
    session.players.sort(key=lambda p: p.player_name.lower())
    return session


@router.post("", response_model=HistoryDetail, status_code=status.HTTP_201_CREATED)
def complete_session(
    payload: HistoryCreate,
    current_user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    # Resolve the plan (optional — a freestyle session can still be logged).
    plan = None
    if payload.plan_id is not None:
        plan = (
            db.query(Plan)
            .filter(Plan.id == payload.plan_id, Plan.user_id == current_user.id)
            .first()
        )
        if plan is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")

    # Resolve the practice whose attendance we snapshot (defaults to today).
    if payload.practice_id is not None:
        practice = (
            db.query(Practice)
            .filter(Practice.id == payload.practice_id, Practice.user_id == current_user.id)
            .first()
        )
        if practice is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Practice not found")
    else:
        practice = get_or_create_today_practice_row(db, current_user.id)

    # History label prefers the coach-given session name; column is String(60).
    sport = (plan.name or plan.sport)[:60] if plan is not None else "Session"

    session = CompletedSession(
        user_id=current_user.id,
        plan_id=plan.id if plan is not None else None,
        sport=sport,
        date=practice.date,
    )
    db.add(session)
    db.flush()

    # Snapshot the checked-in players (name + tier), so later roster edits don't
    # rewrite this record.
    checked_in_ids = [
        row.player_id
        for row in db.query(AttendanceRecord.player_id)
        .filter(AttendanceRecord.practice_id == practice.id)
        .all()
    ]
    if checked_in_ids:
        tiers_by_id = {
            t.id: t.name for t in db.query(Tier).filter(Tier.user_id == current_user.id).all()
        }
        players = (
            db.query(Player)
            .filter(Player.user_id == current_user.id, Player.id.in_(checked_in_ids))
            .all()
        )
        for player in players:
            db.add(
                CompletedSessionPlayer(
                    session_id=session.id,
                    player_name=player.name,
                    tier_name=tiers_by_id.get(player.tier_id) if player.tier_id else None,
                )
            )

    # Snapshot the plan's drills.
    if plan is not None:
        drills = db.query(Drill).filter(Drill.plan_id == plan.id).order_by(Drill.position).all()
        for drill in drills:
            db.add(
                CompletedSessionDrill(
                    session_id=session.id,
                    name=drill.name,
                    duration_minutes=drill.duration_minutes,
                    repeats=drill.repeats,
                    notes=drill.notes,
                    position=drill.position,
                )
            )

    # The lesson is now fully captured in history (drills + attendance are
    # snapshotted above), so remove the plan — its drills cascade — and it drops
    # out of Plans, living on only under Completed.
    if plan is not None:
        db.delete(plan)

    db.commit()
    db.refresh(session)
    session.drills.sort(key=lambda d: d.position)
    session.players.sort(key=lambda p: p.player_name.lower())
    return session


@router.delete("/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_history(
    session_id: str,
    current_user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    session = _get_owned_session(db, session_id, current_user)
    db.delete(session)
    db.commit()
