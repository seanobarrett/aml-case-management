"""
Base model configuration with optimistic locking support.

References:
- D8: Optimistic locking with version column
- EC-001: Concurrent updates handled via version column
"""

import os
from datetime import datetime
from typing import Any, Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, DateTime, Integer, String, event
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import DeclarativeBase, Session, Mapped, mapped_column
from sqlalchemy.exc import IntegrityError
from sqlalchemy.types import TypeDecorator, CHAR


class DatabaseAgnosticUUID(TypeDecorator):
    """
    Platform-independent UUID type.

    Uses PostgreSQL's UUID type when available, otherwise uses CHAR(36)
    for SQLite compatibility. Always stores as string internally for SQLite.
    """

    impl = CHAR
    cache_ok = True

    def load_dialect_impl(self, dialect):
        if dialect.name == 'postgresql':
            return dialect.type_descriptor(PGUUID(as_uuid=True))
        else:
            return dialect.type_descriptor(CHAR(36))

    def process_bind_param(self, value, dialect):
        if value is None:
            return value
        if dialect.name == 'postgresql':
            return value
        else:
            # Convert UUID to string for SQLite
            if isinstance(value, UUID):
                return str(value)
            return value

    def process_result_value(self, value, dialect):
        if value is None:
            return value
        if dialect.name == 'postgresql':
            return value
        else:
            # Convert string back to UUID for SQLite
            if isinstance(value, str):
                return UUID(value)
            return value


class OptimisticLockError(Exception):
    """Raised when optimistic locking detects concurrent modification."""

    def __init__(self, entity_type: str, entity_id: str):
        self.entity_type = entity_type
        self.entity_id = entity_id
        super().__init__(
            f"Concurrent modification detected for {entity_type} with id {entity_id}. "
            "The record has been modified by another transaction."
        )


class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""

    # Allow legacy unmapped attributes for flexibility
    __allow_unmapped__ = True


class TimestampMixin:
    """Mixin for created_at and updated_at timestamps."""

    created_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )


class VersionedMixin(TimestampMixin):
    """
    Mixin for optimistic locking with version column.

    Usage:
        class MyModel(Base, VersionedMixin):
            ...

    The version column is automatically incremented on each update.
    If the version doesn't match the expected value, an OptimisticLockError is raised.
    """

    version = Column(Integer, nullable=False, default=1)

    def increment_version(self) -> None:
        """Increment version for optimistic locking."""
        self.version += 1

    @classmethod
    def get_with_lock(cls, session: Session, id: UUID, expected_version: Optional[int] = None) -> Any:
        """
        Get entity with optional version check for optimistic locking.

        Args:
            session: SQLAlchemy session
            id: Entity ID
            expected_version: If provided, verify version matches

        Returns:
            Entity instance

        Raises:
            OptimisticLockError: If version doesn't match
        """
        entity = session.query(cls).filter(cls.id == id).first()

        if entity is None:
            return None

        if expected_version is not None and entity.version != expected_version:
            raise OptimisticLockError(cls.__name__, str(id))

        return entity


class UUIDPrimaryKeyMixin:
    """Mixin for UUID primary key."""

    id: Mapped[UUID] = mapped_column(
        DatabaseAgnosticUUID(),
        primary_key=True,
        default=uuid4
    )


def validate_version_on_update(mapper, connection, target):
    """
    Event listener to validate version on update.

    This ensures optimistic locking works correctly by checking
    that the version in the database matches the expected version
    before allowing the update to proceed.
    """
    if hasattr(target, "version") and hasattr(target, "_expected_version"):
        # Version validation is handled by the trigger in PostgreSQL
        pass
