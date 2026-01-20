# Research: 001-aml-case-management

> AML Case Management System - Technical Research Document
> Generated: 2026-01-15
> Phase: Research (Iteration 2)

---

## Summary

| ID | Decision | Choice | Rationale |
|----|----------|--------|-----------|
| D1 | Audit Trail Architecture | Append-only audit log with event sourcing for case state | Simpler than full event sourcing; meets 7-year retention; enables replay for compliance |
| D2 | SLA Calculation Engine | Python `holidays` library + configurable calendar table; SLA starts at case creation | Accurate AU business days; extensible for state holidays; clear regulatory start point |
| D3 | External Integration Pattern | Async queue with circuit breaker + dead letter queue + duplicate detection | Resilience per constitution; handles duplicates per EC-005; graceful failure handling |
| D4 | Document Storage | PostgreSQL BYTEA for structured data + S3-compatible object store for attachments | Transactional integrity for SMR drafts; scalable for evidence files |
| D5 | Authentication Architecture | OIDC integration with existing Spriggy SSO + local RBAC | Aligns with assumption A3; enforces role segregation locally |
| D6 | Notification System | Celery async tasks with email provider + in-app notification table; 30s polling for dashboard | Decoupled delivery; supports email Day 1, simple real-time dashboard |
| D7 | Reporting Data Access | Read replicas with materialized views for MI dashboards | Non-blocking to operational queries; pre-computed metrics for governance |
| D8 | Concurrency Control | Optimistic locking with version column | Handles EC-001; prevents lost updates without blocking |
| D9 | Case Reference Generation | PostgreSQL SEQUENCE with formatted prefix | Guaranteed uniqueness; sequential per FR-003 |
| D10 | Communication Template Storage | Version-controlled code repository with database cache | Aligns with A11; deployment-controlled changes per FR-054 |
| D11 | Webhook Authentication | HMAC signature validation for GreenID/Indue webhooks | Industry standard; prevents spoofed alerts; aligns with security requirements |
| D12 | PII Redaction Strategy | Structured payload with explicit PII field list; service-layer redaction | Constitution Principle VI compliance; clear boundaries; auditable |
| D13 | Case Queue Assignment | Manual claim from unassigned queue; analysts self-select | Simple; appropriate for small team (A4); avoids cherry-picking through SLA visibility |

---

## Decision 1: Audit Trail Architecture

### Status
Accepted

### Context
The constitution mandates an **immutable audit trail** (Principle I - NON-NEGOTIABLE) with:
- All case actions, decisions, and state transitions recorded immutably
- Full attribution and timestamp
- 7-year retention minimum
- No deletion of case records or audit entries (FR-061)
- Read access logging (FR-059)
- Export capability for regulatory inspection (FR-062)

Two primary architectural patterns exist for this requirement:
1. **Full Event Sourcing**: Store all changes as immutable events; derive current state by replaying events
2. **Append-Only Audit Log**: Store current state in mutable tables; append audit entries to separate immutable table

### Options Evaluated

| Criterion | Weight | Event Sourcing | Append-Only Log |
|-----------|--------|----------------|-----------------|
| Complexity | 25% | Low (3) - Complex replay, CQRS overhead | High (8) - Standard patterns |
| Team Familiarity | 20% | Low (3) - Novel to most teams | High (9) - Standard Django/FastAPI |
| Auditability | 20% | High (9) - Native immutability | High (8) - Requires discipline |
| Query Performance | 15% | Medium (5) - Needs projections | High (9) - Direct queries |
| Regulatory Fit | 15% | High (9) - Perfect history | High (8) - Meets requirements |
| Data Volume | 5% | High (4) - Event explosion | Medium (7) - Controlled growth |
| **Weighted Score** | | **5.35** | **8.15** |

### Decision
**Append-only audit log with event sourcing for case state transitions**

Hybrid approach:
1. **Case state changes** use lightweight event sourcing (CaseStateEvent table) to guarantee state transition history
2. **All actions** append to immutable AuditLog table with user, timestamp, action type, payload
3. **Current state** maintained in Case table for efficient querying
4. **Soft deletes only** - no physical deletion permitted

### Rationale
- Full event sourcing adds significant complexity without proportional benefit for this use case
- Append-only audit log satisfies all regulatory requirements (FR-058 through FR-062)
- Hybrid approach captures state transitions explicitly while maintaining query simplicity
- Team can implement and maintain with standard FastAPI/SQLAlchemy patterns
- 7-year retention achievable with standard database archival strategies

### Trade-offs Accepted
- Cannot derive complete current state from events alone (must maintain Case table)
- Requires discipline to ensure all mutations go through audit-aware service layer
- Slightly more storage than pure current-state (audit table growth)

### Constitution Alignment
- **Principle I (Immutable Audit Trail)**: Fully satisfied - all actions recorded immutably
- **Principle VI (Sensitive Data Protection)**: Audit payloads must exclude PII from logs per constitution

### Implementation Notes
```python
# AuditLog table structure
class AuditLog(Base):
    __tablename__ = "audit_log"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID, ForeignKey("cases.id"), nullable=True)  # null for system events
    user_id = Column(UUID, ForeignKey("users.id"), nullable=True)  # null for system actions
    action_type = Column(String(50), nullable=False)  # e.g., CASE_CREATED, STATUS_CHANGED
    action_detail = Column(JSONB, nullable=False)  # structured payload
    ip_address = Column(String(45), nullable=True)  # IPv6 compatible
    user_agent = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # No updated_at - immutable
    # No delete capability
```

### Dependencies
- D4 (Document Storage) - Audit log references attachments by ID
- D5 (Authentication) - User attribution requires authenticated context

---

## Decision 2: SLA Calculation Engine

### Status
Accepted

### Context
The constitution mandates **SLA Tracking and Enforcement** (Principle V) with:
- Business day calculations for Australian context (FR-048)
- Specific SLA timelines: KYC 5 days, PEP/Sanctions 24h, Suspicious activity 48h, SMR filing 3 days (FR-049)
- Warning notifications at configurable threshold (FR-050)
- Automatic escalation on breach (FR-051)

Edge cases to handle:
- EC-007: System clock discrepancy - all timestamps must use UTC
- Australian national holidays (federal)
- Potential state-specific holidays (assumption A3 - manual maintenance)

**SLA Start Point**: User clarified that SLA clock starts at **case creation timestamp** (when webhook is received and case is persisted). This is the regulatory-relevant timestamp for audit purposes.

### Options Evaluated

| Criterion | Weight | Python `holidays` + DB | Custom Calendar Table | External Service |
|-----------|--------|------------------------|----------------------|------------------|
| Accuracy | 30% | High (8) - AU holidays built-in | High (9) - Full control | High (8) - Depends on provider |
| Maintainability | 25% | High (8) - Library maintained | Medium (6) - Team maintains | Low (4) - Vendor dependency |
| Flexibility | 20% | Medium (7) - Override in DB | High (9) - Full control | Low (5) - API constraints |
| Team Effort | 15% | Low (9) - Minimal setup | High (4) - Build calendar | Medium (6) - Integration work |
| Cost | 10% | Free (10) | Free (10) | Variable (5) |
| **Weighted Score** | | **8.05** | **7.15** | **5.70** |

