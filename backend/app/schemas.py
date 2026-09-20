import datetime as dt
from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.sports import validate_duration


def _normalize_email(value: str) -> str:
    # Lowercase + strip so "Alex@X.com " and "alex@x.com" are the same account.
    # Pydantic's EmailStr already lowercases the domain but not the local part.
    return value.strip().lower()


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)
    display_name: str = Field(min_length=1, max_length=80)

    @field_validator("email")
    @classmethod
    def _lower_email(cls, value: str) -> str:
        return _normalize_email(value)


class UserLogin(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def _lower_email(cls, value: str) -> str:
        return _normalize_email(value)


class UserOut(BaseModel):
    id: str
    email: str
    display_name: str

    model_config = {"from_attributes": True}


class PlanOrDraftInput(BaseModel):
    sport: str
    custom_sport: Optional[str] = None
    duration_minutes: int

    @field_validator("duration_minutes")
    @classmethod
    def _validate_duration(cls, value: int) -> int:
        return validate_duration(value)


class PlanCreate(PlanOrDraftInput):
    source_draft_id: Optional[str] = None
    name: Optional[str] = Field(default=None, max_length=80)
    session_date: Optional[dt.date] = None

    @field_validator("name")
    @classmethod
    def _strip_name(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        stripped = value.strip()
        return stripped or None


class DraftCreate(PlanOrDraftInput):
    pass


class DraftOut(BaseModel):
    id: str
    sport: str
    duration_minutes: int
    updated_at: datetime

    model_config = {"from_attributes": True}


class PlanOut(BaseModel):
    id: str
    sport: str
    name: Optional[str] = None
    session_date: Optional[dt.date] = None
    duration_minutes: int
    created_at: datetime

    model_config = {"from_attributes": True}


class DrillCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    duration_minutes: int = Field(ge=1, le=240)
    repeats: int = Field(default=1, ge=1, le=20)
    groups: int = Field(default=1, ge=1, le=60)
    notes: Optional[str] = Field(default=None, max_length=4000)

    @field_validator("name")
    @classmethod
    def _strip_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("name must not be blank")
        return stripped


class DrillOut(BaseModel):
    id: str
    name: str
    duration_minutes: int
    repeats: int
    groups: int
    notes: Optional[str]
    position: int

    model_config = {"from_attributes": True}


class DrillMove(BaseModel):
    direction: str

    @field_validator("direction")
    @classmethod
    def _validate_direction(cls, value: str) -> str:
        if value not in ("up", "down"):
            raise ValueError("direction must be 'up' or 'down'")
        return value


class TierCreate(BaseModel):
    name: str = Field(min_length=1, max_length=40)

    @field_validator("name")
    @classmethod
    def _strip_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("name must not be blank")
        return stripped


class TierOut(BaseModel):
    id: str
    name: str
    sort_order: int

    model_config = {"from_attributes": True}


class PlayerCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    tier_id: Optional[str] = None
    notes: Optional[str] = Field(default=None, max_length=4000)
    # When set (on create), the new player is also added to this roster.
    roster_id: Optional[str] = None

    @field_validator("name")
    @classmethod
    def _strip_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("name must not be blank")
        return stripped


class PlayerOut(BaseModel):
    id: str
    name: str
    tier_id: Optional[str]
    rank: Optional[int]
    notes: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


class PlayerAttendanceOut(BaseModel):
    dates: list[dt.date]


class PlayerMove(BaseModel):
    direction: str

    @field_validator("direction")
    @classmethod
    def _validate_direction(cls, value: str) -> str:
        if value not in ("up", "down"):
            raise ValueError("direction must be 'up' or 'down'")
        return value


def _validate_roster_kind(value: str) -> str:
    if value not in ("team", "private"):
        raise ValueError("kind must be 'team' or 'private'")
    return value


class RosterCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    kind: str = "team"

    @field_validator("name")
    @classmethod
    def _strip_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("name must not be blank")
        return stripped

    @field_validator("kind")
    @classmethod
    def _kind(cls, value: str) -> str:
        return _validate_roster_kind(value)


class RosterUpdate(BaseModel):
    name: Optional[str] = Field(default=None, max_length=80)
    kind: Optional[str] = None

    @field_validator("name")
    @classmethod
    def _strip_name(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None
        stripped = value.strip()
        if not stripped:
            raise ValueError("name must not be blank")
        return stripped

    @field_validator("kind")
    @classmethod
    def _kind(cls, value: Optional[str]) -> Optional[str]:
        return None if value is None else _validate_roster_kind(value)


class RosterOut(BaseModel):
    id: str
    name: str
    kind: str
    sort_order: int
    player_count: int


class RosterMembersAdd(BaseModel):
    player_ids: list[str] = Field(min_length=1, max_length=500)


_ALLOWED_IMAGE_TYPES = {"image/png", "image/jpeg", "image/webp", "image/gif"}


class RosterImageRequest(BaseModel):
    # Raw base64 (no data: URI prefix). ~8M chars ≈ 6 MB decoded — the client
    # downscales before upload, so this is a generous safety ceiling, not a target.
    image_base64: str = Field(min_length=1, max_length=8_000_000)
    media_type: str

    @field_validator("media_type")
    @classmethod
    def _validate_media_type(cls, value: str) -> str:
        if value not in _ALLOWED_IMAGE_TYPES:
            raise ValueError("media_type must be one of: " + ", ".join(sorted(_ALLOWED_IMAGE_TYPES)))
        return value


class RosterImageResponse(BaseModel):
    names: list[str]


class AnalyticsMostUsedDrill(BaseModel):
    name: str
    count: int


class AnalyticsTotals(BaseModel):
    sessions_total: int
    sessions_this_month: int
    total_minutes: int
    roster_size: int
    streak_weeks: int
    avg_attendance: int
    avg_session_minutes: int
    avg_drills_per_session: float
    attendance_rate: int
    most_used_drill: Optional[AnalyticsMostUsedDrill] = None


class AnalyticsTrendPoint(BaseModel):
    date: date
    players: int
    drills: int


class AnalyticsDrillMixItem(BaseModel):
    name: str
    minutes: int


class AnalyticsTierCount(BaseModel):
    name: str
    count: int


class AnalyticsPlayerStat(BaseModel):
    name: str
    sessions: int
    tier_name: Optional[str] = None


class AnalyticsWeekdayStat(BaseModel):
    weekday: str
    count: int


class AnalyticsMonthStat(BaseModel):
    label: str
    sessions: int
    minutes: int


class AnalyticsSportStat(BaseModel):
    sport: str
    sessions: int


class AnalyticsSummary(BaseModel):
    totals: AnalyticsTotals
    attendance_trend: list[AnalyticsTrendPoint]
    drill_mix: list[AnalyticsDrillMixItem]
    tier_balance: list[AnalyticsTierCount]
    player_leaderboard: list[AnalyticsPlayerStat]
    weekday_activity: list[AnalyticsWeekdayStat]
    monthly_activity: list[AnalyticsMonthStat]
    sport_breakdown: list[AnalyticsSportStat]


_ALLOWED_SLOTS = {"day", "morning", "afternoon", "night"}


def _validate_slot(value: str) -> str:
    if value not in _ALLOWED_SLOTS:
        raise ValueError("slot must be one of: " + ", ".join(sorted(_ALLOWED_SLOTS)))
    return value


class TodayPracticeRequest(BaseModel):
    # dt.date, not bare `date`: the field's default binds `date = None` in the
    # class namespace before the annotation is evaluated, so a bare `date` here
    # would resolve to None and reject every real value.
    date: Optional[dt.date] = None
    roster_id: Optional[str] = None
    slot: str = "day"

    @field_validator("slot")
    @classmethod
    def _slot(cls, value: str) -> str:
        return _validate_slot(value)


class PracticeOut(BaseModel):
    id: str
    date: date
    plan_id: Optional[str]
    roster_id: Optional[str] = None
    slot: str = "day"
    created_at: datetime

    model_config = {"from_attributes": True}


class PracticeForDateRequest(BaseModel):
    roster_id: Optional[str] = None
    date: dt.date
    slot: str = "day"

    @field_validator("slot")
    @classmethod
    def _slot(cls, value: str) -> str:
        return _validate_slot(value)


class PracticeByDateOut(BaseModel):
    practice_id: Optional[str] = None
    player_ids: list[str] = []


class CalendarDayOut(BaseModel):
    date: dt.date
    attendee_count: int


class AttendanceCheckIn(BaseModel):
    player_id: str


class AttendanceOut(BaseModel):
    player_id: str
    checked_in_at: datetime

    model_config = {"from_attributes": True}


class GroupGenerateRequest(BaseModel):
    group_size: Optional[int] = Field(default=None, ge=2, le=100)
    num_groups: Optional[int] = Field(default=None, ge=1, le=50)
    practice_id: Optional[str] = None

    @model_validator(mode="after")
    def _exactly_one(self):
        if (self.group_size is None) == (self.num_groups is None):
            raise ValueError("Provide exactly one of group_size or num_groups")
        return self


class GroupPlayerOut(BaseModel):
    id: str
    name: str
    tier_name: Optional[str]


class GroupOut(BaseModel):
    group_number: int
    players: list[GroupPlayerOut]


class GroupGenerateResponse(BaseModel):
    groups: list[GroupOut]


class GroupsSaveRequest(BaseModel):
    groups: list[list[str]] = Field(min_length=1, max_length=50)

    @field_validator("groups")
    @classmethod
    def _no_empty_groups(cls, value: list[list[str]]) -> list[list[str]]:
        if any(not group for group in value):
            raise ValueError("groups must not contain empty groups")
        all_ids = [pid for group in value for pid in group]
        if len(all_ids) != len(set(all_ids)):
            raise ValueError("a player cannot appear in more than one group")
        return value


class SavedGroupsOut(BaseModel):
    practice_id: str
    saved_at: Optional[datetime]
    groups: list[GroupOut]


class InsightRequest(BaseModel):
    objective: str = Field(min_length=3, max_length=500)
    sport: Optional[str] = Field(default=None, max_length=40)
    plan_id: Optional[str] = None

    @field_validator("objective")
    @classmethod
    def _strip_objective(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("objective must not be blank")
        return stripped


class ObjectiveIdeasRequest(BaseModel):
    sport: Optional[str] = Field(default=None, max_length=40)


class ObjectiveIdeasOut(BaseModel):
    objectives: list[str]


class InsightDrill(BaseModel):
    name: str
    duration_minutes: int
    description: str


class InsightOut(BaseModel):
    focus: str
    drills: list[InsightDrill]
    coaching_points: list[str]


class HistoryCreate(BaseModel):
    plan_id: Optional[str] = None
    practice_id: Optional[str] = None


class HistoryPlayerOut(BaseModel):
    player_name: str
    tier_name: Optional[str]

    model_config = {"from_attributes": True}


class HistoryDrillOut(BaseModel):
    name: str
    duration_minutes: int
    repeats: int
    notes: Optional[str]
    position: int

    model_config = {"from_attributes": True}


class HistoryListItem(BaseModel):
    id: str
    sport: str
    date: date
    completed_at: datetime
    player_count: int
    drill_count: int


class HistoryDetail(BaseModel):
    id: str
    sport: str
    date: date
    completed_at: datetime
    players: list[HistoryPlayerOut]
    drills: list[HistoryDrillOut]
