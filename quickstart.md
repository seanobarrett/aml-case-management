# AML Case Management API - Quickstart Guide

> Integration guide for the AML Case Management System API
> Feature ID: 001-aml-case-management
> Generated: 2026-01-18

---

## Overview

This guide provides practical examples for integrating with the AML Case Management API. It covers authentication, common user flows, webhook integration, and error handling patterns.

## Base URL

```
Production: https://aml.spriggy.com.au/api/v1
Staging: https://aml-staging.spriggy.com.au/api/v1
```

## Authentication

### User Authentication (OIDC SSO)

The API uses JWT Bearer tokens obtained through Spriggy's SSO. Include the token in all requests:

```bash
# All authenticated requests require the Authorization header
curl -X GET "https://aml.spriggy.com.au/api/v1/cases" \
  -H "Authorization: Bearer <access_token>" \
  -H "Content-Type: application/json"
```

### Webhook Authentication (HMAC)

Webhook endpoints use HMAC-SHA256 signature validation. When sending webhooks to the system:

```bash
# Generate HMAC signature
TIMESTAMP=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
BODY='{"alertId":"alert-123",...}'
SIGNATURE=$(echo -n "${TIMESTAMP}.${BODY}" | openssl dgst -sha256 -hmac "${SHARED_SECRET}" | awk '{print $2}')

curl -X POST "https://aml.spriggy.com.au/api/v1/webhooks/greenid" \
  -H "Content-Type: application/json" \
  -H "X-Signature-256: ${SIGNATURE}" \
  -H "X-Timestamp: ${TIMESTAMP}" \
  -d "${BODY}"
```

---

## Common User Flows

### Flow 1: L1 Analyst Triages a False Positive (US-1)

**Scenario**: L1 analyst reviews a PEP screening alert and determines it's a false positive.

```bash
# Step 1: Get current user's dashboard
curl -X GET "https://aml.spriggy.com.au/api/v1/dashboard/my-cases" \
  -H "Authorization: Bearer ${TOKEN}"

# Response:
# {
#   "data": [...],
#   "metrics": {"totalAssigned": 5, "atRisk": 1, "breached": 0}
# }
```

```bash
# Step 2: View unassigned queue
curl -X GET "https://aml.spriggy.com.au/api/v1/queue/unassigned?tier=L1" \
  -H "Authorization: Bearer ${TOKEN}"

# Response:
# {
#   "data": [
#     {
#       "id": "550e8400-e29b-41d4-a716-446655440000",
#       "referenceCode": "AML-1001",
#       "caseType": "PEP_SANCTIONS_SCREENING",
#       "status": "OPEN",
#       "slaStatus": "on_track",
#       ...
#     }
#   ]
# }
```

```bash
# Step 3: Claim the case
curl -X POST "https://aml.spriggy.com.au/api/v1/cases/550e8400-e29b-41d4-a716-446655440000/claim" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"version": 1}'

# Response includes full case details with version incremented
```

```bash
# Step 4: View case details
curl -X GET "https://aml.spriggy.com.au/api/v1/cases/550e8400-e29b-41d4-a716-446655440000" \
  -H "Authorization: Bearer ${TOKEN}"

# Note: This creates a CASE_VIEWED audit entry (FR-059)
```

```bash
# Step 5: Close as false positive
curl -X POST "https://aml.spriggy.com.au/api/v1/cases/550e8400-e29b-41d4-a716-446655440000/close" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "version": 2,
    "disposition": "FALSE_POSITIVE",
    "justification": "Name similarity match only. Customer John Smith (DOB 1985-03-15) does not match PEP entry for Jonathan Smith (DOB 1952-08-22). Different date of birth, different full name, no other matching identifiers."
  }'

# Response:
# {
#   "id": "550e8400-e29b-41d4-a716-446655440000",
#   "status": "CLOSED",
#   "closedAt": "2026-01-18T10:30:00Z",
#   "version": 3,
#   ...
# }
```

### Flow 2: L2 Analyst Investigates and Recommends SMR (US-4, US-5)

**Scenario**: L2 analyst investigates an escalated case and determines SMR is warranted.

```bash
# Step 1: Claim escalated case from L2 queue
curl -X GET "https://aml.spriggy.com.au/api/v1/cases?status=ESCALATED&tier=L2&assignedUserId=unassigned" \
  -H "Authorization: Bearer ${TOKEN}"
```

```bash
# Step 2: Claim the case
curl -X POST "https://aml.spriggy.com.au/api/v1/cases/${CASE_ID}/claim" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"version": 3}'
```