### Decision
**Python `holidays` library with database override table for custom dates**

Architecture:
1. Use `holidays.Australia()` as base calendar for federal holidays
2. Database table `HolidayOverride` for state-specific or custom dates
3. SLA calculator service that combines both sources
4. All datetime operations in UTC; display conversion at API layer
5. **SLA start point**: Case creation timestamp (`created_at` on Case entity)

### Rationale
- Python `holidays` library is well-maintained and covers Australian federal holidays accurately
- Database override table allows operations team to add state holidays without code deployment
- Aligns with assumption A3 (operations team maintains calendar)
- Straightforward implementation with minimal external dependencies

### Trade-offs Accepted
- Requires annual review of state holiday overrides (operational process)
- Library updates needed for future federal holiday changes (annual Python dependency update)

### Constitution Alignment
- **Principle V (SLA Tracking and Enforcement)**: Fully satisfied with accurate business day calculation

### Implementation Notes
```python
from holidays import Australia
from datetime import date, timedelta

class SLACalculator:
    def __init__(self, holiday_override_repo):
        self.base_holidays = Australia(years=range(2024, 2035))
        self.override_repo = holiday_override_repo

    def is_business_day(self, check_date: date) -> bool:
        if check_date.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return False
        if check_date in self.base_holidays:
            return False
        if self.override_repo.is_holiday(check_date):
            return False
        return True

    def add_business_days(self, start: date, days: int) -> date:
        current = start
        remaining = days
        while remaining > 0:
            current += timedelta(days=1)
            if self.is_business_day(current):
                remaining -= 1
        return current

    def business_days_until(self, start: date, end: date) -> int:
        count = 0
        current = start
        while current < end:
            current += timedelta(days=1)
            if self.is_business_day(current):
                count += 1
        return count
```

### Dependencies
- D1 (Audit Trail) - SLA changes recorded in audit log
- D6 (Notification System) - SLA warnings trigger notifications

---

## Decision 3: External Integration Pattern

### Status
Accepted

### Context
The constitution mandates **External Integration Resilience** (Principle VII) with:
- 30-second timeouts
- Retry with exponential backoff
- Circuit breaker (5 failures to open)

Additionally, **Explicit Error Handling** (Principle IV) requires:
- No silent failures
- Timeout, retry, circuit breaker patterns

Three external integrations required:
1. **GreenID**: Receive screening webhooks, potentially query for details
2. **Indue**: Receive transaction monitoring alerts
3. **Spriggy Onboarding API**: Send block/unblock callbacks (FR-028)

Edge cases:
- EC-002: External service unavailable during screening
- EC-009: Onboarding block API callback failure

### Options Evaluated

| Criterion | Weight | Async Queue + Circuit Breaker | Sync with Retries | Service Mesh |
|-----------|--------|-------------------------------|-------------------|--------------|
| Resilience | 30% | High (9) - Full pattern support | Medium (6) - Limited | High (9) - Built-in |
| Complexity | 25% | Medium (7) - Queue infrastructure | Low (8) - Simple code | High (3) - K8s dependency |
| Team Familiarity | 20% | High (8) - Celery well-known | High (9) - Basic patterns | Low (4) - Specialized |
| Observability | 15% | High (8) - Queue metrics | Medium (6) - Log-based | High (9) - Native |
| Tech Stack Fit | 10% | High (9) - Celery in stack | High (9) - No new tech | Low (3) - New infrastructure |
| **Weighted Score** | | **8.00** | **7.15** | **5.35** |

### Decision
**Async queue (Celery + Redis) with circuit breaker pattern, dead letter queue, and duplicate detection**

Architecture:
1. **Webhook receivers**: Synchronous FastAPI endpoints that authenticate (D11), validate, check duplicates, persist to DB, enqueue processing
2. **Outbound calls** (Spriggy API): Celery tasks with circuit breaker wrapper
3. **Circuit breaker**: Using `pybreaker` library (5 failures to open, 60s reset timeout)
4. **Dead letter queue**: Failed messages after max retries move to DLQ for manual review
5. **Retry policy**: Exponential backoff (2s, 4s, 8s, 16s, 32s max) with 5 attempts
6. **Duplicate detection** (per EC-005): Hash-based deduplication using composite key (customer_id + alert_type + source) within configurable window (default 24 hours). Duplicates link to existing case rather than creating new case.

### Rationale
- Celery + Redis already in tech stack (from context)
- Circuit breaker pattern explicitly required by constitution
- Dead letter queue prevents message loss while enabling investigation
- Async processing decouples webhook receipt from downstream processing (no blocking user flows)

### Trade-offs Accepted
- Eventual consistency for onboarding block status (mitigated by "Pending Sync" indicator per EC-009)
- Queue infrastructure overhead (Redis already in stack)
- Manual intervention needed for DLQ processing (operational procedure)

### Constitution Alignment
- **Principle IV (Explicit Error Handling)**: Circuit breaker and DLQ ensure no silent failures
- **Principle VII (External Integration Resilience)**: Full pattern implementation

### Implementation Notes
```python
from pybreaker import CircuitBreaker
from celery import shared_task
from celery.exceptions import MaxRetriesExceededError
import hashlib
from datetime import datetime, timedelta

# Circuit breaker configuration per constitution
spriggy_circuit = CircuitBreaker(
    fail_max=5,
    reset_timeout=60,
    exclude=[ValidationError]  # Don't trip on validation errors
)

# Duplicate detection (EC-005)
class WebhookDeduplicator:
    WINDOW_HOURS = 24  # Configurable via settings

    def compute_dedup_key(self, customer_id: str, alert_type: str, source: str) -> str:
        """Generate hash key for duplicate detection."""
        raw = f"{customer_id}:{alert_type}:{source}"
        return hashlib.sha256(raw.encode()).hexdigest()

    def check_duplicate(self, dedup_key: str) -> Optional[Case]:
        """Check if webhook was already processed within window."""
        cutoff = datetime.utcnow() - timedelta(hours=self.WINDOW_HOURS)
        existing = db.query(WebhookReceipt).filter(
            WebhookReceipt.dedup_key == dedup_key,
            WebhookReceipt.received_at >= cutoff
        ).first()
        if existing:
            return existing.case
        return None

    def record_receipt(self, dedup_key: str, case_id: str):
        """Record webhook receipt for future duplicate detection."""
        receipt = WebhookReceipt(
            dedup_key=dedup_key,
            case_id=case_id,
            received_at=datetime.utcnow()
        )
        db.add(receipt)

@shared_task(bind=True, max_retries=5, default_retry_delay=2)
def notify_onboarding_service(self, customer_id: str, action: str, case_id: str):
    """Send block/unblock callback to Spriggy onboarding service."""
    try:
        response = spriggy_circuit.call(
            _call_spriggy_api,
            customer_id=customer_id,
            action=action,
            case_id=case_id,
            timeout=30  # Constitution: 30s timeout
        )
        return response
    except CircuitBreakerError:
        # Circuit open - move to DLQ immediately
        move_to_dlq(self.request.id, "circuit_open")
        raise
    except Exception as exc:
        try:
            # Exponential backoff: 2^retry_count seconds
            raise self.retry(exc=exc, countdown=2 ** self.request.retries)
        except MaxRetriesExceededError:
            move_to_dlq(self.request.id, "max_retries")
            raise
```

