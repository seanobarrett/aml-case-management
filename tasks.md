# Implementation Tasks: 001-aml-case-management

> AML Case Management System - Implementation Tasks with TDD Discipline
> Generated: 2026-01-18
> Phase: Tasks
> Tech Stack: Python 3.12, FastAPI, PostgreSQL 15, Celery + Redis

---

## Overview

This document defines implementation tasks organized as vertical slices with TDD discipline. Each cycle delivers observable, testable value following the test-first principle.

**Task Structure**:
- Each cycle begins with a failing test
- Implementation follows to make the test pass
- Refactoring ensures code quality
- Demo validates acceptance criteria

**Markers**:
- `[P]` - Parallel-eligible (can run concurrently after dependencies complete)
- `[US-X]` - Maps to user story X
- `[FR-XXX]` - Maps to functional requirement XXX
- `[EC-XXX]` - Handles edge case XXX
- `[EXTEND]` - Extends existing file
- `[MODIFY]` - Modifies existing code

---

## Foundation Cycles

Foundation cycles must complete sequentially before feature cycles can begin.

---

### Cycle 1: Core Infrastructure

> Stories: US-1 (partial - case creation)
> Dependencies: None
> Type: Foundation

- [x] **T1.1**: Write failing E2E test for case creation via webhook and retrieval in `tests/e2e/test_case_creation.py` [US-1, FR-001, FR-002]
- [x] **T1.2**: Create PostgreSQL schema migrations for Case, Customer, User, Assignment in `src/db/migrations/001_core_entities.py`
- [x] **T1.3**: Create Case model with reference generation (case_ref_seq) in `src/models/case.py` [FR-003, FR-004, FR-005, D9]
- [x] **T1.4**: Create Customer model in `src/models/customer.py`
- [x] **T1.5**: Create User model with RBAC roles in `src/models/user.py` [FR-063, D5]
- [x] **T1.6**: Create Assignment model in `src/models/assignment.py`
- [x] **T1.7**: Create WebhookReceipt model for duplicate detection in `src/models/webhook_receipt.py` [D3, EC-005]
- [x] **T1.8**: Implement HMAC webhook authentication in `src/middleware/webhook_auth.py` [D11]
- [x] **T1.9**: Implement OIDC authentication middleware in `src/middleware/auth.py` [D5]
- [x] **T1.10**: Implement CaseService with create and get methods in `src/services/case_service.py`
- [x] **T1.11**: Create POST /webhooks/greenid endpoint in `src/api/webhooks.py` [FR-001]
- [x] **T1.12**: Create POST /webhooks/indue endpoint in `src/api/webhooks.py` [FR-001]
- [x] **T1.13**: Create GET /cases endpoint with pagination in `src/api/cases.py` [FR-024, FR-025]
- [x] **T1.14**: Create GET /cases/{caseId} endpoint in `src/api/cases.py`
- [x] **T1.15**: Implement optimistic locking with version column in `src/models/base.py` [D8, EC-001]
- [x] **T1.16**: Refactor and verify all tests pass
- [x] **T1.17**: Demo webhook creates case; authenticated user can list and view cases

**Checkpoint**: Webhook creates a case; authenticated user can list and view cases.

---

### Cycle 2: Audit Logging Infrastructure

> Stories: FR-058, FR-059, FR-060, FR-061, Principle I
> Dependencies: C1
> Type: Foundation

