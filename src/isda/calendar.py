"""
Business day adjustment functions.
"""

from opendate import Date

from .enums import BadDayConvention


def adjust_date(
    d: Date,
    convention: BadDayConvention = BadDayConvention.MODIFIED_FOLLOWING,
) -> Date:
    """
    Adjust a date according to a bad day convention.

    Uses opendate's business day snapping:
    - .b.add(days=0) snaps forward to next business day
    - .b.subtract(days=0) snaps backward to previous business day

    MODIFIED_* variants check month boundary and reverse if crossed.

    Args:
        d: Date to adjust
        convention: Bad day convention to apply

    Returns
        Adjusted Date
    """
    if convention == BadDayConvention.NONE or d.is_business_day():
        return d

    if convention == BadDayConvention.FOLLOWING:
        return d.b.add(days=0)

    if convention == BadDayConvention.PRECEDING:
        return d.b.subtract(days=0)

    if convention == BadDayConvention.MODIFIED_FOLLOWING:
        adjusted = d.b.add(days=0)
        return d.b.subtract(days=0) if adjusted.month != d.month else adjusted

    if convention == BadDayConvention.MODIFIED_PRECEDING:
        adjusted = d.b.subtract(days=0)
        return d.b.add(days=0) if adjusted.month != d.month else adjusted

    raise ValueError(f'Unknown bad day convention: {convention}')
