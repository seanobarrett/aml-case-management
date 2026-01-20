<!--
SYNC IMPACT REPORT
==================
Version change: 0.0.0 → 1.0.0 (MAJOR: Initial constitution creation)

Rationale for bump:
- Initial creation establishing project governance for AML Case Management System

Modified Sections:
- None (initial creation)

Added Sections:
- Core Principles (I-XI)
- Technology Stack
- Quality Gates
- Governance

Removed Sections:
- None

Templates Alignment:
- N/A (initial creation)

Follow-up TODOs:
- Create CLAUDE.md for this project
- Set up CI pipeline to enforce quality gates
- Create .pre-commit-config.yaml

Previous Reports:
- None (initial version)
-->

# AML Case Management System Constitution

> Governing document for the AML Case Management System
> Domain: AUSTRAC AML/CTF Compliance
> Version: 1.0.0

---

## Core Principles

### I. Immutable Audit Trail (NON-NEGOTIABLE)

All case actions, state transitions, and data access MUST be recorded in append-only audit logs. No UPDATE or DELETE operations are permitted on audit records.

- AuditLog and TimelineEntry tables MUST have database-level triggers preventing UPDATE/DELETE
- All case actions MUST record: timestamp (UTC), acting user ID, action type, and action detail
- Case view access MUST be logged with user ID and timestamp
- Audit records MUST be retained for minimum 7 years per AUSTRAC requirements
- Audit export MUST produce complete, unmodified history for regulatory inspection

**Enforcement**:
- Database migration `002_audit_immutability.py` creates triggers blocking UPDATE/DELETE on audit tables
- CI runs migration tests verifying trigger behavior (UPDATE/DELETE operations MUST raise exceptions)
- Quarterly audit reviews sample cases for completeness

**Testability**:
- Pass: `pytest tests/integration/test_audit_immutability.py` exits 0
- Pass: Attempting `UPDATE audit_log SET ...` raises PostgreSQL exception
- Pass: Attempting `DELETE FROM timeline_entry WHERE ...` raises PostgreSQL exception
- Fail: Any audit record can be modified or deleted

**Rationale**: AUSTRAC regulations require complete traceability of all compliance decisions. Mutable audit logs could allow evidence tampering, creating regulatory breach and reputational risk. Immutability ensures the integrity of evidence during regulatory inspections.

---

### II. RBAC with Segregation of Duties (NON-NEGOTIABLE)

The system MUST enforce a four-tier role hierarchy (L1 Analyst, L2 Analyst, AML Compliance Manager, Read-Only) with strict segregation preventing conflicts of interest in SMR approval.

- L1 Analysts MUST NOT create or approve SMR recommendations
- L2 Analysts MUST NOT approve their own SMR recommendations
- Users MUST NOT approve recommendations they created, regardless of subsequent role changes
- Read-Only users MUST NOT modify any case data
- Role changes MUST trigger automatic case reassignment to unassigned queue

**Enforcement**:
- Middleware `auth.py` validates role permissions on every request
- Service layer checks `smr_service.py` prevent self-approval using `recommender_user_id`
- Database constraints prevent invalid role assignments
- Code review MUST verify any new endpoint includes role checks

**Testability**:
- Pass: L1 user receives 403 when attempting SMR creation endpoint
- Pass: L2 user receives 403 when attempting to approve own SMR
- Pass: User promoted from L2 to Manager cannot approve SMRs they created as L2
- Pass: Read-Only user receives 403 on all mutating endpoints
- Fail: Any bypass of role restrictions in API or service layer

**Rationale**: Segregation of duties is a core control required by AUSTRAC. Without it, a single analyst could both identify and file suspicious matter reports without independent review, creating compliance risk and potential for abuse.

---

### III. Test-First Development

All production code MUST be developed following test-first methodology. Tests MUST be written before implementation for new features and bug fixes.

- Minimum 80% code coverage for overall codebase
- 100% coverage required for SMR generation logic (`smr_service.py`)
- 100% coverage required for sanctions blocking logic (`onboarding_block_service.py`)
- 100% coverage required for SLA calculation logic (`sla_calculator.py`)
- Test files MUST accompany all new modules in the same PR

