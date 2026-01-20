"""
Enhanced Due Diligence (EDD) checklist model.

References:
- US-7: High-confidence PEP requires EDD
- FR-033: EDD checklist requirements
- FR-034: EDD completion workflow
"""

import enum
from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from sqlalchemy import Column, String, DateTime, Enum, ForeignKey, Text, Boolean
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from src.models.base import Base, DatabaseAgnosticUUID


class EDDItemType(enum.Enum):
    """Types of EDD checklist items."""
    SOURCE_OF_WEALTH = "SOURCE_OF_WEALTH"
    SOURCE_OF_FUNDS = "SOURCE_OF_FUNDS"
    PEP_RELATIONSHIP = "PEP_RELATIONSHIP"
    BUSINESS_PURPOSE = "BUSINESS_PURPOSE"
    EXPECTED_TRANSACTIONS = "EXPECTED_TRANSACTIONS"
    BENEFICIAL_OWNERSHIP = "BENEFICIAL_OWNERSHIP"
    THIRD_PARTY_VERIFICATION = "THIRD_PARTY_VERIFICATION"


class EDDChecklist(Base):
    """
    Enhanced Due Diligence checklist for high-risk customers.

    Required for high-confidence PEP cases before case can be closed.
    """
    __tablename__ = "edd_checklists"

    id = Column(DatabaseAgnosticUUID(), primary_key=True, default=uuid4)
    case_id = Column(DatabaseAgnosticUUID(), ForeignKey("cases.id"), nullable=False, unique=True)

    # Status tracking
    is_required = Column(Boolean, nullable=False, default=True)
    is_completed = Column(Boolean, nullable=False, default=False)
    completed_at = Column(DateTime, nullable=True)
    completed_by_id = Column(DatabaseAgnosticUUID(), ForeignKey("users.id"), nullable=True)

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    case = relationship("Case", backref="edd_checklist", uselist=False)
    completed_by = relationship("User", foreign_keys=[completed_by_id])
    items = relationship(
        "EDDChecklistItem",
        back_populates="checklist",
        cascade="all, delete-orphan",
        order_by="EDDChecklistItem.item_type"
    )

    @classmethod
    def create_for_case(cls, case_id: UUID) -> "EDDChecklist":
        """Create a new EDD checklist with default items."""
        checklist = cls(case_id=case_id)
        return checklist

    def mark_completed(self, user_id: UUID) -> None:
        """Mark the checklist as completed."""
        self.is_completed = True
        self.completed_at = datetime.utcnow()
        self.completed_by_id = user_id

    @property
    def all_items_completed(self) -> bool:
        """Check if all required items are completed."""
        return all(item.is_completed for item in self.items if item.is_required)

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "id": str(self.id),
            "caseId": str(self.case_id),
            "required": self.is_required,
            "completed": self.is_completed,
            "completedAt": self.completed_at.isoformat() if self.completed_at else None,
            "completedById": str(self.completed_by_id) if self.completed_by_id else None,
            "items": [item.to_dict() for item in self.items],
            "createdAt": self.created_at.isoformat() if self.created_at else None,
            "updatedAt": self.updated_at.isoformat() if self.updated_at else None,
        }


class EDDChecklistItem(Base):
    """
    Individual item in an EDD checklist.
    """
    __tablename__ = "edd_checklist_items"

    id = Column(DatabaseAgnosticUUID(), primary_key=True, default=uuid4)
    checklist_id = Column(
        DatabaseAgnosticUUID(),
        ForeignKey("edd_checklists.id"),
        nullable=False
    )

    # Item details
    item_type = Column(Enum(EDDItemType), nullable=False)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=True)
    is_required = Column(Boolean, nullable=False, default=True)

    # Completion status
    is_completed = Column(Boolean, nullable=False, default=False)
    completed_at = Column(DateTime, nullable=True)
    completed_by_id = Column(DatabaseAgnosticUUID(), ForeignKey("users.id"), nullable=True)
    notes = Column(Text, nullable=True)

    # Supporting evidence
    evidence_references = Column(JSONB, nullable=True)  # List of document references

    # Timestamps
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    checklist = relationship("EDDChecklist", back_populates="items")
    completed_by = relationship("User", foreign_keys=[completed_by_id])

    @classmethod
    def create_default_items(cls, checklist_id: UUID) -> list["EDDChecklistItem"]:
        """Create default EDD checklist items."""
        default_items = [
            {
                "item_type": EDDItemType.SOURCE_OF_WEALTH,
                "title": "Source of Wealth Verification",
                "description": "Verify and document the customer's source of wealth (employment, business, inheritance, etc.)",
                "is_required": True,
            },
            {
                "item_type": EDDItemType.SOURCE_OF_FUNDS,
                "title": "Source of Funds Verification",
                "description": "Verify and document the source of funds for the account (salary, savings, investment returns, etc.)",
                "is_required": True,
            },
            {
                "item_type": EDDItemType.PEP_RELATIONSHIP,
                "title": "PEP Relationship Assessment",
                "description": "Document the nature of the PEP relationship and any current political exposure",
                "is_required": True,
            },
            {
                "item_type": EDDItemType.BUSINESS_PURPOSE,
                "title": "Business Purpose Documentation",
                "description": "Document the intended purpose for the banking relationship",
                "is_required": True,
            },
            {
                "item_type": EDDItemType.EXPECTED_TRANSACTIONS,
                "title": "Expected Transaction Profile",
                "description": "Document expected transaction patterns and volumes",
                "is_required": False,
            },
            {
                "item_type": EDDItemType.BENEFICIAL_OWNERSHIP,
                "title": "Beneficial Ownership Verification",
                "description": "Verify and document any beneficial ownership structures",
                "is_required": False,
            },
        ]

        items = []
        for item_data in default_items:
            item = cls(checklist_id=checklist_id, **item_data)
            items.append(item)

        return items

    def complete(self, user_id: UUID, notes: str = None) -> None:
        """Mark this item as completed."""
        self.is_completed = True
        self.completed_at = datetime.utcnow()
        self.completed_by_id = user_id
        if notes:
            self.notes = notes

    def to_dict(self) -> dict:
        """Convert to dictionary representation."""
        return {
            "id": str(self.id),
            "itemId": self.item_type.value,
            "title": self.title,
            "description": self.description,
            "required": self.is_required,
            "completed": self.is_completed,
            "completedAt": self.completed_at.isoformat() if self.completed_at else None,
            "completedById": str(self.completed_by_id) if self.completed_by_id else None,
            "notes": self.notes,
            "evidenceReferences": self.evidence_references,
        }
