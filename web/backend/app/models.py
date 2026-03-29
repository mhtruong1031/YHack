from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, Index, Integer, String, Text, UniqueConstraint, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    __table_args__ = (
        Index(
            "ix_users_handle_unique",
            "handle",
            unique=True,
            postgresql_where=text("handle IS NOT NULL"),
        ),
    )

    sub: Mapped[str] = mapped_column(String(512), primary_key=True)
    email: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    name: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    picture: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    handle: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    updated_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class FriendEdge(Base):
    __tablename__ = "friend_edges"
    __table_args__ = (
        Index(
            "uq_friend_pending_direction",
            "from_sub",
            "to_sub",
            unique=True,
            postgresql_where=text("status = 'pending'"),
        ),
        Index("ix_friend_edges_to_status", "to_sub", "status"),
        Index("ix_friend_edges_from_status", "from_sub", "status"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    from_sub: Mapped[str] = mapped_column(String(512), nullable=False)
    to_sub: Mapped[str] = mapped_column(String(512), nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class PointLedger(Base):
    __tablename__ = "point_ledger"
    __table_args__ = (
        UniqueConstraint("user_sub", "drop_id", name="uq_point_ledger_user_drop"),
        Index("ix_point_ledger_user_week", "user_sub", "week_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_sub: Mapped[str] = mapped_column(String(512), nullable=False)
    points: Mapped[float] = mapped_column(Float, nullable=False)
    source: Mapped[str] = mapped_column(String(64), nullable=False)
    drop_id: Mapped[str] = mapped_column(String(64), nullable=False)
    week_id: Mapped[str] = mapped_column(String(16), nullable=False)
    gemini_value: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


class Drop(Base):
    __tablename__ = "drops"

    drop_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    gemini_value: Mapped[float] = mapped_column(Float, nullable=False)
    classification: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    image_base64: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
