# Implementation Plan: 001-aml-case-management

> Summary document for the planning workflow.
> Generated: 2026-01-15

---

## Overview

The AML Case Management System enables Spriggy to meet AUSTRAC AML/CTF compliance obligations by providing a unified platform for managing three core workstreams: KYC remediation, PEP/Sanctions screening disposition, and suspicious activity investigation. The system enforces a tiered analyst workflow (L1 Triage, L2 Investigation, AML Compliance Manager approval) with strict segregation of duties, immutable audit trails, and SLA tracking.

---

## Key Decisions

| ID | Decision | Choice | See |
|----|----------|--------|-----|
| D1 | Audit Trail Architecture | Append-only log with event sourcing for state transitions | research.md |
| D2 | SLA Calculation Engine | Python `holidays` library + configurable calendar; SLA starts at case creation | research.md |
| D3 | External Integration Pattern | Async queue with circuit breaker + DLQ + duplicate detection | research.md |
| D4 | Document Storage | PostgreSQL BYTEA for structured data + S3-compatible for attachments | research.md |
| D5 | Authentication Architecture | OIDC SSO integration + local RBAC enforcement | research.md |
| D6 | Notification System | Celery async tasks + email provider; 30s polling for dashboard | research.md |
| D7 | Reporting Data Access | Read replicas with materialized views for MI dashboards | research.md |
| D8 | Concurrency Control | Optimistic locking with version column | research.md |
| D9 | Case Reference Generation | PostgreSQL SEQUENCE with AML-NNNN prefix | research.md |
| D10 | Communication Template Storage | Version-controlled code repository with database cache | research.md |
| D11 | Webhook Authentication | HMAC signature validation for GreenID/Indue webhooks | research.md |
| D12 | PII Redaction Strategy | Structured payload with explicit PII field list; service-layer redaction | research.md |
| D13 | Case Queue Assignment | Manual claim from unassigned queue; analysts self-select | research.md |

---

## Entities

| Entity | Status | Key Attributes | Relationships |
|--------|--------|----------------|---------------|
| Case | NEW | referenceCode, caseType, status, tier, slaDeadline, l2ReviewStatus | Customer, User, TimelineEntry, SMRRecommendation |
| Customer | NEW | customerId, name, accountStatus, onboardingStatus | Cases, OnboardingBlocks |
| User | NEW | email, role (L1/L2/Manager/ReadOnly), isActive | Assignments, TimelineEntries |
| Assignment | NEW | assignedAt, unassignedAt, assignmentReason | Case, User |
| TimelineEntry | NEW | entryType, content, actingUserId (immutable) | Case |
| InvestigationFindings | NEW | entitiesInvolved, transactionPatterns, suspiciousIndicators, conclusion | Case |
| SMRRecommendation | NEW | narrative, reasonForSuspicion, status, austrackReferenceNumber | Case, User (recommender/approver) |
| CommunicationTemplate | NEW | templateName, content, applicableCaseTypes | CustomerCommunications |
| CustomerCommunication | NEW | direction, channel, content, analystAssessment | Case, Template |
| OnboardingBlock | NEW | blockType, syncStatus, clearedAt | Customer, Case |
| EDDChecklist | NEW | sourceOfWealth, sourceOfFunds, relationshipPurpose, monitoringFrequency | Case |
| CaseLink | NEW | linkType, sourceCaseId, targetCaseId | Cases (supplementary SMR) |
| Document | NEW | filename, contentType, storageLocation | Case |
| SMRDraft | NEW | draftContent, generatedAt | SMRRecommendation |
| AuditLog | NEW | actionType, actionDetail, userId (immutable) | Case, User |
| Notification | NEW | notificationType, message, isRead | User |
| HolidayOverride | NEW | holidayDate, description | - |
| WebhookReceipt | NEW | payloadHash, receivedAt (duplicate detection) | - |
| PEPThresholdConfig | NEW | thresholdPercentage, effectiveFrom | - |

---

## Endpoints

| Category | Count | Key Endpoints |
|----------|-------|---------------|
| Webhooks | 2 | POST /webhooks/greenid, POST /webhooks/indue |
| Case Management | 11 | GET/claim/close/escalate/reopen cases |
| Queue Management | 3 | L2 quality review queue, unassigned queue |
| SMR Workflow | 7 | Recommend, approve, reject, resubmit, record reference |
| EDD/Onboarding | 4 | EDD checklist, onboarding block management |
| Dashboard | 3 | My cases, metrics, queue metrics |
| Notifications | 4 | List, count, mark read |
| Reports | 5 | Volumes, SLA, SMR, aged cases, export |
| Configuration | 4 | PEP threshold, SLA threshold, holidays |
| Users | 3 | Profile, list, role update |
| **Total** | **55** | - |

---

## Artifacts

| Artifact | Path | Status |
|----------|------|--------|
| Specification | specs/001-aml-case-management/spec.md | Complete |
| Research | specs/001-aml-case-management/research.md | Complete |
| Data Model | specs/001-aml-case-management/data-model.md | Complete |
| API Contracts | specs/001-aml-case-management/contracts/api.yaml | Complete |
| Quickstart | specs/001-aml-case-management/quickstart.md | Complete |

---

## Constitution Alignment

| Principle | Implementation |
|-----------|----------------|
| I. Immutable Audit Trail (NON-NEGOTIABLE) | AuditLog + TimelineEntry with no UPDATE/DELETE; 7-year retention |
| II. RBAC with Segregation (NON-NEGOTIABLE) | 4-tier roles; L1 cannot approve SMRs; L2 cannot approve own recommendations |
| III. Test-First Development | 80% coverage minimum; 100% on SMR generation, sanctions blocking |
| IV. Explicit Error Handling | Circuit breaker (5 failures), retry with backoff, DLQ |
| V. SLA Tracking | Business day calculation with AU holidays; auto-escalation on breach |
| VI. Sensitive Data Protection | PII field registry; service-layer redaction; HMAC webhook auth |
| VII. External Integration Resilience | 30s timeouts; retry with exponential backoff |

---

## Known Limitations

| Issue | Mitigation |
|-------|------------|
| OQ-004: AUSTRAC SMR format | Research during implementation; store as PDF |
| OQ-006: Customer data availability | Snapshot at case creation; immutable during case lifecycle |
| OQ-007: Spriggy onboarding API contract | Define with Spriggy engineering |

---

## Next Steps

Run `/humaninloop:tasks` to generate implementation tasks from this plan.
