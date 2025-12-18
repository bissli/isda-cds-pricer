"""
Tests for backward-compatible API functions.
"""

import pytest
from datetime import date

from isda.compat import (
    cds_all_in_one, compute_isda_upfront, calculate_spread_from_upfront_charge,
    cds_index_all_in_one
)


@pytest.fixture
def sample_trade_data():
    """Sample trade data for testing."""
    return {
        'trade_date': '08/01/2018',
        'effective_date': '08/01/2018',
        'maturity_date': '20/12/2019',
        'value_date': '08/01/2018',
        'accrual_start_date': '20/09/2014',
        'settle_date': '08/01/2018',
        'recovery_rate': 0.4,
        'coupon': 100,  # bps
        'notional': 1000000.0,
        'is_buy_protection': 1,
    }


@pytest.fixture
def sample_swap_rates():
    """Sample swap rates."""
    return [
        -0.00369, -0.00340, -0.00329, -0.00271, -0.00219, -0.00187,
        -0.00149, 0.000040, 0.00159, 0.00303, 0.00435, 0.00559,
        0.00675, 0.00785, 0.00887
    ]


@pytest.fixture
def sample_swap_tenors():
    """Sample swap tenors."""
    return [
        '1M', '2M', '3M', '6M', '9M', '1Y', '2Y', '3Y', '4Y',
        '5Y', '6Y', '7Y', '8Y', '9Y', '10Y'
    ]


@pytest.fixture
def sample_swap_maturity_dates():
    """Sample swap maturity dates."""
    return [
        '12/02/2018', '12/03/2018', '10/04/2018', '10/07/2018', '10/10/2018',
        '10/01/2019', '10/01/2020', '10/01/2021', '10/01/2022', '10/01/2023',
        '10/01/2024', '10/01/2025', '10/01/2026', '10/01/2027', '10/01/2028'
    ]


@pytest.fixture
def sample_credit_spreads():
    """Sample credit spreads for curve building."""
    return [0.0050, 0.0055, 0.0060, 0.0065, 0.0070]


@pytest.fixture
def sample_credit_spread_tenors():
    """Sample credit spread tenors."""
    return ['1Y', '2Y', '3Y', '5Y', '7Y']


class TestCDSAllInOne:
    """Tests for cds_all_in_one function."""

    def test_cds_all_in_one_basic(
        self, sample_trade_data, sample_swap_rates, sample_swap_tenors,
        sample_swap_maturity_dates, sample_credit_spreads, sample_credit_spread_tenors
    ):
        """Test basic cds_all_in_one functionality."""
        result = cds_all_in_one(
            trade_date=sample_trade_data['trade_date'],
            effective_date=sample_trade_data['effective_date'],
            maturity_date=sample_trade_data['maturity_date'],
            value_date=sample_trade_data['value_date'],
            accrual_start_date=sample_trade_data['accrual_start_date'],
            recovery_rate=sample_trade_data['recovery_rate'],
            coupon=sample_trade_data['coupon'],
            notional=sample_trade_data['notional'],
            is_buy_protection=sample_trade_data['is_buy_protection'],
            swap_rates=sample_swap_rates,
            swap_tenors=sample_swap_tenors,
            swap_maturity_dates=sample_swap_maturity_dates,
            credit_spreads=sample_credit_spreads,
            credit_spread_tenors=sample_credit_spread_tenors,
            spread_roll_tenors=['1Y', '2Y', '3Y'],
            imm_dates=['20/03/2018', '20/06/2018'],
            scenario_shifts=[0.0, 0.0001],
        )

        # Should return tuple of 3 tuples
        assert len(result) == 3
        main_results, pvbp_results, par_spread_results = result

        # Main results should have pv_dirty, pv_clean, ai, cs01, dv01, duration
        assert len(main_results) == 6
        pv_dirty, pv_clean, ai, cs01, dv01, duration_ms = main_results

        # All values should be finite
        assert all(abs(x) < 1e15 for x in main_results[:5])

    def test_cds_all_in_one_buy_vs_sell(
        self, sample_trade_data, sample_swap_rates, sample_swap_tenors,
        sample_swap_maturity_dates, sample_credit_spreads, sample_credit_spread_tenors
    ):
        """Test buy vs sell protection gives opposite signs."""
        common_args = {
            'trade_date': sample_trade_data['trade_date'],
            'effective_date': sample_trade_data['effective_date'],
            'maturity_date': sample_trade_data['maturity_date'],
            'value_date': sample_trade_data['value_date'],
            'accrual_start_date': sample_trade_data['accrual_start_date'],
            'recovery_rate': 0.4,
            'coupon': 100,
            'notional': 1.0,
            'swap_rates': sample_swap_rates,
            'swap_tenors': sample_swap_tenors,
            'swap_maturity_dates': sample_swap_maturity_dates,
            'credit_spreads': sample_credit_spreads,
            'credit_spread_tenors': sample_credit_spread_tenors,
            'spread_roll_tenors': ['1Y', '2Y', '3Y'],
            'imm_dates': ['20/03/2018', '20/06/2018'],
            'scenario_shifts': [0.0],
        }

        buy_result = cds_all_in_one(is_buy_protection=1, **common_args)
        sell_result = cds_all_in_one(is_buy_protection=0, **common_args)

        buy_pv = buy_result[0][0]  # pv_dirty
        sell_pv = sell_result[0][0]

        # Buy and sell should have opposite signs
        assert buy_pv * sell_pv < 0 or abs(buy_pv + sell_pv) < 0.0001


