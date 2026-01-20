"""
Seed script to populate the database with test data.

Run inside the container:
    docker compose exec api python scripts/seed_data.py
"""

import sys
sys.path.insert(0, '/app')

from datetime import datetime, timedelta, date
from uuid import uuid4

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Import all models to ensure they're registered with SQLAlchemy
from src.models.base import Base
from src.models.user import User, UserRole
from src.models.customer import Customer
from src.models.case import Case, CaseStatus, CaseType, CaseTier
from src.models.assignment import Assignment, AssignmentReason
from src.models.notification import Notification, NotificationType
from src.models.smr_recommendation import SMRRecommendation, SMRStatus
from src.models.timeline_entry import TimelineEntry, TimelineEntryType
from src.models.holiday_override import HolidayOverride, HolidayScope
from src.models.communication_template import CommunicationTemplate, TemplateCategory
from src.models.onboarding_block import OnboardingBlock
from src.models.case_link import CaseLink
from src.models.audit_log import AuditLog
from src.models.investigation_findings import InvestigationFindings
from src.models.customer_communication import CustomerCommunication
from src.models.edd_checklist import EDDChecklist
from src.models.account_restriction import AccountRestriction
from src.models.pep_threshold_config import PEPThresholdConfig
from src.models.webhook_receipt import WebhookReceipt


DATABASE_URL = "postgresql://aml_user:aml_password@db:5432/aml_case_management"

engine = create_engine(DATABASE_URL)
Session = sessionmaker(bind=engine)


def create_case_reference(session, counter: int) -> str:
    """Generate a case reference."""
    return f"AML-{2024000 + counter:07d}"


def seed_users(session) -> dict:
    """Create test users with different roles."""
    print("Creating users...")

    users = {
        "manager": User(
            id=uuid4(),
            email="manager@spriggy.com.au",
            role=UserRole.AML_MANAGER,
            is_active=True
        ),
        "l2_analyst1": User(
            id=uuid4(),
            email="sarah.chen@spriggy.com.au",
            role=UserRole.L2_ANALYST,
            is_active=True
        ),
        "l2_analyst2": User(
            id=uuid4(),
            email="james.wilson@spriggy.com.au",
            role=UserRole.L2_ANALYST,
            is_active=True
        ),
        "l1_analyst1": User(
            id=uuid4(),
            email="emma.taylor@spriggy.com.au",
            role=UserRole.L1_ANALYST,
            is_active=True
        ),
        "l1_analyst2": User(
            id=uuid4(),
            email="michael.brown@spriggy.com.au",
            role=UserRole.L1_ANALYST,
            is_active=True
        ),
        "l1_analyst3": User(
            id=uuid4(),
            email="lisa.johnson@spriggy.com.au",
            role=UserRole.L1_ANALYST,
            is_active=True
        ),
        "readonly": User(
            id=uuid4(),
            email="auditor@spriggy.com.au",
            role=UserRole.READ_ONLY,
            is_active=True
        ),
    }

    for user in users.values():
        session.add(user)

    session.commit()
    print(f"  Created {len(users)} users")
    return users