### Dependencies
- D4 (Document Storage) - Integration payloads may include attachments
- D1 (Audit Trail) - All integration events logged
- D11 (Webhook Authentication) - Webhooks must be authenticated before processing

---

## Decision 4: Document Storage Strategy

### Status
Accepted

### Context
The system requires storage for:
1. **SMR draft documents** (FR-040): Generated upon manager approval, regulatory format
2. **Evidence attachments**: Files attached during investigation
3. **Customer communication records**: May include document copies

Requirements:
- Transactional integrity for SMR drafts (must not lose approved SMRs)
- 7-year retention (Principle I)
- Potential regulatory inspection access (FR-062)
- PII protection (Principle VI)

Estimated volumes (per OQ-005: 50-100 cases/day):
- SMRs: ~5-10% of cases = 5-10 SMRs/day
- Attachments: ~2-3 per case average = 100-300 attachments/day

### Options Evaluated

| Criterion | Weight | PostgreSQL + S3 | PostgreSQL Only | Pure Object Store |
|-----------|--------|-----------------|-----------------|-------------------|
| Transactional Integrity | 30% | High (8) - Hybrid | High (10) - Native | Low (4) - Eventual |
| Scalability | 25% | High (9) - S3 scales | Medium (6) - DB limits | High (10) - Designed for this |
| Query Capability | 20% | Medium (7) - Metadata in DB | High (9) - Full SQL | Low (3) - Key-value only |
| Cost Efficiency | 15% | High (8) - S3 cheap storage | Medium (6) - DB storage expensive | High (9) - Optimized |
| Operational Simplicity | 10% | Medium (7) - Two systems | High (9) - Single system | Medium (6) - New infrastructure |
| **Weighted Score** | | **8.00** | **7.55** | **5.65** |

### Decision
**PostgreSQL for structured data and small documents + S3-compatible object store for large attachments**

Architecture:
1. **SMR drafts** (critical): Store in PostgreSQL BYTEA column with transactional write
2. **Small attachments** (<1MB): Store in PostgreSQL BYTEA for simplicity
3. **Large attachments** (>=1MB): Store in S3-compatible store (MinIO for dev, S3 for prod)
4. **Metadata always in PostgreSQL**: File name, size, content type, S3 key, hash, case reference
5. **Encryption at rest**: AES-256 per constitution (Principle VI)

### Rationale
- SMR drafts are critical compliance documents - PostgreSQL transactional guarantees prevent loss
- Large attachments benefit from object store cost efficiency and scalability
- S3-compatible allows same code for local dev (MinIO) and production (AWS S3)
- Metadata in PostgreSQL enables efficient queries and joins with case data

### Trade-offs Accepted
- Two storage systems to operate (mitigated by S3-compatible abstraction)
- Large attachments have eventual consistency (acceptable for evidence files)
- S3 bucket permissions require separate security configuration

### Constitution Alignment
- **Principle I (Immutable Audit Trail)**: Document metadata and access logged
- **Principle VI (Sensitive Data Protection)**: AES-256 encryption at rest required

### Implementation Notes
```python
class Document(Base):
    __tablename__ = "documents"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID, ForeignKey("cases.id"), nullable=False)
    filename = Column(String(255), nullable=False)
    content_type = Column(String(100), nullable=False)
    size_bytes = Column(Integer, nullable=False)
    sha256_hash = Column(String(64), nullable=False)  # Integrity verification
    storage_type = Column(String(20), nullable=False)  # 'database' or 's3'
    storage_key = Column(String(500), nullable=True)  # S3 key if external
    content = Column(LargeBinary, nullable=True)  # For database storage
    document_type = Column(String(50), nullable=False)  # 'smr_draft', 'evidence', etc.
    uploaded_by = Column(UUID, ForeignKey("users.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

# SMR-specific storage (always in database)
class SMRDraft(Base):
    __tablename__ = "smr_drafts"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    case_id = Column(UUID, ForeignKey("cases.id"), unique=True, nullable=False)
    smr_recommendation_id = Column(UUID, ForeignKey("smr_recommendations.id"), nullable=False)
    content = Column(LargeBinary, nullable=False)  # PDF or structured format
    format_version = Column(String(20), nullable=False)  # AUSTRAC format version
    generated_at = Column(DateTime(timezone=True), server_default=func.now())
    generated_by = Column(UUID, ForeignKey("users.id"), nullable=False)
```

### Dependencies
- D1 (Audit Trail) - Document access logged
- D5 (Authentication) - Upload permissions enforced

---

## Decision 5: Authentication and Authorization Architecture

### Status
Accepted

### Context
The constitution mandates **Role-Based Access Control with Segregation of Duties** (Principle II - NON-NEGOTIABLE):
- Four roles: L1 Analyst, L2 Analyst, AML Compliance Manager, Read-Only (FR-063)
- L1 cannot approve SMRs (FR-014)
- L2 cannot approve own recommendations (FR-020)
- Track original recommender for segregation enforcement (EC-003)

Open question OQ-003 asks about authentication system - assumption A3 suggests Spriggy SSO integration.

### Options Evaluated

| Criterion | Weight | OIDC SSO + Local RBAC | Full External IAM | Local Auth Only |
|-----------|--------|----------------------|-------------------|-----------------|
| Security | 30% | High (8) - SSO best practice | High (9) - Centralized | Medium (6) - Password management |
| Integration Effort | 25% | Medium (7) - Standard protocol | High (4) - Complex setup | Low (9) - No integration |
| User Experience | 20% | High (9) - Single sign-on | High (9) - Single sign-on | Low (5) - Separate credentials |
| Segregation Control | 15% | High (9) - Local enforcement | Medium (6) - External rules | High (9) - Full control |
| Operational Fit | 10% | High (8) - Aligns with A3 | Medium (5) - New system | Low (4) - Duplicate accounts |
| **Weighted Score** | | **8.00** | **6.45** | **6.65** |

### Decision
**OIDC integration with Spriggy SSO for authentication + local RBAC enforcement**

Architecture:
1. **Authentication**: OIDC/OAuth2 flow with Spriggy's existing identity provider
2. **User provisioning**: JIT (Just-In-Time) provisioning on first login with default Read-Only role
3. **Role management**: Local database role assignment by AML Compliance Manager
4. **Authorization**: FastAPI dependency injection for role checking
5. **Segregation enforcement**: Local logic checking original actor IDs regardless of current role

### Rationale
- OIDC/OAuth2 is industry standard and likely supported by existing Spriggy SSO
- Local RBAC enables strict segregation of duties control required by constitution
- JIT provisioning reduces administrative overhead while maintaining security
- Decoupling auth (who you are) from authz (what you can do) enables fine-grained control

### Trade-offs Accepted
- Role changes require both SSO deprovisioning (if user leaves) and local role update
- JIT provisioning means unknown users can access system (with Read-Only by default)
- Role assignment is manual (acceptable for small team per A4)

### Constitution Alignment
- **Principle II (RBAC with Segregation)**: Fully satisfied with local enforcement
- **Principle I (Audit Trail)**: All auth events logged

