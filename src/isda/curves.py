"""
Curve classes for interest rates and credit spreads.

Provides base curve functionality for:
- Zero rate curves (discount factors)
- Credit curves (survival probabilities)
"""

from abc import ABC, abstractmethod

import numpy as np
from opendate import Date, Interval

from .enums import DayCountConvention
from .interpolation import flat_forward_interp


class Curve(ABC):
    """Abstract base class for all curves."""

    def __init__(
        self,
        base_date: Date,
        day_count: DayCountConvention = DayCountConvention.ACT_365F,
    ):
        """
        Initialize a curve.

        Args:
            base_date: The reference date for the curve
            day_count: Day count convention for time calculations
        """
        self._base_date = base_date
        self._day_count = day_count
        self._times: np.ndarray = np.array([])
        self._values: np.ndarray = np.array([])

    @property
    def base_date(self) -> Date:
        """The reference date for the curve."""
        return self._base_date

    @property
    def day_count(self) -> DayCountConvention:
        """Day count convention used for time calculations."""
        return self._day_count

    @property
    def times(self) -> np.ndarray:
        """Array of times (in years from base date)."""
        return self._times

    @property
    def values(self) -> np.ndarray:
        """Array of curve values (rates or hazard rates)."""
        return self._values

    def time_from_date(self, d: Date) -> float:
        """Convert a date to time (years from base date)."""
        return Interval(self._base_date, d).yearfrac(basis=self._day_count.value)

    def date_to_time(self, d: Date) -> float:
        """Alias for time_from_date."""
        return self.time_from_date(d)

    @abstractmethod
    def value_at(self, t: float) -> float:
        """Get the curve value at time t."""


class ZeroCurve(Curve):
    """
    Zero rate curve for discounting.

    Stores zero rates and provides discount factor calculations.
    Zero rates are continuously compounded: DF(t) = exp(-r(t) * t)
    """

    def __init__(
        self,
        base_date: Date,
        times: np.ndarray | None = None,
        rates: np.ndarray | None = None,
        day_count: DayCountConvention = DayCountConvention.ACT_365F,
    ):
        """
        Initialize a zero curve.

        Args:
            base_date: The curve base date
            times: Array of times (in years)
            rates: Array of zero rates at each time
            day_count: Day count convention
        """
        super().__init__(base_date, day_count)

        if times is not None and rates is not None:
            self._times = np.asarray(times, dtype=float)
            self._values = np.asarray(rates, dtype=float)
        elif times is not None or rates is not None:
            raise ValueError('Both times and rates must be provided, or neither')

    @property
    def rates(self) -> np.ndarray:
        """Array of zero rates."""
        return self._values

    def value_at(self, t: float) -> float:
        """Get the zero rate at time t."""
        if len(self._times) == 0:
            return 0.0
        return flat_forward_interp(t, self._times, self._values)

    def rate(self, t: float) -> float:
        """Get the zero rate at time t."""
        return self.value_at(t)

    def rate_at_date(self, d: Date) -> float:
        """Get the zero rate at a specific date."""
        t = self.time_from_date(d)
        return self.rate(t)

    def discount_factor(self, t: float) -> float:
        """
        Calculate the discount factor at time t.

        DF(t) = exp(-r(t) * t)
        """
        if t <= 0:
            return 1.0
        r = self.rate(t)
        return np.exp(-r * t)

    def discount_factor_at_date(self, d: Date) -> float:
        """Calculate the discount factor at a specific date."""
        t = self.time_from_date(d)
        return self.discount_factor(t)

    def forward_discount_factor(self, t1: float, t2: float) -> float:
        """
        Calculate the forward discount factor from t1 to t2.

        FDF(t1, t2) = DF(t2) / DF(t1)
        """
        df1 = self.discount_factor(t1)
        df2 = self.discount_factor(t2)
        return df2 / df1 if df1 > 0 else 0.0

    def forward_rate(self, t1: float, t2: float) -> float:
        """
        Calculate the forward rate between t1 and t2.

        f(t1, t2) = -ln(FDF(t1, t2)) / (t2 - t1)
        """
        if t2 <= t1:
            return self.rate(t1)
        fdf = self.forward_discount_factor(t1, t2)
        if fdf <= 0:
            return 0.0
        return -np.log(fdf) / (t2 - t1)

    def add_point(self, t: float, rate: float) -> None:
        """Add a single point to the curve."""
        self._times = np.append(self._times, t)
        self._values = np.append(self._values, rate)
        # Keep sorted by time
        sort_idx = np.argsort(self._times)
        self._times = self._times[sort_idx]
        self._values = self._values[sort_idx]

    def set_rate(self, idx: int, rate: float) -> None:
        """Set the rate at a specific index (used during bootstrapping)."""
        if 0 <= idx < len(self._values):
            self._values[idx] = rate


