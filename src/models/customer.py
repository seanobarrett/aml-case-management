"""
Customer model - snapshot at case creation.

The customer data is captured as a snapshot when a case is created
and remains immutable for the case lifecycle. This ensures consistency
in regulatory reporting even if the customer's data changes later.

References:
- G3 (Contracts): Customer snapshot immutability
- EC-008: Customer account closure indicator
"""

from datetime import date, datetime
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import Boolean, Column, Date, DateTime, String
from src.models.base import DatabaseAgnosticUUID
from sqlalchemy.orm import Mapped, relationship

from src.models.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from src.models.case import Case


class Customer(Base, UUIDPrimaryKeyMixin):
    """
    Customer snapshot captured at case creation.

    This is an immutable snapshot of customer data at the time the case
    was created. Changes to the customer's actual data in the core system
    do not affect existing cases.
    """

    __tablename__ = "customers"

    # External reference
    external_customer_id: Mapped[str] = Column(String(255), nullable=False, index=True)

    # Personal information (PII - subject to redaction in audit logs)
    first_name: Mapped[Optional[str]] = Column(String(255), nullable=True)
    last_name: Mapped[Optional[str]] = Column(String(255), nullable=True)
    email: Mapped[Optional[str]] = Column(String(255), nullable=True)
    date_of_birth: Mapped[Optional[date]] = Column(Date, nullable=True)

    # Account status at snapshot time
    account_status: Mapped[Optional[str]] = Column(String(50), nullable=True)
    onboarding_status: Mapped[Optional[str]] = Column(String(50), nullable=True)

    # Account closure indicator (EC-008)
    account_closed: Mapped[bool] = Column(Boolean, nullable=False, default=False)
    account_closed_at: Mapped[Optional[datetime]] = Column(
        DateTime(timezone=True),
        nullable=True
    )
    account_closure_reason: Mapped[Optional[str]] = Column(String(500), nullable=True)

    # Snapshot metadata
    snapshot_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow
    )
    created_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow
    )

    # Relationships
    cases: Mapped[list["Case"]] = relationship("Case", back_populates="customer")

    def __repr__(self) -> str:
        return f"<Customer {self.external_customer_id} snapshot={self.snapshot_at}>"

    @property
    def full_name(self) -> str:
        """Get customer's full name."""
        parts = [p for p in [self.first_name, self.last_name] if p]
        return " ".join(parts) if parts else "Unknown"

    @property
    def is_account_closed(self) -> bool:
        """Check if customer account is marked as closed."""
        return self.account_closed

    @classmethod
    def create_snapshot(
        cls,
        external_customer_id: str,
        first_name: Optional[str] = None,
        last_name: Optional[str] = None,
        email: Optional[str] = None,
        date_of_birth: Optional[date] = None,
        account_status: Optional[str] = None,
        onboarding_status: Optional[str] = None,
    ) -> "Customer":
        """
        Create a new customer snapshot.

        Args:
            external_customer_id: Customer ID from external system
            first_name: Customer first name
            last_name: Customer last name
            email: Customer email
            date_of_birth: Customer date of birth
            account_status: Current account status
            onboarding_status: Current onboarding status

        Returns:
            New Customer snapshot instance
        """
        return cls(
            external_customer_id=external_customer_id,
            first_name=first_name,
            last_name=last_name,
            email=email,
            date_of_birth=date_of_birth,
            account_status=account_status,
            onboarding_status=onboarding_status,
            snapshot_at=datetime.utcnow(),
        )

    def mark_account_closed(self) -> None:
        """Mark this customer's account as closed (EC-008)."""
        self.account_closed = True
