"""
Business day adjustment functions.

Most functionality is in dates.py - this provides bad day conventions.
"""

from datetime import date

from opendate import Date, CustomCalendar

from .dates import DateLike, to_date, is_business_day, add_business_days, WEEKENDS_ONLY
from .enums import BadDayConvention


def adjust_date(
    d: DateLike,
    convention: BadDayConvention = BadDayConvention.MODIFIED_FOLLOWING,
) -> Date:
    """
    Adjust a date according to a bad day convention.

    Args:
        d: Date to adjust
        convention: Bad day convention to apply

    Returns:
        Adjusted Date
    """
    od = to_date(d)

    if convention == BadDayConvention.NONE:
        return od

    if od.is_business_day():
        return od

    if convention == BadDayConvention.FOLLOWING:
        return od.b.add(days=0)

    elif convention == BadDayConvention.MODIFIED_FOLLOWING:
        adjusted = od.b.add(days=0)
        if adjusted.month != od.month:
            return od.b.subtract(days=0)
        return adjusted

    elif convention == BadDayConvention.PRECEDING:
        return od.b.subtract(days=0)

    elif convention == BadDayConvention.MODIFIED_PRECEDING:
        adjusted = od.b.subtract(days=0)
        if adjusted.month != od.month:
            return od.b.add(days=0)
        return adjusted

    else:
        raise ValueError(f'Unknown bad day convention: {convention}')


def business_days_between(start: DateLike, end: DateLike) -> int:
    """Count business days between two dates (excludes start, includes end)."""
    d1 = to_date(start)
    d2 = to_date(end)
    if d1 >= d2:
        return 0
    count = 0
    current = add_business_days(d1, 1)
    while current <= d2:
        count += 1
        current = add_business_days(current, 1)
    return count


# Backward compatibility - Calendar class
class Calendar:
    """Calendar class for backward compatibility."""

    def __init__(self, holidays: set[date] | None = None):
        self._holidays = holidays.copy() if holidays else set()
        if holidays:
            self._cal = CustomCalendar(name='custom', holidays=holidays)
        else:
            self._cal = WEEKENDS_ONLY

    def is_business_day(self, d: DateLike) -> bool:
        od = to_date(d).calendar(self._cal)
        return od.is_business_day()

    def is_holiday(self, d: DateLike) -> bool:
        od = to_date(d)
        return date(od.year, od.month, od.day) in self._holidays

    def is_weekend(self, d: DateLike) -> bool:
        return to_date(d).weekday() >= 5

    def add_holiday(self, d: DateLike) -> None:
        od = to_date(d)
        self._holidays.add(date(od.year, od.month, od.day))
        self._cal = CustomCalendar(name='custom', holidays=self._holidays)

    def add_holidays(self, holidays: set[DateLike]) -> None:
        for h in holidays:
            od = to_date(h)
            self._holidays.add(date(od.year, od.month, od.day))
        self._cal = CustomCalendar(name='custom', holidays=self._holidays)

    def adjust(
        self, d: DateLike, convention: BadDayConvention = BadDayConvention.MODIFIED_FOLLOWING
    ) -> Date:
        return adjust_date(d, convention)

    def add_business_days(self, d: DateLike, days: int) -> Date:
        od = to_date(d).calendar(self._cal)
        if days == 0:
            return od
        return od.b.add(days=days) if days > 0 else od.b.subtract(days=abs(days))

    def business_days_between(self, start: DateLike, end: DateLike) -> int:
        d1 = to_date(start)
        d2 = to_date(end)
        if d1 >= d2:
            return 0
        count = 0
        current = self.add_business_days(d1, 1)
        while current <= d2:
            count += 1
            current = self.add_business_days(current, 1)
        return count


DEFAULT_CALENDAR = Calendar()
