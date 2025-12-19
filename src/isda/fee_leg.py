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
    protect_start: bool = True,
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
        protect_start: If True (default), observe survival at start of day
                      This matches ISDA standard where protection starts at
                      beginning of the protection period.

    Returns
        Present value of the fee leg (positive for protection buyer)
    """
    from datetime import timedelta

    vd = parse_date(value_date)

    # ISDA uses stepin_date = today + 1 for checking if period should be included
    stepin_date = vd + timedelta(days=1)

    # obsOffset: when observing at start of day, subtract 1 from dates for survival
    # This is because survival is calculated at end of day, so to observe at start
    # of a given day, we use the previous day's end-of-day survival.
    obs_offset_days = -1 if protect_start else 0

    total_pv = 0.0
    num_periods = len(schedule.periods)

    for i, period in enumerate(schedule.periods):
        is_last_period = (i == num_periods - 1)

        # Skip periods that end before or on stepin date (ISDA convention)
        if period.accrual_end <= stepin_date:
            continue

        # Calculate times
        t_start = discount_curve.time_from_date(period.accrual_start)
        t_pay = discount_curve.time_from_date(period.payment_date)

        # For the last period with protectStart, ISDA adds 1 day to accEndDate
        # then applies obsOffset of -1, which cancels out.
        # For other periods, just apply obsOffset.
        if is_last_period and protect_start:
            # Last period: accEndDate + 1 - 1 = accEndDate (no net change)
            surv_date = period.accrual_end
        else:
            # Other periods: accEndDate + obsOffset
            surv_date = period.accrual_end + timedelta(days=obs_offset_days)

        t_surv = discount_curve.time_from_date(surv_date)
        t_end = discount_curve.time_from_date(period.accrual_end)

        # ISDA standard: for the last period with protectStart, the accrual end
        # date is extended by 1 day (line 207 in cds.c). This affects the year
        # fraction but NOT the survival calculation (which cancels out due to
        # the -1 obsOffset).
        if is_last_period and protect_start:
            # Last period: accEndDate = endDate + 1, so recalculate year fraction
            extended_end = period.accrual_end + timedelta(days=1)
            yf = year_fraction(period.accrual_start, extended_end, schedule.day_count)
        else:
            yf = period.year_fraction

        # Regular coupon payment (survival-weighted)
        coupon_amount = notional * coupon_rate * yf

        # Discount factor at payment date
        df_pay = discount_curve.discount_factor(t_pay)

        # Survival probability at observation date
        surv_end = credit_curve.survival_probability(t_surv)

        # Regular payment PV
        regular_pv = coupon_amount * surv_end * df_pay
        total_pv += regular_pv

        # Accrual on default
        if accrual_on_default == AccrualOnDefault.ACCRUED_TO_DEFAULT:
            # For accrual on default, C code also applies obsOffset to dates
            aod_start_date = period.accrual_start + timedelta(days=obs_offset_days)
            if is_last_period and protect_start:
                # Last period: accEndDate + 1 - 1 = accEndDate
                aod_end_date = period.accrual_end
            else:
                aod_end_date = period.accrual_end + timedelta(days=obs_offset_days)

            t_aod_start = discount_curve.time_from_date(aod_start_date)
            t_aod_end = discount_curve.time_from_date(aod_end_date)

            # For the last period with protectStart, use extended accrual end
            # for calculating the total accrual amount (yf includes extra day)
            if is_last_period and protect_start:
                acc_end_for_amount = period.accrual_end + timedelta(days=1)
            else:
                acc_end_for_amount = period.accrual_end

            accrual_pv = _calculate_accrual_on_default(
                t_aod_start, t_aod_end, coupon_rate, notional,
                discount_curve, credit_curve,
                period.accrual_start, acc_end_for_amount,
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

    This implements the exact ISDA methodology from feeleg.c:
    JpmcdsAccrualOnDefaultPVWithTimeLine

    The integral computes expected accrued payment in case of default,
    where accrual grows linearly with time during the period.
    """
    if t_end <= t_start:
        return 0.0

    # Total accrual time for the period (used to calculate accrual rate)
    total_yf = year_fraction(acc_start, acc_end, day_count)
    total_amount = notional * coupon_rate * total_yf

    # Accrual rate per year (amount / time in years)
    # Using 365 for time calculation as per ISDA C code
    period_days = (acc_end - acc_start).days
    acc_rate = total_amount / (period_days / 365.0)

    # Use uniform subdivision for integration
    dt = (t_end - t_start) / num_points
    pv = 0.0

    for i in range(num_points):
        # Times for this sub-interval (as curve times)
        t0_curve = t_start + i * dt
        t1_curve = t_start + (i + 1) * dt

        # Survival probabilities and discount factors at sub-interval boundaries
        s0 = credit_curve.survival_probability(t0_curve)
        s1 = credit_curve.survival_probability(t1_curve)
        df0 = discount_curve.discount_factor(t0_curve)
        df1 = discount_curve.discount_factor(t1_curve)

        # Calculate lambda and forward rate for this sub-interval
        # lambda = -ln(s1/s0) = ln(s0) - ln(s1)
        # fwd_rate = -ln(df1/df0) = ln(df0) - ln(df1)
        if s0 > 0 and s1 > 0:
            lambda_ = np.log(s0) - np.log(s1)
        else:
            lambda_ = 0.0

        if df0 > 0 and df1 > 0:
            fwd_rate = np.log(df0) - np.log(df1)
        else:
            fwd_rate = 0.0

        lambda_fwd_rate = lambda_ + fwd_rate + 1e-50

        # Calculate t0 and t1 relative to period start (in years, using 365)
        # C code adds 0.5 day adjustment for mid-day observation
        # t0 = (subStartDate + 0.5 - startDate) / 365.0
        # t1 = (tl->fArray[i] + 0.5 - startDate) / 365.0
        t0 = (t0_curve - t_start) + 0.5 / 365.0  # Add half-day adjustment
        t1 = (t1_curve - t_start) + 0.5 / 365.0
        t = t1 - t0

        if abs(lambda_fwd_rate) > 1e-4:
            # Original ISDA formula for accrual on default integral
            # thisPv = lambda * accRate * s0 * df0 * (
            #     (t0 + t/lambdafwdRate)/lambdafwdRate -
            #     (t1 + t/lambdafwdRate)/lambdafwdRate * s1/s0 * df1/df0
            # )
            term1 = (t0 + t / lambda_fwd_rate) / lambda_fwd_rate
            term2 = (t1 + t / lambda_fwd_rate) / lambda_fwd_rate * (s1 / s0) * (df1 / df0)
            pv_sub = lambda_ * acc_rate * s0 * df0 * (term1 - term2)
        else:
            # Taylor expansion for numerical stability when lambda_fwd_rate is small
            # From ISDA C code feeleg.c
            lambda_acc_rate = lambda_ * s0 * df0 * acc_rate * 0.5
            pv1 = lambda_acc_rate * (t0 + t1)

            lambda_acc_rate_lfr = lambda_acc_rate * lambda_fwd_rate / 3.0
            pv2 = -lambda_acc_rate_lfr * (t0 + 2.0 * t1)

            lambda_acc_rate_lfr2 = lambda_acc_rate_lfr * lambda_fwd_rate * 0.25
            pv3 = lambda_acc_rate_lfr2 * (t0 + 3.0 * t1)

            lambda_acc_rate_lfr3 = lambda_acc_rate_lfr2 * lambda_fwd_rate * 0.2
            pv4 = -lambda_acc_rate_lfr3 * (t0 + 4.0 * t1)

            lambda_acc_rate_lfr4 = lambda_acc_rate_lfr3 * lambda_fwd_rate / 6.0
            pv5 = lambda_acc_rate_lfr4 * (t0 + 5.0 * t1)

            pv_sub = pv1 + pv2 + pv3 + pv4 + pv5

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
    stepin_date: DateLike | None = None,
) -> float:
    """
    Calculate accrued interest at the stepin date.

    ISDA convention: Accrued interest is calculated to stepinDate (value_date + 1),
    not value_date. This is because the stepin date is when the protection buyer
    actually steps into the trade.

    Args:
        value_date: Valuation date (today)
        schedule: CDS payment schedule
        coupon_rate: Annual coupon rate
        notional: Notional amount
        stepin_date: Date for accrued calculation (default: value_date + 1)

    Returns
        Accrued interest (always positive for accrued premium)
    """
    from datetime import timedelta

    vd = parse_date(value_date)

    # ISDA convention: accrued is calculated to stepinDate, not today
    if stepin_date is None:
        ai_date = vd + timedelta(days=1)
    else:
        ai_date = parse_date(stepin_date)

    for period in schedule.periods:
        if period.accrual_start <= ai_date <= period.accrual_end:
            yf = year_fraction(period.accrual_start, ai_date, schedule.day_count)
            return notional * coupon_rate * yf
        # Also handle case where ai_date falls in extended last period
        if period == schedule.periods[-1] and period.accrual_start < ai_date:
            yf = year_fraction(period.accrual_start, ai_date, schedule.day_count)
            return notional * coupon_rate * yf

    # Check if before first period
    if ai_date < schedule.periods[0].accrual_start:
        return 0.0

    # If after all periods, use last period
    last = schedule.periods[-1]
    if ai_date > last.accrual_end:
        yf = year_fraction(last.accrual_start, last.accrual_end, schedule.day_count)
        return notional * coupon_rate * yf

    return 0.0
