import re
from typing import Optional

STANDARD_SPORTS = ["Soccer", "Basketball", "Baseball", "Football", "Tennis"]
OTHER_SPORT_VALUE = "__other__"

_CUSTOM_SPORT_PATTERN = re.compile(r"^[A-Za-z0-9 '\-]+$")
_CUSTOM_SPORT_MAX_LENGTH = 40


class InvalidSportError(ValueError):
    pass


def resolve_sport(sport: str, custom_sport: Optional[str]) -> str:
    if sport in STANDARD_SPORTS:
        return sport

    if sport != OTHER_SPORT_VALUE:
        raise InvalidSportError(f"Unknown sport value: {sport!r}")

    cleaned = (custom_sport or "").strip()
    if not cleaned:
        raise InvalidSportError("custom_sport is required when sport is '__other__'")
    if len(cleaned) > _CUSTOM_SPORT_MAX_LENGTH:
        raise InvalidSportError(f"custom_sport must be {_CUSTOM_SPORT_MAX_LENGTH} characters or fewer")
    if not _CUSTOM_SPORT_PATTERN.match(cleaned):
        raise InvalidSportError("custom_sport contains disallowed characters")

    return cleaned


def validate_duration(duration_minutes: int) -> int:
    if duration_minutes < 5 or duration_minutes > 240:
        raise ValueError("duration_minutes must be between 5 and 240")
    if duration_minutes % 5 != 0:
        raise ValueError("duration_minutes must be a multiple of 5")
    return duration_minutes
