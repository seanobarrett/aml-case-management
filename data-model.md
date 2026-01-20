# Data Model: 001-aml-case-management

> AML Case Management System - Entity Definitions and Relationships
> Generated: 2026-01-16
> Phase: Data Model (Iteration 2)

---

## Summary

| Entity | Attributes | Relationships | Status | PII Fields |
|--------|------------|---------------|--------|------------|
| Case | 22 | 10 | [NEW] | None |
| Customer | 9 | 2 | [NEW] | 4 |
| User | 11 | 3 | [NEW] | 1 |
| Assignment | 8 | 3 | [NEW] | None |
| TimelineEntry | 10 | 2 | [NEW] | None |
| InvestigationFindings | 10 | 2 | [NEW] | None |
| SMRRecommendation | 15 | 4 | [NEW] | None |
| CommunicationTemplate | 10 | 1 | [NEW] | None |
| CustomerCommunication | 11 | 3 | [NEW] | 2 |
| OnboardingBlock | 10 | 3 | [NEW] | None |
| EDDChecklist | 10 | 2 | [NEW] | 2 |
| CaseLink | 7 | 3 | [NEW] | None |
| PEPThresholdConfig | 6 | 1 | [NEW] | None |
| Document | 13 | 2 | [NEW] | None |
| SMRDraft | 8 | 3 | [NEW] | None |
| AuditLog | 10 | 2 | [NEW] | None |
| Notification | 11 | 2 | [NEW] | None |
| HolidayOverride | 6 | 1 | [NEW] | None |
| WebhookReceipt | 6 | 1 | [NEW] | None |

---

## Entity: Case [NEW]

> The central work item representing an investigation or remediation task requiring analyst action.
> Sources: FR-001 through FR-007, FR-024, FR-025, US-1 through US-18

### Attributes

| Attribute | Type | Required | Default | Validation | Description |
|-----------|------|----------|---------|------------|-------------|
| id | UUID | Yes | auto-generated | - | Primary key |
| referenceNumber | Integer | Yes | sequence | Unique | Sequential reference (from case_ref_seq) |
| referenceCode | Text(20) | Yes | computed | Unique, Pattern: ^AML-[0-9]+$ | Formatted reference (AML-1000) |
| caseType | Enum | Yes | - | OneOf: [KYC_REMEDIATION, PEP_SANCTIONS_SCREENING, SUSPICIOUS_ACTIVITY, SUPPLEMENTARY_SMR] | Primary case classification (FR-004) |
| caseSubtype | Enum | No | null | OneOf: [SANCTIONS_ONBOARDING, SANCTIONS_EXISTING_CUSTOMER, PEP_EDD_REQUIRED, PEP_PROVISIONAL_REVIEW] | Secondary classification |
| status | Enum | Yes | OPEN | See State Machine | Current case status (FR-005) |
| tier | Enum | Yes | L1 | OneOf: [L1, L2] | Assigned analyst tier |
| priority | Integer | Yes | 0 | Range: 0-100 | Computed priority score |
| slaDeadline | Timestamp | Yes | computed | - | SLA expiration (FR-049) |
| slaBreached | Boolean | Yes | false | - | Whether SLA has been breached |
| source | Enum | Yes | - | OneOf: [GREENID, INDUE] | Alert source system (FR-002) |
| sourceAlertId | Text(100) | No | null | - | External alert identifier |
| pepConfidenceScore | Decimal(5,2) | No | null | Range: 0-100 | GreenID confidence score (FR-030) |
| hasCombinedAlert | Boolean | Yes | false | - | Sanctions + PEP combined (FR-035) |
| customerId | Reference(Customer) | Yes | - | FK | Customer under investigation |
| assignedUserId | Reference(User) | No | null | FK | Currently assigned analyst |
| assignedAt | Timestamp | No | null | - | When current assignment began |
| closedAt | Timestamp | No | null | - | When case was closed (G3 - resolution time tracking) |
| l2ReviewStatus | Enum | Yes | NOT_REQUIRED | OneOf: [NOT_REQUIRED, PENDING_REVIEW, REVIEWED_ACCEPTED, REVIEWED_REOPENED] | L2 quality review status (G2 - FR-012, FR-018) |
| version | Integer | Yes | 1 | Min: 1 | Optimistic lock version (D8) |
| createdAt | Timestamp | Yes | auto | - | Case creation time (SLA start - D2) |
| updatedAt | Timestamp | Yes | auto | - | Last modification time |

### Relationships

| Relationship | Type | Target | FK Location | On Delete | Description |
|--------------|------|--------|-------------|-----------|-------------|
| customer | N:1 | Customer | Case.customerId | Restrict | Customer under investigation |
| assignedUser | N:1 | User | Case.assignedUserId | Set Null | Currently assigned analyst |
| assignments | 1:N | Assignment | Assignment.caseId | Cascade | Assignment history |
| timelineEntries | 1:N | TimelineEntry | TimelineEntry.caseId | Cascade | Immutable action log |
| smrRecommendation | 1:1 | SMRRecommendation | SMRRecommendation.caseId | Cascade | SMR recommendation if applicable |
| communications | 1:N | CustomerCommunication | CustomerCommunication.caseId | Cascade | Customer outreach records |
| onboardingBlock | 1:1 | OnboardingBlock | OnboardingBlock.caseId | Cascade | Blocking status if applicable |
| eddChecklist | 1:1 | EDDChecklist | EDDChecklist.caseId | Cascade | EDD documentation if applicable |
| investigationFindings | 1:1 | InvestigationFindings | InvestigationFindings.caseId | Cascade | Structured investigation documentation (G4 - US-4) |
| documents | 1:N | Document | Document.caseId | Cascade | Attached evidence files |
| linkedCases | N:M | Case | CaseLink | Cascade | Supplementary SMR relationships (FR-044) |

### Constraints

| Constraint | Type | Fields | Rule |
|------------|------|--------|------|
| uk_reference_number | Unique | referenceNumber | - |
| uk_reference_code | Unique | referenceCode | - |
| chk_pep_score_range | Check | pepConfidenceScore | pepConfidenceScore IS NULL OR (pepConfidenceScore >= 0 AND pepConfidenceScore <= 100) |
| chk_assignment_consistency | Check | assignedUserId, assignedAt | (assignedUserId IS NULL AND assignedAt IS NULL) OR (assignedUserId IS NOT NULL AND assignedAt IS NOT NULL) |
| chk_closed_timestamp | Check | status, closedAt | (status IN ('CLOSED', 'SMR_FILED') AND closedAt IS NOT NULL) OR (status NOT IN ('CLOSED', 'SMR_FILED') AND closedAt IS NULL) |
| idx_l2_review_pending | Index | l2ReviewStatus | For L2 quality review queue retrieval |

### Business Rules

| Rule ID | Condition | Error Message | Source |
|---------|-----------|---------------|--------|
| BR-CASE-001 | Source must be GREENID or INDUE | Manual case creation not permitted | FR-002 |
| BR-CASE-002 | Combined alert only when caseType = PEP_SANCTIONS_SCREENING | Combined alert flag invalid for this case type | FR-035 |
| BR-CASE-003 | caseSubtype required when caseType = PEP_SANCTIONS_SCREENING | Subtype required for screening cases | FR-037 |
| BR-CASE-004 | l2ReviewStatus = PENDING_REVIEW only when L1 closes with satisfactory explanation | L2 review only applies to L1 satisfactory explanation closures | FR-012 |
| BR-CASE-005 | closedAt must be set when status transitions to CLOSED or SMR_FILED | Closed timestamp required for resolution tracking | FR-070 |

