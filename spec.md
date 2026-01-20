# AML Case Management System

> Feature ID: 001-aml-case-management
> Created: 2026-01-13
> Status: Draft (Iteration 3)

---

## Overview

The AML Case Management System enables Spriggy to meet AUSTRAC AML/CTF compliance obligations by providing a unified platform for managing three core workstreams: KYC remediation, PEP/Sanctions screening disposition, and suspicious activity investigation. The system enforces a tiered analyst workflow (L1 Triage, L2 Investigation, AML Compliance Manager approval) with strict segregation of duties, immutable audit trails, and SLA tracking. Day 1 delivery focuses on core workflow capabilities with manual AUSTRAC submission; automated API integration is deferred to Phase 2.

---

## User Stories

### User Story 1 - L1 Analyst Triages Screening Alert (Priority: P1)

An L1 Analyst receives notification of a new PEP/Sanctions screening hit from GreenID. They review the alert details, compare against customer information, and determine it is a false positive due to name similarity. They document their reasoning using the mandatory fields and close the case as a false positive.

**Why this priority**: Core triage workflow is essential for Day 1 operations. Without L1 triage capability, the system cannot process the expected volume of screening alerts, creating regulatory risk and blocking customer onboarding.

**Independent Test**: Create a test screening alert assigned to an L1 user. Verify the analyst can view alert details, access the false positive closure form, enter required documentation, and successfully close the case. Confirm the action is recorded in the audit trail.

**Acceptance Scenarios**:
1. **Given** an L1 Analyst with an assigned PEP screening alert, **When** they review the case and select "Close as False Positive", **Then** they see a mandatory documentation form requiring justification before closure is permitted.
2. **Given** an L1 Analyst completing false positive documentation, **When** they submit with all required fields populated, **Then** the case status changes to "Closed - False Positive" and the action appears in the audit trail with timestamp and analyst attribution.
3. **Given** an L1 Analyst attempting to close a case, **When** required documentation fields are empty, **Then** the system prevents closure and displays which fields are missing.

### User Story 2 - L1 Analyst Requests Customer Information (Priority: P1)

An L1 Analyst reviewing a KYC remediation case needs additional documentation from the customer. They select from pre-approved scripted templates to request the information, and the system records the outreach in the case timeline. The SLA clock continues while awaiting response.

**Why this priority**: Customer communication is fundamental to case resolution. Without documented outreach capability, cases cannot progress and compliance cannot demonstrate proper process.

**Independent Test**: Create a KYC remediation case requiring customer contact. Verify L1 can select a communication template, customize permitted fields, record the outreach, and see it in the case timeline. Confirm SLA tracking remains active.

**Acceptance Scenarios**:
1. **Given** an L1 Analyst on a KYC case requiring customer documents, **When** they select "Request Information", **Then** they see a list of pre-approved communication templates appropriate to the case type.
2. **Given** an L1 Analyst selecting a communication template, **When** they complete required fields and submit, **Then** the outreach is recorded in the case timeline with timestamp, template used, and message content.
3. **Given** an L1 Analyst who has requested information, **When** customer response is received, **Then** the analyst can record the response and document their assessment of whether it satisfies the request.

### User Story 3 - L1 Analyst Escalates Suspicious Case (Priority: P1)

An L1 Analyst identifies indicators that suggest genuinely suspicious activity during transaction monitoring alert triage. They document the concern and escalate to L2 for full investigation, as L1 is not authorized to make SMR determinations.

**Why this priority**: Escalation pathway is critical for regulatory compliance. L1 must be able to route genuinely suspicious cases to qualified investigators; blocking this creates compliance risk.

**Independent Test**: Create a transaction monitoring case assigned to L1. Verify escalation option is available, requires documented reasoning, and successfully transfers the case to L2 queue with full history preserved.

**Acceptance Scenarios**:
1. **Given** an L1 Analyst reviewing a transaction monitoring alert, **When** they identify suspicious indicators, **Then** they see an "Escalate to L2" option that requires documented reasoning.
2. **Given** an L1 Analyst completing escalation documentation, **When** they submit the escalation, **Then** the case moves to the L2 queue with all prior documentation and timeline preserved.
3. **Given** an escalated case arriving in L2 queue, **When** an L2 Analyst views it, **Then** they see the L1 analyst's escalation reasoning and complete case history.

### User Story 4 - L2 Analyst Completes Investigation and Recommends SMR (Priority: P1)

An L2 Analyst conducts a full investigation of an escalated suspicious activity case. They document findings, determine an SMR is warranted, and create a detailed SMR recommendation including the required narrative for AML Compliance Manager review.

**Why this priority**: SMR recommendation is a core regulatory function. Without this capability, Spriggy cannot fulfill its reporting entity obligations under AUSTRAC requirements.

**Independent Test**: Create an escalated case assigned to L2. Verify the analyst can document investigation findings, access the SMR recommendation form, complete all required fields including narrative, and submit for manager approval.

**Acceptance Scenarios**:
1. **Given** an L2 Analyst with an assigned investigation, **When** they complete their analysis, **Then** they can document findings with structured fields for entities involved, transaction patterns, and suspicious indicators.
2. **Given** an L2 Analyst determining an SMR is warranted, **When** they select "Create SMR Recommendation", **Then** they see a form requiring narrative description, supporting evidence references, and reason for suspicion.
3. **Given** an L2 Analyst submitting an SMR recommendation, **When** submission succeeds, **Then** the case enters "Pending Manager Approval" status and the AML Compliance Manager is notified.

