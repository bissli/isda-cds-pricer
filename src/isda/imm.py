"""
IMM (International Monetary Market) date generation.

IMM dates are the standard maturity dates for CDS contracts:
- 20th of March, June, September, December
- Semi-annual roll convention implemented post-2015
"""

from datetime import date, timedelta

from .dates import DateLike, add_months, parse_date

# Standard IMM months
IMM_MONTHS = (3, 6, 9, 12)

# Semi-annual roll months (March and September)
SEMI_ANNUAL_ROLL_MONTHS = (3, 9)

# IMM day of month
IMM_DAY = 20

# Date when semi-annual roll convention started
SEMI_ANNUAL_ROLL_START = date(2015, 12, 20)


def is_imm_date(d: DateLike) -> bool:
    """
    Check if a date is an IMM date.

    An IMM date is the 20th of March, June, September, or December.

    Args:
        d: Date to check

    Returns
        True if the date is an IMM date
    """
    dt = parse_date(d)
    return dt.day == IMM_DAY and dt.month in IMM_MONTHS


def next_imm_date(
    d: DateLike,
    include_current: bool = False,
    apply_semi_annual_roll: bool = True,
) -> date:
    """
    Find the next IMM date from a given date.

    Args:
        d: Reference date
        include_current: If True and d is an IMM date, return d
        apply_semi_annual_roll: Apply semi-annual roll convention (post-2015)

    Returns
        Next IMM date
    """
    dt = parse_date(d)

    # If include_current and already on an IMM date, handle it
    if include_current and is_imm_date(dt):
        if apply_semi_annual_roll and dt >= SEMI_ANNUAL_ROLL_START:
            # Apply semi-annual roll adjustment if on March or September
            if dt.month in SEMI_ANNUAL_ROLL_MONTHS:
                # Move back 3 months for semi-annual roll
                return _adjust_for_semi_annual_roll(dt)
        return dt

    # Find the next IMM date by searching forward
    current = dt + timedelta(days=1)

    while True:
        if current.day == IMM_DAY and current.month in IMM_MONTHS:
            # Found an IMM date
            if apply_semi_annual_roll and current >= SEMI_ANNUAL_ROLL_START:
                return _adjust_for_semi_annual_roll(current)
            return current
        current += timedelta(days=1)

        # Safety check - shouldn't take more than a year
        if (current - dt).days > 400:
            raise RuntimeError('Failed to find next IMM date')


def _adjust_for_semi_annual_roll(imm_date: date) -> date:
    """
    Apply semi-annual roll adjustment to an IMM date.

    Under the semi-annual roll convention (post-2015), if the IMM date
    is in March or September, we move forward to June or December.
    """
    if imm_date.month in SEMI_ANNUAL_ROLL_MONTHS:
        # Move forward 3 months to June or December
        return add_months(imm_date, 3)
    return imm_date


def previous_imm_date(d: DateLike) -> date:
    """
    Find the previous IMM date from a given date.

    Args:
        d: Reference date

    Returns
        Previous IMM date (strictly before d)
    """
    dt = parse_date(d)
    current = dt - timedelta(days=1)

    while True:
        if current.day == IMM_DAY and current.month in IMM_MONTHS:
            return current
        current -= timedelta(days=1)

        # Safety check
        if (dt - current).days > 400:
            raise RuntimeError('Failed to find previous IMM date')


def imm_date_for_tenor(
    reference_date: DateLike,
    tenor_months: int,
    apply_semi_annual_roll: bool = True,
) -> date:
    """
    Get the IMM date for a given tenor from a reference date.

    The tenor is measured from the reference date, and we find the
    next IMM date after that point.

    Args:
        reference_date: Starting date
        tenor_months: Number of months for the tenor
        apply_semi_annual_roll: Apply semi-annual roll convention

    Returns
        IMM maturity date
    """
    dt = parse_date(reference_date)
    target = add_months(dt, tenor_months)
    return next_imm_date(target, include_current=False, apply_semi_annual_roll=apply_semi_annual_roll)