- [x] **T2.1**: Write failing test for audit log immutability and case view logging in `tests/e2e/test_audit_logging.py` [FR-058, FR-059]
- [x] **T2.2**: Create AuditLog model with immutability constraints in `src/models/audit_log.py` [D1]
- [x] **T2.3**: Create TimelineEntry model in `src/models/timeline_entry.py` [Principle I]
- [x] **T2.4**: Implement PII redaction service in `src/services/pii_redaction.py` [D12]
- [x] **T2.5**: Implement AuditService with redacted payload logging in `src/services/audit_service.py` [D12]
- [x] **T2.6**: Create database triggers to prevent UPDATE/DELETE on audit tables in `src/db/migrations/002_audit_immutability.py`
- [x] **T2.7**: Implement audit middleware for all mutating endpoints in `src/middleware/audit.py`
- [x] **T2.8**: [MODIFY] Update GET /cases/{caseId} to log case views in `src/api/cases.py` [FR-059]
- [x] **T2.9**: Refactor and verify tests pass
- [x] **T2.10**: Demo all case operations create immutable audit entries; PII is redacted from payloads

**Checkpoint**: All case operations create immutable audit entries; PII is redacted from payloads.

---

### Cycle 3: Notification and Queue Infrastructure

> Stories: FR-066-069, D6, D13
> Dependencies: C1, C2
> Type: Foundation

- [x] **T3.1**: Write failing test for notification delivery and queue ordering in `tests/e2e/test_notifications.py` [FR-066, FR-024, FR-025]
- [x] **T3.2**: Create Notification model in `src/models/notification.py`
- [x] **T3.3**: Implement NotificationService in `src/services/notification_service.py` [D6]
- [x] **T3.4**: Create Celery task for email notifications in `src/tasks/notification_tasks.py` [D6]
- [x] **T3.5**: Create GET /notifications endpoint in `src/api/notifications.py` [FR-069]
- [x] **T3.6**: Create GET /notifications/count endpoint in `src/api/notifications.py`
- [x] **T3.7**: Create PATCH /notifications/{id}/read endpoint in `src/api/notifications.py`
- [x] **T3.8**: Create GET /queue/unassigned endpoint with SLA ordering in `src/api/queue.py` [D13, FR-024, FR-025]
- [x] **T3.9**: Refactor and verify tests pass
- [x] **T3.10**: Demo cases appear in unassigned queue ordered by SLA; notifications are created and can be retrieved

**Checkpoint**: Cases appear in unassigned queue; notifications are created and can be retrieved.

---

## Feature Cycles

Feature cycles can proceed after foundation cycles complete. Cycles marked [P] can run in parallel.

---

### Cycle 4: L1 Case Triage Workflow [P]

> Stories: US-1, US-13
> Dependencies: C1, C2, C3
> Type: Feature [P]

- [x] **T4.1**: Write failing E2E test for L1 case claim and closure (false positive + satisfactory explanation) in `tests/e2e/test_l1_triage.py` [US-1, US-13, FR-009, FR-011]
- [x] **T4.2**: Write failing test for customer account closure indicator in `tests/e2e/test_account_closure.py` [EC-008]
- [x] **T4.3**: Implement CaseQueueService with claim logic in `src/services/case_queue_service.py` [D13]
- [x] **T4.4**: Create POST /cases/{caseId}/claim endpoint in `src/api/cases.py`
- [x] **T4.5**: Implement case closure with mandatory documentation in `src/services/case_service.py` [FR-009, FR-011, FR-015]
- [x] **T4.6**: [EXTEND] Add l2ReviewStatus field and logic to Case model in `src/models/case.py` [FR-012]
- [x] **T4.7**: Create POST /cases/{caseId}/close endpoint in `src/api/cases.py`
- [x] **T4.8**: [EXTEND] Add accountClosed indicator to Customer model for EC-008 in `src/models/customer.py` [EC-008]
- [x] **T4.9**: Implement webhook handler for customer account closure in `src/api/webhooks.py` [EC-008]
- [x] **T4.10**: Implement prevention of auto-closure for cases with account closure indicator in `src/services/case_service.py` [EC-008]
- [x] **T4.11**: Refactor and verify tests pass
- [x] **T4.12**: Demo L1 can claim case from queue and close with documented justification; cases with closed accounts display indicator and prevent auto-closure

