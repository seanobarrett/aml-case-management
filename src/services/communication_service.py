"""
Communication service for managing customer correspondence.

References:
- US-2: L1 Analyst requests additional information from customer
- FR-053: Case status changes to PENDING_INFORMATION
- FR-055: SLA pauses while awaiting customer response
- FR-056: Customer response is recorded in case timeline
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from src.models.case import Case, CaseStatus
from src.models.customer_communication import (
    CustomerCommunication,
    CommunicationDirection,
    CommunicationMethod
)
from src.models.timeline_entry import TimelineEntry
from src.services.template_service import TemplateService


class CommunicationService:
    """Service for managing customer communications."""

    def __init__(self, db: Session):
        """
        Initialize communication service.

        Args:
            db: Database session
        """
        self.db = db
        self.template_service = TemplateService(db)

    def request_information(
        self,
        case_id: UUID,
        user_id: UUID,
        template_id: str,
        custom_message: str,
        method: CommunicationMethod = CommunicationMethod.EMAIL
    ) -> CustomerCommunication:
        """
        Send an information request to customer.

        Updates case status to PENDING_INFORMATION and pauses SLA (FR-053, FR-055).

        Args:
            case_id: Case ID
            user_id: Requesting analyst ID
            template_id: Template to use
            custom_message: Custom message content
            method: Communication method

        Returns:
            Created CustomerCommunication

        Raises:
            ValueError: If template not found or case not found
        """
        # Get case
        case = self.db.query(Case).filter(Case.id == case_id).first()
        if not case:
            raise ValueError(f"Case not found: {case_id}")

        # Get template and render
        template = self.template_service.get_template(template_id)
        if not template:
            raise ValueError(f"Template not found: {template_id}")

        # Build context for template rendering
        context = {
            "case_reference": case.case_reference,
            "customer_name": case.customer.full_name if case.customer else "Customer",
            "custom_message": custom_message,
        }

        subject, body = template.render(context)

        # Create communication record
        communication = CustomerCommunication.create_outbound(
            case_id=case_id,
            user_id=user_id,
            method=method,
            subject=subject,
            content=body,
            template_id=template.id
        )
        self.db.add(communication)

        # Update case status (FR-053)
        case.status = CaseStatus.PENDING_INFORMATION

        # Record SLA pause time (FR-055)
        case.sla_pause_start = datetime.utcnow()
        case.sla_paused = True

        # Create timeline entry
        timeline_entry = TimelineEntry.create(
            case_id=case_id,
            entry_type="INFORMATION_REQUESTED",
            content=f"Information requested from customer via {method.value}. Template: {template.name}",
            acting_user_id=user_id
        )
        self.db.add(timeline_entry)

        self.db.commit()
        self.db.refresh(communication)

        return communication

    def record_response(
        self,
        case_id: UUID,
        user_id: UUID,
        response_method: CommunicationMethod,
        response_summary: str,
        received_at: datetime
    ) -> CustomerCommunication:
        """
        Record a customer response.

        Updates case status back to ASSIGNED and resumes SLA (FR-056).

        Args:
            case_id: Case ID
            user_id: Analyst recording the response
            response_method: How response was received
            response_summary: Summary of customer response
            received_at: When response was received

        Returns:
            Created CustomerCommunication

        Raises:
            ValueError: If case not found
        """
        # Get case
        case = self.db.query(Case).filter(Case.id == case_id).first()
        if not case:
            raise ValueError(f"Case not found: {case_id}")

        # Create communication record
        communication = CustomerCommunication.record_inbound(
            case_id=case_id,
            user_id=user_id,
            method=response_method,
            response_summary=response_summary,
            received_at=received_at
        )
        self.db.add(communication)

        # Update case status back to ASSIGNED
        case.status = CaseStatus.ASSIGNED

        # Resume SLA (FR-055) - calculate pause duration and adjust deadline
        if case.sla_pause_start and case.sla_deadline:
            pause_duration = datetime.utcnow() - case.sla_pause_start
            case.sla_deadline = case.sla_deadline + pause_duration
            case.sla_pause_start = None
            case.sla_paused = False

        # Create timeline entry
        timeline_entry = TimelineEntry.create(
            case_id=case_id,
            entry_type="CUSTOMER_RESPONSE_RECORDED",
            content=f"Customer response received via {response_method.value}: {response_summary[:100]}",
            acting_user_id=user_id
        )
        self.db.add(timeline_entry)

        self.db.commit()
        self.db.refresh(communication)

        return communication

    def get_case_communications(
        self,
        case_id: UUID,
        direction: Optional[CommunicationDirection] = None
    ) -> list[CustomerCommunication]:
        """
        Get all communications for a case.

        Args:
            case_id: Case ID
            direction: Filter by direction

        Returns:
            List of communications
        """
        query = self.db.query(CustomerCommunication).filter(
            CustomerCommunication.case_id == case_id
        )

        if direction:
            query = query.filter(CustomerCommunication.direction == direction)

        return query.order_by(CustomerCommunication.created_at.desc()).all()