def seed_customers(session) -> list:
    """Create test customers."""
    print("Creating customers...")

    customers_data = [
        {"external_id": "CUS-001", "first": "John", "last": "Smith", "email": "john.smith@example.com", "dob": date(1985, 3, 15)},
        {"external_id": "CUS-002", "first": "Jane", "last": "Doe", "email": "jane.doe@example.com", "dob": date(1990, 7, 22)},
        {"external_id": "CUS-003", "first": "Robert", "last": "Johnson", "email": "r.johnson@example.com", "dob": date(1978, 11, 8)},
        {"external_id": "CUS-004", "first": "Maria", "last": "Garcia", "email": "maria.g@example.com", "dob": date(1995, 2, 28)},
        {"external_id": "CUS-005", "first": "David", "last": "Williams", "email": "d.williams@example.com", "dob": date(1982, 9, 10)},
        {"external_id": "CUS-006", "first": "Emily", "last": "Brown", "email": "emily.b@example.com", "dob": date(1988, 5, 3)},
        {"external_id": "CUS-007", "first": "Ahmed", "last": "Hassan", "email": "a.hassan@example.com", "dob": date(1975, 12, 20)},
        {"external_id": "CUS-008", "first": "Sophie", "last": "Martin", "email": "sophie.m@example.com", "dob": date(1992, 4, 17)},
        {"external_id": "CUS-009", "first": "Chen", "last": "Wei", "email": "chen.wei@example.com", "dob": date(1980, 8, 5)},
        {"external_id": "CUS-010", "first": "Sarah", "last": "O'Connor", "email": "s.oconnor@example.com", "dob": date(1993, 1, 30)},
        {"external_id": "CUS-011", "first": "Vladimir", "last": "Petrov", "email": "v.petrov@example.com", "dob": date(1970, 6, 12)},
        {"external_id": "CUS-012", "first": "Yuki", "last": "Tanaka", "email": "y.tanaka@example.com", "dob": date(1998, 10, 25)},
    ]

    customers = []
    for data in customers_data:
        customer = Customer(
            id=uuid4(),
            external_customer_id=data["external_id"],
            first_name=data["first"],
            last_name=data["last"],
            email=data["email"],
            date_of_birth=data["dob"],
            account_status="ACTIVE",
            onboarding_status="COMPLETED",
            snapshot_at=datetime.utcnow()
        )
        session.add(customer)
        customers.append(customer)

    session.commit()
    print(f"  Created {len(customers)} customers")
    return customers