### Implementation Notes
```python
from enum import Enum
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2AuthorizationCodeBearer

class Role(str, Enum):
    L1_ANALYST = "l1_analyst"
    L2_ANALYST = "l2_analyst"
    AML_MANAGER = "aml_manager"
    READ_ONLY = "read_only"

# Role hierarchy for permission checks
ROLE_HIERARCHY = {
    Role.READ_ONLY: 0,
    Role.L1_ANALYST: 1,
    Role.L2_ANALYST: 2,
    Role.AML_MANAGER: 3,
}

def require_role(minimum_role: Role):
    """Dependency that enforces minimum role requirement."""
    def role_checker(current_user: User = Depends(get_current_user)):
        if ROLE_HIERARCHY[current_user.role] < ROLE_HIERARCHY[minimum_role]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role {minimum_role} or higher required"
            )
        return current_user
    return role_checker

def enforce_segregation(original_actor_id: str, action: str):
    """Enforce segregation of duties regardless of current role."""
    def segregation_checker(current_user: User = Depends(get_current_user)):
        if str(current_user.id) == original_actor_id:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Cannot {action} your own work (segregation of duties)"
            )
        return current_user
    return segregation_checker
```

### Dependencies
- D1 (Audit Trail) - Auth events logged
- D6 (Notification System) - Role change triggers case reassignment (FR-026)

---

## Decision 6: Notification System Design

### Status
Accepted

### Context
The specification requires notifications for:
- Case assignments (FR-066)
- SLA warnings and breaches (FR-067)
- Escalations requiring attention (FR-068)
- In-system dashboard notifications (FR-069 - SHOULD)

Assumption A5 confirms email is primary channel for Day 1; Slack is Phase 2.

### Options Evaluated

| Criterion | Weight | Celery Tasks + Notification Table | External Notification Service | Sync Email Only |
|-----------|--------|-----------------------------------|-------------------------------|-----------------|
| Extensibility | 30% | High (9) - Add channels easily | High (8) - API-based | Low (4) - Hardcoded |
| Reliability | 25% | High (8) - Retry, DLQ | High (9) - Provider SLA | Low (5) - Sync failures |
| Team Familiarity | 20% | High (8) - Celery in stack | Medium (5) - New service | High (9) - Simple |
| In-App Support | 15% | High (9) - Native table | Medium (6) - Polling needed | Low (3) - No support |
| Cost | 10% | Low (8) - Existing infra | Medium (5) - Service fees | Low (9) - Email only |
| **Weighted Score** | | **8.45** | **7.05** | **5.20** |

### Decision
**Celery async tasks with email provider integration + in-app notification table + 30-second polling**

Architecture:
1. **Notification creation**: Domain events trigger notification records
2. **Notification table**: Stores all notifications with delivery status
3. **Email delivery**: Celery task sends via email provider (SendGrid/SES)
4. **In-app delivery**: **30-second polling interval** for dashboard updates (user confirmed)
5. **Preference management**: User notification preferences in database
6. **Retry logic**: Failed email deliveries retry with backoff

### Rationale
- Celery already in stack, no new infrastructure
- Notification table enables in-app dashboard (FR-069)
- Async delivery prevents email failures from blocking user workflows
- Architecture supports Slack addition in Phase 2 (new delivery channel only)
- **30-second polling chosen** over WebSocket for simplicity: small team (under 10 analysts per A4) does not justify WebSocket infrastructure complexity; polling is adequate for dashboard responsiveness and easier to implement/debug

### Trade-offs Accepted
- Notification delivery is eventually consistent (may be seconds delay)
- Email deliverability depends on provider (standard operational concern)
- Dashboard updates have up to 30-second latency (acceptable for small team)

### Constitution Alignment
- **Principle IV (Explicit Error Handling)**: Failed notifications tracked and retried
- **Principle V (SLA Enforcement)**: SLA warnings delivered reliably

### Implementation Notes
```python
class NotificationType(str, Enum):
    CASE_ASSIGNED = "case_assigned"
    SLA_WARNING = "sla_warning"
    SLA_BREACH = "sla_breach"
    ESCALATION = "escalation"
    SMR_PENDING_APPROVAL = "smr_pending_approval"
    SMR_APPROVED = "smr_approved"
    SMR_REJECTED = "smr_rejected"

class Notification(Base):
    __tablename__ = "notifications"

    id = Column(UUID, primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID, ForeignKey("users.id"), nullable=False)
    notification_type = Column(String(50), nullable=False)
    title = Column(String(255), nullable=False)
    body = Column(Text, nullable=False)
    case_id = Column(UUID, ForeignKey("cases.id"), nullable=True)
    email_sent = Column(Boolean, default=False)
    email_sent_at = Column(DateTime(timezone=True), nullable=True)
    read_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

@shared_task(bind=True, max_retries=3)
def send_notification_email(self, notification_id: str):
    """Send email for notification with retry logic."""
    notification = get_notification(notification_id)
    try:
        email_service.send(
            to=notification.user.email,
            subject=notification.title,
            body=notification.body
        )
        mark_notification_email_sent(notification_id)
    except Exception as exc:
        raise self.retry(exc=exc, countdown=2 ** self.request.retries)
```

### Dependencies
- D2 (SLA Calculation) - SLA warnings trigger notifications
- D5 (Authentication) - User email from SSO profile

---

## Decision 7: Reporting and MI Data Access

### Status
Accepted

### Context
Reporting requirements:
- Operational reports: case volumes, open count, aging, SLA compliance (FR-070)
- Risk reports: SMR volumes, screening hit rates, false positive rates (FR-071)
- Export for governance committee (FR-072)
- Aged case visibility (FR-073)

Read-only users need report access without impacting operational system (FR-064).
Expected query patterns: aggregations, time-series, filtering by date range.

### Options Evaluated

| Criterion | Weight | Read Replica + Materialized Views | Direct Queries | Data Warehouse |
|-----------|--------|-----------------------------------|----------------|----------------|
| Operational Impact | 30% | Low (9) - Isolated | High (4) - Shared resources | Low (9) - Isolated |
| Query Performance | 25% | High (8) - Pre-computed | Medium (6) - On-demand | High (9) - Optimized |
| Implementation Effort | 20% | Medium (7) - PostgreSQL native | Low (9) - No additional setup | High (3) - New infrastructure |
| Data Freshness | 15% | High (8) - Near real-time | High (10) - Real-time | Medium (5) - Batch latency |
| Cost | 10% | Medium (7) - Replica cost | Low (9) - No additional | High (4) - DW licensing |
| **Weighted Score** | | **8.00** | **6.50** | **6.35** |

### Decision
**Read replica with materialized views for MI dashboards**

Architecture:
1. **Read replica**: PostgreSQL streaming replication for report queries
2. **Materialized views**: Pre-computed aggregations refreshed on schedule
3. **Report API**: Dedicated endpoints querying read replica
4. **Export service**: Generate CSV/Excel from materialized views
5. **Refresh schedule**: Hourly for operational metrics, daily for governance reports

### Rationale
- Read replica isolates reporting from operational database
- PostgreSQL materialized views are native and well-supported
- Streaming replication provides near real-time data (seconds of lag)
- No new infrastructure beyond PostgreSQL (already in stack)