**Enforcement**:
- CI runs `pytest --cov=src --cov-fail-under=80` and blocks merge on failure
- CI runs targeted coverage checks for critical modules: `pytest --cov=src/services/smr_service --cov-fail-under=100`
- PR template includes checkbox: "Tests written before implementation"
- Code review MUST verify test coverage for new functionality

**Testability**:
- Pass: `pytest --cov=src --cov-report=term-missing` shows >= 80% coverage
- Pass: Critical modules show 100% coverage in CI report
- Pass: New PR includes test files for all new source files
- Fail: Coverage below threshold blocks merge
- Fail: New module merged without accompanying tests

**Rationale**: Tests written after implementation tend to validate what was built rather than what was intended. Test-first ensures requirements drive implementation, catches defects early when they are cheapest to fix, and produces inherently testable, modular code.

---

### IV. Explicit Error Handling

All external service calls and async operations MUST implement explicit error handling with circuit breaker, retry with backoff, and dead letter queue patterns.

- Circuit breaker MUST open after 5 consecutive failures
- Retry MUST use exponential backoff: initial 1s, max 30s, multiplier 2x
- Failed operations after retry exhaustion MUST be sent to dead letter queue
- All errors MUST be logged with correlation ID for tracing
- Error responses MUST NOT expose internal implementation details

**Enforcement**:
- Service classes MUST inherit from `BaseExternalService` which implements circuit breaker
- Celery tasks MUST use `bind=True` and implement `on_failure` handler
- Code review MUST verify error handling for any external API call
- Integration tests MUST simulate service failures

**Testability**:
- Pass: 5 consecutive failures to GreenID opens circuit breaker (verified in tests)
- Pass: Retry backoff timing matches specification (1s, 2s, 4s, 8s, 16s, 30s, 30s...)
- Pass: Failed operations appear in DLQ after retry exhaustion
- Pass: Error responses return structured error without stack traces
- Fail: Unhandled exception propagates to API response

**Rationale**: External services (GreenID, Indue, Spriggy onboarding API) will experience transient failures. Without explicit handling, these failures cascade into system unavailability. Circuit breakers prevent resource exhaustion; DLQs ensure no operations are silently lost.

---

### V. SLA Tracking with Business Day Calculation

All cases MUST track SLA deadlines using Australian business day calculations. The system MUST automatically warn and escalate on SLA approach and breach.

- SLA calculations MUST exclude weekends and Australian national holidays
- SLA start time MUST be case creation timestamp
- Warning notification MUST trigger at 80% of SLA elapsed (configurable)
- Automatic escalation MUST trigger on SLA breach
- Manager notification MUST trigger on any SLA breach

**Enforcement**:
- `sla_calculator.py` uses `holidays` library for AU holiday calendar
- Celery beat task `sla_tasks.py` runs every 15 minutes checking SLA status
- Database stores SLA deadlines as UTC timestamps
- Integration tests verify business day calculations against known holiday dates

**Testability**:
- Pass: Case created Friday 4pm, 24-hour SLA = deadline Monday 4pm (not Sunday)
- Pass: Warning notification sent when case reaches 80% of SLA
- Pass: Case auto-escalated when SLA breached
- Pass: Manager notification received on breach
- Fail: Weekend or holiday counted in SLA calculation

**Rationale**: AUSTRAC expects timely case resolution. Business day calculation ensures fair SLA tracking that accounts for non-working periods. Automatic escalation ensures visibility into aging cases before they become compliance failures.

---

### VI. Sensitive Data Protection

All PII and sensitive data MUST be protected through explicit field registry, service-layer redaction, and secure webhook authentication.

- PII fields MUST be registered in `pii_redaction.py` field registry
- Audit log content MUST redact PII before storage
- API responses MUST redact PII based on caller role
- Webhook endpoints MUST validate HMAC signatures before processing
- Sensitive data MUST NOT appear in application logs

