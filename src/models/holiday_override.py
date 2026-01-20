"""
Holiday override model for SLA business day calculations.

References:
- FR-048: SLA calculation with business days
- US-9: SLA tracking and breach escalation
"""

from datetime import date
from enum import Enum
from typing import Optional
from uuid import uuid4

from sqlalchemy import Column, Date, Enum as SQLEnum, String, Text

from src.models.base import Base, DatabaseAgnosticUUID


class HolidayScope(str, Enum):
    """Scope of holiday application."""
    ALL = "ALL"  # National holiday - applies to all
    NSW = "NSW"  # New South Wales
    VIC = "VIC"  # Victoria
    QLD = "QLD"  # Queensland
    SA = "SA"  # South Australia
    WA = "WA"  # Western Australia
    TAS = "TAS"  # Tasmania
    NT = "NT"  # Northern Territory
    ACT = "ACT"  # Australian Capital Territory


class HolidayOverride(Base):
    """
    Holiday override for SLA business day calculations.

    Stores public holidays that should be excluded from SLA calculations.
    Supports both national holidays (ALL) and state-specific holidays.
    """

    __tablename__ = "holiday_overrides"

    id = Column(DatabaseAgnosticUUID, primary_key=True, default=uuid4)
    holiday_date = Column(Date, nullable=False, index=True)
    name = Column(String(255), nullable=False)
    scope = Column(SQLEnum(HolidayScope), nullable=False, default=HolidayScope.ALL)
    description = Column(Text, nullable=True)
    created_by = Column(DatabaseAgnosticUUID, nullable=True)  # User who added the holiday

    def __repr__(self) -> str:
        return f"<HolidayOverride {self.name} on {self.holiday_date} ({self.scope.value})>"

    @classmethod
    def create(
        cls,
        holiday_date: date,
        name: str,
        scope: HolidayScope = HolidayScope.ALL,
        description: Optional[str] = None,
        created_by: Optional[str] = None
    ) -> "HolidayOverride":
        """
        Create a new holiday override.

        Args:
            holiday_date: The date of the holiday
            name: Name of the holiday (e.g., "Australia Day")
            scope: Geographic scope (ALL for national, or state code)
            description: Optional description
            created_by: User ID who created the holiday

        Returns:
            New HolidayOverride instance
        """
        return cls(
            holiday_date=holiday_date,
            name=name,
            scope=scope,
            description=description,
            created_by=created_by
        )

    def applies_to_state(self, state: Optional[str]) -> bool:
        """
        Check if this holiday applies to a given state.

        Args:
            state: State code (e.g., "NSW") or None for national

        Returns:
            True if holiday applies
        """
        if self.scope == HolidayScope.ALL:
            return True
        if state is None:
            return self.scope == HolidayScope.ALL
        return self.scope.value == state

    @classmethod
    def get_australian_public_holidays_2026(cls) -> list[dict]:
        """
        Returns standard Australian public holidays for 2026.

        These can be used to seed the database with common holidays.
        Note: State-specific holidays should be added separately.
        """
        return [
            {"date": date(2026, 1, 1), "name": "New Year's Day", "scope": HolidayScope.ALL},
            {"date": date(2026, 1, 26), "name": "Australia Day", "scope": HolidayScope.ALL},
            {"date": date(2026, 4, 3), "name": "Good Friday", "scope": HolidayScope.ALL},
            {"date": date(2026, 4, 4), "name": "Easter Saturday", "scope": HolidayScope.ALL},
            {"date": date(2026, 4, 6), "name": "Easter Monday", "scope": HolidayScope.ALL},
            {"date": date(2026, 4, 25), "name": "Anzac Day", "scope": HolidayScope.ALL},
            {"date": date(2026, 6, 8), "name": "Queen's Birthday", "scope": HolidayScope.ALL},
            {"date": date(2026, 12, 25), "name": "Christmas Day", "scope": HolidayScope.ALL},
            {"date": date(2026, 12, 26), "name": "Boxing Day", "scope": HolidayScope.ALL},
        ]
