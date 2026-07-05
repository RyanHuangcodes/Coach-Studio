from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DbSession

from app.database import get_db
from app.models import Draft, Plan, User
from app.schemas import DraftCreate, DraftOut, PlanOut
from app.security import get_current_user
from app.sports import InvalidSportError, resolve_sport

router = APIRouter(prefix="/api/drafts", tags=["drafts"])


def _get_owned_draft(db: DbSession, draft_id: str, current_user: User) -> Draft:
    draft = db.query(Draft).filter(Draft.id == draft_id, Draft.user_id == current_user.id).first()
    if draft is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found")
    return draft


def _resolve_sport_or_422(sport: str, custom_sport: Optional[str]) -> str:
    try:
        return resolve_sport(sport, custom_sport)
    except InvalidSportError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc


@router.get("", response_model=list[DraftOut])
def list_drafts(
    current_user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    return (
        db.query(Draft)
        .filter(Draft.user_id == current_user.id)
        .order_by(Draft.updated_at.desc())
        .all()
    )


@router.post("", response_model=DraftOut, status_code=status.HTTP_201_CREATED)
def create_draft(
    payload: DraftCreate,
    current_user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    sport = _resolve_sport_or_422(payload.sport, payload.custom_sport)
    draft = Draft(user_id=current_user.id, sport=sport, duration_minutes=payload.duration_minutes)
    db.add(draft)
    db.commit()
    db.refresh(draft)
    return draft


@router.patch("/{draft_id}", response_model=DraftOut)
def update_draft(
    draft_id: str,
    payload: DraftCreate,
    current_user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    draft = _get_owned_draft(db, draft_id, current_user)
    draft.sport = _resolve_sport_or_422(payload.sport, payload.custom_sport)
    draft.duration_minutes = payload.duration_minutes
    db.commit()
    db.refresh(draft)
    return draft


@router.post("/{draft_id}/promote", response_model=PlanOut, status_code=status.HTTP_201_CREATED)
def promote_draft(
    draft_id: str,
    payload: DraftCreate,
    current_user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    draft = _get_owned_draft(db, draft_id, current_user)
    sport = _resolve_sport_or_422(payload.sport, payload.custom_sport)

    plan = Plan(
        user_id=current_user.id,
        sport=sport,
        duration_minutes=payload.duration_minutes,
        source_draft_id=draft.id,
    )
    db.add(plan)
    db.delete(draft)
    db.commit()
    db.refresh(plan)
    return plan


@router.delete("/{draft_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_draft(
    draft_id: str,
    current_user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    draft = _get_owned_draft(db, draft_id, current_user)
    db.delete(draft)
    db.commit()