### User Story 5 - AML Compliance Manager Approves SMR (Priority: P1)

The AML Compliance Manager reviews an SMR recommendation from an L2 Analyst. They examine the investigation documentation, verify the recommendation meets AUSTRAC standards, approve the SMR, and the system generates an SMR-formatted draft document ready for manual submission.

**Why this priority**: Manager approval is the final control before regulatory filing. This segregation of duty is non-negotiable for compliance; L2 cannot approve their own recommendations.

**Independent Test**: Create a case with pending SMR recommendation. Verify Manager can review full investigation, approve/reject with documented reasoning, and upon approval see a generated SMR draft document.

**Acceptance Scenarios**:
1. **Given** an AML Compliance Manager viewing a pending SMR recommendation, **When** they open the case, **Then** they see the complete investigation documentation, L2 narrative, and recommendation details.
2. **Given** an AML Compliance Manager approving an SMR, **When** they confirm approval, **Then** the system generates an SMR-formatted draft document and records the approval in the audit trail.
3. **Given** an AML Compliance Manager rejecting an SMR recommendation, **When** they provide rejection reasoning, **Then** the case returns to L2 with the feedback and "Manager Rejected" status, and L2 can resubmit with revisions.

### User Story 6 - System Blocks Sanctions-Hit Customer Onboarding (Priority: P1)

During customer onboarding, GreenID returns a sanctions screening hit. The system automatically blocks the onboarding process via API callback to Spriggy's onboarding service and creates a case for analyst review. The customer cannot proceed until an analyst clears the alert.

**Why this priority**: Sanctions blocking is a non-negotiable regulatory requirement. Allowing sanctions-hit customers to onboard creates immediate regulatory breach and reputational risk.

**Independent Test**: Simulate a GreenID webhook with sanctions hit data. Verify case is created, onboarding block API is called, and the block persists until an analyst disposition is recorded. Verify callback to Spriggy's onboarding service when block is cleared.

**Acceptance Scenarios**:
1. **Given** a new customer application triggering sanctions screening, **When** GreenID returns a sanctions match, **Then** onboarding is blocked via API callback to Spriggy's onboarding service and a case is automatically created with "Sanctions - Pending Review" status.
2. **Given** a blocked sanctions case, **When** no analyst disposition exists, **Then** the customer cannot proceed with onboarding regardless of other verification status.
3. **Given** an analyst clearing a sanctions alert as false positive, **When** they complete required documentation, **Then** the system calls Spriggy's onboarding service API to remove the block and the customer can proceed.

### User Story 7 - PEP High-Confidence Hit Triggers Enhanced Due Diligence (Priority: P1)

A high-confidence PEP screening hit (GreenID confidence score above configurable threshold, default 80%) blocks onboarding until an analyst reviews and completes the structured EDD checklist. The case documents what EDD was applied before the customer can proceed.

**Why this priority**: PEP handling with EDD is a regulatory requirement. High-confidence matches require human review and documented EDD before relationship establishment.

**Independent Test**: Create a case from high-confidence PEP hit (score > threshold). Verify onboarding is blocked, analyst can access and complete the structured EDD checklist (source of wealth, source of funds, relationship purpose, enhanced monitoring frequency), and block is removed only after EDD completion.

**Acceptance Scenarios**:
1. **Given** a PEP screening hit with confidence score above the configured threshold (default 80%), **When** the case is created, **Then** onboarding is blocked via API callback and case type is "PEP - EDD Required".
2. **Given** an analyst reviewing a high-confidence PEP case, **When** they access EDD documentation, **Then** they see a structured checklist requiring: source of wealth, source of funds, relationship purpose, and enhanced monitoring frequency.
3. **Given** EDD checklist completion on a PEP case, **When** the analyst submits with all mandatory fields completed, **Then** the onboarding block is removed via API callback and the EDD decision is recorded with full attribution.

### User Story 8 - Low-Confidence PEP Allows Provisional Onboarding (Priority: P2)

A low-confidence PEP hit (GreenID confidence score at or below configurable threshold) creates a case for parallel review but allows the customer to proceed with onboarding provisionally. The analyst review happens in parallel rather than blocking.

**Why this priority**: This is a business efficiency consideration. While important for customer experience, the system can operate Day 1 with manual handling of low-confidence cases.

**Independent Test**: Create a low-confidence PEP case (score <= threshold). Verify customer can proceed with onboarding (no blocking API call) while case remains open. Confirm case still requires analyst resolution.

**Acceptance Scenarios**:
1. **Given** a PEP screening hit with confidence score at or below the configured threshold (default 80%), **When** the case is created, **Then** case type is "PEP - Provisional Review" and no onboarding block API callback is made.
2. **Given** a provisional PEP case, **When** an analyst reviews and confirms false positive, **Then** the case closes without affecting the established customer relationship.
3. **Given** a provisional PEP case, **When** an analyst determines EDD is required, **Then** the customer relationship is flagged for ongoing enhanced monitoring.

### User Story 9 - SLA Breach Triggers Automatic Escalation (Priority: P1)

A KYC remediation case approaches its 5 business day SLA. The system sends warning notifications at defined thresholds. Upon breach, the case automatically escalates and notifies management.

