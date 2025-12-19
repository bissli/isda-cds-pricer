"""
Tests for calendar and business day functions.
"""

from isda.calendar import adjust_date
from isda.enums import BadDayConvention
from opendate import Date


class TestAdjustDate:
    """Tests for date adjustment functions."""

    def test_adjust_none(self):
        """Test no adjustment."""
        d = Date(2020, 1, 18)  # Saturday
        adjusted = adjust_date(d, BadDayConvention.NONE)
        assert adjusted == d

    def test_adjust_following(self):
        """Test following adjustment."""
        d = Date(2020, 1, 18)  # Saturday
        adjusted = adjust_date(d, BadDayConvention.FOLLOWING)
        assert adjusted == Date(2020, 1, 20)  # Monday

    def test_adjust_preceding(self):
        """Test preceding adjustment."""
        d = Date(2020, 1, 18)  # Saturday
        adjusted = adjust_date(d, BadDayConvention.PRECEDING)
        assert adjusted == Date(2020, 1, 17)  # Friday

    def test_adjust_modified_following_same_month(self):
        """Test modified following stays in same month."""
        d = Date(2020, 1, 18)  # Saturday mid-month
        adjusted = adjust_date(d, BadDayConvention.MODIFIED_FOLLOWING)
        assert adjusted == Date(2020, 1, 20)  # Monday

    def test_adjust_modified_following_end_of_month(self):
        """Test modified following falls back at month end."""
        d = Date(2020, 1, 31)  # Friday
        # Jan 31, 2020 is a Friday, so no adjustment needed
        adjusted = adjust_date(d, BadDayConvention.MODIFIED_FOLLOWING)
        assert adjusted == Date(2020, 1, 31)

    def test_adjust_modified_following_crosses_month(self):
        """Test modified following falls back when crossing month."""
        # February 29, 2020 is Saturday, March 1 is Sunday
        # Following would be March 2, but that crosses month
        # So should fall back to Friday Feb 28
        d = Date(2020, 2, 29)  # Saturday
        adjusted = adjust_date(d, BadDayConvention.MODIFIED_FOLLOWING)
        assert adjusted == Date(2020, 2, 28)  # Friday


class TestBusinessDayArithmetic:
    """Tests for business day arithmetic using opendate."""

    def test_is_business_day_method(self):
        """Test Date.is_business_day method."""
        assert Date(2020, 1, 15).is_business_day()  # Wednesday
        assert not Date(2020, 1, 18).is_business_day()  # Saturday

    def test_add_business_days_positive(self):
        """Test adding positive business days."""
        # Wednesday Jan 15 + 2 business days = Friday Jan 17
        result = Date(2020, 1, 15).b.add(days=2)
        assert result == Date(2020, 1, 17)

    def test_add_business_days_over_weekend(self):
        """Test adding business days over weekend."""
        # Friday Jan 17 + 1 business day = Monday Jan 20
        result = Date(2020, 1, 17).b.add(days=1)
        assert result == Date(2020, 1, 20)

    def test_add_business_days_negative(self):
        """Test subtracting business days."""
        # Wednesday Jan 15 - 2 business days = Monday Jan 13
        result = Date(2020, 1, 15).b.subtract(days=2)
        assert result == Date(2020, 1, 13)

    def test_add_business_days_zero(self):
        """Test adding zero business days."""
        d = Date(2020, 1, 15)
        result = d.b.add(days=0)
        assert result == d