---

## Entity: Customer [NEW]

> The Spriggy customer who is the subject of a case.
> Sources: Key Entities - Customer

### Attributes

| Attribute | Type | Required | Default | Validation | Description |
|-----------|------|----------|---------|------------|-------------|
| id | UUID | Yes | auto-generated | - | Primary key |
| externalId | Text(100) | Yes | - | Unique | Spriggy customer identifier |
| firstName | Text(100) | No | null | - | **PII** Customer first name |
| lastName | Text(100) | No | null | - | **PII** Customer last name |
| email | Email | No | null | Format: email | **PII** Customer email |
| phone | Text(20) | No | null | - | **PII** Customer phone |
| accountStatus | Enum | Yes | ACTIVE | OneOf: [ACTIVE, SUSPENDED, CLOSED] | Current account status (EC-008) |
| onboardingStatus | Enum | Yes | UNKNOWN | OneOf: [IN_PROGRESS, COMPLETED, BLOCKED, UNKNOWN] | Onboarding state |
| riskClassification | Enum | No | null | OneOf: [LOW, MEDIUM, HIGH, UNCLASSIFIED] | Risk rating |
| createdAt | Timestamp | Yes | auto | - | Record creation time |
| updatedAt | Timestamp | Yes | auto | - | Last modification time |

### Relationships

| Relationship | Type | Target | FK Location | On Delete | Description |
|--------------|------|--------|-------------|-----------|-------------|
| cases | 1:N | Case | Case.customerId | Restrict | Associated investigations |
| onboardingBlocks | 1:N | OnboardingBlock | OnboardingBlock.customerId | Cascade | Active/historical blocks |

### Constraints

| Constraint | Type | Fields | Rule |
|------------|------|--------|------|
| uk_external_id | Unique | externalId | - |

### PII Field Registry

Per D12 (PII Redaction Strategy), the following fields are marked as PII and will be redacted from audit log payloads:
- `firstName`
- `lastName`
- `email`
- `phone`

---

## Entity: User [NEW]

> A system user who can access cases and perform actions based on their role.
> Sources: Key Entities - User, FR-063, FR-065, Principle II

### Attributes

| Attribute | Type | Required | Default | Validation | Description |
|-----------|------|----------|---------|------------|-------------|
| id | UUID | Yes | auto-generated | - | Primary key |
| externalId | Text(255) | Yes | - | Unique | SSO subject identifier (D5) |
| email | Email | Yes | - | Unique, Format: email | **PII** User email from SSO |
| displayName | Text(100) | No | null | - | Display name |
| role | Enum | Yes | READ_ONLY | OneOf: [L1_ANALYST, L2_ANALYST, AML_MANAGER, READ_ONLY] | System role (FR-063) |
| isActive | Boolean | Yes | true | - | Can access system |
| lastLoginAt | Timestamp | No | null | - | Most recent login |
| roleChangedAt | Timestamp | No | null | - | When role was last changed |
| roleChangedBy | Reference(User) | No | null | FK | Who changed the role |
| createdAt | Timestamp | Yes | auto | - | First login / provisioning time |
| updatedAt | Timestamp | Yes | auto | - | Last modification time |

### Relationships

| Relationship | Type | Target | FK Location | On Delete | Description |
|--------------|------|--------|-------------|-----------|-------------|
| assignments | 1:N | Assignment | Assignment.userId | Set Null | Cases assigned to this user |
| timelineEntries | 1:N | TimelineEntry | TimelineEntry.userId | Set Null | Actions performed by this user |
| roleChangedByUser | N:1 | User | User.roleChangedBy | Set Null | User who last changed this user's role |

### Constraints

| Constraint | Type | Fields | Rule |
|------------|------|--------|------|
| uk_external_id | Unique | externalId | - |
| uk_email | Unique | email | - |

### Business Rules

| Rule ID | Condition | Error Message | Source |
|---------|-----------|---------------|--------|
| BR-USER-001 | L1_ANALYST cannot create SMR recommendations | L1 analysts cannot create SMR recommendations | FR-014 |
| BR-USER-002 | Cannot approve own SMR recommendation (check original recommender) | Cannot approve your own SMR recommendation | FR-020, EC-003, Principle II |
| BR-USER-003 | READ_ONLY cannot modify any case data | Read-only users cannot modify cases | FR-064 |
| BR-USER-004 | When User.role changes, all Cases where Case.assignedUserId = User.id MUST have: (1) Current Assignment.unassignedAt set to now, (2) New Assignment created with reason = ROLE_CHANGE, previousUserId = User.id, (3) Case.assignedUserId set to null, Case.assignedAt set to null, (4) TimelineEntry created recording role change reassignment, (5) AuditLog entry created for each case | Cases must be unassigned when analyst role changes | FR-026, FR-027, G5 |

---

## Entity: Assignment [NEW]

> Tracks which analyst is responsible for a case at any point in time.
> Sources: Key Entities - Assignment, FR-026, FR-027

### Attributes

| Attribute | Type | Required | Default | Validation | Description |
|-----------|------|----------|---------|------------|-------------|
| id | UUID | Yes | auto-generated | - | Primary key |
| caseId | Reference(Case) | Yes | - | FK | Case being assigned |
| userId | Reference(User) | Yes | - | FK | Assigned analyst |
| assignmentReason | Enum | Yes | - | OneOf: [INITIAL, ESCALATION, REASSIGNMENT, ROLE_CHANGE, L2_REOPEN, MANUAL_CLAIM] | Why assignment occurred |
| previousUserId | Reference(User) | No | null | FK | Previously assigned analyst |
| notes | Text | No | null | - | Additional context |
| assignedAt | Timestamp | Yes | auto | - | When assignment occurred |
| unassignedAt | Timestamp | No | null | - | When assignment ended |
| createdAt | Timestamp | Yes | auto | - | Record creation time |

### Relationships

| Relationship | Type | Target | FK Location | On Delete | Description |
|--------------|------|--------|-------------|-----------|-------------|
| case | N:1 | Case | Assignment.caseId | Cascade | Assigned case |
| user | N:1 | User | Assignment.userId | Set Null | Assigned analyst |
| previousUser | N:1 | User | Assignment.previousUserId | Set Null | Previously assigned analyst |

### Constraints

| Constraint | Type | Fields | Rule |
|------------|------|--------|------|
| idx_case_active | Index | caseId, unassignedAt | For finding current assignment |

---

## Entity: TimelineEntry [NEW]

> An immutable record of an action, event, or note on a case.
> Sources: Key Entities - Timeline Entry, FR-058, FR-059, FR-061, Principle I

### Attributes

| Attribute | Type | Required | Default | Validation | Description |
|-----------|------|----------|---------|------------|-------------|
| id | UUID | Yes | auto-generated | - | Primary key |
| caseId | Reference(Case) | Yes | - | FK | Associated case |
| userId | Reference(User) | No | null | FK | Acting user (null for system events) |
| entryType | Enum | Yes | - | OneOf: [ACTION, NOTE, SYSTEM_EVENT, COMMUNICATION, VIEW, CLOSURE, REOPEN, ESCALATION, SLA_WARNING, SLA_BREACH] | Type of timeline entry |
| action | Text(100) | Yes | - | - | Specific action code |
| summary | Text(500) | Yes | - | - | Human-readable summary |
| details | JSON | No | null | - | Structured details (PII redacted per D12) |
| ipAddress | Text(45) | No | null | - | Client IP (IPv6 compatible) |
| userAgent | Text(255) | No | null | - | Client user agent |
| createdAt | Timestamp | Yes | auto | - | Entry timestamp |

