"""
Fee (premium) leg calculation for CDS.

The fee leg is the stream of coupon payments from the protection buyer
to the protection seller. It includes:

1. Regular coupon payments (survival-weighted)
2. Accrued premium on default (optional)

This implements the ISDA standard methodology.
"""

from datetime import date

import numpy as np

from .curves import CreditCurve, ZeroCurve
from .dates import DateLike, parse_date, year_fraction
from .enums import AccrualOnDefault, DayCountConvention
from .schedule import CDSSchedule


def fee_leg_pv(
    value_date: DateLike,
    schedule: CDSSchedule,
    coupon_rate: float,
    discount_curve: ZeroCurve,
    credit_curve: CreditCurve,
    notional: float = 1.0,
    accrual_on_default: AccrualOnDefault = AccrualOnDefault.ACCRUED_TO_DEFAULT,
    integration_points: int = 20,
) -> float:
    """
    Calculate the present value of the fee (premium) leg.

    The fee leg PV consists of:
    1. Sum of expected coupon payments (weighted by survival probability)
    2. Expected accrued premium in case of default (optional)

    Args:
        value_date: Valuation date
        schedule: CDS payment schedule
        coupon_rate: Annual coupon rate (e.g., 0.01 for 100bps)
        discount_curve: Zero curve for discounting
        credit_curve: Credit curve for survival probabilities
        notional: Notional amount
        accrual_on_default: Whether to include accrual on default
        integration_points: Points per period for accrual integration

    Returns
        Present value of the fee leg (positive for protection buyer)
    """
    vd = parse_date(value_date)
    t_value = discount_curve.time_from_date(vd)

    total_pv = 0.0

    for period in schedule.periods:
        # Skip periods that end before value date
        if period.accrual_end <= vd:
            continue

        # Calculate times
        t_start = discount_curve.time_from_date(period.accrual_start)
        t_end = discount_curve.time_from_date(period.accrual_end)
        t_pay = discount_curve.time_from_date(period.payment_date)

        # Handle partial first period
        if period.accrual_start < vd:
            t_start = t_value
            yf = year_fraction(vd, period.accrual_end, schedule.day_count)
        else:
            yf = period.year_fraction

        # Regular coupon payment (survival-weighted)
        coupon_amount = notional * coupon_rate * yf

        # Discount factor at payment date
        df_pay = discount_curve.discount_factor(t_pay)

        # Survival probability at accrual end
        surv_end = credit_curve.survival_probability(t_end)

        # Regular payment PV
        regular_pv = coupon_amount * surv_end * df_pay
        total_pv += regular_pv

        # Accrual on default
        if accrual_on_default == AccrualOnDefault.ACCRUED_TO_DEFAULT:
            accrual_pv = _calculate_accrual_on_default(
                t_start, t_end, coupon_rate, notional,
                discount_curve, credit_curve,
                period.accrual_start, period.accrual_end,
                schedule.day_count, integration_points
            )
            total_pv += accrual_pv

    return total_pv


