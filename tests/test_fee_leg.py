"""
Tests for fee leg (premium leg) calculations.
"""

from datetime import date

import numpy as np
import pytest
from isda.curves import CreditCurve, ZeroCurve
from isda.enums import DayCountConvention, PaymentFrequency
from isda.fee_leg import calculate_accrued_interest, fee_leg_pv, risky_annuity
from isda.schedule import CDSSchedule


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
def sample_schedule():
    """Create a sample CDS schedule."""
    return CDSSchedule(
        accrual_start=date(2020, 3, 20),
        maturity=date(2025, 3, 20),
        frequency=PaymentFrequency.QUARTERLY,
        day_count=DayCountConvention.ACT_360,
    )


class TestFeeLegPV:
    """Tests for fee leg present value calculation."""

    def test_fee_leg_pv_positive(self, sample_zero_curve, sample_credit_curve, sample_schedule):
        """Test fee leg PV is positive."""
        pv = fee_leg_pv(
            value_date=date(2020, 3, 20),
            schedule=sample_schedule,
            coupon_rate=0.01,  # 100 bps
            discount_curve=sample_zero_curve,
            credit_curve=sample_credit_curve,
        )
        assert pv > 0

    def test_fee_leg_pv_proportional_to_coupon(self, sample_zero_curve, sample_credit_curve, sample_schedule):
        """Test fee leg PV is proportional to coupon rate."""
        pv_100bps = fee_leg_pv(
            value_date=date(2020, 3, 20),
            schedule=sample_schedule,
            coupon_rate=0.01,
            discount_curve=sample_zero_curve,
            credit_curve=sample_credit_curve,
        )
        pv_200bps = fee_leg_pv(
            value_date=date(2020, 3, 20),
            schedule=sample_schedule,
            coupon_rate=0.02,
            discount_curve=sample_zero_curve,
            credit_curve=sample_credit_curve,
        )
        # Should be approximately 2x (within numerical tolerance)
        assert abs(pv_200bps / pv_100bps - 2.0) < 0.01

    def test_fee_leg_pv_proportional_to_notional(self, sample_zero_curve, sample_credit_curve, sample_schedule):
        """Test fee leg PV is proportional to notional."""
        pv_1 = fee_leg_pv(
            value_date=date(2020, 3, 20),
            schedule=sample_schedule,
            coupon_rate=0.01,
            discount_curve=sample_zero_curve,
            credit_curve=sample_credit_curve,
            notional=1.0,
        )
        pv_1m = fee_leg_pv(
            value_date=date(2020, 3, 20),
            schedule=sample_schedule,
            coupon_rate=0.01,
            discount_curve=sample_zero_curve,
            credit_curve=sample_credit_curve,
            notional=1_000_000.0,
        )
        assert abs(pv_1m / pv_1 - 1_000_000.0) < 1.0


class TestRiskyAnnuity:
    """Tests for risky annuity calculation."""

    def test_risky_annuity_positive(self, sample_zero_curve, sample_credit_curve, sample_schedule):
        """Test risky annuity is positive."""
        ra = risky_annuity(
            value_date=date(2020, 3, 20),
            schedule=sample_schedule,
            discount_curve=sample_zero_curve,
            credit_curve=sample_credit_curve,
        )
        assert ra > 0

    def test_risky_annuity_less_than_risk_free(self, sample_zero_curve, sample_credit_curve, sample_schedule):
        """Test risky annuity is less than risk-free annuity."""
        # Risky annuity accounts for default probability
        ra = risky_annuity(
            value_date=date(2020, 3, 20),
            schedule=sample_schedule,
            discount_curve=sample_zero_curve,
            credit_curve=sample_credit_curve,
        )

        # For a 5Y CDS, risk-free annuity would be roughly 5 * avg(DF)
        # Risky annuity should be smaller due to default risk
        assert ra < 5.0


class TestAccruedInterestFeeLeg:
    """Tests for accrued interest calculation in fee leg."""

    def test_accrued_interest_calculation(self, sample_schedule):
        """Test accrued interest calculation."""
        ai = calculate_accrued_interest(
            value_date=date(2020, 4, 20),  # 1 month after start
            schedule=sample_schedule,
            coupon_rate=0.01,
            notional=1_000_000.0,
        )
        # 31 days at 100 bps on 1M = 1M * 0.01 * 31/360 = ~861
        assert 800 < ai < 900

    def test_accrued_interest_at_period_start(self, sample_schedule):
        """Test accrued interest at period start.

        ISDA convention: accrued is calculated to stepinDate (value_date + 1).
        So at period start (March 20), stepinDate is March 21, giving 1 day of accrued.
        """
        ai = calculate_accrued_interest(
            value_date=date(2020, 3, 20),  # Period start
            schedule=sample_schedule,
            coupon_rate=0.01,
            notional=1_000_000.0,
        )
        # 1 day of accrued (stepinDate = March 21)
        # 1/360 * 0.01 * 1,000,000 = 27.7778
        assert abs(ai - 27.777777778) < 0.01

    def test_accrued_interest_before_schedule(self):
        """Test accrued interest before schedule start is zero."""
        schedule = CDSSchedule(
            accrual_start=date(2020, 3, 20),
            maturity=date(2020, 9, 20),
            frequency=PaymentFrequency.QUARTERLY,
        )

        ai = calculate_accrued_interest(
            value_date=date(2020, 1, 1),  # Before schedule
            schedule=schedule,
            coupon_rate=0.01,
            notional=1_000_000.0,
        )
        assert ai == 0.0


class TestFeeLegIntegration:
    """Integration tests for fee leg."""

    def test_fee_leg_short_maturity(self, sample_zero_curve, sample_credit_curve):
        """Test fee leg PV for short maturity CDS."""
        schedule = CDSSchedule(
            accrual_start=date(2020, 3, 20),
            maturity=date(2020, 9, 20),  # 6 months
            frequency=PaymentFrequency.QUARTERLY,
            day_count=DayCountConvention.ACT_360,
        )

        pv = fee_leg_pv(
            value_date=date(2020, 3, 20),
            schedule=schedule,
            coupon_rate=0.01,
            discount_curve=sample_zero_curve,
            credit_curve=sample_credit_curve,
        )

        assert pv > 0
        # Should be less than full notional
        assert pv < 1.0

    def test_fee_leg_higher_hazard_rate(self, sample_zero_curve):
        """Test fee leg PV decreases with higher hazard rate."""
        schedule = CDSSchedule(
            accrual_start=date(2020, 3, 20),
            maturity=date(2025, 3, 20),
            frequency=PaymentFrequency.QUARTERLY,
        )

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
            hazard_rates=np.array([0.10, 0.10]),
        )

        pv_low = fee_leg_pv(
            value_date=date(2020, 3, 20),
            schedule=schedule,
            coupon_rate=0.01,
            discount_curve=sample_zero_curve,
            credit_curve=low_hazard,
        )

        pv_high = fee_leg_pv(
            value_date=date(2020, 3, 20),
            schedule=schedule,
            coupon_rate=0.01,
            discount_curve=sample_zero_curve,
            credit_curve=high_hazard,
        )

        # Higher hazard rate means fewer expected payments
        assert pv_high < pv_low
