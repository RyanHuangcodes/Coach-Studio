from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session as DbSession

from app.database import get_db
from app.models import Assignment, Drill, Feedback, Message, Plan, Player, User
from app.schemas import (
    AssignmentCreate,
    AssignmentDoneUpdate,
    AssignmentOut,
    CommsUnreadOut,
    FeedbackCreate,
    FeedbackOut,
    MeProfileOut,
    MeTrainingDrill,
    MeTrainingOut,
    MeUnreadOut,
    MessageCreate,
    MessageOut,
)
from app.routers.push import push_to_user
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
        due_date=payload.due_date,
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


@router.get("/players/{player_id}/feedback", response_model=list[FeedbackOut])
def list_feedback(
    player_id: str,
    current_user: User = Depends(get_current_coach),
    db: DbSession = Depends(get_db),
):
    player = _owned_player(db, player_id, current_user)
    return (
        db.query(Feedback)
        .filter(Feedback.player_id == player.id)
        .order_by(Feedback.created_at.desc())
        .all()
    )


@router.post("/players/{player_id}/feedback", response_model=FeedbackOut, status_code=status.HTTP_201_CREATED)
def create_feedback(
    player_id: str,
    payload: FeedbackCreate,
    current_user: User = Depends(get_current_coach),
    db: DbSession = Depends(get_db),
):
    player = _owned_player(db, player_id, current_user)
    feedback = Feedback(
        coach_id=current_user.id,
        player_id=player.id,
        session_label=payload.session_label,
        body=payload.body,
    )
    db.add(feedback)
    db.commit()
    db.refresh(feedback)
    if player.login_user_id:
        push_to_user(db, player.login_user_id, title=current_user.display_name + " left feedback", body=payload.body, url="/")
    return feedback


@router.delete("/players/{player_id}/feedback/{feedback_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_feedback(
    player_id: str,
    feedback_id: str,
    current_user: User = Depends(get_current_coach),
    db: DbSession = Depends(get_db),
):
    player = _owned_player(db, player_id, current_user)
    db.query(Feedback).filter(
        Feedback.id == feedback_id, Feedback.player_id == player.id
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
    if player.login_user_id:
        push_to_user(db, player.login_user_id, title=current_user.display_name, body=payload.body, url="/")
    return message


@router.post("/players/{player_id}/messages/read", status_code=status.HTTP_204_NO_CONTENT)
def mark_thread_read_coach(
    player_id: str,
    current_user: User = Depends(get_current_coach),
    db: DbSession = Depends(get_db),
):
    player = _owned_player(db, player_id, current_user)
    player.coach_last_read_at = datetime.now(timezone.utc)
    db.commit()


@router.get("/comms/unread", response_model=CommsUnreadOut)
def coach_unread(
    current_user: User = Depends(get_current_coach),
    db: DbSession = Depends(get_db),
):
    """Per-player unread counts (messages the player sent since the coach last
    opened that thread), plus the total for the chat-bubble badge."""
    players = db.query(Player).filter(Player.user_id == current_user.id).all()
    by_player: dict[str, int] = {}
    total = 0
    for player in players:
        query = db.query(func.count(Message.id)).filter(
            Message.player_id == player.id, Message.sender_role == "player"
        )
        if player.coach_last_read_at is not None:
            query = query.filter(Message.created_at > player.coach_last_read_at)
        count = query.scalar() or 0
        if count:
            by_player[player.id] = count
            total += count
    return CommsUnreadOut(total=total, by_player=by_player)


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


@router.get("/me/feedback", response_model=list[FeedbackOut])
def my_feedback(
    player: Player = Depends(get_current_player),
    db: DbSession = Depends(get_db),
):
    return (
        db.query(Feedback)
        .filter(Feedback.player_id == player.id)
        .order_by(Feedback.created_at.desc())
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
    push_to_user(db, player.user_id, title=player.name, body=payload.body, url="/#comms")
    return message


@router.post("/me/messages/read", status_code=status.HTTP_204_NO_CONTENT)
def my_mark_read(
    player: Player = Depends(get_current_player),
    db: DbSession = Depends(get_db),
):
    player.player_last_read_at = datetime.now(timezone.utc)
    db.commit()


@router.get("/me/unread", response_model=MeUnreadOut)
def my_unread(
    player: Player = Depends(get_current_player),
    db: DbSession = Depends(get_db),
):
    query = db.query(func.count(Message.id)).filter(
        Message.player_id == player.id, Message.sender_role == "coach"
    )
    if player.player_last_read_at is not None:
        query = query.filter(Message.created_at > player.player_last_read_at)
    return MeUnreadOut(count=query.scalar() or 0)


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