**Why this priority**: SLA enforcement is critical for regulatory compliance. AUSTRAC expects timely case resolution; automatic escalation ensures visibility into aging cases before they become compliance failures.

**Independent Test**: Create a case and advance system time toward SLA deadline. Verify warning notification at threshold, automatic escalation upon breach, and management notification.

**Acceptance Scenarios**:
1. **Given** a case approaching SLA deadline, **When** the warning threshold is reached (configurable, default 80%), **Then** the assigned analyst receives a warning notification.
2. **Given** a case that has breached SLA, **When** the breach is detected, **Then** the case is automatically escalated and the AML Compliance Manager is notified.
3. **Given** SLA calculations, **When** computing time remaining, **Then** only Australian business days are counted (excluding weekends and national holidays).

### User Story 10 - Read-Only User Exports Cases for Governance Reporting (Priority: P2)

A member of the Risk Committee needs to review AML case statistics for the quarterly board report. They access the system with read-only credentials, view case summaries and metrics, and export data for their committee presentation.

**Why this priority**: Governance reporting is required but can use interim manual processes for Day 1 if needed. Systematic export capability improves efficiency but is not blocking.

**Independent Test**: Create cases across different types and statuses. Log in as read-only user. Verify they can view cases and reports but cannot edit. Test export functionality produces usable output.

**Acceptance Scenarios**:
1. **Given** a Read-Only user logging into the system, **When** they access the case list, **Then** they can view all cases but see no edit, close, or action buttons.
2. **Given** a Read-Only user viewing reports, **When** they access operational dashboards, **Then** they see case volumes, SLA compliance, and risk metrics.
3. **Given** a Read-Only user selecting cases for export, **When** they initiate export, **Then** they receive a formatted report suitable for committee presentation.

### User Story 11 - Analyst Records AUSTRAC Reference Number After Manual Submission (Priority: P1)

After manually submitting an approved SMR via AUSTRAC Online, an analyst returns to the system to record the AUSTRAC reference number, completing the filing record. Once approved, the SMR cannot be withdrawn; any new information requires a supplementary filing.

**Why this priority**: Reference number recording closes the compliance loop. Without this, the system cannot demonstrate that approved SMRs were actually filed with AUSTRAC.

**Independent Test**: Create an approved SMR case. Verify analyst can access reference number entry form, input is validated, and submission updates case to "Filed" status with the reference recorded. Verify no withdrawal option is available for approved SMRs.

**Acceptance Scenarios**:
1. **Given** an approved SMR awaiting AUSTRAC submission, **When** an analyst accesses the case, **Then** they see a "Record AUSTRAC Reference" option but no option to withdraw or cancel the approved SMR.
2. **Given** an analyst entering an AUSTRAC reference number, **When** they submit, **Then** the case status changes to "SMR Filed" and the reference is recorded in the audit trail.
3. **Given** an SMR without recorded reference number beyond the 3 business day SLA, **When** the deadline passes, **Then** the system flags the case and notifies management.

### User Story 12 - Dashboard Shows Analyst Workload and Priorities (Priority: P1)

An L1 Analyst logs in and sees their dashboard showing assigned cases ordered by SLA urgency, with visual indicators for approaching deadlines and case types requiring immediate attention. Cases with equal SLA urgency are ordered by creation date (oldest first).

**Why this priority**: Operational efficiency is essential for a small team managing compliance workload. Without clear prioritization, analysts may miss urgent items among routine work.

**Independent Test**: Create multiple cases with varying SLAs and types assigned to a test user. Log in and verify dashboard displays correct prioritization (SLA urgency first, then creation date FIFO), SLA indicators, and case counts.

**Acceptance Scenarios**:
1. **Given** an analyst logging into the system, **When** they view their dashboard, **Then** they see their assigned cases ordered by SLA urgency (most urgent first), with cases of equal urgency ordered by creation date (oldest first).
2. **Given** cases with different SLA states, **When** displayed on dashboard, **Then** visual indicators distinguish approaching deadline (warning) from breached (critical).
3. **Given** an analyst dashboard, **When** new cases are assigned, **Then** the dashboard updates to reflect the new assignment and adjusted workload.

### User Story 13 - L1 Analyst Closes Case with Satisfactory Explanation (Priority: P1)

An L1 Analyst reviews a customer's response to an information request and determines the explanation satisfactorily addresses the compliance concern. They document their assessment reasoning and close the case, understanding their decision is subject to L2 review.

**Why this priority**: L1 closure authority for satisfactory explanations is essential for workflow efficiency. Without this, all cases would require L2 review, creating bottlenecks.

**Independent Test**: Create a case where customer has responded to an information request. Verify L1 can document their assessment reasoning, close the case, and the closure is flagged as subject to L2 review.

**Acceptance Scenarios**:
1. **Given** an L1 Analyst with a case where customer has responded, **When** they select "Close with Satisfactory Explanation", **Then** they see a mandatory documentation form requiring their assessment of why the explanation is satisfactory.
2. **Given** an L1 Analyst completing closure documentation, **When** they submit with documented reasoning, **Then** the case closes and is flagged as available for L2 quality review.
3. **Given** an L2 Analyst reviewing L1 closure decisions, **When** they access the quality review queue, **Then** they can see L1-closed cases with the closure reasoning and can reopen if they disagree with the assessment.

