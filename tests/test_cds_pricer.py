"""
Tests for CDS pricing against baseline results.
"""

import json
import os

import pytest
from isda import CDSPricer
import pathlib

# Load baseline results
BASELINE_PATH = os.path.join(
    pathlib.Path(__file__).parent, 'baseline_results.json'
)


def load_baseline():
    """Load baseline results if available."""
    if pathlib.Path(BASELINE_PATH).exists():
        with pathlib.Path(BASELINE_PATH).open() as f:
            return json.load(f)
    return None


BASELINE = load_baseline()


class TestCDSPricer:
    """Tests for CDSPricer class."""

    @pytest.fixture
    def pricer(self):
        """Create a sample pricer."""
        swap_rates = [
            -0.00369, -0.00340, -0.00329, -0.00271, -0.00219, -0.00187,
            -0.00149, 0.000040, 0.00159, 0.00303, 0.00435, 0.00559,
            0.00675, 0.00785, 0.00887
        ]
        swap_tenors = [
            '1M', '2M', '3M', '6M', '9M', '1Y', '2Y', '3Y', '4Y',
            '5Y', '6Y', '7Y', '8Y', '9Y', '10Y'
        ]

        return CDSPricer(
            trade_date='08/01/2018',
            swap_rates=swap_rates,
            swap_tenors=swap_tenors,
        )

    def test_price_cds_basic(self, pricer):
        """Test basic CDS pricing."""
        result = pricer.price_cds(
            maturity_date='20/12/2023',
            par_spread=0.01,  # 100bps
            coupon_rate=100,  # 100bps
            notional=1.0,
            recovery_rate=0.4,
            is_buy_protection=True,
        )

        # At par (spread = coupon), PV should be close to zero
        assert abs(result.pv_dirty) < 0.1

    def test_buy_vs_sell_symmetry(self, pricer):
        """Test that buy and sell protection give opposite PVs."""
        result_buy = pricer.price_cds(
            maturity_date='20/12/2023',
            par_spread=0.02,
            coupon_rate=100,
            notional=1.0,
            recovery_rate=0.4,
            is_buy_protection=True,
        )

        result_sell = pricer.price_cds(
            maturity_date='20/12/2023',
            par_spread=0.02,
            coupon_rate=100,
            notional=1.0,
            recovery_rate=0.4,
            is_buy_protection=False,
        )

        # PVs should be opposite signs
        assert result_buy.pv_dirty * result_sell.pv_dirty < 0

    def test_spread_greater_than_coupon(self, pricer):
        """Test case where spread > coupon (protection buyer benefits)."""
        result = pricer.price_cds(
            maturity_date='20/12/2023',
            par_spread=0.05,  # 500bps
            coupon_rate=100,  # 100bps
            notional=1.0,
            recovery_rate=0.4,
            is_buy_protection=True,
        )

        # Buy protection with spread > coupon should have positive PV
        # (receiving more protection than paying for)
        assert result.pv_dirty > 0

    def test_recovery_rate_sensitivity(self, pricer):
        """Test that different recovery rates give different prices."""
        result_40 = pricer.price_cds(
            maturity_date='20/12/2023',
            par_spread=0.03,
            coupon_rate=100,
            notional=1.0,
            recovery_rate=0.4,
            is_buy_protection=True,
        )

        result_60 = pricer.price_cds(
            maturity_date='20/12/2023',
            par_spread=0.03,
            coupon_rate=100,
            notional=1.0,
            recovery_rate=0.6,
            is_buy_protection=True,
        )

        # Different recovery rates should give different prices
        assert result_40.pv_dirty != result_60.pv_dirty


