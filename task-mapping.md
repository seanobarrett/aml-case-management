# Task Mapping: 001-aml-case-management

> AML Case Management System - User Story to Implementation Cycle Mapping
> Generated: 2026-01-18
> Revised: 2026-01-18 (Iteration 2)
> Phase: Mapping

---

## Overview

This document maps user stories from the specification to implementation cycles. Each cycle represents a vertical slice that delivers observable, testable value following TDD discipline.

**Tech Stack**: Python 3.12, FastAPI, PostgreSQL 15, Celery + Redis

---

## Story to Cycle Mapping

| Story | Priority | Cycle(s) | Description |
|-------|----------|----------|-------------|
| US-1 | P1 | C1, C4 | L1 triages screening alert (false positive closure) |
| US-2 | P1 | C5 | L1 requests customer information |
| US-3 | P1 | C6 | L1 escalates suspicious case to L2 |
| US-4 | P1 | C7 | L2 completes investigation and recommends SMR |
| US-5 | P1 | C8 | AML Manager approves SMR |
| US-6 | P1 | C9 | Sanctions blocks onboarding |
| US-7 | P1 | C10 | High-confidence PEP triggers EDD |
| US-8 | P2 | C11 | Low-confidence PEP allows provisional onboarding |
| US-9 | P1 | C12 | SLA breach triggers escalation |
| US-10 | P2 | C16 | Read-only user exports cases |
| US-11 | P1 | C8 | Analyst records AUSTRAC reference |
| US-12 | P1 | C13 | Dashboard shows workload and priorities |
| US-13 | P1 | C4 | L1 closes with satisfactory explanation |
| US-14 | P2 | C17 | Cases reassigned on role change |
| US-15 | P2 | C9 | Simultaneous sanctions/PEP handling |
| US-16 | P1 | C14 | L2 overturns L1 closure |
| US-17 | P1 | C15 | Existing customer sanctions alert |
| US-18 | P1 | C18 | Supplementary SMR filing |

---

## Cycle Overview

### Foundation Cycles (Sequential)

| Cycle | Type | Dependencies | Description | Stories |
|-------|------|--------------|-------------|---------|
| C1 | Foundation | None | Core infrastructure: database, models, auth, webhook receipt | US-1 (partial) |
| C2 | Foundation | C1 | Audit logging and timeline infrastructure | FR-058, FR-059, Principle I |
| C3 | Foundation | C1, C2 | Notification and queue infrastructure | FR-066-069, D6, D13 |

### Feature Cycles (Parallel-Eligible After Foundation)

| Cycle | Type | Dependencies | Description | Stories |
|-------|------|--------------|-------------|---------|
| C4 | Feature [P] | C1, C2, C3 | L1 case triage: view, claim, close (false positive + satisfactory) | US-1, US-13 |
| C5 | Feature [P] | C1, C2, C3 | Customer communication: request info, record response | US-2 |
| C6 | Feature [P] | C1, C2, C3 | L1 to L2 escalation workflow | US-3 |
| C7 | Feature [P] | C1, C2, C3 | L2 investigation findings and SMR recommendation | US-4 |
| C8 | Feature | C7 | Manager SMR approval, draft generation, AUSTRAC recording | US-5, US-11 |
| C9 | Feature [P] | C1, C2, C3 | Sanctions blocking during onboarding | US-6, US-15 |
| C10 | Feature [P] | C9 | High-confidence PEP with EDD workflow | US-7 |
| C11 | Feature [P] | C9 | Low-confidence PEP provisional onboarding | US-8 |
| C12 | Feature [P] | C1, C2, C3 | SLA tracking, warnings, breach escalation | US-9 |
| C13 | Feature [P] | C1, C2, C3 | Dashboard with prioritization and metrics | US-12 |
| C14 | Feature | C4 | L2 quality review queue and case reopen | US-16 |
| C15 | Feature [P] | C9 | Existing customer sanctions (no auto-block) | US-17 |
| C16 | Feature [P] | C1, C2, C3 | Read-only reports and export | US-10 |
| C17 | Feature [P] | C1, C2, C3 | Role change case reassignment | US-14 |
| C18 | Feature | C8 | Supplementary SMR workflow | US-18 |

