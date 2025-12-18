"""
Tests for contingent leg (protection leg) calculations.
"""

import pytest
import numpy as np
from datetime import date

from isda.contingent_leg import contingent_leg_pv, protection_leg_pv, expected_loss
from isda.curves import ZeroCurve, CreditCurve
from isda.enums import DayCountConvention


@pytest.fixture
def sample_zero_curve():
    """Create a sample zero curve for testing."""
    times = np.array([0.25, 0.5, 1.0, 2.0, 3.0, 5.0])
    rates = np.array([0.02, 0.022, 0.025, 0.028, 0.03, 0.032])
    return ZeroCurve(
        base_date=date(2020, 3, 20),
        times=times,
        rates=rates,
    )


@pytest.fixture
def sample_credit_curve():
    """Create a sample credit curve for testing."""
    times = np.array([0.5, 1.0, 2.0, 3.0, 5.0])
    hazard_rates = np.array([0.01, 0.012, 0.015, 0.017, 0.02])
    return CreditCurve(
        base_date=date(2020, 3, 20),
        times=times,
        hazard_rates=hazard_rates,
    )


@pytest.fixture
def flat_credit_curve():
    """Create a flat credit curve for testing."""
    times = np.array([1.0, 5.0])
    hazard_rates = np.array([0.02, 0.02])  # Flat 2%
    return CreditCurve(
        base_date=date(2020, 3, 20),
        times=times,
        hazard_rates=hazard_rates,
    )


class TestContingentLegPV:
    """Tests for contingent leg present value calculation."""

    def test_contingent_leg_pv_positive(self, sample_zero_curve, sample_credit_curve):
        """Test contingent leg PV is positive."""
        pv = contingent_leg_pv(
            value_date=date(2020, 3, 20),
            maturity_date=date(2025, 3, 20),
            discount_curve=sample_zero_curve,
            credit_curve=sample_credit_curve,
            recovery_rate=0.4,
        )
        assert pv > 0

    def test_contingent_leg_pv_proportional_to_loss(self, sample_zero_curve, sample_credit_curve):
        """Test contingent leg PV is proportional to loss (1 - recovery)."""
        pv_40_rr = contingent_leg_pv(
            value_date=date(2020, 3, 20),
            maturity_date=date(2025, 3, 20),
            discount_curve=sample_zero_curve,
            credit_curve=sample_credit_curve,
            recovery_rate=0.4,  # Loss = 60%
        )
        pv_20_rr = contingent_leg_pv(
            value_date=date(2020, 3, 20),
            maturity_date=date(2025, 3, 20),
            discount_curve=sample_zero_curve,
            credit_curve=sample_credit_curve,
            recovery_rate=0.2,  # Loss = 80%
        )
        # PV with 20% RR should be 80/60 = 1.33x PV with 40% RR
        ratio = pv_20_rr / pv_40_rr
        assert abs(ratio - (0.8 / 0.6)) < 0.01

    def test_contingent_leg_pv_proportional_to_notional(self, sample_zero_curve, sample_credit_curve):
        """Test contingent leg PV is proportional to notional."""
        pv_1 = contingent_leg_pv(
            value_date=date(2020, 3, 20),
            maturity_date=date(2025, 3, 20),
            discount_curve=sample_zero_curve,
            credit_curve=sample_credit_curve,
            recovery_rate=0.4,
            notional=1.0,
        )
        pv_1m = contingent_leg_pv(
            value_date=date(2020, 3, 20),
            maturity_date=date(2025, 3, 20),
            discount_curve=sample_zero_curve,
            credit_curve=sample_credit_curve,
            recovery_rate=0.4,
            notional=1_000_000.0,
        )
        assert abs(pv_1m / pv_1 - 1_000_000.0) < 1.0

    def test_contingent_leg_pv_zero_at_full_recovery(self, sample_zero_curve, sample_credit_curve):
        """Test contingent leg PV is zero at 100% recovery."""
        pv = contingent_leg_pv(
            value_date=date(2020, 3, 20),
            maturity_date=date(2025, 3, 20),
            discount_curve=sample_zero_curve,
            credit_curve=sample_credit_curve,
            recovery_rate=1.0,  # Full recovery, no loss
        )
        assert abs(pv) < 1e-10

    def test_contingent_leg_pv_increases_with_default_prob(self, sample_zero_curve):
        """Test contingent leg PV increases with default probability."""
        # Low hazard rate curve
        low_hazard = CreditCurve(
            base_date=date(2020, 3, 20),
            times=np.array([1.0, 5.0]),
            hazard_rates=np.array([0.01, 0.01]),
        )
        # High hazard rate curve
        high_hazard = CreditCurve(
            base_date=date(2020, 3, 20),
            times=np.array([1.0, 5.0]),
            hazard_rates=np.array([0.05, 0.05]),
        )

        pv_low = contingent_leg_pv(
            value_date=date(2020, 3, 20),
            maturity_date=date(2025, 3, 20),
            discount_curve=sample_zero_curve,
            credit_curve=low_hazard,
            recovery_rate=0.4,
        )
        pv_high = contingent_leg_pv(
            value_date=date(2020, 3, 20),
            maturity_date=date(2025, 3, 20),
            discount_curve=sample_zero_curve,
            credit_curve=high_hazard,
            recovery_rate=0.4,
        )

        assert pv_high > pv_low

    def test_contingent_leg_pv_decreases_with_maturity(self, sample_zero_curve, sample_credit_curve):
        """Test contingent leg PV for shorter maturity is smaller."""
        pv_5y = contingent_leg_pv(
            value_date=date(2020, 3, 20),
            maturity_date=date(2025, 3, 20),
            discount_curve=sample_zero_curve,
            credit_curve=sample_credit_curve,
            recovery_rate=0.4,
        )
        pv_3y = contingent_leg_pv(
            value_date=date(2020, 3, 20),
            maturity_date=date(2023, 3, 20),
            discount_curve=sample_zero_curve,
            credit_curve=sample_credit_curve,
            recovery_rate=0.4,
        )

        assert pv_3y < pv_5y