**Checkpoint**: L1 can claim case from queue and close with documented justification; cases with closed accounts display indicator and prevent auto-closure.

---

### Cycle 5: Customer Communication Workflow [P]

> Stories: US-2
> Dependencies: C1, C2, C3
> Type: Feature [P]

- [x] **T5.1**: Write failing E2E test for customer information request and response recording in `tests/e2e/test_customer_communication.py` [US-2, FR-053, FR-055, FR-056]
- [x] **T5.2**: Create CommunicationTemplate model in `src/models/communication_template.py` [D10]
- [x] **T5.3**: Create CustomerCommunication model in `src/models/customer_communication.py`
- [x] **T5.4**: Load communication templates from YAML files on startup in `src/services/template_service.py` [D10, FR-054]
- [x] **T5.5**: Implement CommunicationService in `src/services/communication_service.py`
- [x] **T5.6**: Create POST /cases/{caseId}/request-information endpoint in `src/api/cases.py` [FR-053]
- [x] **T5.7**: Create POST /cases/{caseId}/record-response endpoint in `src/api/cases.py` [FR-056]
- [x] **T5.8**: [MODIFY] Update case status transition to PENDING_INFORMATION in `src/services/case_service.py`
- [x] **T5.9**: Refactor and verify tests pass
- [x] **T5.10**: Demo L1 can send templated request and record customer response

**Checkpoint**: L1 can send templated request and record customer response.

---

### Cycle 6: L1 to L2 Escalation [P]

> Stories: US-3
> Dependencies: C1, C2, C3
> Type: Feature [P]

- [x] **T6.1**: Write failing E2E test for L1 to L2 escalation with documented reasoning in `tests/e2e/test_escalation.py` [US-3, FR-013]
- [x] **T6.2**: Implement escalation logic with tier change in `src/services/case_service.py` [FR-013]
- [x] **T6.3**: Create POST /cases/{caseId}/escalate endpoint in `src/api/cases.py`
- [x] **T6.4**: [MODIFY] Update case status transition to ESCALATED in `src/services/case_service.py`
- [x] **T6.5**: Create notification for L2 queue on escalation in `src/services/notification_service.py` [FR-068]
- [x] **T6.6**: Refactor and verify tests pass
- [x] **T6.7**: Demo L1 can escalate case to L2 queue with documented reasoning

**Checkpoint**: L1 can escalate case to L2 queue with documented reasoning.

---

### Cycle 7: L2 Investigation and SMR Recommendation [P]

> Stories: US-4
> Dependencies: C1, C2, C3
> Type: Feature [P]

- [x] **T7.1**: Write failing E2E test for investigation findings and SMR recommendation creation in `tests/e2e/test_l2_investigation.py` [US-4, FR-039]
- [x] **T7.2**: Create InvestigationFindings model in `src/models/investigation_findings.py`
- [x] **T7.3**: Create SMRRecommendation model in `src/models/smr_recommendation.py` [FR-039]
- [x] **T7.4**: Implement InvestigationService in `src/services/investigation_service.py`
- [x] **T7.5**: Create POST /cases/{caseId}/investigation-findings endpoint in `src/api/investigation.py`
- [x] **T7.6**: Implement SMR recommendation logic with L2 role restriction in `src/services/smr_service.py` [FR-014, BR-SMR-001]
- [x] **T7.7**: Create POST /cases/{caseId}/smr/recommend endpoint in `src/api/smr.py`
- [x] **T7.8**: [MODIFY] Update case status transition to PENDING_APPROVAL in `src/services/case_service.py`
- [x] **T7.9**: Create notification for manager on SMR submission in `src/services/notification_service.py`
- [x] **T7.10**: Refactor and verify tests pass
- [x] **T7.11**: Demo L2 can document investigation and create SMR recommendation

**Checkpoint**: L2 can document investigation findings and create SMR recommendation.

---

### Cycle 8: Manager SMR Approval and AUSTRAC Recording