---

## Cycle Details

### Foundation Cycles

---

### Cycle 1: Core Infrastructure

> Stories: US-1 (partial - case creation)
> Dependencies: None
> Type: Foundation

**Scope**:
- PostgreSQL schema and migrations for core entities (Case, Customer, User, Assignment)
- FastAPI application setup with OIDC authentication (D5)
- Webhook endpoints with HMAC authentication (D11)
- GreenID/Indue webhook receivers with duplicate detection (D3, EC-005)
- Case reference generation (D9)
- Optimistic locking infrastructure (D8)

**Key Entities Created**:
- Case (core attributes, status, tier, SLA deadline)
- Customer (external reference, basic attributes)
- User (SSO integration, roles)
- Assignment (case-user relationship)
- WebhookReceipt (duplicate detection)

**Key Endpoints**:
- POST /webhooks/greenid
- POST /webhooks/indue
- GET /cases
- GET /cases/{caseId}

**Slice Rationale**:
This cycle establishes the minimum infrastructure for ALL other cycles. No user story can function without case creation from webhooks and basic case viewing. Foundation includes auth because all endpoints require authenticated context.

**Checkpoint**: Webhook creates a case; authenticated user can list and view cases.

---

### Cycle 2: Audit Logging Infrastructure

> Stories: FR-058, FR-059, FR-060, FR-061, Principle I
> Dependencies: C1
> Type: Foundation

**Scope**:
- AuditLog entity with immutability enforcement
- TimelineEntry entity for case-specific events
- PII redaction service (D12)
- Audit middleware for all mutating endpoints
- Case view logging (FR-059)
- Database triggers to prevent UPDATE/DELETE

**Key Entities Created**:
- AuditLog
- TimelineEntry

**Slice Rationale**:
Constitution Principle I (Immutable Audit Trail) is NON-NEGOTIABLE. Every subsequent cycle needs audit logging. Extracting this ensures consistent implementation across all features.

**Checkpoint**: All case operations create immutable audit entries; PII is redacted from payloads.

---

### Cycle 3: Notification and Queue Infrastructure

> Stories: FR-066-069, D6, D13
> Dependencies: C1, C2
> Type: Foundation

**Scope**:
- Notification entity and delivery service
- Celery task for email notifications
- In-app notification endpoints (list, count, mark read)
- Unassigned case queue endpoint (D13)
- Queue ordering by SLA urgency then creation date (FR-024, FR-025)

**Key Entities Created**:
- Notification

**Key Endpoints**:
- GET /queue/unassigned
- GET /notifications
- GET /notifications/count
- PATCH /notifications/{id}/read

**Slice Rationale**:
Queue and notification infrastructure is required by most feature workflows (case assignment, SLA warnings, escalations). Building this as foundation prevents duplication.

**Checkpoint**: Cases appear in unassigned queue; notifications are created and can be retrieved.

---

### Feature Cycles

---

### Cycle 4: L1 Case Triage Workflow

> Stories: US-1, US-13
> Dependencies: C1, C2, C3
> Type: Feature [P]

**Scope**:
- Claim case from queue (POST /cases/{caseId}/claim)
- Close as false positive with mandatory documentation (POST /cases/{caseId}/close)
- Close with satisfactory explanation (disposition type)
- L2 review status flag for satisfactory explanation closures (FR-012)
- Tier restrictions on case actions
- Customer account closure indicator (EC-008): Display "Customer Account Closed" status on cases where customer has closed their Spriggy account during investigation
- Prevention of auto-closure for cases with account closure indicator

**Key API Actions**:
- Claim case (OPEN -> IN_PROGRESS)
- Close case (OPEN/IN_PROGRESS -> CLOSED)
- Implicit claim on close (atomic operation)

