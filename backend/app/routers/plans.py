from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DbSession

from app.database import get_db
from app.models import Draft, Plan, User
from app.schemas import PlanCreate, PlanOut
from app.security import get_current_user
from app.sports import InvalidSportError, resolve_sport

router = APIRouter(prefix="/api/plans", tags=["plans"])


@router.get("", response_model=list[PlanOut])
def list_plans(
    current_user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    return (
        db.query(Plan)
        .filter(Plan.user_id == current_user.id)
        .order_by(Plan.created_at.desc())
        .all()
    )


@router.post("", response_model=PlanOut, status_code=status.HTTP_201_CREATED)
def create_plan(
    payload: PlanCreate,
    current_user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    try:
        sport = resolve_sport(payload.sport, payload.custom_sport)
    except InvalidSportError as exc:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc)) from exc

    source_draft = None
    if payload.source_draft_id is not None:
        source_draft = (
            db.query(Draft)
            .filter(Draft.id == payload.source_draft_id, Draft.user_id == current_user.id)
            .first()
        )
        if source_draft is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Draft not found")

    plan = Plan(
        user_id=current_user.id,
        sport=sport,
        duration_minutes=payload.duration_minutes,
        source_draft_id=source_draft.id if source_draft else None,
    )
    db.add(plan)

    if source_draft is not None:
        db.delete(source_draft)

    db.commit()
    db.refresh(plan)
    return plan
