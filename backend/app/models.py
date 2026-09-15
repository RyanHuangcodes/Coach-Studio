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
    # Optional coach-given session title; display falls back to sport when unset.
    name: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    # Optional date the session is planned for (organizational, coach-local).
    session_date: Mapped[Optional[datetime]] = mapped_column(Date, nullable=True)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)
    # Historical breadcrumb only — deliberately NOT a foreign key. The source
    # draft is deleted in the same transaction that creates the plan, so an FK
    # with ON DELETE SET NULL would immediately wipe this value.
    source_draft_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), nullable=True)

    __table_args__ = (
        CheckConstraint("duration_minutes >= 5 AND duration_minutes <= 240", name="plan_duration_range"),
    )


class Drill(Base):
    __tablename__ = "drills"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    plan_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("plans.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    repeats: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    # Preset number of rotation groups for the session timer (total/groups per turn).
    groups: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)

    __table_args__ = (
        CheckConstraint("duration_minutes >= 1 AND duration_minutes <= 240", name="drill_duration_range"),
        CheckConstraint("repeats >= 1 AND repeats <= 20", name="drill_repeats_range"),
        CheckConstraint("groups >= 1 AND groups <= 60", name="drill_groups_range"),
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


class CompletedSession(Base):
    __tablename__ = "completed_sessions"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    user_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    # plan_id is a reference only, not a source of truth — the drills that actually
    # took place are snapshotted below so later edits/deletes to the plan don't
    # rewrite history.
    plan_id: Mapped[Optional[str]] = mapped_column(UUID(as_uuid=False), nullable=True)
    sport: Mapped[str] = mapped_column(String(60), nullable=False)
    date: Mapped[datetime] = mapped_column(Date, nullable=False)
    completed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now, nullable=False)

    players: Mapped[list["CompletedSessionPlayer"]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True
    )
    drills: Mapped[list["CompletedSessionDrill"]] = relationship(
        cascade="all, delete-orphan", passive_deletes=True
    )


class CompletedSessionPlayer(Base):
    __tablename__ = "completed_session_players"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("completed_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    # Snapshotted so a later player rename/delete never changes the record.
    player_name: Mapped[str] = mapped_column(String(80), nullable=False)
    tier_name: Mapped[Optional[str]] = mapped_column(String(40), nullable=True)


class CompletedSessionDrill(Base):
    __tablename__ = "completed_session_drills"

    id: Mapped[str] = mapped_column(UUID(as_uuid=False), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("completed_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    duration_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    repeats: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
