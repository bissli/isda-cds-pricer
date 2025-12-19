"""
IMM (International Monetary Market) date generation.

IMM dates are the standard maturity dates for CDS contracts:
- 20th of March, June, September, December
- Semi-annual roll convention implemented post-2015
"""

from opendate import Date, Interval

# Standard IMM months
IMM_MONTHS = (3, 6, 9, 12)

# Semi-annual roll months (March and September)
SEMI_ANNUAL_ROLL_MONTHS = (3, 9)

# IMM day of month
IMM_DAY = 20

# Date when semi-annual roll convention started
SEMI_ANNUAL_ROLL_START = Date(2015, 12, 20)


def is_imm_date(d: Date) -> bool:
    """
    Check if a date is an IMM date.

    An IMM date is the 20th of March, June, September, or December.

    Args:
        d: Date to check

    Returns
        True if the date is an IMM date
    """
    return d.day == IMM_DAY and d.month in IMM_MONTHS


def next_imm_date(
    d: Date,
    include_current: bool = False,
    apply_semi_annual_roll: bool = True,
) -> Date:
    """
    Find the next IMM date from a given date.

    Args:
        d: Reference date (Date object)
        include_current: If True and d is an IMM date, return d
        apply_semi_annual_roll: Apply semi-annual roll convention (post-2015)

    Returns
        Next IMM date
    """
    # If include_current and already on an IMM date, handle it
    if include_current and is_imm_date(d):
        if apply_semi_annual_roll and d >= SEMI_ANNUAL_ROLL_START:
            # Apply semi-annual roll adjustment if on March or September
            if d.month in SEMI_ANNUAL_ROLL_MONTHS:
                # Move back 3 months for semi-annual roll
                return _adjust_for_semi_annual_roll(d)
        return d

    # Find the next IMM date by searching forward
    current = d.add(days=1)

    while True:
        if current.day == IMM_DAY and current.month in IMM_MONTHS:
            # Found an IMM date
            if apply_semi_annual_roll and current >= SEMI_ANNUAL_ROLL_START:
                return _adjust_for_semi_annual_roll(current)
            return current
        current = current.add(days=1)

        # Safety check - shouldn't take more than a year
        if Interval(d, current).days > 400:
            raise RuntimeError('Failed to find next IMM date')


def _adjust_for_semi_annual_roll(imm_date: Date) -> Date:
    """
    Apply semi-annual roll adjustment to an IMM date.

    Under the semi-annual roll convention (post-2015), if the IMM date
    is in March or September, we move forward to June or December.
    """
    if imm_date.month in SEMI_ANNUAL_ROLL_MONTHS:
        # Move forward 3 months to June or December
        return imm_date.add(months=3)
    return imm_date


def previous_imm_date(d: Date) -> Date:
    """
    Find the previous IMM date from a given date.

    Args:
        d: Reference date (Date object)

    Returns
        Previous IMM date (strictly before d)
    """
    current = d.subtract(days=1)

    while True:
        if current.day == IMM_DAY and current.month in IMM_MONTHS:
            return current
        current = current.subtract(days=1)

        # Safety check
        if Interval(current, d).days > 400:
            raise RuntimeError('Failed to find previous IMM date')


def imm_date_for_tenor(
    reference_date: Date,
    tenor_months: int,
    apply_semi_annual_roll: bool = True,
) -> Date:
    """
    Get the IMM date for a given tenor from a reference date.

    The tenor is measured from the reference date, and we find the
    next IMM date after that point.

    Args:
        reference_date: Starting date (Date object)
        tenor_months: Number of months for the tenor
        apply_semi_annual_roll: Apply semi-annual roll convention

    Returns
        IMM maturity date
    """
    target = reference_date.add(months=tenor_months) if tenor_months >= 0 else reference_date.subtract(months=-tenor_months)
    return next_imm_date(target, include_current=False, apply_semi_annual_roll=apply_semi_annual_roll)


def imm_dates_for_tenors(
    reference_date: Date,
    tenor_list: list[float],
    apply_semi_annual_roll: bool = True,
    date_format: str = '%d/%m/%Y',
) -> list[tuple[str, str]]:
    """
    Generate IMM dates for a list of tenors.

    Args:
        reference_date: Starting date (Date object)
        tenor_list: List of tenors in years (e.g., [0.5, 1, 2, 3, 5, 7, 10])
        apply_semi_annual_roll: Apply semi-annual roll convention
        date_format: Output date format (empty string returns raw dates)

    Returns
        List of (tenor_label, imm_date_string) tuples

    Example:
        >>> imm_dates_for_tenors(Date(2018, 1, 8), [0.5, 1, 2, 3, 5, 7])
        [('6M', '20/06/2018'), ('1Y', '20/12/2018'), ...]
    """
    results = []

    for tenor_years in tenor_list:
        # Convert tenor to months
        if tenor_years < 1:
            months = int(tenor_years * 12)
            label = f'{months}M'
        else:
            months = int(tenor_years * 12)
            label = f'{int(tenor_years)}Y'

        imm = imm_date_for_tenor(reference_date, months, apply_semi_annual_roll)

        if date_format:
            results.append((label, imm.strftime(date_format)))
        else:
            results.append((label, imm))

    return results


def imm_date_vector(
    start_date: Date,
    tenor_list: list[float] = [0.5, 1, 2, 3, 4, 5, 7, 10, 15, 20, 30],
    format: str = '%d/%m/%Y',
) -> list[tuple[str, str | Date]]:
    """
    Generate IMM date vector for tenors.

    Legacy function - preserved for backward compatibility.
    Prefer using imm_dates_for_tenors instead.
    """
    return imm_dates_for_tenors(start_date, tenor_list, date_format=format)