**Enforcement**:
- `pii_redaction.py` maintains explicit list of PII field names
- `webhook_auth.py` middleware validates HMAC on webhook endpoints
- Logging configuration excludes PII fields via custom formatter
- Code review MUST verify new fields are classified for PII status

**Testability**:
- Pass: Customer name redacted in audit log content
- Pass: Webhook request without valid HMAC returns 401
- Pass: Webhook request with invalid HMAC returns 401
- Pass: Application logs contain no PII when searched
- Fail: PII field appears unredacted in logs or unauthorized responses

**Rationale**: Privacy regulations and AUSTRAC requirements mandate protection of customer data. Service-layer redaction ensures consistent application regardless of access path. HMAC authentication prevents webhook endpoint abuse.

---

### VII. External Integration Resilience

All external service integrations MUST implement timeout, retry, and health monitoring patterns.

- HTTP client timeouts MUST be set to 30 seconds maximum
- Retry MUST use exponential backoff (see Principle IV)
- Service health MUST be exposed via health check endpoint
- Failed webhook deliveries MUST be queued for retry
- Duplicate webhook detection MUST use payload hash with 24-hour window

**Enforcement**:
- `httpx` client configuration sets connect and read timeouts
- `WebhookReceipt` model stores payload hash for duplicate detection
- Health endpoint aggregates external service circuit breaker states
- Integration tests simulate timeout and retry scenarios

**Testability**:
- Pass: HTTP request times out after 30 seconds (not hanging indefinitely)
- Pass: Duplicate webhook (same payload hash within 24h) returns 200 without reprocessing
- Pass: Health endpoint reports circuit breaker states
- Fail: External service call with no timeout configuration
- Fail: Duplicate webhook creates duplicate case

**Rationale**: External services are outside our control and will experience latency, failures, and duplicate deliveries. Resilience patterns ensure the system degrades gracefully and recovers automatically without manual intervention.

---

### VIII. Type Safety and Static Analysis

All Python code MUST pass static type checking and linting without errors.

- All functions MUST have type annotations (parameters and return types)
- `mypy --strict` MUST pass with zero errors
- `ruff check .` MUST pass with zero errors
- Line length MUST NOT exceed 100 characters
- Import order MUST follow isort conventions (enforced by ruff)

**Enforcement**:
- CI runs `mypy --strict src/` and blocks merge on errors
- CI runs `ruff check .` and blocks merge on errors
- Pre-commit hooks run ruff and mypy locally
- Editor configuration encourages real-time feedback

**Testability**:
- Pass: `mypy --strict src/` exits with code 0
- Pass: `ruff check .` exits with code 0
- Pass: All functions have type annotations visible in source
- Fail: Any mypy error in CI
- Fail: Any ruff error in CI

**Rationale**: Type safety catches bugs at development time rather than runtime. In a compliance system, type errors could lead to incorrect case handling or data corruption. Static analysis provides consistent code quality without subjective review debates.

---

### IX. API Contract Stability

All API endpoints MUST follow RESTful conventions and maintain backward compatibility within major versions.

- Endpoints MUST use standard HTTP methods (GET, POST, PUT, DELETE)
- Response schemas MUST use Pydantic models with explicit field definitions
- Breaking changes MUST increment major version and require migration plan
- API documentation MUST be auto-generated from Pydantic schemas
- Error responses MUST follow consistent schema: `{"error": string, "code": string, "details": object}`

**Enforcement**:
- FastAPI auto-generates OpenAPI spec from Pydantic models
- CI validates OpenAPI spec generation succeeds
- PR template requires "API Changes" section for any endpoint modifications
- Contract tests verify response schemas match documented contracts

**Testability**:
- Pass: `/docs` endpoint renders OpenAPI documentation
- Pass: All endpoints return Pydantic-validated responses
- Pass: Error responses match standard schema
- Fail: Endpoint returns unstructured dictionary
- Fail: Breaking change without version bump

**Rationale**: The frontend will depend on stable API contracts. Inconsistent APIs create integration bugs and slow development. Auto-generated documentation ensures docs stay synchronized with implementation.

---

### X. Frontend Component Architecture (FRONTEND)

All frontend components MUST follow atomic design principles with clear separation between presentational and container components.

