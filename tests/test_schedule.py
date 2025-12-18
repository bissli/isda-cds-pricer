"""
Tests for CDS payment schedule generation.
"""

import pytest
from datetime import date

from isda.schedule import (
    CDSSchedule, CouponPeriod, generate_cds_schedule,
    get_accrued_days, calculate_accrued_interest
)
from isda.enums import PaymentFrequency, DayCountConvention, BadDayConvention


class TestCouponPeriod:
    """Tests for CouponPeriod class."""

    def test_create_coupon_period(self):
        """Test creating a coupon period."""
        period = CouponPeriod(
            accrual_start=date(2020, 1, 20),
            accrual_end=date(2020, 4, 20),
            payment_date=date(2020, 4, 20),
            year_fraction=0.25,
        )
        assert period.accrual_start == date(2020, 1, 20)
        assert period.accrual_end == date(2020, 4, 20)
        assert period.year_fraction == 0.25


class TestCDSSchedule:
    """Tests for CDSSchedule class."""

    def test_create_quarterly_schedule(self):
        """Test creating a quarterly schedule."""
        schedule = CDSSchedule(
            accrual_start=date(2020, 3, 20),
            maturity=date(2025, 3, 20),
            frequency=PaymentFrequency.QUARTERLY,
        )

        # 5 years quarterly = 20 periods
        assert len(schedule) == 20

    def test_schedule_periods_property(self):
        """Test accessing periods property."""
        schedule = CDSSchedule(
            accrual_start=date(2020, 3, 20),
            maturity=date(2021, 3, 20),
            frequency=PaymentFrequency.QUARTERLY,
        )

        assert len(schedule.periods) == 4

    def test_schedule_iteration(self):
        """Test iterating over schedule."""
        schedule = CDSSchedule(
            accrual_start=date(2020, 3, 20),
            maturity=date(2020, 9, 20),
            frequency=PaymentFrequency.QUARTERLY,
        )

        periods = list(schedule)
        assert len(periods) == 2

    def test_schedule_indexing(self):
        """Test indexing into schedule."""
        schedule = CDSSchedule(
            accrual_start=date(2020, 3, 20),
            maturity=date(2020, 9, 20),
            frequency=PaymentFrequency.QUARTERLY,
        )

        first = schedule[0]
        assert first.accrual_start == date(2020, 3, 20)

    def test_schedule_dates_alignment(self):
        """Test that schedule dates are properly aligned."""
        schedule = CDSSchedule(
            accrual_start=date(2020, 3, 20),
            maturity=date(2020, 9, 20),
            frequency=PaymentFrequency.QUARTERLY,
        )

        # First period ends where second begins
        assert schedule[0].accrual_end == schedule[1].accrual_start
        # Last period ends at maturity
        assert schedule[-1].accrual_end == date(2020, 9, 20)

    def test_schedule_year_fractions(self):
        """Test year fraction calculation."""
        schedule = CDSSchedule(
            accrual_start=date(2020, 3, 20),
            maturity=date(2020, 6, 20),
            frequency=PaymentFrequency.QUARTERLY,
            day_count=DayCountConvention.ACT_360,
        )

        # Single period of ~92 days / 360
        period = schedule[0]
        assert 0.25 < period.year_fraction < 0.26

    def test_schedule_semi_annual(self):
        """Test semi-annual schedule."""
        schedule = CDSSchedule(
            accrual_start=date(2020, 3, 20),
            maturity=date(2021, 3, 20),
            frequency=PaymentFrequency.SEMI_ANNUAL,
        )

        assert len(schedule) == 2

    def test_schedule_annual(self):
        """Test annual schedule."""
        schedule = CDSSchedule(
            accrual_start=date(2020, 3, 20),
            maturity=date(2023, 3, 20),
            frequency=PaymentFrequency.ANNUAL,
        )

        assert len(schedule) == 3

    def test_schedule_stub_period(self):
        """Test schedule with stub period."""
        # Start date not aligned with frequency
        schedule = CDSSchedule(
            accrual_start=date(2020, 2, 15),
            maturity=date(2020, 12, 20),
            frequency=PaymentFrequency.QUARTERLY,
        )

        # First period should be short (stub)
        first_period = schedule[0]
        assert first_period.year_fraction < 0.25


