---
type: tasks-request
phase: completed
status: completed
iteration: 1
feature_id: 001-aml-case-management
created: 2026-01-15T22:40:00Z
updated: 2026-01-15T23:02:00Z
mapping_status: complete
tasks_status: complete
---

# Tasks Request

## Feature Context

| Aspect | Value |
|--------|-------|
| Feature ID | 001-aml-case-management |
| Plan Status | complete |
| Current Phase | mapping |
| Constitution | Embedded (from plan workflow) |

## File Paths

| File | Path | Status |
|------|------|--------|
| Spec | /Users/sean/specs/001-aml-case-management/spec.md | complete |
| Plan | /Users/sean/specs/001-aml-case-management/plan.md | complete |
| Research | /Users/sean/specs/001-aml-case-management/research.md | complete |
| Data Model | /Users/sean/specs/001-aml-case-management/data-model.md | complete |
| Contracts | /Users/sean/specs/001-aml-case-management/contracts/api.yaml | complete |
| Task Mapping | /Users/sean/specs/001-aml-case-management/task-mapping.md | pending |
| Tasks | /Users/sean/specs/001-aml-case-management/tasks.md | pending |
| Architect Report | /Users/sean/specs/001-aml-case-management/.workflow/planner-report.md | - |
| Advocate Report | /Users/sean/specs/001-aml-case-management/.workflow/advocate-report.md | - |

## Constitution Principles

The following principles from the constitution MUST guide task generation:

1. **I. Immutable Audit Trail (NON-NEGOTIABLE)**: All case actions, decisions, and state transitions MUST be recorded immutably with full attribution and timestamp. 7-year retention.

2. **II. Role-Based Access Control with Segregation of Duties (NON-NEGOTIABLE)**: Four roles enforced (L1, L2, AML Manager, Read-Only). L1 cannot approve SMRs. L2 cannot approve own recommendations.

3. **III. Test-First Development**: 80% coverage minimum, 100% on critical paths (SMR generation, sanctions blocking).

4. **IV. Explicit Error Handling and Recovery**: Timeout, retry, circuit breaker patterns for external services. No silent failures.

5. **V. SLA Tracking and Enforcement**: Business day calculations, automatic escalation on breach.

6. **VI. Sensitive Data Protection**: TLS 1.2+, AES-256 at rest, no PII in logs.

7. **VII. External Integration Resilience**: 30s timeouts, retry with backoff, circuit breaker (5 failures to open).

## Tech Stack

| Aspect | Value |
|--------|-------|
| Language | Python 3.12 |
| Framework | FastAPI |
| Database | PostgreSQL 15 |
| Task Queue | Celery + Redis |

## Supervisor Instructions

**Phase**: Tasks Review

Review the task list for completeness and TDD structure.

**Read**:
- Task Mapping: `/Users/sean/specs/001-aml-case-management/task-mapping.md`
- Tasks: `/Users/sean/specs/001-aml-case-management/tasks.md`
- Spec: `/Users/sean/specs/001-aml-case-management/spec.md`
- Architect report: `/Users/sean/specs/001-aml-case-management/.workflow/planner-report.md`

**Write**:
- Report: `/Users/sean/specs/001-aml-case-management/.workflow/advocate-report.md`

**Use Skills**:
- `validation-task-artifacts` (phase: tasks)

**Report format**: Follow `/Users/sean/.claude/plugins/cache/humaninloop-plugins/humaninloop/0.7.4/templates/advocate-report-template.md`

**Check**:
- TDD structure: test-first ordering in each cycle
- Cycle coverage: all 18 mapped cycles have tasks
- File path specificity: exact paths for models, services, endpoints, tests
- Cross-artifact consistency with mapping
- Requirements traceability: FR-XXX, US-XX, EC-XXX references
- Checkpoints: observable outcomes for each cycle

## Clarification Log

### Phase: Mapping - Iteration 1

#### Gaps Identified (from Devil's Advocate)

| ID | Severity | Description |
|----|----------|-------------|
| TM-001 | Important | C16 dependency on C13 limits parallelization unnecessarily |
| TM-002 | Important | EC-008 (customer account closure during investigation) not mapped |
| TM-003 | Important | EC-014 (new alert during active investigation) not mapped |

#### User Answers

| Gap ID | Question | User Answer |
|--------|----------|-------------|
| TM-001 | Should C16 be parallel with C13? | Yes, make parallel - remove dependency |
| TM-002 | Where to add EC-008? | Add to C4 (L1 Triage) |
| TM-003 | Where to add EC-014? | Add to C9 (Sanctions Onboarding) |