> Stories: US-5, US-11
> Dependencies: C7
> Type: Feature

- [x] **T8.1**: Write failing E2E test for SMR approval, rejection, and AUSTRAC reference recording in `tests/e2e/test_smr_workflow.py` [US-5, US-11, FR-040, FR-041, FR-043]
- [x] **T8.2**: Create SMRDraft model in `src/models/smr_draft.py`
- [x] **T8.3**: Implement SMR approval with segregation of duties enforcement in `src/services/smr_service.py` [FR-020, FR-021, BR-SMR-002, BR-SMR-003]
- [x] **T8.4**: Implement SMR draft document generation in `src/services/smr_draft_service.py` [FR-040]
- [x] **T8.5**: Create POST /cases/{caseId}/smr/approve endpoint in `src/api/smr.py`
- [x] **T8.6**: Create POST /cases/{caseId}/smr/reject endpoint in `src/api/smr.py` [FR-023, EC-010]
- [x] **T8.7**: Create POST /cases/{caseId}/smr/resubmit endpoint in `src/api/smr.py`
- [x] **T8.8**: Implement AUSTRAC reference recording in `src/services/smr_service.py` [FR-041]
- [x] **T8.9**: Create POST /cases/{caseId}/smr/record-reference endpoint in `src/api/smr.py`
- [x] **T8.10**: Implement 3-day SMR filing SLA tracking in `src/services/sla_service.py` [FR-042]
- [x] **T8.11**: [MODIFY] Prevent SMR withdrawal after approval in `src/services/smr_service.py` [FR-043]
- [x] **T8.12**: Refactor and verify tests pass
- [x] **T8.13**: Demo manager can approve/reject SMR; analyst can record AUSTRAC reference

**Checkpoint**: Manager can approve/reject SMR; analyst can record AUSTRAC reference.

---

### Cycle 9: Sanctions Blocking During Onboarding [P]

> Stories: US-6, US-15
> Dependencies: C1, C2, C3
> Type: Feature [P]

- [x] **T9.1**: Write failing E2E test for sanctions block creation and clearance in `tests/e2e/test_sanctions_blocking.py` [US-6, FR-028, FR-029]
- [x] **T9.2**: Write failing test for combined sanctions/PEP handling in `tests/e2e/test_combined_alerts.py` [US-15, FR-035]
- [x] **T9.3**: Write failing test for new alert case linking in `tests/e2e/test_alert_case_linking.py` [EC-014]
- [x] **T9.4**: Create OnboardingBlock model with sync status tracking in `src/models/onboarding_block.py` [EC-009]
- [x] **T9.5**: Create CaseLink model for case relationships in `src/models/case_link.py` [FR-046]
- [x] **T9.6**: Implement OnboardingBlockService with circuit breaker for Spriggy API in `src/services/onboarding_block_service.py` [D3, FR-028]
- [x] **T9.7**: Create Celery task for Spriggy API callback with retry logic in `src/tasks/onboarding_tasks.py` [D3, EC-009]
- [x] **T9.8**: [MODIFY] Update GreenID webhook handler for sanctions case creation in `src/api/webhooks.py`
- [x] **T9.9**: Implement combined sanctions/PEP case creation logic in `src/services/case_service.py` [FR-035]
- [x] **T9.10**: Implement new alert case linking for existing open cases in `src/services/case_link_service.py` [EC-014]
- [x] **T9.11**: Implement block clearance on case closure in `src/services/onboarding_block_service.py`
- [x] **T9.12**: Create GET /cases/{caseId}/linked-cases endpoint in `src/api/cases.py` [EC-014]
- [x] **T9.13**: Refactor and verify tests pass
- [x] **T9.14**: Demo sanctions webhook blocks onboarding; analyst clearance removes block; new alerts for customers with open cases are linked

**Checkpoint**: Sanctions webhook blocks onboarding; analyst clearance removes block; new alerts for customers with open cases are linked for analyst awareness.

