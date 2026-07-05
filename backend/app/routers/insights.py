import json

import anthropic
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as DbSession

from app.config import settings
from app.database import get_db
from app.models import AttendanceRecord, Drill, Plan, Player, Tier, User
from app.routers.practices import get_or_create_today_practice_row
from app.schemas import InsightOut, InsightRequest
from app.security import get_current_user

router = APIRouter(prefix="/api/insights", tags=["insights"])

_MODEL = "claude-opus-4-8"

_INSIGHT_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "required": ["focus", "drills", "coaching_points"],
    "properties": {
        "focus": {
            "type": "string",
            "description": "A 1-2 sentence tactical focus statement for today's session",
        },
        "drills": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "required": ["name", "duration_minutes", "description"],
                "properties": {
                    "name": {"type": "string"},
                    "duration_minutes": {"type": "integer"},
                    "description": {"type": "string"},
                },
            },
        },
        "coaching_points": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Short courtside cues the coach can call out",
        },
    },
}

_SYSTEM_PROMPT = (
    "You are an assistant for a professional sports coach using a training-management app. "
    "Given the coach's objective for today's session and context about their roster and "
    "attendance, suggest a tactical focus, 3-5 concrete drills (with realistic durations "
    "between 5 and 40 minutes each), and 3-5 short coaching cues. Ground suggestions in the "
    "roster size and skill tiers provided. Be specific and practical, not generic."
)


def _build_context(db: DbSession, current_user: User, plan_id) -> str:
    lines = []

    tiers = db.query(Tier).filter(Tier.user_id == current_user.id).order_by(Tier.sort_order).all()
    players = db.query(Player).filter(Player.user_id == current_user.id).all()
    tier_names = {t.id: t.name for t in tiers}

    lines.append(f"Roster: {len(players)} players")
    for tier in tiers:
        tier_players = [p.name for p in players if p.tier_id == tier.id]
        if tier_players:
            lines.append(f"- {tier.name}: {', '.join(tier_players)}")
    untiered = [p.name for p in players if not p.tier_id]
    if untiered:
        lines.append(f"- No tier: {', '.join(untiered)}")

    practice = get_or_create_today_practice_row(db, current_user.id)
    checked_in = (
        db.query(AttendanceRecord).filter(AttendanceRecord.practice_id == practice.id).count()
    )
    lines.append(f"Checked in for today's practice: {checked_in} of {len(players)}")

    if plan_id:
        plan = db.query(Plan).filter(Plan.id == plan_id, Plan.user_id == current_user.id).first()
        if plan is not None:
            lines.append(f"Today's plan: {plan.sport}, {plan.duration_minutes} minutes total")
            drills = (
                db.query(Drill).filter(Drill.plan_id == plan.id).order_by(Drill.position).all()
            )
            if drills:
                lines.append("Drills already planned:")
                for drill in drills:
                    lines.append(
                        f"- {drill.name}: {drill.repeats} x {drill.duration_minutes} min"
                        + (f" ({drill.notes})" if drill.notes else "")
                    )

    return "\n".join(lines)


@router.post("/generate", response_model=InsightOut)
def generate_insight(
    payload: InsightRequest,
    current_user: User = Depends(get_current_user),
    db: DbSession = Depends(get_db),
):
    if not settings.anthropic_api_key:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI insights are not configured yet — add ANTHROPIC_API_KEY to backend/.env",
        )

    context = _build_context(db, current_user, payload.plan_id)
    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    try:
        response = client.messages.create(
            model=_MODEL,
            max_tokens=2000,
            thinking={"type": "adaptive"},
            system=_SYSTEM_PROMPT,
            output_config={"format": {"type": "json_schema", "schema": _INSIGHT_SCHEMA}},
            messages=[
                {
                    "role": "user",
                    "content": f"Today's objective: {payload.objective}\n\n{context}",
                }
            ],
        )
    except anthropic.AuthenticationError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The configured Anthropic API key was rejected",
        ) from exc
    except anthropic.RateLimitError as exc:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="AI service is rate-limited right now — try again in a moment",
        ) from exc
    except anthropic.APIStatusError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"AI service error ({exc.status_code})",
        ) from exc
    except anthropic.APIConnectionError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not reach the AI service",
        ) from exc

    if response.stop_reason == "refusal" or not response.content:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="The AI declined to answer this objective — try rephrasing it",
        )

    text_blocks = [block.text for block in response.content if block.type == "text"]
    try:
        return json.loads("".join(text_blocks))
    except (json.JSONDecodeError, ValueError) as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="AI returned an unreadable response — try again",
        ) from exc
