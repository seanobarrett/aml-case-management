---
type: specification-request
status: completed
iteration: 3
feature_id: 001-aml-case-management
created: 2026-01-13T08:25:00Z
updated: 2026-01-13T09:15:00Z
---

# Specification Request

## User Input

AML Case Management System for Spriggy AUSTRAC compliance program.

### Detailed Requirements from Brainstorming Session

**Business Context:**
- Company: Spriggy (Australian fintech, family/youth financial products - prepaid cards)
- Regulatory Driver: AUSTRAC AML/CTF regulation changes bringing Spriggy into reporting entity scope
- Deadline: 31 March 2026
- Approach: Brownfield build extending existing systems

**System Scope - Three Workstreams:**

1. **KYC Management**: Customer identification issues, verification failures, document remediation
2. **PEP/Sanctions Screening**: Disposition of screening hits, false positive management, enhanced due diligence
3. **Suspicious Activity**: Transaction monitoring alerts from Indue, investigation, SMR determination

**Integration Points:**
- GreenID: KYC verification + PEP/sanctions screening (existing)
- Indue: Transaction monitoring alerts (existing banking partner)
- AUSTRAC: SMR reporting (system-generated drafts, manual submission initially)

**Workflow Model - Tiered Structure:**
- L1 Triage: Close false positives, request customer info, close if explanation satisfactory, escalate if suspicious
- L2 Investigation: Full investigation, customer contact if needed, SMR recommendation
- AML Compliance Manager: Approve/reject SMRs, audit L1/L2 decisions
- Governance: Reporting to Risk Meetings → Compliance & Risk Committee → Board

**L1 Authority:**
- CAN: Close false positives, request info from customers, close with satisfactory explanation, escalate
- CANNOT: File/recommend SMRs, close without documentation, override sanctions blocks
- Required: Scripted customer contact templates, mandatory documentation, clear escalation triggers

**PEP/Sanctions Handling:**
- Sanctions: Block onboarding until cleared by analyst
- PEP (high confidence): Block onboarding, review and apply EDD before proceeding
- PEP (low confidence): Provisional proceed, case created for parallel review

**SMR Filing Process:**
1. L2 completes investigation, documents findings
2. L2 creates SMR recommendation with narrative
3. AML Compliance Manager reviews and approves/rejects
4. System generates SMR-formatted draft document
5. Manual submission via AUSTRAC Online
6. AUSTRAC reference number recorded in system

**Ongoing Screening:**
- OPEN ITEM: Confirm GreenID ongoing monitoring capability
- If unavailable: Implement batch rescreening or evaluate alternatives

**Customer Communication:**
- Use existing channels (email, in-app, phone)
- Document in case: what requested, when, response, assessment
- Mandatory documentation before L1 can close

**Notification Requirements:**
- Day 1: In-system dashboards, email notifications for assignments/SLA warnings/escalations
- Phase 2: Slack alerts for critical items

**Access Control (4 roles):**
- L1 Analyst: View assigned, triage, document, close false positives, request info, escalate
- L2 Analyst: All L1 + full investigation, SMR recommendation, review L1 decisions
- AML Compliance Manager: All + approve SMRs, override, system config, user management
- Read-only (Audit/Governance): View all cases/reports, no edit, export for committee

**Reporting/MI (Day 1):**
- Operational: Case volumes by type, open count/aging, SLA compliance, closure rates
- Risk: SMR filing volumes, screening hit rates, false positive rates, cases by risk category

**Record Retention:**
- 7 years minimum (AUSTRAC requirement)
- All data in system (single authoritative source)
- Immutable audit trail, no deletion
- Every action timestamped with user attribution

**SLA Timelines:**
- KYC remediation: 5 business days
- PEP/Sanctions triage: 24 hours
- Suspicious activity triage: 48 hours
- SMR filing: 3 business days from approval
- Business days use Australian national holidays

**Automation Phasing:**
- Day 1 (March 31): Core workflow, SLA tracking, email notifications, basic reporting, SMR draft generation
- Phase 2: Automated prioritization, Slack integration, enhanced MI, AUSTRAC API integration

**Out of Scope:**
- TTRs (not applicable to Spriggy products)
- IFTIs (not applicable)
- Transaction monitoring engine (Indue handles this)
- Identity verification (GreenID handles this)
- Direct AUSTRAC API (Phase 2)

## Project Context

| Aspect | Value |
|--------|-------|
| Project Name | Spriggy AML Case Management System |
| Tech Stack | Python 3.12, FastAPI, PostgreSQL 15, Celery + Redis |
| Constitution | .humaninloop/memory/constitution.md |

## Constitution Principles

The following principles from the constitution MUST guide the specification:

1. **I. Immutable Audit Trail (NON-NEGOTIABLE)**: All case actions, decisions, and state transitions MUST be recorded immutably with full attribution and timestamp. 7-year retention.

2. **II. Role-Based Access Control with Segregation of Duties (NON-NEGOTIABLE)**: Four roles enforced (L1, L2, AML Manager, Read-Only). L1 cannot approve SMRs. L2 cannot approve own recommendations.

3. **III. Test-First Development**: 80% coverage minimum, 100% on critical paths (SMR generation, sanctions blocking).