---

### Cycle 10: High-Confidence PEP with EDD [P]

> Stories: US-7
> Dependencies: C9
> Type: Feature [P]

- [x] **T10.1**: Write failing E2E test for high-confidence PEP blocking and EDD completion in `tests/e2e/test_pep_edd.py` [US-7, FR-030, FR-031, FR-033, FR-034]
- [x] **T10.2**: Create EDDChecklist model in `src/models/edd_checklist.py` [FR-033]
- [x] **T10.3**: Create PEPThresholdConfig model in `src/models/pep_threshold_config.py` [FR-030]
- [x] **T10.4**: Implement PEP confidence score classification in `src/services/pep_service.py` [FR-030]
- [x] **T10.5**: [MODIFY] Update webhook handler for high-confidence PEP case creation with block in `src/api/webhooks.py` [FR-031]
- [x] **T10.6**: Implement EDDService in `src/services/edd_service.py`
- [x] **T10.7**: Create GET /cases/{caseId}/edd-checklist endpoint in `src/api/edd.py`
- [x] **T10.8**: Create POST /cases/{caseId}/edd-checklist endpoint in `src/api/edd.py` [FR-034]
- [x] **T10.9**: [MODIFY] Implement block clearance after EDD completion in `src/services/onboarding_block_service.py`
- [x] **T10.10**: Refactor and verify tests pass
- [x] **T10.11**: Demo high-confidence PEP blocks onboarding; EDD completion clears block

**Checkpoint**: High-confidence PEP blocks onboarding; EDD completion clears block.

---

### Cycle 11: Low-Confidence PEP Provisional Onboarding [P]

> Stories: US-8
> Dependencies: C9
> Type: Feature [P]

- [x] **T11.1**: Write failing E2E test for low-confidence PEP case creation without blocking in `tests/e2e/test_pep_provisional.py` [US-8, FR-032, EC-011]
- [x] **T11.2**: [MODIFY] Update webhook handler for low-confidence PEP case creation (no block) in `src/api/webhooks.py` [FR-032]
- [x] **T11.3**: Implement threshold boundary logic (equal to threshold = low confidence) in `src/services/pep_service.py` [EC-011]
- [x] **T11.4**: [EXTEND] Add enhanced monitoring flag to Case model in `src/models/case.py`
- [x] **T11.5**: Implement analyst confirmation workflow in `src/services/case_service.py`
- [x] **T11.6**: Refactor and verify tests pass
- [x] **T11.7**: Demo low-confidence PEP creates case without blocking onboarding

**Checkpoint**: Low-confidence PEP creates case without blocking onboarding.

---

### Cycle 12: SLA Tracking and Breach Escalation [P]

> Stories: US-9
> Dependencies: C1, C2, C3
> Type: Feature [P]

- [x] **T12.1**: Write failing E2E test for SLA warning and breach escalation in `tests/e2e/test_sla_tracking.py` [US-9, FR-048, FR-049, FR-050, FR-051, FR-052]
- [x] **T12.2**: Create HolidayOverride model in `src/models/holiday_override.py`
- [x] **T12.3**: Implement SLACalculator with Australian business day logic in `src/services/sla_calculator.py` [D2, FR-048]
- [x] **T12.4**: Implement SLA warning notification at threshold in `src/services/sla_service.py` [FR-050]
- [x] **T12.5**: Implement automatic escalation on SLA breach in `src/services/sla_service.py` [FR-051]
- [x] **T12.6**: Create Celery periodic task for SLA monitoring in `src/tasks/sla_tasks.py`
- [x] **T12.7**: Implement manager notification for breaches in `src/services/notification_service.py` [FR-052]
- [x] **T12.8**: Create GET /config/holidays endpoint in `src/api/holidays.py`
- [x] **T12.9**: Create POST /config/holidays endpoint in `src/api/holidays.py`
- [x] **T12.10**: Refactor and verify tests pass
- [x] **T12.11**: Demo SLA warnings sent; breached cases auto-escalate with manager notification