class TestComputeISDAUpfront:
    """Tests for compute_isda_upfront function."""

    def test_compute_upfront_basic(
        self, sample_trade_data, sample_swap_rates, sample_swap_tenors
    ):
        """Test basic upfront calculation."""
        dirty, clean, ai, duration = compute_isda_upfront(
            trade_date=sample_trade_data['trade_date'],
            maturity_date=sample_trade_data['maturity_date'],
            accrual_start_date=sample_trade_data['accrual_start_date'],
            settle_date=sample_trade_data['settle_date'],
            recovery_rate=0.4,
            coupon_rate=100,
            notional=1000000.0,
            is_buy_protection=1,
            swap_rates=sample_swap_rates,
            swap_tenors=sample_swap_tenors,
            par_spread=0.0100,  # 100 bps = at-the-money
            is_rofr=1,
        )

        # All values should be finite
        assert all(x is not None and abs(x) < 1e15 for x in [dirty, clean, ai])

    def test_compute_upfront_at_the_money(
        self, sample_trade_data, sample_swap_rates, sample_swap_tenors
    ):
        """Test upfront is near zero at-the-money."""
        dirty, clean, ai, duration = compute_isda_upfront(
            trade_date=sample_trade_data['trade_date'],
            maturity_date=sample_trade_data['maturity_date'],
            accrual_start_date=sample_trade_data['accrual_start_date'],
            settle_date=sample_trade_data['settle_date'],
            recovery_rate=0.4,
            coupon_rate=100,  # 100 bps coupon
            notional=1.0,
            is_buy_protection=1,
            swap_rates=sample_swap_rates,
            swap_tenors=sample_swap_tenors,
            par_spread=0.01,  # 100 bps spread = at-the-money
        )

        # At-the-money, clean upfront should be near zero
        assert abs(clean) < 0.1

    def test_compute_upfront_relationship(
        self, sample_trade_data, sample_swap_rates, sample_swap_tenors
    ):
        """Test dirty = clean + accrued."""
        dirty, clean, ai, duration = compute_isda_upfront(
            trade_date=sample_trade_data['trade_date'],
            maturity_date=sample_trade_data['maturity_date'],
            accrual_start_date=sample_trade_data['accrual_start_date'],
            settle_date=sample_trade_data['settle_date'],
            recovery_rate=0.4,
            coupon_rate=100,
            notional=1000000.0,
            is_buy_protection=1,
            swap_rates=sample_swap_rates,
            swap_tenors=sample_swap_tenors,
            par_spread=0.0100,
        )

        # Dirty = Clean + Accrued
        assert abs(dirty - (clean + ai)) < 1.0  # Within $1


