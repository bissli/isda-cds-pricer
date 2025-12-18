"""
Shared test fixtures for CDS pricer tests.
"""

import json
import os
import sys

import pytest
import pathlib

# Add src to path for imports
sys.path.insert(0, os.path.join(pathlib.Path(__file__).parent, '..', 'src'))


@pytest.fixture
def sample_swap_rates():
    """EUR swap rates with some negative short-term rates."""
    return [
        -0.00369, -0.00340, -0.00329, -0.00271, -0.00219, -0.00187,
        -0.00149, 0.000040, 0.00159, 0.00303, 0.00435, 0.00559,
        0.00675, 0.00785, 0.00887
    ]


@pytest.fixture
def sample_swap_tenors():
    """Swap tenors matching sample_swap_rates."""
    return [
        '1M', '2M', '3M', '6M', '9M', '1Y', '2Y', '3Y', '4Y',
        '5Y', '6Y', '7Y', '8Y', '9Y', '10Y'
    ]


@pytest.fixture
def sample_swap_maturity_dates():
    """Swap maturity dates matching sample_swap_rates."""
    return [
        '12/2/2018', '12/3/2018', '10/4/2018', '10/07/2018', '10/10/2018',
        '10/1/2019', '10/01/2020', '10/1/2021', '10/1/2022', '10/1/2023',
        '10/1/2024', '10/1/2025', '10/1/2026', '10/01/2027', '10/01/2028'
    ]


@pytest.fixture
def sample_credit_spreads():
    """Credit spreads for a BBB corporate."""
    return [0.84054, 0.58931, 0.40310, 0.33168, 0.30398, 0.28037, 0.25337, 0.23090]


@pytest.fixture
def sample_credit_spread_tenors():
    """Tenors for credit spreads."""
    return ['6M', '1Y', '2Y', '3Y', '4Y', '5Y', '7Y', '10Y']


@pytest.fixture
def trade_date():
    """Sample trade date."""
    return '12/12/2014'


@pytest.fixture
def value_date():
    """Sample value date."""
    return '08/01/2018'


@pytest.fixture
def maturity_date():
    """Sample maturity date."""
    return '20/12/2019'


@pytest.fixture
def accrual_start_date():
    """Sample accrual start date."""
    return '20/9/2014'


@pytest.fixture
def baseline_results():
    """Load baseline results if available."""
    baseline_path = os.path.join(
        pathlib.Path(__file__).parent, '..', 'baseline_results.json'
    )
    if pathlib.Path(baseline_path).exists():
        with pathlib.Path(baseline_path).open('r') as f:
            return json.load(f)
    return None


# USD swap rates (for alternative market data tests)
@pytest.fixture
def usd_swap_rates():
    """USD swap rates (positive rate environment)."""
    return [
        0.02, 0.021, 0.022, 0.025, 0.027, 0.03,
        0.035, 0.038, 0.04, 0.042, 0.044, 0.046,
        0.047, 0.048, 0.05
    ]


@pytest.fixture
def usd_swap_tenors():
    """USD swap tenors."""
    return [
        '1M', '2M', '3M', '6M', '9M', '1Y', '2Y', '3Y', '4Y',
        '5Y', '6Y', '7Y', '8Y', '9Y', '10Y'
    ]