def seed_cases(session, users: dict, customers: list) -> list:
    """Create test cases in various states."""
    print("Creating cases...")

    cases = []
    counter = 1
    now = datetime.utcnow()

    # Case 1: New KYC case, unassigned
    case1 = Case(
        id=uuid4(),
        case_reference=create_case_reference(session, counter),
        case_type=CaseType.KYC_REMEDIATION,
        status=CaseStatus.OPEN,
        tier=CaseTier.L1,
        customer_id=customers[0].id,
        sla_deadline=now + timedelta(days=3)
    )
    session.add(case1)
    cases.append(case1)
    counter += 1

    # Case 2: KYC case assigned to L1 analyst
    case2 = Case(
        id=uuid4(),
        case_reference=create_case_reference(session, counter),
        case_type=CaseType.KYC_REMEDIATION,
        status=CaseStatus.ASSIGNED,
        tier=CaseTier.L1,
        customer_id=customers[1].id,
        assigned_to_id=users["l1_analyst1"].id,
        sla_deadline=now + timedelta(days=2)
    )
    session.add(case2)
    cases.append(case2)
    counter += 1

    # Case 3: PEP case pending information
    case3 = Case(
        id=uuid4(),
        case_reference=create_case_reference(session, counter),
        case_type=CaseType.PEP_HIGH_CONFIDENCE,
        status=CaseStatus.PENDING_INFORMATION,
        tier=CaseTier.L1,
        customer_id=customers[2].id,
        assigned_to_id=users["l1_analyst2"].id,
        sla_deadline=now + timedelta(days=4),
        sla_paused=True,
        sla_pause_start=now - timedelta(hours=6),
        pep_match_score=85
    )
    session.add(case3)
    cases.append(case3)
    counter += 1

    # Case 4: Escalated to L2
    case4 = Case(
        id=uuid4(),
        case_reference=create_case_reference(session, counter),
        case_type=CaseType.SANCTIONS_ONBOARDING,
        status=CaseStatus.ESCALATED,
        tier=CaseTier.L2,
        customer_id=customers[3].id,
        escalation_reason="Potential sanctions match requires L2 review",
        escalation_findings="Customer name matches OFAC SDN list entry",
        escalated_by_id=users["l1_analyst1"].id,
        escalated_at=now - timedelta(hours=2),
        sla_deadline=now + timedelta(days=1)
    )
    session.add(case4)
    cases.append(case4)
    counter += 1

    # Case 5: L2 case assigned and under investigation
    case5 = Case(
        id=uuid4(),
        case_reference=create_case_reference(session, counter),
        case_type=CaseType.SANCTIONS_EXISTING_CUSTOMER,
        status=CaseStatus.ASSIGNED,
        tier=CaseTier.L2,
        customer_id=customers[4].id,
        assigned_to_id=users["l2_analyst1"].id,
        sla_deadline=now + timedelta(days=2),
        enhanced_monitoring=True
    )
    session.add(case5)
    cases.append(case5)
    counter += 1

    # Case 6: Pending SMR approval
    case6 = Case(
        id=uuid4(),
        case_reference=create_case_reference(session, counter),
        case_type=CaseType.SUSPICIOUS_ACTIVITY,
        status=CaseStatus.PENDING_APPROVAL,
        tier=CaseTier.L2,
        customer_id=customers[5].id,
        assigned_to_id=users["l2_analyst1"].id,
        sla_deadline=now + timedelta(hours=12)
    )
    session.add(case6)
    cases.append(case6)
    counter += 1

    # Case 7: SLA warning - approaching deadline
    case7 = Case(
        id=uuid4(),
        case_reference=create_case_reference(session, counter),
        case_type=CaseType.PEP_LOW_CONFIDENCE,
        status=CaseStatus.ASSIGNED,
        tier=CaseTier.L1,
        customer_id=customers[6].id,
        assigned_to_id=users["l1_analyst3"].id,
        sla_deadline=now + timedelta(hours=8),
        sla_warning_sent=True,
        sla_warning_sent_at=now - timedelta(hours=2),
        pep_match_score=45
    )
    session.add(case7)
    cases.append(case7)
    counter += 1

    # Case 8: SLA breached
    case8 = Case(
        id=uuid4(),
        case_reference=create_case_reference(session, counter),
        case_type=CaseType.KYC_REMEDIATION,
        status=CaseStatus.ASSIGNED,
        tier=CaseTier.L2,
        customer_id=customers[7].id,
        assigned_to_id=users["l2_analyst2"].id,
        sla_deadline=now - timedelta(hours=4),
        sla_breach=True,
        sla_breach_at=now - timedelta(hours=4),
        sla_warning_sent=True
    )
    session.add(case8)
    cases.append(case8)
    counter += 1

    # Case 9: Closed case with filed SMR
    case9 = Case(
        id=uuid4(),
        case_reference=create_case_reference(session, counter),
        case_type=CaseType.SUSPICIOUS_ACTIVITY,
        status=CaseStatus.CLOSED,
        tier=CaseTier.L2,
        customer_id=customers[8].id,
        assigned_to_id=users["l2_analyst1"].id,
        closure_reason="SMR filed with AUSTRAC",
        closure_documentation="Suspicious transaction pattern identified and reported",
        closed_at=now - timedelta(days=3)
    )
    session.add(case9)
    cases.append(case9)
    counter += 1

    # Case 10: Closed - no action required
    case10 = Case(
        id=uuid4(),
        case_reference=create_case_reference(session, counter),
        case_type=CaseType.PEP_LOW_CONFIDENCE,
        status=CaseStatus.CLOSED,
        tier=CaseTier.L1,
        customer_id=customers[9].id,
        assigned_to_id=users["l1_analyst1"].id,
        closure_reason="False positive - name similarity only",
        closure_documentation="Verified customer identity does not match PEP",
        closed_at=now - timedelta(days=5)
    )
    session.add(case10)
    cases.append(case10)
    counter += 1

    # Case 11: Combined sanctions + PEP
    case11 = Case(
        id=uuid4(),
        case_reference=create_case_reference(session, counter),
        case_type=CaseType.SANCTIONS_PEP_COMBINED,
        status=CaseStatus.ASSIGNED,
        tier=CaseTier.L2,
        customer_id=customers[10].id,
        assigned_to_id=users["l2_analyst2"].id,
        sla_deadline=now + timedelta(days=1),
        alert_types=["SANCTIONS", "PEP"],
        pep_match_score=72
    )
    session.add(case11)
    cases.append(case11)
    counter += 1

    # Case 12: New unassigned in queue
    case12 = Case(
        id=uuid4(),
        case_reference=create_case_reference(session, counter),
        case_type=CaseType.KYC_REMEDIATION,
        status=CaseStatus.OPEN,
        tier=CaseTier.L1,
        customer_id=customers[11].id,
        sla_deadline=now + timedelta(days=5)
    )
    session.add(case12)
    cases.append(case12)
    counter += 1

    session.commit()
    print(f"  Created {len(cases)} cases")
    return cases


