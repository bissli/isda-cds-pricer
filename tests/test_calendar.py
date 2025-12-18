"""
Tests for calendar and business day functions.
"""

from datetime import date

from isda.calendar import Calendar, adjust_date
from isda.dates import add_business_days, is_business_day
from isda.enums import BadDayConvention


class TestCalendar:
    """Tests for Calendar class."""

    def test_create_empty_calendar(self):
        """Test creating calendar with no holidays."""
        cal = Calendar()
        assert len(cal._holidays) == 0

    def test_create_calendar_with_holidays(self):
        """Test creating calendar with holidays."""
        holidays = {date(2020, 1, 1), date(2020, 12, 25)}
        cal = Calendar(holidays=holidays)
        assert len(cal._holidays) == 2

    def test_is_holiday(self):
        """Test holiday check."""
        holidays = {date(2020, 1, 1)}
        cal = Calendar(holidays=holidays)

        assert cal.is_holiday(date(2020, 1, 1))
        assert not cal.is_holiday(date(2020, 1, 2))

    def test_is_business_day_weekday(self):
        """Test that weekdays are business days."""
        cal = Calendar()
        # Wednesday Jan 15, 2020
        assert cal.is_business_day(date(2020, 1, 15))

    def test_is_business_day_weekend(self):
        """Test that weekends are not business days."""
        cal = Calendar()
        # Saturday Jan 18, 2020
        assert not cal.is_business_day(date(2020, 1, 18))
        # Sunday Jan 19, 2020
        assert not cal.is_business_day(date(2020, 1, 19))

    def test_is_business_day_holiday(self):
        """Test that holidays are not business days."""
        holidays = {date(2020, 1, 15)}  # Wednesday
        cal = Calendar(holidays=holidays)
        assert not cal.is_business_day(date(2020, 1, 15))

    def test_add_holiday(self):
        """Test adding a single holiday."""
        cal = Calendar()
        cal.add_holiday(date(2020, 1, 1))
        assert cal.is_holiday(date(2020, 1, 1))

    def test_add_holidays(self):
        """Test adding multiple holidays."""
        cal = Calendar()
        cal.add_holidays({date(2020, 1, 1), date(2020, 12, 25)})
        assert cal.is_holiday(date(2020, 1, 1))
        assert cal.is_holiday(date(2020, 12, 25))


class TestAdjustDate:
    """Tests for date adjustment functions."""

    def test_adjust_none(self):
        """Test no adjustment."""
        d = date(2020, 1, 18)  # Saturday
        adjusted = adjust_date(d, BadDayConvention.NONE)
        assert adjusted == d

    def test_adjust_following(self):
        """Test following adjustment."""
        d = date(2020, 1, 18)  # Saturday
        adjusted = adjust_date(d, BadDayConvention.FOLLOWING)
        assert adjusted == date(2020, 1, 20)  # Monday

    def test_adjust_preceding(self):
        """Test preceding adjustment."""
        d = date(2020, 1, 18)  # Saturday
        adjusted = adjust_date(d, BadDayConvention.PRECEDING)
        assert adjusted == date(2020, 1, 17)  # Friday

    def test_adjust_modified_following_same_month(self):
        """Test modified following stays in same month."""
        d = date(2020, 1, 18)  # Saturday mid-month
        adjusted = adjust_date(d, BadDayConvention.MODIFIED_FOLLOWING)
        assert adjusted == date(2020, 1, 20)  # Monday

    def test_adjust_modified_following_end_of_month(self):
        """Test modified following falls back at month end."""
        d = date(2020, 1, 31)  # Friday
        # Jan 31, 2020 is a Friday, so no adjustment needed
        adjusted = adjust_date(d, BadDayConvention.MODIFIED_FOLLOWING)
        assert adjusted == date(2020, 1, 31)

    def test_adjust_modified_following_crosses_month(self):
        """Test modified following falls back when crossing month."""
        # February 29, 2020 is Saturday, March 1 is Sunday
        # Following would be March 2, but that crosses month
        # So should fall back to Friday Feb 28
        d = date(2020, 2, 29)  # Saturday
        adjusted = adjust_date(d, BadDayConvention.MODIFIED_FOLLOWING)
        assert adjusted == date(2020, 2, 28)  # Friday


class TestBusinessDayArithmetic:
    """Tests for business day arithmetic."""

    def test_is_business_day_function(self):
        """Test standalone is_business_day function."""
        assert is_business_day(date(2020, 1, 15))  # Wednesday
        assert not is_business_day(date(2020, 1, 18))  # Saturday

    def test_add_business_days_positive(self):
        """Test adding positive business days."""
        # Wednesday Jan 15 + 2 business days = Friday Jan 17
        result = add_business_days(date(2020, 1, 15), 2)
        assert result == date(2020, 1, 17)

    def test_add_business_days_over_weekend(self):
        """Test adding business days over weekend."""
        # Friday Jan 17 + 1 business day = Monday Jan 20
        result = add_business_days(date(2020, 1, 17), 1)
        assert result == date(2020, 1, 20)

    def test_add_business_days_negative(self):
        """Test subtracting business days."""
        # Wednesday Jan 15 - 2 business days = Monday Jan 13
        result = add_business_days(date(2020, 1, 15), -2)
        assert result == date(2020, 1, 13)

    def test_add_business_days_zero(self):
        """Test adding zero business days."""
        d = date(2020, 1, 15)
        result = add_business_days(d, 0)
        assert result == d

    def test_business_days_between(self):
        """Test counting business days between dates."""
        cal = Calendar()
        # Wed Jan 15 to Fri Jan 17 = 2 business days (Thu + Fri)
        count = cal.business_days_between(date(2020, 1, 15), date(2020, 1, 17))
        assert count == 2

    def test_business_days_between_over_weekend(self):
        """Test counting business days over weekend."""
        cal = Calendar()
        # Fri Jan 17 to Mon Jan 20 = 1 business day (Mon)
        count = cal.business_days_between(date(2020, 1, 17), date(2020, 1, 20))
        assert count == 1