```bash
# Step 3: Document investigation findings (required before SMR)
curl -X POST "https://aml.spriggy.com.au/api/v1/cases/${CASE_ID}/investigation-findings" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "entitiesInvolved": [
      {
        "entityType": "PERSON",
        "name": "John Smith",
        "role": "Account holder",
        "notes": "Primary subject of investigation"
      },
      {
        "entityType": "BUSINESS",
        "name": "ABC Trading Pty Ltd",
        "role": "Recipient of funds",
        "notes": "Received 15 transfers totaling $45,000"
      }
    ],
    "transactionPatterns": [
      {
        "patternType": "Structuring",
        "description": "Multiple deposits just under $10,000 threshold over 3-week period",
        "dateRange": {"from": "2026-01-01", "to": "2026-01-21"},
        "totalAmount": 45000,
        "transactionCount": 15
      }
    ],
    "suspiciousIndicators": [
      {
        "indicatorCode": "STRUCTURING",
        "description": "Deposits structured to avoid reporting thresholds",
        "severity": "HIGH",
        "evidence": "15 cash deposits ranging from $2,800-$3,200 over 21 days"
      },
      {
        "indicatorCode": "SHELL_COMPANY",
        "description": "Recipient business has no visible legitimate operations",
        "severity": "MEDIUM",
        "evidence": "ABN search shows no business activity; address is virtual office"
      }
    ],
    "conclusion": "SUSPICIOUS_ACTIVITY_IDENTIFIED",
    "notes": "Pattern strongly indicates deliberate structuring to avoid CTR reporting. Recommend SMR filing."
  }'
```

```bash
# Step 4: Create SMR recommendation
curl -X POST "https://aml.spriggy.com.au/api/v1/cases/${CASE_ID}/smr-recommendation" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "narrative": "Investigation revealed a pattern of structured cash deposits designed to avoid Currency Transaction Reporting thresholds. Account holder John Smith made 15 cash deposits between $2,800 and $3,200 over a 21-day period (1 Jan 2026 to 21 Jan 2026), totaling $45,000. All funds were immediately transferred to ABC Trading Pty Ltd, a company with no visible legitimate business operations. The deposits occurred at multiple branch locations, suggesting deliberate structuring. This activity is consistent with money laundering indicators outlined in AUSTRAC guidance.",
    "reasonForSuspicion": "Structured cash deposits below reporting threshold with immediate transfer to shell company indicates potential money laundering. Customer has no business relationship that would explain cash-intensive activity.",
    "evidenceReferences": [
      "Transaction report 2026-01-01 to 2026-01-21",
      "ABN search results for ABC Trading Pty Ltd",
      "Customer profile showing employment as administrative assistant"
    ]
  }'

# Response:
# {
#   "id": "recommendation-uuid",
#   "status": "PENDING",
#   "recommendingUser": {"displayName": "Jane Investigator"},
#   ...
# }

# Case status changes to PENDING_APPROVAL
# Manager receives notification
```

### Flow 3: AML Manager Approves SMR (US-5)

**Scenario**: AML Compliance Manager reviews and approves an SMR recommendation.

```bash
# Step 1: View cases pending approval
curl -X GET "https://aml.spriggy.com.au/api/v1/cases?status=PENDING_APPROVAL" \
  -H "Authorization: Bearer ${TOKEN}"
```

```bash
# Step 2: Review the SMR recommendation
curl -X GET "https://aml.spriggy.com.au/api/v1/cases/${CASE_ID}/smr-recommendation" \
  -H "Authorization: Bearer ${TOKEN}"

# Response includes full narrative, evidence references, and recommending analyst
```

```bash
# Step 3: Review investigation findings
curl -X GET "https://aml.spriggy.com.au/api/v1/cases/${CASE_ID}/investigation-findings" \
  -H "Authorization: Bearer ${TOKEN}"
```

```bash
# Step 4: Approve the SMR
curl -X POST "https://aml.spriggy.com.au/api/v1/cases/${CASE_ID}/smr-recommendation/approve" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "approvalNotes": "Investigation thoroughly documented. Structuring pattern clearly established. Approved for AUSTRAC submission."
  }'

# Response:
# {
#   "id": "recommendation-uuid",
#   "status": "APPROVED",
#   "approvedAt": "2026-01-18T14:00:00Z",
#   "approvingUser": {"displayName": "Senior Manager"},
#   "smrDraftGenerated": true,
#   "smrDraftId": "draft-uuid"
# }
```

```bash
# Step 5: Download SMR draft for manual AUSTRAC submission
curl -X GET "https://aml.spriggy.com.au/api/v1/cases/${CASE_ID}/smr-draft" \
  -H "Authorization: Bearer ${TOKEN}" \
  -o smr_draft_AML-1001.pdf
```

