"""
Communication templates API endpoints.

References:
- D10: Communication templates from YAML files
- FR-054: Communication templates are available
"""

from typing import Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from src.middleware.auth import CurrentUser, get_current_user
from src.services.template_service import TemplateService
from src.models.communication_template import TemplateCategory
from src.db.session import get_db


router = APIRouter(prefix="/templates", tags=["templates"])


class TemplateItem(BaseModel):
    """Template in list response."""
    id: str
    templateId: str
    name: str
    description: str | None
    category: str
    subject: str
    body: str
    isActive: bool


class TemplateListResponse(BaseModel):
    """Template list response."""
    items: list[TemplateItem]
    total: int


@router.get(
    "/communication",
    response_model=TemplateListResponse,
    summary="List communication templates"
)
async def list_templates(
    category: Optional[str] = None,
    user: CurrentUser = Depends(get_current_user),
    db=Depends(get_db)
):
    """
    List available communication templates.

    Templates can be used for customer information requests (FR-054).
    """
    service = TemplateService(db)

    # Parse category filter
    category_filter = None
    if category:
        try:
            category_filter = TemplateCategory(category.upper())
        except ValueError:
            pass

    templates = service.list_templates(category=category_filter)

    return TemplateListResponse(
        items=[
            TemplateItem(
                id=str(template.id),
                templateId=template.template_id,
                name=template.name,
                description=template.description,
                category=template.category.value,
                subject=template.subject,
                body=template.body,
                isActive=template.is_active
            )
            for template in templates
        ],
        total=len(templates)
    )