class TestCalculateSpreadFromUpfront:
    """Tests for calculate_spread_from_upfront_charge function."""

    def test_spread_from_upfront_round_trip(
        self, sample_trade_data, sample_swap_rates, sample_swap_tenors
    ):
        """Test round-trip: spread -> upfront -> spread."""
        original_spread = 0.0150  # 150 bps

        # Get upfront from spread
        dirty, clean, ai, _ = compute_isda_upfront(
            trade_date=sample_trade_data['trade_date'],
            maturity_date=sample_trade_data['maturity_date'],
            accrual_start_date=sample_trade_data['accrual_start_date'],
            settle_date=sample_trade_data['settle_date'],
            recovery_rate=0.4,
            coupon_rate=100,
            notional=1.0,
            is_buy_protection=1,
            swap_rates=sample_swap_rates,
            swap_tenors=sample_swap_tenors,
            par_spread=original_spread,
        )

        # Get spread from upfront
        recovered_spread, _ = calculate_spread_from_upfront_charge(
            trade_date=sample_trade_data['trade_date'],
            maturity_date=sample_trade_data['maturity_date'],
            accrual_start_date=sample_trade_data['accrual_start_date'],
            settle_date=sample_trade_data['settle_date'],
            recovery_rate=0.4,
            coupon_rate=100,
            notional=1.0,
            is_buy_protection=1,
            swap_rates=sample_swap_rates,
            swap_tenors=sample_swap_tenors,
            upfront_charge=dirty,  # Using dirty upfront
            is_clean=0,
        )

        # Should recover original spread within tolerance
        assert abs(recovered_spread - original_spread) < 1e-4

    def test_spread_from_upfront_clean_vs_dirty(
        self, sample_trade_data, sample_swap_rates, sample_swap_tenors
    ):
        """Test spread from both clean and dirty upfront."""
        original_spread = 0.0200  # 200 bps

        dirty, clean, ai, _ = compute_isda_upfront(
            trade_date=sample_trade_data['trade_date'],
            maturity_date=sample_trade_data['maturity_date'],
            accrual_start_date=sample_trade_data['accrual_start_date'],
            settle_date=sample_trade_data['settle_date'],
            recovery_rate=0.4,
            coupon_rate=100,
            notional=1.0,
            is_buy_protection=1,
            swap_rates=sample_swap_rates,
            swap_tenors=sample_swap_tenors,
            par_spread=original_spread,
        )

        # From dirty upfront
        spread_dirty, _ = calculate_spread_from_upfront_charge(
            trade_date=sample_trade_data['trade_date'],
            maturity_date=sample_trade_data['maturity_date'],
            accrual_start_date=sample_trade_data['accrual_start_date'],
            settle_date=sample_trade_data['settle_date'],
            recovery_rate=0.4,
            coupon_rate=100,
            notional=1.0,
            is_buy_protection=1,
            swap_rates=sample_swap_rates,
            swap_tenors=sample_swap_tenors,
            upfront_charge=dirty,
            is_clean=0,
        )

        # From clean upfront
        spread_clean, _ = calculate_spread_from_upfront_charge(
            trade_date=sample_trade_data['trade_date'],
            maturity_date=sample_trade_data['maturity_date'],
            accrual_start_date=sample_trade_data['accrual_start_date'],
            settle_date=sample_trade_data['settle_date'],
            recovery_rate=0.4,
            coupon_rate=100,
            notional=1.0,
            is_buy_protection=1,
            swap_rates=sample_swap_rates,
            swap_tenors=sample_swap_tenors,
            upfront_charge=clean,
            is_clean=1,
        )

        # Both should give same spread (within tolerance)
        assert abs(spread_dirty - spread_clean) < 1e-4