### Trade-offs Accepted
- Read replica cost (additional database instance)
- Materialized views may be slightly stale (acceptable for governance reports)
- Complex aggregations require view definition (one-time setup)

### Constitution Alignment
- **Principle I (Audit Trail)**: Report exports logged
- **Principle II (RBAC)**: Read-only role can only access reports, not modify data

### Implementation Notes
```sql
-- Materialized view for case metrics
CREATE MATERIALIZED VIEW case_metrics AS
SELECT
    date_trunc('day', created_at) as report_date,
    case_type,
    case_subtype,
    COUNT(*) as total_cases,
    COUNT(*) FILTER (WHERE status = 'Closed') as closed_cases,
    COUNT(*) FILTER (WHERE sla_breached = true) as sla_breaches,
    AVG(EXTRACT(EPOCH FROM (closed_at - created_at)) / 86400)
        FILTER (WHERE closed_at IS NOT NULL) as avg_resolution_days
FROM cases
GROUP BY date_trunc('day', created_at), case_type, case_subtype;

-- Refresh on schedule (pg_cron or application job)
REFRESH MATERIALIZED VIEW CONCURRENTLY case_metrics;
```

### Dependencies
- D1 (Audit Trail) - Report access logged
- D5 (Authentication) - Read-only role enforced

---

## Decision 8: Concurrency Control

### Status
Accepted

### Context
Edge case EC-001 requires handling concurrent case actions:
- Two analysts attempt to action same case simultaneously
- First submission succeeds; second receives conflict notification
- Option to refresh and review changes

This is a classic lost update problem requiring concurrency control.

### Options Evaluated

| Criterion | Weight | Optimistic Locking | Pessimistic Locking | Last Write Wins |
|-----------|--------|-------------------|---------------------|-----------------|
| User Experience | 35% | High (8) - Non-blocking | Low (4) - Wait time | Low (3) - Data loss |
| Correctness | 30% | High (9) - Detects conflicts | High (9) - Prevents conflicts | Low (2) - Incorrect |
| Performance | 20% | High (9) - No locks held | Low (5) - Lock contention | High (10) - No overhead |
| Implementation | 15% | Medium (7) - Version checks | Medium (7) - Lock management | High (9) - Trivial |
| **Weighted Score** | | **8.15** | **5.95** | **4.95** |

### Decision
**Optimistic locking with version column**

Architecture:
1. **Version column**: Each case has `version` integer, incremented on each update
2. **Update pattern**: Include version in WHERE clause, check rows affected
3. **Conflict response**: HTTP 409 Conflict with current state for refresh
4. **UI handling**: User sees conflict dialog with option to refresh and retry

### Rationale
- Optimistic locking is standard pattern for web applications with low conflict rate
- Small team (A4) and queue-based assignment reduces conflict likelihood
- No database locks held during user think time (better scalability)
- Conflict detection provides clear feedback to users (no silent data loss)

### Trade-offs Accepted
- Conflicts require user intervention (refresh and potentially redo work)
- Slight complexity in all update operations (version check required)

### Constitution Alignment
- **Principle I (Audit Trail)**: Conflict attempts can be logged for analysis

### Implementation Notes
```python
class Case(Base):
    __tablename__ = "cases"
    # ... other columns
    version = Column(Integer, nullable=False, default=1)

def update_case(case_id: UUID, update_data: CaseUpdate, expected_version: int) -> Case:
    """Update case with optimistic locking."""
    result = db.execute(
        update(Case)
        .where(Case.id == case_id, Case.version == expected_version)
        .values(
            **update_data.dict(exclude_unset=True),
            version=expected_version + 1,
            updated_at=func.now()
        )
        .returning(Case)
    )

    updated_case = result.fetchone()
    if updated_case is None:
        # Version mismatch - another user modified
        current_case = get_case(case_id)
        raise OptimisticLockException(
            message="Case was modified by another user",
            current_version=current_case.version,
            current_state=current_case
        )
    return updated_case
```

### Dependencies
- D1 (Audit Trail) - Updates logged with version changes

---

## Decision 9: Case Reference Generation

### Status
Accepted

### Context
FR-003 requires: "System MUST assign each case a unique, sequential case reference number."

Requirements:
- Unique: No duplicate references
- Sequential: Monotonically increasing (not random)
- Human-readable: Used in communications and audit

### Options Evaluated

| Criterion | Weight | PostgreSQL SEQUENCE | Application Counter | UUID |
|-----------|--------|---------------------|---------------------|------|
| Uniqueness | 35% | High (10) - Guaranteed | Medium (7) - Race conditions | High (10) - Guaranteed |
| Sequential | 30% | High (10) - Native | High (9) - Requires locking | Low (1) - Random |
| Performance | 20% | High (9) - Minimal overhead | Medium (6) - Lock contention | High (10) - No coordination |
| Simplicity | 15% | High (9) - Built-in | Low (5) - Complex | High (10) - Trivial |
| **Weighted Score** | | **9.65** | **6.95** | **6.85** |

### Decision
**PostgreSQL SEQUENCE with formatted prefix**

Architecture:
1. **Sequence**: `CREATE SEQUENCE case_ref_seq START 1000`
2. **Format**: `AML-{SEQUENCE}` (e.g., AML-1000, AML-1001)
3. **Assignment**: Sequence value fetched at case creation, never recycled
4. **Storage**: Store both numeric sequence and formatted reference

### Rationale
- PostgreSQL sequences guarantee uniqueness across concurrent transactions
- Native database feature, no application code complexity
- Sequential numbering aids human communication and audit queries
- Starting at 1000 provides room for test data and avoids single-digit references

### Trade-offs Accepted
- Reference numbers may have gaps if transactions roll back (acceptable)
- Prefix change requires migration (unlikely to change)

### Constitution Alignment
- **Principle I (Audit Trail)**: Reference number enables tracking across systems

### Implementation Notes
```sql
CREATE SEQUENCE case_ref_seq START 1000;

-- In application
class CaseService:
    def create_case(self, data: CaseCreate) -> Case:
        ref_number = db.execute(text("SELECT nextval('case_ref_seq')")).scalar()
        case = Case(
            id=uuid.uuid4(),
            reference_number=ref_number,
            reference_code=f"AML-{ref_number}",
            # ... other fields
        )
        db.add(case)
        return case
```

### Dependencies
- None (standalone decision)

---

## Decision 10: Communication Template Storage

### Status
Accepted

### Context
FR-053/FR-054 require:
- Pre-approved communication templates for customer outreach
- Templates are static and changed only through code deployments
- AML Compliance Manager review required for changes

Assumption A11 confirms templates version-controlled in code repository.

### Options Evaluated

| Criterion | Weight | Code Repo + DB Cache | Database Only | File System |
|-----------|--------|----------------------|---------------|-------------|
| Version Control | 35% | High (10) - Git native | Low (4) - Custom versioning | Low (5) - Manual tracking |
| Deployment Control | 30% | High (9) - PR process | Medium (6) - DB migration | Low (4) - File deployment |
| Query Performance | 20% | High (9) - Cached | High (9) - Direct | Low (4) - File I/O |
| Auditability | 15% | High (9) - Git history | Medium (6) - Change tracking | Low (3) - No history |
| **Weighted Score** | | **9.40** | **5.95** | **4.20** |