### Relationships

| Relationship | Type | Target | FK Location | On Delete | Description |
|--------------|------|--------|-------------|-----------|-------------|
| case | N:1 | Case | TimelineEntry.caseId | Cascade | Associated case |
| user | N:1 | User | TimelineEntry.userId | Set Null | Acting user |

### Constraints

| Constraint | Type | Fields | Rule |
|------------|------|--------|------|
| idx_case_created | Index | caseId, createdAt | For timeline ordering |

### Immutability Rules (Principle I)

- **No UPDATE operations permitted** on this entity
- **No DELETE operations permitted** on this entity
- Application must enforce through service layer
- Database trigger recommended as additional safeguard

---

## Entity: InvestigationFindings [NEW]

> Structured documentation of investigation findings before SMR recommendation decision.
> Sources: US-4 scenario 1, G4 (Advocate Report - Iteration 1)

### Attributes

| Attribute | Type | Required | Default | Validation | Description |
|-----------|------|----------|---------|------------|-------------|
| id | UUID | Yes | auto-generated | - | Primary key |
| caseId | Reference(Case) | Yes | - | FK, Unique | Associated case (one per case) |
| entitiesInvolved | JSON | Yes | [] | - | List of entities identified (persons, businesses, accounts) |
| transactionPatterns | JSON | Yes | [] | - | Identified transaction patterns and anomalies |
| suspiciousIndicators | JSON | Yes | [] | - | List of suspicious activity indicators observed |
| conclusion | Enum | Yes | - | OneOf: [NO_SUSPICION, SUSPICIOUS_ACTIVITY_IDENTIFIED, INSUFFICIENT_EVIDENCE, FURTHER_MONITORING_REQUIRED] | Investigation conclusion |
| notes | Text | No | null | - | Additional investigator notes |
| completedByUserId | Reference(User) | Yes | - | FK | Analyst who completed findings |
| completedAt | Timestamp | Yes | auto | - | When findings were documented |
| createdAt | Timestamp | Yes | auto | - | Record creation time |
| updatedAt | Timestamp | Yes | auto | - | Last modification time |

### Relationships

| Relationship | Type | Target | FK Location | On Delete | Description |
|--------------|------|--------|-------------|-----------|-------------|
| case | 1:1 | Case | InvestigationFindings.caseId | Cascade | Associated case |
| completedByUser | N:1 | User | InvestigationFindings.completedByUserId | Restrict | Completing analyst |

### Constraints

| Constraint | Type | Fields | Rule |
|------------|------|--------|------|
| uk_case | Unique | caseId | One findings record per case |

### JSON Schema: entitiesInvolved

```json
{
  "type": "array",
  "items": {
    "type": "object",
    "properties": {
      "entityType": { "enum": ["PERSON", "BUSINESS", "ACCOUNT", "OTHER"] },
      "identifier": { "type": "string" },
      "name": { "type": "string" },
      "role": { "type": "string" },
      "notes": { "type": "string" }
    },
    "required": ["entityType", "name"]
  }
}
```

### JSON Schema: transactionPatterns

```json
{
  "type": "array",
  "items": {
    "type": "object",
    "properties": {
      "patternType": { "type": "string" },
      "description": { "type": "string" },
      "dateRange": {
        "type": "object",
        "properties": {
          "from": { "type": "string", "format": "date" },
          "to": { "type": "string", "format": "date" }
        }
      },
      "totalAmount": { "type": "number" },
      "transactionCount": { "type": "integer" }
    },
    "required": ["patternType", "description"]
  }
}
```

### JSON Schema: suspiciousIndicators

```json
{
  "type": "array",
  "items": {
    "type": "object",
    "properties": {
      "indicatorCode": { "type": "string" },
      "description": { "type": "string" },
      "severity": { "enum": ["LOW", "MEDIUM", "HIGH"] },
      "evidence": { "type": "string" }
    },
    "required": ["indicatorCode", "description", "severity"]
  }
}
```

### Business Rules

| Rule ID | Condition | Error Message | Source |
|---------|-----------|---------------|--------|
| BR-INV-001 | completedByUserId.role must be L2_ANALYST or AML_MANAGER | Only L2+ can complete investigation findings | FR-017 |
| BR-INV-002 | InvestigationFindings must exist before SMRRecommendation can be created for same case | Investigation findings required before SMR recommendation | US-4 |

### Notes

- InvestigationFindings captures the investigation work product independent of SMR decision
- Cases that do not warrant SMR still benefit from documented findings
- If conclusion = SUSPICIOUS_ACTIVITY_IDENTIFIED, L2 analyst should proceed to create SMRRecommendation
- Findings are preserved even if case is later closed without SMR

---

## Entity: SMRRecommendation [NEW]

> A recommendation to file a Suspicious Matter Report, requiring manager approval.
> Sources: Key Entities - SMR Recommendation, FR-039 through FR-043, US-4, US-5, US-11

### Attributes

| Attribute | Type | Required | Default | Validation | Description |
|-----------|------|----------|---------|------------|-------------|
| id | UUID | Yes | auto-generated | - | Primary key |
| caseId | Reference(Case) | Yes | - | FK, Unique | Associated case (one per case) |
| narrative | Text | Yes | - | Min length: 100 | Detailed description (FR-039) |
| reasonForSuspicion | Text | Yes | - | Min length: 50 | Why activity is suspicious |
| evidenceReferences | JSON | Yes | [] | - | References to evidence documents |
| status | Enum | Yes | PENDING | See State Machine | Recommendation status |
| recommendingUserId | Reference(User) | Yes | - | FK | L2 analyst who created |
| rejectionCount | Integer | Yes | 0 | Min: 0 | Number of rejections (EC-010) |
| rejectionHistory | JSON | Yes | [] | - | History of rejections with reasons |
| approvedAt | Timestamp | No | null | - | When approved by manager |
| approvingUserId | Reference(User) | No | null | FK | Manager who approved |
| austracReferenceNumber | Text(50) | No | null | - | AUSTRAC filing reference (FR-041) |
| austracFiledAt | Timestamp | No | null | - | When filed with AUSTRAC |
| isSupplementary | Boolean | Yes | false | - | Whether linked to prior filing |
| createdAt | Timestamp | Yes | auto | - | Creation time |
| updatedAt | Timestamp | Yes | auto | - | Last modification time |

### Relationships

| Relationship | Type | Target | FK Location | On Delete | Description |
|--------------|------|--------|-------------|-----------|-------------|
| case | 1:1 | Case | SMRRecommendation.caseId | Cascade | Associated case |
| recommendingUser | N:1 | User | SMRRecommendation.recommendingUserId | Restrict | L2 analyst |
| approvingUser | N:1 | User | SMRRecommendation.approvingUserId | Restrict | Approving manager |
| smrDraft | 1:1 | SMRDraft | SMRDraft.smrRecommendationId | Cascade | Generated draft document |

### Constraints

