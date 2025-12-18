"""
Tenor parsing and manipulation.

A tenor represents a time period like "3M" (3 months), "1Y" (1 year), etc.
"""

import re
from dataclasses import dataclass
from datetime import date

from .calendar import adjust_date
from .dates import DateLike, add_days, add_months, add_years, parse_date
from .enums import BadDayConvention


@dataclass
class Tenor:
    """
    Represents a time period.

    Attributes
        value: Numeric value (e.g., 3 for "3M")
        unit: Time unit ('D', 'W', 'M', 'Y')
    """

    value: int
    unit: str

    def __post_init__(self):
        self.unit = self.unit.upper()
        if self.unit not in {'D', 'W', 'M', 'Y'}:
            raise ValueError(f'Invalid tenor unit: {self.unit}')

    def __str__(self) -> str:
        return f'{self.value}{self.unit}'

    def __repr__(self) -> str:
        return f"Tenor({self.value}, '{self.unit}')"

    @property
    def months(self) -> int:
        """Convert tenor to approximate number of months."""
        if self.unit == 'D':
            return 0
        elif self.unit == 'W':
            return 0
        elif self.unit == 'M':
            return self.value
        elif self.unit == 'Y':
            return self.value * 12
        else:
            return 0

    @property
    def days(self) -> int:
        """Convert tenor to approximate number of days."""
        if self.unit == 'D':
            return self.value
        elif self.unit == 'W':
            return self.value * 7
        elif self.unit == 'M':
            return self.value * 30  # Approximate
        elif self.unit == 'Y':
            return self.value * 365  # Approximate
        else:
            return 0

    @property
    def years(self) -> float:
        """Convert tenor to approximate number of years."""
        if self.unit == 'D':
            return self.value / 365.0
        elif self.unit == 'W':
            return self.value * 7 / 365.0
        elif self.unit == 'M':
            return self.value / 12.0
        elif self.unit == 'Y':
            return float(self.value)
        else:
            return 0.0

    def add_to_date(
        self,
        d: DateLike,
        convention: BadDayConvention = BadDayConvention.NONE,
    ) -> date:
        """
        Add this tenor to a date.

        Args:
            d: Starting date
            convention: Bad day convention to apply to result

        Returns
            Resulting date
        """
        dt = parse_date(d)

        if self.unit == 'D':
            result = add_days(dt, self.value)
        elif self.unit == 'W':
            result = add_days(dt, self.value * 7)
        elif self.unit == 'M':
            result = add_months(dt, self.value)
        elif self.unit == 'Y':
            result = add_years(dt, self.value)
        else:
            raise ValueError(f'Invalid tenor unit: {self.unit}')

        if convention != BadDayConvention.NONE:
            result = adjust_date(result, convention)

        return result


def parse_tenor(s: str) -> Tenor:
    """
    Parse a tenor string.

    Supported formats:
        - "1D", "7D" (days)
        - "1W", "2W" (weeks)
        - "1M", "3M", "6M" (months)
        - "1Y", "5Y", "10Y" (years)

    Also supports:
        - "ON" (overnight) = 1D
        - "TN" (tomorrow-next) = 2D
        - "SN" (spot-next) = 1D

    Args:
        s: Tenor string

    Returns
        Tenor object
    """
    s = s.strip().upper()

    # Special cases
    if s == 'ON':  # Overnight
        return Tenor(1, 'D')
    if s == 'TN':  # Tomorrow-next
        return Tenor(2, 'D')
    if s == 'SN':  # Spot-next
        return Tenor(1, 'D')

    # Standard format: number + unit
    match = re.match(r'^(\d+)([DWMY])$', s)
    if match:
        value = int(match.group(1))
        unit = match.group(2)
        return Tenor(value, unit)

    raise ValueError(f'Cannot parse tenor: {s}')


def tenor_to_date(
    tenor: str | Tenor,
    reference_date: DateLike,
    convention: BadDayConvention = BadDayConvention.MODIFIED_FOLLOWING,
) -> date:
    """
    Convert a tenor to a date relative to a reference date.

    Args:
        tenor: Tenor string or Tenor object
        reference_date: Base date for calculation
        convention: Bad day convention

    Returns
        Resulting date
    """
    if isinstance(tenor, str):
        tenor = parse_tenor(tenor)

    return tenor.add_to_date(reference_date, convention)


def tenor_to_years(tenor: str | Tenor) -> float:
    """Convert a tenor to approximate number of years."""
    if isinstance(tenor, str):
        tenor = parse_tenor(tenor)
    return tenor.years