def imm_dates_for_tenors(
    reference_date: DateLike,
    tenor_list: list[float],
    apply_semi_annual_roll: bool = True,
    date_format: str = '%d/%m/%Y',
) -> list[tuple[str, str]]:
    """
    Generate IMM dates for a list of tenors.

    Args:
        reference_date: Starting date
        tenor_list: List of tenors in years (e.g., [0.5, 1, 2, 3, 5, 7, 10])
        apply_semi_annual_roll: Apply semi-annual roll convention
        date_format: Output date format (empty string returns raw dates)

    Returns
        List of (tenor_label, imm_date_string) tuples

    Example:
        >>> imm_dates_for_tenors(date(2018, 1, 8), [0.5, 1, 2, 3, 5, 7])
        [('6M', '20/06/2018'), ('1Y', '20/12/2018'), ...]
    """
    dt = parse_date(reference_date)
    results = []

    for tenor_years in tenor_list:
        # Convert tenor to months
        if tenor_years < 1:
            months = int(tenor_years * 12)
            label = f'{months}M'
        else:
            months = int(tenor_years * 12)
            label = f'{int(tenor_years)}Y'

        imm = imm_date_for_tenor(dt, months, apply_semi_annual_roll)

        if date_format:
            results.append((label, imm.strftime(date_format)))
        else:
            results.append((label, imm))

    return results


def standard_imm_dates(
    reference_date: DateLike,
    num_dates: int = 4,
    apply_semi_annual_roll: bool = True,
) -> list[date]:
    """
    Generate the next N standard IMM dates.

    Args:
        reference_date: Starting date
        num_dates: Number of IMM dates to generate
        apply_semi_annual_roll: Apply semi-annual roll convention

    Returns
        List of IMM dates
    """
    dt = parse_date(reference_date)
    dates = []
    current = dt

    while len(dates) < num_dates:
        imm = next_imm_date(current, include_current=False, apply_semi_annual_roll=False)
        if apply_semi_annual_roll and imm >= SEMI_ANNUAL_ROLL_START:
            imm = _adjust_for_semi_annual_roll(imm)
        if imm not in dates:  # Avoid duplicates from roll adjustment
            dates.append(imm)
        current = imm

    return dates[:num_dates]


# Backward-compatible functions from original imm.py

def date_by_adding_business_days(from_date: DateLike, add_days: int) -> date:
    """
    Add business days to a date.

    Legacy function - prefer using calendar.add_business_days instead.
    """
    from .calendar import add_business_days as cal_add_business_days
    return cal_add_business_days(from_date, add_days)


def move_n_months(d: DateLike, start: int, n: int, direction: str = 'add') -> date:
    """
    Move a date by N months.

    Legacy recursive function - preserved for backward compatibility.

    Args:
        d: Starting date
        start: Current iteration (usually 0)
        n: Target number of months
        direction: 'add' or 'remove'

    Returns
        Date shifted by n months
    """
    dt = parse_date(d)
    if direction == 'add':
        return add_months(dt, n - start)
    else:
        return add_months(dt, -(n - start))


def next_imm(
    s_date: DateLike,
    semi_annual_roll_start: date = SEMI_ANNUAL_ROLL_START,
    imm_month_list: tuple[int, ...] = IMM_MONTHS,
    imm_semi_annual_roll_months: tuple[int, ...] = SEMI_ANNUAL_ROLL_MONTHS,
) -> date:
    """
    Find the next IMM date.

    Legacy function - preserved for backward compatibility.
    Prefer using next_imm_date instead.
    """
    return next_imm_date(s_date, include_current=False, apply_semi_annual_roll=True)


def imm_date_vector(
    start_date: DateLike,
    tenor_list: list[float] = [0.5, 1, 2, 3, 4, 5, 7, 10, 15, 20, 30],
    format: str = '%d/%m/%Y',
) -> list[tuple[str, str | date]]:
    """
    Generate IMM date vector for tenors.

    Legacy function - preserved for backward compatibility.
    Prefer using imm_dates_for_tenors instead.
    """
    return imm_dates_for_tenors(start_date, tenor_list, date_format=format)
