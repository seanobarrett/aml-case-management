"""
Customer communication model for tracking correspondence.

References:
- US-2: L1 Analyst requests additional information from customer
- FR-053: Case status changes to PENDING_INFORMATION
- FR-056: Customer response is recorded in case timeline
"""

from datetime import datetime
from enum import Enum
from typing import TYPE_CHECKING, Optional
from uuid import UUID

from sqlalchemy import Column, DateTime, ForeignKey, String, Text
from sqlalchemy import Enum as SQLEnum
from src.models.base import DatabaseAgnosticUUID
from sqlalchemy.orm import Mapped, relationship

from src.models.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from src.models.case import Case
    from src.models.user import User
    from src.models.communication_template import CommunicationTemplate


class CommunicationDirection(str, Enum):
    """Direction of communication."""

    OUTBOUND = "OUTBOUND"  # To customer
    INBOUND = "INBOUND"    # From customer


class CommunicationMethod(str, Enum):
    """Method of communication."""

    EMAIL = "EMAIL"
    PHONE = "PHONE"
    LETTER = "LETTER"
    IN_APP = "IN_APP"
    OTHER = "OTHER"


class CustomerCommunication(Base, UUIDPrimaryKeyMixin):
    """
    Record of customer communication related to a case.

    Tracks both outbound requests for information and inbound
    customer responses.
    """

    __tablename__ = "customer_communications"

    # Case relationship
    case_id: Mapped[UUID] = Column(
        DatabaseAgnosticUUID(),
        ForeignKey("cases.id"),
        nullable=False,
        index=True
    )
    case: Mapped["Case"] = relationship("Case", backref="communications")

    # Communication details
    direction: Mapped[CommunicationDirection] = Column(
        SQLEnum(CommunicationDirection, name="communication_direction", create_type=False),
        nullable=False
    )
    method: Mapped[CommunicationMethod] = Column(
        SQLEnum(CommunicationMethod, name="communication_method", create_type=False),
        nullable=False
    )

    # Template used (for outbound)
    template_id: Mapped[Optional[UUID]] = Column(
        DatabaseAgnosticUUID(),
        ForeignKey("communication_templates.id"),
        nullable=True
    )
    template: Mapped[Optional["CommunicationTemplate"]] = relationship(
        "CommunicationTemplate"
    )

    # Content
    subject: Mapped[Optional[str]] = Column(String(500), nullable=True)
    content: Mapped[str] = Column(Text, nullable=False)

    # Response details (for inbound)
    response_summary: Mapped[Optional[str]] = Column(Text, nullable=True)
    received_at: Mapped[Optional[datetime]] = Column(
        DateTime(timezone=True),
        nullable=True
    )

    # Actor
    created_by_id: Mapped[UUID] = Column(
        DatabaseAgnosticUUID(),
        ForeignKey("users.id"),
        nullable=False
    )
    created_by: Mapped["User"] = relationship("User")

    # Timestamps
    created_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<CustomerCommunication {self.direction.value} case={self.case_id}>"

    @classmethod
    def create_outbound(
        cls,
        case_id: UUID,
        user_id: UUID,
        method: CommunicationMethod,
        subject: str,
        content: str,
        template_id: Optional[UUID] = None
    ) -> "CustomerCommunication":
        """
        Create an outbound communication to customer.

        Args:
            case_id: Associated case ID
            user_id: User sending the communication
            method: Communication method
            subject: Message subject
            content: Message content
            template_id: Optional template used

        Returns:
            New CustomerCommunication instance
        """
        return cls(
            case_id=case_id,
            direction=CommunicationDirection.OUTBOUND,
            method=method,
            template_id=template_id,
            subject=subject,
            content=content,
            created_by_id=user_id
        )

    @classmethod
    def record_inbound(
        cls,
        case_id: UUID,
        user_id: UUID,
        method: CommunicationMethod,
        response_summary: str,
        received_at: datetime
    ) -> "CustomerCommunication":
        """
        Record an inbound response from customer.

        Args:
            case_id: Associated case ID
            user_id: User recording the response
            method: How the response was received
            response_summary: Summary of customer response
            received_at: When the response was received

        Returns:
            New CustomerCommunication instance
        """
        return cls(
            case_id=case_id,
            direction=CommunicationDirection.INBOUND,
            method=method,
            content=response_summary,
            response_summary=response_summary,
            received_at=received_at,
            created_by_id=user_id
        )
