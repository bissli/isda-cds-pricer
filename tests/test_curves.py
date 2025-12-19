"""
Tests for curve classes.
"""

import numpy as np
from isda import CreditCurve, ZeroCurve, bootstrap_zero_curve
from opendate import Date


class TestZeroCurve:
    """Tests for ZeroCurve class."""

    def test_create_zero_curve(self):
        """Test creating a zero curve."""
        times = np.array([0.5, 1.0, 2.0, 5.0])
        rates = np.array([0.01, 0.02, 0.025, 0.03])

        curve = ZeroCurve(
            base_date=Date(2020, 1, 1),
            times=times,
            rates=rates,
        )

        assert len(curve.times) == 4
        assert curve.base_date == Date(2020, 1, 1)

    def test_discount_factor(self):
        """Test discount factor calculation."""
        times = np.array([1.0, 2.0])
        rates = np.array([0.05, 0.05])

        curve = ZeroCurve(
            base_date=Date(2020, 1, 1),
            times=times,
            rates=rates,
        )

        # At t=1, DF = exp(-0.05 * 1) = exp(-0.05)
        df = curve.discount_factor(1.0)
        expected = np.exp(-0.05)
        assert abs(df - expected) < 1e-10

    def test_discount_factor_zero_time(self):
        """Test discount factor at time 0 is 1."""
        times = np.array([1.0, 2.0])
        rates = np.array([0.05, 0.05])

        curve = ZeroCurve(
            base_date=Date(2020, 1, 1),
            times=times,
            rates=rates,
        )

        assert curve.discount_factor(0.0) == 1.0

    def test_rate_interpolation(self):
        """Test flat forward interpolation of rates."""
        times = np.array([1.0, 2.0])
        rates = np.array([0.05, 0.06])

        curve = ZeroCurve(
            base_date=Date(2020, 1, 1),
            times=times,
            rates=rates,
        )

        # Rate at t=1.5 should be interpolated
        r = curve.rate(1.5)
        assert 0.05 < r < 0.06

    def test_forward_rate(self):
        """Test forward rate calculation."""
        times = np.array([1.0, 2.0])
        rates = np.array([0.05, 0.06])

        curve = ZeroCurve(
            base_date=Date(2020, 1, 1),
            times=times,
            rates=rates,
        )

        fwd = curve.forward_rate(1.0, 2.0)
        # Forward rate should be such that DF(2) = DF(1) * exp(-fwd)
        df1 = curve.discount_factor(1.0)
        df2 = curve.discount_factor(2.0)
        expected_fwd = -np.log(df2 / df1)
        assert abs(fwd - expected_fwd) < 1e-10


class TestCreditCurve:
    """Tests for CreditCurve class."""

    def test_create_credit_curve(self):
        """Test creating a credit curve."""
        times = np.array([1.0, 3.0, 5.0])
        hazard_rates = np.array([0.01, 0.012, 0.015])

        curve = CreditCurve(
            base_date=Date(2020, 1, 1),
            times=times,
            hazard_rates=hazard_rates,
        )

        assert len(curve.times) == 3
        assert curve.base_date == Date(2020, 1, 1)

    def test_survival_probability(self):
        """Test survival probability calculation."""
        times = np.array([1.0, 5.0])
        hazard_rates = np.array([0.02, 0.02])

        curve = CreditCurve(
            base_date=Date(2020, 1, 1),
            times=times,
            hazard_rates=hazard_rates,
        )

        # At t=1, Q = exp(-0.02 * 1)
        surv = curve.survival_probability(1.0)
        expected = np.exp(-0.02)
        assert abs(surv - expected) < 1e-10

    def test_survival_probability_zero_time(self):
        """Test survival probability at time 0 is 1."""
        times = np.array([1.0, 5.0])
        hazard_rates = np.array([0.02, 0.02])

        curve = CreditCurve(
            base_date=Date(2020, 1, 1),
            times=times,
            hazard_rates=hazard_rates,
        )

        assert curve.survival_probability(0.0) == 1.0

    def test_default_probability(self):
        """Test default probability calculation."""
        times = np.array([1.0])
        hazard_rates = np.array([0.02])

        curve = CreditCurve(
            base_date=Date(2020, 1, 1),
            times=times,
            hazard_rates=hazard_rates,
        )

        pd = curve.default_probability(1.0)
        surv = curve.survival_probability(1.0)
        assert abs(pd + surv - 1.0) < 1e-10


class TestBootstrapZeroCurve:
    """Tests for zero curve bootstrapping."""

    def test_bootstrap_simple(self):
        """Test bootstrapping a simple curve."""
        rates = [0.02, 0.025, 0.03, 0.035]
        tenors = ['6M', '1Y', '2Y', '3Y']

        curve = bootstrap_zero_curve(
            base_date='01/01/2020',
            swap_rates=rates,
            swap_tenors=tenors,
        )

        # Curve should have 4 points
        assert len(curve.times) == 4

        # Discount factor at short end should be close to what we expect
        df_6m = curve.discount_factor(0.5)
        # For MM rate, DF = 1 / (1 + r * t)
        # Then zero rate is -ln(DF) / t
        expected_df = 1 / (1 + 0.02 * 0.5)
        assert abs(df_6m - expected_df) < 0.001

    def test_bootstrap_negative_rates(self):
        """Test bootstrapping handles negative rates."""
        rates = [-0.005, -0.003, 0.0, 0.005]
        tenors = ['3M', '6M', '1Y', '2Y']

        curve = bootstrap_zero_curve(
            base_date='01/01/2020',
            swap_rates=rates,
            swap_tenors=tenors,
        )

        # Should handle negative rates without error
        assert len(curve.times) == 4

        # Discount factors should still be positive and sensible
        df = curve.discount_factor(1.0)
        assert df > 0
        assert df < 2  # Reasonable bound
