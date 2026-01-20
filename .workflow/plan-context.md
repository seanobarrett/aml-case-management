---
type: planning-request
phase: completed
status: completed
iteration: 2
feature_id: 001-aml-case-management
created: 2026-01-15T21:45:00Z
updated: 2026-01-15T22:35:00Z
research_status: complete
datamodel_status: complete
contracts_status: complete
---

# Planning Request

## Feature Context

| Aspect | Value |
|--------|-------|
| Feature ID | 001-aml-case-management |
| Spec Status | complete |
| Current Phase | research |
| Constitution | Embedded (from specify workflow) |

## File Paths

| File | Path | Status |
|------|------|--------|
| Spec | /Users/sean/specs/001-aml-case-management/spec.md | complete |
| Research | /Users/sean/specs/001-aml-case-management/research.md | pending |
| Data Model | /Users/sean/specs/001-aml-case-management/data-model.md | pending |
| Contracts | /Users/sean/specs/001-aml-case-management/contracts/ | pending |
| Planner Report | /Users/sean/specs/001-aml-case-management/.workflow/planner-report.md | - |
| Advocate Report | /Users/sean/specs/001-aml-case-management/.workflow/advocate-report.md | - |

## Constitution Principles

The following principles from the constitution MUST guide the planning:

1. **I. Immutable Audit Trail (NON-NEGOTIABLE)**: All case actions, decisions, and state transitions MUST be recorded immutably with full attribution and timestamp. 7-year retention.

2. **II. Role-Based Access Control with Segregation of Duties (NON-NEGOTIABLE)**: Four roles enforced (L1, L2, AML Manager, Read-Only). L1 cannot approve SMRs. L2 cannot approve own recommendations.

3. **III. Test-First Development**: 80% coverage minimum, 100% on critical paths (SMR generation, sanctions blocking).

4. **IV. Explicit Error Handling and Recovery**: Timeout, retry, circuit breaker patterns for external services. No silent failures.

5. **V. SLA Tracking and Enforcement**: Business day calculations, automatic escalation on breach.

6. **VI. Sensitive Data Protection**: TLS 1.2+, AES-256 at rest, no PII in logs.

7. **VII. External Integration Resilience**: 30s timeouts, retry with backoff, circuit breaker (5 failures to open).

## Tech Stack (from Specify Context)

| Aspect | Value |
|--------|-------|
| Language | Python 3.12 |
| Framework | FastAPI |
| Database | PostgreSQL 15 |
| Task Queue | Celery + Redis |

## Codebase Context

Greenfield project - no existing codebase to analyze.

## Supervisor Instructions

**Phase**: Contracts Review (Iteration 2)

Review the REVISED API contracts and verify all gaps from Iteration 1 have been addressed.

**Read**:
- Spec: `/Users/sean/specs/001-aml-case-management/spec.md`
- Research: `/Users/sean/specs/001-aml-case-management/research.md`
- Data Model: `/Users/sean/specs/001-aml-case-management/data-model.md`
- Revised contracts: `/Users/sean/specs/001-aml-case-management/contracts/api.yaml`
- Revised quickstart: `/Users/sean/specs/001-aml-case-management/quickstart.md`
- Planner report: `/Users/sean/specs/001-aml-case-management/.workflow/planner-report.md`
- Previous gaps from Clarification Log below

**Write**:
- Report: `/Users/sean/specs/001-aml-case-management/.workflow/advocate-report.md`

**Use Skills**:
- `validation-plan-artifacts` (phase: contracts)

**Report format**: Follow `/Users/sean/.claude/plugins/cache/humaninloop-plugins/humaninloop/0.7.4/templates/advocate-report-template.md`

**Verify**:
- G1 (SLA config) resolved by /config/sla-warning-threshold endpoint
- G2 (tier check) resolved by TIER_MISMATCH error response
- G3 (customer sync) resolved by customer snapshot immutability documentation
- G4 (Indue webhook) resolved by customerOnboardingStatus field
- Identify any remaining or new gaps

## Clarification Log

### Phase: Research - Iteration 1

#### Gaps Identified (from Devil's Advocate)

| ID | Severity | Description |
|----|----------|-------------|
| G1 | Critical | No decision for PII handling in audit log payloads |
| G2 | Important | No decision for case queue assignment algorithm |
| G3 | Critical | No decision for webhook authentication/validation |
| G4 | Important | SMR document format research deferred without concrete plan |
| G5 | Important | No decision for dashboard real-time update mechanism |
| G6 | Important | Duplicate webhook handling not covered in integration decision |
| G7 | Important | No decision for SLA calculation start point |
| G10 | Important | No decision for customer data synchronization |

#### User Answers

| Gap ID | Question | User Answer |
|--------|----------|-------------|
| G3 | How should webhooks be authenticated? | HMAC signature validation |
| G1 | What is the PII redaction strategy for audit logs? | Structured payload with PII field list - define explicit PII fields; service layer redacts before audit write |
| G7 | When does SLA clock start? | Case creation timestamp |
| G2 | How are cases assigned to analysts? | Manual claim from queue - cases enter unassigned queue; analysts self-select |
| G5 | How does dashboard receive updates? | Polling (30-second interval) |

### Phase: Data Model - Iteration 1

#### Gaps Identified (from Devil's Advocate)

| ID | Severity | Description |
|----|----------|-------------|
| G1 | Critical | State machine missing direct OPEN to CLOSED transition for false positive closures |
| G2 | Important | No mechanism for tracking L1 closures flagged for L2 quality review |
| G3 | Important | Case entity missing closedAt timestamp for resolution time metrics |
| G4 | Important | No model for investigation findings before SMR recommendation |
| G5 | Important | User role change cascade to Assignment not explicitly documented |

#### User Answers

| Gap ID | Question | User Answer |
|--------|----------|-------------|
| G1 | Should claiming be implicit or explicit two-step? | Implicit claim - single operation; closing a case automatically claims it if unassigned |
| G2 | How should L1 closures be flagged for L2 review? | Status enum: NOT_REQUIRED, PENDING_REVIEW, REVIEWED_ACCEPTED, REVIEWED_REOPENED |
| G4 | Where should investigation findings be stored? | Separate InvestigationFindings entity with structured fields |

### Phase: Contracts - Iteration 1

#### Gaps Identified (from Devil's Advocate)

| ID | Severity | Description |
|----|----------|-------------|
| G1 | Important | No SLA warning threshold configuration endpoint |
| G2 | Important | Tier validation on close unclear - no TIER_MISMATCH error |
| G3 | Important | No customer data sync mechanism defined |
| G4 | Minor | Indue webhook missing customerOnboardingStatus field |

#### User Answers

| Gap ID | Question | User Answer |
|--------|----------|-------------|
| G1 | Should we add SLA warning threshold config endpoint? | Yes, add /config/sla-warning-threshold endpoint |
| G2 | How to handle L1 closing L2-tier cases? | Explicit TIER_MISMATCH error (403) when L1 tries to close L2 case |
| G3 | How should customer data sync work? | Document immutability - customer snapshot at case creation; changes don't affect existing cases |
