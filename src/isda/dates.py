"""
Date utilities for CDS pricing.

Uses opendate.Date as the primary date type.
"""

from datetime import date, datetime
from typing import Union

from opendate import CustomCalendar, Date, register_calendar
from opendate import interval as make_interval
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

    Uses opendate's yearfrac with ISDA day count conventions:
    - ACT_360: basis=2 (Actual/360)
    - ACT_365F/ACT_365: basis=3 (Actual/365)
    - THIRTY_360: basis=0 (US 30/360)

    Args:
        start: Start date
        end: End date
        convention: Day count convention to use

    Returns:
        Year fraction as a float
    """
    d1 = to_date(start)
    d2 = to_date(end)
    iv = make_interval(d1, d2)

    # Map DayCountConvention to opendate yearfrac basis
    if convention == DayCountConvention.ACT_360:
        return iv.yearfrac(basis=2)
    elif convention in {DayCountConvention.ACT_365F, DayCountConvention.ACT_365}:
        return iv.yearfrac(basis=3)
    elif convention == DayCountConvention.THIRTY_360:
        return iv.yearfrac(basis=0)
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
