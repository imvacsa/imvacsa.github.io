# IDNT (아이덴트) - SQLAlchemy Models
# ---------------------------------------------------------------
# Requires PostgreSQL with the pgvector extension enabled:
#   CREATE EXTENSION IF NOT EXISTS vector;
#
# Run migrations (or create tables) via the startup event in main.py.
# ---------------------------------------------------------------

from __future__ import annotations

import enum
import uuid
from datetime import datetime

from sqlalchemy import (
    Column,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    String,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

try:
    from pgvector.sqlalchemy import Vector
except ImportError:
    # Fallback: store as raw array when pgvector is not installed
    from sqlalchemy import ARRAY, Float

    def Vector(dim: int):  # noqa: N802
        return ARRAY(Float, dimensions=(dim,))


# ── Base ─────────────────────────────────────────────────────────

class Base(DeclarativeBase):
    """Shared declarative base for all models."""


# ── Enums ────────────────────────────────────────────────────────

class CardStatus(str, enum.Enum):
    """Lifecycle status of an ID card."""
    processing = "processing"
    active = "active"
    expired = "expired"
    deactivated = "deactivated"


class EmployeeRole(str, enum.Enum):
    """Employee access role."""
    user = "user"
    admin = "admin"
    hr = "hr"


# ── Models ───────────────────────────────────────────────────────

class Employee(Base):
    """An employee in the organisation."""

    __tablename__ = "employees"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    employee_number: Mapped[str] = mapped_column(
        String(50), unique=True, nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    department: Mapped[str] = mapped_column(String(100), nullable=False)
    position: Mapped[str] = mapped_column(String(100), nullable=False)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    role: Mapped[EmployeeRole] = mapped_column(
        Enum(EmployeeRole), default=EmployeeRole.user, nullable=False
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    face_embeddings: Mapped[list[FaceEmbedding]] = relationship(
        back_populates="employee", cascade="all, delete-orphan"
    )
    id_cards: Mapped[list[IDCard]] = relationship(
        back_populates="employee", cascade="all, delete-orphan"
    )
    access_logs: Mapped[list[AccessLog]] = relationship(
        back_populates="employee", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<Employee {self.employee_number} {self.name}>"


class FaceEmbedding(Base):
    """512-dimensional face embedding for an employee."""

    __tablename__ = "face_embeddings"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    embedding = Column(Vector(512), nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    employee: Mapped[Employee] = relationship(back_populates="face_embeddings")

    __table_args__ = (
        Index(
            "ix_face_embeddings_vector",
            embedding,
            postgresql_using="ivfflat",
            postgresql_ops={"embedding": "vector_cosine_ops"},
        ),
    )

    def __repr__(self) -> str:
        return f"<FaceEmbedding employee_id={self.employee_id}>"


class IDCard(Base):
    """Issued digital ID card."""

    __tablename__ = "id_cards"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    card_image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[CardStatus] = mapped_column(
        Enum(CardStatus), default=CardStatus.processing, nullable=False, index=True
    )
    pkpass_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    google_pass_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    issued_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    # Relationships
    employee: Mapped[Employee] = relationship(back_populates="id_cards")
    access_logs: Mapped[list[AccessLog]] = relationship(
        back_populates="card", cascade="all, delete-orphan"
    )

    def __repr__(self) -> str:
        return f"<IDCard {self.id} status={self.status}>"


class AccessLog(Base):
    """Audit log for card-related actions."""

    __tablename__ = "access_logs"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    employee_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("employees.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    card_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("id_cards.id", ondelete="SET NULL"),
        nullable=True,
    )
    action: Mapped[str] = mapped_column(String(100), nullable=False)
    location: Mapped[str | None] = mapped_column(String(255), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    # Relationships
    employee: Mapped[Employee] = relationship(back_populates="access_logs")
    card: Mapped[IDCard | None] = relationship(back_populates="access_logs")

    def __repr__(self) -> str:
        return f"<AccessLog {self.action} employee={self.employee_id}>"