- Components MUST be organized: atoms, molecules, organisms, templates, pages
- Presentational components MUST be stateless and receive data via props
- Container components MUST handle state and data fetching
- Component files MUST NOT exceed 200 lines
- Shared UI components MUST live in `components/ui/` directory

**Enforcement**:
- Directory structure enforces atomic design organization
- ESLint rules flag components exceeding line limits
- Code review MUST verify component classification
- Storybook documents all presentational components

**Testability**:
- Pass: `find src/components -name "*.tsx" | xargs wc -l` shows no file > 200 lines
- Pass: Presentational components have no useState/useEffect hooks
- Pass: All atoms and molecules have Storybook stories
- Fail: Component file exceeds 200 lines without approved exception

**Rationale**: AML analysts need a consistent, predictable UI to efficiently process cases. Atomic design creates reusable components that maintain visual consistency. Line limits force decomposition into testable, maintainable units.

---

### XI. Frontend State Management (FRONTEND)

Frontend MUST implement predictable state management with clear data flow patterns.

- Server state MUST be managed via React Query (or similar) with caching
- Form state MUST be managed via React Hook Form (or similar) with validation
- UI state MUST be colocated with components unless shared across routes
- Global state MUST be minimized; prefer server-derived state
- Optimistic updates MUST handle rollback on server error

**Enforcement**:
- Code review MUST verify state management approach
- ESLint plugin for React Query patterns
- Unit tests verify optimistic update rollback behavior
- No Redux or global state stores without documented justification

**Testability**:
- Pass: API calls use React Query hooks, not raw fetch
- Pass: Forms use React Hook Form with Zod/Yup validation
- Pass: Optimistic updates revert on 4xx/5xx response
- Fail: Global state used for data that could be server-derived
- Fail: Form without client-side validation

**Rationale**: AML case management involves complex forms (EDD checklists, SMR narratives) and real-time data (case queues, SLA status). Proper state management ensures data consistency, prevents lost work, and provides responsive user experience.

---

## Technology Stack

### Backend (Implemented)

| Category | Choice | Version | Rationale |
|----------|--------|---------|-----------|
| Language | Python | 3.12 | Type hints, async support, ecosystem maturity |
| Framework | FastAPI | >=0.109.0 | Async-first, Pydantic integration, auto-documentation |
| ORM | SQLAlchemy | >=2.0.0 | Mature, type-safe 2.0 style, migration support |
| Database | PostgreSQL | 15 | JSONB, triggers for audit immutability, reliability |
| Migrations | Alembic | >=1.13.0 | SQLAlchemy native, version controlled |
| Task Queue | Celery | >=5.3.0 | Distributed tasks, beat scheduler for SLA checks |
| Cache/Broker | Redis | >=5.0.0 | Celery broker, caching, rate limiting |
| HTTP Client | httpx | >=0.26.0 | Async support, timeout configuration |
| Holidays | holidays | >=0.40 | AU business day calculations |
| Linting | ruff | >=0.1.0 | Fast, replaces flake8/isort/black |
| Type Checking | mypy | >=1.8.0 | Strict mode, comprehensive type coverage |
| Testing | pytest | >=7.4.0 | Fixtures, async support, coverage plugin |

### Frontend (Upcoming)

| Category | Choice | Version | Rationale |
|----------|--------|---------|-----------|
| Language | TypeScript | >=5.0 | Type safety, IDE support, refactoring confidence |
| Framework | React | >=18.0 | Component model, ecosystem, team familiarity |
| Build Tool | Vite | >=5.0 | Fast HMR, ES modules, optimized builds |
| Routing | React Router | >=6.0 | Standard routing, nested layouts |
| State (Server) | TanStack Query | >=5.0 | Caching, background refetch, optimistic updates |
| State (Form) | React Hook Form | >=7.0 | Performance, validation integration |
| Validation | Zod | >=3.0 | TypeScript-first, schema inference |
| UI Components | shadcn/ui | - | Radix primitives + Tailwind, accessible, customizable |
| Styling | Tailwind CSS | >=3.4 | Utility-first, works with shadcn/ui |
| Testing | Vitest | >=1.0 | Vite-native, Jest-compatible API |
| E2E Testing | Playwright | >=1.40 | Cross-browser, reliable, auto-waiting |
| Linting | ESLint | >=8.0 | TypeScript support, React plugin |
| Formatting | Prettier | >=3.0 | Consistent formatting, zero config |