| Constraint | Type | Fields | Rule |
|------------|------|--------|------|
| uk_case | Unique | caseId | One recommendation per case |
| chk_approved_fields | Check | status, approvedAt, approvingUserId | If APPROVED: approvedAt and approvingUserId required |
| chk_filed_fields | Check | status, austracReferenceNumber, austracFiledAt | If FILED: reference number and filed timestamp required |

### Business Rules

| Rule ID | Condition | Error Message | Source |
|---------|-----------|---------------|--------|
| BR-SMR-001 | recommendingUserId.role must be L2_ANALYST or AML_MANAGER | Only L2+ can create SMR recommendations | FR-014 |
| BR-SMR-002 | approvingUserId must not equal recommendingUserId | Cannot approve your own SMR recommendation | FR-020, Principle II |
| BR-SMR-003 | approvingUserId.role must be AML_MANAGER | Only AML Manager can approve SMRs | FR-021 |
| BR-SMR-004 | Cannot transition from APPROVED to any state except FILED | Approved SMRs cannot be withdrawn | FR-043 |

---

## Entity: CommunicationTemplate [NEW]

> Pre-approved scripted content for customer outreach.
> Sources: Key Entities - Communication Template, FR-053, FR-054, D10

### Attributes

| Attribute | Type | Required | Default | Validation | Description |
|-----------|------|----------|---------|------------|-------------|
| id | Text(100) | Yes | - | Primary Key, Pattern: ^[a-z0-9_]+$ | Template identifier |
| name | Text(200) | Yes | - | - | Human-readable name |
| version | Text(20) | Yes | - | Pattern: ^[0-9]+\.[0-9]+$ | Template version |
| content | Text | Yes | - | Min length: 50 | Template content with placeholders |
| placeholders | JSON | Yes | [] | - | Placeholder definitions |
| applicableCaseTypes | JSON | Yes | [] | - | Case types this template applies to |
| isActive | Boolean | Yes | true | - | Whether template is available |
| deploymentVersion | Text(50) | No | null | - | Code deployment that added this |
| createdAt | Timestamp | Yes | auto | - | When loaded into database |
| updatedAt | Timestamp | Yes | auto | - | Last cache refresh |

### Relationships

| Relationship | Type | Target | FK Location | On Delete | Description |
|--------------|------|--------|-------------|-----------|-------------|
| communications | 1:N | CustomerCommunication | CustomerCommunication.templateId | Set Null | Communications using this template |

### Constraints

| Constraint | Type | Fields | Rule |
|------------|------|--------|------|
| pk_template | Primary Key | id | - |

### Notes

Per D10 (Communication Template Storage):
- Source of truth is code repository (YAML files)
- Database serves as runtime cache
- Changes require code deployment (FR-054)
- AML Compliance Manager review via PR process

---

## Entity: CustomerCommunication [NEW]

> A record of outreach to or response from a customer.
> Sources: Key Entities - Customer Communication, FR-055, FR-056, FR-057, US-2

### Attributes

| Attribute | Type | Required | Default | Validation | Description |
|-----------|------|----------|---------|------------|-------------|
| id | UUID | Yes | auto-generated | - | Primary key |
| caseId | Reference(Case) | Yes | - | FK | Associated case |
| templateId | Reference(CommunicationTemplate) | No | null | FK | Template used (for outbound) |
| direction | Enum | Yes | - | OneOf: [OUTBOUND, INBOUND] | Communication direction |
| channel | Enum | Yes | - | OneOf: [EMAIL, IN_APP, PHONE, OTHER] | Communication channel |
| content | Text | Yes | - | - | **PII** Message content |
| sentByUserId | Reference(User) | No | null | FK | Analyst who sent (outbound) |
| customerResponse | Text | No | null | - | **PII** Customer's response (inbound) |
| responseAssessment | Text | No | null | - | Analyst assessment of response |
| respondedAt | Timestamp | No | null | - | When customer responded |
| createdAt | Timestamp | Yes | auto | - | When recorded |
| updatedAt | Timestamp | Yes | auto | - | Last modification |

### Relationships

| Relationship | Type | Target | FK Location | On Delete | Description |
|--------------|------|--------|-------------|-----------|-------------|
| case | N:1 | Case | CustomerCommunication.caseId | Cascade | Associated case |
| template | N:1 | CommunicationTemplate | CustomerCommunication.templateId | Set Null | Template used |
| sentByUser | N:1 | User | CustomerCommunication.sentByUserId | Set Null | Sending analyst |

### PII Field Registry

Per D12 (PII Redaction Strategy), the following fields are marked as PII:
- `content`
- `customerResponse`

---

## Entity: OnboardingBlock [NEW]

> A hold preventing customer onboarding completion due to compliance screening result.
> Sources: Key Entities - Onboarding Block, FR-028, FR-029, EC-009, US-6, US-7

### Attributes

| Attribute | Type | Required | Default | Validation | Description |
|-----------|------|----------|---------|------------|-------------|
| id | UUID | Yes | auto-generated | - | Primary key |
| customerId | Reference(Customer) | Yes | - | FK | Blocked customer |
| caseId | Reference(Case) | Yes | - | FK | Associated case |
| blockType | Enum | Yes | - | OneOf: [SANCTIONS, PEP_EDD_REQUIRED] | Reason for block |
| blockReason | Text(500) | Yes | - | - | Detailed reason |
| syncStatus | Enum | Yes | PENDING_SYNC | OneOf: [SYNCED, PENDING_SYNC, SYNC_FAILED] | API callback status (EC-009) |
| lastSyncAttempt | Timestamp | No | null | - | When last sync attempted |
| syncAttemptCount | Integer | Yes | 0 | Min: 0 | Number of sync attempts |
| clearedAt | Timestamp | No | null | - | When block was removed |
| clearedByUserId | Reference(User) | No | null | FK | Analyst who cleared |
| createdAt | Timestamp | Yes | auto | - | When block applied |

### Relationships

| Relationship | Type | Target | FK Location | On Delete | Description |
|--------------|------|--------|-------------|-----------|-------------|
| customer | N:1 | Customer | OnboardingBlock.customerId | Cascade | Blocked customer |
| case | N:1 | Case | OnboardingBlock.caseId | Cascade | Associated case |
| clearedByUser | N:1 | User | OnboardingBlock.clearedByUserId | Set Null | Clearing analyst |

### Constraints

| Constraint | Type | Fields | Rule |
|------------|------|--------|------|
| idx_customer_active | Index | customerId, clearedAt | For finding active blocks |
| chk_cleared_fields | Check | clearedAt, clearedByUserId | (clearedAt IS NULL AND clearedByUserId IS NULL) OR (clearedAt IS NOT NULL AND clearedByUserId IS NOT NULL) |

---

## Entity: EDDChecklist [NEW]

> Structured documentation of Enhanced Due Diligence measures applied to a PEP case.
> Sources: Key Entities - EDD Checklist, FR-033, FR-034, US-7

### Attributes