### User Story 14 - Cases Reassigned When Analyst Role Changes (Priority: P2)

An L1 Analyst is promoted to L2. All cases currently assigned to them are returned to the unassigned queue for reassignment, ensuring no cases are orphaned during role transitions.

**Why this priority**: Role change handling ensures operational continuity. While role changes are infrequent, failing to handle them could leave cases stranded.

**Independent Test**: Assign multiple cases to a test analyst. Change their role in the system. Verify all assigned cases are moved to unassigned queue and the role change is recorded in each case's audit trail.

**Acceptance Scenarios**:
1. **Given** an analyst with assigned cases, **When** their system role is changed, **Then** all their assigned cases are moved to the unassigned queue for reassignment.
2. **Given** cases returned to queue due to role change, **When** a supervisor views the queue, **Then** each case shows an audit entry noting "Unassigned due to analyst role change".
3. **Given** a role change occurring, **When** the cases are reassigned, **Then** no case history is lost and the full timeline remains accessible.

### User Story 15 - System Handles Simultaneous Sanctions and PEP Hits (Priority: P2)

During customer onboarding, GreenID returns both a sanctions match and a PEP match for the same customer. The system creates a single Sanctions case (as sanctions takes precedence) but captures the PEP details within that case for analyst awareness.

**Why this priority**: Handling overlapping screening results prevents duplicate case confusion while ensuring the more severe concern (sanctions) drives the workflow.

**Independent Test**: Simulate a GreenID webhook with both sanctions and PEP hit data for the same customer. Verify a single Sanctions case is created, PEP details are captured in the case, and onboarding is blocked.

**Acceptance Scenarios**:
1. **Given** a customer application triggering both sanctions and PEP screening hits, **When** the system receives the alerts, **Then** a single case is created with type "Sanctions - Pending Review" and the PEP hit details are captured as additional context.
2. **Given** an analyst reviewing a combined sanctions/PEP case, **When** they view the case details, **Then** they see both the sanctions match information and the PEP match information clearly identified.
3. **Given** the analyst clears the sanctions concern, **When** they complete the case, **Then** the PEP information remains documented and the case can indicate whether separate PEP follow-up is warranted.

### User Story 16 - L2 Analyst Overturns L1 Closure Decision (Priority: P1)

An L2 Analyst reviewing L1 closure decisions for quality assurance disagrees with an L1's assessment that a customer explanation was satisfactory. The L2 reopens the case to their own queue and takes over the investigation.

**Why this priority**: Quality oversight is essential for regulatory compliance. L2 must have authority to overturn L1 decisions when the closure reasoning is insufficient or the suspicion indicators were missed.

**Independent Test**: Create a case closed by L1 with satisfactory explanation. Verify L2 can access the quality review queue, view the closure reasoning, reopen the case to their own queue, and the L1 closure is overturned with full audit trail.

**Acceptance Scenarios**:
1. **Given** an L2 Analyst reviewing the quality review queue, **When** they select an L1-closed case to review, **Then** they see the complete case history including L1's closure reasoning and all prior documentation.
2. **Given** an L2 Analyst who disagrees with an L1 closure, **When** they select "Reopen Case", **Then** the case is assigned to their own queue, the status changes from "Closed" to "In Progress", and the L1 closure is overturned.
3. **Given** a case reopened by L2, **When** viewing the audit trail, **Then** it shows the L2 analyst, timestamp, and that the case was "Reopened from L1 closure - assigned to L2 for investigation".

### User Story 17 - Existing Customer Triggers Post-Onboarding Sanctions Alert (Priority: P1)

An existing Spriggy customer triggers a sanctions alert during ongoing screening (not during onboarding). The system creates a case for analyst review but does not automatically block the customer's account; the analyst decides whether account restrictions are warranted based on investigation.

**Why this priority**: Ongoing sanctions monitoring is a regulatory requirement. Unlike onboarding, existing customers require human judgment on account restrictions to balance compliance with customer impact.

**Independent Test**: Simulate a sanctions alert for an existing customer (not in onboarding flow). Verify case is created without automatic account block. Verify analyst has option to recommend account restrictions after investigation.

**Acceptance Scenarios**:
1. **Given** an existing customer (onboarding complete), **When** ongoing screening triggers a sanctions alert, **Then** a case is created with type "Sanctions - Existing Customer" and no automatic account block is applied.
2. **Given** an analyst investigating a post-onboarding sanctions case, **When** they determine the alert is a false positive, **Then** they can close the case without any account restrictions being applied.
3. **Given** an analyst investigating a post-onboarding sanctions case, **When** they determine account restrictions are warranted, **Then** they can document their recommendation and escalate for AML Compliance Manager decision on restrictions.

### User Story 18 - Supplementary SMR Filing for Filed Cases (Priority: P1)

After an SMR has been filed with AUSTRAC, new relevant information emerges about the same matter. The analyst creates a new linked case that follows the full SMR workflow (L2 recommendation, Manager approval) while maintaining the connection to the original filed SMR.

**Why this priority**: Supplementary filings are a regulatory requirement when new information emerges after initial SMR. The system must support this workflow to maintain compliance.

**Independent Test**: Create a case with filed SMR status. Verify analyst can create a new linked case for supplementary filing. Verify the new case follows full SMR workflow and displays link to original case.

