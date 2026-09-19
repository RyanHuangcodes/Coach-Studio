from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import func
from sqlalchemy.orm import Session as DbSession

from app.database import get_db
from app.models import Player, Roster, RosterPlayer, Tier, User
from app.rate_limit import limiter
from app.schemas import (
    PlayerCreate,
    PlayerMove,
    PlayerOut,
    RosterImageRequest,
    RosterImageResponse,
)
from app.security import get_current_user
from app.vision import extract_roster_names

router = APIRouter(prefix="/api/players", tags=["players"])


def _validate_tier(db: DbSession, tier_id: Optional[str], current_user: User) -> None:
    if tier_id is None:
        return
    tier = db.query(Tier).filter(Tier.id == tier_id, Tier.user_id == current_user.id).first()
    if tier is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unknown tier_id")


def _validate_roster(db: DbSession, roster_id: Optional[str], current_user: User) -> None:
    if roster_id is None:
        return
    roster = db.query(Roster).filter(Roster.id == roster_id, Roster.user_id == current_user.id).first()
    if roster is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Unknown roster_id")


def _get_owned_player(db: DbSession, player_id: str, current_user: User) -> Player:
    player = db.query(Player).filter(Player.id == player_id, Player.user_id == current_user.id).first()
    if player is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Player not found")
    return player


def _next_rank_in_tier(db: DbSession, user_id: str, tier_id: str) -> int:
    max_rank = (
        db.query(func.max(Player.rank))
        .filter(Player.user_id == user_id, Player.tier_id == tier_id)
        .scalar()
    )
    return (max_rank + 1) if max_rank is not None else 1


@router.get("", response_model=list[PlayerOut])
def list_players(
    roster_id: Optional[str] = None,
    current_user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    query = db.query(Player).filter(Player.user_id == current_user.id)
    if roster_id is not None:
        query = query.join(RosterPlayer, RosterPlayer.player_id == Player.id).filter(
            RosterPlayer.roster_id == roster_id
        )
    return query.order_by(Player.rank.is_(None), Player.rank.asc(), Player.name.asc()).all()


@router.post("", response_model=PlayerOut, status_code=status.HTTP_201_CREATED)
def create_player(
    payload: PlayerCreate,
    current_user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    _validate_tier(db, payload.tier_id, current_user)
    _validate_roster(db, payload.roster_id, current_user)
    rank = _next_rank_in_tier(db, current_user.id, payload.tier_id) if payload.tier_id else None
    player = Player(
        user_id=current_user.id,
        name=payload.name,
        tier_id=payload.tier_id,
        rank=rank,
        notes=payload.notes,
    )
    db.add(player)
    db.flush()
    # New players join the active roster they were created from, so they show up
    # immediately in the roster the coach is looking at.
    if payload.roster_id is not None:
        db.add(RosterPlayer(roster_id=payload.roster_id, player_id=player.id))
    db.commit()
    db.refresh(player)
    return player


@router.post("/extract-image", response_model=RosterImageResponse)
@limiter.limit("15/hour")
def extract_players_from_image(
    payload: RosterImageRequest,
    request: Request,
    current_user: User = Depends(get_current_user),
):
    # The image is processed for name extraction and never stored server-side.
    names = extract_roster_names(payload.image_base64, payload.media_type)
    return RosterImageResponse(names=names)


@router.patch("/{player_id}", response_model=PlayerOut)
def update_player(
    player_id: str,
    payload: PlayerCreate,
    current_user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    player = _get_owned_player(db, player_id, current_user)
    _validate_tier(db, payload.tier_id, current_user)

    if payload.tier_id != player.tier_id:
        player.rank = _next_rank_in_tier(db, current_user.id, payload.tier_id) if payload.tier_id else None

    player.name = payload.name
    player.tier_id = payload.tier_id
    player.notes = payload.notes
    db.commit()
    db.refresh(player)
    return player


@router.post("/{player_id}/move", status_code=status.HTTP_204_NO_CONTENT)
def move_player(
    player_id: str,
    payload: PlayerMove,
    current_user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    player = _get_owned_player(db, player_id, current_user)
    if player.tier_id is None:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Player has no tier to rank within",
        )

    tier_players = (
        db.query(Player)
        .filter(Player.user_id == current_user.id, Player.tier_id == player.tier_id)
        .order_by(Player.rank.asc())
        .all()
    )
    index = next(i for i, p in enumerate(tier_players) if p.id == player.id)

    neighbor_index = index - 1 if payload.direction == "up" else index + 1
    if 0 <= neighbor_index < len(tier_players):
        neighbor = tier_players[neighbor_index]
        player.rank, neighbor.rank = neighbor.rank, player.rank
        db.commit()


@router.delete("/{player_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_player(
    player_id: str,
    current_user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    player = _get_owned_player(db, player_id, current_user)
    db.delete(player)
    db.commit()