| Attribute | Type | Required | Default | Validation | Description |
|-----------|------|----------|---------|------------|-------------|
| id | UUID | Yes | auto-generated | - | Primary key |
| caseId | Reference(Case) | Yes | - | FK, Unique | Associated PEP case |
| sourceOfWealth | Text | Yes | - | Min length: 50 | **PII** Source of wealth documentation |
| sourceOfFunds | Text | Yes | - | Min length: 50 | **PII** Source of funds documentation |
| relationshipPurpose | Text | Yes | - | Min length: 20 | Purpose of relationship |
| enhancedMonitoringFrequency | Enum | Yes | - | OneOf: [WEEKLY, MONTHLY, QUARTERLY, ANNUALLY] | Monitoring frequency |
| additionalNotes | Text | No | null | - | Additional EDD notes |
| completedAt | Timestamp | Yes | auto | - | When checklist completed |
| completedByUserId | Reference(User) | Yes | - | FK | Completing analyst |
| createdAt | Timestamp | Yes | auto | - | Record creation time |
| updatedAt | Timestamp | Yes | auto | - | Last modification time |

### Relationships

| Relationship | Type | Target | FK Location | On Delete | Description |
|--------------|------|--------|-------------|-----------|-------------|
| case | 1:1 | Case | EDDChecklist.caseId | Cascade | Associated PEP case |
| completedByUser | N:1 | User | EDDChecklist.completedByUserId | Restrict | Completing analyst |

### Constraints

| Constraint | Type | Fields | Rule |
|------------|------|--------|------|
| uk_case | Unique | caseId | One EDD checklist per case |

### PII Field Registry

Per D12, the following contain customer financial information:
- `sourceOfWealth`
- `sourceOfFunds`

---

## Entity: CaseLink [NEW]

> Represents a relationship between two cases, particularly for supplementary SMR filings.
> Sources: Key Entities - Case Link, FR-044, FR-045, FR-046, FR-047, US-18

### Attributes

| Attribute | Type | Required | Default | Validation | Description |
|-----------|------|----------|---------|------------|-------------|
| id | UUID | Yes | auto-generated | - | Primary key |
| sourceCaseId | Reference(Case) | Yes | - | FK | Source case (supplementary) |
| targetCaseId | Reference(Case) | Yes | - | FK | Target case (original) |
| linkType | Enum | Yes | - | OneOf: [SUPPLEMENTARY_TO_ORIGINAL, RELATED, SAME_CUSTOMER] | Relationship type |
| notes | Text | No | null | - | Link context |
| createdByUserId | Reference(User) | Yes | - | FK | User who created link |
| createdAt | Timestamp | Yes | auto | - | When link created |

### Relationships

| Relationship | Type | Target | FK Location | On Delete | Description |
|--------------|------|--------|-------------|-----------|-------------|
| sourceCase | N:1 | Case | CaseLink.sourceCaseId | Cascade | Source case |
| targetCase | N:1 | Case | CaseLink.targetCaseId | Cascade | Target case |
| createdByUser | N:1 | User | CaseLink.createdByUserId | Restrict | Link creator |

### Constraints

| Constraint | Type | Fields | Rule |
|------------|------|--------|------|
| uk_link | Unique | sourceCaseId, targetCaseId, linkType | Prevent duplicate links |
| chk_no_self_link | Check | sourceCaseId, targetCaseId | sourceCaseId != targetCaseId |

---

## Entity: PEPThresholdConfig [NEW]

> System configuration for PEP confidence score classification.
> Sources: Key Entities - PEP Confidence Threshold Configuration, FR-030, FR-031, EC-011

### Attributes

| Attribute | Type | Required | Default | Validation | Description |
|-----------|------|----------|---------|------------|-------------|
| id | UUID | Yes | auto-generated | - | Primary key |
| thresholdValue | Decimal(5,2) | Yes | 80.00 | Range: 0-100 | PEP confidence threshold (default 80%) |
| effectiveFrom | Timestamp | Yes | - | - | When this threshold takes effect |
| effectiveUntil | Timestamp | No | null | - | When this threshold expires (null = current) |
| changedByUserId | Reference(User) | Yes | - | FK | User who set this threshold |
| createdAt | Timestamp | Yes | auto | - | Record creation time |

### Relationships

| Relationship | Type | Target | FK Location | On Delete | Description |
|--------------|------|--------|-------------|-----------|-------------|
| changedByUser | N:1 | User | PEPThresholdConfig.changedByUserId | Restrict | User who changed threshold |

### Constraints

| Constraint | Type | Fields | Rule |
|------------|------|--------|------|
| idx_effective_current | Index | effectiveFrom, effectiveUntil | For finding current threshold |

### Notes

Per EC-011: Score **equal to** threshold is treated as low-confidence (provisional proceed). Only scores **strictly above** threshold trigger blocking EDD requirement.

---

## Entity: Document [NEW]

> Attached evidence files and supporting documentation.
> Sources: D4 (Document Storage Strategy)

### Attributes

| Attribute | Type | Required | Default | Validation | Description |
|-----------|------|----------|---------|------------|-------------|
| id | UUID | Yes | auto-generated | - | Primary key |
| caseId | Reference(Case) | Yes | - | FK | Associated case |
| filename | Text(255) | Yes | - | - | Original filename |
| contentType | Text(100) | Yes | - | - | MIME type |
| sizeBytes | Integer | Yes | - | Min: 1 | File size in bytes |
| sha256Hash | Text(64) | Yes | - | Pattern: ^[a-f0-9]{64}$ | Integrity hash |
| storageType | Enum | Yes | - | OneOf: [DATABASE, S3] | Where file is stored |
| storageKey | Text(500) | No | null | - | S3 key if external storage |
| content | Binary | No | null | - | File content if database storage |
| documentType | Enum | Yes | - | OneOf: [SMR_DRAFT, EVIDENCE, CUSTOMER_DOCUMENT, OTHER] | Document classification |
| uploadedByUserId | Reference(User) | Yes | - | FK | Uploading user |
| createdAt | Timestamp | Yes | auto | - | Upload time |

### Relationships

| Relationship | Type | Target | FK Location | On Delete | Description |
|--------------|------|--------|-------------|-----------|-------------|
| case | N:1 | Case | Document.caseId | Cascade | Associated case |
| uploadedByUser | N:1 | User | Document.uploadedByUserId | Restrict | Uploading user |

### Constraints

| Constraint | Type | Fields | Rule |
|------------|------|--------|------|
| chk_storage_consistency | Check | storageType, storageKey, content | (storageType = 'DATABASE' AND content IS NOT NULL) OR (storageType = 'S3' AND storageKey IS NOT NULL) |
| chk_small_db_storage | Check | storageType, sizeBytes | storageType = 'S3' OR sizeBytes <= 1048576 | Only files <= 1MB in database |

---

## Entity: SMRDraft [NEW]

> Generated SMR document upon manager approval.
> Sources: FR-040, D4 (Document Storage Strategy)

### Attributes

| Attribute | Type | Required | Default | Validation | Description |
|-----------|------|----------|---------|------------|-------------|
| id | UUID | Yes | auto-generated | - | Primary key |
| caseId | Reference(Case) | Yes | - | FK, Unique | Associated case |
| smrRecommendationId | Reference(SMRRecommendation) | Yes | - | FK | Source recommendation |
| content | Binary | Yes | - | - | PDF content (stored in database for integrity) |
| formatVersion | Text(20) | Yes | - | - | AUSTRAC format version |
| generatedAt | Timestamp | Yes | auto | - | Generation time |
| generatedByUserId | Reference(User) | Yes | - | FK | Manager who approved (triggers generation) |
| createdAt | Timestamp | Yes | auto | - | Record creation time |

### Relationships

