"""
Case service for AML case management operations.

References:
- FR-001: System receives GreenID/Indue webhooks
- FR-003: System generates unique case reference
- FR-004: System captures case creation timestamp
- FR-005: System sets initial case status (OPEN)
- D2: SLA calculation engine
"""

from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID

from sqlalchemy.orm import Session

from src.models.case import Case, CaseStatus, CaseType, CaseTier, L2ReviewStatus
from src.models.customer import Customer
from src.models.assignment import Assignment, AssignmentReason
from src.models.webhook_receipt import WebhookReceipt
from src.middleware.auth import TierMismatchError


class DuplicateWebhookError(Exception):
    """Raised when a duplicate webhook is detected."""

    def __init__(self, message: str = "Duplicate webhook detected"):
        self.message = message
        super().__init__(self.message)


class CaseNotFoundError(Exception):
    """Raised when a case is not found."""

    def __init__(self, case_id: str):
        self.case_id = case_id
        self.message = f"Case not found: {case_id}"
        super().__init__(self.message)


class AccountClosureBlockError(Exception):
    """Raised when auto-closure is blocked due to customer account closure (EC-008)."""

    def __init__(self, case_reference: str, customer_id: str):
        self.case_reference = case_reference
        self.customer_id = customer_id
        self.message = f"Auto-closure blocked for case {case_reference}: customer account is closed"
        super().__init__(self.message)


