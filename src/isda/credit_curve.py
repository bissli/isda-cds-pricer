"""
Credit curve bootstrapping from CDS spreads.

Builds a credit (hazard rate) curve from par CDS spreads using
the ISDA standard methodology.
"""


import numpy as np
from opendate import Date, Interval

from .curves import CreditCurve, ZeroCurve
from .enums import DayCountConvention
from .exceptions import BootstrapError
from .root_finding import brent
from .tenor import parse_tenor


def bootstrap_credit_curve(
    base_date: Date,
    par_spreads: list[float],
    spread_tenors: list[str],
    zero_curve: ZeroCurve,
    recovery_rate: float = 0.4,
    day_count: DayCountConvention = DayCountConvention.ACT_365F,
) -> CreditCurve:
    """
    Bootstrap a credit curve from par CDS spreads.

    Uses the iterative bootstrapping methodology:
    - For each tenor, find the hazard rate that makes the par spread match

    The par spread is the spread that makes the CDS have zero NPV:
        PV(fee leg) = PV(contingent leg)

    Args:
        base_date: Curve base date
        par_spreads: List of par CDS spreads (as decimals, e.g., 0.01 for 100bps)
        spread_tenors: List of tenor strings (e.g., ['1Y', '3Y', '5Y'])
        zero_curve: Discount curve for PV calculations
        recovery_rate: Recovery rate assumption (e.g., 0.4 for 40%)
        day_count: Day count convention

    Returns
        Bootstrapped CreditCurve
    """
    if len(par_spreads) != len(spread_tenors):
        raise BootstrapError('par_spreads and spread_tenors must have same length')

    # Calculate maturity times
    times = []
    for tenor_str in spread_tenors:
        tenor = parse_tenor(tenor_str)
        mat_date = tenor.add_to_date(base_date)
        t = Interval(base_date, mat_date).yearfrac(basis=day_count.value)
        times.append(t)

    times = np.array(times)

    # Initialize credit curve
    credit_curve = CreditCurve(
        base_date=base_date,
        times=times,
        hazard_rates=np.zeros(len(times)),
        day_count=day_count,
    )

    # Bootstrap each hazard rate
    for i, (spread, t) in enumerate(zip(par_spreads, times)):
        if t <= 0:
            credit_curve._values[i] = spread / (1.0 - recovery_rate)
            continue

        try:
            hazard_rate = _bootstrap_hazard_rate(
                credit_curve, i, spread, t, zero_curve, recovery_rate
            )
            credit_curve._values[i] = hazard_rate
        except Exception as e:
            raise BootstrapError(f'Failed to bootstrap hazard rate at {spread_tenors[i]}: {e}')

    return credit_curve


def _bootstrap_hazard_rate(
    credit_curve: CreditCurve,
    idx: int,
    par_spread: float,
    maturity_time: float,
    zero_curve: ZeroCurve,
    recovery_rate: float,
) -> float:
    """
    Bootstrap a single hazard rate from a par spread.

    Finds the hazard rate that makes:
        PV(premium leg) = PV(protection leg)

    Uses a simplified approach where we approximate the legs:
        Premium leg ≈ spread * risky_annuity
        Protection leg ≈ (1 - R) * default_probability * avg_discount

    For exact pricing, we'd need payment schedules. This is a simplified
    bootstrap that works well for most cases.
    """
    loss_given_default = 1.0 - recovery_rate

    def objective(h: float) -> float:
        # Set the hazard rate
        credit_curve._values[idx] = h

        # Calculate survival probability at maturity
        surv_prob = credit_curve.survival_probability(maturity_time)

        # Calculate discount factor at maturity
        df = zero_curve.discount_factor(maturity_time)

        # Simplified premium leg PV (risky annuity approximation)
        # This is a rough approximation for bootstrapping
        risky_annuity = _calculate_risky_annuity(
            credit_curve, zero_curve, maturity_time
        )
        premium_pv = par_spread * risky_annuity

        # Simplified protection leg PV
        protection_pv = _calculate_protection_pv(
            credit_curve, zero_curve, maturity_time, loss_given_default
        )

        return premium_pv - protection_pv

    # Use Brent's method with reasonable bounds
    # Hazard rate should be positive and typically < 1 for most credits
    try:
        hazard_rate = brent(objective, 0.0001, 0.5, tol=1e-14)
    except Exception:
        # Try wider bounds
        hazard_rate = brent(objective, 1e-8, 2.0, tol=1e-12)

    return hazard_rate


def _calculate_risky_annuity(
    credit_curve: CreditCurve,
    zero_curve: ZeroCurve,
    maturity: float,
    num_periods: int = 20,
) -> float:
    """
    Calculate the risky annuity (premium leg PV per unit spread).

    Uses numerical integration with multiple time steps.
    """
    if maturity <= 0:
        return 0.0

    dt = maturity / num_periods
    risky_annuity = 0.0

    for i in range(1, num_periods + 1):
        t = i * dt
        t_prev = (i - 1) * dt

        # Average survival and discount over the period
        surv = credit_curve.survival_probability(t)
        df = zero_curve.discount_factor(t)

        # Year fraction for this period (simplified to dt for ACT/365)
        yf = dt

        risky_annuity += yf * surv * df

    return risky_annuity


def _calculate_protection_pv(
    credit_curve: CreditCurve,
    zero_curve: ZeroCurve,
    maturity: float,
    loss_given_default: float,
    num_periods: int = 20,
) -> float:
    """
    Calculate the protection leg PV.

    Uses numerical integration over the default probability distribution.
    """
    if maturity <= 0:
        return 0.0

    dt = maturity / num_periods
    protection_pv = 0.0

    for i in range(1, num_periods + 1):
        t = i * dt
        t_prev = (i - 1) * dt

        # Probability of default in this period
        surv_prev = credit_curve.survival_probability(t_prev)
        surv = credit_curve.survival_probability(t)
        default_prob = surv_prev - surv

        # Average discount factor for defaults in this period
        df = zero_curve.discount_factor((t + t_prev) / 2)

        protection_pv += loss_given_default * default_prob * df

    return protection_pv


def credit_curve_from_hazard_rates(
    base_date: Date,
    hazard_rates: list[float],
    tenors: list[str],
    day_count: DayCountConvention = DayCountConvention.ACT_365F,
) -> CreditCurve:
    """
    Build a credit curve directly from hazard rates.

    Args:
        base_date: Curve base date
        hazard_rates: List of average hazard rates
        tenors: List of tenor strings
        day_count: Day count convention

    Returns
        CreditCurve
    """
    times = []
    for tenor_str in tenors:
        tenor = parse_tenor(tenor_str)
        mat_date = tenor.add_to_date(base_date)
        t = Interval(base_date, mat_date).yearfrac(basis=day_count.value)
        times.append(t)

    return CreditCurve(base_date, np.array(times), np.array(hazard_rates), day_count)