| Relationship | Type | Target | FK Location | On Delete | Description |
|--------------|------|--------|-------------|-----------|-------------|
| case | 1:1 | Case | SMRDraft.caseId | Cascade | Associated case |
| smrRecommendation | 1:1 | SMRRecommendation | SMRDraft.smrRecommendationId | Cascade | Source recommendation |
| generatedByUser | N:1 | User | SMRDraft.generatedByUserId | Restrict | Generating manager |

### Constraints

| Constraint | Type | Fields | Rule |
|------------|------|--------|------|
| uk_case | Unique | caseId | One draft per case |
| uk_recommendation | Unique | smrRecommendationId | One draft per recommendation |

---

## Entity: AuditLog [NEW]

> Immutable record of all system actions for regulatory compliance.
> Sources: D1 (Audit Trail Architecture), FR-058, FR-059, FR-060, FR-061, FR-062, Principle I

### Attributes

| Attribute | Type | Required | Default | Validation | Description |
|-----------|------|----------|---------|------------|-------------|
| id | UUID | Yes | auto-generated | - | Primary key |
| caseId | Reference(Case) | No | null | FK | Associated case (null for system events) |
| userId | Reference(User) | No | null | FK | Acting user (null for system actions) |
| actionType | Text(50) | Yes | - | - | Action classification |
| actionDetail | JSON | Yes | {} | - | Structured payload (PII redacted per D12) |
| resourceType | Text(50) | No | null | - | Entity type affected |
| resourceId | UUID | No | null | - | Entity ID affected |
| ipAddress | Text(45) | No | null | - | Client IP (IPv6 compatible) |
| userAgent | Text(255) | No | null | - | Client user agent |
| createdAt | Timestamp | Yes | auto | - | Action timestamp |

### Relationships

| Relationship | Type | Target | FK Location | On Delete | Description |
|--------------|------|--------|-------------|-----------|-------------|
| case | N:1 | Case | AuditLog.caseId | Set Null | Associated case |
| user | N:1 | User | AuditLog.userId | Set Null | Acting user |

### Constraints

| Constraint | Type | Fields | Rule |
|------------|------|--------|------|
| idx_case_created | Index | caseId, createdAt | For case audit retrieval |
| idx_user_created | Index | userId, createdAt | For user activity retrieval |
| idx_action_type | Index | actionType, createdAt | For action analysis |

### Immutability Rules (Principle I)

- **No UPDATE operations permitted** on this entity
- **No DELETE operations permitted** on this entity
- 7-year retention minimum (FR-060)
- All payloads must pass through PII redaction service (D12)
- Database trigger recommended to enforce immutability

### Standard Action Types

| Action Type | Description |
|-------------|-------------|
| CASE_CREATED | New case created from webhook |
| CASE_VIEWED | Case read access (FR-059) |
| CASE_CLAIMED | Analyst claimed from queue |
| CASE_ESCALATED | Case escalated to higher tier |
| CASE_CLOSED | Case closed with disposition |
| CASE_REOPENED | Case reopened (L2 overturn) |
| SMR_RECOMMENDED | SMR recommendation created |
| SMR_APPROVED | SMR approved by manager |
| SMR_REJECTED | SMR rejected by manager |
| SMR_FILED | AUSTRAC reference recorded |
| BLOCK_APPLIED | Onboarding block applied |
| BLOCK_CLEARED | Onboarding block removed |
| EDD_COMPLETED | EDD checklist submitted |
| COMMUNICATION_SENT | Customer outreach recorded |
| ROLE_CHANGED | User role modified |
| LOGIN_SUCCESS | User authenticated |
| LOGIN_FAILED | Authentication failure |
| WEBHOOK_RECEIVED | External webhook processed |
| WEBHOOK_AUTH_FAILED | Webhook authentication rejected |

---

## Entity: Notification [NEW]

> System notifications for users.
> Sources: D6 (Notification System), FR-066, FR-067, FR-068, FR-069

### Attributes

| Attribute | Type | Required | Default | Validation | Description |
|-----------|------|----------|---------|------------|-------------|
| id | UUID | Yes | auto-generated | - | Primary key |
| userId | Reference(User) | Yes | - | FK | Recipient user |
| notificationType | Enum | Yes | - | OneOf: [CASE_ASSIGNED, SLA_WARNING, SLA_BREACH, ESCALATION, SMR_PENDING_APPROVAL, SMR_APPROVED, SMR_REJECTED] | Notification type |
| title | Text(255) | Yes | - | - | Notification title |
| body | Text | Yes | - | - | Notification body |
| caseId | Reference(Case) | No | null | FK | Related case |
| emailSent | Boolean | Yes | false | - | Whether email was sent |
| emailSentAt | Timestamp | No | null | - | When email was sent |
| readAt | Timestamp | No | null | - | When user read notification |
| createdAt | Timestamp | Yes | auto | - | When created |

### Relationships

| Relationship | Type | Target | FK Location | On Delete | Description |
|--------------|------|--------|-------------|-----------|-------------|
| user | N:1 | User | Notification.userId | Cascade | Recipient |
| case | N:1 | Case | Notification.caseId | Set Null | Related case |

### Constraints

| Constraint | Type | Fields | Rule |
|------------|------|--------|------|
| idx_user_unread | Index | userId, readAt | For unread notification count |
| idx_user_created | Index | userId, createdAt | For notification list |

---

## Entity: HolidayOverride [NEW]

> Custom holiday dates for SLA business day calculations.
> Sources: D2 (SLA Calculation Engine), FR-048

### Attributes

| Attribute | Type | Required | Default | Validation | Description |
|-----------|------|----------|---------|------------|-------------|
| id | UUID | Yes | auto-generated | - | Primary key |
| holidayDate | Date | Yes | - | Unique | Holiday date |
| description | Text(200) | Yes | - | - | Holiday name/description |
| region | Text(50) | No | null | - | State/region if applicable |
| createdByUserId | Reference(User) | Yes | - | FK | User who added |
| createdAt | Timestamp | Yes | auto | - | Record creation time |

### Constraints

| Constraint | Type | Fields | Rule |
|------------|------|--------|------|
| uk_date | Unique | holidayDate | One entry per date |

---

## Entity: WebhookReceipt [NEW]

> Tracks received webhooks for duplicate detection.
> Sources: D3 (External Integration Pattern), EC-005

### Attributes

| Attribute | Type | Required | Default | Validation | Description |
|-----------|------|----------|---------|------------|-------------|
| id | UUID | Yes | auto-generated | - | Primary key |
| dedupKey | Text(64) | Yes | - | Indexed | SHA256 hash of customer_id:alert_type:source |
| caseId | Reference(Case) | Yes | - | FK | Created or linked case |
| source | Enum | Yes | - | OneOf: [GREENID, INDUE] | Webhook source |
| receivedAt | Timestamp | Yes | auto | - | When webhook received |
| rawPayloadHash | Text(64) | Yes | - | - | Hash of raw payload |

### Relationships

| Relationship | Type | Target | FK Location | On Delete | Description |
|--------------|------|--------|-------------|-----------|-------------|
| case | N:1 | Case | WebhookReceipt.caseId | Cascade | Created/linked case |

### Constraints

| Constraint | Type | Fields | Rule |
|------------|------|--------|------|
| idx_dedup_received | Index | dedupKey, receivedAt | For duplicate detection within window |

### Notes

Per D3: Duplicates within 24-hour window (configurable) are linked to existing case rather than creating new case.

