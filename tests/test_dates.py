"""
Tests for date utilities using opendate library.
"""

from isda import DayCountConvention
from opendate import Date, Interval


class TestDateParse:
    """Tests for Date.parse function."""

    def test_parse_dd_mm_yyyy(self):
        """Test DD/MM/YYYY format."""
        d = Date.parse('15/03/2020')
        assert d.year == 2020
        assert d.month == 3
        assert d.day == 15

    def test_parse_iso_format(self):
        """Test YYYY-MM-DD format."""
        d = Date.parse('2020-03-15')
        assert d.year == 2020
        assert d.month == 3
        assert d.day == 15


class TestYearFraction:
    """Tests for year fraction using opendate Interval."""

    def test_act_360(self):
        """Test ACT/360 day count."""
        d1 = Date(2020, 1, 1)
        d2 = Date(2020, 4, 1)  # 91 days
        yf = Interval(d1, d2).yearfrac(basis=DayCountConvention.ACT_360.value)
        assert abs(yf - 91 / 360) < 1e-10

    def test_act_365f(self):
        """Test ACT/365F day count."""
        d1 = Date(2020, 1, 1)
        d2 = Date(2020, 4, 1)  # 91 days
        yf = Interval(d1, d2).yearfrac(basis=DayCountConvention.ACT_365F.value)
        assert abs(yf - 91 / 365) < 1e-10

    def test_thirty_360(self):
        """Test 30/360 day count."""
        d1 = Date(2020, 1, 15)
        d2 = Date(2020, 4, 15)  # 3 months = 90 days in 30/360
        yf = Interval(d1, d2).yearfrac(basis=DayCountConvention.THIRTY_360.value)
        assert abs(yf - 90 / 360) < 1e-10

    def test_full_year_act_365(self):
        """Test full year with ACT/365F."""
        d1 = Date(2020, 1, 1)
        d2 = Date(2021, 1, 1)  # 366 days (leap year)
        yf = Interval(d1, d2).yearfrac(basis=DayCountConvention.ACT_365F.value)
        assert abs(yf - 366 / 365) < 1e-10


class TestDateArithmetic:
    """Tests for Date arithmetic methods."""

    def test_add_one_month(self):
        """Test adding one month."""
        d = Date(2020, 1, 15)
        result = d.add(months=1)
        assert result == Date(2020, 2, 15)

    def test_add_months_year_rollover(self):
        """Test month addition with year rollover."""
        d = Date(2020, 11, 15)
        result = d.add(months=3)
        assert result == Date(2021, 2, 15)

    def test_add_months_end_of_month(self):
        """Test adding months to end of month."""
        d = Date(2020, 1, 31)
        result = d.add(months=1)
        # Feb has only 29 days in 2020
        assert result == Date(2020, 2, 29)

    def test_subtract_months(self):
        """Test subtracting months."""
        d = Date(2020, 3, 15)
        result = d.subtract(months=2)
        assert result == Date(2020, 1, 15)

    def test_add_days(self):
        """Test adding days."""
        d = Date(2020, 1, 15)
        result = d.add(days=10)
        assert result == Date(2020, 1, 25)

    def test_subtract_days(self):
        """Test subtracting days."""
        d = Date(2020, 1, 15)
        result = d.subtract(days=10)
        assert result == Date(2020, 1, 5)

    def test_add_days_month_rollover(self):
        """Test day addition with month rollover."""
        d = Date(2020, 1, 25)
        result = d.add(days=10)
        assert result == Date(2020, 2, 4)

    def test_add_year(self):
        """Test adding one year."""
        d = Date(2020, 3, 15)
        result = d.add(years=1)
        assert result == Date(2021, 3, 15)

    def test_add_year_feb29(self):
        """Test adding year from Feb 29 to non-leap year."""
        d = Date(2020, 2, 29)
        result = d.add(years=1)
        assert result == Date(2021, 2, 28)