**Acceptance Scenarios**:
1. **Given** a case with status "SMR Filed", **When** an analyst selects "Create Supplementary Filing", **Then** a new case is created with type "Supplementary SMR" and a visible link to the original case.
2. **Given** a supplementary SMR case, **When** the analyst completes investigation, **Then** the case follows the standard SMR workflow: L2 recommendation, Manager approval, draft generation, manual submission, reference recording.
3. **Given** a supplementary SMR case, **When** viewing either the original or supplementary case, **Then** the system displays the relationship between the linked cases with navigation to view both.

---

## Edge Cases

### EC-001: Concurrent Case Action by Multiple Users
Two analysts attempt to action the same case simultaneously (e.g., both try to close or escalate). The system must prevent conflicting operations.
- **Handling**: Implement optimistic locking. First submission succeeds; second receives conflict notification with option to refresh and review changes.

### EC-002: External Service Unavailable During Screening
GreenID or Indue is unreachable when processing a screening request or receiving an alert.
- **Handling**: Apply circuit breaker pattern (open after 5 failures). Queue the operation for retry with exponential backoff. Alert operations team. Do not block user workflows for transient failures.

### EC-003: SMR Approval After Recommending Analyst Role Change
An L2 Analyst who created an SMR recommendation is promoted to AML Compliance Manager before the SMR is approved.
- **Handling**: System must prevent users from approving their own recommendations regardless of current role. Track original recommender and enforce segregation.

### EC-004: Customer Responds After Case Auto-Escalated
Customer provides requested information after a case has been escalated due to SLA breach.
- **Handling**: The escalated case owner (now higher tier) can still process the response. Create audit entry noting response received post-escalation. Do not auto-de-escalate.

### EC-005: Duplicate Screening Alerts for Same Customer
GreenID sends multiple alerts for the same customer and screening type within a short period (duplicate webhooks or re-screening).
- **Handling**: Detect duplicates by customer ID and alert type within configurable window (default 24 hours). Create single case, link duplicate alerts. Flag for analyst awareness.

### EC-006: Case Assignment When All Analysts Unavailable
A new alert arrives but all analysts of the appropriate tier are on leave or unavailable.
- **Handling**: Case enters unassigned queue. Trigger immediate escalation notification to AML Compliance Manager. Dashboard highlights unassigned cases prominently.

### EC-007: System Clock Discrepancy Affecting SLA Calculations
Server time drifts or is incorrectly configured, affecting SLA deadline calculations.
- **Handling**: All timestamps use UTC with timezone conversion for display. SLA calculations reference authoritative time source. Audit trail includes raw UTC timestamps.

### EC-008: Mid-Investigation Customer Account Closure
Customer closes their Spriggy account while an investigation is active.
- **Handling**: Investigation continues to completion regardless of account status. Case cannot be auto-closed. Flag case with "Customer Account Closed" indicator.

### EC-009: Onboarding Block API Callback Failure
The API callback to Spriggy's onboarding service fails when applying or clearing a block.
- **Handling**: Apply circuit breaker pattern. Queue for retry with exponential backoff. Alert operations team. Case status reflects intended block state with "Pending Sync" indicator until callback succeeds.

### EC-010: Multiple SMR Rejections for Same Case
AML Compliance Manager repeatedly rejects SMR recommendations for a case.
- **Handling**: No system-imposed limit on resubmissions. L2 can revise and resubmit indefinitely. Resolution of persistent disagreements occurs through discussion outside the system. Each rejection and resubmission is recorded in audit trail.

### EC-011: PEP Confidence Score Exactly at Threshold
GreenID returns a PEP confidence score exactly equal to the configured threshold (e.g., exactly 80%).
- **Handling**: Score equal to threshold is treated as low-confidence (provisional proceed). Only scores strictly above threshold trigger blocking EDD requirement.

### EC-012: L2 Reopens Case After L1 Has Left Organization
An L2 Analyst reviews and disagrees with an L1 closure, but the original L1 analyst has since left the organization.
- **Handling**: L2 can still reopen the case to their own queue. Audit trail preserves original L1 closure decision. No action required from departed analyst.

### EC-013: Supplementary SMR for Case with Multiple Prior Filings
New information emerges for a matter that has already had multiple supplementary SMR filings.
- **Handling**: Create new linked case referencing all prior filings. Display complete filing history showing chain of original and all supplementary cases.

### EC-014: Ongoing Screening Alert During Active Investigation
An existing customer triggers a new screening alert while they already have an open case under investigation.
- **Handling**: Create new case for the new alert. Link to existing open case for analyst awareness. Analyst decides whether to consolidate or investigate separately.

---

## Functional Requirements

### Case Lifecycle

- **FR-001**: System MUST create cases automatically when receiving screening alerts from GreenID or transaction monitoring alerts from Indue.
- **FR-002**: System MUST NOT allow manual case creation; all cases MUST originate from system integrations.
- **FR-003**: System MUST assign each case a unique, sequential case reference number.
- **FR-004**: System MUST categorize cases into one of three types: KYC Remediation, PEP/Sanctions Screening, or Suspicious Activity.
- **FR-005**: System MUST track case status through defined states: Open, In Progress, Pending Information, Escalated, Pending Approval, Closed, SMR Filed.
- **FR-006**: System MUST record state transitions with timestamp, user attribution, and documented reasoning.
- **FR-007**: System MUST NOT enforce a maximum case age; aged cases MUST be surfaced through reporting for management attention.

