from datetime import date as date_type
from datetime import datetime, timedelta, timezone
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session as DbSession

from app.database import get_db
from app.models import AttendanceRecord, Player, Practice, Roster, User
from app.schemas import AttendanceCheckIn, AttendanceOut, PracticeOut, TodayPracticeRequest
from app.security import get_current_user

router = APIRouter(prefix="/api/practices", tags=["practices"])


def _get_owned_practice(db: DbSession, practice_id: str, current_user: User) -> Practice:
    practice = (
        db.query(Practice)
        .filter(Practice.id == practice_id, Practice.user_id == current_user.id)
        .first()
    )
    if practice is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Practice not found")
    return practice


def get_or_create_today_practice_row(
    db: DbSession,
    user_id: str,
    local_date: Optional[date_type] = None,
    roster_id: Optional[str] = None,
) -> Practice:
    # Coaches live in local time; the browser supplies its local date so evening
    # sessions don't roll onto tomorrow's UTC date. Server-side callers (group
    # generation, AI context) fall back to UTC. A supplied date more than a day
    # away from UTC-now is rejected as clock tampering.
    utc_today = datetime.now(timezone.utc).date()
    today = local_date or utc_today
    if abs(today - utc_today) > timedelta(days=1):
        today = utc_today

    # Sessions are scoped per roster so a coach can run a team practice and a
    # private lesson on the same day without them sharing one attendance sheet.
    practice = (
        db.query(Practice)
        .filter(
            Practice.user_id == user_id,
            Practice.date == today,
            Practice.roster_id == roster_id,
        )
        .first()
    )
    if practice is not None:
        return practice

    practice = Practice(user_id=user_id, date=today, roster_id=roster_id)
    db.add(practice)
    try:
        db.commit()
    except IntegrityError:
        # A concurrent request created the same (user, date, roster) row first.
        db.rollback()
        practice = (
            db.query(Practice)
            .filter(
                Practice.user_id == user_id,
                Practice.date == today,
                Practice.roster_id == roster_id,
            )
            .first()
        )
        if practice is None:
            raise
        return practice
    db.refresh(practice)
    return practice


@router.get("", response_model=list[PracticeOut])
def list_practices(
    current_user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    return (
        db.query(Practice)
        .filter(Practice.user_id == current_user.id)
        .order_by(Practice.date.desc())
        .all()
    )


@router.post("/today", response_model=PracticeOut, status_code=status.HTTP_200_OK)
def get_or_create_today_practice(
    payload: Optional[TodayPracticeRequest] = None,
    current_user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    local_date = payload.date if payload else None
    roster_id = payload.roster_id if payload else None
    if roster_id is not None:
        roster = (
            db.query(Roster)
            .filter(Roster.id == roster_id, Roster.user_id == current_user.id)
            .first()
        )
        if roster is None:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unknown roster_id"
            )
    return get_or_create_today_practice_row(db, current_user.id, local_date, roster_id)


@router.get("/{practice_id}/attendance", response_model=list[AttendanceOut])
def list_attendance(
    practice_id: str,
    current_user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    practice = _get_owned_practice(db, practice_id, current_user)
    return db.query(AttendanceRecord).filter(AttendanceRecord.practice_id == practice.id).all()


@router.post(
    "/{practice_id}/attendance",
    response_model=AttendanceOut,
    status_code=status.HTTP_201_CREATED,
)
def check_in(
    practice_id: str,
    payload: AttendanceCheckIn,
    current_user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    practice = _get_owned_practice(db, practice_id, current_user)
    player = (
        db.query(Player)
        .filter(Player.id == payload.player_id, Player.user_id == current_user.id)
        .first()
    )
    if player is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Player not found")

    existing = (
        db.query(AttendanceRecord)
        .filter(AttendanceRecord.practice_id == practice.id, AttendanceRecord.player_id == player.id)
        .first()
    )
    if existing is not None:
        return existing

    record = AttendanceRecord(practice_id=practice.id, player_id=player.id)
    db.add(record)
    db.commit()
    db.refresh(record)
    return record


@router.delete(
    "/{practice_id}/attendance/{player_id}",
    status_code=status.HTTP_204_NO_CONTENT,
)
def check_out(
    practice_id: str,
    player_id: str,
    current_user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    practice = _get_owned_practice(db, practice_id, current_user)
    db.query(AttendanceRecord).filter(
        AttendanceRecord.practice_id == practice.id,
        AttendanceRecord.player_id == player_id,
    ).delete()
    db.commit()
