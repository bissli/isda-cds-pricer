"""
CDS payment schedule generation.

Generates the payment schedule for the fee (premium) leg of a CDS,
following ISDA standard conventions.
"""

from dataclasses import dataclass
from datetime import date

from .calendar import adjust_date
from .dates import DateLike, add_months, parse_date, year_fraction
from .enums import BadDayConvention, DayCountConvention, PaymentFrequency
from .enums import StubMethod


@dataclass
class CouponPeriod:
    """
    Represents a single coupon payment period.

    Attributes
        accrual_start: Start of accrual period
        accrual_end: End of accrual period
        payment_date: Date when payment is made
        year_fraction: Year fraction for this period
    """

    accrual_start: date
    accrual_end: date
    payment_date: date
    year_fraction: float

    def __repr__(self) -> str:
        return (
            f'CouponPeriod({self.accrual_start}, {self.accrual_end}, '
            f'yf={self.year_fraction:.6f})'
        )


class CDSSchedule:
    """
    A CDS payment schedule.

    Contains all coupon periods from the accrual start date to maturity.
    """

    def __init__(
        self,
        accrual_start: DateLike,
        maturity: DateLike,
        frequency: PaymentFrequency = PaymentFrequency.QUARTERLY,
        day_count: DayCountConvention = DayCountConvention.ACT_360,
        bad_day: BadDayConvention = BadDayConvention.MODIFIED_FOLLOWING,
        stub_method: StubMethod = StubMethod.FRONT_SHORT,
    ):
        """
        Create a CDS payment schedule.

        Args:
            accrual_start: Start of first accrual period (typically previous IMM date)
            maturity: CDS maturity date
            frequency: Payment frequency (typically quarterly for CDS)
            day_count: Day count convention (typically ACT/360 for CDS)
            bad_day: Business day adjustment
            stub_method: How to handle stub periods
        """
        self.accrual_start = parse_date(accrual_start)
        self.maturity = parse_date(maturity)
        self.frequency = frequency
        self.day_count = day_count
        self.bad_day = bad_day
        self.stub_method = stub_method

        self._periods: list[CouponPeriod] = []
        self._generate_schedule()

    def _generate_schedule(self) -> None:
        """Generate the payment schedule."""
        self._periods = []

        months_per_period = self.frequency.months

        if self.stub_method in {StubMethod.FRONT_SHORT, StubMethod.FRONT_LONG}:
            # Generate backwards from maturity
            unadj_dates = self._generate_dates_backward(
                self.accrual_start, self.maturity, months_per_period
            )
        else:
            # Generate forwards from accrual start
            unadj_dates = self._generate_dates_forward(
                self.accrual_start, self.maturity, months_per_period
            )

        # Build periods from dates
        for i in range(len(unadj_dates) - 1):
            acc_start = unadj_dates[i]
            acc_end = unadj_dates[i + 1]

            # Adjust payment date (accrual end is the payment date)
            pay_date = adjust_date(acc_end, self.bad_day)

            # Calculate year fraction
            yf = year_fraction(acc_start, acc_end, self.day_count)

            self._periods.append(CouponPeriod(
                accrual_start=acc_start,
                accrual_end=acc_end,
                payment_date=pay_date,
                year_fraction=yf,
            ))

    def _generate_dates_backward(
        self, start: date, end: date, months: int
    ) -> list[date]:
        """Generate dates backward from end to start."""
        dates = [end]
        current = end

        while True:
            prev = add_months(current, -months)
            if prev <= start:
                dates.append(start)
                break
            dates.append(prev)
            current = prev

        dates.reverse()
        return dates

    def _generate_dates_forward(
        self, start: date, end: date, months: int
    ) -> list[date]:
        """Generate dates forward from start to end."""
        dates = [start]
        current = start

        while True:
            next_date = add_months(current, months)
            if next_date >= end:
                dates.append(end)
                break
            dates.append(next_date)
            current = next_date

        return dates

    @property
    def periods(self) -> list[CouponPeriod]:
        """List of coupon periods."""
        return self._periods

    def __len__(self) -> int:
        return len(self._periods)

    def __iter__(self):
        return iter(self._periods)

    def __getitem__(self, idx: int) -> CouponPeriod:
        return self._periods[idx]


def generate_cds_schedule(
    accrual_start: DateLike,
    maturity: DateLike,
    frequency: PaymentFrequency = PaymentFrequency.QUARTERLY,
    day_count: DayCountConvention = DayCountConvention.ACT_360,
    bad_day: BadDayConvention = BadDayConvention.MODIFIED_FOLLOWING,
) -> CDSSchedule:
    """
    Generate a CDS payment schedule.

    This is the standard function for creating CDS schedules following
    ISDA conventions.

    Args:
        accrual_start: Start of first accrual period
        maturity: CDS maturity date
        frequency: Payment frequency (default: quarterly)
        day_count: Day count convention (default: ACT/360)
        bad_day: Business day convention (default: Modified Following)

    Returns
        CDSSchedule with all coupon periods
    """
    return CDSSchedule(
        accrual_start=accrual_start,
        maturity=maturity,
        frequency=frequency,
        day_count=day_count,
        bad_day=bad_day,
    )


def get_accrued_days(
    value_date: DateLike,
    schedule: CDSSchedule,
) -> tuple[int, int]:
    """
    Calculate accrued days and period days for a value date.

    Args:
        value_date: The valuation date
        schedule: CDS payment schedule

    Returns
        Tuple of (accrued_days, period_days) for the current period
    """
    vd = parse_date(value_date)

    for period in schedule.periods:
        if period.accrual_start <= vd < period.accrual_end:
            accrued_days = (vd - period.accrual_start).days
            period_days = (period.accrual_end - period.accrual_start).days
            return accrued_days, period_days

    # If value date is before first period
    if vd < schedule.periods[0].accrual_start:
        return 0, 0

    # If value date is after last period
    last = schedule.periods[-1]
    accrued_days = (vd - last.accrual_start).days
    period_days = (last.accrual_end - last.accrual_start).days
    return accrued_days, period_days


def calculate_accrued_interest(
    value_date: DateLike,
    schedule: CDSSchedule,
    coupon_rate: float,
    notional: float = 1.0,
) -> float:
    """
    Calculate accrued interest at a given date.

    Args:
        value_date: The valuation date
        schedule: CDS payment schedule
        coupon_rate: Annual coupon rate (e.g., 0.01 for 100bps)
        notional: Notional amount (default 1.0)

    Returns
        Accrued interest amount
    """
    vd = parse_date(value_date)

    for period in schedule.periods:
        if period.accrual_start <= vd <= period.accrual_end:
            # Calculate year fraction to value date
            yf = year_fraction(period.accrual_start, vd, schedule.day_count)
            return notional * coupon_rate * yf

    return 0.0