### Tiered Workflow

- **FR-008**: System MUST enforce tiered workflow with L1 Triage, L2 Investigation, and AML Compliance Manager approval levels.
- **FR-009**: L1 Analysts MUST be able to close cases as false positives with mandatory documentation.
- **FR-010**: L1 Analysts MUST be able to request customer information using pre-approved templates.
- **FR-011**: L1 Analysts MUST be able to close cases with satisfactory explanation when customer provides requested information, with mandatory documentation of their assessment reasoning.
- **FR-012**: L1 closure decisions with satisfactory explanation MUST be flagged as subject to L2 quality review.
- **FR-013**: L1 Analysts MUST be able to escalate cases to L2 with documented reasoning.
- **FR-014**: L1 Analysts MUST NOT be able to create or recommend SMRs.
- **FR-015**: L1 Analysts MUST NOT be able to close cases without completing required documentation.
- **FR-016**: L1 Analysts MUST NOT be able to override sanctions blocks.
- **FR-017**: L2 Analysts MUST have all L1 capabilities plus full investigation and SMR recommendation authority.
- **FR-018**: L2 Analysts MUST be able to review L1 closure decisions through a dedicated quality review queue.
- **FR-019**: L2 Analysts MUST be able to reopen L1-closed cases to their own queue, overturning the L1 closure decision.
- **FR-020**: L2 Analysts MUST NOT be able to approve their own SMR recommendations.
- **FR-021**: AML Compliance Manager MUST be able to approve or reject SMR recommendations.
- **FR-022**: AML Compliance Manager MUST be able to override case decisions with documented reasoning.
- **FR-023**: System MUST NOT impose a limit on SMR recommendation resubmissions after rejection.

### Case Prioritization

- **FR-024**: System MUST order cases by SLA urgency (most urgent first).
- **FR-025**: System MUST order cases with equal SLA urgency by creation date (oldest first, FIFO).

### Role Change Handling

- **FR-026**: System MUST return all assigned cases to the unassigned queue when an analyst's role changes.
- **FR-027**: System MUST record role change reassignment in each affected case's audit trail.

### Sanctions and PEP Handling - Onboarding

- **FR-028**: System MUST notify Spriggy's onboarding service via API callback when an onboarding block is applied or cleared.
- **FR-029**: System MUST block customer onboarding when a sanctions screening hit is received during onboarding until analyst disposition.
- **FR-030**: System MUST classify PEP screening hits using GreenID's numeric confidence score against a configurable threshold (default 80%).
- **FR-031**: System MUST block customer onboarding for PEP hits with confidence score strictly above the threshold until EDD is documented and approved.
- **FR-032**: System SHOULD allow provisional onboarding for PEP hits with confidence score at or below the threshold while creating a parallel review case.
- **FR-033**: System MUST provide a structured EDD checklist requiring: source of wealth, source of funds, relationship purpose, and enhanced monitoring frequency.
- **FR-034**: System MUST record completed EDD checklist before allowing PEP-flagged customer to proceed.
- **FR-035**: When simultaneous sanctions and PEP hits occur for the same customer, System MUST create a single Sanctions case and capture PEP details within that case.

### Sanctions Handling - Existing Customers

- **FR-036**: System MUST create a case without automatic account block when an existing customer (onboarding complete) triggers a sanctions screening alert.
- **FR-037**: System MUST distinguish between onboarding sanctions cases (automatic block) and existing customer sanctions cases (no automatic block) through case type.
- **FR-038**: System MUST allow analysts to document and recommend account restrictions for existing customer sanctions cases after investigation.

### SMR Process

- **FR-039**: System MUST capture SMR recommendation details including narrative, evidence references, and reason for suspicion.
- **FR-040**: System MUST generate SMR-formatted draft documents upon manager approval.
- **FR-041**: System MUST provide capability to record AUSTRAC reference number after manual submission.
- **FR-042**: System MUST track SMR filing SLA (3 business days from approval).
- **FR-043**: System MUST NOT allow withdrawal of approved SMRs; new information MUST be handled through supplementary filing.

### Supplementary SMR Filing

- **FR-044**: System MUST allow creation of supplementary SMR cases linked to a previously filed SMR case.
- **FR-045**: Supplementary SMR cases MUST follow the standard SMR workflow: L2 recommendation, Manager approval, draft generation, reference recording.
- **FR-046**: System MUST display bidirectional links between original SMR cases and their supplementary cases.
- **FR-047**: System MUST support multiple supplementary filings for a single original SMR case.

### SLA Management

- **FR-048**: System MUST calculate SLAs using Australian business days, excluding weekends and national holidays.
- **FR-049**: System MUST apply configured SLA timelines: KYC remediation 5 days, PEP/Sanctions triage 24 hours, Suspicious activity triage 48 hours, SMR filing 3 days.
- **FR-050**: System MUST send warning notifications when cases approach SLA deadline (configurable threshold, default 80%).
- **FR-051**: System MUST automatically escalate cases when SLA is breached.
- **FR-052**: System MUST notify AML Compliance Manager of SLA breaches.

### Customer Communication