def seed_smr_recommendations(session, users: dict, cases: list) -> list:
    """Create SMR recommendations."""
    print("Creating SMR recommendations...")

    from src.models.smr_recommendation import SMRRecommendationType

    smrs = []
    now = datetime.utcnow()

    # SMR for case 6 (pending approval)
    smr1 = SMRRecommendation(
        id=uuid4(),
        case_id=cases[5].id,  # case6
        recommended_by_id=users["l2_analyst1"].id,
        recommendation_type=SMRRecommendationType.SUBMIT,
        justification="Multiple structured deposits below reporting threshold. Pattern consistent with structuring to avoid CTR reporting requirements. Customer has no legitimate explanation for the transaction pattern.",
        suspicious_activity="12 deposits of $9,900 each over 2 week period. All deposits made in cash at different branches.",
        supporting_documents=["Transaction history", "Branch deposit records", "Customer correspondence"],
        status=SMRStatus.PENDING_APPROVAL,
        recommended_at=now - timedelta(hours=4)
    )
    session.add(smr1)
    smrs.append(smr1)

    # SMR for case 9 (closed - filed)
    smr2 = SMRRecommendation(
        id=uuid4(),
        case_id=cases[8].id,  # case9
        recommended_by_id=users["l2_analyst1"].id,
        approved_by_id=users["manager"].id,
        recommendation_type=SMRRecommendationType.SUBMIT,
        justification="Unusual international transfers to high-risk jurisdiction inconsistent with customer profile. Customer explanation for transfers does not align with transaction history.",
        suspicious_activity="$50,000 transferred to high-risk jurisdiction in multiple transactions over 5 days. Rapid movement of funds with no clear business purpose.",
        supporting_documents=["Wire transfer records", "Customer interview notes", "Risk assessment"],
        status=SMRStatus.FILED,
        recommended_at=now - timedelta(days=5),
        approved_at=now - timedelta(days=4),
        filed_at=now - timedelta(days=3),
        austrac_reference="SMR-2024-001234"
    )
    session.add(smr2)
    smrs.append(smr2)

    session.commit()
    print(f"  Created {len(smrs)} SMR recommendations")
    return smrs


def seed_notifications(session, users: dict, cases: list) -> list:
    """Create notifications for users."""
    print("Creating notifications...")

    notifications = []
    now = datetime.utcnow()

    # SLA warning notification
    notif1 = Notification(
        id=uuid4(),
        user_id=users["l1_analyst3"].id,
        notification_type=NotificationType.SLA_WARNING.value,
        title="SLA Warning",
        message=f"Case {cases[6].case_reference} is approaching SLA deadline",
        case_id=cases[6].id,
        is_read=False,
        created_at=now - timedelta(hours=2)
    )
    session.add(notif1)
    notifications.append(notif1)

    # SLA breach notification to manager
    notif2 = Notification(
        id=uuid4(),
        user_id=users["manager"].id,
        notification_type=NotificationType.SLA_BREACH.value,
        title="SLA Breach",
        message=f"Case {cases[7].case_reference} has breached SLA",
        case_id=cases[7].id,
        is_read=False,
        created_at=now - timedelta(hours=4)
    )
    session.add(notif2)
    notifications.append(notif2)

    # Assignment notification
    notif3 = Notification(
        id=uuid4(),
        user_id=users["l1_analyst1"].id,
        notification_type=NotificationType.CASE_ASSIGNED.value,
        title="Case Assigned",
        message=f"Case {cases[1].case_reference} has been assigned to you",
        case_id=cases[1].id,
        is_read=True,
        read_at=now - timedelta(hours=1),
        created_at=now - timedelta(hours=3)
    )
    session.add(notif3)
    notifications.append(notif3)

    # SMR approval pending notification
    notif4 = Notification(
        id=uuid4(),
        user_id=users["manager"].id,
        notification_type=NotificationType.SMR_SUBMITTED.value,
        title="SMR Pending Approval",
        message=f"SMR recommendation for case {cases[5].case_reference} requires your approval",
        case_id=cases[5].id,
        is_read=False,
        created_at=now - timedelta(hours=4)
    )
    session.add(notif4)
    notifications.append(notif4)

    # Escalation notification
    notif5 = Notification(
        id=uuid4(),
        user_id=users["l2_analyst1"].id,
        notification_type=NotificationType.CASE_ESCALATED.value,
        title="Case Escalated",
        message=f"Case {cases[3].case_reference} has been escalated to L2",
        case_id=cases[3].id,
        is_read=False,
        created_at=now - timedelta(hours=2)
    )
    session.add(notif5)
    notifications.append(notif5)

    session.commit()
    print(f"  Created {len(notifications)} notifications")
    return notifications


