import calendar
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

# How many recent sessions to chart in the attendance trend, how many named
# drills to show before the rest collapse into "Other", how many players to
# rank in the attendance leaderboard, and how many months of activity to chart.
_TREND_LIMIT = 8
_DRILL_MIX_LIMIT = 6
_LEADERBOARD_LIMIT = 8
_MONTHS_BACK = 6

_WEEKDAYS = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


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


def _last_months(today: dt.date, count: int) -> list[tuple[int, int]]:
    """Return the last `count` (year, month) pairs, oldest first, incl. current."""
    result: list[tuple[int, int]] = []
    for step in range(count - 1, -1, -1):
        month = today.month - step
        year = today.year
        while month <= 0:
            month += 12
            year -= 1
        result.append((year, month))
    return result


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
    session_completed_at = {s.id: s.completed_at for s in sessions}

    drills_count_by_session: dict[str, int] = defaultdict(int)
    minutes_by_session: dict[str, int] = defaultdict(int)
    players_count_by_session: dict[str, int] = defaultdict(int)
    drill_minutes_by_name: dict[str, int] = defaultdict(int)
    drill_uses_by_name: dict[str, int] = defaultdict(int)
    total_minutes = 0
    total_drills = 0
    total_attendance = 0

    # Player leaderboard: sessions attended per player, plus the most recently
    # recorded tier so the badge reflects where they play now.
    player_sessions: dict[str, int] = defaultdict(int)
    player_latest_tier: dict[str, str | None] = {}
    player_latest_seen: dict[str, dt.datetime] = {}

    if session_ids:
        for drill in (
            db.query(CompletedSessionDrill)
            .filter(CompletedSessionDrill.session_id.in_(session_ids))
            .all()
        ):
            minutes = drill.duration_minutes * drill.repeats
            drills_count_by_session[drill.session_id] += 1
            minutes_by_session[drill.session_id] += minutes
            drill_minutes_by_name[drill.name] += minutes
            drill_uses_by_name[drill.name] += 1
            total_minutes += minutes
            total_drills += 1

        for cp in (
            db.query(CompletedSessionPlayer)
            .filter(CompletedSessionPlayer.session_id.in_(session_ids))
            .all()
        ):
            players_count_by_session[cp.session_id] += 1
            total_attendance += 1
            player_sessions[cp.player_name] += 1
            seen_at = session_completed_at.get(cp.session_id)
            if seen_at is not None and (
                cp.player_name not in player_latest_seen
                or seen_at >= player_latest_seen[cp.player_name]
            ):
                player_latest_seen[cp.player_name] = seen_at
                player_latest_tier[cp.player_name] = cp.tier_name

    num_sessions = len(sessions)
    roster_size = db.query(Player).filter(Player.user_id == current_user.id).count()

    avg_attendance = round(total_attendance / num_sessions) if num_sessions else 0
    avg_session_minutes = round(total_minutes / num_sessions) if num_sessions else 0
    avg_drills_per_session = round(total_drills / num_sessions, 1) if num_sessions else 0.0
    attendance_rate = (
        min(100, round((avg_attendance / roster_size) * 100)) if roster_size else 0
    )

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

    leaderboard_sorted = sorted(
        player_sessions.items(), key=lambda kv: (-kv[1], kv[0].lower())
    )[:_LEADERBOARD_LIMIT]
    player_leaderboard = [
        {"name": name, "sessions": count, "tier_name": player_latest_tier.get(name)}
        for name, count in leaderboard_sorted
    ]

    weekday_counts = [0] * 7
    sport_counts: dict[str, int] = defaultdict(int)
    for s in sessions:
        weekday_counts[s.date.weekday()] += 1
        sport_counts[s.sport] += 1
    weekday_activity = [
        {"weekday": _WEEKDAYS[i], "count": weekday_counts[i]} for i in range(7)
    ]

    month_buckets = _last_months(today, _MONTHS_BACK)
    month_sessions: dict[tuple[int, int], int] = defaultdict(int)
    month_minutes: dict[tuple[int, int], int] = defaultdict(int)
    window = set(month_buckets)
    for s in sessions:
        key = (s.date.year, s.date.month)
        if key in window:
            month_sessions[key] += 1
            month_minutes[key] += minutes_by_session.get(s.id, 0)
    monthly_activity = [
        {
            "label": calendar.month_abbr[month],
            "sessions": month_sessions.get((year, month), 0),
            "minutes": month_minutes.get((year, month), 0),
        }
        for (year, month) in month_buckets
    ]

    sport_breakdown = [
        {"sport": sport, "sessions": count}
        for sport, count in sorted(sport_counts.items(), key=lambda kv: (-kv[1], kv[0].lower()))
    ]

    return {
        "totals": {
            "sessions_total": num_sessions,
            "sessions_this_month": sessions_this_month,
            "total_minutes": total_minutes,
            "roster_size": roster_size,
            "streak_weeks": _week_streak([s.date for s in sessions], today),
            "avg_attendance": avg_attendance,
            "avg_session_minutes": avg_session_minutes,
            "avg_drills_per_session": avg_drills_per_session,
            "attendance_rate": attendance_rate,
            "most_used_drill": most_used_drill,
        },
        "attendance_trend": attendance_trend,
        "drill_mix": drill_mix,
        "tier_balance": tier_balance,
        "player_leaderboard": player_leaderboard,
        "weekday_activity": weekday_activity,
        "monthly_activity": monthly_activity,
        "sport_breakdown": sport_breakdown,
    }