def _calculate_accrual_on_default(
    t_start: float,
    t_end: float,
    coupon_rate: float,
    notional: float,
    discount_curve: ZeroCurve,
    credit_curve: CreditCurve,
    acc_start: date,
    acc_end: date,
    day_count: DayCountConvention,
    num_points: int = 20,
) -> float:
    """
    Calculate the expected accrued premium paid on default.

    This uses numerical integration with the ISDA methodology that includes
    Taylor expansion for numerical stability when lambda + fwd_rate is small.

    From ISDA C code (feeleg.c:414-471):
    - For each sub-period, integrate the product of:
      * Probability of default in period
      * Accrued coupon at default
      * Discount factor at default
    """
    if t_end <= t_start:
        return 0.0

    # Use numerical integration with Taylor expansion
    dt = (t_end - t_start) / num_points
    pv = 0.0

    for i in range(num_points):
        t0 = t_start + i * dt
        t1 = t_start + (i + 1) * dt

        # Survival probabilities
        s0 = credit_curve.survival_probability(t0)
        s1 = credit_curve.survival_probability(t1)

        # Discount factors
        df0 = discount_curve.discount_factor(t0)
        df1 = discount_curve.discount_factor(t1)

        # Calculate lambda (hazard rate * dt) and forward rate
        # lambda_ = -ln(s1/s0) = ln(s0) - ln(s1)
        # fwd_rate = -ln(df1/df0) = ln(df0) - ln(df1)
        if s0 > 0 and s1 > 0:
            lambda_ = np.log(s0) - np.log(s1)
        else:
            lambda_ = 0.0

        if df0 > 0 and df1 > 0:
            fwd_rate = np.log(df0) - np.log(df1)
        else:
            fwd_rate = 0.0

        lambda_fwd_rate = lambda_ + fwd_rate + 1e-50  # Avoid division by zero

        # Accrued fraction at mid-point of sub-period
        t_mid = (t0 + t1) / 2
        accrued_frac = (t_mid - t_start) / (t_end - t_start)

        # Accrued coupon amount (proportional to accrued fraction)
        total_yf = year_fraction(acc_start, acc_end, day_count)
        accrued_coupon = notional * coupon_rate * total_yf * accrued_frac

        # PV contribution from this sub-period
        # This is the integral of (accrued_at_t) * (default_density) * (discount)
        if abs(lambda_fwd_rate) > 1e-4:
            # Direct calculation
            pv_sub = (
                accrued_coupon * lambda_ / lambda_fwd_rate
                * (1.0 - np.exp(-lambda_fwd_rate))
                * s0 * df0
            )
        else:
            # Taylor expansion for numerical stability
            # From ISDA C code (feeleg.c:454-467)
            pv0 = accrued_coupon * lambda_ * s0 * df0
            pv1 = -pv0 * lambda_fwd_rate * 0.5
            pv2 = -pv1 * lambda_fwd_rate / 3.0
            pv3 = -pv2 * lambda_fwd_rate * 0.25
            pv4 = -pv3 * lambda_fwd_rate * 0.2
            pv_sub = pv0 + pv1 + pv2 + pv3 + pv4

        pv += pv_sub

    return pv


def risky_annuity(
    value_date: DateLike,
    schedule: CDSSchedule,
    discount_curve: ZeroCurve,
    credit_curve: CreditCurve,
) -> float:
    """
    Calculate the risky annuity (RPV01 or risky duration).

    The risky annuity is the present value of 1bp of premium payments,
    accounting for default risk. It's the fee leg PV per unit spread.

    Args:
        value_date: Valuation date
        schedule: CDS payment schedule
        discount_curve: Zero curve for discounting
        credit_curve: Credit curve for survival probabilities

    Returns
        Risky annuity value
    """
    # Fee leg PV with 1bp coupon = risky annuity
    return fee_leg_pv(
        value_date=value_date,
        schedule=schedule,
        coupon_rate=0.0001,  # 1 basis point
        discount_curve=discount_curve,
        credit_curve=credit_curve,
        notional=1.0,
        accrual_on_default=AccrualOnDefault.ACCRUED_TO_DEFAULT,
    )


def calculate_accrued_interest(
    value_date: DateLike,
    schedule: CDSSchedule,
    coupon_rate: float,
    notional: float = 1.0,
) -> float:
    """
    Calculate accrued interest at the value date.

    Args:
        value_date: Valuation date
        schedule: CDS payment schedule
        coupon_rate: Annual coupon rate
        notional: Notional amount

    Returns
        Accrued interest (always positive for accrued premium)
    """
    vd = parse_date(value_date)

    for period in schedule.periods:
        if period.accrual_start <= vd <= period.accrual_end:
            yf = year_fraction(period.accrual_start, vd, schedule.day_count)
            return notional * coupon_rate * yf

    # Check if before first period
    if vd < schedule.periods[0].accrual_start:
        return 0.0

    # If after all periods, use last period
    last = schedule.periods[-1]
    if vd > last.accrual_end:
        yf = year_fraction(last.accrual_start, last.accrual_end, schedule.day_count)
        return notional * coupon_rate * yf

    return 0.0
