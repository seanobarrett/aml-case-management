"""
Case link model for related cases.

References:
- FR-046: Case linking for related cases
- EC-014: New alerts for customers with open cases are linked
- FR-044, FR-045: Supplementary SMR cases
"""

import enum
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import Column, String, DateTime, Enum, ForeignKey, Text, UniqueConstraint
from src.models.base import DatabaseAgnosticUUID
from sqlalchemy.orm import relationship

from src.models.base import Base


class CaseLinkType(enum.Enum):
    """Type of relationship between linked cases."""
    NEW_ALERT = "NEW_ALERT"  # New alert for same customer while case open (EC-014)
    SUPPLEMENTARY_TO_ORIGINAL = "SUPPLEMENTARY_TO_ORIGINAL"  # Supplementary SMR case (FR-046)
    RELATED_CUSTOMER = "RELATED_CUSTOMER"  # Cases for related customers
    MERGED = "MERGED"  # Cases that were merged together


class CaseLink(Base):
    """
    Links between related cases.

    Enables bidirectional navigation between cases that are related,
    such as:
    - New alerts for customers with existing open cases (EC-014)
    - Supplementary SMR filings linked to original case (FR-046)
    - Manually linked related cases

    Links are always bidirectional - if A links to B, B links to A.
    """
    __tablename__ = "case_links"

    id = Column(DatabaseAgnosticUUID(), primary_key=True, default=uuid4)

    # Source case (the case where the link is viewed from)
    source_case_id = Column(
        DatabaseAgnosticUUID(),
        ForeignKey("cases.id"),
        nullable=False,
        index=True
    )

    # Target case (the linked case)
    target_case_id = Column(
        DatabaseAgnosticUUID(),
        ForeignKey("cases.id"),
        nullable=False,
        index=True
    )

    # Link metadata
    link_type = Column(Enum(CaseLinkType), nullable=False)
    description = Column(Text, nullable=True)
    created_by_id = Column(DatabaseAgnosticUUID(), ForeignKey("users.id"), nullable=True)

    # For supplementary SMR links, track the original/supplementary relationship
    is_primary = Column(String(10), nullable=False, default="false")  # "true" for original case

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)

    # Relationships
    source_case = relationship(
        "Case",
        foreign_keys=[source_case_id],
        back_populates="outgoing_links"
    )
    target_case = relationship(
        "Case",
        foreign_keys=[target_case_id],
        back_populates="incoming_links"
    )
    created_by = relationship("User", foreign_keys=[created_by_id])

    # Ensure no duplicate links between same cases with same type
    __table_args__ = (
        UniqueConstraint(
            'source_case_id', 'target_case_id', 'link_type',
            name='uq_case_link_source_target_type'
        ),
    )

    @classmethod
    def create_bidirectional_link(
        cls,
        case_a_id: UUID,
        case_b_id: UUID,
        link_type: CaseLinkType,
        description: str = None,
        created_by_id: UUID = None,
        primary_case_id: UUID = None
    ) -> tuple["CaseLink", "CaseLink"]:
        """
        Create bidirectional links between two cases.

        Returns both link objects for persistence.
        """
        link_a_to_b = cls(
            source_case_id=case_a_id,
            target_case_id=case_b_id,
            link_type=link_type,
            description=description,
            created_by_id=created_by_id,
            is_primary="true" if primary_case_id == case_a_id else "false"
        )

        link_b_to_a = cls(
            source_case_id=case_b_id,
            target_case_id=case_a_id,
            link_type=link_type,
            description=description,
            created_by_id=created_by_id,
            is_primary="true" if primary_case_id == case_b_id else "false"
        )

        return link_a_to_b, link_b_to_a

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "id": str(self.id),
            "caseId": str(self.target_case_id),
            "linkType": self.link_type.value,
            "description": self.description,
            "isPrimary": self.is_primary == "true",
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "createdById": str(self.created_by_id) if self.created_by_id else None,
        }
