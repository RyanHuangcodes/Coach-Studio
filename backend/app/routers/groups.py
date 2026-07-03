import math
import random

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DbSession

from app.database import get_db
from app.models import AttendanceRecord, Player, Practice, PracticeGroup, PracticeGroupPlayer, Tier, User
from app.routers.practices import get_or_create_today_practice_row
from app.schemas import GroupGenerateRequest, GroupGenerateResponse, GroupsSaveRequest, SavedGroupsOut
from app.security import get_current_user

router = APIRouter(prefix="/api", tags=["groups"])

_TIER_SPACING = 1000
# Rank gap between neighbors in the same tier is normally 1, so jitter must exceed
# 0.5 for a flip to ever be possible. 0.75 gives roughly a 5-6% chance per adjacent
# pair per generation — occasional variation without disrupting tier boundaries
# (a tier's minimum 1000-point gap is never bridgeable by this jitter).
_JITTER = 0.75
_UNRANKED_TIER_SORT_ORDER = -1


def _get_owned_practice(db: DbSession, practice_id: str, current_user: User) -> Practice:
    practice = (
        db.query(Practice)
        .filter(Practice.id == practice_id, Practice.user_id == current_user.id)
        .first()
    )
    if practice is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Practice not found")
    return practice


def _group_out(db: DbSession, practice: Practice, current_user: User):
    saved_groups = (
        db.query(PracticeGroup)
        .filter(PracticeGroup.practice_id == practice.id)
        .order_by(PracticeGroup.group_number.asc())
        .all()
    )
    players_by_id = {
        player.id: player
        for player in db.query(Player).filter(Player.user_id == current_user.id).all()
    }
    tiers_by_id = {tier.id: tier for tier in db.query(Tier).filter(Tier.user_id == current_user.id).all()}

    groups = []
    saved_at = None
    for group in saved_groups:
        saved_at = group.created_at
        members = (
            db.query(PracticeGroupPlayer)
            .filter(PracticeGroupPlayer.group_id == group.id)
            .all()
        )
        group_players = []
        for member in members:
            player = players_by_id.get(member.player_id)
            if player is None:
                continue
            group_players.append({
                "id": player.id,
                "name": player.name,
                "tier_name": tiers_by_id[player.tier_id].name if player.tier_id in tiers_by_id else None,
            })
        groups.append({"group_number": group.group_number, "players": group_players})

    return {"practice_id": practice.id, "saved_at": saved_at, "groups": groups}


@router.post("/groups/generate", response_model=GroupGenerateResponse)
def generate_groups(
    payload: GroupGenerateRequest,
    current_user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    if payload.practice_id is not None:
        practice = _get_owned_practice(db, payload.practice_id, current_user)
    else:
        practice = get_or_create_today_practice_row(db, current_user.id)

    checked_in_ids = [
        row.player_id
        for row in db.query(AttendanceRecord.player_id)
        .filter(AttendanceRecord.practice_id == practice.id)
        .all()
    ]
    if not checked_in_ids:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No players checked in for this practice yet",
        )

    players = (
        db.query(Player)
        .filter(Player.user_id == current_user.id, Player.id.in_(checked_in_ids))
        .all()
    )
    tiers_by_id = {tier.id: tier for tier in db.query(Tier).filter(Tier.user_id == current_user.id).all()}

    def skill_score(player: Player) -> float:
        tier = tiers_by_id.get(player.tier_id) if player.tier_id else None
        tier_sort_order = tier.sort_order if tier is not None else _UNRANKED_TIER_SORT_ORDER
        rank = player.rank if player.rank is not None else 0
        base_score = tier_sort_order * _TIER_SPACING - rank
        return base_score + random.uniform(-_JITTER, _JITTER)

    ranked_players = sorted(players, key=skill_score, reverse=True)
    player_count = len(ranked_players)

    if payload.num_groups is not None:
        group_count = payload.num_groups
    else:
        group_count = math.ceil(player_count / payload.group_size)
    group_count = max(1, min(group_count, player_count))

    base_size, remainder = divmod(player_count, group_count)
    groups = []
    cursor = 0
    for group_number in range(1, group_count + 1):
        size = base_size + (1 if group_number <= remainder else 0)
        chunk = ranked_players[cursor:cursor + size]
        cursor += size
        groups.append({
            "group_number": group_number,
            "players": [
                {
                    "id": player.id,
                    "name": player.name,
                    "tier_name": tiers_by_id[player.tier_id].name if player.tier_id in tiers_by_id else None,
                }
                for player in chunk
            ],
        })

    return {"groups": groups}


@router.get("/practices/{practice_id}/groups", response_model=SavedGroupsOut)
def get_saved_groups(
    practice_id: str,
    current_user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    practice = _get_owned_practice(db, practice_id, current_user)
    return _group_out(db, practice, current_user)


@router.put("/practices/{practice_id}/groups", response_model=SavedGroupsOut)
def save_groups(
    practice_id: str,
    payload: GroupsSaveRequest,
    current_user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    practice = _get_owned_practice(db, practice_id, current_user)

    all_player_ids = [pid for group in payload.groups for pid in group]
    owned_count = (
        db.query(Player)
        .filter(Player.user_id == current_user.id, Player.id.in_(all_player_ids))
        .count()
    )
    if owned_count != len(all_player_ids):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="One or more player ids are unknown",
        )

    existing_group_ids = [
        row.id
        for row in db.query(PracticeGroup.id).filter(PracticeGroup.practice_id == practice.id).all()
    ]
    if existing_group_ids:
        db.query(PracticeGroupPlayer).filter(
            PracticeGroupPlayer.group_id.in_(existing_group_ids)
        ).delete(synchronize_session=False)
        db.query(PracticeGroup).filter(PracticeGroup.practice_id == practice.id).delete(
            synchronize_session=False
        )

    for group_number, player_ids in enumerate(payload.groups, start=1):
        group = PracticeGroup(practice_id=practice.id, group_number=group_number)
        db.add(group)
        db.flush()
        for player_id in player_ids:
            db.add(PracticeGroupPlayer(group_id=group.id, player_id=player_id))

    db.commit()
    return _group_out(db, practice, current_user)
