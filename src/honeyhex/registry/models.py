from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy.types import JSON


class Base(DeclarativeBase):
    pass


def _uuid() -> str:
    return str(uuid.uuid4())


class Swarm(Base):
    __tablename__ = "swarms"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(256))
    quorum_threshold: Mapped[float] = mapped_column(default=0.51)
    validator_agent_ids: Mapped[list[str]] = mapped_column(JSON, default=lambda: [])
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )

    agents: Mapped[list[Agent]] = relationship(back_populates="swarm")
    pull_requests: Mapped[list[PullRequest]] = relationship(back_populates="swarm")


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[str] = mapped_column(String(256), primary_key=True)
    swarm_id: Mapped[str] = mapped_column(String(64), ForeignKey("swarms.id"))
    display_name: Mapped[str | None] = mapped_column(String(256), nullable=True)
    last_head_sha: Mapped[str | None] = mapped_column(String(64), nullable=True)
    branch: Mapped[str | None] = mapped_column(String(256), nullable=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    swarm: Mapped[Swarm] = relationship(back_populates="agents")


class PullRequest(Base):
    __tablename__ = "pull_requests"

    id: Mapped[str] = mapped_column(String(64), primary_key=True, default=_uuid)
    swarm_id: Mapped[str] = mapped_column(String(64), ForeignKey("swarms.id"))
    source_agent_id: Mapped[str] = mapped_column(String(256))
    target_agent_id: Mapped[str] = mapped_column(String(256))
    head_sha: Mapped[str] = mapped_column(String(64))
    title: Mapped[str] = mapped_column(String(512), default="")
    status: Mapped[str] = mapped_column(String(32), default="open")
    votes: Mapped[dict[str, Any]] = mapped_column(JSON, default=lambda: {})
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )

    swarm: Mapped[Swarm] = relationship(back_populates="pull_requests")


class BlackboardEntry(Base):
    """Append-only mesh blackboard (ordered by Lamport clock)."""

    __tablename__ = "blackboard_entries"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    swarm_id: Mapped[str] = mapped_column(String(64), ForeignKey("swarms.id"))
    agent_id: Mapped[str] = mapped_column(String(256))
    lamport: Mapped[int] = mapped_column()
    payload: Mapped[dict[str, Any]] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(UTC),
    )
