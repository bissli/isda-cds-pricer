"""
Enumeration types for the ISDA CDS pricer.

These enums define the standard conventions used in CDS pricing.
"""

from enum import Enum, auto


class DayCountConvention(Enum):
    """Day count conventions for calculating year fractions.

    Values correspond to opendate Interval.yearfrac() basis parameter:
    - 0 = US (NASD) 30/360
    - 2 = Actual/360
    - 3 = Actual/365
    """

    ACT_360 = 2       # Actual/360 - opendate basis=2
    ACT_365F = 3      # Actual/365 Fixed - opendate basis=3
    ACT_365 = 3       # Alias for ACT/365F
    THIRTY_360 = 0    # US 30/360 - opendate basis=0

    @classmethod
    def from_string(cls, s: str) -> 'DayCountConvention':
        """Parse a day count convention from string."""
        mapping = {
            'ACT/360': cls.ACT_360,
            'ACT360': cls.ACT_360,
            'A360': cls.ACT_360,
            'ACT/365F': cls.ACT_365F,
            'ACT/365': cls.ACT_365F,
            'ACT365': cls.ACT_365F,
            'ACT365F': cls.ACT_365F,
            'A365': cls.ACT_365F,
            'A365F': cls.ACT_365F,
            '30/360': cls.THIRTY_360,
            '30360': cls.THIRTY_360,
        }
        key = s.upper().replace(' ', '')
        if key not in mapping:
            raise ValueError(f'Unknown day count convention: {s}')
        return mapping[key]


class BadDayConvention(Enum):
    """Business day adjustment conventions."""

    NONE = auto()           # No adjustment
    FOLLOWING = auto()      # Move to next business day
    MODIFIED_FOLLOWING = auto()  # Move to next business day, unless it crosses month boundary
    PRECEDING = auto()      # Move to previous business day
    MODIFIED_PRECEDING = auto()  # Move to previous business day, unless it crosses month boundary

    @classmethod
    def from_string(cls, s: str) -> 'BadDayConvention':
        """Parse a bad day convention from string."""
        mapping = {
            'NONE': cls.NONE,
            'N': cls.NONE,
            'FOLLOWING': cls.FOLLOWING,
            'F': cls.FOLLOWING,
            'MODIFIED_FOLLOWING': cls.MODIFIED_FOLLOWING,
            'MODFOLLOWING': cls.MODIFIED_FOLLOWING,
            'MF': cls.MODIFIED_FOLLOWING,
            'PRECEDING': cls.PRECEDING,
            'P': cls.PRECEDING,
            'MODIFIED_PRECEDING': cls.MODIFIED_PRECEDING,
            'MODPRECEDING': cls.MODIFIED_PRECEDING,
            'MP': cls.MODIFIED_PRECEDING,
        }
        key = s.upper().replace(' ', '').replace('_', '')
        # Try with underscores too
        for k, v in mapping.items():
            if key == k.replace('_', ''):
                return v
        raise ValueError(f'Unknown bad day convention: {s}')


class StubMethod(Enum):
    """Stub period conventions for CDS schedules."""

    FRONT_SHORT = auto()    # Short first period
    FRONT_LONG = auto()     # Long first period
    BACK_SHORT = auto()     # Short last period
    BACK_LONG = auto()      # Long last period

    @classmethod
    def from_string(cls, s: str) -> 'StubMethod':
        """Parse a stub method from string."""
        mapping = {
            'FRONT_SHORT': cls.FRONT_SHORT,
            'FRONTSHORT': cls.FRONT_SHORT,
            'SHORT_FRONT': cls.FRONT_SHORT,
            'FRONT_LONG': cls.FRONT_LONG,
            'FRONTLONG': cls.FRONT_LONG,
            'LONG_FRONT': cls.FRONT_LONG,
            'BACK_SHORT': cls.BACK_SHORT,
            'BACKSHORT': cls.BACK_SHORT,
            'SHORT_BACK': cls.BACK_SHORT,
            'BACK_LONG': cls.BACK_LONG,
            'BACKLONG': cls.BACK_LONG,
            'LONG_BACK': cls.BACK_LONG,
        }
        key = s.upper().replace(' ', '').replace('_', '')
        for k, v in mapping.items():
            if key == k.replace('_', ''):
                return v
        raise ValueError(f'Unknown stub method: {s}')


class AccrualOnDefault(Enum):
    """How to handle accrued premium when default occurs."""

    NONE = auto()              # No accrued premium on default
    ACCRUED_TO_DEFAULT = auto()  # Pay accrued premium up to default date

    @classmethod
    def from_string(cls, s: str) -> 'AccrualOnDefault':
        """Parse accrual on default setting from string."""
        mapping = {
            'NONE': cls.NONE,
            'FALSE': cls.NONE,
            'NO': cls.NONE,
            '0': cls.NONE,
            'ACCRUED': cls.ACCRUED_TO_DEFAULT,
            'ACCRUEDTODEFAULT': cls.ACCRUED_TO_DEFAULT,
            'TRUE': cls.ACCRUED_TO_DEFAULT,
            'YES': cls.ACCRUED_TO_DEFAULT,
            '1': cls.ACCRUED_TO_DEFAULT,
        }
        key = s.upper().replace(' ', '').replace('_', '')
        for k, v in mapping.items():
            if key == k.replace('_', ''):
                return v
        raise ValueError(f'Unknown accrual on default setting: {s}')


class PaymentFrequency(Enum):
    """Payment frequency for CDS fee leg."""

    QUARTERLY = 3    # Standard CDS payment frequency
    SEMI_ANNUAL = 6
    ANNUAL = 12
    MONTHLY = 1

    @property
    def months(self) -> int:
        """Return the number of months between payments."""
        return self.value

    @classmethod
    def from_string(cls, s: str) -> 'PaymentFrequency':
        """Parse payment frequency from string."""
        mapping = {
            'Q': cls.QUARTERLY,
            'QUARTERLY': cls.QUARTERLY,
            '3M': cls.QUARTERLY,
            'S': cls.SEMI_ANNUAL,
            'SEMIANNUAL': cls.SEMI_ANNUAL,
            'SEMI-ANNUAL': cls.SEMI_ANNUAL,
            '6M': cls.SEMI_ANNUAL,
            'A': cls.ANNUAL,
            'ANNUAL': cls.ANNUAL,
            '1Y': cls.ANNUAL,
            '12M': cls.ANNUAL,
            'M': cls.MONTHLY,
            'MONTHLY': cls.MONTHLY,
            '1M': cls.MONTHLY,
        }
        key = s.upper().replace(' ', '').replace('_', '')
        if key not in mapping:
            raise ValueError(f'Unknown payment frequency: {s}')
        return mapping[key]