class TestContingentLegTaylorExpansion:
    """Tests for Taylor expansion numerical stability."""

    def test_contingent_leg_pv_with_zero_rates(self, sample_credit_curve):
        """Test contingent leg PV with zero interest rates."""
        # Zero rate curve to test Taylor expansion
        zero_rate_curve = ZeroCurve(
            base_date=date(2020, 3, 20),
            times=np.array([1.0, 5.0]),
            rates=np.array([0.0, 0.0]),
        )

        # Should not raise and should give reasonable result
        pv = contingent_leg_pv(
            value_date=date(2020, 3, 20),
            maturity_date=date(2025, 3, 20),
            discount_curve=zero_rate_curve,
            credit_curve=sample_credit_curve,
            recovery_rate=0.4,
        )
        assert pv > 0

    def test_contingent_leg_pv_with_very_small_hazard(self, sample_zero_curve):
        """Test contingent leg PV with very small hazard rates."""
        tiny_hazard = CreditCurve(
            base_date=date(2020, 3, 20),
            times=np.array([1.0, 5.0]),
            hazard_rates=np.array([1e-10, 1e-10]),
        )

        # Should not raise and should give small but positive result
        pv = contingent_leg_pv(
            value_date=date(2020, 3, 20),
            maturity_date=date(2025, 3, 20),
            discount_curve=sample_zero_curve,
            credit_curve=tiny_hazard,
            recovery_rate=0.4,
        )
        assert pv >= 0
        assert pv < 0.01  # Very small due to low hazard


class TestProtectionLegAlias:
    """Tests for protection_leg_pv alias."""

    def test_protection_leg_same_as_contingent(self, sample_zero_curve, sample_credit_curve):
        """Test protection_leg_pv gives same result as contingent_leg_pv."""
        pv_contingent = contingent_leg_pv(
            value_date=date(2020, 3, 20),
            maturity_date=date(2025, 3, 20),
            discount_curve=sample_zero_curve,
            credit_curve=sample_credit_curve,
            recovery_rate=0.4,
        )
        pv_protection = protection_leg_pv(
            value_date=date(2020, 3, 20),
            maturity_date=date(2025, 3, 20),
            discount_curve=sample_zero_curve,
            credit_curve=sample_credit_curve,
            recovery_rate=0.4,
        )
        assert pv_contingent == pv_protection


class TestExpectedLoss:
    """Tests for expected loss calculation."""

    def test_expected_loss_positive(self, sample_credit_curve):
        """Test expected loss is positive."""
        el = expected_loss(
            value_date=date(2020, 3, 20),
            maturity_date=date(2025, 3, 20),
            credit_curve=sample_credit_curve,
            recovery_rate=0.4,
        )
        assert el > 0

    def test_expected_loss_proportional_to_lgd(self, sample_credit_curve):
        """Test expected loss is proportional to loss given default."""
        el_40_rr = expected_loss(
            value_date=date(2020, 3, 20),
            maturity_date=date(2025, 3, 20),
            credit_curve=sample_credit_curve,
            recovery_rate=0.4,
        )
        el_20_rr = expected_loss(
            value_date=date(2020, 3, 20),
            maturity_date=date(2025, 3, 20),
            credit_curve=sample_credit_curve,
            recovery_rate=0.2,
        )
        # EL with 20% RR should be 80/60 = 1.33x EL with 40% RR
        ratio = el_20_rr / el_40_rr
        assert abs(ratio - (0.8 / 0.6)) < 0.01


class TestContingentLegIntegration:
    """Integration tests for contingent leg."""

    def test_contingent_leg_flat_curves(self, sample_zero_curve, flat_credit_curve):
        """Test contingent leg with flat curves."""
        pv = contingent_leg_pv(
            value_date=date(2020, 3, 20),
            maturity_date=date(2025, 3, 20),
            discount_curve=sample_zero_curve,
            credit_curve=flat_credit_curve,
            recovery_rate=0.4,
        )
        # With flat 2% hazard rate over 5Y, cumulative default prob ~9.5%
        # Loss = 60%, so PV ~ 0.095 * 0.6 * avg_discount ~ 0.05
        assert 0.02 < pv < 0.15

    def test_contingent_leg_step_function(self):
        """Test contingent leg with step function integration."""
        # Create curves with multiple steps
        zero_curve = ZeroCurve(
            base_date=date(2020, 3, 20),
            times=np.array([1.0, 2.0, 3.0, 4.0, 5.0]),
            rates=np.array([0.02, 0.025, 0.03, 0.032, 0.035]),
        )
        credit_curve = CreditCurve(
            base_date=date(2020, 3, 20),
            times=np.array([1.0, 2.0, 3.0, 4.0, 5.0]),
            hazard_rates=np.array([0.01, 0.015, 0.02, 0.022, 0.025]),
        )

        pv = contingent_leg_pv(
            value_date=date(2020, 3, 20),
            maturity_date=date(2025, 3, 20),
            discount_curve=zero_curve,
            credit_curve=credit_curve,
            recovery_rate=0.4,
        )

        assert pv > 0
