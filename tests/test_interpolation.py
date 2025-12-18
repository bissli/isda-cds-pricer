"""
Tests for interpolation functions.
"""

import numpy as np
import pytest
from isda.interpolation import flat_forward_discount_factor
from isda.interpolation import flat_forward_interp
from isda.interpolation import flat_forward_survival_probability, forward_rate
from isda.interpolation import interpolate_curve


class TestFlatForwardInterp:
    """Tests for flat forward interpolation."""

    def test_flat_forward_at_nodes(self):
        """Test interpolation returns exact values at nodes."""
        times = np.array([1.0, 2.0, 3.0])
        rates = np.array([0.02, 0.03, 0.04])

        assert flat_forward_interp(1.0, times, rates) == 0.02
        assert flat_forward_interp(2.0, times, rates) == 0.03
        assert flat_forward_interp(3.0, times, rates) == 0.04

    def test_flat_forward_between_nodes(self):
        """Test interpolation between nodes."""
        times = np.array([1.0, 2.0])
        rates = np.array([0.02, 0.04])

        rate = flat_forward_interp(1.5, times, rates)
        # Flat forward should give consistent discount factor
        assert 0.02 < rate < 0.04

    def test_flat_forward_before_first_node(self):
        """Test interpolation before first node uses flat extrapolation."""
        times = np.array([1.0, 2.0])
        rates = np.array([0.02, 0.04])

        rate = flat_forward_interp(0.5, times, rates)
        assert rate == 0.02  # Flat extrapolation

    def test_flat_forward_after_last_node(self):
        """Test interpolation after last node uses flat extrapolation."""
        times = np.array([1.0, 2.0])
        rates = np.array([0.02, 0.04])

        rate = flat_forward_interp(3.0, times, rates)
        assert rate == 0.04  # Flat extrapolation

    def test_flat_forward_consistency(self):
        """Test flat forward interpolation gives consistent discount factors."""
        times = np.array([1.0, 2.0])
        rates = np.array([0.02, 0.04])

        # Get interpolated rate at midpoint
        t_mid = 1.5
        r_mid = flat_forward_interp(t_mid, times, rates)

        # Calculate discount factors
        df1 = np.exp(-0.02 * 1.0)
        df2 = np.exp(-0.04 * 2.0)
        df_mid = np.exp(-r_mid * t_mid)

        # Check that interpolated DF lies between
        assert df2 < df_mid < df1


class TestFlatForwardDiscountFactor:
    """Tests for flat forward discount factor."""

    def test_discount_factor_at_zero(self):
        """Test discount factor at time 0 is 1."""
        times = np.array([1.0, 2.0])
        rates = np.array([0.02, 0.04])

        df = flat_forward_discount_factor(0.0, times, rates)
        assert df == 1.0

    def test_discount_factor_positive(self):
        """Test discount factor is positive and less than 1."""
        times = np.array([1.0, 2.0])
        rates = np.array([0.02, 0.04])

        df = flat_forward_discount_factor(1.5, times, rates)
        assert 0 < df < 1

    def test_discount_factor_decreasing(self):
        """Test discount factor decreases with time."""
        times = np.array([1.0, 2.0, 3.0])
        rates = np.array([0.02, 0.03, 0.04])

        df1 = flat_forward_discount_factor(1.0, times, rates)
        df2 = flat_forward_discount_factor(2.0, times, rates)
        df3 = flat_forward_discount_factor(3.0, times, rates)

        assert df3 < df2 < df1 < 1.0


class TestFlatForwardSurvivalProbability:
    """Tests for survival probability calculation."""

    def test_survival_at_zero(self):
        """Test survival probability at time 0 is 1."""
        times = np.array([1.0, 2.0])
        hazard_rates = np.array([0.02, 0.03])

        sp = flat_forward_survival_probability(0.0, times, hazard_rates)
        assert sp == 1.0

    def test_survival_decreasing(self):
        """Test survival probability decreases with time."""
        times = np.array([1.0, 2.0, 3.0])
        hazard_rates = np.array([0.02, 0.03, 0.04])

        sp1 = flat_forward_survival_probability(1.0, times, hazard_rates)
        sp2 = flat_forward_survival_probability(2.0, times, hazard_rates)
        sp3 = flat_forward_survival_probability(3.0, times, hazard_rates)

        assert sp3 < sp2 < sp1 < 1.0


class TestInterpolateCurve:
    """Tests for curve interpolation."""

    def test_interpolate_multiple_points(self):
        """Test interpolating multiple points at once."""
        times = np.array([1.0, 2.0, 3.0])
        rates = np.array([0.02, 0.03, 0.04])
        target_times = np.array([0.5, 1.5, 2.5, 3.5])

        result = interpolate_curve(target_times, times, rates)
        assert len(result) == 4

    def test_interpolate_linear_method(self):
        """Test linear interpolation method."""
        times = np.array([1.0, 3.0])
        rates = np.array([0.02, 0.04])
        target_times = np.array([2.0])

        result = interpolate_curve(target_times, times, rates, method='linear')
        # Midpoint should be 0.03 for linear
        assert abs(result[0] - 0.03) < 1e-10


class TestForwardRate:
    """Tests for forward rate calculation."""

    def test_forward_rate_single_period(self):
        """Test forward rate calculation for single period."""
        times = np.array([1.0, 2.0])
        rates = np.array([0.02, 0.03])

        fwd = forward_rate(1.0, 2.0, times, rates)

        # Forward rate from 1 to 2:
        # DF(2) = DF(1) * exp(-fwd * (2-1))
        # exp(-0.03*2) = exp(-0.02*1) * exp(-fwd)
        # fwd = 0.03*2 - 0.02*1 = 0.04
        expected = (0.03 * 2.0 - 0.02 * 1.0) / 1.0
        assert abs(fwd - expected) < 1e-10

    def test_forward_rate_error_on_invalid_times(self):
        """Test forward rate raises error when t2 <= t1."""
        times = np.array([1.0, 2.0])
        rates = np.array([0.02, 0.03])

        with pytest.raises(Exception):
            forward_rate(2.0, 1.0, times, rates)


class TestInterpolationEdgeCases:
    """Edge case tests for interpolation."""

    def test_single_point(self):
        """Test interpolation with single point."""
        times = np.array([1.0])
        rates = np.array([0.02])

        # Should extrapolate flat
        assert flat_forward_interp(0.5, times, rates) == 0.02
        assert flat_forward_interp(1.0, times, rates) == 0.02
        assert flat_forward_interp(2.0, times, rates) == 0.02

    def test_negative_rates(self):
        """Test interpolation with negative rates."""
        times = np.array([1.0, 2.0])
        rates = np.array([-0.01, -0.005])

        rate = flat_forward_interp(1.5, times, rates)
        assert -0.01 < rate < -0.005

    def test_zero_time(self):
        """Test interpolation at time zero."""
        times = np.array([0.5, 1.0])
        rates = np.array([0.02, 0.03])

        rate = flat_forward_interp(0.0, times, rates)
        assert rate == 0.02  # Flat extrapolation