**Checkpoint**: SLA warnings sent; breached cases auto-escalate with manager notification.

---

### Cycle 13: Dashboard with Prioritization [P]

> Stories: US-12
> Dependencies: C1, C2, C3
> Type: Feature [P]

- [x] **T13.1**: Write failing E2E test for dashboard case ordering and SLA indicators in `tests/e2e/test_dashboard.py` [US-12, FR-024, FR-025]
- [x] **T13.2**: Implement DashboardService with case prioritization in `src/services/dashboard_service.py`
- [x] **T13.3**: Create GET /dashboard/my-cases endpoint in `src/api/dashboard.py`
- [x] **T13.4**: Create GET /dashboard/queue-metrics endpoint in `src/api/dashboard.py`
- [x] **T13.5**: Implement SLA visual indicator calculation in `src/services/dashboard_service.py`
- [x] **T13.6**: Implement 30-second polling support in dashboard endpoints in `src/api/dashboard.py` [D6]
- [x] **T13.7**: Refactor and verify tests pass
- [x] **T13.8**: Demo analyst sees prioritized case list with SLA indicators

**Checkpoint**: Analyst sees prioritized case list with SLA indicators.

---

### Cycle 14: L2 Quality Review and Case Reopen

> Stories: US-16
> Dependencies: C4
> Type: Feature

- [x] **T14.1**: Write failing E2E test for L2 quality review queue and case reopen in `tests/e2e/test_l2_quality_review.py` [US-16, FR-018, FR-019]
- [x] **T14.2**: Implement L2 review queue filtering in `src/services/case_queue_service.py` [FR-018]
- [x] **T14.3**: Create GET /queue/l2-review endpoint in `src/api/queue.py`
- [x] **T14.4**: Create POST /queue/l2-review/{caseId}/accept endpoint in `src/api/queue.py`
- [x] **T14.5**: Implement case reopen logic with assignment to L2 in `src/services/case_service.py` [FR-019]
- [x] **T14.6**: Create POST /cases/{caseId}/reopen endpoint in `src/api/cases.py`
- [x] **T14.7**: [MODIFY] Update l2ReviewStatus transitions in `src/services/case_service.py`
- [x] **T14.8**: Refactor and verify tests pass
- [x] **T14.9**: Demo L2 can review L1 closures and reopen cases to their queue

**Checkpoint**: L2 can review L1 closures and reopen cases to their queue.

---

### Cycle 15: Existing Customer Sanctions [P]

> Stories: US-17
> Dependencies: C9
> Type: Feature [P]

- [x] **T15.1**: Write failing E2E test for existing customer sanctions case without auto-block in `tests/e2e/test_existing_customer_sanctions.py` [US-17, FR-036, FR-037, FR-038]
- [x] **T15.2**: Implement existing customer detection in webhook processing in `src/services/case_service.py` [FR-037]
- [x] **T15.3**: [MODIFY] Update case creation for SANCTIONS_EXISTING_CUSTOMER subtype in `src/api/webhooks.py` [FR-036]
- [x] **T15.4**: Implement account restriction recommendation capability in `src/api/cases.py` [FR-038]
- [x] **T15.5**: Refactor and verify tests pass
- [x] **T15.6**: Demo existing customer sanctions creates case without blocking account

**Checkpoint**: Existing customer sanctions creates case without blocking account.

---

### Cycle 16: Read-Only Reports and Export [P]

> Stories: US-10
> Dependencies: C1, C2, C3
> Type: Feature [P]