**Edge Case Handling**:
- EC-008: When a customer account closure webhook is received, mark any active cases for that customer with "Customer Account Closed" indicator. Investigation continues regardless of account status. System prevents auto-closure of flagged cases.

**Acceptance Criteria from US-1**:
1. L1 sees false positive closure form with mandatory documentation
2. Closure changes status and appears in audit trail
3. Empty required fields prevent closure

**Acceptance Criteria from US-13**:
1. L1 sees mandatory documentation form for satisfactory explanation
2. Closure is flagged for L2 quality review (l2ReviewStatus = PENDING_REVIEW)
3. L2 can see L1-closed cases in quality review queue

**Acceptance Criteria from EC-008**:
1. Cases for customers who close their accounts display "Customer Account Closed" indicator
2. Such cases cannot be auto-closed and must proceed through normal investigation workflow
3. Analyst is aware of account closure status when reviewing case

**Slice Rationale**:
This is the most common L1 workflow. Delivers complete false positive and satisfactory explanation closure capability. L2 review queue (C14) can follow independently. EC-008 handling is included here because account closure impacts L1's triage decisions and case display.

**Checkpoint**: L1 can claim case from queue and close with documented justification; cases with closed accounts display indicator and prevent auto-closure.

---

### Cycle 5: Customer Communication Workflow

> Stories: US-2
> Dependencies: C1, C2, C3
> Type: Feature [P]

**Scope**:
- CommunicationTemplate entity (loaded from code repository per D10)
- CustomerCommunication entity
- Request information endpoint (POST /cases/{caseId}/request-information)
- Record response endpoint (POST /cases/{caseId}/record-response)
- State transitions: IN_PROGRESS -> PENDING_INFORMATION -> IN_PROGRESS

**Key Entities Created**:
- CommunicationTemplate
- CustomerCommunication

**Acceptance Criteria from US-2**:
1. L1 sees pre-approved communication templates for case type
2. Outreach recorded in case timeline with timestamp, template, content
3. L1 can record response and document assessment

**Slice Rationale**:
Customer communication is a discrete workflow that can be developed independently of closure types. Required for cases where information is needed before resolution.

**Checkpoint**: L1 can send templated request and record customer response.

---

### Cycle 6: L1 to L2 Escalation

> Stories: US-3
> Dependencies: C1, C2, C3
> Type: Feature [P]

**Scope**:
- Escalate case endpoint (POST /cases/{caseId}/escalate)
- State transition: IN_PROGRESS -> ESCALATED
- Tier change: L1 -> L2
- Documented reasoning requirement
- Case appears in L2 queue after escalation

**Acceptance Criteria from US-3**:
1. L1 sees "Escalate to L2" option requiring documented reasoning
2. Case moves to L2 queue with all prior documentation preserved
3. L2 sees escalation reasoning and complete case history

**Slice Rationale**:
Escalation is a distinct L1 action that enables the L2 investigation workflow. This slice focuses only on the escalation pathway; L2 investigation is C7.

**Checkpoint**: L1 can escalate case to L2 queue with documented reasoning.

---

### Cycle 7: L2 Investigation and SMR Recommendation

> Stories: US-4
> Dependencies: C1, C2, C3
> Type: Feature [P]

**Scope**:
- InvestigationFindings entity
- SMRRecommendation entity (without approval workflow)
- Create investigation findings endpoint
- Create SMR recommendation endpoint (POST /cases/{caseId}/smr/recommend)
- State transition: IN_PROGRESS -> PENDING_APPROVAL
- L2-only role restriction (BR-SMR-001)

**Key Entities Created**:
- InvestigationFindings
- SMRRecommendation

**Acceptance Criteria from US-4**:
1. L2 can document findings with structured fields (entities, patterns, indicators)
2. L2 can create SMR recommendation with narrative, evidence, reason for suspicion
3. Case enters "Pending Manager Approval" and manager is notified

**Slice Rationale**:
Investigation and SMR recommendation is a coherent L2 workflow. Approval (C8) is a separate slice because it involves different actor (Manager) and additional complexity (draft generation).

