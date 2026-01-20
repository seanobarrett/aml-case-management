# Analyst Report

> Feature: 001-aml-case-management
> Iteration: 3
> Generated: 2026-01-13T09:15:00Z

---

## What I Created

| Metric | Count |
|--------|-------|
| User Stories | 18 |
| Edge Cases | 14 |
| Functional Requirements | 73 |
| Key Entities | 12 |
| Success Criteria | 10 |

### Summary

This iteration incorporated four clarifications from user feedback in Iteration 2:

1. **L2 Quality Review Disagreement (G21)**: Added User Story 16 specifying that when L2 disagrees with an L1 closure, L2 reopens the case to their own queue and takes over investigation. Added FR-018 and FR-019 to formalize the quality review queue and L2 reopen capability.

2. **Post-Onboarding Sanctions Handling (G22)**: Added User Story 17 for existing customer sanctions alerts, which create cases WITHOUT automatic account blocks (unlike onboarding). Added FR-036, FR-037, FR-038 under new "Sanctions Handling - Existing Customers" section. Added case subtype distinction.

3. **Supplementary SMR Filing Workflow (G28)**: Added User Story 18 for supplementary filings when new information emerges after SMR is filed. Added FR-044 through FR-047 under new "Supplementary SMR Filing" section. Added Case Link entity and updated Case entity with linked case references.

4. **GreenID Ongoing Monitoring (G27)**: Updated assumption A9 to note that capability must be validated with vendor, and batch rescreening will be added to scope if unavailable. Updated OQ-001 with clearer suggested default.

Additional refinements:
- Added 3 new edge cases (EC-012, EC-013, EC-014) to address scenarios arising from new functionality
- Added 2 new success criteria (SC-009, SC-010) covering L2 quality review and post-onboarding sanctions handling
- Added 2 new assumptions (A13, A14) for existing customer restrictions and supplementary filing volume
- Added 1 new open question (OQ-009) regarding available account restriction types

---

## Gap Resolutions

| Gap ID | Resolution |
|--------|------------|
| G21 (Important) | Added US-16 for L2 analyst overturning L1 closure. L2 reopens to own queue per user answer. Added FR-018 (quality review queue) and FR-019 (reopen capability). Updated Timeline Entry with "reopen" type. Updated Assignment with "L2 reopen" reason. |
| G22 (Important) | Added US-17 for post-onboarding sanctions alerts. Created new FR section "Sanctions Handling - Existing Customers" with FR-036 through FR-038. Case subtype distinguishes onboarding (auto-block) from existing customer (no auto-block). Added EC-014 for alert during active investigation. |
| G27 (Important) | Updated A9 to conditional assumption requiring vendor validation. Updated OQ-001 with explicit fallback: add batch rescreening to scope if GreenID ongoing monitoring unavailable. |
| G28 (Important) | Added US-18 for supplementary SMR filings. Created new FR section "Supplementary SMR Filing" with FR-044 through FR-047. Added Case Link entity for relationships. Updated Case entity with linked case references. Added EC-013 for multiple prior filings. |

---

## Changes from Iteration 2

### User Stories Added

| Story | Priority | Description |
|-------|----------|-------------|
| US-16 | P1 | L2 Analyst Overturns L1 Closure Decision |
| US-17 | P1 | Existing Customer Triggers Post-Onboarding Sanctions Alert |
| US-18 | P1 | Supplementary SMR Filing for Filed Cases |

### Functional Requirements Added

| FR | Section | Description |
|----|---------|-------------|
| FR-018 | Tiered Workflow | L2 quality review queue for L1 closures |
| FR-019 | Tiered Workflow | L2 can reopen L1-closed cases to own queue |
| FR-036 | Sanctions - Existing Customers | Case creation without auto-block for existing customers |
| FR-037 | Sanctions - Existing Customers | Case type distinction (onboarding vs existing) |
| FR-038 | Sanctions - Existing Customers | Analyst account restriction recommendation |
| FR-044 | Supplementary SMR Filing | Creation of linked supplementary cases |
| FR-045 | Supplementary SMR Filing | Full workflow for supplementary cases |
| FR-046 | Supplementary SMR Filing | Bidirectional case links |
| FR-047 | Supplementary SMR Filing | Multiple supplementary filings support |

### Edge Cases Added

| EC | Description |
|----|-------------|
| EC-012 | L2 reopens case after L1 has left organization |
| EC-013 | Supplementary SMR for case with multiple prior filings |
| EC-014 | Ongoing screening alert during active investigation |

### Success Criteria Added

| SC | Description |
|----|-------------|
| SC-009 | L2 quality review identifies and corrects insufficient L1 closures |
| SC-010 | Post-onboarding sanctions handled with appropriate analyst discretion |

### Entities Modified

| Entity | Changes |
|--------|---------|
| Case | Added case subtype attribute; added linked case references |
| Assignment | Added "L2 reopen" to assignment reason enum |
| Timeline Entry | Added "reopen" to entry type enum |
| SMR Recommendation | Added supplementary indicator |
| Case Link | New entity for case relationships |

---

## Assumptions Made

| ID | Assumption | Rationale |
|----|------------|-----------|
| A13 | Existing customer account restrictions require AML Compliance Manager approval after analyst recommendation | User confirmed analyst decides on restrictions; manager approval assumed for actual restriction implementation to maintain segregation of duties |
| A14 | Supplementary SMR filings are relatively rare (less than 10% of filed SMRs) | Workflow designed to handle them but volume optimization deferred; assumption allows simpler initial design |

---

## Notes

### Key Design Decisions

1. **Onboarding vs Existing Customer Distinction**: Created explicit case subtypes rather than a simple flag. This ensures the automatic blocking behavior is tied to case type at creation time and cannot be accidentally modified.

2. **L2 Reopen Ownership**: The user specified L2 "takes over" the case. This means the case is assigned to the specific L2 analyst who disagreed, not returned to a general L2 queue. This creates accountability for the overturn decision.

3. **Supplementary Filing as New Case**: Rather than extending the original case, supplementary filings create new linked cases. This preserves the integrity of the original filing record while enabling full workflow for the supplementary matter.

4. **Account Restrictions Left Open**: The user confirmed analysts decide on restrictions for existing customers, but the specific restriction types and downstream integration remain undefined. This is captured in OQ-009 for resolution before implementation.

### Requirement Renumbering

Due to the addition of new requirements in the middle of the document, the following renumbering occurred:
- Former FR-023 through FR-065 are now FR-024 through FR-073
- New FR-018, FR-019 inserted in Tiered Workflow section
- New FR-036 through FR-038 inserted as new "Sanctions - Existing Customers" section
- New FR-044 through FR-047 inserted as new "Supplementary SMR Filing" section

### Remaining Considerations for Devil's Advocate

- The L2 reopen workflow assumes L2 has capacity to take on cases they overturn. Consider workload implications.
- Existing customer sanctions cases do not auto-block, but there is no defined SLA for analyst decision on restrictions. Consider whether urgency requires expedited handling.
- Supplementary SMR cases follow full workflow including manager approval. Consider whether expedited approval is needed for urgent supplementary information.
- GreenID ongoing monitoring assumption (A9) remains conditional. Technical feasibility should be confirmed before planning phase.

---