### Flow 4: Record AUSTRAC Reference After Filing (US-11)

```bash
# After manual submission to AUSTRAC Online
curl -X POST "https://aml.spriggy.com.au/api/v1/cases/${CASE_ID}/smr-recommendation/record-reference" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "austracReferenceNumber": "SMR-2026-00012345"
  }'

# Response:
# {
#   "status": "FILED",
#   "austracReferenceNumber": "SMR-2026-00012345",
#   "austracFiledAt": "2026-01-18T15:30:00Z"
# }

# Case status changes to SMR_FILED
```

### Flow 5: Sanctions Block During Onboarding (US-6)

**Scenario**: GreenID sends sanctions alert, system blocks onboarding, analyst clears.

```bash
# Webhook received from GreenID (sent by GreenID system)
curl -X POST "https://aml.spriggy.com.au/api/v1/webhooks/greenid" \
  -H "Content-Type: application/json" \
  -H "X-Signature-256: ${HMAC_SIGNATURE}" \
  -H "X-Timestamp: 2026-01-18T10:00:00Z" \
  -d '{
    "alertId": "greenid-alert-123",
    "customerId": "cust-456",
    "alertType": "SANCTIONS",
    "matchData": {
      "matchedName": "John Smith",
      "matchedList": "OFAC SDN",
      "matchReasons": ["Name match", "Country match"]
    },
    "customerOnboardingStatus": "IN_PROGRESS",
    "timestamp": "2026-01-18T10:00:00Z"
  }'

# Response:
# {
#   "received": true,
#   "caseId": "case-uuid",
#   "caseReference": "AML-1002"
# }

# System automatically:
# 1. Creates case with type SANCTIONS_ONBOARDING
# 2. Creates OnboardingBlock with PENDING_SYNC status
# 3. Calls Spriggy onboarding API to apply block
```

```bash
# L2 analyst reviews and clears false positive
# (L1 cannot clear sanctions blocks - FR-016)

curl -X POST "https://aml.spriggy.com.au/api/v1/cases/${CASE_ID}/onboarding-block/clear" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "clearanceReason": "Confirmed false positive. Customer John Smith (Australian citizen, born 1985) does not match OFAC SDN entry for Johnathan Schmidt (German national, born 1960). Different nationality, different name spelling, different date of birth."
  }'

# Response:
# {
#   "id": "block-uuid",
#   "syncStatus": "SYNCED",  // or "PENDING_SYNC" if API temporarily unavailable
#   "clearedAt": "2026-01-18T11:00:00Z",
#   "clearedBy": {"displayName": "L2 Analyst"}
# }
```

### Flow 6: High-Confidence PEP Requires EDD (US-7)

**Scenario**: PEP hit with confidence > 80% requires EDD before onboarding proceeds.

```bash
# View case requiring EDD
curl -X GET "https://aml.spriggy.com.au/api/v1/cases/${CASE_ID}" \
  -H "Authorization: Bearer ${TOKEN}"

# Response shows:
# - caseSubtype: "PEP_EDD_REQUIRED"
# - pepConfidenceScore: 92.5
# - hasOnboardingBlock: true
# - hasEDDChecklist: false
```

```bash
# Submit EDD checklist
curl -X POST "https://aml.spriggy.com.au/api/v1/cases/${CASE_ID}/edd-checklist" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "sourceOfWealth": "Customer is a senior government official (Department of Finance). Salary of $280,000 per annum confirmed via employment letter dated 15 Jan 2026. No other significant wealth sources identified.",
    "sourceOfFunds": "Funds for account opening ($5,000) sourced from ANZ savings account in customers name. Bank statement provided showing funds accumulated from salary deposits over 6 months.",
    "relationshipPurpose": "Personal savings account for family expenses",
    "enhancedMonitoringFrequency": "QUARTERLY",
    "additionalNotes": "Customer cooperative and provided all requested documentation promptly. No adverse media identified."
  }'

# Response:
# {
#   "id": "edd-uuid",
#   "completedAt": "2026-01-18T12:00:00Z",
#   "completedBy": {"displayName": "Analyst"}
# }

# System automatically clears onboarding block
```

### Flow 7: L2 Quality Review of L1 Closure (US-16)

**Scenario**: L2 reviews and disagrees with an L1 closure decision.

```bash
# Step 1: View L2 quality review queue
curl -X GET "https://aml.spriggy.com.au/api/v1/queue/l2-review" \
  -H "Authorization: Bearer ${TOKEN}"

# Response: Cases closed by L1 with l2ReviewStatus = PENDING_REVIEW
```