def seed_holidays(session, users: dict) -> list:
    """Create 2026 Australian public holidays."""
    print("Creating holidays...")

    holidays_data = [
        {"date": date(2026, 1, 1), "name": "New Year's Day", "scope": HolidayScope.ALL},
        {"date": date(2026, 1, 26), "name": "Australia Day", "scope": HolidayScope.ALL},
        {"date": date(2026, 4, 3), "name": "Good Friday", "scope": HolidayScope.ALL},
        {"date": date(2026, 4, 4), "name": "Easter Saturday", "scope": HolidayScope.ALL},
        {"date": date(2026, 4, 6), "name": "Easter Monday", "scope": HolidayScope.ALL},
        {"date": date(2026, 4, 25), "name": "Anzac Day", "scope": HolidayScope.ALL},
        {"date": date(2026, 6, 8), "name": "Queen's Birthday", "scope": HolidayScope.ALL},
        {"date": date(2026, 12, 25), "name": "Christmas Day", "scope": HolidayScope.ALL},
        {"date": date(2026, 12, 26), "name": "Boxing Day", "scope": HolidayScope.ALL},
    ]

    holidays = []
    for data in holidays_data:
        holiday = HolidayOverride(
            id=uuid4(),
            holiday_date=data["date"],
            name=data["name"],
            scope=data["scope"],
            created_by=users["manager"].id
        )
        session.add(holiday)
        holidays.append(holiday)

    session.commit()
    print(f"  Created {len(holidays)} holidays")
    return holidays


def seed_templates(session) -> list:
    """Create communication templates."""
    print("Creating communication templates...")

    templates_data = [
        {
            "template_id": "kyc_document_request",
            "name": "KYC Document Request",
            "description": "Request additional identity documents from customer",
            "subject": "Action Required: Additional Documentation Needed",
            "body": """Dear {{customer_name}},

We are writing regarding your account verification. To complete this process, we require the following documentation:

{{document_list}}

Please upload these documents through your account portal within 7 business days.

If you have any questions, please contact our support team.

Best regards,
Spriggy Compliance Team""",
            "category": TemplateCategory.DOCUMENT_REQUEST
        },
        {
            "template_id": "identity_verification_reminder",
            "name": "Identity Verification Reminder",
            "description": "Reminder for pending identity verification",
            "subject": "Reminder: Complete Your Identity Verification",
            "body": """Dear {{customer_name}},

This is a reminder that your identity verification is still pending.

To continue using your account, please complete the verification process at your earliest convenience.

Case Reference: {{case_reference}}

Best regards,
Spriggy Compliance Team""",
            "category": TemplateCategory.IDENTITY_VERIFICATION
        },
        {
            "template_id": "general_followup",
            "name": "General Follow-up",
            "description": "General follow-up communication",
            "subject": "Follow-up: {{subject}}",
            "body": """Dear {{customer_name}},

{{message_body}}

If you have any questions, please don't hesitate to contact us.

Best regards,
Spriggy Compliance Team""",
            "category": TemplateCategory.FOLLOW_UP
        },
    ]

    templates = []
    for data in templates_data:
        template = CommunicationTemplate(
            id=uuid4(),
            template_id=data["template_id"],
            name=data["name"],
            description=data["description"],
            subject=data["subject"],
            body=data["body"],
            category=data["category"],
            is_active=True,
            version=1
        )
        session.add(template)
        templates.append(template)

    session.commit()
    print(f"  Created {len(templates)} templates")
    return templates