class CaseService:
    """Service for case management operations."""

    # Default SLA days by case type
    SLA_DAYS = {
        CaseType.KYC_REMEDIATION: 5,
        CaseType.PEP_SCREENING: 3,
        CaseType.PEP_HIGH_CONFIDENCE: 3,
        CaseType.PEP_LOW_CONFIDENCE: 5,
        CaseType.SANCTIONS_ONBOARDING: 1,
        CaseType.SANCTIONS_EXISTING_CUSTOMER: 3,
        CaseType.SANCTIONS_PEP_COMBINED: 1,  # FR-035: Most urgent SLA
        CaseType.SUSPICIOUS_ACTIVITY: 10,
        CaseType.SMR_SUPPLEMENTARY: 5,  # FR-044: Supplementary SMR filing
    }

    def __init__(self, db: Session):
        self.db = db

    def create_case_from_greenid_webhook(
        self,
        payload: dict,
        customer_data: dict
    ) -> Case:
        """
        Create a case from GreenID webhook payload.

        Args:
            payload: GreenID webhook payload
            customer_data: Customer data from payload

        Returns:
            Created Case instance

        Raises:
            DuplicateWebhookError: If webhook was already processed
        """
        # Check for duplicate webhook (EC-005)
        payload_hash = WebhookReceipt.compute_payload_hash(payload)
        existing_receipt = self.db.query(WebhookReceipt).filter(
            WebhookReceipt.payload_hash == payload_hash
        ).first()

        if existing_receipt:
            raise DuplicateWebhookError(
                f"Webhook already processed at {existing_receipt.received_at}"
            )

        # Create webhook receipt
        receipt = WebhookReceipt.create(
            payload=payload,
            webhook_source="greenid",
            external_id=payload.get("verificationId")
        )
        self.db.add(receipt)

        # Create customer snapshot
        customer = Customer.create_snapshot(
            external_customer_id=payload.get("customerId", ""),
            first_name=customer_data.get("firstName"),
            last_name=customer_data.get("lastName"),
            email=customer_data.get("email"),
            date_of_birth=self._parse_date(customer_data.get("dateOfBirth")),
            onboarding_status=payload.get("verificationType"),
        )
        self.db.add(customer)
        self.db.flush()  # Get customer ID

        # Determine case type
        case_type = self._determine_greenid_case_type(payload)

        # Calculate SLA deadline
        sla_deadline = self._calculate_sla_deadline(case_type)

        # Determine tier - combined cases go to L2
        tier = CaseTier.L2 if case_type == CaseType.SANCTIONS_PEP_COMBINED else CaseTier.L1

        # Set alert types for combined cases
        alert_types = None
        if case_type == CaseType.SANCTIONS_PEP_COMBINED:
            alert_types = ["SANCTIONS", "PEP"]

        # Create case with generated reference
        case = Case(
            case_reference=Case.generate_reference(self.db),
            case_type=case_type,
            status=CaseStatus.OPEN,
            tier=tier,
            customer_id=customer.id,
            sla_deadline=sla_deadline,
            external_verification_id=payload.get("verificationId"),
            source_webhook_payload=payload,
            alert_types=alert_types,
        )
        self.db.add(case)
        self.db.flush()

        # Update receipt with case ID
        receipt.mark_processed(case.id)

        self.db.commit()
        self.db.refresh(case)

        return case

    def create_case_from_indue_webhook(
        self,
        payload: dict,
        customer_id: str
    ) -> Case:
        """
        Create a case from Indue webhook payload.

        Args:
            payload: Indue webhook payload
            customer_id: Customer external ID

        Returns:
            Created Case instance

        Raises:
            DuplicateWebhookError: If webhook was already processed
        """
        # Check for duplicate webhook
        payload_hash = WebhookReceipt.compute_payload_hash(payload)
        existing_receipt = self.db.query(WebhookReceipt).filter(
            WebhookReceipt.payload_hash == payload_hash
        ).first()

        if existing_receipt:
            raise DuplicateWebhookError(
                f"Webhook already processed at {existing_receipt.received_at}"
            )

        # Create webhook receipt
        receipt = WebhookReceipt.create(
            payload=payload,
            webhook_source="indue",
            external_id=payload.get("screeningId")
        )
        self.db.add(receipt)

        # Create or find customer snapshot
        customer = Customer.create_snapshot(
            external_customer_id=customer_id,
        )
        self.db.add(customer)
        self.db.flush()

        # Determine case type based on screening type
        case_type = self._determine_indue_case_type(payload)

        # Calculate SLA deadline
        sla_deadline = self._calculate_sla_deadline(case_type)

        # Create case with generated reference
        case = Case(
            case_reference=Case.generate_reference(self.db),
            case_type=case_type,
            status=CaseStatus.OPEN,
            tier=CaseTier.L1,
            customer_id=customer.id,
            sla_deadline=sla_deadline,
            external_screening_id=payload.get("screeningId"),
            pep_match_score=payload.get("matchScore"),
            source_webhook_payload=payload,
        )
        self.db.add(case)
        self.db.flush()

        # Update receipt
        receipt.mark_processed(case.id)

        self.db.commit()
        self.db.refresh(case)

        return case

    def get_case_by_id(self, case_id: UUID) -> Optional[Case]:
        """
        Get case by ID.

        Args:
            case_id: Case UUID

        Returns:
            Case instance or None
        """
        return self.db.query(Case).filter(Case.id == case_id).first()

    def get_case_by_reference(self, reference: str) -> Optional[Case]:
        """
        Get case by reference number.

        Args:
            reference: Case reference (e.g., 'AML-1001')

        Returns:
            Case instance or None
        """
        return self.db.query(Case).filter(Case.case_reference == reference).first()

    # Sentinel value to distinguish "no filter" from "filter for None"
    _UNSET = object()

    def list_cases(
        self,
        status: Optional[CaseStatus] = None,
        status_list: Optional[list[CaseStatus]] = None,
        tier: Optional[CaseTier] = None,
        assigned_to_id: Optional[UUID] = _UNSET,
        unassigned_only: bool = False,
        page: int = 1,
        page_size: int = 20,
        sort_by: str = "sla_deadline"
    ) -> tuple[list[Case], int]:
        """
        List cases with filtering and pagination.

        Args:
            status: Filter by single status
            status_list: Filter by multiple statuses (OR logic)
            tier: Filter by tier
            assigned_to_id: Filter by assigned user
            unassigned_only: If True, only return cases with no assignee
            page: Page number (1-indexed)
            page_size: Items per page
            sort_by: Sort field

        Returns:
            Tuple of (cases list, total count)
        """
        query = self.db.query(Case)

        # Apply filters
        if status_list:
            query = query.filter(Case.status.in_(status_list))
        elif status:
            query = query.filter(Case.status == status)
        if tier:
            query = query.filter(Case.tier == tier)
        if unassigned_only:
            query = query.filter(Case.assigned_to_id.is_(None))
        elif assigned_to_id is not self._UNSET and assigned_to_id is not None:
            query = query.filter(Case.assigned_to_id == assigned_to_id)

        # Get total count
        total = query.count()

        # Apply sorting
        if sort_by == "sla_deadline":
            query = query.order_by(Case.sla_deadline.asc().nullslast())
        elif sort_by == "created_at":
            query = query.order_by(Case.created_at.desc())
        elif sort_by == "case_reference":
            query = query.order_by(Case.case_reference.asc())

        # Apply pagination
        offset = (page - 1) * page_size
        cases = query.offset(offset).limit(page_size).all()

        return cases, total

    def claim_case(self, case_id: UUID, user_id: UUID) -> Case:
        """
        Claim a case for an analyst.

        Args:
            case_id: Case to claim
            user_id: User claiming the case

        Returns:
            Updated Case instance

        Raises:
            CaseNotFoundError: If case doesn't exist
        """
        case = self.get_case_by_id(case_id)
        if not case:
            raise CaseNotFoundError(str(case_id))

        # Implicit claim - if unassigned, automatically claim
        # Create assignment record
        assignment = Assignment.create_claim(case_id, user_id)
        self.db.add(assignment)

        # Update case
        case.claim(user_id)

        self.db.commit()
        self.db.refresh(case)

        return case

    def close_case(
        self,
        case_id: UUID,
        user_id: UUID,
        user_role: str,
        reason: str,
        documentation: str,
        is_auto_closure: bool = False
    ) -> Case:
        """
        Close a case with documentation.

        Args:
            case_id: Case to close
            user_id: User closing the case
            user_role: User's role
            reason: Closure reason
            documentation: Supporting documentation
            is_auto_closure: Whether this is an automatic closure (EC-008)

        Returns:
            Updated Case instance

        Raises:
            CaseNotFoundError: If case doesn't exist
            TierMismatchError: If L1 tries to close L2 case
            AccountClosureBlockError: If auto-closure blocked due to account closure
        """
        case = self.get_case_by_id(case_id)
        if not case:
            raise CaseNotFoundError(str(case_id))

        # Check tier access
        if case.tier == CaseTier.L2 and user_role == "L1_ANALYST":
            raise TierMismatchError("L1_ANALYST", "L2")

        # EC-008: Prevent auto-closure when customer account is closed
        if is_auto_closure and case.customer and case.customer.account_closed:
            raise AccountClosureBlockError(
                case.case_reference,
                case.customer.external_customer_id
            )

        # Implicit claim if not assigned (D13)
        if not case.is_assigned:
            assignment = Assignment.create_claim(case_id, user_id)
            self.db.add(assignment)
            case.assigned_to_id = user_id

        # Determine if L2 review required (L1 closing L1 case)
        requires_l2_review = (
            user_role == "L1_ANALYST" and
            case.tier == CaseTier.L1
        )

        case.close(reason, documentation, requires_l2_review)

        # FR-029: Clear onboarding block on case closure
        self._clear_onboarding_block_if_exists(case_id, user_id)

        self.db.commit()
        self.db.refresh(case)

        return case

    def _clear_onboarding_block_if_exists(
        self,
        case_id: UUID,
        user_id: UUID
    ) -> None:
        """
        Clear onboarding block if one exists for this case (FR-029).

        Args:
            case_id: Case ID
            user_id: User clearing the block
        """
        from src.services.onboarding_block_service import OnboardingBlockService

        block_service = OnboardingBlockService(self.db)
        block_service.clear_block(case_id, user_id)

    def mark_customer_account_closed(
        self,
        customer_id: str,
        closure_date: str,
        reason: Optional[str] = None
    ) -> int:
        """
        Mark all active cases for a customer as having a closed account (EC-008).

        Args:
            customer_id: External customer ID
            closure_date: Date of account closure
            reason: Optional closure reason

        Returns:
            Number of affected cases
        """
        from src.models.customer import Customer

        # Find customers by external ID
        customers = self.db.query(Customer).filter(
            Customer.external_customer_id == customer_id
        ).all()

        if not customers:
            return 0

        customer_ids = [c.id for c in customers]

        # Find all active cases for these customers
        active_statuses = [
            CaseStatus.OPEN,
            CaseStatus.ASSIGNED,
            CaseStatus.PENDING_INFORMATION,
            CaseStatus.ESCALATED,
            CaseStatus.PENDING_APPROVAL
        ]

        cases = self.db.query(Case).filter(
            Case.customer_id.in_(customer_ids),
            Case.status.in_(active_statuses)
        ).all()

        # Update all matching customer records
        for customer in customers:
            customer.account_closed = True
            customer.account_closed_at = self._parse_date(closure_date) or datetime.utcnow()
            customer.account_closure_reason = reason

        self.db.commit()

        return len(cases)

    def escalate_case(
        self,
        case_id: UUID,
        user_id: UUID,
        reason: str,
        findings: str
    ) -> Case:
        """
        Escalate a case from L1 to L2.

        Args:
            case_id: Case to escalate
            user_id: User escalating the case
            reason: Reason for escalation
            findings: Initial investigation findings

        Returns:
            Updated Case instance

        Raises:
            CaseNotFoundError: If case doesn't exist
        """
        from src.services.notification_service import NotificationService
        from src.services.audit_service import AuditService

        case = self.get_case_by_id(case_id)
        if not case:
            raise CaseNotFoundError(str(case_id))

        # Escalate the case (changes tier to L2, status to ESCALATED, unassigns)
        case.escalate()

        # Store escalation details
        case.escalation_reason = reason
        case.escalation_findings = findings
        case.escalated_by_id = user_id
        case.escalated_at = datetime.utcnow()

        # Create audit log and timeline entry
        audit_service = AuditService(self.db)
        audit_service.log_case_escalated(
            case_id=case_id,
            user_id=user_id,
            reason=reason
        )

        # Create notifications for L2 analysts (FR-068)
        notification_service = NotificationService(self.db)
        notification_service.notify_escalation(
            case_id=case_id,
            case_reference=case.case_reference
        )

        self.db.commit()
        self.db.refresh(case)

        return case

    def create_supplementary_case(
        self,
        original_case_id: UUID,
        reason: str,
        new_evidence: str,
        created_by_id: UUID
    ) -> Case:
        """
        Create a supplementary SMR case linked to an original case (FR-044).

        Supplementary cases:
        - Can only be created from closed cases with filed SMRs
        - Inherit customer information from original
        - Follow full SMR workflow (FR-045)
        - Support multiple supplementary filings per original (FR-047)

        Args:
            original_case_id: ID of the original case
            reason: Reason for supplementary filing
            new_evidence: New evidence discovered
            created_by_id: User creating the supplementary case

        Returns:
            Created supplementary Case instance

        Raises:
            CaseNotFoundError: If original case doesn't exist
            ValueError: If original case not eligible for supplementary
        """
        from src.services.case_link_service import CaseLinkService
        from src.models.smr_recommendation import SMRRecommendation, SMRStatus

        # Get original case
        original_case = self.get_case_by_id(original_case_id)
        if not original_case:
            raise CaseNotFoundError(str(original_case_id))

        # Validate original case is closed
        if original_case.status != CaseStatus.CLOSED:
            raise ValueError(
                "Supplementary cases can only be created from closed cases"
            )

        # Validate original case has a filed SMR
        filed_smr = self.db.query(SMRRecommendation).filter(
            SMRRecommendation.case_id == original_case_id,
            SMRRecommendation.status.in_([SMRStatus.APPROVED, SMRStatus.FILED])
        ).first()

        if not filed_smr:
            raise ValueError(
                "Supplementary cases can only be created for cases with filed SMRs"
            )

        # Create supplementary case with same customer
        supplementary_case = Case(
            case_reference=Case.generate_reference(self.db),
            case_type=CaseType.SMR_SUPPLEMENTARY,
            status=CaseStatus.OPEN,
            tier=CaseTier.L2,  # Supplementary always goes to L2
            customer_id=original_case.customer_id,
            sla_deadline=self._calculate_sla_deadline(CaseType.SMR_SUPPLEMENTARY),
            supplementary_reason=reason,
            supplementary_evidence=new_evidence,
            original_case_id=original_case_id,
        )
        self.db.add(supplementary_case)
        self.db.flush()

        # Create bidirectional link
        link_service = CaseLinkService(self.db)
        link_service.link_supplementary_case(
            original_case_id=original_case_id,
            supplementary_case_id=supplementary_case.id,
            created_by_id=created_by_id
        )

        self.db.commit()
        self.db.refresh(supplementary_case)

        return supplementary_case

    def get_open_cases_for_customer(self, external_customer_id: str) -> list[Case]:
        """
        Get all open cases for a customer by external ID (EC-014).

        Used to link new alerts to existing open cases.

        Args:
            external_customer_id: External customer identifier

        Returns:
            List of open Case instances for the customer
        """
        # Expire any cached objects to ensure we get fresh data
        self.db.expire_all()

        # Find customer IDs
        customers = self.db.query(Customer).filter(
            Customer.external_customer_id == external_customer_id
        ).all()

        if not customers:
            return []

        customer_ids = [c.id for c in customers]

        # Find open cases (not closed or approved)
        open_statuses = [
            CaseStatus.OPEN,
            CaseStatus.ASSIGNED,
            CaseStatus.PENDING_INFORMATION,
            CaseStatus.ESCALATED,
            CaseStatus.PENDING_APPROVAL
        ]

        return self.db.query(Case).filter(
            Case.customer_id.in_(customer_ids),
            Case.status.in_(open_statuses)
        ).all()

    def _determine_greenid_case_type(self, payload: dict) -> CaseType:
        """Determine case type from GreenID payload."""
        verification_type = payload.get("verificationType", "")
        alert_type = payload.get("alertType", "")

        # Handle combined alerts (FR-035) - via verificationType
        if verification_type == "SANCTIONS_PEP_COMBINED":
            return CaseType.SANCTIONS_PEP_COMBINED

        # Handle combined alerts (FR-035) - via alertType
        if alert_type == "COMBINED":
            alerts = payload.get("alerts", [])
            alert_types = [a.get("type") for a in alerts]
            if "SANCTIONS_HIT" in alert_types and "PEP_HIT" in alert_types:
                return CaseType.SANCTIONS_PEP_COMBINED

        # Handle sanctions alerts
        if verification_type == "SANCTIONS" or alert_type == "SANCTIONS_HIT":
            return CaseType.SANCTIONS_ONBOARDING

        # Handle PEP alerts
        if alert_type == "PEP_HIT":
            # Default to screening, will be refined by PEP service
            return CaseType.PEP_SCREENING

        if verification_type == "KYC_REMEDIATION":
            return CaseType.KYC_REMEDIATION

        return CaseType.KYC_REMEDIATION

    def _determine_indue_case_type(self, payload: dict) -> CaseType:
        """Determine case type from Indue payload."""
        screening_type = payload.get("screeningType", "")
        match_score = payload.get("matchScore", 0)

        # Handle combined alerts (FR-035)
        if screening_type == "COMBINED":
            return CaseType.SANCTIONS_PEP_COMBINED

        if screening_type == "SANCTIONS":
            # Check if this is an existing customer (FR-037)
            customer_status = payload.get("customerOnboardingStatus", "")
            if customer_status == "EXISTING":
                return CaseType.SANCTIONS_EXISTING_CUSTOMER
            return CaseType.SANCTIONS_ONBOARDING
        elif screening_type == "PEP":
            # Use PEP service for proper classification (FR-030, EC-011)
            from src.services.pep_service import PEPService
            pep_service = PEPService(self.db)
            classification = pep_service.classify_pep_match(match_score or 0)
            return classification.case_type

        return CaseType.PEP_SCREENING

    def _calculate_sla_deadline(self, case_type: CaseType) -> datetime:
        """
        Calculate SLA deadline based on case type.

        Uses business days (excludes weekends and Australian holidays).
        SLA starts at case creation (D2).
        """
        from src.services.sla_calculator import SLACalculator

        calculator = SLACalculator(self.db)
        return calculator.calculate_sla_deadline(
            case_type=case_type,
            created_at=datetime.utcnow()
        )

    def _parse_date(self, date_str: Optional[str]) -> Optional[datetime]:
        """Parse date string to date object."""
        if not date_str:
            return None
        try:
            return datetime.fromisoformat(date_str.replace("Z", "+00:00")).date()
        except (ValueError, AttributeError):
            return None