- [x] **T16.1**: Write failing E2E test for report viewing and export in `tests/e2e/test_reports.py` [US-10, FR-064, FR-070, FR-071, FR-072]
- [x] **T16.2**: Create materialized views for report data in `src/db/migrations/010_report_views.py` [D7]
- [x] **T16.3**: Implement ReportService in `src/services/report_service.py`
- [x] **T16.4**: Create GET /reports/volumes endpoint in `src/api/reports.py` [FR-070]
- [x] **T16.5**: Create GET /reports/sla-compliance endpoint in `src/api/reports.py` [FR-070]
- [x] **T16.6**: Create GET /reports/smr-metrics endpoint in `src/api/reports.py` [FR-071]
- [x] **T16.7**: Create GET /reports/aged-cases endpoint in `src/api/reports.py` [FR-073]
- [x] **T16.8**: Implement export service with CSV/Excel generation in `src/services/export_service.py`
- [x] **T16.9**: Create GET /reports/export endpoint in `src/api/reports.py` [FR-072]
- [x] **T16.10**: Implement read-only role enforcement on report endpoints in `src/api/reports.py` [FR-064]
- [x] **T16.11**: Refactor and verify tests pass
- [x] **T16.12**: Demo read-only user can view reports and export case data

**Checkpoint**: Read-only user can view reports and export case data.

---

### Cycle 17: Role Change Case Reassignment [P]

> Stories: US-14
> Dependencies: C1, C2, C3
> Type: Feature [P]

- [x] **T17.1**: Write failing E2E test for role change triggering case unassignment in `tests/e2e/test_role_change.py` [US-14, FR-026, FR-027]
- [x] **T17.2**: Implement role change detection and case reassignment in `src/services/user_service.py` [FR-026]
- [x] **T17.3**: Implement audit entry creation for each affected case in `src/services/audit_service.py` [FR-027]
- [x] **T17.4**: [MODIFY] Update user role update endpoint to trigger reassignment in `src/api/users.py`
- [x] **T17.5**: [EXTEND] Add ROLE_CHANGE to AssignmentReason enum in `src/models/assignment.py`
- [x] **T17.6**: Refactor and verify tests pass
- [x] **T17.7**: Demo role change unassigns all analyst cases with audit trail

**Checkpoint**: Role change unassigns all analyst cases with audit trail.

---

### Cycle 18: Supplementary SMR Filing

> Stories: US-18
> Dependencies: C8, C9
> Type: Feature

- [x] **T18.1**: Write failing E2E test for supplementary SMR creation and workflow in `tests/e2e/test_supplementary_smr.py` [US-18, FR-044, FR-045, FR-046, FR-047]
- [x] **T18.2**: Implement supplementary case creation logic in `src/services/case_service.py` [FR-044]
- [x] **T18.3**: Create POST /cases/{caseId}/create-supplementary endpoint in `src/api/cases.py`
- [x] **T18.4**: [EXTEND] Add SUPPLEMENTARY_TO_ORIGINAL link type to CaseLink in `src/models/case_link.py` [FR-046]
- [x] **T18.5**: Implement bidirectional navigation between linked cases in `src/services/case_link_service.py` [FR-046]
- [x] **T18.6**: [MODIFY] Support multiple supplementary filings per original in `src/services/case_service.py` [FR-047]
- [x] **T18.7**: Verify supplementary case follows full SMR workflow in `tests/e2e/test_supplementary_smr.py` [FR-045]
- [x] **T18.8**: Refactor and verify tests pass
- [x] **T18.9**: Demo can create supplementary SMR linked to original filed case

**Checkpoint**: Can create supplementary SMR linked to original filed case.

---

## Dependency Graph