---

## Entity Relationships Diagram

```
Customer ──1:N──▶ Case (subject of)
Customer ──1:N──▶ OnboardingBlock (has)

User ──1:N──▶ Assignment (assigned)
User ──1:N──▶ TimelineEntry (performed)
User ──1:N──▶ SMRRecommendation (recommended)
User ──1:N──▶ SMRRecommendation (approved)
User ──1:N──▶ Notification (receives)

Case ──1:N──▶ Assignment (has)
Case ──1:N──▶ TimelineEntry (has)
Case ──1:1──▶ InvestigationFindings (may have)
Case ──1:1──▶ SMRRecommendation (may have)
Case ──1:N──▶ CustomerCommunication (has)
Case ──1:1──▶ OnboardingBlock (may have)
Case ──1:1──▶ EDDChecklist (may have)
Case ──1:N──▶ Document (has)
Case ──1:1──▶ SMRDraft (may have)
Case ◀──N:M──▶ Case (via CaseLink)

SMRRecommendation ──1:1──▶ SMRDraft (generates)

CommunicationTemplate ──1:N──▶ CustomerCommunication (used by)
```

---

## State Machines

### Case Status State Machine

#### Implicit Claiming Principle (G1 Resolution)

**Key Design Decision**: Claiming is implicit in any case action.

When an analyst performs any action on an OPEN case (e.g., closing as false positive), the system automatically:
1. Claims the case to the analyst (creates Assignment record)
2. Transitions through IN_PROGRESS
3. Completes the requested action

This allows atomic operations like "close as false positive" on an unassigned case without requiring a separate claim step. The state machine represents observable business states, not micro-operations.

**Example - False Positive Closure (US-1)**:
- L1 analyst reviews OPEN case in queue
- Analyst submits closure with required documentation
- System atomically: creates assignment + transitions to IN_PROGRESS + transitions to CLOSED
- Single API call, single audit trail entry showing "Claimed and closed as false positive"

#### States

| State | Description | Entry Condition |
|-------|-------------|-----------------|
| `OPEN` | Initial state | Case created from webhook |
| `IN_PROGRESS` | Active investigation | Analyst claimed or assigned (explicit or implicit) |
| `PENDING_INFORMATION` | Awaiting customer response | Communication sent |
| `ESCALATED` | Moved to higher tier | L1 escalated to L2 |
| `PENDING_APPROVAL` | SMR awaiting manager | L2 submitted recommendation |
| `CLOSED` | Investigation complete | Analyst closed case |
| `SMR_FILED` | SMR submitted to AUSTRAC | AUSTRAC reference recorded |

#### Transitions

| From | To | Trigger | Guard | Side Effects |
|------|-----|---------|-------|--------------|
| OPEN | IN_PROGRESS | analyst.claimCase() | Analyst has appropriate tier | Create assignment; Set assignedAt |
| OPEN | CLOSED | analyst.closeCase() | Analyst has appropriate tier; Required documentation complete | **Implicit claim**: Create assignment; Set assignedAt; Set closedAt; Create timeline entry; Record disposition; Set l2ReviewStatus if L1 satisfactory explanation |
| IN_PROGRESS | PENDING_INFORMATION | analyst.requestInformation() | Communication sent | Create timeline entry |
| PENDING_INFORMATION | IN_PROGRESS | analyst.recordResponse() | Response received | Create timeline entry |
| IN_PROGRESS | ESCALATED | l1Analyst.escalate() | User is L1; has documented reasoning | Create assignment to L2 queue; Change tier |
| ESCALATED | IN_PROGRESS | l2Analyst.claimCase() | User is L2+ | Create assignment |
| IN_PROGRESS | CLOSED | analyst.closeCase() | Required documentation complete | Set closedAt; Create timeline entry; Record disposition; Set l2ReviewStatus if L1 satisfactory explanation |
| CLOSED | IN_PROGRESS | l2Analyst.reopenCase() | User is L2+; was L1 closure | Clear closedAt; Set l2ReviewStatus = REVIEWED_REOPENED; Create timeline entry; Create assignment to L2 |
| IN_PROGRESS | PENDING_APPROVAL | l2Analyst.submitSMR() | SMR recommendation complete | Create notification to manager |
| PENDING_APPROVAL | IN_PROGRESS | manager.rejectSMR() | User is AML_MANAGER; not recommender | Increment rejection count; Create notification |
| PENDING_APPROVAL | CLOSED | manager.approveSMR() | User is AML_MANAGER; not recommender | Set closedAt; Generate SMR draft; Create notification |
| CLOSED | SMR_FILED | analyst.recordAUSTRAC() | SMR was approved; reference number provided | Record reference; Create timeline entry |

#### L2 Review Status Transitions

When L1 closes a case with satisfactory explanation:
- l2ReviewStatus is set to `PENDING_REVIEW` (FR-012)
- Case appears in L2 quality review queue (FR-018)

When L2 reviews and accepts the closure:
- l2ReviewStatus is set to `REVIEWED_ACCEPTED`
- Case remains CLOSED

When L2 reviews and disagrees:
- l2ReviewStatus is set to `REVIEWED_REOPENED`
- Case transitions from CLOSED to IN_PROGRESS
- Case is assigned to L2 reviewer (FR-019)

#### Diagram

```
                                   ┌───────────────────────┐
                                   │       [OPEN]          │
                                   └───────────┬───────────┘
                                               │
                          ┌────────────────────┼────────────────────┐
                          │ claim (explicit)   │                    │ close (implicit claim)
                          ▼                    │                    ▼
       ┌──────────────────────────────────────────────────────────────────┐
       │                        [IN_PROGRESS]                              │
       │                                                                   │
       │  ◀──record response── [PENDING_INFORMATION] ◀──request info──    │
       │                                                                   │
       │  ◀──claim (L2)─────── [ESCALATED] ◀──────────────────escalate──  │
       │                                                                   │
       │  ──submit SMR──▶ [PENDING_APPROVAL] ──approve──▶                 │
       │        ▲                    │                                     │
       │        └────reject──────────┘                                     │
       └───────────────────────────────────────────────────────────────────┘
                               │ close                  │ approve SMR
                               ▼                        ▼
                         [CLOSED] ◀─────────────────────┘
                          │    ▲
                          │    │ L2 reopen (quality review)
                          │    └──────────────────────────────────────────
                          │
                          │ record AUSTRAC ref
                          ▼
                         [SMR_FILED]

      Note: OPEN -> CLOSED path represents atomic close with implicit claim
      L2 can reopen CLOSED cases (L1 closures) back to IN_PROGRESS
```

### SMR Recommendation Status State Machine

#### States

| State | Description | Entry Condition |
|-------|-------------|-----------------|
| `PENDING` | Initial state | L2 created recommendation |
| `APPROVED` | Manager approved | Manager approved SMR |
| `REJECTED` | Manager rejected | Manager rejected with feedback |
| `FILED` | Submitted to AUSTRAC | Reference number recorded |

#### Transitions

| From | To | Trigger | Guard | Side Effects |
|------|-----|---------|-------|--------------|
| PENDING | APPROVED | manager.approve() | User is AML_MANAGER; not recommender | Set approvedAt, approvingUserId; Generate SMRDraft |
| PENDING | REJECTED | manager.reject() | User is AML_MANAGER; reason provided | Increment rejectionCount; Add to rejectionHistory |
| REJECTED | PENDING | l2Analyst.resubmit() | Updated narrative | Clear rejection (keep history) |
| APPROVED | FILED | analyst.recordReference() | AUSTRAC reference provided | Set austracReferenceNumber, austracFiledAt |