---

## Quality Gates

| Gate | Requirement | Command | Enforcement |
|------|-------------|---------|-------------|
| Type Check (Backend) | Zero errors | `mypy --strict src/` | CI blocks merge |
| Lint (Backend) | Zero errors | `ruff check .` | CI blocks merge |
| Unit Tests (Backend) | All pass | `pytest tests/unit/` | CI blocks merge |
| Integration Tests | All pass | `pytest tests/integration/` | CI blocks merge |
| Coverage (Overall) | >= 80% | `pytest --cov-fail-under=80` | CI blocks merge |
| Coverage (SMR) | 100% | `pytest --cov=src/services/smr_service --cov-fail-under=100` | CI blocks merge |
| Coverage (Sanctions) | 100% | `pytest --cov=src/services/onboarding_block_service --cov-fail-under=100` | CI blocks merge |
| Type Check (Frontend) | Zero errors | `tsc --noEmit` | CI blocks merge |
| Lint (Frontend) | Zero errors | `eslint src/ --max-warnings=0` | CI blocks merge |
| Format (Frontend) | No changes | `prettier --check src/` | CI blocks merge |
| Component Tests | All pass | `vitest run` | CI blocks merge |
| E2E Tests | All pass | `playwright test` | CI blocks merge |
| Security Audit | No high/critical | `pip-audit` / `npm audit` | CI blocks merge |

---

## Governance

### Amendment Process

1. **Propose**: Create PR modifying this constitution file
2. **Document**: Include rationale for change in PR description
3. **Impact**: Assess impact on existing code and processes
4. **Review**: Obtain approval from AML Compliance Manager (for regulatory principles) or Tech Lead (for technical principles)
5. **Version**: Update version per semantic versioning rules below
6. **Sync**: Update CLAUDE.md if sync mapping applies

### Version Policy

| Bump | Trigger | Examples |
|------|---------|----------|
| **MAJOR** | Principle removed or incompatibly redefined | Removing "Immutable Audit Trail"; changing coverage from 80% to 50% |
| **MINOR** | New principle added or significant expansion | Adding new frontend principle; adding 5+ rules to existing principle |
| **PATCH** | Clarification or wording improvement | Fixing typo; rewording for clarity; adding examples |

### Exception Registry

Approved exceptions to constitution principles MUST be recorded in `.humaninloop/constitution-exceptions.md` with:

| Field | Description |
|-------|-------------|
| Exception ID | Unique identifier (EX-001, EX-002, ...) |
| Principle | Which principle is being excepted |
| Scope | What code/component the exception applies to |
| Justification | Why the exception is necessary |
| Approved By | Name and role of approver |
| Approved Date | ISO date of approval |
| Expiry | When the exception must be reviewed (or "None") |
| Tracking Issue | Link to GitHub issue if applicable |

### Compliance Review

- **Weekly**: Tech Lead reviews CI failure trends
- **Monthly**: Team reviews exception registry for expiring exceptions
- **Quarterly**: Full constitution review for relevance and completeness

---

## CLAUDE.md Synchronization

The `CLAUDE.md` file MUST be created and synchronized with this constitution when established.

**Mandatory Sync Mapping**:

| Constitution Section | CLAUDE.md Section | Sync Rule |
|---------------------|-------------------|-----------|
| Core Principles | Principles Summary | MUST list all with enforcement keywords |
| Technology Stack | Technical Stack | MUST match exactly |
| Quality Gates | Quality Gates | MUST match exactly |
| Governance | Development Workflow | MUST include versioning rules |

**Note**: CLAUDE.md does not exist yet. First sync will create it.

---

**Version**: 1.0.0 | **Ratified**: 2026-01-20 | **Last Amended**: 2026-01-20