4. **IV. Explicit Error Handling and Recovery**: Timeout, retry, circuit breaker patterns for external services. No silent failures.

5. **V. SLA Tracking and Enforcement**: Business day calculations, automatic escalation on breach.

6. **VI. Sensitive Data Protection**: TLS 1.2+, AES-256 at rest, no PII in logs.

7. **VII. External Integration Resilience**: 30s timeouts, retry with backoff, circuit breaker (5 failures to open).

## File Paths

| File | Path |
|------|------|
| Spec | specs/001-aml-case-management/spec.md |
| Context | specs/001-aml-case-management/.workflow/context.md |
| Analyst Report | specs/001-aml-case-management/.workflow/analyst-report.md |
| Advocate Report | specs/001-aml-case-management/.workflow/advocate-report.md |

## Supervisor Instructions

Review the REVISED specification (Iteration 3) and verify all gaps have been addressed.

**Read**:
- Spec: `specs/001-aml-case-management/spec.md`
- Analyst report: `specs/001-aml-case-management/.workflow/analyst-report.md`
- Previous gaps from Clarification Log below (Iteration 1 and 2)

**Write**:
- Report: `specs/001-aml-case-management/.workflow/advocate-report.md`

**Report format**: Follow `/Users/sean/.claude/plugins/cache/humaninloop-plugins/humaninloop/0.7.4/templates/advocate-report-template.md`

**Focus**: Verify all 4 Important gaps from Iteration 2 have been adequately addressed. Identify any remaining or new gaps.

## Clarification Log

### Iteration 1

#### Gaps Identified (from Devil's Advocate)

| ID | Severity | Description |
|----|----------|-------------|
| G1 | Critical | No specification for PEP confidence level classification |
| G2 | Critical | No maximum case age or dormancy rules |
| G11 | Critical | No specification for onboarding block integration |
| G3 | Important | No handling for multiple SMR rejections |
| G4 | Important | Template management undefined |
| G7 | Important | Case priority within same SLA undefined |
| G9 | Important | EDD documentation requirements undefined |
| G12 | Important | No manual case creation specified |
| G13 | Important | No handling for simultaneous sanctions + PEP hits |
| G16 | Important | "Satisfactory explanation" undefined for L1 closure |
| G17 | Important | No audit trail for READ operations |
| G19 | Important | No handling for role changes mid-case |
| G20 | Important | No SMR withdrawal after approval |

#### User Answers

| Gap ID | Question | User Answer |
|--------|----------|-------------|
| G1 | How are PEP confidence levels determined? | GreenID provides numeric confidence score; system applies configurable threshold (e.g., >80% = high confidence) |
| G2 | What is the maximum age for unresolved cases? | No maximum age; rely on reporting to surface aged cases for management attention |
| G11 | How does onboarding block integrate with Spriggy? | API callback - this system notifies Spriggy's onboarding service via API when block is applied/cleared |
| G9 | What constitutes acceptable EDD documentation? | Structured checklist with mandatory fields: source of wealth, source of funds, relationship purpose, enhanced monitoring frequency |
| G4 | Who approves communication templates? | Static templates at launch; changed only through code deployments with AML Compliance Manager review |
| G7 | How to prioritize cases with equal SLA urgency? | Creation date (FIFO) - oldest cases first within same urgency level |
| G12 | Can analysts create cases manually? | No manual creation; all cases must originate from system integrations (GreenID/Indue) |
| G13 | What happens with simultaneous sanctions AND PEP hits? | Sanctions takes precedence - create single Sanctions case; PEP details captured but sanctions workflow applies |
| G16 | What defines "satisfactory explanation" for L1 closure? | Analyst judgment with documentation; must document why explanation was satisfactory; subject to L2 review |
| G17 | Should read access be logged in audit trail? | Log all reads - every case view recorded with user and timestamp |
| G19 | What happens to cases when analyst changes roles? | Reassign all cases - all cases returned to queue for reassignment when role changes |
| G20 | Can approved SMR be withdrawn before AUSTRAC submission? | Cannot withdraw - once approved, SMR must be filed; new information goes into supplementary filing |
| G3 | What happens when SMR rejected multiple times? | No limit - L2 can resubmit indefinitely; resolution through discussion outside system |

### Iteration 2

#### Gaps Identified (from Devil's Advocate)

| ID | Severity | Description |
|----|----------|-------------|
| G21 | Important | No specification for L2 quality review disagreement workflow |
| G22 | Important | No handling for post-onboarding sanctions hits on existing customers |
| G27 | Important | A9 assumes GreenID ongoing monitoring but marked as open item |
| G28 | Important | No workflow for supplementary SMR filings |

#### User Answers

| Gap ID | Question | User Answer |
|--------|----------|-------------|
| G21 | What happens when L2 disagrees with L1 closure? | L2 reopens to own queue - L2 takes over the case for investigation (L1 closure overturned) |
| G22 | What happens if existing customer triggers sanctions alert? | Case only, no automatic block - analyst decides on account restrictions |
| G28 | What is workflow for supplementary SMR filing? | New linked case - create new case linked to original with full workflow (L2 recommend, Manager approve) |
| G27 | Should ongoing monitoring handle GreenID unavailable scenario? | Confirm with GreenID - validate capability exists; if not, add batch rescreening to scope |
