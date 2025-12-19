"""
Contingent (protection) leg calculation for CDS.

The contingent leg is the payment from the protection seller to the
protection buyer upon default. It equals:
    (1 - Recovery Rate) * Notional

This implements the ISDA standard methodology with Taylor expansion
for numerical stability.
"""

import numpy as np

from .curves import CreditCurve, ZeroCurve
from .dates import DateLike, parse_date


def contingent_leg_pv(
    value_date: DateLike,
    maturity_date: DateLike,
    discount_curve: ZeroCurve,
    credit_curve: CreditCurve,
    recovery_rate: float = 0.4,
    notional: float = 1.0,
    integration_points: int = 100,
    protection_start_date: DateLike | None = None,
    protect_start: bool = True,
) -> float:
    """
    Calculate the present value of the contingent (protection) leg.

    The protection leg pays (1 - R) * N upon default. The PV is:

        PV = (1 - R) * N * ∫₀ᵀ λ(t) * Q(t) * DF(t) dt

    where:
        λ(t) = instantaneous hazard rate
        Q(t) = survival probability
        DF(t) = discount factor

    This uses the ISDA methodology with numerical integration and
    Taylor expansion for stability when lambda + forward_rate is small.

    Args:
        value_date: Valuation date
        maturity_date: CDS maturity date
        discount_curve: Zero curve for discounting
        credit_curve: Credit curve for survival probabilities
        recovery_rate: Recovery rate (e.g., 0.4 for 40%)
        notional: Notional amount
        integration_points: Number of integration points
        protection_start_date: Start of protection period. If None, uses
                              value_date + 1 (stepin_date) per ISDA convention.
        protect_start: If True (default), protection starts at beginning of day

    Returns
        Present value of the contingent leg (positive value)
    """

    vd = parse_date(value_date)
    mat = parse_date(maturity_date)

    # ISDA logic for protection start:
    # When protectStart = TRUE (default):
    #   offset = 1
    #   startDate = MAX(cl->startDate, stepinDate - offset)
    #   startDate = MAX(startDate, today - offset)
    # This effectively means protection starts from MAX(accrual_start, today)
    # when protectStart is TRUE.
    if protection_start_date is None:
        # Default: protection starts from value_date (today)
        # This matches ISDA logic: MAX(cl->startDate, stepinDate - 1) = today
        prot_start = vd
    else:
        prot_start = parse_date(protection_start_date)

    # Calculate times for integration
    t_start = discount_curve.time_from_date(prot_start)
    t_end = discount_curve.time_from_date(mat)

    if t_end <= t_start:
        return 0.0

    loss_given_default = (1.0 - recovery_rate) * notional

    # Use the curve points for integration if available
    # Otherwise use uniform grid
    return _integrate_protection_leg(
        t_start, t_end, loss_given_default,
        discount_curve, credit_curve,
        integration_points
    )


