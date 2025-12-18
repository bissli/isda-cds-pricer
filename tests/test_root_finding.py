"""
Tests for root finding algorithms.
"""

import pytest
import numpy as np

from isda.root_finding import brent, newton_raphson, secant, bisection, find_root
from isda.exceptions import ConvergenceError


class TestBrent:
    """Tests for Brent's method."""

    def test_brent_linear(self):
        """Test Brent's method on linear function."""
        def f(x):
            return 2 * x - 4

        root = brent(f, 0, 10)
        assert abs(root - 2.0) < 1e-10

    def test_brent_quadratic(self):
        """Test Brent's method on quadratic function."""
        def f(x):
            return x**2 - 4

        root = brent(f, 0, 10)
        assert abs(root - 2.0) < 1e-10

    def test_brent_trig(self):
        """Test Brent's method on trigonometric function."""
        def f(x):
            return np.sin(x)

        root = brent(f, 3, 4)  # Pi is between 3 and 4
        assert abs(root - np.pi) < 1e-10

    def test_brent_negative_root(self):
        """Test Brent's method for negative root."""
        def f(x):
            return x + 2

        root = brent(f, -5, 0)
        assert abs(root - (-2.0)) < 1e-10

    def test_brent_same_sign_error(self):
        """Test Brent's method raises error when bounds have same sign."""
        def f(x):
            return x**2 + 1  # Always positive

        with pytest.raises(ConvergenceError):
            brent(f, 0, 10)

    def test_brent_tolerance(self):
        """Test Brent's method respects tolerance."""
        def f(x):
            return x - 1.5

        # With loose tolerance
        root_loose = brent(f, 0, 10, tol=1e-3)
        assert abs(root_loose - 1.5) < 1e-3

        # With tight tolerance
        root_tight = brent(f, 0, 10, tol=1e-12)
        assert abs(root_tight - 1.5) < 1e-12

    def test_brent_max_iter(self):
        """Test Brent's method raises error on max iterations."""
        def f(x):
            return x - 0.5

        with pytest.raises(ConvergenceError):
            brent(f, 0, 1, max_iter=1)


class TestNewtonRaphson:
    """Tests for Newton-Raphson method."""

    def test_newton_linear(self):
        """Test Newton-Raphson on linear function."""
        def f(x):
            return 2 * x - 4

        def df(x):
            return 2

        root = newton_raphson(f, df, 0)
        assert abs(root - 2.0) < 1e-10

    def test_newton_quadratic(self):
        """Test Newton-Raphson on quadratic function."""
        def f(x):
            return x**2 - 4

        def df(x):
            return 2 * x

        root = newton_raphson(f, df, 5)
        assert abs(root - 2.0) < 1e-10

    def test_newton_zero_derivative_error(self):
        """Test Newton-Raphson raises error on zero derivative."""
        def f(x):
            return x**3

        def df(x):
            return 0  # Always zero (incorrect derivative)

        with pytest.raises(ConvergenceError):
            newton_raphson(f, df, 1)


class TestSecant:
    """Tests for secant method."""

    def test_secant_linear(self):
        """Test secant method on linear function."""
        def f(x):
            return 2 * x - 4

        root = secant(f, 0, 5)
        assert abs(root - 2.0) < 1e-10

    def test_secant_quadratic(self):
        """Test secant method on quadratic function."""
        def f(x):
            return x**2 - 4

        root = secant(f, 1, 5)
        assert abs(root - 2.0) < 1e-10


class TestBisection:
    """Tests for bisection method."""

    def test_bisection_linear(self):
        """Test bisection on linear function."""
        def f(x):
            return 2 * x - 4

        root = bisection(f, 0, 10)
        assert abs(root - 2.0) < 1e-10

    def test_bisection_quadratic(self):
        """Test bisection on quadratic function."""
        def f(x):
            return x**2 - 4

        root = bisection(f, 0, 10)
        assert abs(root - 2.0) < 1e-10

    def test_bisection_same_sign_error(self):
        """Test bisection raises error when bounds have same sign."""
        def f(x):
            return x**2 + 1

        with pytest.raises(ConvergenceError):
            bisection(f, 0, 10)


class TestFindRoot:
    """Tests for find_root convenience function."""

    def test_find_root_brent(self):
        """Test find_root with Brent's method."""
        def f(x):
            return x - 2

        root = find_root(f, 0, 10, method='brent')
        assert abs(root - 2.0) < 1e-10

    def test_find_root_bisection(self):
        """Test find_root with bisection method."""
        def f(x):
            return x - 2

        root = find_root(f, 0, 10, method='bisection')
        assert abs(root - 2.0) < 1e-10

    def test_find_root_invalid_method(self):
        """Test find_root raises error for invalid method."""
        def f(x):
            return x - 2

        with pytest.raises(ValueError):
            find_root(f, 0, 10, method='invalid')


class TestRootFindingEdgeCases:
    """Edge case tests for root finding."""

    def test_root_at_boundary(self):
        """Test finding root at boundary."""
        def f(x):
            return x

        root = brent(f, 0, 10)
        assert abs(root) < 1e-10

    def test_very_close_bounds(self):
        """Test with very close bounds."""
        def f(x):
            return x - 1.0

        root = brent(f, 0.9999, 1.0001)
        assert abs(root - 1.0) < 1e-10

    def test_steep_function(self):
        """Test with steep function."""
        def f(x):
            return 1000 * x - 1

        root = brent(f, 0, 1)
        assert abs(root - 0.001) < 1e-10

    def test_flat_near_root(self):
        """Test function that's flat near root."""
        def f(x):
            return (x - 1.5)**3

        root = brent(f, 0, 3)
        assert abs(root - 1.5) < 1e-4  # May need looser tolerance
