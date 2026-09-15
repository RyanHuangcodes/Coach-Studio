from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session as DbSession

from app.database import get_db
from app.models import Drill, Plan, User
from app.schemas import DrillCreate, DrillMove, DrillOut
from app.security import get_current_user

router = APIRouter(prefix="/api", tags=["drills"])


def _get_owned_plan(db: DbSession, plan_id: str, current_user: User) -> Plan:
    plan = db.query(Plan).filter(Plan.id == plan_id, Plan.user_id == current_user.id).first()
    if plan is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Plan not found")
    return plan


def _get_owned_drill(db: DbSession, drill_id: str, current_user: User) -> Drill:
    drill = (
        db.query(Drill)
        .join(Plan, Plan.id == Drill.plan_id)
        .filter(Drill.id == drill_id, Plan.user_id == current_user.id)
        .first()
    )
    if drill is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Drill not found")
    return drill


@router.get("/plans/{plan_id}/drills", response_model=list[DrillOut])
def list_drills(
    plan_id: str,
    current_user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    plan = _get_owned_plan(db, plan_id, current_user)
    return (
        db.query(Drill)
        .filter(Drill.plan_id == plan.id)
        .order_by(Drill.position.asc())
        .all()
    )


@router.post("/plans/{plan_id}/drills", response_model=DrillOut, status_code=status.HTTP_201_CREATED)
def create_drill(
    plan_id: str,
    payload: DrillCreate,
    current_user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    plan = _get_owned_plan(db, plan_id, current_user)
    max_position = db.query(func.max(Drill.position)).filter(Drill.plan_id == plan.id).scalar()
    drill = Drill(
        plan_id=plan.id,
        name=payload.name,
        duration_minutes=payload.duration_minutes,
        repeats=payload.repeats,
        groups=payload.groups,
        notes=payload.notes,
        position=(max_position + 1) if max_position is not None else 1,
    )
    db.add(drill)
    db.commit()
    db.refresh(drill)
    return drill


@router.patch("/drills/{drill_id}", response_model=DrillOut)
def update_drill(
    drill_id: str,
    payload: DrillCreate,
    current_user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    drill = _get_owned_drill(db, drill_id, current_user)
    drill.name = payload.name
    drill.duration_minutes = payload.duration_minutes
    drill.repeats = payload.repeats
    drill.groups = payload.groups
    drill.notes = payload.notes
    db.commit()
    db.refresh(drill)
    return drill


@router.post("/drills/{drill_id}/move", status_code=status.HTTP_204_NO_CONTENT)
def move_drill(
    drill_id: str,
    payload: DrillMove,
    current_user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    drill = _get_owned_drill(db, drill_id, current_user)
    plan_drills = (
        db.query(Drill)
        .filter(Drill.plan_id == drill.plan_id)
        .order_by(Drill.position.asc())
        .all()
    )
    index = next(i for i, d in enumerate(plan_drills) if d.id == drill.id)
    neighbor_index = index - 1 if payload.direction == "up" else index + 1
    if 0 <= neighbor_index < len(plan_drills):
        neighbor = plan_drills[neighbor_index]
        drill.position, neighbor.position = neighbor.position, drill.position
        db.commit()


@router.delete("/drills/{drill_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_drill(
    drill_id: str,
    current_user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    drill = _get_owned_drill(db, drill_id, current_user)
    db.delete(drill)
    db.commit()
