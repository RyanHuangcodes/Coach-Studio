from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DbSession

from app.database import get_db
from app.models import Assignment, Drill, Message, Plan, Player, User
from app.schemas import (
    AssignmentCreate,
    AssignmentDoneUpdate,
    AssignmentOut,
    MeProfileOut,
    MeTrainingDrill,
    MeTrainingOut,
    MessageCreate,
    MessageOut,
)
from app.security import get_current_coach, get_current_user

router = APIRouter(prefix="/api", tags=["comms"])


def _owned_player(db: DbSession, player_id: str, coach: User) -> Player:
    player = (
        db.query(Player).filter(Player.id == player_id, Player.user_id == coach.id).first()
    )
    if player is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Player not found")
    return player


def get_current_player(
    current_user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
) -> Player:
    """Guards player-only endpoints and resolves the athlete's own Player row."""
    if current_user.role != "player":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Players only")
    player = db.query(Player).filter(Player.login_user_id == current_user.id).first()
    if player is None:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, detail="No player profile is linked to this account"
        )
    return player


# ============================ Coach side ============================

@router.get("/players/{player_id}/assignments", response_model=list[AssignmentOut])
def list_assignments(
    player_id: str,
    current_user: User = Depends(get_current_coach),
    db: DbSession = Depends(get_db),
):
    player = _owned_player(db, player_id, current_user)
    return (
        db.query(Assignment)
        .filter(Assignment.player_id == player.id)
        .order_by(Assignment.created_at.asc())
        .all()
    )


@router.post("/players/{player_id}/assignments", response_model=AssignmentOut, status_code=status.HTTP_201_CREATED)
def create_assignment(
    player_id: str,
    payload: AssignmentCreate,
    current_user: User = Depends(get_current_coach),
    db: DbSession = Depends(get_db),
):
    player = _owned_player(db, player_id, current_user)
    assignment = Assignment(
        coach_id=current_user.id,
        player_id=player.id,
        category=payload.category,
        title=payload.title,
        notes=payload.notes,
    )
    db.add(assignment)
    db.commit()
    db.refresh(assignment)
    return assignment


@router.delete("/players/{player_id}/assignments/{assignment_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_assignment(
    player_id: str,
    assignment_id: str,
    current_user: User = Depends(get_current_coach),
    db: DbSession = Depends(get_db),
):
    player = _owned_player(db, player_id, current_user)
    db.query(Assignment).filter(
        Assignment.id == assignment_id, Assignment.player_id == player.id
    ).delete()
    db.commit()


@router.get("/players/{player_id}/messages", response_model=list[MessageOut])
def list_messages_coach(
    player_id: str,
    current_user: User = Depends(get_current_coach),
    db: DbSession = Depends(get_db),
):
    player = _owned_player(db, player_id, current_user)
    return (
        db.query(Message)
        .filter(Message.player_id == player.id)
        .order_by(Message.created_at.asc())
        .all()
    )


@router.post("/players/{player_id}/messages", response_model=MessageOut, status_code=status.HTTP_201_CREATED)
def send_message_coach(
    player_id: str,
    payload: MessageCreate,
    current_user: User = Depends(get_current_coach),
    db: DbSession = Depends(get_db),
):
    player = _owned_player(db, player_id, current_user)
    message = Message(player_id=player.id, sender_role="coach", body=payload.body)
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


# ============================ Player side ============================

@router.get("/me/profile", response_model=MeProfileOut)
def my_profile(
    player: Player = Depends(get_current_player),
    db: DbSession = Depends(get_db),
):
    coach = db.query(User).filter(User.id == player.user_id).first()
    return MeProfileOut(
        player_name=player.name,
        coach_name=coach.display_name if coach else "your coach",
        can_view_trainings=player.can_view_trainings,
    )


@router.get("/me/assignments", response_model=list[AssignmentOut])
def my_assignments(
    player: Player = Depends(get_current_player),
    db: DbSession = Depends(get_db),
):
    return (
        db.query(Assignment)
        .filter(Assignment.player_id == player.id)
        .order_by(Assignment.created_at.asc())
        .all()
    )


@router.patch("/me/assignments/{assignment_id}", response_model=AssignmentOut)
def my_assignment_done(
    assignment_id: str,
    payload: AssignmentDoneUpdate,
    player: Player = Depends(get_current_player),
    db: DbSession = Depends(get_db),
):
    assignment = (
        db.query(Assignment)
        .filter(Assignment.id == assignment_id, Assignment.player_id == player.id)
        .first()
    )
    if assignment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Assignment not found")
    assignment.done = payload.done
    assignment.done_at = datetime.now(timezone.utc) if payload.done else None
    db.commit()
    db.refresh(assignment)
    return assignment


@router.get("/me/messages", response_model=list[MessageOut])
def my_messages(
    player: Player = Depends(get_current_player),
    db: DbSession = Depends(get_db),
):
    return (
        db.query(Message)
        .filter(Message.player_id == player.id)
        .order_by(Message.created_at.asc())
        .all()
    )


@router.post("/me/messages", response_model=MessageOut, status_code=status.HTTP_201_CREATED)
def my_send_message(
    payload: MessageCreate,
    player: Player = Depends(get_current_player),
    db: DbSession = Depends(get_db),
):
    message = Message(player_id=player.id, sender_role="player", body=payload.body)
    db.add(message)
    db.commit()
    db.refresh(message)
    return message


@router.get("/me/trainings", response_model=list[MeTrainingOut])
def my_trainings(
    player: Player = Depends(get_current_player),
    db: DbSession = Depends(get_db),
):
    if not player.can_view_trainings:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Your coach hasn't shared trainings with you yet",
        )
    plans = (
        db.query(Plan)
        .filter(Plan.user_id == player.user_id)
        .order_by(Plan.created_at.desc())
        .all()
    )
    result = []
    for plan in plans:
        drills = db.query(Drill).filter(Drill.plan_id == plan.id).order_by(Drill.position).all()
        result.append(
            MeTrainingOut(
                id=plan.id,
                sport=plan.sport,
                name=plan.name,
                session_date=plan.session_date,
                duration_minutes=plan.duration_minutes,
                drills=[MeTrainingDrill.model_validate(d) for d in drills],
            )
        )
    return result