class TestCDSIndexAllInOne:
    """Tests for cds_index_all_in_one function."""

    def test_cds_index_basic(
        self, sample_trade_data, sample_swap_rates, sample_swap_tenors,
        sample_swap_maturity_dates, sample_credit_spread_tenors
    ):
        """Test basic index CDS calculation."""
        n_names = 3
        recovery_rates = [0.4] * n_names
        credit_spreads = [[0.0100, 0.0110, 0.0120, 0.0130, 0.0140] for _ in range(n_names)]

        status, result = cds_index_all_in_one(
            trade_date=sample_trade_data['trade_date'],
            effective_date=sample_trade_data['effective_date'],
            maturity_date=sample_trade_data['maturity_date'],
            value_date=sample_trade_data['value_date'],
            accrual_start_date=sample_trade_data['accrual_start_date'],
            recovery_rate_list=recovery_rates,
            coupon=100,
            notional=1.0,
            is_buy_protection=1,
            swap_rates=sample_swap_rates,
            swap_tenors=sample_swap_tenors,
            swap_maturity_dates=sample_swap_maturity_dates,
            credit_spread_list=credit_spreads,
            credit_spread_tenors=sample_credit_spread_tenors,
            spread_roll_tenors=['1Y', '2Y', '3Y'],
            imm_dates=['20/03/2018', '20/06/2018'],
            scenario_shifts=[0.0],
        )

        assert status == 'OK'
        pv_dirty, pv_clean, ai, duration_ms = result
        assert all(abs(x) < 1e15 for x in [pv_dirty, pv_clean, ai])

    def test_cds_index_sum_of_parts(
        self, sample_trade_data, sample_swap_rates, sample_swap_tenors,
        sample_swap_maturity_dates, sample_credit_spread_tenors
    ):
        """Test index PV equals sum of individual name PVs."""
        n_names = 2
        recovery_rates = [0.4, 0.4]
        spread_1 = [0.0100, 0.0110, 0.0120, 0.0130, 0.0140]
        spread_2 = [0.0150, 0.0160, 0.0170, 0.0180, 0.0190]
        credit_spreads = [spread_1, spread_2]
        notional = 1000000.0

        # Price as index
        _, index_result = cds_index_all_in_one(
            trade_date=sample_trade_data['trade_date'],
            effective_date=sample_trade_data['effective_date'],
            maturity_date=sample_trade_data['maturity_date'],
            value_date=sample_trade_data['value_date'],
            accrual_start_date=sample_trade_data['accrual_start_date'],
            recovery_rate_list=recovery_rates,
            coupon=100,
            notional=notional,
            is_buy_protection=1,
            swap_rates=sample_swap_rates,
            swap_tenors=sample_swap_tenors,
            swap_maturity_dates=sample_swap_maturity_dates,
            credit_spread_list=credit_spreads,
            credit_spread_tenors=sample_credit_spread_tenors,
            spread_roll_tenors=['1Y', '2Y', '3Y'],
            imm_dates=['20/03/2018', '20/06/2018'],
            scenario_shifts=[0.0],
        )

        index_pv = index_result[0]  # pv_dirty

        # Price individual names
        total_individual_pv = 0.0
        for i in range(n_names):
            result = cds_all_in_one(
                trade_date=sample_trade_data['trade_date'],
                effective_date=sample_trade_data['effective_date'],
                maturity_date=sample_trade_data['maturity_date'],
                value_date=sample_trade_data['value_date'],
                accrual_start_date=sample_trade_data['accrual_start_date'],
                recovery_rate=recovery_rates[i],
                coupon=100,
                notional=notional / n_names,
                is_buy_protection=1,
                swap_rates=sample_swap_rates,
                swap_tenors=sample_swap_tenors,
                swap_maturity_dates=sample_swap_maturity_dates,
                credit_spreads=credit_spreads[i],
                credit_spread_tenors=sample_credit_spread_tenors,
                spread_roll_tenors=['1Y', '2Y', '3Y'],
                imm_dates=['20/03/2018', '20/06/2018'],
                scenario_shifts=[0.0],
            )
            total_individual_pv += result[0][0]  # pv_dirty

        # Index PV should equal sum of individual PVs
        assert abs(index_pv - total_individual_pv) < 1.0