class CreditCurve(Curve):
    """
    Credit curve for survival probabilities.

    Stores hazard rates and provides survival probability calculations.
    Survival probability: Q(t) = exp(-h(t) * t)
    where h(t) is the average hazard rate from 0 to t.
    """

    def __init__(
        self,
        base_date: Date,
        times: np.ndarray | None = None,
        hazard_rates: np.ndarray | None = None,
        day_count: DayCountConvention = DayCountConvention.ACT_365F,
    ):
        """
        Initialize a credit curve.

        Args:
            base_date: The curve base date
            times: Array of times (in years)
            hazard_rates: Array of average hazard rates at each time
            day_count: Day count convention
        """
        super().__init__(base_date, day_count)

        if times is not None and hazard_rates is not None:
            self._times = np.asarray(times, dtype=float)
            self._values = np.asarray(hazard_rates, dtype=float)
        elif times is not None or hazard_rates is not None:
            raise ValueError('Both times and hazard_rates must be provided, or neither')

    @property
    def hazard_rates(self) -> np.ndarray:
        """Array of average hazard rates."""
        return self._values

    def value_at(self, t: float) -> float:
        """Get the average hazard rate at time t."""
        if len(self._times) == 0:
            return 0.0
        return flat_forward_interp(t, self._times, self._values)

    def hazard_rate(self, t: float) -> float:
        """Get the average hazard rate at time t."""
        return self.value_at(t)

    def hazard_rate_at_date(self, d: Date) -> float:
        """Get the average hazard rate at a specific date."""
        t = self.time_from_date(d)
        return self.hazard_rate(t)

    def survival_probability(self, t: float) -> float:
        """
        Calculate the survival probability at time t.

        Q(t) = exp(-h(t) * t)
        """
        if t <= 0:
            return 1.0
        h = self.hazard_rate(t)
        return np.exp(-h * t)

    def survival_probability_at_date(self, d: Date) -> float:
        """Calculate the survival probability at a specific date."""
        t = self.time_from_date(d)
        return self.survival_probability(t)

    def forward_survival_probability(self, t1: float, t2: float) -> float:
        """
        Calculate the forward survival probability from t1 to t2.

        Q(t1, t2) = Q(t2) / Q(t1)
        """
        q1 = self.survival_probability(t1)
        q2 = self.survival_probability(t2)
        return q2 / q1 if q1 > 0 else 0.0

    def default_probability(self, t: float) -> float:
        """
        Calculate the cumulative default probability at time t.

        PD(t) = 1 - Q(t)
        """
        return 1.0 - self.survival_probability(t)

    def forward_hazard_rate(self, t1: float, t2: float) -> float:
        """
        Calculate the forward hazard rate between t1 and t2.

        lambda(t1, t2) = -ln(Q(t1, t2)) / (t2 - t1)
        """
        if t2 <= t1:
            return self.hazard_rate(t1)
        fsurv = self.forward_survival_probability(t1, t2)
        if fsurv <= 0:
            return 0.0
        return -np.log(fsurv) / (t2 - t1)

    def add_point(self, t: float, hazard_rate: float) -> None:
        """Add a single point to the curve."""
        self._times = np.append(self._times, t)
        self._values = np.append(self._values, hazard_rate)
        # Keep sorted by time
        sort_idx = np.argsort(self._times)
        self._times = self._times[sort_idx]
        self._values = self._values[sort_idx]

    def set_hazard_rate(self, idx: int, hazard_rate: float) -> None:
        """Set the hazard rate at a specific index (used during bootstrapping)."""
        if 0 <= idx < len(self._values):
            self._values[idx] = hazard_rate
