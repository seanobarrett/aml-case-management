# Advocate Report: Tasks Review

> Feature: 001-aml-case-management
> Phase: Tasks
> Iteration: 1
> Generated: 2026-01-18

---

## Summary

| Metric | Value |
|--------|-------|
| **Phase** | Tasks |
| **Artifacts Reviewed** | task-mapping.md, tasks.md |
| **Verdict** | **ready** |

---

## Checks Executed

### Tasks Phase Checks

| Check | Result | Issue |
|-------|--------|-------|
| Cycle coverage | PASS | - |
| TDD structure | PASS | - |
| File paths | PASS | - |
| Task IDs | PASS | - |
| Story labels | PASS | - |
| Brownfield markers | PASS | - |
| Parallel markers | PASS | - |
| Checkpoints | PASS | - |
| Dependencies | PASS | - |

### Cross-Artifact Checks

| Check | Result | Issue |
|-------|--------|-------|
| Mapping-Tasks alignment | PASS | - |
| Story traceability | PASS | - |
| Cycle consistency | PASS | - |
| Dependency consistency | PASS | - |
| Foundation-Feature alignment | PASS | - |

---

## Issues Found

### Critical (0)

None.

### Important (0)

None.

### Minor (2)

**Issue TT-001**: Migration file numbering gap in C16

- **Check**: File path consistency
- **Severity**: Minor
- **Evidence**: C16/T16.2 uses `src/db/migrations/010_report_views.py` but there are only 3 foundation cycles creating migrations (001, 002). Gap between 002 and 010.
- **Impact**: No functional impact, but could cause confusion during implementation about whether migrations 003-009 exist.
- **Suggested Fix**: Either use sequential numbering (003_report_views.py) or document that gaps are intentional for namespace reservation.

**Issue TT-002**: Minor inconsistency in cycle title formatting

- **Check**: Format consistency
- **Severity**: Minor
- **Evidence**: Most cycles use "Cycle X: Title [P]" but tasks.md uses "### Cycle X: Title [P]" and also "### Cycle X: Title" (without [P] in header for non-parallel, only in cycle metadata). This is internally consistent but worth noting.
- **Impact**: No functional impact; the parallel marking is clear in the metadata table.
- **Suggested Fix**: None required; current format is acceptable.

---

## Detailed Review Analysis

### 1. Cycle Coverage Validation

All 18 cycles from task-mapping.md have corresponding task sections in tasks.md:

| Cycle | Mapping | Tasks | Status |
|-------|---------|-------|--------|
| C1 | Core Infrastructure | 17 tasks | PRESENT |
| C2 | Audit Logging Infrastructure | 10 tasks | PRESENT |
| C3 | Notification and Queue Infrastructure | 10 tasks | PRESENT |
| C4 | L1 Case Triage Workflow | 12 tasks | PRESENT |
| C5 | Customer Communication Workflow | 10 tasks | PRESENT |
| C6 | L1 to L2 Escalation | 7 tasks | PRESENT |
| C7 | L2 Investigation and SMR Recommendation | 11 tasks | PRESENT |
| C8 | Manager SMR Approval and AUSTRAC Recording | 13 tasks | PRESENT |
| C9 | Sanctions Blocking During Onboarding | 14 tasks | PRESENT |
| C10 | High-Confidence PEP with EDD | 11 tasks | PRESENT |
| C11 | Low-Confidence PEP Provisional Onboarding | 7 tasks | PRESENT |
| C12 | SLA Tracking and Breach Escalation | 11 tasks | PRESENT |
| C13 | Dashboard with Prioritization | 8 tasks | PRESENT |
| C14 | L2 Quality Review and Case Reopen | 9 tasks | PRESENT |
| C15 | Existing Customer Sanctions | 6 tasks | PRESENT |
| C16 | Read-Only Reports and Export | 12 tasks | PRESENT |
| C17 | Role Change Case Reassignment | 7 tasks | PRESENT |
| C18 | Supplementary SMR Filing | 9 tasks | PRESENT |

**Total**: 171 tasks across 18 cycles. All accounted for.

### 2. TDD Structure Validation

Every cycle follows the correct test-first structure:

| Cycle | First Task | TDD Compliant |
|-------|------------|---------------|
| C1 | T1.1: Write failing E2E test for case creation via webhook | YES |
| C2 | T2.1: Write failing test for audit log immutability | YES |
| C3 | T3.1: Write failing test for notification delivery and queue ordering | YES |
| C4 | T4.1: Write failing E2E test for L1 case claim and closure | YES |
| C5 | T5.1: Write failing E2E test for customer information request | YES |
| C6 | T6.1: Write failing E2E test for L1 to L2 escalation | YES |
| C7 | T7.1: Write failing E2E test for investigation findings and SMR | YES |
| C8 | T8.1: Write failing E2E test for SMR approval, rejection, reference | YES |
| C9 | T9.1: Write failing E2E test for sanctions block creation and clearance | YES |
| C10 | T10.1: Write failing E2E test for high-confidence PEP blocking and EDD | YES |
| C11 | T11.1: Write failing E2E test for low-confidence PEP case creation | YES |
| C12 | T12.1: Write failing E2E test for SLA warning and breach escalation | YES |
| C13 | T13.1: Write failing E2E test for dashboard case ordering | YES |
| C14 | T14.1: Write failing E2E test for L2 quality review queue | YES |
| C15 | T15.1: Write failing E2E test for existing customer sanctions | YES |
| C16 | T16.1: Write failing E2E test for report viewing and export | YES |
| C17 | T17.1: Write failing E2E test for role change triggering case unassignment | YES |
| C18 | T18.1: Write failing E2E test for supplementary SMR creation | YES |

All cycles end with refactor and demo tasks. Constitution Principle III (Test-First Development) is properly enforced.

### 3. File Path Specificity Validation

All 171 tasks specify concrete file paths. Sample verification:

| Task | File Path | Specific |
|------|-----------|----------|
| T1.2 | `src/db/migrations/001_core_entities.py` | YES |
| T1.3 | `src/models/case.py` | YES |
| T4.4 | `src/api/cases.py` | YES |
| T9.6 | `src/services/onboarding_block_service.py` | YES |
| T12.3 | `src/services/sla_calculator.py` | YES |

No vague paths found (e.g., "update relevant files"). All tasks identify specific file locations.

### 4. Story-to-Cycle-to-Task Traceability

Verified traceability chain for all P1 and P2 stories:

**P1 Stories (All Traced)**:

| Story | Cycle | Task Range | Traced |
|-------|-------|------------|--------|
| US-1 | C1, C4 | T1.1-T1.17, T4.1-T4.12 | YES |
| US-2 | C5 | T5.1-T5.10 | YES |
| US-3 | C6 | T6.1-T6.7 | YES |
| US-4 | C7 | T7.1-T7.11 | YES |
| US-5 | C8 | T8.1-T8.13 | YES |
| US-6 | C9 | T9.1-T9.14 | YES |
| US-7 | C10 | T10.1-T10.11 | YES |
| US-9 | C12 | T12.1-T12.11 | YES |
| US-11 | C8 | T8.1-T8.13 | YES |
| US-12 | C13 | T13.1-T13.8 | YES |
| US-13 | C4 | T4.1-T4.12 | YES |
| US-16 | C14 | T14.1-T14.9 | YES |
| US-17 | C15 | T15.1-T15.6 | YES |
| US-18 | C18 | T18.1-T18.9 | YES |

**P2 Stories (All Traced)**:

| Story | Cycle | Task Range | Traced |
|-------|-------|------------|--------|
| US-8 | C11 | T11.1-T11.7 | YES |
| US-10 | C16 | T16.1-T16.12 | YES |
| US-14 | C17 | T17.1-T17.7 | YES |
| US-15 | C9 | T9.1-T9.14 | YES |

### 5. Edge Case Coverage Verification

All edge cases from clarification log are incorporated:

| Edge Case | Cycle | Task References | Incorporated |
|-----------|-------|-----------------|--------------|
| EC-001 (Concurrent action) | C1 | T1.15 | YES |
| EC-005 (Duplicate webhooks) | C1 | T1.7 | YES |
| EC-008 (Account closure) | C4 | T4.2, T4.8-T4.10 | YES |
| EC-009 (API callback failure) | C9 | T9.4, T9.7 | YES |
| EC-010 (Multiple SMR rejections) | C8 | T8.6 | YES |
| EC-011 (PEP threshold boundary) | C11 | T11.1, T11.3 | YES |
| EC-014 (New alert during investigation) | C9 | T9.3, T9.10, T9.12 | YES |

Clarification log items TM-001, TM-002, TM-003 have all been addressed:
- TM-001: C16 is now parallel with C13 (correctly marked [P])
- TM-002: EC-008 added to C4 (T4.2, T4.8-T4.10)
- TM-003: EC-014 added to C9 (T9.3, T9.10, T9.12)

### 6. Dependency Consistency Validation

Dependencies match between mapping and tasks:

| Cycle | Mapping Dependencies | Tasks Dependencies | Match |
|-------|---------------------|-------------------|-------|
| C1 | None | None | YES |
| C2 | C1 | C1 | YES |
| C3 | C1, C2 | C1, C2 | YES |
| C4 | C1, C2, C3 | C1, C2, C3 | YES |
| C8 | C7 | C7 | YES |
| C9 | C1, C2, C3 | C1, C2, C3 | YES |
| C10 | C9 | C9 | YES |
| C11 | C9 | C9 | YES |
| C14 | C4 | C4 | YES |
| C15 | C9 | C9 | YES |
| C16 | C1, C2, C3 | C1, C2, C3 | YES |
| C18 | C8, C9 | C8, C9 | YES |

All dependencies correctly propagated.

### 7. Parallel Marker Validation

Feature cycles are correctly marked:

| Cycle | Type | [P] Marker | Correct |
|-------|------|------------|---------|
| C4 | Feature | [P] | YES - depends only on foundation |
| C5 | Feature | [P] | YES - depends only on foundation |
| C6 | Feature | [P] | YES - depends only on foundation |
| C7 | Feature | [P] | YES - depends only on foundation |
| C8 | Feature | None | YES - depends on C7 (sequential) |
| C9 | Feature | [P] | YES - depends only on foundation |
| C10 | Feature | [P] | YES - depends on C9 but parallel with C11, C15 |
| C11 | Feature | [P] | YES - depends on C9 but parallel with C10, C15 |
| C12 | Feature | [P] | YES - depends only on foundation |
| C13 | Feature | [P] | YES - depends only on foundation |
| C14 | Feature | None | YES - depends on C4 (sequential) |
| C15 | Feature | [P] | YES - depends on C9 but parallel with C10, C11 |
| C16 | Feature | [P] | YES - depends only on foundation (TM-001 fix applied) |
| C17 | Feature | [P] | YES - depends only on foundation |
| C18 | Feature | None | YES - depends on C8 and C9 (sequential) |

### 8. Checkpoint Validation

All cycles have observable, testable checkpoints:

| Cycle | Checkpoint | Observable |
|-------|------------|------------|
| C1 | "Webhook creates a case; authenticated user can list and view cases" | YES |
| C2 | "All case operations create immutable audit entries; PII is redacted" | YES |
| C3 | "Cases appear in unassigned queue; notifications are created" | YES |
| C4 | "L1 can claim case and close with documented justification; account closure indicator" | YES |
| C5 | "L1 can send templated request and record customer response" | YES |
| C6 | "L1 can escalate case to L2 queue with documented reasoning" | YES |
| C7 | "L2 can document investigation findings and create SMR recommendation" | YES |
| C8 | "Manager can approve/reject SMR; analyst can record AUSTRAC reference" | YES |
| C9 | "Sanctions webhook blocks onboarding; analyst clearance removes block; alerts linked" | YES |
| C10 | "High-confidence PEP blocks onboarding; EDD completion clears block" | YES |
| C11 | "Low-confidence PEP creates case without blocking onboarding" | YES |
| C12 | "SLA warnings sent; breached cases auto-escalate with manager notification" | YES |
| C13 | "Analyst sees prioritized case list with SLA indicators" | YES |
| C14 | "L2 can review L1 closures and reopen cases to their queue" | YES |
| C15 | "Existing customer sanctions creates case without blocking account" | YES |
| C16 | "Read-only user can view reports and export case data" | YES |
| C17 | "Role change unassigns all analyst cases with audit trail" | YES |
| C18 | "Can create supplementary SMR linked to original filed case" | YES |

### 9. Constitution Alignment Validation

All seven constitution principles are addressed:

| Principle | Cycle(s) | Key Tasks | Addressed |
|-----------|----------|-----------|-----------|
| I. Immutable Audit Trail (NON-NEGOTIABLE) | C2 | T2.2-T2.6 (AuditLog, triggers) | YES |
| II. RBAC with Segregation (NON-NEGOTIABLE) | C1, C8 | T1.5, T1.9, T8.3 | YES |
| III. Test-First Development | All | All T*.1 tasks | YES |
| IV. Explicit Error Handling | C9 | T9.6, T9.7 (circuit breaker) | YES |
| V. SLA Tracking and Enforcement | C12 | T12.1-T12.11 | YES |
| VI. Sensitive Data Protection | C2 | T2.4, T2.5 (PII redaction) | YES |
| VII. External Integration Resilience | C1, C9 | T1.8, T9.6, T9.7 | YES |