```bash
# Step 2: Review the case (view full history)
curl -X GET "https://aml.spriggy.com.au/api/v1/cases/${CASE_ID}/timeline" \
  -H "Authorization: Bearer ${TOKEN}"

# See L1's closure reasoning in timeline
```

```bash
# Step 3a: If agree with closure
curl -X POST "https://aml.spriggy.com.au/api/v1/queue/l2-review/${CASE_ID}/accept" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "reviewNotes": "L1 assessment appropriate. Documentation sufficient."
  }'

# l2ReviewStatus -> REVIEWED_ACCEPTED
# Case remains CLOSED
```

```bash
# Step 3b: If disagree with closure (reopen)
curl -X POST "https://aml.spriggy.com.au/api/v1/cases/${CASE_ID}/reopen" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "version": 4,
    "reopenReason": "L1 closure documentation insufficient. Customer explanation does not adequately address the transaction pattern identified. Additional investigation required to determine if structuring occurred."
  }'

# Response:
# {
#   "status": "IN_PROGRESS",
#   "l2ReviewStatus": "REVIEWED_REOPENED",
#   "assignedUser": {"displayName": "L2 Analyst"},  // Assigned to reopening L2
#   "version": 5
# }
```

---

## Webhook Integration

### GreenID Webhook Format

```json
{
  "alertId": "greenid-12345",
  "customerId": "spriggy-customer-uuid",
  "alertType": "SANCTIONS | PEP",
  "confidenceScore": 85.5,
  "matchData": {
    "matchedName": "Name on watchlist",
    "matchedList": "OFAC SDN | PEP Database",
    "matchReasons": ["Name match", "DOB match"]
  },
  "customerOnboardingStatus": "IN_PROGRESS | COMPLETED",
  "timestamp": "2026-01-18T10:00:00Z"
}
```

### Indue Webhook Format

```json
{
  "alertId": "indue-67890",
  "customerId": "spriggy-customer-uuid",
  "alertType": "SUSPICIOUS_TRANSACTION | UNUSUAL_PATTERN | THRESHOLD_BREACH",
  "alertDetails": {
    "ruleTriggered": "STRUCTURING_DETECTION",
    "transactionIds": ["txn-1", "txn-2", "txn-3"],
    "totalAmount": 45000.00,
    "currency": "AUD"
  },
  "customerOnboardingStatus": "IN_PROGRESS | COMPLETED",
  "timestamp": "2026-01-18T10:00:00Z"
}
```

**Note on customerOnboardingStatus**: This optional field distinguishes between onboarding alerts (which may trigger automatic blocks) and existing customer alerts (which require analyst discretion on restrictions per FR-036/FR-037).

### Webhook Response Codes

| Status | Meaning | Action |
|--------|---------|--------|
| 202 | Accepted | Webhook processed, case created |
| 400 | Bad Request | Invalid payload format |
| 401 | Unauthorized | Invalid HMAC signature |
| 409 | Conflict | Duplicate webhook (linked to existing case) |

### Duplicate Handling

Webhooks for the same customer/alert-type within 24 hours return 409 with existing case reference:

```json
{
  "duplicate": true,
  "existingCaseId": "550e8400-e29b-41d4-a716-446655440000",
  "existingCaseReference": "AML-1001",
  "message": "Duplicate webhook linked to existing case"
}
```

---

## Error Handling

### Standard Error Format

All errors follow this format:

```json
{
  "code": "MACHINE_READABLE_CODE",
  "message": "Human-readable description",
  "details": {
    "additionalContext": "varies by error type"
  }
}
```

### Common Error Codes

| Code | Status | Description | Action |
|------|--------|-------------|--------|
| `VALIDATION_ERROR` | 400 | Invalid request format | Check request body |
| `UNAUTHORIZED` | 401 | Missing/invalid token | Refresh authentication |
| `FORBIDDEN` | 403 | Insufficient role | Contact admin |
| `TIER_MISMATCH` | 403 | L1 attempting action on L2-tier case | Use L2+ role or wait for L2 |
| `NOT_FOUND` | 404 | Resource not found | Verify ID |
| `VERSION_CONFLICT` | 409 | Optimistic lock failure | Refresh and retry |
| `INVALID_STATE_TRANSITION` | 422 | Invalid workflow action | Check case status |

### Optimistic Locking (409 Version Conflict)

```json
{
  "code": "VERSION_CONFLICT",
  "message": "Case was modified by another user",
  "details": {
    "currentVersion": 5,
    "yourVersion": 3
  }
}
```

**Recovery**: Fetch current case state, review changes, retry with current version.

### External Service Unavailable (503)

