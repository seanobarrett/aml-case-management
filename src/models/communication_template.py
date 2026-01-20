"""
Communication template model for customer correspondence.

References:
- D10: Communication templates from YAML files
- FR-054: Communication templates are available
"""

from datetime import datetime
from enum import Enum
from typing import Optional

from sqlalchemy import Column, DateTime, Integer, String, Text, Boolean
from sqlalchemy import Enum as SQLEnum
from sqlalchemy.orm import Mapped

from src.models.base import Base, UUIDPrimaryKeyMixin


class TemplateCategory(str, Enum):
    """Communication template category."""

    IDENTITY_VERIFICATION = "IDENTITY_VERIFICATION"
    DOCUMENT_REQUEST = "DOCUMENT_REQUEST"
    FOLLOW_UP = "FOLLOW_UP"
    GENERAL = "GENERAL"


class CommunicationTemplate(Base, UUIDPrimaryKeyMixin):
    """
    Communication template for customer correspondence.

    Templates are loaded from YAML files on startup (D10) and stored
    in the database for easy management and versioning.
    """

    __tablename__ = "communication_templates"

    # Template identification
    template_id: Mapped[str] = Column(
        String(100),
        nullable=False,
        unique=True,
        index=True
    )
    name: Mapped[str] = Column(String(255), nullable=False)
    description: Mapped[Optional[str]] = Column(Text, nullable=True)

    # Template content
    subject: Mapped[str] = Column(String(500), nullable=False)
    body: Mapped[str] = Column(Text, nullable=False)

    # Categorization
    category: Mapped[TemplateCategory] = Column(
        SQLEnum(TemplateCategory, name="template_category", create_type=False),
        nullable=False,
        default=TemplateCategory.GENERAL
    )

    # Status
    is_active: Mapped[bool] = Column(Boolean, nullable=False, default=True)

    # Metadata
    version: Mapped[int] = Column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow
    )
    updated_at: Mapped[datetime] = Column(
        DateTime(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow
    )

    def __repr__(self) -> str:
        return f"<CommunicationTemplate {self.template_id}>"

    @classmethod
    def from_yaml(cls, template_id: str, data: dict) -> "CommunicationTemplate":
        """
        Create a template from YAML data.

        Args:
            template_id: Unique template identifier
            data: Template data from YAML file

        Returns:
            New CommunicationTemplate instance
        """
        category = data.get("category", "GENERAL")
        if isinstance(category, str):
            category = TemplateCategory(category.upper())

        return cls(
            template_id=template_id,
            name=data.get("name", template_id),
            description=data.get("description"),
            subject=data.get("subject", ""),
            body=data.get("body", ""),
            category=category,
            is_active=data.get("is_active", True)
        )

    def render(self, context: dict) -> tuple[str, str]:
        """
        Render template with context variables.

        Args:
            context: Variables to substitute in template

        Returns:
            Tuple of (rendered_subject, rendered_body)
        """
        rendered_subject = self.subject
        rendered_body = self.body

        for key, value in context.items():
            placeholder = f"{{{{{key}}}}}"
            rendered_subject = rendered_subject.replace(placeholder, str(value))
            rendered_body = rendered_body.replace(placeholder, str(value))

        return rendered_subject, rendered_body
