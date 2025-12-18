"""
Tests for date utilities.
"""

import pytest
from datetime import date

from isda import parse_date, year_fraction, add_months, add_days, add_years
from isda import DayCountConvention


class TestParseDate:
    """Tests for parse_date function."""

    def test_parse_dd_mm_yyyy(self):
        """Test DD/MM/YYYY format."""
        d = parse_date('15/03/2020')
        assert d == date(2020, 3, 15)

    def test_parse_iso_format(self):
        """Test YYYY-MM-DD format."""
        d = parse_date('2020-03-15')
        assert d == date(2020, 3, 15)

    def test_parse_date_object(self):
        """Test passing date object directly."""
        d = date(2020, 3, 15)
        assert parse_date(d) == d

    def test_parse_invalid_raises(self):
        """Test invalid format raises ValueError."""
        with pytest.raises(ValueError):
            parse_date('invalid')


class TestYearFraction:
    """Tests for year_fraction function."""

    def test_act_360(self):
        """Test ACT/360 day count."""
        d1 = date(2020, 1, 1)
        d2 = date(2020, 4, 1)  # 91 days
        yf = year_fraction(d1, d2, DayCountConvention.ACT_360)
        assert abs(yf - 91 / 360) < 1e-10

    def test_act_365f(self):
        """Test ACT/365F day count."""
        d1 = date(2020, 1, 1)
        d2 = date(2020, 4, 1)  # 91 days
        yf = year_fraction(d1, d2, DayCountConvention.ACT_365F)
        assert abs(yf - 91 / 365) < 1e-10

    def test_thirty_360(self):
        """Test 30/360 day count."""
        d1 = date(2020, 1, 15)
        d2 = date(2020, 4, 15)  # 3 months = 90 days in 30/360
        yf = year_fraction(d1, d2, DayCountConvention.THIRTY_360)
        assert abs(yf - 90 / 360) < 1e-10

    def test_full_year_act_365(self):
        """Test full year with ACT/365F."""
        d1 = date(2020, 1, 1)
        d2 = date(2021, 1, 1)  # 366 days (leap year)
        yf = year_fraction(d1, d2, DayCountConvention.ACT_365F)
        assert abs(yf - 366 / 365) < 1e-10


class TestAddMonths:
    """Tests for add_months function."""

    def test_add_one_month(self):
        """Test adding one month."""
        d = date(2020, 1, 15)
        result = add_months(d, 1)
        assert result == date(2020, 2, 15)

    def test_add_months_year_rollover(self):
        """Test month addition with year rollover."""
        d = date(2020, 11, 15)
        result = add_months(d, 3)
        assert result == date(2021, 2, 15)

    def test_add_months_end_of_month(self):
        """Test adding months to end of month."""
        d = date(2020, 1, 31)
        result = add_months(d, 1)
        # Feb has only 29 days in 2020
        assert result == date(2020, 2, 29)

    def test_subtract_months(self):
        """Test subtracting months."""
        d = date(2020, 3, 15)
        result = add_months(d, -2)
        assert result == date(2020, 1, 15)


class TestAddDays:
    """Tests for add_days function."""

    def test_add_days(self):
        """Test adding days."""
        d = date(2020, 1, 15)
        result = add_days(d, 10)
        assert result == date(2020, 1, 25)

    def test_subtract_days(self):
        """Test subtracting days."""
        d = date(2020, 1, 15)
        result = add_days(d, -10)
        assert result == date(2020, 1, 5)

    def test_add_days_month_rollover(self):
        """Test day addition with month rollover."""
        d = date(2020, 1, 25)
        result = add_days(d, 10)
        assert result == date(2020, 2, 4)


class TestAddYears:
    """Tests for add_years function."""

    def test_add_year(self):
        """Test adding one year."""
        d = date(2020, 3, 15)
        result = add_years(d, 1)
        assert result == date(2021, 3, 15)

    def test_add_year_feb29(self):
        """Test adding year from Feb 29 to non-leap year."""
        d = date(2020, 2, 29)
        result = add_years(d, 1)
        assert result == date(2021, 2, 28)