- **FR-053**: System MUST provide pre-approved communication templates for customer outreach.
- **FR-054**: Communication templates MUST be static and changed only through code deployments with AML Compliance Manager review.
- **FR-055**: System MUST record all customer communications in the case timeline with timestamp and content.
- **FR-056**: System MUST capture customer responses and analyst assessment of responses.
- **FR-057**: System MUST NOT allow L1 closure without documented customer communication when information was requested.

### Audit Trail

- **FR-058**: System MUST record all case actions immutably with timestamp and user attribution.
- **FR-059**: System MUST record all case read access (views) with user and timestamp.
- **FR-060**: System MUST retain all case data and audit records for minimum 7 years.
- **FR-061**: System MUST NOT allow deletion of case records or audit entries.
- **FR-062**: System MUST generate complete audit history exportable for regulatory inspection.

### Access Control

- **FR-063**: System MUST enforce four distinct roles: L1 Analyst, L2 Analyst, AML Compliance Manager, Read-Only.
- **FR-064**: System MUST restrict Read-Only users to viewing and exporting only; no case modifications permitted.
- **FR-065**: System MUST log all access and action attempts including denied operations.

### Notifications

- **FR-066**: System MUST send email notifications for case assignments.
- **FR-067**: System MUST send email notifications for SLA warnings and breaches.
- **FR-068**: System MUST send email notifications for escalations requiring attention.
- **FR-069**: System SHOULD provide in-system dashboard notifications for all alert types.

### Reporting

- **FR-070**: System MUST provide operational reports showing case volumes by type, open count, aging, and SLA compliance.
- **FR-071**: System MUST provide risk reports showing SMR filing volumes, screening hit rates, and false positive rates.
- **FR-072**: System MUST allow report export for governance committee presentation.
- **FR-073**: System MUST surface aged cases in reporting for management visibility (no maximum age enforcement).

---

## Key Entities

### Case
The central work item representing an investigation or remediation task requiring analyst action.

**Attributes:**
- Unique reference number
- Case type (KYC, PEP/Sanctions, Suspicious Activity, Supplementary SMR)
- Case subtype (Sanctions-Onboarding, Sanctions-Existing Customer, PEP-EDD Required, PEP-Provisional Review)
- Current status
- Priority/urgency level
- SLA deadline
- Source (GreenID, Indue) - manual creation not permitted
- Creation and last modified timestamps
- PEP confidence score (when applicable)
- Combined alert indicator (for simultaneous sanctions/PEP hits)
- Linked case references (for supplementary SMR filings)

**Relationships:**
- Belongs to one Customer
- Has one current Assignment (to an Analyst)
- Has many Timeline Entries
- May have one SMR Recommendation
- Has many Document attachments
- May link to other Cases (original/supplementary relationship)

### Customer
The Spriggy customer who is the subject of a case.

**Attributes:**
- Customer identifier
- Name
- Account status
- Onboarding status
- Risk classification

**Relationships:**
- Has many Cases
- May have onboarding Blocks

### Assignment
Tracks which analyst is responsible for a case at any point in time.

**Attributes:**
- Assigned user
- Assignment timestamp
- Assignment reason (initial, escalation, reassignment, role change, L2 reopen)

**Relationships:**
- Belongs to one Case
- Belongs to one User (Analyst)

### Timeline Entry
An immutable record of an action, event, or note on a case.

**Attributes:**
- Entry type (action, note, system event, communication, view, closure, reopen)
- Content/description
- Timestamp
- Acting user (or system for automated entries)

**Relationships:**
- Belongs to one Case

### SMR Recommendation
A recommendation to file a Suspicious Matter Report, requiring manager approval.

**Attributes:**
- Narrative description
- Reason for suspicion
- Evidence references
- Recommendation status (pending, approved, rejected)
- Recommending analyst
- Rejection count and history
- Approval/rejection timestamp
- Approving manager (if approved)
- AUSTRAC reference number (if filed)
- Supplementary indicator (if linked to prior filing)

**Relationships:**
- Belongs to one Case

### Communication Template
Pre-approved scripted content for customer outreach.

**Attributes:**
- Template name
- Template content with placeholders
- Applicable case types
- Active/inactive status
- Deployment version (managed through code deployments)

**Relationships:**
- Used by many Customer Communications

### Customer Communication
A record of outreach to or response from a customer.

**Attributes:**
- Communication direction (outbound/inbound)
- Channel used (email, in-app, phone)
- Content
- Timestamp
- Analyst assessment of response (if applicable)

**Relationships:**
- Belongs to one Case
- May use one Communication Template

### User
A system user who can access cases and perform actions based on their role.

**Attributes:**
- Username/identifier
- Email
- Role (L1, L2, Manager, ReadOnly)
- Active status
- Role change history

**Relationships:**
- Has many Assignments
- Has many Timeline Entries (as actor)

### Onboarding Block
A hold preventing customer onboarding completion due to compliance screening result.

**Attributes:**
- Block type (Sanctions, PEP-EDD-Required)
- Block reason
- Created timestamp
- Cleared timestamp (if cleared)
- Clearing analyst
- Sync status (synced, pending sync - for API callback tracking)

**Relationships:**
- Belongs to one Customer
- Associated with one Case

### EDD Checklist
Structured documentation of Enhanced Due Diligence measures applied to a PEP case.

**Attributes:**
- Source of wealth documentation
- Source of funds documentation
- Relationship purpose
- Enhanced monitoring frequency
- Completion timestamp
- Completing analyst

**Relationships:**
- Belongs to one Case