def _integrate_protection_leg(
    t_start: float,
    t_end: float,
    loss: float,
    discount_curve: ZeroCurve,
    credit_curve: CreditCurve,
    num_points: int,
) -> float:
    """
    Integrate the protection leg PV using the ISDA methodology.

    From ISDA C code (contingentleg.c:219-266):

    For each sub-period, calculate:
        lambda_ = ln(s0) - ln(s1)    # hazard rate * dt
        fwd_rate = ln(df0) - ln(df1) # interest rate * dt
        lambda_fwd_rate = lambda_ + fwd_rate

    If |lambda_fwd_rate| > 1e-4:
        pv = loss * lambda_ / lambda_fwd_rate * (1 - exp(-lambda_fwd_rate)) * s0 * df0
    Else:
        # Taylor expansion for numerical stability
        pv = loss * lambda_ * s0 * df0 * (1 - lambda_fwd_rate/2 + lambda_fwd_rate²/6 - ...)
    """
    if t_end <= t_start:
        return 0.0

    dt = (t_end - t_start) / num_points
    pv = 0.0

    for i in range(num_points):
        t0 = t_start + i * dt
        t1 = t_start + (i + 1) * dt

        # Survival probabilities at start and end of sub-period
        s0 = credit_curve.survival_probability(t0)
        s1 = credit_curve.survival_probability(t1)

        # Discount factors at start and end of sub-period
        df0 = discount_curve.discount_factor(t0)
        df1 = discount_curve.discount_factor(t1)

        # Calculate lambda (hazard rate * dt approximation)
        # lambda_ = -ln(S(t1)/S(t0)) = ln(S(t0)) - ln(S(t1))
        if s0 > 0 and s1 > 0:
            lambda_ = np.log(s0) - np.log(s1)
        else:
            lambda_ = 0.0

        # Calculate forward rate * dt
        # fwd_rate = -ln(DF(t1)/DF(t0)) = ln(DF(t0)) - ln(DF(t1))
        if df0 > 0 and df1 > 0:
            fwd_rate = np.log(df0) - np.log(df1)
        else:
            fwd_rate = 0.0

        # Combined rate (add small number to avoid division by zero)
        lambda_fwd_rate = lambda_ + fwd_rate + 1e-50

        # Calculate PV contribution from this sub-period
        # This is the integral over the sub-period of:
        #   loss * (instantaneous default probability) * (discount factor)
        if abs(lambda_fwd_rate) > 1e-4:
            # Direct formula when lambda_fwd_rate is not too small
            # PV = loss * λ / (λ+r) * (1 - e^{-(λ+r)}) * S(t0) * DF(t0)
            pv_sub = (
                loss * lambda_ / lambda_fwd_rate
                * (1.0 - np.exp(-lambda_fwd_rate))
                * s0 * df0
            )
        else:
            # Taylor expansion for numerical stability
            # e^{-x} ≈ 1 - x + x²/2! - x³/3! + ...
            # (1 - e^{-x})/x ≈ 1 - x/2 + x²/6 - x³/24 + x⁴/120 - ...
            # So: PV ≈ loss * λ * S0 * DF0 * (1 - λfr/2 + λfr²/6 - λfr³/24 + λfr⁴/120)
            pv0 = loss * lambda_ * s0 * df0
            pv1 = -pv0 * lambda_fwd_rate * 0.5
            pv2 = -pv1 * lambda_fwd_rate / 3.0
            pv3 = -pv2 * lambda_fwd_rate * 0.25
            pv4 = -pv3 * lambda_fwd_rate * 0.2
            pv_sub = pv0 + pv1 + pv2 + pv3 + pv4

        pv += pv_sub

    return pv


def protection_leg_pv(
    value_date: DateLike,
    maturity_date: DateLike,
    discount_curve: ZeroCurve,
    credit_curve: CreditCurve,
    recovery_rate: float = 0.4,
    notional: float = 1.0,
    integration_points: int = 100,
    protection_start_date: DateLike | None = None,
    protect_start: bool = True,
) -> float:
    """
    Alias for contingent_leg_pv.

    The protection leg and contingent leg refer to the same thing:
    the payment made upon default.
    """
    return contingent_leg_pv(
        value_date, maturity_date,
        discount_curve, credit_curve,
        recovery_rate, notional,
        integration_points,
        protection_start_date,
        protect_start,
    )


def expected_loss(
    value_date: DateLike,
    maturity_date: DateLike,
    credit_curve: CreditCurve,
    recovery_rate: float = 0.4,
    notional: float = 1.0,
) -> float:
    """
    Calculate the expected loss (undiscounted) over the CDS life.

    This is simpler than the protection PV as it doesn't include discounting.

        EL = (1 - R) * N * (1 - Q(T))

    Args:
        value_date: Valuation date
        maturity_date: CDS maturity date
        credit_curve: Credit curve
        recovery_rate: Recovery rate
        notional: Notional amount

    Returns
        Expected loss amount
    """
    vd = parse_date(value_date)
    mat = parse_date(maturity_date)

    t_mat = credit_curve.time_from_date(mat)
    survival = credit_curve.survival_probability(t_mat)
    default_prob = 1.0 - survival

    return (1.0 - recovery_rate) * notional * default_prob


def default_probability_from_pv(
    protection_pv: float,
    recovery_rate: float,
    notional: float,
    avg_discount_factor: float,
) -> float:
    """
    Estimate default probability from protection leg PV.

    This inverts the simple relationship:
        PV ≈ (1 - R) * N * PD * avg_DF

    Args:
        protection_pv: Protection leg present value
        recovery_rate: Recovery rate
        notional: Notional amount
        avg_discount_factor: Average discount factor over period

    Returns
        Estimated default probability
    """
    loss = (1.0 - recovery_rate) * notional
    if loss > 0 and avg_discount_factor > 0:
        return protection_pv / (loss * avg_discount_factor)
    return 0.0