**Checkpoint**: L2 can document investigation and create SMR recommendation.

---

### Cycle 8: Manager SMR Approval and AUSTRAC Recording

> Stories: US-5, US-11
> Dependencies: C7
> Type: Feature

**Scope**:
- SMRDraft entity for generated documents
- Approve SMR endpoint (POST /cases/{caseId}/smr/approve)
- Reject SMR endpoint (POST /cases/{caseId}/smr/reject)
- Resubmit SMR endpoint (POST /cases/{caseId}/smr/resubmit)
- Record AUSTRAC reference endpoint (POST /cases/{caseId}/smr/record-reference)
- SMR draft document generation (FR-040)
- Segregation of duties enforcement (BR-SMR-002)
- State transitions: PENDING_APPROVAL -> CLOSED, CLOSED -> SMR_FILED
- 3-day SMR filing SLA tracking (FR-042)

**Key Entities Created**:
- SMRDraft

**Acceptance Criteria from US-5**:
1. Manager sees complete investigation documentation and recommendation
2. Approval generates SMR-formatted draft and records in audit trail
3. Rejection returns case to L2 with feedback

**Acceptance Criteria from US-11**:
1. Analyst sees "Record AUSTRAC Reference" option (no withdrawal option)
2. Reference recorded with case status change to "SMR Filed"
3. SMR without reference beyond 3 days is flagged

**Slice Rationale**:
SMR approval and AUSTRAC recording are tightly coupled - both involve the final stages of SMR workflow. Combining avoids orphan approval without recording capability.

**Checkpoint**: Manager can approve/reject SMR; analyst can record AUSTRAC reference.

---

### Cycle 9: Sanctions Blocking During Onboarding

> Stories: US-6, US-15
> Dependencies: C1, C2, C3
> Type: Feature [P]

**Scope**:
- OnboardingBlock entity with sync status tracking (EC-009)
- Automatic block creation on sanctions hit during onboarding
- Spriggy onboarding API callback integration (FR-028)
- Circuit breaker pattern for API calls (D3)
- Block clearance when analyst closes case
- Combined sanctions/PEP handling (FR-035, US-15)
- Case subtype: SANCTIONS_ONBOARDING
- CaseLink entity (introduced early for EC-014): Represents relationships between cases
- New alert detection for customers with existing open cases (EC-014): Create new case and link to existing open case for analyst awareness

**Key Entities Created**:
- OnboardingBlock
- CaseLink (introduced here, also used in C18)

**Edge Case Handling**:
- EC-009: If Spriggy onboarding API callback fails, apply circuit breaker pattern and queue for retry. Case status reflects intended block state with "Pending Sync" indicator.
- EC-014: When a new screening alert is received for a customer with existing open case(s), create a new case for the new alert and automatically create CaseLink entries pointing to all existing open cases. Display linked cases prominently for analyst awareness. Analyst decides whether to consolidate or investigate separately.

**Acceptance Criteria from US-6**:
1. Sanctions match blocks onboarding via API callback
2. Customer cannot proceed while block exists
3. Analyst clearance calls API to remove block

**Acceptance Criteria from US-15**:
1. Simultaneous sanctions/PEP creates single Sanctions case
2. PEP details captured as additional context
3. Analyst sees both match types in case details

**Acceptance Criteria from EC-014**:
1. New alert for customer with existing open case creates separate case with link
2. Analyst sees "Related Open Cases" section showing linked active investigations
3. Bidirectional navigation between linked cases is available

**Slice Rationale**:
Sanctions blocking is a critical compliance feature (NON-NEGOTIABLE per Principle II). Combined with US-15 because the same case creation logic handles both. CaseLink entity is introduced here (rather than waiting for C18) because EC-014 requires case-linking during alert processing. C18 (Supplementary SMR) will reuse the CaseLink entity.

**Checkpoint**: Sanctions webhook blocks onboarding; analyst clearance removes block; new alerts for customers with open cases are linked for analyst awareness.

