from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session as DbSession

from app.database import get_db
from app.models import Player, Roster, RosterPlayer, User
from app.schemas import (
    PlayerOut,
    RosterCreate,
    RosterMembersAdd,
    RosterOut,
    RosterUpdate,
)
from app.security import get_current_user

router = APIRouter(prefix="/api/rosters", tags=["rosters"])


def _get_owned_roster(db: DbSession, roster_id: str, current_user: User) -> Roster:
    roster = (
        db.query(Roster)
        .filter(Roster.id == roster_id, Roster.user_id == current_user.id)
        .first()
    )
    if roster is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Roster not found")
    return roster


def _roster_out(roster: Roster, player_count: int) -> RosterOut:
    return RosterOut(
        id=roster.id,
        name=roster.name,
        kind=roster.kind,
        sort_order=roster.sort_order,
        player_count=player_count,
    )


@router.get("", response_model=list[RosterOut])
def list_rosters(
    current_user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    rows = (
        db.query(Roster, func.count(RosterPlayer.id))
        .outerjoin(RosterPlayer, RosterPlayer.roster_id == Roster.id)
        .filter(Roster.user_id == current_user.id)
        .group_by(Roster.id)
        .order_by(Roster.sort_order.asc(), Roster.created_at.asc())
        .all()
    )
    return [_roster_out(roster, count) for roster, count in rows]


@router.post("", response_model=RosterOut, status_code=status.HTTP_201_CREATED)
def create_roster(
    payload: RosterCreate,
    current_user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    max_order = (
        db.query(func.max(Roster.sort_order)).filter(Roster.user_id == current_user.id).scalar()
    )
    roster = Roster(
        user_id=current_user.id,
        name=payload.name,
        kind=payload.kind,
        sort_order=(max_order + 1) if max_order is not None else 0,
    )
    db.add(roster)
    db.commit()
    db.refresh(roster)
    return _roster_out(roster, 0)


@router.patch("/{roster_id}", response_model=RosterOut)
def update_roster(
    roster_id: str,
    payload: RosterUpdate,
    current_user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    roster = _get_owned_roster(db, roster_id, current_user)
    if payload.name is not None:
        roster.name = payload.name
    if payload.kind is not None:
        roster.kind = payload.kind
    db.commit()
    db.refresh(roster)
    count = (
        db.query(func.count(RosterPlayer.id))
        .filter(RosterPlayer.roster_id == roster.id)
        .scalar()
    )
    return _roster_out(roster, count or 0)


@router.delete("/{roster_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_roster(
    roster_id: str,
    current_user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    roster = _get_owned_roster(db, roster_id, current_user)
    # Deleting a roster removes memberships (cascade) but never the players.
    db.delete(roster)
    db.commit()


@router.get("/{roster_id}/players", response_model=list[PlayerOut])
def list_roster_players(
    roster_id: str,
    current_user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    roster = _get_owned_roster(db, roster_id, current_user)
    return (
        db.query(Player)
        .join(RosterPlayer, RosterPlayer.player_id == Player.id)
        .filter(RosterPlayer.roster_id == roster.id, Player.user_id == current_user.id)
        .order_by(Player.rank.is_(None), Player.rank.asc(), Player.name.asc())
        .all()
    )


@router.post("/{roster_id}/players", status_code=status.HTTP_204_NO_CONTENT)
def add_roster_players(
    roster_id: str,
    payload: RosterMembersAdd,
    current_user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    roster = _get_owned_roster(db, roster_id, current_user)

    requested = list(dict.fromkeys(payload.player_ids))  # de-dupe, keep order
    owned_ids = {
        row.id
        for row in db.query(Player.id)
        .filter(Player.user_id == current_user.id, Player.id.in_(requested))
        .all()
    }
    unknown = [pid for pid in requested if pid not in owned_ids]
    if unknown:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="One or more player ids are unknown",
        )

    already = {
        row.player_id
        for row in db.query(RosterPlayer.player_id)
        .filter(RosterPlayer.roster_id == roster.id, RosterPlayer.player_id.in_(requested))
        .all()
    }
    for pid in requested:
        if pid not in already:
            db.add(RosterPlayer(roster_id=roster.id, player_id=pid))
    db.commit()


@router.delete("/{roster_id}/players/{player_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_roster_player(
    roster_id: str,
    player_id: str,
    current_user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    roster = _get_owned_roster(db, roster_id, current_user)
    db.query(RosterPlayer).filter(
        RosterPlayer.roster_id == roster.id,
        RosterPlayer.player_id == player_id,
    ).delete()
    db.commit()
