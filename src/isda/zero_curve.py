"""
Zero curve bootstrapping from market instruments.

Builds a zero rate curve from:
- Money market rates (deposits)
- Swap rates

Uses the standard ISDA methodology with flat forward interpolation.
"""

from datetime import date

import numpy as np

from .calendar import adjust_date
from .curves import ZeroCurve
from .dates import DateLike, add_months, parse_date, year_fraction
from .enums import BadDayConvention, DayCountConvention, PaymentFrequency
from .exceptions import BootstrapError
from .root_finding import brent
from .tenor import parse_tenor


def bootstrap_zero_curve(
    base_date: DateLike,
    swap_rates: list[float],
    swap_tenors: list[str],
    swap_maturity_dates: list[DateLike] | None = None,
    fixed_day_count: DayCountConvention = DayCountConvention.ACT_365F,
    float_day_count: DayCountConvention = DayCountConvention.ACT_360,
    fixed_frequency: PaymentFrequency = PaymentFrequency.ANNUAL,
    float_frequency: PaymentFrequency = PaymentFrequency.SEMI_ANNUAL,
    bad_day_convention: BadDayConvention = BadDayConvention.MODIFIED_FOLLOWING,
) -> ZeroCurve:
    """
    Bootstrap a zero curve from swap rates.

    This implements the standard ISDA methodology:
    1. For short tenors (< 1Y), treat rates as money market rates
    2. For longer tenors, bootstrap from swap rates

    Args:
        base_date: Curve base date
        swap_rates: List of swap/money market rates
        swap_tenors: List of tenor strings (e.g., ['1M', '3M', '1Y', '5Y'])
        swap_maturity_dates: Optional explicit maturity dates (overrides tenors)
        fixed_day_count: Day count for fixed leg
        float_day_count: Day count for floating leg
        fixed_frequency: Payment frequency for fixed leg
        float_frequency: Payment frequency for floating leg
        bad_day_convention: Bad day adjustment convention

    Returns
        Bootstrapped ZeroCurve
    """
    bd = parse_date(base_date)

    if len(swap_rates) != len(swap_tenors):
        raise BootstrapError('swap_rates and swap_tenors must have same length')

    # Parse maturity dates
    if swap_maturity_dates is not None:
        if len(swap_maturity_dates) != len(swap_rates):
            raise BootstrapError('swap_maturity_dates must match swap_rates length')
        maturity_dates = [parse_date(d) for d in swap_maturity_dates]
    else:
        # Calculate maturity dates from tenors
        maturity_dates = []
        for tenor_str in swap_tenors:
            tenor = parse_tenor(tenor_str)
            mat_date = tenor.add_to_date(bd, bad_day_convention)
            maturity_dates.append(mat_date)

    # Calculate times from base date
    times = np.array([
        year_fraction(bd, d, fixed_day_count) for d in maturity_dates
    ])

    # Initialize curve with placeholder rates
    curve = ZeroCurve(
        base_date=bd,
        times=times,
        rates=np.zeros(len(times)),
        day_count=fixed_day_count,
    )

    # Bootstrap each rate
    for i, (rate, tenor_str, mat_date) in enumerate(zip(swap_rates, swap_tenors, maturity_dates)):
        tenor = parse_tenor(tenor_str)
        t = times[i]

        if t <= 0:
            curve._values[i] = rate
            continue

        if tenor.years <= 1.0:
            # Money market rate: simple rate
            # DF = 1 / (1 + r * t)
            # Zero rate: DF = exp(-z * t)
            # So z = -ln(DF) / t = -ln(1 / (1 + r * t)) / t = ln(1 + r * t) / t
            df = 1.0 / (1.0 + rate * t)
            zero_rate = -np.log(df) / t
            curve._values[i] = zero_rate
        else:
            # Swap rate: need to bootstrap
            # For a par swap: PV(fixed) = PV(float)
            # Sum(coupon * DF_i) + notional * DF_n = notional * DF_0
            # With notional = 1 and DF_0 = 1:
            # Sum(coupon * DF_i) + DF_n = 1
            # DF_n = (1 - Sum(coupon * DF_i)) / (1 + coupon)

            try:
                zero_rate = _bootstrap_swap_rate(
                    curve, i, rate, bd, mat_date,
                    fixed_frequency, fixed_day_count
                )
                curve._values[i] = zero_rate
            except Exception as e:
                raise BootstrapError(f'Failed to bootstrap rate for {tenor_str}: {e}')

    return curve