---

### Cycle 10: High-Confidence PEP with EDD

> Stories: US-7
> Dependencies: C9
> Type: Feature [P]

**Scope**:
- EDDChecklist entity
- PEPThresholdConfig entity
- PEP confidence score classification (FR-030)
- Onboarding block for high-confidence PEP (> threshold)
- EDD checklist endpoints (GET, POST)
- Block clearance after EDD completion
- Case subtype: PEP_EDD_REQUIRED

**Key Entities Created**:
- EDDChecklist
- PEPThresholdConfig

**Acceptance Criteria from US-7**:
1. High-confidence PEP (> 80% default) blocks onboarding
2. Analyst sees structured EDD checklist (source of wealth, funds, purpose, monitoring)
3. EDD completion removes block with full attribution

**Slice Rationale**:
EDD workflow is a distinct extension of PEP handling. Depends on C9 for onboarding block infrastructure. Separated from low-confidence PEP (C11) because they have different behaviors.

**Checkpoint**: High-confidence PEP blocks onboarding; EDD completion clears block.

---

### Cycle 11: Low-Confidence PEP Provisional Onboarding

> Stories: US-8
> Dependencies: C9
> Type: Feature [P]

**Scope**:
- PEP case creation without onboarding block (<= threshold)
- Case subtype: PEP_PROVISIONAL_REVIEW
- Parallel review while customer proceeds
- Flag for ongoing enhanced monitoring on confirmation

**Acceptance Criteria from US-8**:
1. Low-confidence PEP (<= 80%) creates case without blocking
2. Case type is "PEP - Provisional Review"
3. Analyst can confirm false positive or flag for enhanced monitoring

**Slice Rationale**:
Low-confidence PEP has opposite behavior to high-confidence - no block. Separated to ensure clear implementation of the threshold boundary (EC-011: equal to threshold = low confidence).

**Checkpoint**: Low-confidence PEP creates case without blocking onboarding.

---

### Cycle 12: SLA Tracking and Breach Escalation

> Stories: US-9
> Dependencies: C1, C2, C3
> Type: Feature [P]

**Scope**:
- SLA calculation service with business day logic (D2)
- HolidayOverride entity for custom holidays
- SLA warning notifications at threshold (default 80%)
- Automatic escalation on SLA breach
- Manager notification for breaches
- Celery periodic task for SLA monitoring

**Key Entities Created**:
- HolidayOverride

**Acceptance Criteria from US-9**:
1. Warning notification at threshold (80% of SLA consumed)
2. Breach triggers automatic escalation and manager notification
3. SLA uses Australian business days (excluding weekends and holidays)

**Slice Rationale**:
SLA tracking is a cross-cutting concern that applies to all cases. Implemented as a monitoring/notification system that runs independently of user actions.

**Checkpoint**: SLA warnings sent; breached cases auto-escalate with manager notification.

---

### Cycle 13: Dashboard with Prioritization

> Stories: US-12
> Dependencies: C1, C2, C3
> Type: Feature [P]

**Scope**:
- Dashboard endpoint (GET /dashboard/my-cases)
- Queue metrics endpoint (GET /dashboard/queue-metrics)
- Case ordering: SLA urgency first, then creation date FIFO (FR-024, FR-025)
- SLA visual indicators (warning, breached)
- Real-time assignment updates (30s polling per D6)

**Acceptance Criteria from US-12**:
1. Dashboard shows cases ordered by SLA urgency, then creation date
2. Visual indicators distinguish approaching deadline from breached
3. Dashboard updates when new cases are assigned

**Slice Rationale**:
Dashboard is the primary analyst interface. Separated from reporting (C16) because it serves different purpose (operational vs governance).

**Checkpoint**: Analyst sees prioritized case list with SLA indicators.

---

### Cycle 14: L2 Quality Review and Case Reopen

> Stories: US-16
> Dependencies: C4
> Type: Feature