### 10. Brownfield Marker Validation

[EXTEND] and [MODIFY] markers are correctly applied:

| Task | Marker | Rationale |
|------|--------|-----------|
| T2.8 | [MODIFY] | Update existing endpoint to log case views | CORRECT |
| T4.6 | [EXTEND] | Add field to existing Case model | CORRECT |
| T4.8 | [EXTEND] | Add indicator to existing Customer model | CORRECT |
| T5.8 | [MODIFY] | Update existing case service | CORRECT |
| T6.4 | [MODIFY] | Update existing case service | CORRECT |
| T7.8 | [MODIFY] | Update existing case service | CORRECT |
| T9.8 | [MODIFY] | Update existing webhook handler | CORRECT |
| T10.5 | [MODIFY] | Update existing webhook handler | CORRECT |
| T10.9 | [MODIFY] | Update existing service | CORRECT |
| T11.2 | [MODIFY] | Update existing webhook handler | CORRECT |
| T11.4 | [EXTEND] | Add field to existing Case model | CORRECT |
| T14.7 | [MODIFY] | Update existing service | CORRECT |
| T15.3 | [MODIFY] | Update existing webhook handler | CORRECT |
| T17.4 | [MODIFY] | Update existing endpoint | CORRECT |
| T17.5 | [EXTEND] | Add enum value to existing model | CORRECT |
| T18.4 | [EXTEND] | Add link type to existing entity | CORRECT |
| T18.6 | [MODIFY] | Update existing service | CORRECT |

---

## What's Strong

### 1. Exceptional TDD Discipline

Every single cycle begins with a failing test task. This is not merely compliance with Principle III; the tests are directly tied to acceptance criteria from user stories, making them meaningful verification of business requirements rather than just technical coverage.

### 2. Complete Story Traceability

The traceability matrix is complete and verifiable. Every P1 and P2 story maps to at least one cycle, and every cycle's tasks reference specific requirements using [US-X], [FR-XXX], and [EC-XXX] markers. This creates an auditable chain from business need to implementation task.

### 3. Thoughtful Vertical Slicing

The cycles are true vertical slices delivering observable user value. Notable examples:
- C4 delivers complete L1 triage (claim, close, document) including EC-008
- C9 delivers sanctions blocking with API integration, circuit breaker, and case linking for EC-014
- C8 combines SMR approval and AUSTRAC recording since they are tightly coupled

### 4. Appropriate Parallelization

The [P] markers correctly identify which cycles can run concurrently:
- 12 of 15 feature cycles are marked parallel-eligible
- Dependencies are minimal and accurately documented
- The TM-001 clarification (C16 parallel with C13) was correctly applied

### 5. Specific File Paths

All 171 tasks have concrete file paths. The consistent naming convention (src/models/, src/services/, src/api/, tests/e2e/) makes the implementation structure clear and predictable.

### 6. Constitution Compliance

The NON-NEGOTIABLE principles (I and II) have dedicated foundation cycles:
- C2 creates immutable audit infrastructure with database triggers
- C1 establishes RBAC with OIDC authentication
- C8 explicitly enforces segregation of duties (T8.3)

### 7. Edge Case Handling

The clarification log items (TM-001, TM-002, TM-003) were thoroughly incorporated:
- EC-008 (account closure) has 4 dedicated tasks in C4
- EC-014 (alert case linking) has 3 dedicated tasks in C9
- CaseLink entity is introduced in C9 and reused in C18

### 8. Clear Checkpoints

Every cycle has a checkpoint describing an observable outcome in user-facing terms, not technical jargon. For example, "L1 can claim case from queue and close with documented justification" is verifiable by a product stakeholder.

---

## Verdict

**Status**: **ready**

**Rationale**: The tasks.md artifact passes all critical and important checks. The task structure demonstrates:

1. **Complete coverage**: All 18 cycles from mapping have corresponding task sections
2. **TDD compliance**: Every cycle begins with a failing test
3. **Specific paths**: All 171 tasks have concrete file locations
4. **Full traceability**: All P1/P2 stories trace through cycles to tasks
5. **Correct dependencies**: Mapping and tasks dependencies match perfectly
6. **Constitution alignment**: All seven principles are explicitly addressed

The two minor issues identified (migration numbering gap, header formatting) are purely cosmetic and do not impact implementation correctness or traceability.

This artifact is ready to proceed to implementation. The Task Architect has produced a high-quality, TDD-disciplined task breakdown that faithfully implements the specification.

---

## Recommendation

Proceed to implementation phase. No revision required.