```json
{
  "code": "EXTERNAL_SERVICE_UNAVAILABLE",
  "message": "Spriggy onboarding service temporarily unavailable. Block clearance queued for retry.",
  "details": {
    "syncStatus": "PENDING_SYNC",
    "retryScheduled": true
  }
}
```

**Note**: Operation is queued for retry. The `syncStatus` field indicates eventual consistency status.

---

## Polling Patterns

### Dashboard Polling (30-second interval)

```bash
# Poll dashboard metrics
while true; do
  curl -s -X GET "https://aml.spriggy.com.au/api/v1/dashboard/metrics" \
    -H "Authorization: Bearer ${TOKEN}" | jq '.'
  sleep 30
done
```

### Notification Polling

```bash
# Poll for unread notification count (badge update)
curl -X GET "https://aml.spriggy.com.au/api/v1/notifications/unread-count" \
  -H "Authorization: Bearer ${TOKEN}"

# Response: {"unreadCount": 3}
```

---

## Reporting Examples

### Case Volume Report

```bash
curl -X GET "https://aml.spriggy.com.au/api/v1/reports/case-volumes?startDate=2026-01-01&endDate=2026-01-31&groupBy=week" \
  -H "Authorization: Bearer ${TOKEN}"
```

### SLA Compliance Report

```bash
curl -X GET "https://aml.spriggy.com.au/api/v1/reports/sla-compliance?startDate=2026-01-01&endDate=2026-01-31" \
  -H "Authorization: Bearer ${TOKEN}"
```

### Export for Governance

```bash
curl -X POST "https://aml.spriggy.com.au/api/v1/reports/export" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{
    "reportType": "case_volumes",
    "format": "xlsx",
    "startDate": "2026-01-01",
    "endDate": "2026-03-31"
  }' \
  -o q1_2026_case_volumes.xlsx
```

---

## Role-Based Access Summary

| Endpoint | L1 | L2 | Manager | Read-Only |
|----------|----|----|---------|-----------|
| List/View Cases | Yes | Yes | Yes | Yes |
| Claim Cases | Yes | Yes | Yes | No |
| Close Cases | Yes | Yes | Yes | No |
| Escalate to L2 | Yes | No | No | No |
| Clear Sanctions Block | No | Yes | Yes | No |
| Create SMR Recommendation | No | Yes | Yes | No |
| Approve/Reject SMR | No | No | Yes | No |
| Reopen Closed Cases | No | Yes | Yes | No |
| Update User Roles | No | No | Yes | No |
| Export Reports | Yes | Yes | Yes | Yes |
| Configure Thresholds | No | No | Yes | No |

---

## System Configuration

### SLA Warning Threshold

Configure when SLA warning notifications are triggered (FR-050).

```bash
# Get current threshold
curl -X GET "https://aml.spriggy.com.au/api/v1/config/sla-warning-threshold" \
  -H "Authorization: Bearer ${TOKEN}"

# Response:
# {
#   "thresholdPercentage": 80.0,
#   "effectiveFrom": "2026-01-01T00:00:00Z",
#   "changedBy": {"displayName": "Admin User"}
# }
```

```bash
# Update threshold (Manager only)
curl -X PUT "https://aml.spriggy.com.au/api/v1/config/sla-warning-threshold" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"thresholdPercentage": 75.0}'

# Analysts will now receive warnings when 75% of SLA timeline has elapsed
```

### PEP Confidence Threshold

Configure the confidence score threshold for PEP classification (FR-030).

```bash
# Get current threshold
curl -X GET "https://aml.spriggy.com.au/api/v1/config/pep-threshold" \
  -H "Authorization: Bearer ${TOKEN}"

# Response:
# {
#   "thresholdValue": 80.0,
#   "effectiveFrom": "2026-01-01T00:00:00Z"
# }
```

```bash
# Update threshold (Manager only)
curl -X PUT "https://aml.spriggy.com.au/api/v1/config/pep-threshold" \
  -H "Authorization: Bearer ${TOKEN}" \
  -H "Content-Type: application/json" \
  -d '{"thresholdValue": 85.0}'

# Scores > 85% will now trigger blocking EDD requirement
# Scores <= 85% will allow provisional onboarding
```

---

## Rate Limits

| Endpoint Category | Limit | Window |
|-------------------|-------|--------|
| Webhooks | 100/min | Per source |
| Read operations | 1000/min | Per user |
| Write operations | 100/min | Per user |
| Report exports | 10/hour | Per user |

Rate limit headers:
- `X-RateLimit-Limit`: Request limit
- `X-RateLimit-Remaining`: Requests remaining
- `X-RateLimit-Reset`: Unix timestamp of reset
