from datetime import date, datetime
from typing import Optional

from pydantic import BaseModel, EmailStr, Field, field_validator, model_validator

from app.sports import validate_duration


class UserCreate(BaseModel):
    email: EmailStr
    password: str = Field(min_length=8, max_length=200)
    display_name: str = Field(min_length=1, max_length=80)


class UserLogin(BaseModel):
    email: EmailStr
    password: str


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
    duration_minutes: int
    created_at: datetime

    model_config = {"from_attributes": True}


class DrillCreate(BaseModel):
    name: str = Field(min_length=1, max_length=80)
    duration_minutes: int = Field(ge=1, le=240)
    repeats: int = Field(default=1, ge=1, le=20)
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


class PlayerMove(BaseModel):
    direction: str

    @field_validator("direction")
    @classmethod
    def _validate_direction(cls, value: str) -> str:
        if value not in ("up", "down"):
            raise ValueError("direction must be 'up' or 'down'")
        return value


class PracticeOut(BaseModel):
    id: str
    date: date
    plan_id: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}


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
    plan_id: Optional[str] = None

    @field_validator("objective")
    @classmethod
    def _strip_objective(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("objective must not be blank")
        return stripped


class InsightDrill(BaseModel):
    name: str
    duration_minutes: int
    description: str


class InsightOut(BaseModel):
    focus: str
    drills: list[InsightDrill]
    coaching_points: list[str]