### PEP Confidence Threshold Configuration
System configuration for PEP classification.

**Attributes:**
- Threshold value (default 80%)
- Effective date
- Changed by user

**Relationships:**
- Applied to PEP screening evaluations

### Case Link
Represents a relationship between two cases, particularly for supplementary SMR filings.

**Attributes:**
- Link type (supplementary-to-original, related)
- Source case reference
- Target case reference
- Created timestamp
- Created by user

**Relationships:**
- Connects two Cases

---

## Success Criteria

- **SC-001**: All SMR-worthy cases are identified, investigated, and filed within regulatory timeframes, with zero missed filings in the first 6 months of operation.
- **SC-002**: 95% of cases are resolved within their defined SLA timelines.
- **SC-003**: Audit demonstrates complete traceability for 100% of cases, with no gaps in documentation or attribution.
- **SC-004**: Sanctions-flagged customers are blocked from onboarding in 100% of cases until analyst clearance.
- **SC-005**: Segregation of duties is maintained with zero instances of analysts approving their own SMR recommendations.
- **SC-006**: Governance reporting is delivered on schedule for all Risk Committee and Board meetings.
- **SC-007**: All case views are logged in audit trail, enabling regulatory demonstration of access patterns.
- **SC-008**: PEP confidence thresholds correctly classify 100% of PEP hits as high-confidence (blocking) or low-confidence (provisional) based on configured threshold.
- **SC-009**: L2 quality review identifies and corrects insufficient L1 closure decisions, with zero regulatory findings related to improper case closures.
- **SC-010**: Post-onboarding sanctions alerts are investigated with appropriate analyst discretion on account restrictions, maintaining customer trust while ensuring compliance.

---

## Assumptions

| ID | Assumption | Rationale |
|----|------------|-----------|
| A1 | GreenID integration exists and can be extended to send screening results with numeric confidence scores to this system | Context states GreenID is existing integration; user confirmed confidence scores are available |
| A2 | Indue transaction monitoring alerts can be delivered via webhook or file transfer | Context states Indue is existing banking partner with alert capability |
| A3 | Australian public holiday calendar will be maintained by operations team | SLA calculations require accurate holiday data; assuming manual maintenance initially |
| A4 | Initial analyst team size is small (under 10) and can share a single queue per tier | No specific team size provided; designing for small team with growth flexibility |
| A5 | Email is the primary notification channel for Day 1 | Context specifies Slack is Phase 2; email handles all notifications initially |
| A6 | SMR document format follows standard AUSTRAC specifications available publicly | SMR generation requires known format; assuming standard format available |
| A7 | Customer communication occurs through existing Spriggy channels, not through this system | System records communications but does not send them; uses existing email/app/phone |
| A8 | Single-tenant deployment serving only Spriggy | No mention of multi-tenancy; assuming dedicated instance |
| A9 | GreenID provides ongoing monitoring capability for existing customers | User answer: validate capability exists; if unavailable, batch rescreening will be added to scope |
| A10 | Spriggy's onboarding service has an API endpoint capable of receiving block/unblock callbacks | User confirmed API callback approach for integration |
| A11 | Communication templates will be version-controlled in code repository | User confirmed static templates changed through code deployments |
| A12 | L2 quality review of L1 closures is a sampling/audit process, not mandatory for every closure | Implicit from user answer about L1 judgment being "subject to L2 review" |
| A13 | Existing customer account restrictions require AML Compliance Manager approval after analyst recommendation | User confirmed analyst decides on restrictions; assuming manager approval for actual restriction action |
| A14 | Supplementary SMR filings are relatively rare (less than 10% of filed SMRs) | Workflow designed to handle them but not optimized for high volume |

---

## Open Questions

| ID | Question | Impact | Suggested Default |
|----|----------|--------|-------------------|
| OQ-001 | Can GreenID provide ongoing/periodic rescreening for existing customers, or is batch rescreening required? | Affects ongoing monitoring implementation; may require additional integration work | Validate with GreenID vendor; add batch rescreening to scope if unavailable |
| OQ-002 | What are the specific SLA warning thresholds (e.g., warn at 50%, 75%, 90% of deadline)? | Affects notification timing configuration | Default to single 80% warning threshold |
| OQ-003 | What authentication system will users access the platform through (SSO, local auth, etc.)? | Affects user management and security implementation | Assume integration with existing Spriggy SSO |
| OQ-004 | Are there specific AUSTRAC SMR format requirements or templates that must be used? | Affects SMR document generation feature | Research AUSTRAC documentation for required format |
| OQ-005 | What is the expected case volume (daily/weekly) for capacity planning? | Affects queue design, assignment logic, and performance requirements | Design for 50-100 cases per day initially |
| OQ-006 | What customer information is available from existing systems for case context? | Affects case display and investigation efficiency | Assume basic profile, account, and transaction history available |
| OQ-007 | What is the API contract for Spriggy's onboarding service block/unblock endpoint? | Required for integration implementation | Work with Spriggy engineering to define contract |
| OQ-008 | What percentage of L1 closures should L2 review for quality assurance? | Affects L2 workload and quality process design | Default to 10% sampling rate |
| OQ-009 | What account restrictions are available for existing customer sanctions cases? | Affects analyst recommendation options and downstream integration | Define available restriction types with product team |

---
can we do the plan and get ready to build a demo?