#### Diagram

```
[PENDING] ──approve──▶ [APPROVED] ──record ref──▶ [FILED]
    │                       │
    │                       │ (cannot withdraw - FR-043)
    ▼                       │
[REJECTED] ──resubmit──────▶│
    ▲                       │
    └───────────────────────┘
         (no limit - EC-010)
```

### Onboarding Block Sync Status

#### States

| State | Description |
|-------|-------------|
| `PENDING_SYNC` | Initial state; API callback pending |
| `SYNCED` | API callback succeeded |
| `SYNC_FAILED` | API callback failed after retries |

#### Transitions

| From | To | Trigger | Side Effects |
|------|-----|---------|--------------|
| PENDING_SYNC | SYNCED | Spriggy API success | Clear retry state |
| PENDING_SYNC | SYNC_FAILED | Max retries exceeded | Move to DLQ; Alert operations |
| SYNC_FAILED | PENDING_SYNC | Manual retry trigger | Reset retry count |

---

## Traceability

### Requirement to Entity Mapping

| Requirement | Entities | Description |
|-------------|----------|-------------|
| FR-001, FR-002, FR-003, FR-004, FR-005, FR-006 | Case | Core case lifecycle |
| FR-008 through FR-011, FR-013 through FR-023 | Case, User, Assignment, SMRRecommendation | Tiered workflow |
| FR-012, FR-018, FR-019 | Case (l2ReviewStatus) | L2 quality review queue |
| FR-024, FR-025 | Case | Case prioritization |
| FR-026, FR-027 | Assignment, User | Role change handling |
| FR-028, FR-029, FR-030, FR-031, FR-032 | OnboardingBlock, Case | Onboarding blocking |
| FR-033, FR-034 | EDDChecklist | EDD requirements |
| FR-035 | Case | Combined alert handling |
| FR-036, FR-037, FR-038 | Case | Existing customer sanctions |
| FR-039, FR-040, FR-041, FR-042, FR-043 | SMRRecommendation, SMRDraft | SMR process |
| FR-044, FR-045, FR-046, FR-047 | CaseLink, SMRRecommendation | Supplementary SMR |
| FR-048, FR-049, FR-050, FR-051, FR-052 | Case, HolidayOverride, Notification | SLA management |
| FR-053, FR-054, FR-055, FR-056, FR-057 | CommunicationTemplate, CustomerCommunication | Customer communication |
| FR-058, FR-059, FR-060, FR-061, FR-062 | AuditLog, TimelineEntry | Audit trail |
| FR-063, FR-064, FR-065 | User | Access control |
| FR-066, FR-067, FR-068, FR-069 | Notification | Notifications |
| FR-070, FR-071, FR-072, FR-073 | (Materialized views - not entities) | Reporting |

### User Story to Entity Mapping

| User Story | Primary Entities | Supporting Entities |
|------------|------------------|---------------------|
| US-1 | Case, TimelineEntry | Customer, User |
| US-2 | CustomerCommunication, CommunicationTemplate | Case |
| US-3 | Case, Assignment, TimelineEntry | User |
| US-4 | InvestigationFindings, SMRRecommendation, Case | User, TimelineEntry |
| US-5 | SMRRecommendation, SMRDraft | Case, User |
| US-6 | OnboardingBlock, Case | Customer |
| US-7 | EDDChecklist, OnboardingBlock, Case | Customer, User |
| US-8 | Case | Customer |
| US-9 | Case, Notification | HolidayOverride |
| US-10 | (Reporting views) | User |
| US-11 | SMRRecommendation, Case | User |
| US-12 | Case, Notification | User |
| US-13 | Case, TimelineEntry | User |
| US-14 | Assignment, Case | User |
| US-15 | Case | Customer |
| US-16 | Case, Assignment, TimelineEntry | User |
| US-17 | Case, OnboardingBlock | Customer |
| US-18 | CaseLink, Case, SMRRecommendation | User |

### Edge Case to Entity Mapping

| Edge Case | Entities Involved | Handling |
|-----------|-------------------|----------|
| EC-001 | Case | Optimistic locking via version column |
| EC-002 | (Integration layer) | Circuit breaker pattern |
| EC-003 | SMRRecommendation, User | recommendingUserId tracking |
| EC-004 | Case, TimelineEntry | Timeline preserves escalation history |
| EC-005 | WebhookReceipt, Case | Duplicate detection via dedupKey |
| EC-006 | Case, Assignment, Notification | Unassigned queue with manager alerts |
| EC-007 | (All timestamps) | UTC storage, timezone conversion |
| EC-008 | Customer, Case | accountStatus flag; case continues |
| EC-009 | OnboardingBlock | syncStatus with retry tracking |
| EC-010 | SMRRecommendation | rejectionCount, rejectionHistory |
| EC-011 | PEPThresholdConfig, Case | Threshold comparison logic (> not >=) |
| EC-012 | Assignment, TimelineEntry | Audit trail preserved |
| EC-013 | CaseLink | Multiple supplementary links supported |
| EC-014 | Case, CaseLink | Related case linking |

---

## Constitution Alignment

### Principle I: Immutable Audit Trail

| Requirement | Implementation |
|-------------|----------------|
| All actions recorded immutably | AuditLog and TimelineEntry with no UPDATE/DELETE |
| Full attribution | userId on all entries |
| Timestamp accuracy | UTC timestamps with server_default |
| 7-year retention | Retention policy on AuditLog (operational) |
| No deletion | Database triggers to prevent DELETE |
| Export capability | Indexed for efficient retrieval |

### Principle II: RBAC with Segregation

| Requirement | Implementation |
|-------------|----------------|
| Four roles enforced | User.role enum with L1_ANALYST, L2_ANALYST, AML_MANAGER, READ_ONLY |
| L1 cannot approve SMRs | Business rule BR-SMR-001 |
| L2 cannot approve own | Business rule BR-SMR-002; recommendingUserId tracking |
| Role change tracking | User.roleChangedAt, roleChangedBy |

### Principle VI: Sensitive Data Protection

| Requirement | Implementation |
|-------------|----------------|
| PII identification | PII fields marked in Customer, CustomerCommunication, EDDChecklist |
| No PII in logs | D12 redaction service applied to AuditLog.actionDetail |
| Encryption at rest | Database-level encryption (operational) |

---

## Notes for Contracts Phase

1. **Webhook endpoints** need to:
   - Validate HMAC signatures (D11)
   - Check for duplicates via WebhookReceipt
   - Create Case with appropriate type/subtype
   - Trigger OnboardingBlock creation when applicable

2. **Case endpoints** need to:
   - Include version for optimistic locking (D8)
   - Return 409 Conflict on version mismatch
   - Order queue by slaDeadline, then createdAt

3. **SMR endpoints** need to:
   - Enforce segregation of duties (BR-SMR-002)
   - Prevent state transitions from APPROVED except to FILED

4. **Dashboard endpoints** need to:
   - Support 30-second polling interval (D6)
   - Include unread notification count
   - Show SLA indicators

5. **All write endpoints** need to:
   - Create AuditLog entries with PII redaction
   - Create TimelineEntry for case-related actions
