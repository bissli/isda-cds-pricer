"""
Date utilities for CDS pricing.

Uses opendate.Date as the primary date type.
"""

from datetime import date, datetime
from typing import Union

from opendate import CustomCalendar, Date, register_calendar
from opendate import set_default_calendar

from .enums import DayCountConvention

# Setup weekends-only calendar as default
WEEKENDS_ONLY = CustomCalendar(
    name='WEEKENDS_ONLY',
    holidays=set(),
    weekmask='Mon Tue Wed Thu Fri',
)
register_calendar('WEEKENDS_ONLY', WEEKENDS_ONLY)
set_default_calendar('WEEKENDS_ONLY')


# Accept various date-like inputs
DateLike = Union[Date, date, datetime, str]


def to_date(d: DateLike) -> Date:
    """Convert any date-like input to opendate.Date."""
    if isinstance(d, Date):
        return d.calendar(WEEKENDS_ONLY)
    if isinstance(d, datetime):
        return Date.instance(d.date()).calendar(WEEKENDS_ONLY)
    if isinstance(d, date):
        return Date.instance(d).calendar(WEEKENDS_ONLY)
    if isinstance(d, str):
        result = Date.parse(d)
        if result is None:
            raise ValueError(f'Cannot parse date: {d}')
        return result.calendar(WEEKENDS_ONLY)
    raise TypeError(f'Expected Date, date, datetime, or string, got {type(d)}')


# Alias for backward compatibility
parse_date = to_date


def year_fraction(
    start: DateLike,
    end: DateLike,
    convention: DayCountConvention = DayCountConvention.ACT_360,
) -> float:
    """
    Calculate the year fraction between two dates.

    Args:
        start: Start date
        end: End date
        convention: Day count convention to use

    Returns
        Year fraction as a float
    """
    d1 = to_date(start)
    d2 = to_date(end)
    days = d2.diff(d1).in_days()

    if convention == DayCountConvention.ACT_360:
        return days / 360.0

    elif convention in {DayCountConvention.ACT_365F, DayCountConvention.ACT_365}:
        return days / 365.0

    elif convention == DayCountConvention.THIRTY_360:
        y1, m1, d1_day = d1.year, d1.month, d1.day
        y2, m2, d2_day = d2.year, d2.month, d2.day
        if d1_day == 31:
            d1_day = 30
        if d2_day == 31 and d1_day >= 30:
            d2_day = 30
        return (360 * (y2 - y1) + 30 * (m2 - m1) + (d2_day - d1_day)) / 360.0

    else:
        raise ValueError(f'Unknown day count convention: {convention}')


def add_days(d: DateLike, days: int) -> Date:
    """Add calendar days to a date."""
    od = to_date(d)
    return od.add(days=days) if days >= 0 else od.subtract(days=-days)


def add_months(d: DateLike, months: int) -> Date:
    """Add months to a date."""
    od = to_date(d)
    return od.add(months=months) if months >= 0 else od.subtract(months=-months)


def add_years(d: DateLike, years: int) -> Date:
    """Add years to a date."""
    od = to_date(d)
    return od.add(years=years) if years >= 0 else od.subtract(years=-years)


def add_business_days(d: DateLike, days: int) -> Date:
    """Add business days to a date."""
    od = to_date(d)
    if days == 0:
        return od
    return od.b.add(days=days) if days > 0 else od.b.subtract(days=abs(days))


def is_business_day(d: DateLike) -> bool:
    """Check if a date is a business day."""
    return to_date(d).is_business_day()