### Decision
**Version-controlled code repository with database cache**

Architecture:
1. **Source of truth**: Template files in code repository (YAML/JSON format)
2. **Database cache**: Loaded on deployment for query performance
3. **Deployment process**: PR review includes AML Compliance Manager for template changes
4. **Cache invalidation**: Application restart reloads templates
5. **Template structure**: Content with placeholders, applicable case types, version

### Rationale
- Git provides full version control with diff, review, and rollback
- PR process enables AML Compliance Manager review requirement
- Database cache provides efficient runtime queries
- Single source of truth prevents drift between code and database

### Trade-offs Accepted
- Template changes require deployment (by design per FR-054)
- Cache sync requires application restart (acceptable for infrequent changes)

### Constitution Alignment
- **Principle I (Audit Trail)**: Git history provides change audit

### Implementation Notes
```yaml
# templates/communication/kyc_information_request.yaml
id: kyc_info_request_v1
name: KYC Information Request
version: "1.0"
applicable_case_types:
  - KYC_REMEDIATION
content: |
  Dear {{customer_name}},

  We are conducting a review of your account and require the following
  documentation to proceed:

  {{required_documents}}

  Please provide these documents within {{deadline_days}} business days.

  Thank you for your cooperation.

  Spriggy Compliance Team
placeholders:
  - name: customer_name
    type: string
    required: true
  - name: required_documents
    type: string
    required: true
  - name: deadline_days
    type: integer
    default: 5
```

```python
class CommunicationTemplateService:
    def __init__(self):
        self.templates = self._load_templates()

    def _load_templates(self) -> dict:
        """Load templates from YAML files on startup."""
        templates = {}
        template_dir = Path(__file__).parent / "templates" / "communication"
        for yaml_file in template_dir.glob("*.yaml"):
            with open(yaml_file) as f:
                template = yaml.safe_load(f)
                templates[template["id"]] = template
        return templates

    def get_templates_for_case_type(self, case_type: str) -> list:
        return [t for t in self.templates.values()
                if case_type in t["applicable_case_types"]]
```

### Dependencies
- D5 (Authentication) - Template selection logged with user attribution

---

## Decision 11: Webhook Authentication

### Status
Accepted

### Context
The system receives webhooks from external services (GreenID for screening alerts, Indue for transaction monitoring alerts). These webhooks trigger case creation and potentially onboarding blocks - security-critical trust boundaries.

Without authentication:
- Attackers could inject fake sanctions alerts, blocking legitimate customers
- Spurious cases would waste analyst time and pollute audit trails
- Fraudulent SMR recommendations could be created

Gap G3 from Devil's Advocate identified this as Critical severity.

### Options Evaluated

| Criterion | Weight | HMAC Signature | IP Allowlist | mTLS |
|-----------|--------|----------------|--------------|------|
| Security | 35% | High (9) - Cryptographic verification | Medium (6) - Spoofable IPs | High (10) - Mutual auth |
| Implementation Effort | 25% | Medium (7) - Standard pattern | Low (9) - Firewall rules | High (3) - Certificate management |
| Industry Adoption | 20% | High (9) - Stripe/GitHub/etc. | Medium (6) - Legacy | Medium (5) - Enterprise |
| Operational Complexity | 15% | Low (8) - Single secret | Low (8) - Network team | High (3) - PKI infrastructure |
| Vendor Support | 5% | High (8) - Common support | High (9) - Universal | Medium (5) - Varies |
| **Weighted Score** | | **8.20** | **7.00** | **5.35** |

### Decision
**HMAC signature validation for all incoming webhooks from GreenID and Indue**

Architecture:
1. **Shared secret**: Securely exchange HMAC secret with each vendor during integration setup
2. **Signature header**: Vendors include `X-Signature-256` header with HMAC-SHA256 of request body
3. **Validation**: Webhook endpoint validates signature before any processing
4. **Rejection**: Invalid signatures return 401 Unauthorized and log security event
5. **Replay protection**: Include timestamp in signed payload; reject requests older than 5 minutes
6. **Secret rotation**: Support multiple active secrets during rotation periods

### Rationale
- HMAC is industry standard for webhook authentication (used by Stripe, GitHub, Slack)
- Cryptographically secure - cannot be forged without shared secret
- Simple implementation with no infrastructure overhead
- GreenID and Indue likely support HMAC (verify during integration); if not, IP allowlist as fallback with documented risk acceptance
- Aligns with security requirements without complexity of mTLS

### Trade-offs Accepted
- Requires secure secret exchange with vendors (one-time setup)
- Secrets must be rotated periodically (operational process)
- Vendor must support HMAC (fallback to IP allowlist if unavailable)

### Constitution Alignment
- **Principle VI (Sensitive Data Protection)**: Prevents unauthorized access to case creation
- **Principle I (Audit Trail)**: Security events logged for rejected webhooks

### Implementation Notes
```python
import hmac
import hashlib
from datetime import datetime, timedelta
from fastapi import Request, HTTPException, status

class WebhookAuthenticator:
    def __init__(self, secrets: dict[str, list[str]]):
        """
        secrets: {"greenid": ["current_secret", "previous_secret"], ...}
        Multiple secrets support rotation.
        """
        self.secrets = secrets
        self.max_age_seconds = 300  # 5 minutes replay protection

    def validate_signature(
        self,
        source: str,
        signature: str,
        timestamp: str,
        body: bytes
    ) -> bool:
        """Validate HMAC signature from webhook source."""
        # Replay protection
        try:
            ts = datetime.fromisoformat(timestamp)
            if datetime.utcnow() - ts > timedelta(seconds=self.max_age_seconds):
                return False
        except (ValueError, TypeError):
            return False

        # Try all active secrets for this source (supports rotation)
        for secret in self.secrets.get(source, []):
            expected = hmac.new(
                secret.encode(),
                f"{timestamp}.{body.decode()}".encode(),
                hashlib.sha256
            ).hexdigest()
            if hmac.compare_digest(signature, expected):
                return True
        return False

async def verify_webhook(request: Request, source: str):
    """FastAPI dependency for webhook authentication."""
    signature = request.headers.get("X-Signature-256")
    timestamp = request.headers.get("X-Timestamp")

    if not signature or not timestamp:
        audit_log.record_security_event(
            event_type="WEBHOOK_AUTH_MISSING_HEADERS",
            source=source,
            ip=request.client.host
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authentication headers"
        )

    body = await request.body()
    if not authenticator.validate_signature(source, signature, timestamp, body):
        audit_log.record_security_event(
            event_type="WEBHOOK_AUTH_INVALID_SIGNATURE",
            source=source,
            ip=request.client.host
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid webhook signature"
        )
```

### Dependencies
- D1 (Audit Trail) - Security events logged
- D3 (External Integration) - Webhook endpoints use this authentication

---

## Decision 12: PII Redaction Strategy

### Status
Accepted

### Context
Constitution Principle VI (Sensitive Data Protection) mandates "No PII in logs" as NON-NEGOTIABLE. D1 (Audit Trail Architecture) specifies comprehensive audit logging with action payloads, but did not define HOW PII is excluded.

