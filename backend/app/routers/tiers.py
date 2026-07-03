from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session as DbSession

from app.database import get_db
from app.models import Tier, User
from app.schemas import TierCreate, TierOut
from app.security import get_current_user

router = APIRouter(prefix="/api/tiers", tags=["tiers"])


def _get_owned_tier(db: DbSession, tier_id: str, current_user: User) -> Tier:
    tier = db.query(Tier).filter(Tier.id == tier_id, Tier.user_id == current_user.id).first()
    if tier is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tier not found")
    return tier


@router.get("", response_model=list[TierOut])
def list_tiers(
    current_user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    return (
        db.query(Tier)
        .filter(Tier.user_id == current_user.id)
        .order_by(Tier.sort_order.asc())
        .all()
    )


@router.post("", response_model=TierOut, status_code=status.HTTP_201_CREATED)
def create_tier(
    payload: TierCreate,
    current_user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    max_sort_order = (
        db.query(func.max(Tier.sort_order)).filter(Tier.user_id == current_user.id).scalar()
    )
    tier = Tier(
        user_id=current_user.id,
        name=payload.name,
        sort_order=(max_sort_order + 1) if max_sort_order is not None else 0,
    )
    db.add(tier)
    db.commit()
    db.refresh(tier)
    return tier


@router.patch("/{tier_id}", response_model=TierOut)
def rename_tier(
    tier_id: str,
    payload: TierCreate,
    current_user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    tier = _get_owned_tier(db, tier_id, current_user)
    tier.name = payload.name
    db.commit()
    db.refresh(tier)
    return tier


@router.delete("/{tier_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_tier(
    tier_id: str,
    current_user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    tier = _get_owned_tier(db, tier_id, current_user)
    db.delete(tier)
    db.commit()