class TestGenerateCDSSchedule:
    """Tests for generate_cds_schedule function."""

    def test_generate_default_params(self):
        """Test generating schedule with default parameters."""
        schedule = generate_cds_schedule(
            accrual_start='20/03/2020',
            maturity='20/03/2025',
        )

        # Default is quarterly
        assert len(schedule) == 20

    def test_generate_with_string_dates(self):
        """Test generating schedule with string dates."""
        schedule = generate_cds_schedule(
            accrual_start='20/03/2020',
            maturity='20/09/2020',
            frequency=PaymentFrequency.QUARTERLY,
        )

        assert len(schedule) == 2


class TestAccruedDays:
    """Tests for accrued days calculation."""

    def test_get_accrued_days_mid_period(self):
        """Test accrued days in middle of period."""
        schedule = CDSSchedule(
            accrual_start=date(2020, 3, 20),
            maturity=date(2020, 9, 20),
            frequency=PaymentFrequency.QUARTERLY,
        )

        # Value date in middle of first period
        accrued, total = get_accrued_days(date(2020, 4, 20), schedule)
        assert accrued == 31  # Mar 20 to Apr 20
        assert total > 0

    def test_get_accrued_days_start_of_period(self):
        """Test accrued days at start of period."""
        schedule = CDSSchedule(
            accrual_start=date(2020, 3, 20),
            maturity=date(2020, 9, 20),
            frequency=PaymentFrequency.QUARTERLY,
        )

        accrued, total = get_accrued_days(date(2020, 3, 20), schedule)
        assert accrued == 0

    def test_get_accrued_days_before_schedule(self):
        """Test accrued days before schedule start."""
        schedule = CDSSchedule(
            accrual_start=date(2020, 3, 20),
            maturity=date(2020, 9, 20),
            frequency=PaymentFrequency.QUARTERLY,
        )

        accrued, total = get_accrued_days(date(2020, 1, 1), schedule)
        assert accrued == 0
        assert total == 0


class TestAccruedInterest:
    """Tests for accrued interest calculation."""

    def test_calculate_accrued_interest(self):
        """Test accrued interest calculation."""
        schedule = CDSSchedule(
            accrual_start=date(2020, 3, 20),
            maturity=date(2020, 9, 20),
            frequency=PaymentFrequency.QUARTERLY,
            day_count=DayCountConvention.ACT_360,
        )

        # 100 bps coupon, 1M notional
        ai = calculate_accrued_interest(
            value_date=date(2020, 4, 20),
            schedule=schedule,
            coupon_rate=0.01,  # 100 bps
            notional=1_000_000,
        )

        # 31 days of accrual at 100 bps on 1M
        # AI = 1M * 0.01 * 31/360 = ~861
        assert 800 < ai < 900

    def test_calculate_accrued_interest_at_start(self):
        """Test accrued interest at period start is zero."""
        schedule = CDSSchedule(
            accrual_start=date(2020, 3, 20),
            maturity=date(2020, 9, 20),
            frequency=PaymentFrequency.QUARTERLY,
        )

        ai = calculate_accrued_interest(
            value_date=date(2020, 3, 20),
            schedule=schedule,
            coupon_rate=0.01,
            notional=1_000_000,
        )

        assert ai == 0.0

    def test_calculate_accrued_interest_outside_schedule(self):
        """Test accrued interest outside schedule is zero."""
        schedule = CDSSchedule(
            accrual_start=date(2020, 3, 20),
            maturity=date(2020, 9, 20),
            frequency=PaymentFrequency.QUARTERLY,
        )

        ai = calculate_accrued_interest(
            value_date=date(2019, 1, 1),
            schedule=schedule,
            coupon_rate=0.01,
            notional=1_000_000,
        )

        assert ai == 0.0
