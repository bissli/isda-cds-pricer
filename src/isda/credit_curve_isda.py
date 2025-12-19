"""
ISDA-compliant credit curve bootstrapping from CDS spreads.

This module implements the exact ISDA methodology for building a credit curve
from par CDS spreads, using the same algorithm as the ISDA C library.

The key difference from the simplified bootstrap is that this version uses
the exact fee leg and contingent leg PV calculations during the bootstrap
iteration, ensuring perfect alignment with the C library results.
"""

import numpy as np
from opendate import Date, Interval

from .contingent_leg import contingent_leg_pv
from .curves import CreditCurve, ZeroCurve
from .enums import AccrualOnDefault, BadDayConvention, DayCountConvention
from .enums import PaymentFrequency
from .exceptions import BootstrapError
from .fee_leg import fee_leg_pv
from .root_finding import brent
from .schedule import generate_cds_schedule


def bootstrap_credit_curve_isda(
    base_date: Date,
    par_spread: float,
    maturity_date: Date,
    zero_curve: ZeroCurve,
    recovery_rate: float = 0.4,
    accrual_start_date: Date | None = None,
    stepin_date: Date | None = None,
    payment_frequency: PaymentFrequency = PaymentFrequency.QUARTERLY,
    day_count: DayCountConvention = DayCountConvention.ACT_360,
    bad_day_convention: BadDayConvention = BadDayConvention.FOLLOWING,
) -> CreditCurve:
    """
    Bootstrap a credit curve from a single par CDS spread.

    This implements the ISDA methodology where we find the hazard rate
    that makes the CDS with the given spread have zero NPV:
        PV(fee leg) = PV(contingent leg)

    Args:
        base_date: Curve base date (trade date)
        par_spread: Par CDS spread (as decimal, e.g., 0.01 for 100bps)
        maturity_date: CDS maturity date
        zero_curve: Discount curve for PV calculations
        recovery_rate: Recovery rate assumption (e.g., 0.4 for 40%)
        accrual_start_date: Start of first accrual period
        stepin_date: Stepin date (default: base_date + 1)
        payment_frequency: CDS payment frequency
        day_count: Day count for CDS
        bad_day_convention: Bad day adjustment

    Returns
        Bootstrapped CreditCurve with a single point at maturity
    """
    # Default stepin date to base_date + 1 (ISDA standard)
    if stepin_date is None:
        step_in = base_date.add(days=1)
    else:
        step_in = stepin_date

    # Default accrual start to a previous IMM date or start date
    if accrual_start_date is None:
        from .imm import previous_imm_date
        accrual_start = previous_imm_date(base_date)
    else:
        accrual_start = accrual_start_date

    # Calculate maturity time
    t_mat = Interval(base_date, maturity_date).yearfrac(
        basis=DayCountConvention.ACT_365F.value
    )

    # Generate the CDS schedule
    schedule = generate_cds_schedule(
        accrual_start=accrual_start,
        maturity=maturity_date,
        frequency=payment_frequency,
        day_count=day_count,
        bad_day=bad_day_convention,
    )

    # Initialize credit curve with placeholder rate
    credit_curve = CreditCurve(
        base_date=base_date,
        times=np.array([t_mat]),
        hazard_rates=np.array([0.01]),  # Initial guess
        day_count=DayCountConvention.ACT_365F,
    )

    # Objective function: find hazard rate such that CDS price = 0
    # C bootstrap uses isPriceClean=TRUE, which subtracts accrued from fee leg PV
    def objective(h: float) -> float:
        # Set the hazard rate
        credit_curve._values[0] = h

        # Calculate fee leg PV with the par spread as coupon
        # (for a par CDS, coupon = spread)
        fee_pv = fee_leg_pv(
            value_date=base_date,
            schedule=schedule,
            coupon_rate=par_spread,
            discount_curve=zero_curve,
            credit_curve=credit_curve,
            notional=1.0,
            accrual_on_default=AccrualOnDefault.ACCRUED_TO_DEFAULT,
        )

        # C bootstrap uses isPriceClean=TRUE, which subtracts accrued interest
        # from the fee leg PV. The accrued is calculated to stepinDate.
        from .fee_leg import calculate_accrued_interest
        accrued = calculate_accrued_interest(
            value_date=base_date,
            schedule=schedule,
            coupon_rate=par_spread,
            notional=1.0,
            stepin_date=step_in,
        )
        fee_pv_clean = fee_pv - accrued

        # Calculate contingent leg PV
        cont_pv = contingent_leg_pv(
            value_date=base_date,
            maturity_date=maturity_date,
            discount_curve=zero_curve,
            credit_curve=credit_curve,
            recovery_rate=recovery_rate,
            notional=1.0,
        )

        # Return the difference (should be 0 for par spread)
        # C code: *pv = pvC - pvF where pvF is clean
        return cont_pv - fee_pv_clean

    # Initial guess: spread / (1 - recovery)
    guess = par_spread / (1.0 - recovery_rate)

    # Use Brent's method to find the hazard rate
    try:
        hazard_rate = brent(objective, 0.0, 10.0, tol=1e-10)
    except Exception:
        # Try with initial guess closer to expected value
        try:
            hazard_rate = brent(objective, guess * 0.1, guess * 10, tol=1e-10)
        except Exception as e:
            raise BootstrapError(f'Failed to bootstrap credit curve: {e}')

    # Set the final hazard rate
    credit_curve._values[0] = hazard_rate

    return credit_curve


def bootstrap_credit_curve_flat(
    base_date: Date,
    par_spread: float,
    maturity_dates: list[Date],
    zero_curve: ZeroCurve,
    recovery_rate: float = 0.4,
    accrual_start_date: Date | None = None,
    payment_frequency: PaymentFrequency = PaymentFrequency.QUARTERLY,
    day_count: DayCountConvention = DayCountConvention.ACT_360,
) -> CreditCurve:
    """
    Bootstrap a flat credit curve from a single par spread applied to multiple maturities.

    This creates a credit curve with the same hazard rate at all maturities,
    matching the behavior of the C library's JpmcdsCleanSpreadCurve for a
    single-spread input.

    Args:
        base_date: Curve base date
        par_spread: Par CDS spread (decimal)
        maturity_dates: List of maturity dates for the curve
        zero_curve: Discount curve
        recovery_rate: Recovery rate
        accrual_start_date: Start of first accrual period
        payment_frequency: CDS payment frequency
        day_count: Day count for CDS

    Returns
        CreditCurve with flat hazard rate across all maturities
    """
    if not maturity_dates:
        raise BootstrapError('At least one maturity date required')

    # Use the last maturity for bootstrapping
    final_maturity = max(maturity_dates)

    # Bootstrap using final maturity
    single_point_curve = bootstrap_credit_curve_isda(
        base_date=base_date,
        par_spread=par_spread,
        maturity_date=final_maturity,
        zero_curve=zero_curve,
        recovery_rate=recovery_rate,
        accrual_start_date=accrual_start_date,
        payment_frequency=payment_frequency,
        day_count=day_count,
    )

    # Get the hazard rate from the single-point curve
    hazard_rate = single_point_curve._values[0]

    # Create multi-point curve with same hazard rate at all maturities
    times = np.array([
        Interval(base_date, d).yearfrac(basis=DayCountConvention.ACT_365F.value)
        for d in maturity_dates
    ])
    times.sort()

    return CreditCurve(
        base_date=base_date,
        times=times,
        hazard_rates=np.full(len(times), hazard_rate),
        day_count=DayCountConvention.ACT_365F,
    )
