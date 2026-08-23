import datetime as dt
from collections import defaultdict

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session as DbSession

from app.database import get_db
from app.models import (
    CompletedSession,
    CompletedSessionDrill,
    CompletedSessionPlayer,
    Player,
    Tier,
    User,
)
from app.schemas import AnalyticsSummary
from app.security import get_current_user

router = APIRouter(prefix="/api/analytics", tags=["analytics"])

# How many recent sessions to chart in the attendance trend, and how many named
# drills to show in the mix before the rest collapse into "Other".
_TREND_LIMIT = 8
_DRILL_MIX_LIMIT = 6


def _week_key(day: dt.date) -> tuple[int, int]:
    iso = day.isocalendar()
    return (iso[0], iso[1])


def _week_streak(session_dates: list[dt.date], today: dt.date) -> int:
    """Consecutive calendar weeks (ending at the current week) with a session.

    The current week is allowed to be empty without breaking the streak — a
    coach shouldn't lose their streak just because this week's practice hasn't
    happened yet.
    """
    weeks = {_week_key(day) for day in session_dates}
    if not weeks:
        return 0
    cursor = today
    if _week_key(cursor) not in weeks:
        cursor = today - dt.timedelta(days=7)
    streak = 0
    while _week_key(cursor) in weeks:
        streak += 1
        cursor = cursor - dt.timedelta(days=7)
    return streak


@router.get("/summary", response_model=AnalyticsSummary)
def analytics_summary(
    current_user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    sessions = (
        db.query(CompletedSession)
        .filter(CompletedSession.user_id == current_user.id)
        .order_by(CompletedSession.completed_at.asc())
        .all()
    )
    session_ids = [s.id for s in sessions]

    drills_count_by_session: dict[str, int] = defaultdict(int)
    players_count_by_session: dict[str, int] = defaultdict(int)
    drill_minutes_by_name: dict[str, int] = defaultdict(int)
    drill_uses_by_name: dict[str, int] = defaultdict(int)
    total_minutes = 0

    if session_ids:
        for drill in (
            db.query(CompletedSessionDrill)
            .filter(CompletedSessionDrill.session_id.in_(session_ids))
            .all()
        ):
            minutes = drill.duration_minutes * drill.repeats
            drills_count_by_session[drill.session_id] += 1
            drill_minutes_by_name[drill.name] += minutes
            drill_uses_by_name[drill.name] += 1
            total_minutes += minutes

        for (session_id,) in (
            db.query(CompletedSessionPlayer.session_id)
            .filter(CompletedSessionPlayer.session_id.in_(session_ids))
            .all()
        ):
            players_count_by_session[session_id] += 1

    today = dt.date.today()
    sessions_this_month = sum(
        1
        for s in sessions
        if s.completed_at is not None
        and s.completed_at.year == today.year
        and s.completed_at.month == today.month
    )

    most_used_drill = None
    if drill_uses_by_name:
        name = max(
            drill_uses_by_name,
            key=lambda n: (drill_uses_by_name[n], drill_minutes_by_name[n]),
        )
        most_used_drill = {"name": name, "count": drill_uses_by_name[name]}

    roster_size = db.query(Player).filter(Player.user_id == current_user.id).count()

    attendance_trend = [
        {
            "date": s.date,
            "players": players_count_by_session.get(s.id, 0),
            "drills": drills_count_by_session.get(s.id, 0),
        }
        for s in sessions[-_TREND_LIMIT:]
    ]

    sorted_mix = sorted(drill_minutes_by_name.items(), key=lambda kv: kv[1], reverse=True)
    drill_mix = [{"name": name, "minutes": minutes} for name, minutes in sorted_mix[:_DRILL_MIX_LIMIT]]
    other_minutes = sum(minutes for _, minutes in sorted_mix[_DRILL_MIX_LIMIT:])
    if other_minutes:
        drill_mix.append({"name": "Other", "minutes": other_minutes})

    tiers = (
        db.query(Tier)
        .filter(Tier.user_id == current_user.id)
        .order_by(Tier.sort_order.asc())
        .all()
    )
    counts_by_tier: dict[object, int] = defaultdict(int)
    for (tier_id,) in db.query(Player.tier_id).filter(Player.user_id == current_user.id).all():
        counts_by_tier[tier_id] += 1
    tier_balance = [{"name": t.name, "count": counts_by_tier.get(t.id, 0)} for t in tiers]
    if counts_by_tier.get(None):
        tier_balance.append({"name": "No tier", "count": counts_by_tier[None]})

    return {
        "totals": {
            "sessions_total": len(sessions),
            "sessions_this_month": sessions_this_month,
            "total_minutes": total_minutes,
            "roster_size": roster_size,
            "streak_weeks": _week_streak([s.date for s in sessions], today),
            "most_used_drill": most_used_drill,
        },
        "attendance_trend": attendance_trend,
        "drill_mix": drill_mix,
        "tier_balance": tier_balance,
    }