**Scope**:
- L2 review queue endpoint (GET /queue/l2-review)
- Accept L1 closure endpoint (POST /queue/l2-review/{caseId}/accept)
- Reopen case endpoint (POST /cases/{caseId}/reopen)
- State transition: CLOSED -> IN_PROGRESS
- l2ReviewStatus transitions (PENDING_REVIEW -> REVIEWED_ACCEPTED or REVIEWED_REOPENED)

**Acceptance Criteria from US-16**:
1. L2 sees complete case history including L1 closure reasoning
2. Reopen assigns case to L2 and changes status to "In Progress"
3. Audit trail shows reopen with L2 attribution

**Slice Rationale**:
L2 quality review depends on L1 satisfactory closure (C4) creating the review queue entries. This slice completes the quality oversight workflow.

**Checkpoint**: L2 can review L1 closures and reopen cases to their queue.

---

### Cycle 15: Existing Customer Sanctions

> Stories: US-17
> Dependencies: C9
> Type: Feature [P]

**Scope**:
- Existing customer detection in webhook processing
- Case subtype: SANCTIONS_EXISTING_CUSTOMER
- No automatic block for existing customers
- Account restriction recommendation capability

**Acceptance Criteria from US-17**:
1. Existing customer sanctions creates case without auto-block
2. Analyst can close as false positive without account restrictions
3. Analyst can recommend account restrictions with escalation

**Slice Rationale**:
Existing customer handling differs from onboarding - requires analyst judgment rather than automatic blocking. Shares infrastructure with C9 but different business logic.

**Checkpoint**: Existing customer sanctions creates case without blocking account.

---

### Cycle 16: Read-Only Reports and Export

> Stories: US-10
> Dependencies: C1, C2, C3
> Type: Feature [P]

**Scope**:
- Report endpoints (volumes, SLA, SMR, aged cases)
- Export endpoint (GET /reports/export)
- Materialized views for report data (D7)
- Read-only role enforcement (FR-064)
- CSV/Excel export generation

**Acceptance Criteria from US-10**:
1. Read-only user can view cases but not edit
2. Operational dashboards show volumes, SLA compliance, risk metrics
3. Export produces formatted report for committee presentation

**Slice Rationale**:
Reporting is a distinct capability for governance users serving a different audience (Risk Committee, Board) than the analyst dashboard (C13). Both cycles query the same foundation data (cases, audit logs) but produce different outputs: C13 provides operational views for analysts, while C16 provides governance reports and exports. No shared metrics logic is required between them; each implements its own aggregation queries against foundation data.

**Checkpoint**: Read-only user can view reports and export case data.

---

### Cycle 17: Role Change Case Reassignment

> Stories: US-14
> Dependencies: C1, C2, C3
> Type: Feature [P]

**Scope**:
- Role change detection on user update
- Automatic case unassignment (FR-026)
- Audit entries for each affected case (FR-027)
- Assignment with reason = ROLE_CHANGE

**Acceptance Criteria from US-14**:
1. Role change moves assigned cases to unassigned queue
2. Each case shows audit entry noting role change reassignment
3. No case history is lost

**Slice Rationale**:
Role change handling is an administrative feature that runs independently of case workflows. P2 priority allows deferral if needed.

**Checkpoint**: Role change unassigns all analyst cases with audit trail.

---

### Cycle 18: Supplementary SMR Filing

> Stories: US-18
> Dependencies: C8, C9
> Type: Feature

**Scope**:
- Create supplementary case endpoint (POST /cases/{caseId}/create-supplementary)
- Supplementary SMR follows full workflow
- Bidirectional navigation between linked cases (FR-046)
- Support for multiple supplementary filings (FR-047)
- Link type: SUPPLEMENTARY_TO_ORIGINAL (distinct from RELATED type used in EC-014)

**Key Entities Used**:
- CaseLink (created in C9, extended with SUPPLEMENTARY link type)

**Acceptance Criteria from US-18**:
1. "Create Supplementary Filing" option on SMR_FILED cases
2. New case is linked to original with visible relationship
3. Supplementary follows full SMR workflow (L2 recommendation, approval, recording)

