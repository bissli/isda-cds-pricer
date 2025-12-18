"""
Tests for IMM date generation.
"""

import pytest
from datetime import date

from isda import next_imm_date, previous_imm_date, is_imm_date
from isda import imm_dates_for_tenors


class TestIsImmDate:
    """Tests for is_imm_date function."""

    def test_march_20_is_imm(self):
        """March 20th should be an IMM date."""
        assert is_imm_date(date(2020, 3, 20))

    def test_june_20_is_imm(self):
        """June 20th should be an IMM date."""
        assert is_imm_date(date(2020, 6, 20))

    def test_september_20_is_imm(self):
        """September 20th should be an IMM date."""
        assert is_imm_date(date(2020, 9, 20))

    def test_december_20_is_imm(self):
        """December 20th should be an IMM date."""
        assert is_imm_date(date(2020, 12, 20))

    def test_january_20_not_imm(self):
        """January 20th is not an IMM date."""
        assert not is_imm_date(date(2020, 1, 20))

    def test_march_15_not_imm(self):
        """March 15th is not an IMM date (wrong day)."""
        assert not is_imm_date(date(2020, 3, 15))


class TestNextImmDate:
    """Tests for next_imm_date function."""

    def test_next_imm_from_january(self):
        """Next IMM from January should be March or June (with semi-annual roll)."""
        imm = next_imm_date(date(2020, 1, 15))
        # With semi-annual roll (post-2015), March rolls to June
        assert imm.month in (3, 6)
        assert imm.day == 20

    def test_next_imm_from_march_19(self):
        """Next IMM from March 19 should be next IMM."""
        imm = next_imm_date(date(2020, 3, 19))
        # With semi-annual roll, March 20 rolls to June 20
        assert imm == date(2020, 6, 20)

    def test_next_imm_from_march_20(self):
        """Next IMM from March 20 should go to next IMM."""
        imm = next_imm_date(date(2020, 3, 20), include_current=False)
        # With semi-annual roll, next is June 20
        assert imm == date(2020, 6, 20)

    def test_next_imm_from_june_21(self):
        """Next IMM from June 21 should be September or December."""
        imm = next_imm_date(date(2020, 6, 21))
        # With semi-annual roll, September rolls to December
        assert imm.month == 12
        assert imm.day == 20


class TestPreviousImmDate:
    """Tests for previous_imm_date function."""

    def test_previous_imm_from_april(self):
        """Previous IMM from April should be March."""
        imm = previous_imm_date(date(2020, 4, 15))
        assert imm == date(2020, 3, 20)

    def test_previous_imm_from_march_21(self):
        """Previous IMM from March 21 should be March 20."""
        imm = previous_imm_date(date(2020, 3, 21))
        assert imm == date(2020, 3, 20)

    def test_previous_imm_from_march_20(self):
        """Previous IMM from March 20 should be December of previous year."""
        imm = previous_imm_date(date(2020, 3, 20))
        assert imm == date(2019, 12, 20)


class TestImmDatesForTenors:
    """Tests for imm_dates_for_tenors function."""

    def test_standard_tenors(self):
        """Test generating IMM dates for standard tenors."""
        tenors = [0.5, 1, 2, 3, 5]
        result = imm_dates_for_tenors(
            reference_date=date(2018, 1, 8),
            tenor_list=tenors,
        )

        assert len(result) == 5

        # Check labels
        labels = [r[0] for r in result]
        assert '6M' in labels
        assert '1Y' in labels
        assert '5Y' in labels

    def test_imm_dates_are_valid(self):
        """Test that all generated dates are valid IMM dates."""
        tenors = [0.5, 1, 2, 3, 5, 7, 10]
        result = imm_dates_for_tenors(
            reference_date=date(2018, 1, 8),
            tenor_list=tenors,
            date_format='',  # Return date objects
        )

        for label, imm in result:
            assert imm.day == 20
            assert imm.month in (6, 12)  # With semi-annual roll

    def test_dates_are_increasing(self):
        """Test that IMM dates are in increasing order."""
        tenors = [0.5, 1, 2, 3, 5, 7, 10]
        result = imm_dates_for_tenors(
            reference_date=date(2018, 1, 8),
            tenor_list=tenors,
            date_format='',
        )

        dates = [r[1] for r in result]
        for i in range(len(dates) - 1):
            assert dates[i] < dates[i + 1]