```
Foundation (Sequential):
C1 (Core Infrastructure)
 └── C2 (Audit Logging)
      └── C3 (Notifications/Queue)

Feature Cycles (After Foundation):

                     ┌─────────────────────────────────────────────────────────────────┐
                     │                    PARALLEL GROUP A                              │
                     │  C4 [P] (L1 Triage + EC-008) ────────> C14 (L2 Review Queue)    │
                     │  C5 [P] (Communication)                                          │
                     │  C6 [P] (Escalation)                                             │
                     │  C7 [P] (Investigation) ────────> C8 (Approval) ─┬─> C18 (Supp) │
                     └─────────────────────────────────────────────────────────────────┘

                     ┌─────────────────────────────────────────────────────────────────┐
                     │                    PARALLEL GROUP B                              │
                     │  C9 [P] (Sanctions + EC-014) ──┬─> C10 [P] (PEP EDD)            │
                     │                                ├─> C11 [P] (Low-Conf PEP)       │
                     │                                └─> C15 [P] (Existing Cust)      │
                     └─────────────────────────────────────────────────────────────────┘

                     ┌─────────────────────────────────────────────────────────────────┐
                     │                    PARALLEL GROUP C                              │
                     │  C12 [P] (SLA Tracking)                                          │
                     │  C13 [P] (Dashboard)                                             │
                     │  C16 [P] (Reports + Export)                                      │
                     │  C17 [P] (Role Change)                                           │
                     └─────────────────────────────────────────────────────────────────┘

Note: C18 depends on both C8 (SMR workflow) and C9 (CaseLink entity)
```

---

## Traceability Summary

### P1 User Story Coverage

| Story | Cycle | Tasks |
|-------|-------|-------|
| US-1 | C1, C4 | T1.1-T1.17, T4.1-T4.12 |
| US-2 | C5 | T5.1-T5.10 |
| US-3 | C6 | T6.1-T6.7 |
| US-4 | C7 | T7.1-T7.11 |
| US-5 | C8 | T8.1-T8.13 |
| US-6 | C9 | T9.1-T9.14 |
| US-7 | C10 | T10.1-T10.11 |
| US-9 | C12 | T12.1-T12.11 |
| US-11 | C8 | T8.1-T8.13 |
| US-12 | C13 | T13.1-T13.8 |
| US-13 | C4 | T4.1-T4.12 |
| US-16 | C14 | T14.1-T14.9 |
| US-17 | C15 | T15.1-T15.6 |
| US-18 | C18 | T18.1-T18.9 |

### P2 User Story Coverage

| Story | Cycle | Tasks |
|-------|-------|-------|
| US-8 | C11 | T11.1-T11.7 |
| US-10 | C16 | T16.1-T16.12 |
| US-14 | C17 | T17.1-T17.7 |
| US-15 | C9 | T9.1-T9.14 |

### Edge Case Coverage

| Edge Case | Cycle | Tasks |
|-----------|-------|-------|
| EC-001 | C1 | T1.15 |
| EC-005 | C1 | T1.7 |
| EC-008 | C4 | T4.2, T4.8-T4.10 |
| EC-009 | C9 | T9.4, T9.7 |
| EC-010 | C8 | T8.6 |
| EC-011 | C11 | T11.1, T11.3 |
| EC-014 | C9 | T9.3, T9.10, T9.12 |

### Constitution Alignment

| Principle | Primary Cycles | Key Tasks |
|-----------|---------------|-----------|
| I. Immutable Audit Trail | C2 | T2.1-T2.10 |
| II. RBAC with Segregation | C1, C8 | T1.5, T1.9, T8.3 |
| III. Test-First Development | All | Every T*.1 task |
| IV. Explicit Error Handling | C9 | T9.6, T9.7 |
| V. SLA Tracking | C12 | T12.1-T12.11 |
| VI. Sensitive Data Protection | C2 | T2.4, T2.5 |
| VII. External Integration Resilience | C9 | T9.6, T9.7 |

---

## Task Statistics

| Metric | Value |
|--------|-------|
| Total Cycles | 18 |
| Foundation Cycles | 3 |
| Feature Cycles | 15 |
| Parallel-Eligible Cycles | 12 |
| Total Tasks | 171 |
| Average Tasks per Cycle | 9.5 |