**Slice Rationale**:
Supplementary SMR depends on completed SMR workflow (C8) and uses CaseLink entity (C9). This is the final piece of the SMR lifecycle.

**Checkpoint**: Can create supplementary SMR linked to original filed case.

---

## Dependency Graph

```
Foundation:
C1 (Core Infrastructure)
 └── C2 (Audit Logging)
      └── C3 (Notifications/Queue)

Feature Cycles:
After C1, C2, C3 complete, all [P] cycles can proceed in parallel:

C4 (L1 Triage + EC-008) ───────> C14 (L2 Review Queue)
C5 (Communication) [P]
C6 (Escalation) [P]
C7 (Investigation/SMR) ────────> C8 (Approval/AUSTRAC) ─┬─> C18 (Supplementary)
                                                        │
C9 (Sanctions + EC-014) [P] ──┬─> C10 (PEP EDD) [P]     │
                              ├─> C11 (Low-Conf PEP) [P]│
                              ├─> C15 (Existing Cust) [P]
                              └─────────────────────────┘
C12 (SLA Tracking) [P]
C13 (Dashboard) [P]
C16 (Reports) [P]
C17 (Role Change) [P]

Note: C18 depends on both C8 (for SMR workflow) and C9 (for CaseLink entity)
```

---

## Traceability Notes

### P1 Coverage

All P1 user stories are mapped:
- US-1, US-2, US-3: C4, C5, C6 (L1 workflows)
- US-4, US-5, US-11: C7, C8 (L2/Manager SMR workflow)
- US-6, US-7: C9, C10 (Onboarding blocking)
- US-9: C12 (SLA enforcement)
- US-12: C13 (Dashboard)
- US-13: C4 (L1 satisfactory closure)
- US-16: C14 (L2 quality review)
- US-17: C15 (Existing customer sanctions)
- US-18: C18 (Supplementary SMR)

### P2 Coverage

All P2 user stories are mapped:
- US-8: C11 (Low-confidence PEP)
- US-10: C16 (Reports and export)
- US-14: C17 (Role change handling)
- US-15: C9 (Combined with sanctions handling)

### Constitution Alignment

| Principle | Cycles |
|-----------|--------|
| I. Immutable Audit Trail | C2 (primary), all other cycles use audit service |
| II. RBAC with Segregation | C1 (auth), C7/C8 (SMR segregation) |
| III. Test-First Development | All cycles follow TDD structure |
| IV. Explicit Error Handling | C9 (circuit breaker), C12 (SLA handling) |
| V. SLA Tracking | C12 (primary), C1/C13 (SLA fields) |
| VI. Sensitive Data Protection | C2 (PII redaction), C1 (HMAC auth) |
| VII. External Integration Resilience | C9 (Spriggy API), C1 (webhook handling) |

---

## Parallel Opportunities

After foundation cycles (C1, C2, C3) complete, the following cycles have no inter-dependencies and can proceed in parallel:

**Parallel Group A** (Core Workflows):
- C4: L1 Triage (includes EC-008 account closure handling)
- C5: Customer Communication
- C6: L1 Escalation
- C7: L2 Investigation

**Parallel Group B** (Onboarding):
- C9: Sanctions Blocking (includes EC-014 case-linking, creates CaseLink entity)
- C10: PEP EDD (after C9)
- C11: Low-Confidence PEP (after C9)
- C15: Existing Customer (after C9)

**Parallel Group C** (System):
- C12: SLA Tracking
- C13: Dashboard
- C16: Reports and Export
- C17: Role Change

**Sequential Dependencies**:
- C8 depends on C7 (SMR approval requires SMR recommendation)
- C14 depends on C4 (L2 review requires L1 closures to review)
- C18 depends on C8 and C9 (supplementary SMR requires both SMR workflow and CaseLink entity)

---

## Next Steps

Run `/humaninloop:tasks` with phase=tasks to generate detailed implementation tasks for each cycle.
