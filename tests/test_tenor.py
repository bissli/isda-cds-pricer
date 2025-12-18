"""
Tests for tenor parsing and manipulation.
"""

from datetime import date

import pytest
from isda.tenor import Tenor, parse_tenor, tenor_to_date, tenor_to_years


class TestTenor:
    """Tests for Tenor class."""

    def test_create_tenor(self):
        """Test creating tenor objects."""
        t = Tenor(3, 'M')
        assert t.value == 3
        assert t.unit == 'M'

    def test_tenor_unit_uppercase(self):
        """Test tenor unit is uppercased."""
        t = Tenor(3, 'm')
        assert t.unit == 'M'

    def test_tenor_invalid_unit(self):
        """Test invalid unit raises error."""
        with pytest.raises(ValueError):
            Tenor(3, 'X')

    def test_tenor_str(self):
        """Test string representation."""
        t = Tenor(3, 'M')
        assert str(t) == '3M'

    def test_tenor_months_day(self):
        """Test days to months conversion."""
        t = Tenor(30, 'D')
        assert t.months == 0

    def test_tenor_months_week(self):
        """Test weeks to months conversion."""
        t = Tenor(2, 'W')
        assert t.months == 0

    def test_tenor_months_month(self):
        """Test months to months."""
        t = Tenor(3, 'M')
        assert t.months == 3

    def test_tenor_months_year(self):
        """Test years to months."""
        t = Tenor(2, 'Y')
        assert t.months == 24

    def test_tenor_days_day(self):
        """Test days to days."""
        t = Tenor(30, 'D')
        assert t.days == 30

    def test_tenor_days_week(self):
        """Test weeks to days."""
        t = Tenor(2, 'W')
        assert t.days == 14

    def test_tenor_days_month(self):
        """Test months to days (approximate)."""
        t = Tenor(3, 'M')
        assert t.days == 90

    def test_tenor_days_year(self):
        """Test years to days (approximate)."""
        t = Tenor(1, 'Y')
        assert t.days == 365

    def test_tenor_years_day(self):
        """Test days to years."""
        t = Tenor(365, 'D')
        assert abs(t.years - 1.0) < 0.01

    def test_tenor_years_week(self):
        """Test weeks to years."""
        t = Tenor(52, 'W')
        assert abs(t.years - 1.0) < 0.01

    def test_tenor_years_month(self):
        """Test months to years."""
        t = Tenor(6, 'M')
        assert t.years == 0.5

    def test_tenor_years_year(self):
        """Test years to years."""
        t = Tenor(5, 'Y')
        assert t.years == 5.0

    def test_add_to_date_days(self):
        """Test adding days to date."""
        t = Tenor(7, 'D')
        result = t.add_to_date(date(2020, 1, 1))
        assert result == date(2020, 1, 8)

    def test_add_to_date_weeks(self):
        """Test adding weeks to date."""
        t = Tenor(2, 'W')
        result = t.add_to_date(date(2020, 1, 1))
        assert result == date(2020, 1, 15)

    def test_add_to_date_months(self):
        """Test adding months to date."""
        t = Tenor(3, 'M')
        result = t.add_to_date(date(2020, 1, 15))
        assert result == date(2020, 4, 15)

    def test_add_to_date_years(self):
        """Test adding years to date."""
        t = Tenor(2, 'Y')
        result = t.add_to_date(date(2020, 1, 15))
        assert result == date(2022, 1, 15)

    def test_add_to_date_month_end(self):
        """Test adding months at month end."""
        t = Tenor(1, 'M')
        # Jan 31 + 1M = Feb 28 (non-leap year) or Feb 29 (leap year)
        result = t.add_to_date(date(2019, 1, 31))
        assert result == date(2019, 2, 28)


class TestParseTenor:
    """Tests for tenor parsing."""

    def test_parse_days(self):
        """Test parsing day tenors."""
        t = parse_tenor('7D')
        assert t.value == 7
        assert t.unit == 'D'

    def test_parse_weeks(self):
        """Test parsing week tenors."""
        t = parse_tenor('2W')
        assert t.value == 2
        assert t.unit == 'W'

    def test_parse_months(self):
        """Test parsing month tenors."""
        t = parse_tenor('3M')
        assert t.value == 3
        assert t.unit == 'M'

    def test_parse_years(self):
        """Test parsing year tenors."""
        t = parse_tenor('5Y')
        assert t.value == 5
        assert t.unit == 'Y'

    def test_parse_overnight(self):
        """Test parsing ON (overnight)."""
        t = parse_tenor('ON')
        assert t.value == 1
        assert t.unit == 'D'

    def test_parse_tomorrow_next(self):
        """Test parsing TN (tomorrow-next)."""
        t = parse_tenor('TN')
        assert t.value == 2
        assert t.unit == 'D'

    def test_parse_spot_next(self):
        """Test parsing SN (spot-next)."""
        t = parse_tenor('SN')
        assert t.value == 1
        assert t.unit == 'D'

    def test_parse_lowercase(self):
        """Test parsing lowercase tenors."""
        t = parse_tenor('3m')
        assert t.value == 3
        assert t.unit == 'M'

    def test_parse_with_spaces(self):
        """Test parsing tenors with spaces."""
        t = parse_tenor('  3M  ')
        assert t.value == 3
        assert t.unit == 'M'

    def test_parse_double_digit(self):
        """Test parsing double-digit tenors."""
        t = parse_tenor('10Y')
        assert t.value == 10
        assert t.unit == 'Y'

    def test_parse_invalid(self):
        """Test parsing invalid tenor raises error."""
        with pytest.raises(ValueError):
            parse_tenor('3X')

    def test_parse_no_number(self):
        """Test parsing tenor without number raises error."""
        with pytest.raises(ValueError):
            parse_tenor('M')


class TestTenorConversion:
    """Tests for tenor conversion functions."""

    def test_tenor_to_date_string(self):
        """Test tenor_to_date with string tenor."""
        result = tenor_to_date('3M', date(2020, 1, 15))
        assert result == date(2020, 4, 15)

    def test_tenor_to_date_object(self):
        """Test tenor_to_date with Tenor object."""
        t = Tenor(3, 'M')
        result = tenor_to_date(t, date(2020, 1, 15))
        assert result == date(2020, 4, 15)

    def test_tenor_to_years_string(self):
        """Test tenor_to_years with string tenor."""
        years = tenor_to_years('6M')
        assert years == 0.5

    def test_tenor_to_years_object(self):
        """Test tenor_to_years with Tenor object."""
        t = Tenor(6, 'M')
        years = tenor_to_years(t)
        assert years == 0.5
