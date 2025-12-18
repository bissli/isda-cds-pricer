"""
Interpolation methods for curve construction.

Implements flat forward interpolation which is the standard method
for ISDA CDS pricing.
"""


import numpy as np

from .exceptions import InterpolationError


def flat_forward_interp(
    target_time: float,
    times: np.ndarray,
    rates: np.ndarray,
) -> float:
    """
    Interpolate a rate using flat forward interpolation.

    This method assumes that forward rates are constant (flat) between
    curve points. This is the ISDA standard for CDS pricing.

    For zero rates r(t), flat forward means:
        DF(t) = exp(-r(t) * t) is piecewise exponential

    Between times t[i] and t[i+1]:
        DF(t) = DF(t[i]) * exp(-f[i] * (t - t[i]))
    where f[i] is the flat forward rate in that segment.

    Args:
        target_time: Time point to interpolate (in years)
        times: Array of curve times (in years)
        rates: Array of zero rates at each time

    Returns
        Interpolated zero rate at target_time
    """
    if len(times) == 0 or len(rates) == 0:
        raise InterpolationError('Empty curve data')

    if len(times) != len(rates):
        raise InterpolationError('Times and rates arrays must have same length')

    n = len(times)

    # Handle extrapolation before first point
    if target_time <= times[0]:
        return rates[0]

    # Handle extrapolation after last point
    if target_time >= times[-1]:
        return rates[-1]

    # Find the segment containing target_time
    # Binary search for efficiency
    idx = np.searchsorted(times, target_time) - 1
    idx = max(0, min(idx, n - 2))

    t0, t1 = times[idx], times[idx + 1]
    r0, r1 = rates[idx], rates[idx + 1]

    # Flat forward interpolation formula:
    # r(t) * t = r0 * t0 + f * (t - t0)
    # where f is the forward rate that makes r1 * t1 = r0 * t0 + f * (t1 - t0)
    # so f = (r1 * t1 - r0 * t0) / (t1 - t0)

    dt = t1 - t0
    if abs(dt) < 1e-14:
        return r0

    # Forward rate in this segment
    fwd_rate = (r1 * t1 - r0 * t0) / dt

    # Interpolated rate
    rate = (r0 * t0 + fwd_rate * (target_time - t0)) / target_time

    return rate


def flat_forward_discount_factor(
    target_time: float,
    times: np.ndarray,
    rates: np.ndarray,
) -> float:
    """
    Calculate discount factor using flat forward interpolation.

    Args:
        target_time: Time point (in years)
        times: Array of curve times
        rates: Array of zero rates

    Returns
        Discount factor at target_time
    """
    if target_time <= 0:
        return 1.0

    rate = flat_forward_interp(target_time, times, rates)
    return np.exp(-rate * target_time)


def flat_forward_survival_probability(
    target_time: float,
    times: np.ndarray,
    hazard_rates: np.ndarray,
) -> float:
    """
    Calculate survival probability using flat forward interpolation.

    The survival probability Q(t) = exp(-h(t) * t) where h(t) is the
    average hazard rate to time t.

    Args:
        target_time: Time point (in years)
        times: Array of curve times
        hazard_rates: Array of average hazard rates

    Returns
        Survival probability at target_time
    """
    if target_time <= 0:
        return 1.0

    rate = flat_forward_interp(target_time, times, hazard_rates)
    return np.exp(-rate * target_time)


def interpolate_curve(
    target_times: np.ndarray,
    times: np.ndarray,
    values: np.ndarray,
    method: str = 'flat_forward',
) -> np.ndarray:
    """
    Interpolate multiple points on a curve.

    Args:
        target_times: Array of times to interpolate
        times: Array of curve times
        values: Array of curve values (rates)
        method: Interpolation method ('flat_forward' or 'linear')

    Returns
        Array of interpolated values
    """
    if method == 'flat_forward':
        return np.array([
            flat_forward_interp(t, times, values) for t in target_times
        ])
    elif method == 'linear':
        return np.interp(target_times, times, values)
    else:
        raise InterpolationError(f'Unknown interpolation method: {method}')


def forward_rate(
    t1: float,
    t2: float,
    times: np.ndarray,
    rates: np.ndarray,
) -> float:
    """
    Calculate the forward rate between two times.

    The forward rate f(t1, t2) is defined such that:
        DF(t2) = DF(t1) * exp(-f * (t2 - t1))

    Args:
        t1: Start time (in years)
        t2: End time (in years)
        times: Array of curve times
        rates: Array of zero rates

    Returns
        Forward rate between t1 and t2
    """
    if t2 <= t1:
        raise InterpolationError(f't2 ({t2}) must be greater than t1 ({t1})')

    df1 = flat_forward_discount_factor(t1, times, rates) if t1 > 0 else 1.0
    df2 = flat_forward_discount_factor(t2, times, rates)

    return -np.log(df2 / df1) / (t2 - t1)