def seed_timeline_entries(session, users: dict, cases: list) -> list:
    """Create timeline entries for cases."""
    print("Creating timeline entries...")

    entries = []
    now = datetime.utcnow()

    # Timeline for case 2 (assigned)
    entry1 = TimelineEntry(
        id=uuid4(),
        case_id=cases[1].id,
        entry_type=TimelineEntryType.CASE_CREATED.value,
        content="Case created from GreenID webhook",
        created_at=now - timedelta(hours=5)
    )
    session.add(entry1)
    entries.append(entry1)

    entry2 = TimelineEntry(
        id=uuid4(),
        case_id=cases[1].id,
        entry_type=TimelineEntryType.CASE_CLAIMED.value,
        content="Case assigned to Emma Taylor",
        acting_user_id=users["l1_analyst1"].id,
        created_at=now - timedelta(hours=3)
    )
    session.add(entry2)
    entries.append(entry2)

    # Timeline for case 4 (escalated)
    entry3 = TimelineEntry(
        id=uuid4(),
        case_id=cases[3].id,
        entry_type=TimelineEntryType.CASE_CREATED.value,
        content="Case created from sanctions screening",
        created_at=now - timedelta(hours=8)
    )
    session.add(entry3)
    entries.append(entry3)

    entry4 = TimelineEntry(
        id=uuid4(),
        case_id=cases[3].id,
        entry_type=TimelineEntryType.CASE_ESCALATED.value,
        content="Case escalated to L2: Potential sanctions match requires review",
        acting_user_id=users["l1_analyst1"].id,
        created_at=now - timedelta(hours=2)
    )
    session.add(entry4)
    entries.append(entry4)

    # Timeline for case 6 (pending approval)
    entry5 = TimelineEntry(
        id=uuid4(),
        case_id=cases[5].id,
        entry_type=TimelineEntryType.CASE_CREATED.value,
        content="Case created from suspicious activity alert",
        created_at=now - timedelta(days=2)
    )
    session.add(entry5)
    entries.append(entry5)

    entry6 = TimelineEntry(
        id=uuid4(),
        case_id=cases[5].id,
        entry_type=TimelineEntryType.SMR_RECOMMENDED.value,
        content="SMR recommendation submitted for approval",
        acting_user_id=users["l2_analyst1"].id,
        created_at=now - timedelta(hours=4)
    )
    session.add(entry6)
    entries.append(entry6)

    session.commit()
    print(f"  Created {len(entries)} timeline entries")
    return entries


def main():
    """Main seed function."""
    print("\n" + "="*50)
    print("AML Case Management - Database Seeding")
    print("="*50 + "\n")

    session = Session()

    try:
        # Check if data already exists
        existing_users = session.query(User).count()
        if existing_users > 0:
            print(f"Database already has {existing_users} users. Skipping seed.")
            print("To re-seed, drop and recreate the database.")
            return

        # Seed in order of dependencies
        users = seed_users(session)
        customers = seed_customers(session)
        cases = seed_cases(session, users, customers)
        seed_smr_recommendations(session, users, cases)
        seed_notifications(session, users, cases)
        seed_holidays(session, users)
        seed_templates(session)
        seed_timeline_entries(session, users, cases)

        print("\n" + "="*50)
        print("Seeding complete!")
        print("="*50)
        print("\nTest Accounts:")
        print("-" * 40)
        print("Manager:     manager@spriggy.com.au")
        print("L2 Analysts: sarah.chen@spriggy.com.au")
        print("             james.wilson@spriggy.com.au")
        print("L1 Analysts: emma.taylor@spriggy.com.au")
        print("             michael.brown@spriggy.com.au")
        print("             lisa.johnson@spriggy.com.au")
        print("Read-only:   auditor@spriggy.com.au")
        print("-" * 40)
        print(f"\nCases created: 12")
        print("  - 2 open (unassigned)")
        print("  - 4 assigned (various tiers)")
        print("  - 1 pending information")
        print("  - 1 escalated")
        print("  - 1 pending approval")
        print("  - 1 SLA warning")
        print("  - 1 SLA breached")
        print("  - 2 closed")
        print("\n")

    except Exception as e:
        session.rollback()
        print(f"\nError during seeding: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    main()