def _bootstrap_swap_rate(
    curve: ZeroCurve,
    idx: int,
    swap_rate: float,
    base_date: date,
    maturity_date: date,
    frequency: PaymentFrequency,
    day_count: DayCountConvention,
) -> float:
    """
    Bootstrap a single swap rate to find the zero rate.

    Uses Brent's method to find the zero rate that makes the swap PV zero.
    """
    # Generate payment dates for the fixed leg
    payment_dates = _generate_payment_dates(
        base_date, maturity_date, frequency
    )

    # Calculate year fractions for each period
    year_fracs = []
    prev_date = base_date
    for pay_date in payment_dates:
        yf = year_fraction(prev_date, pay_date, day_count)
        year_fracs.append(yf)
        prev_date = pay_date

    # Objective function: find zero rate that prices swap at par
    def objective(z: float) -> float:
        # Temporarily set the rate
        curve._values[idx] = z

        # Calculate PV of fixed leg
        pv_fixed = 0.0
        for i, (pay_date, yf) in enumerate(zip(payment_dates, year_fracs)):
            t = year_fraction(base_date, pay_date, curve.day_count)
            df = curve.discount_factor(t)
            pv_fixed += swap_rate * yf * df

        # Add notional at maturity
        t_mat = year_fraction(base_date, maturity_date, curve.day_count)
        df_mat = curve.discount_factor(t_mat)
        pv_fixed += df_mat

        # For a par swap, PV should equal 1 (notional)
        return pv_fixed - 1.0

    # Use Brent's method to find the root
    # Start with reasonable bounds
    try:
        zero_rate = brent(objective, -0.5, 0.5, tol=1e-14)
    except Exception:
        # Expand bounds for extreme cases
        zero_rate = brent(objective, -1.0, 1.0, tol=1e-14)

    return zero_rate


def _generate_payment_dates(
    start_date: date,
    end_date: date,
    frequency: PaymentFrequency,
    bad_day: BadDayConvention = BadDayConvention.MODIFIED_FOLLOWING,
) -> list[date]:
    """Generate payment dates for a swap leg."""
    dates = []
    months_per_period = frequency.months

    current = start_date
    while True:
        next_date = add_months(current, months_per_period)
        if next_date >= end_date:
            dates.append(end_date)
            break
        adjusted = adjust_date(next_date, bad_day)
        dates.append(adjusted)
        current = next_date

    return dates


def build_zero_curve_from_rates(
    base_date: DateLike,
    rates: list[float],
    tenors: list[str],
    maturity_dates: list[DateLike] | None = None,
    day_count: DayCountConvention = DayCountConvention.ACT_365F,
    rate_type: str = 'swap',  # 'swap', 'zero', 'discount'
) -> ZeroCurve:
    """
    Build a zero curve from rates.

    This is a simpler interface for building curves when you don't need
    full swap curve bootstrapping.

    Args:
        base_date: Curve base date
        rates: List of rates
        tenors: List of tenor strings
        maturity_dates: Optional explicit maturity dates
        day_count: Day count convention
        rate_type: Type of rates ('swap', 'zero', or 'discount')

    Returns
        ZeroCurve
    """
    bd = parse_date(base_date)

    # Calculate maturity dates
    if maturity_dates is not None:
        mat_dates = [parse_date(d) for d in maturity_dates]
    else:
        mat_dates = []
        for tenor_str in tenors:
            tenor = parse_tenor(tenor_str)
            mat_dates.append(tenor.add_to_date(bd))

    # Calculate times
    times = np.array([year_fraction(bd, d, day_count) for d in mat_dates])

    # Convert rates to zero rates if needed
    if rate_type == 'zero':
        zero_rates = np.array(rates)
    elif rate_type == 'discount':
        # Convert discount factors to zero rates
        zero_rates = np.array([
            -np.log(df) / t if t > 0 else 0.0
            for df, t in zip(rates, times)
        ])
    else:  # 'swap' or default
        # Use full bootstrapping
        return bootstrap_zero_curve(bd, rates, tenors, maturity_dates)

    return ZeroCurve(bd, times, zero_rates, day_count)
