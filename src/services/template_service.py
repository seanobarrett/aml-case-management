"""
Template service for loading and managing communication templates.

References:
- D10: Communication templates from YAML files
- FR-054: Communication templates are available
"""

import logging
from pathlib import Path
from typing import Optional

import yaml
from sqlalchemy.orm import Session

from src.models.communication_template import CommunicationTemplate, TemplateCategory

logger = logging.getLogger(__name__)


# Default templates to seed if no YAML files found
DEFAULT_TEMPLATES = [
    {
        "id": "identity-verification",
        "name": "Identity Verification Request",
        "description": "Request additional identity documents from customer",
        "category": "IDENTITY_VERIFICATION",
        "subject": "Additional Identity Verification Required - {{case_reference}}",
        "body": """Dear {{customer_name}},

We are writing regarding your account verification with Spriggy.

We require additional documentation to complete our verification process. Please provide the following:

{{custom_message}}

Please respond within 5 business days to avoid any delays.

If you have any questions, please contact our support team.

Best regards,
Spriggy Compliance Team"""
    },
    {
        "id": "document-request",
        "name": "Document Request",
        "description": "General document request template",
        "category": "DOCUMENT_REQUEST",
        "subject": "Document Request - {{case_reference}}",
        "body": """Dear {{customer_name}},

We require the following document(s) for your account:

{{custom_message}}

Please submit these documents at your earliest convenience.

Best regards,
Spriggy Compliance Team"""
    },
    {
        "id": "follow-up",
        "name": "Follow Up",
        "description": "Follow up on previous request",
        "category": "FOLLOW_UP",
        "subject": "Follow Up - {{case_reference}}",
        "body": """Dear {{customer_name}},

This is a follow-up regarding our previous request dated {{original_request_date}}.

We have not yet received a response. Please note that failure to respond may result in restrictions on your account.

{{custom_message}}

Please respond at your earliest convenience.

Best regards,
Spriggy Compliance Team"""
    },
    {
        "id": "general-enquiry",
        "name": "General Enquiry",
        "description": "General communication template",
        "category": "GENERAL",
        "subject": "Enquiry Regarding Your Account - {{case_reference}}",
        "body": """Dear {{customer_name}},

{{custom_message}}

Please contact us if you have any questions.

Best regards,
Spriggy Compliance Team"""
    }
]


class TemplateService:
    """Service for managing communication templates."""

    def __init__(self, db: Session, templates_dir: Optional[Path] = None):
        """
        Initialize template service.

        Args:
            db: Database session
            templates_dir: Directory containing YAML template files
        """
        self.db = db
        self.templates_dir = templates_dir or Path("templates/communication")

    def load_templates_from_yaml(self) -> int:
        """
        Load templates from YAML files.

        Returns:
            Number of templates loaded
        """
        count = 0

        if not self.templates_dir.exists():
            logger.warning(
                f"Templates directory not found: {self.templates_dir}. "
                "Loading default templates."
            )
            return self._load_default_templates()

        for yaml_file in self.templates_dir.glob("*.yaml"):
            try:
                with open(yaml_file) as f:
                    data = yaml.safe_load(f)

                if not data:
                    continue

                templates = data if isinstance(data, list) else [data]

                for template_data in templates:
                    template_id = template_data.get("id")
                    if not template_id:
                        logger.warning(f"Template in {yaml_file} missing 'id' field")
                        continue

                    self._upsert_template(template_id, template_data)
                    count += 1

            except yaml.YAMLError as e:
                logger.error(f"Error parsing {yaml_file}: {e}")
            except Exception as e:
                logger.error(f"Error loading {yaml_file}: {e}")

        if count == 0:
            logger.info("No templates found in YAML files. Loading defaults.")
            return self._load_default_templates()

        self.db.commit()
        logger.info(f"Loaded {count} templates from YAML files")
        return count

    def _load_default_templates(self) -> int:
        """Load default templates."""
        count = 0
        for template_data in DEFAULT_TEMPLATES:
            template_id = template_data["id"]
            self._upsert_template(template_id, template_data)
            count += 1

        self.db.commit()
        logger.info(f"Loaded {count} default templates")
        return count

    def _upsert_template(self, template_id: str, data: dict) -> CommunicationTemplate:
        """
        Insert or update a template.

        Args:
            template_id: Template identifier
            data: Template data

        Returns:
            CommunicationTemplate instance
        """
        existing = self.db.query(CommunicationTemplate).filter(
            CommunicationTemplate.template_id == template_id
        ).first()

        if existing:
            # Update existing template
            existing.name = data.get("name", template_id)
            existing.description = data.get("description")
            existing.subject = data.get("subject", "")
            existing.body = data.get("body", "")
            existing.is_active = data.get("is_active", True)

            category = data.get("category", "GENERAL")
            if isinstance(category, str):
                existing.category = TemplateCategory(category.upper())
            else:
                existing.category = category

            existing.version += 1
            return existing
        else:
            # Create new template
            template = CommunicationTemplate.from_yaml(template_id, data)
            self.db.add(template)
            return template

    def get_template(self, template_id: str) -> Optional[CommunicationTemplate]:
        """
        Get a template by ID.

        Args:
            template_id: Template identifier

        Returns:
            CommunicationTemplate or None
        """
        return self.db.query(CommunicationTemplate).filter(
            CommunicationTemplate.template_id == template_id,
            CommunicationTemplate.is_active == True
        ).first()

    def list_templates(
        self,
        category: Optional[TemplateCategory] = None,
        active_only: bool = True
    ) -> list[CommunicationTemplate]:
        """
        List available templates.

        Args:
            category: Filter by category
            active_only: Only return active templates

        Returns:
            List of templates
        """
        query = self.db.query(CommunicationTemplate)

        if active_only:
            query = query.filter(CommunicationTemplate.is_active == True)

        if category:
            query = query.filter(CommunicationTemplate.category == category)

        return query.order_by(CommunicationTemplate.name).all()

    def render_template(
        self,
        template_id: str,
        context: dict
    ) -> Optional[tuple[str, str]]:
        """
        Render a template with context.

        Args:
            template_id: Template to render
            context: Variables for substitution

        Returns:
            Tuple of (subject, body) or None if template not found
        """
        template = self.get_template(template_id)
        if not template:
            return None

        return template.render(context)