Gap G1 from Devil's Advocate identified this as Critical severity because:
- Without concrete strategy, implementation teams make inconsistent decisions
- Customer data leaking into audit logs creates compliance and regulatory exposure
- PII fields include: customer name, email, phone, address, ID numbers, account details

### Options Evaluated

| Criterion | Weight | Structured Field List + Service Redaction | Reference-Only Entries | Encrypted PII in Audit |
|-----------|--------|-------------------------------------------|------------------------|------------------------|
| Clarity | 30% | High (9) - Explicit boundaries | Medium (6) - Implicit | Medium (7) - Hidden |
| Implementation | 25% | Medium (7) - Service layer work | High (4) - Complex queries | Low (4) - Key management |
| Auditability | 20% | High (8) - Clear what's redacted | Medium (6) - Needs joins | High (8) - Accessible if needed |
| Performance | 15% | High (9) - No joins needed | Low (5) - Join overhead | Medium (6) - Encryption overhead |
| Compliance | 10% | High (9) - Demonstrably PII-free | High (8) - No PII in table | Medium (7) - PII present, encrypted |
| **Weighted Score** | | **8.05** | **5.55** | **5.90** |

### Decision
**Structured payload with explicit PII field list and service-layer redaction**

Architecture:
1. **PII field registry**: Maintain explicit list of PII field names across all entities
2. **Service-layer redaction**: AuditService sanitizes payloads before writing to audit log
3. **Redaction marker**: Replaced fields show `[REDACTED]` to indicate data was present but removed
4. **Reference preservation**: Entity IDs (UUIDs) are NOT considered PII and are preserved for traceability
5. **Audit payload structure**: Structured JSON with before/after states, all PII redacted
6. **View access logging**: Read access logs only record case_id and user_id, not viewed content

### PII Field Registry
```python
PII_FIELDS = {
    # Customer entity
    "first_name", "last_name", "full_name", "name",
    "email", "phone", "mobile", "address",
    "date_of_birth", "dob", "birth_date",
    "tax_file_number", "tfn", "ssn",
    "driver_license", "passport_number",
    "bank_account", "bsb",

    # Communication content
    "message_content", "email_body",
    "customer_response",

    # Case investigation details (may contain customer info)
    "investigation_notes",  # Redacted in audit; full text in Case entity
}

# Fields that look like PII but are safe to log
SAFE_FIELDS = {
    "customer_id",  # UUID reference, not identifying
    "case_id",
    "user_id",
    "analyst_name",  # Internal users, not customers
}
```

### Rationale
- Explicit field list creates clear boundaries for implementation teams
- Service-layer redaction ensures consistency (single enforcement point)
- `[REDACTED]` markers preserve audit record structure while removing sensitive data
- Reference IDs enable traceability without exposing PII
- Straightforward to audit compliance: grep audit_log for PII field names should return zero results

### Trade-offs Accepted
- PII field list requires maintenance when new entities/fields are added
- Audit payloads cannot fully reconstruct original state (intentional per constitution)
- Investigation notes redacted in audit - full text must be queried from Case entity

### Constitution Alignment
- **Principle VI (Sensitive Data Protection)**: Directly implements "No PII in logs" requirement
- **Principle I (Audit Trail)**: Preserves full audit capability with redacted payloads

### Implementation Notes
```python
from typing import Any
import copy

class AuditService:
    def __init__(self, pii_fields: set[str]):
        self.pii_fields = pii_fields

    def redact_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Recursively redact PII fields from payload."""
        redacted = copy.deepcopy(payload)
        self._redact_recursive(redacted)
        return redacted

    def _redact_recursive(self, obj: Any) -> None:
        """Recursively walk dict/list and redact PII fields in place."""
        if isinstance(obj, dict):
            for key, value in obj.items():
                if key.lower() in self.pii_fields:
                    obj[key] = "[REDACTED]"
                elif isinstance(value, (dict, list)):
                    self._redact_recursive(value)
        elif isinstance(obj, list):
            for item in obj:
                self._redact_recursive(item)

    def create_audit_entry(
        self,
        case_id: str,
        user_id: str,
        action_type: str,
        action_detail: dict
    ) -> AuditLog:
        """Create audit entry with PII redacted."""
        redacted_detail = self.redact_payload(action_detail)

        return AuditLog(
            case_id=case_id,
            user_id=user_id,
            action_type=action_type,
            action_detail=redacted_detail,
            created_at=datetime.utcnow()
        )

# Example usage
audit_service = AuditService(PII_FIELDS)

# Before redaction
payload = {
    "customer_id": "uuid-123",
    "customer_name": "John Smith",
    "email": "john@example.com",
    "case_type": "KYC_REMEDIATION",
    "status_change": {"from": "Open", "to": "In Progress"}
}

# After redaction
# {
#     "customer_id": "uuid-123",  # Preserved - UUID reference
#     "customer_name": "[REDACTED]",
#     "email": "[REDACTED]",
#     "case_type": "KYC_REMEDIATION",
#     "status_change": {"from": "Open", "to": "In Progress"}
# }
```

### Dependencies
- D1 (Audit Trail) - This decision defines how D1 payloads are sanitized

---

## Decision 13: Case Queue Assignment

### Status
Accepted

### Context
Gap G2 from Devil's Advocate identified that the research document did not specify how cases are assigned to analysts. The specification references:
- US-12: Analyst dashboard with assigned cases
- FR-024/FR-025: Case ordering by SLA urgency, then creation date
- EC-006: Cases entering unassigned queue when analysts unavailable

User confirmed: **Manual claim from queue** - cases enter unassigned queue and analysts self-select.

### Options Evaluated

| Criterion | Weight | Manual Claim | Round-Robin | Workload-Balanced |
|-----------|--------|--------------|-------------|-------------------|
| Simplicity | 30% | High (9) - No algorithm | Medium (6) - Rotation logic | Low (4) - Tracking required |
| Fairness | 25% | Medium (6) - Self-selection bias | High (9) - Even distribution | High (9) - Load-based |
| Analyst Autonomy | 20% | High (10) - Full choice | Low (3) - No choice | Low (3) - No choice |
| Team Size Fit | 15% | High (9) - Perfect for small team | Medium (7) - Any size | Medium (7) - Better for large teams |
| Gaming Resistance | 10% | Medium (6) - SLA visibility helps | High (8) - No cherry-picking | High (9) - System-controlled |
| **Weighted Score** | | **8.15** | **6.45** | **5.95** |

### Decision
**Manual claim from unassigned queue with analyst self-selection**

Architecture:
1. **Unassigned queue**: All new cases enter a shared unassigned queue
2. **Queue visibility**: All analysts see the unassigned queue ordered by SLA urgency, then creation date (FIFO)
3. **Claim action**: Analyst clicks "Claim Case" to assign to themselves
4. **Optimistic locking**: Prevent race condition if two analysts claim simultaneously (first wins)
5. **SLA visibility**: Unassigned cases show SLA countdown, incentivizing timely claims
6. **Manager visibility**: Dashboard shows unassigned case count and age for oversight
7. **Escalation trigger**: Cases unassigned for configurable period (default 2 hours) trigger manager alert

### Rationale
- Simple implementation appropriate for small team (under 10 per A4)
- Analyst autonomy allows specialists to select cases matching their expertise
- SLA visibility in queue discourages cherry-picking (urgent cases are visually prominent)
- No complex assignment algorithm to maintain or debug
- Manager escalation prevents cases from being ignored

