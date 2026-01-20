"""
SLA calculator service for business day calculations.

References:
- FR-048: SLA calculation with business days
- FR-049: Case type SLA configuration
- US-9: SLA tracking and breach escalation
"""

from datetime import date, datetime, timedelta
from typing import Optional

from sqlalchemy.orm import Session

from src.models.case import CaseType
from src.models.holiday_override import HolidayOverride, HolidayScope


# Default SLA days by case type (in business days)
DEFAULT_SLA_DAYS = {
    CaseType.KYC_REMEDIATION: 5,
    CaseType.SANCTIONS_ONBOARDING: 1,  # Urgent - 1 business day
    CaseType.SANCTIONS_EXISTING_CUSTOMER: 3,  # Existing customer - 3 business days
    CaseType.PEP_HIGH_CONFIDENCE: 3,
    CaseType.PEP_LOW_CONFIDENCE: 5,
    CaseType.SANCTIONS_PEP_COMBINED: 1,  # Treat as sanctions - most urgent
    CaseType.SMR_SUPPLEMENTARY: 5,  # Supplementary SMR - 5 business days
}

# Warning threshold as percentage of SLA time elapsed
DEFAULT_WARNING_THRESHOLD = 0.75  # 75% of SLA time


class SLACalculator:
    """
    Calculator for SLA deadlines using Australian business days.

    Business days exclude:
    - Weekends (Saturday, Sunday)
    - Public holidays (from holiday_overrides table)
    """

    def __init__(self, db: Session, state: Optional[str] = None):
        """
        Initialize SLA calculator.

        Args:
            db: Database session for querying holidays
            state: Optional state code for state-specific holidays
        """
        self.db = db
        self.state = state
        self._holiday_cache: Optional[set[date]] = None

    def _load_holidays(self, start_date: date, end_date: date) -> set[date]:
        """
        Load holidays between two dates.

        Args:
            start_date: Start of date range
            end_date: End of date range

        Returns:
            Set of holiday dates
        """
        holidays = self.db.query(HolidayOverride).filter(
            HolidayOverride.holiday_date >= start_date,
            HolidayOverride.holiday_date <= end_date
        ).all()

        return {
            h.holiday_date for h in holidays
            if h.applies_to_state(self.state)
        }

    def is_business_day(self, check_date: date) -> bool:
        """
        Check if a date is a business day.

        Args:
            check_date: Date to check

        Returns:
            True if business day (not weekend, not holiday)
        """
        # Weekend check
        if check_date.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return False

        # Holiday check
        if self._holiday_cache is None:
            # Load holidays for a reasonable range
            self._holiday_cache = self._load_holidays(
                check_date - timedelta(days=30),
                check_date + timedelta(days=365)
            )

        return check_date not in self._holiday_cache

    def add_business_days(self, start_date: date, business_days: int) -> date:
        """
        Add business days to a date.

        Args:
            start_date: Starting date
            business_days: Number of business days to add

        Returns:
            Resulting date after adding business days
        """
        if business_days < 0:
            raise ValueError("business_days must be non-negative")

        current_date = start_date
        days_added = 0

        # Load holidays for expected range (generous estimate)
        max_calendar_days = business_days * 2 + 30  # Worst case
        self._holiday_cache = self._load_holidays(
            start_date,
            start_date + timedelta(days=max_calendar_days)
        )

        while days_added < business_days:
            current_date += timedelta(days=1)
            if self.is_business_day(current_date):
                days_added += 1

        return current_date

    def count_business_days(self, start_date: date, end_date: date) -> int:
        """
        Count business days between two dates (exclusive of start, inclusive of end).

        Args:
            start_date: Start date (not counted)
            end_date: End date (counted if business day)

        Returns:
            Number of business days
        """
        if end_date <= start_date:
            return 0

        self._holiday_cache = self._load_holidays(start_date, end_date)

        count = 0
        current_date = start_date + timedelta(days=1)
        while current_date <= end_date:
            if self.is_business_day(current_date):
                count += 1
            current_date += timedelta(days=1)

        return count

    def calculate_sla_deadline(
        self,
        case_type: CaseType,
        created_at: datetime,
        custom_sla_days: Optional[int] = None
    ) -> datetime:
        """
        Calculate SLA deadline for a case.

        Args:
            case_type: Type of case
            created_at: Case creation timestamp
            custom_sla_days: Override SLA days (optional)

        Returns:
            SLA deadline datetime (end of business day)
        """
        sla_days = custom_sla_days or DEFAULT_SLA_DAYS.get(case_type, 5)
        deadline_date = self.add_business_days(created_at.date(), sla_days)

        # Set deadline to end of business day (5 PM AEST)
        return datetime.combine(deadline_date, datetime.min.time().replace(hour=17))

    def calculate_warning_threshold(
        self,
        created_at: datetime,
        sla_deadline: datetime,
        threshold: float = DEFAULT_WARNING_THRESHOLD
    ) -> datetime:
        """
        Calculate when SLA warning should be triggered.

        Args:
            created_at: Case creation timestamp
            sla_deadline: SLA deadline timestamp
            threshold: Percentage of time elapsed (default 75%)

        Returns:
            Warning threshold datetime
        """
        total_seconds = (sla_deadline - created_at).total_seconds()
        warning_seconds = total_seconds * threshold
        return created_at + timedelta(seconds=warning_seconds)

    def is_approaching_breach(
        self,
        created_at: datetime,
        sla_deadline: datetime,
        current_time: Optional[datetime] = None
    ) -> bool:
        """
        Check if case is approaching SLA breach.

        Args:
            created_at: Case creation timestamp
            sla_deadline: SLA deadline timestamp
            current_time: Time to check against (default: now)

        Returns:
            True if past warning threshold but before deadline
        """
        current_time = current_time or datetime.utcnow()
        warning_time = self.calculate_warning_threshold(created_at, sla_deadline)
        return warning_time <= current_time < sla_deadline

    def is_breached(
        self,
        sla_deadline: datetime,
        current_time: Optional[datetime] = None
    ) -> bool:
        """
        Check if SLA has been breached.

        Args:
            sla_deadline: SLA deadline timestamp
            current_time: Time to check against (default: now)

        Returns:
            True if past SLA deadline
        """
        current_time = current_time or datetime.utcnow()
        return current_time >= sla_deadline

    def calculate_adjusted_deadline(
        self,
        original_deadline: datetime,
        pause_start: datetime,
        resume_time: datetime
    ) -> datetime:
        """
        Calculate adjusted SLA deadline after pause/resume.

        When SLA is paused (e.g., waiting for customer info), the deadline
        is extended by the business days the case was paused.

        Args:
            original_deadline: Original SLA deadline
            pause_start: When SLA timer was paused
            resume_time: When SLA timer resumed

        Returns:
            Adjusted deadline datetime
        """
        # Count business days during pause
        paused_business_days = self.count_business_days(
            pause_start.date(),
            resume_time.date()
        )

        # Add those business days to the original deadline
        new_deadline_date = self.add_business_days(
            original_deadline.date(),
            paused_business_days
        )

        # Preserve the time component
        return datetime.combine(new_deadline_date, original_deadline.time())

    def get_sla_days_for_case_type(self, case_type: CaseType) -> int:
        """
        Get default SLA days for a case type.

        Args:
            case_type: Type of case

        Returns:
            Default SLA days
        """
        return DEFAULT_SLA_DAYS.get(case_type, 5)
