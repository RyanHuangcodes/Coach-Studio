import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy import CheckConstraint, Date, ForeignKey, String, DateTime, Integer, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    email: Mapped[str] = mapped_column(String, unique=True, index=True, nullable=False)
    password_hash: Mapped[str] = mapped_column(String, nullable=False)
    display_name: Mapped[str] = mapped_column(String, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)


class Session(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    user: Mapped["User"] = relationship()


class Draft(Base):
    __tablename__ = "drafts"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sport: Mapped[str] = mapped_column(String(60), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=_now, onupdate=_now, nullable=False
    )

    __table_args__ = (
        CheckConstraint("duration_minutes >= 5 AND duration_minutes <= 240", name="draft_duration_range"),
    )


class Plan(Base):
    __tablename__ = "plans"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    sport: Mapped[str] = mapped_column(String(60), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    source_draft_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False), ForeignKey("drafts.id", ondelete="SET NULL"), nullable=True
    )

    __table_args__ = (
        CheckConstraint("duration_minutes >= 5 AND duration_minutes <= 240", name="plan_duration_range"),
    )


class Tier(Base):
    __tablename__ = "tiers"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(40), nullable=False)
    sort_order: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)


class Player(Base):
    __tablename__ = "players"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    tier_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False), ForeignKey("tiers.id", ondelete="SET NULL"), nullable=True
    )
    rank: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)


class Practice(Base):
    __tablename__ = "practices"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    date: Mapped[datetime] = mapped_column(Date, nullable=False)
    plan_id: Mapped[Optional[str]] = mapped_column(
        UUID(as_uuid=False), ForeignKey("plans.id", ondelete="SET NULL"), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)

    __table_args__ = (UniqueConstraint("user_id", "date", name="practice_user_date_unique"),)


class AttendanceRecord(Base):
    __tablename__ = "attendance_records"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    practice_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("practices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    player_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("players.id", ondelete="CASCADE"), nullable=False, index=True
    )
    checked_in_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("practice_id", "player_id", name="attendance_practice_player_unique"),
    )


class PracticeGroup(Base):
    __tablename__ = "practice_groups"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    practice_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("practices.id", ondelete="CASCADE"), nullable=False, index=True
    )
    group_number: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)

    __table_args__ = (
        UniqueConstraint("practice_id", "group_number", name="practice_group_number_unique"),
    )


class PracticeGroupPlayer(Base):
    __tablename__ = "practice_group_players"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    group_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("practice_groups.id", ondelete="CASCADE"), nullable=False, index=True
    )
    player_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("players.id", ondelete="CASCADE"), nullable=False, index=True
    )

    __table_args__ = (
        UniqueConstraint("group_id", "player_id", name="group_player_unique"),
    )