### Trade-offs Accepted
- Potential for cherry-picking easier cases (mitigated by SLA visibility and manager oversight)
- Unassigned queue requires monitoring (manager responsibility)
- May need algorithm upgrade if team scales significantly (design for extensibility)

### Constitution Alignment
- **Principle V (SLA Tracking)**: SLA visibility in queue supports timely case handling
- **Principle I (Audit Trail)**: Claim actions logged with attribution

### Implementation Notes
```python
from fastapi import Depends, HTTPException, status
from sqlalchemy import and_

class CaseQueueService:
    def __init__(self, case_repo, audit_service):
        self.case_repo = case_repo
        self.audit_service = audit_service

    def get_unassigned_cases(self, tier: str) -> list[Case]:
        """Get unassigned cases for a tier, ordered by urgency."""
        return self.case_repo.query(
            Case.assigned_user_id.is_(None),
            Case.tier == tier
        ).order_by(
            Case.sla_deadline.asc(),  # Most urgent first
            Case.created_at.asc()      # Then oldest first (FIFO)
        ).all()

    def claim_case(self, case_id: str, user_id: str, version: int) -> Case:
        """Claim unassigned case with optimistic locking."""
        result = self.case_repo.update(
            where=and_(
                Case.id == case_id,
                Case.version == version,
                Case.assigned_user_id.is_(None)  # Must be unassigned
            ),
            values={
                "assigned_user_id": user_id,
                "assigned_at": datetime.utcnow(),
                "version": version + 1
            }
        )

        if result.rowcount == 0:
            # Either version mismatch or already claimed
            current = self.case_repo.get(case_id)
            if current.assigned_user_id:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="Case already claimed by another analyst"
                )
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Case was modified, please refresh"
            )

        claimed_case = self.case_repo.get(case_id)

        self.audit_service.create_audit_entry(
            case_id=case_id,
            user_id=user_id,
            action_type="CASE_CLAIMED",
            action_detail={
                "assignment_reason": "manual_claim_from_queue"
            }
        )

        return claimed_case

    def get_unassigned_metrics(self) -> dict:
        """Get metrics for manager dashboard."""
        cases = self.case_repo.query(Case.assigned_user_id.is_(None)).all()
        now = datetime.utcnow()

        return {
            "total_unassigned": len(cases),
            "by_tier": {tier: sum(1 for c in cases if c.tier == tier)
                        for tier in ["L1", "L2"]},
            "oldest_unassigned_hours": max(
                ((now - c.created_at).total_seconds() / 3600 for c in cases),
                default=0
            ),
            "sla_at_risk": sum(1 for c in cases if c.sla_deadline < now)
        }
```

### Dependencies
- D8 (Concurrency Control) - Optimistic locking for claim operation
- D1 (Audit Trail) - Claim actions logged
- D2 (SLA Calculation) - SLA urgency drives queue ordering

---

## Dependencies Map

| Decision | Depends On | Impacts |
|----------|------------|---------|
| D1 (Audit Trail) | D4 (Document Storage), D5 (Authentication), D12 (PII Redaction) | All other decisions use audit logging |
| D2 (SLA Calculation) | - | D6 (Notifications), D13 (Case Queue) |
| D3 (External Integration) | D1 (Audit Trail), D4 (Document Storage), D11 (Webhook Auth) | - |
| D4 (Document Storage) | D1 (Audit Trail), D5 (Authentication) | D3 (External Integration) |
| D5 (Authentication) | D1 (Audit Trail) | D6 (Notifications), D4, D7, D10 |
| D6 (Notifications) | D2 (SLA Calculation), D5 (Authentication) | - |
| D7 (Reporting) | D1 (Audit Trail), D5 (Authentication) | - |
| D8 (Concurrency) | D1 (Audit Trail) | D13 (Case Queue) |
| D9 (Case Reference) | - | - |
| D10 (Templates) | D5 (Authentication) | - |
| D11 (Webhook Auth) | D1 (Audit Trail) | D3 (External Integration) |
| D12 (PII Redaction) | - | D1 (Audit Trail) |
| D13 (Case Queue) | D8 (Concurrency), D1 (Audit Trail), D2 (SLA Calculation) | - |

---

## Open Questions Resolution

| OQ ID | Question | Resolution |
|-------|----------|------------|
| OQ-002 | SLA warning thresholds | Resolved: Default 80% single warning threshold (configurable) |
| OQ-003 | Authentication system | Resolved: OIDC integration with existing Spriggy SSO (D5) |
| OQ-004 | AUSTRAC SMR format | Partially resolved: Research AUSTRAC documentation during implementation; store as PDF |

### Remaining Open Questions for Escalation

| OQ ID | Question | Impact | Recommendation |
|-------|----------|--------|----------------|
| OQ-001 | GreenID ongoing screening capability | May require batch rescreening implementation | Validate with vendor; defer to Phase 2 if unavailable |
| OQ-005 | Expected case volume | Affects queue design, performance requirements | Proceed with 50-100 cases/day assumption; design for horizontal scaling |
| OQ-006 | Customer information availability | Affects case display completeness | Define minimal required fields; add context as available |
| OQ-007 | Spriggy onboarding API contract | Required for integration implementation | Work with Spriggy engineering to define; document in contracts phase |
| OQ-008 | L2 quality review percentage | Affects L2 workload | Proceed with 10% sampling assumption; make configurable |
| OQ-009 | Available account restrictions | Affects recommendation options | Define with product team; implement as enum with extensibility |

---

## Constitution Compliance Summary

| Principle | Status | How Addressed |
|-----------|--------|---------------|
| I. Immutable Audit Trail | Compliant | D1: Append-only log with full attribution; D12: PII redaction preserves structure |
| II. RBAC with Segregation | Compliant | D5: Local RBAC with segregation enforcement |
| III. Test-First Development | N/A (Implementation) | Will guide implementation phase |
| IV. Explicit Error Handling | Compliant | D3: Circuit breaker, DLQ, retry patterns, duplicate detection |
| V. SLA Tracking | Compliant | D2: Business day calculator with SLA start at case creation; D13: Queue ordering by urgency |
| VI. Sensitive Data Protection | Compliant | D4: AES-256 encryption; D11: Webhook auth; D12: Explicit PII redaction strategy |
| VII. External Integration Resilience | Compliant | D3: 30s timeout, backoff, circuit breaker (5 failures); D11: HMAC authentication |

---

## Next Steps

1. **Data Model Phase**: Use these decisions to define entity schemas with:
   - Audit log structure with PII redaction (D1, D12)
   - Version columns for optimistic locking (D8)
   - Document metadata tables (D4)
   - Notification tables (D6)
   - WebhookReceipt table for duplicate detection (D3)
   - Case assignment tracking (D13)

2. **Contracts Phase**: Use these decisions to define API contracts with:
   - OIDC authentication flow (D5)
   - HMAC webhook authentication (D11)
   - Conflict response handling (D8)
   - Case claim endpoint (D13)
   - Async webhook receipt pattern with duplicate handling (D3)

3. **Implementation**: Apply constitution principles III (Test-First) and validate all decisions against real code patterns.
