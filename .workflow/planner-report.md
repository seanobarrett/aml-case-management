# Planner Report: Tasks

> Feature: 001-aml-case-management
> Phase: Tasks
> Iteration: 1
> Generated: 2026-01-18

---

## Summary

| Metric | Value |
|--------|-------|
| **Phase** | Tasks |
| **Artifact** | /Users/sean/specs/001-aml-case-management/tasks.md |
| **Completion** | Complete |

---

## What Was Produced

Generated implementation task list from the approved task-mapping.md with 18 cycles organized into TDD structure. Each cycle follows test-first discipline with specific file paths for all tasks. Foundation cycles (C1-C3) are sequential; feature cycles are marked with [P] for parallel eligibility where appropriate.

Incorporated clarification log updates:
- TM-001: C16 is now parallel with C13 (no dependency between them)
- TM-002: EC-008 (customer account closure during investigation) added to C4
- TM-003: EC-014 (new alert during active investigation) added to C9

---

## Key Outputs

### Cycle Statistics

| Category | Count |
|----------|-------|
| Total Cycles | 18 |
| Foundation Cycles (sequential) | 3 |
| Feature Cycles | 15 |
| Parallel-Eligible Cycles | 12 |
| Total Tasks | 171 |
| Average Tasks per Cycle | 9.5 |

### Foundation Cycles

| Cycle | Tasks | Description |
|-------|-------|-------------|
| C1 | 17 | Core Infrastructure (database, models, auth, webhooks) |
| C2 | 10 | Audit Logging Infrastructure (immutability, PII redaction) |
| C3 | 10 | Notification and Queue Infrastructure |

### Feature Cycles

| Cycle | Tasks | Type | Dependencies | Description |
|-------|-------|------|--------------|-------------|
| C4 | 12 | [P] | C1,C2,C3 | L1 Case Triage + EC-008 account closure |
| C5 | 10 | [P] | C1,C2,C3 | Customer Communication Workflow |
| C6 | 7 | [P] | C1,C2,C3 | L1 to L2 Escalation |
| C7 | 11 | [P] | C1,C2,C3 | L2 Investigation and SMR Recommendation |
| C8 | 13 | - | C7 | Manager SMR Approval and AUSTRAC Recording |
| C9 | 14 | [P] | C1,C2,C3 | Sanctions Blocking + EC-014 case linking |
| C10 | 11 | [P] | C9 | High-Confidence PEP with EDD |
| C11 | 7 | [P] | C9 | Low-Confidence PEP Provisional Onboarding |
| C12 | 11 | [P] | C1,C2,C3 | SLA Tracking and Breach Escalation |
| C13 | 8 | [P] | C1,C2,C3 | Dashboard with Prioritization |
| C14 | 9 | - | C4 | L2 Quality Review and Case Reopen |
| C15 | 6 | [P] | C9 | Existing Customer Sanctions |
| C16 | 12 | [P] | C1,C2,C3 | Read-Only Reports and Export |
| C17 | 7 | [P] | C1,C2,C3 | Role Change Case Reassignment |
| C18 | 9 | - | C8,C9 | Supplementary SMR Filing |

---

## Vertical Slice Rationale

Each cycle was structured as a true vertical slice that delivers observable, testable value:

1. **Foundation Cycles (C1-C3)**: Sequential because they establish infrastructure ALL features depend on. C1 creates the core entities and webhook handling; C2 adds audit logging (NON-NEGOTIABLE per Principle I); C3 adds notification and queue infrastructure used by most workflows.

2. **L1/L2 Workflow Cycles (C4-C8)**: Represent the complete analyst workflow from triage through SMR filing. C4-C7 are parallel-eligible after foundation. C8 depends on C7 (approval requires recommendation). C14 depends on C4 (L2 review requires L1 closures to review).

3. **Onboarding Cycles (C9-C11, C15)**: C9 establishes sanctions blocking and introduces CaseLink entity. C10/C11/C15 extend C9 for different PEP/sanctions scenarios and can run in parallel.

4. **System Cycles (C12-C13, C16-C17)**: Independent system features that only depend on foundation. All parallel-eligible. C16 has no dependency on C13 (per TM-001 clarification).

5. **Supplementary SMR (C18)**: Final feature that depends on both C8 (SMR workflow) and C9 (CaseLink entity for linking cases).

---

## TDD Structure Applied

Every cycle follows test-first discipline:

1. **First task**: Write failing E2E or integration test
   - Example: `T4.1: Write failing E2E test for L1 case claim and closure`
   - Tests express acceptance criteria from user stories
   - Tests MUST fail before implementation begins

2. **Implementation tasks**: Make tests pass with minimal code
   - Models, services, and endpoints in logical order
   - Brownfield markers ([EXTEND], [MODIFY]) where applicable

3. **Refactor task**: Improve code quality without changing behavior
   - Example: `T4.11: Refactor and verify tests pass`

4. **Demo task**: Validate observable behavior
   - Example: `T4.12: Demo L1 can claim case and close with documented justification`
   - Verifies acceptance criteria from user stories

5. **Checkpoint**: Concrete, observable outcome
   - Example: "L1 can claim case from queue and close with documented justification"

---

## Constitution Alignment

| Principle | Implementation in Tasks |
|-----------|------------------------|
| **I. Immutable Audit Trail (NON-NEGOTIABLE)** | C2 dedicated to audit infrastructure. T2.2-T2.6 create AuditLog and TimelineEntry with immutability. T2.4-T2.5 implement PII redaction. T2.6 creates database triggers to prevent UPDATE/DELETE. |
| **II. RBAC with Segregation (NON-NEGOTIABLE)** | C1 establishes OIDC auth (T1.9) and User model with roles (T1.5). C8 enforces segregation of duties for SMR approval (T8.3). |
| **III. Test-First Development** | Every cycle begins with failing test (T*.1). All 171 tasks organized in TDD order. |
| **IV. Explicit Error Handling** | C9 implements circuit breaker pattern (T9.6) and retry logic for Spriggy API (T9.7). |
| **V. SLA Tracking and Enforcement** | C12 implements business day calculator (T12.3), warnings (T12.4), and auto-escalation (T12.5). |
| **VI. Sensitive Data Protection** | C2 implements PII redaction service (T2.4) and applies to audit payloads (T2.5). |
| **VII. External Integration Resilience** | C1 implements HMAC webhook auth (T1.8). C9 implements circuit breaker (T9.6) and retry with backoff (T9.7). |

---

## Parallel Execution Opportunities

After foundation cycles (C1, C2, C3) complete, the following parallel groups can proceed simultaneously:

**Parallel Group A (Core Workflows)**:
- C4: L1 Triage (includes EC-008)
- C5: Customer Communication
- C6: L1 Escalation
- C7: L2 Investigation

**Parallel Group B (Onboarding)**:
- C9: Sanctions Blocking (includes EC-014, creates CaseLink entity)
- Then C10, C11, C15 can parallelize (all depend on C9)

**Parallel Group C (System)**:
- C12: SLA Tracking
- C13: Dashboard
- C16: Reports and Export
- C17: Role Change

**Sequential Dependencies**:
- C8 waits for C7 (SMR approval requires recommendation)
- C14 waits for C4 (L2 review requires L1 closures)
- C18 waits for C8 and C9 (supplementary SMR requires both)

---

## File Path Conventions

All tasks specify concrete file paths following this structure:

| Category | Path Pattern | Examples |
|----------|-------------|----------|
| E2E Tests | `tests/e2e/test_[feature].py` | `tests/e2e/test_l1_triage.py` |
| Models | `src/models/[entity].py` | `src/models/case.py` |
| Services | `src/services/[service]_service.py` | `src/services/case_service.py` |
| API Endpoints | `src/api/[resource].py` | `src/api/cases.py` |
| Tasks (Celery) | `src/tasks/[category]_tasks.py` | `src/tasks/notification_tasks.py` |
| Migrations | `src/db/migrations/[number]_[name].py` | `src/db/migrations/001_core_entities.py` |
| Middleware | `src/middleware/[name].py` | `src/middleware/audit.py` |

---

## Open Questions

None. All clarification items from the mapping phase have been resolved and incorporated:
- TM-001: C16 parallelization with C13 applied
- TM-002: EC-008 added to C4 (tasks T4.2, T4.8-T4.10)
- TM-003: EC-014 added to C9 (tasks T9.3, T9.10, T9.12)

---

## Ready for Review

**Yes** - The tasks.md artifact is complete and ready for Devil's Advocate review.

All success criteria are met:
- Every cycle from mapping has corresponding tasks
- Each cycle follows TDD structure (test first)
- Foundation cycles are sequential; feature cycles marked [P] where appropriate
- Every task has a specific file path
- Tasks within each cycle have correct dependencies
- Acceptance criteria from stories inform test definitions
- Constitution principles are addressed in appropriate cycles