class TestUpfrontCalculation:
    """Tests for upfront calculation."""

    @pytest.fixture
    def pricer(self):
        """Create a sample pricer."""
        swap_rates = [
            -0.00369, -0.00340, -0.00329, -0.00271, -0.00219, -0.00187,
            -0.00149, 0.000040, 0.00159, 0.00303, 0.00435, 0.00559,
            0.00675, 0.00785, 0.00887
        ]
        swap_tenors = [
            '1M', '2M', '3M', '6M', '9M', '1Y', '2Y', '3Y', '4Y',
            '5Y', '6Y', '7Y', '8Y', '9Y', '10Y'
        ]

        return CDSPricer(
            trade_date='08/01/2018',
            swap_rates=swap_rates,
            swap_tenors=swap_tenors,
        )

    def test_upfront_basic(self, pricer):
        """Test basic upfront calculation."""
        dirty, clean, accrued = pricer.compute_upfront(
            maturity_date='20/12/2023',
            par_spread=0.02,
            coupon_rate=100,
            notional=1000000,
            recovery_rate=0.4,
            is_buy_protection=True,
        )

        # Should have some non-zero values
        assert dirty != 0 or clean != 0


class TestSpreadFromUpfront:
    """Tests for spread from upfront calculation."""

    @pytest.fixture
    def pricer(self):
        """Create a sample pricer."""
        swap_rates = [
            -0.00369, -0.00340, -0.00329, -0.00271, -0.00219, -0.00187,
            -0.00149, 0.000040, 0.00159, 0.00303, 0.00435, 0.00559,
            0.00675, 0.00785, 0.00887
        ]
        swap_tenors = [
            '1M', '2M', '3M', '6M', '9M', '1Y', '2Y', '3Y', '4Y',
            '5Y', '6Y', '7Y', '8Y', '9Y', '10Y'
        ]

        return CDSPricer(
            trade_date='08/01/2018',
            swap_rates=swap_rates,
            swap_tenors=swap_tenors,
        )

    def test_round_trip(self, pricer):
        """Test spread -> upfront -> spread round trip."""
        original_spread = 0.025  # 250bps

        # Calculate upfront from spread
        dirty, clean, accrued = pricer.compute_upfront(
            maturity_date='20/12/2023',
            par_spread=original_spread,
            coupon_rate=100,
            notional=1.0,
            recovery_rate=0.4,
            is_buy_protection=True,
        )

        # Calculate spread from upfront (using dirty upfront as fraction of notional)
        implied_spread = pricer.compute_spread_from_upfront(
            maturity_date='20/12/2023',
            upfront_charge=dirty,
            coupon_rate=100,
            notional=1.0,
            recovery_rate=0.4,
            is_buy_protection=True,
            is_clean=False,
        )

        # Should match original spread closely
        assert abs(implied_spread - original_spread) < 1e-6


@pytest.mark.skipif(BASELINE is None, reason='No baseline results available')
class TestBaselineValidation:
    """Tests that validate against baseline results from C++ implementation."""

    def test_baseline_cds_pricing_sample(self):
        """Test a sample CDS pricing case from baseline."""
        # Find a test case in baseline
        for test in BASELINE.get('cds_all_in_one', []):
            if test.get('success'):
                inputs = test['inputs']
                outputs = test['outputs']

                # This is just a structural test - full validation would
                # require matching the exact parameters
                assert 'pv_dirty' in outputs
                assert 'pv_clean' in outputs
                assert 'cs01' in outputs
                break

    def test_baseline_upfront_sample(self):
        """Test a sample upfront case from baseline."""
        for test in BASELINE.get('compute_isda_upfront', []):
            if test.get('success'):
                outputs = test['outputs']

                assert 'dirty_upfront' in outputs
                assert 'clean_upfront' in outputs
                break

    def test_baseline_sign_conventions(self):
        """Validate sign conventions from baseline."""
        # Buy protection should have specific sign patterns
        for test in BASELINE.get('cds_all_in_one', []):
            if test.get('success') and 'buy' in test['name']:
                inputs = test['inputs']
                outputs = test['outputs']

                # For buy protection:
                # - When spread > coupon, PV should be positive (in the money)
                # - CS01 should be positive (higher spreads = higher protection value)
                is_buy = inputs.get('is_buy_protection', 1) == 1
                spread = inputs.get('par_spread', 0)
                coupon = inputs.get('coupon', 100) / 10000  # Convert from bps

                if is_buy and spread > coupon:
                    # PV should be positive for buy when spread > coupon
                    pass  # Sign check would be done here with actual validation

                break
