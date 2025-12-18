#!/usr/bin/env python3
"""
Baseline Capture Script for CDS Pricer

Runs comprehensive experiments with existing C++ implementation and captures
results as golden dataset for validation of the Python rewrite.
"""

import json
import datetime
import os
import uuid
import sys
from itertools import product
from typing import Dict, List, Any, Tuple

# Add isda module to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from isda.isda import (
    cds_all_in_one,
    compute_isda_upfront,
    calculate_spread_from_upfront_charge,
)
from isda.imm import imm_date_vector


def create_holiday_file() -> str:
    """Create temporary holiday file."""
    unique_filename = f'{uuid.uuid4()}.dat'
    holiday_list = [16010101, 20180320]
    with open(unique_filename, mode='wt', encoding='utf-8') as f:
        for h in holiday_list:
            f.write(f'{h}\n')
    return unique_filename


def cleanup_holiday_file(filename: str):
    """Remove temporary holiday file."""
    if os.path.exists(filename):
        os.remove(filename)


# ============================================================================
# Market Data Sets
# ============================================================================

# EUR negative rate environment (from tests)
EUR_SWAP_RATES = [
    -0.00369, -0.00340, -0.00329, -0.00271, -0.00219, -0.00187, -0.00149,
    0.000040, 0.00159, 0.00303, 0.00435, 0.00559, 0.00675, 0.00785, 0.00887
]
EUR_SWAP_TENORS = ['1M', '2M', '3M', '6M', '9M', '1Y', '2Y', '3Y', '4Y', '5Y', '6Y', '7Y', '8Y', '9Y', '10Y']
EUR_SWAP_MATURITIES = [
    '12/2/2018', '12/3/2018', '10/4/2018', '10/07/2018', '10/10/2018', '10/1/2019',
    '10/01/2020', '10/1/2021', '10/1/2022', '10/1/2023', '10/1/2024', '10/1/2025',
    '10/1/2026', '10/01/2027', '10/01/2028'
]

# USD positive rate environment (from TestUpfrontFee3)
USD_SWAP_RATES = [
    0.002979, 0.006419, 0.010791, 0.015937, 0.018675, 0.018777, 0.018998,
    0.019199, 0.019409, 0.019639, 0.019958, 0.020279, 0.020649, 0.021399,
    0.021989, 0.02138, 0.019411
]
USD_SWAP_TENORS = ['1M', '3M', '6M', '1Y', '2Y', '3Y', '4Y', '5Y', '6Y', '7Y', '8Y', '9Y', '10Y', '12Y', '15Y', '20Y', '30Y']

# Higher rate environment (from TestSpreadFromUpfront)
HIGH_SWAP_RATES = [
    0.032869, 0.035129, 0.037749, 0.04169, 0.04442, 0.043513, 0.041393,
    0.039835, 0.038784, 0.037992, 0.037292, 0.036762, 0.036352, 0.036092,
    0.035742, 0.035332, 0.034192, 0.032562, 0.031092
]
HIGH_SWAP_TENORS = ['1M', '2M', '3M', '6M', '1Y', '2Y', '3Y', '4Y', '5Y', '6Y', '7Y', '8Y', '9Y', '10Y', '12Y', '15Y', '20Y', '25Y', '30Y']


# ============================================================================
# Test Functions
# ============================================================================

def capture_cds_all_in_one_tests() -> List[Dict[str, Any]]:
    """Capture results from cds_all_in_one across parameter combinations."""
    results = []

    # Test parameters
    buy_sell = [0, 1]  # 0=sell, 1=buy
    recovery_rates = [0.20, 0.30, 0.40, 0.50, 0.60]
    coupons = [100.0, 500.0]  # bps
    spreads_bps = [50, 100, 200, 500, 1000]  # bps
    notionals = [1.0, 10.0, 70.0]

    # Trade setup (from TestCdsPricer)
    trade_date = '12/12/2014'
    effective_date = '13/12/2014'
    accrual_start_date = '20/9/2014'
    maturity_date = '20/12/2019'
    sdate = datetime.datetime(2018, 1, 8)
    value_date = sdate.strftime('%d/%m/%Y')

    tenor_list = [0.5, 1, 2, 3, 4, 5, 7, 10]
    imm_dates = [f[1] for f in imm_date_vector(start_date=sdate, tenor_list=tenor_list)]
    spread_roll_tenors = ['1D', '-1D', '-1W', '-1M', '-6M', '-1Y', '-5Y']
    scenario_shifts = [-50, -10, 0, 10, 20, 50, 150, 100]
    credit_spread_tenors = ['6M', '1Y', '2Y', '3Y', '4Y', '5Y', '7Y', '10Y']

    # Subset of combinations to keep runtime reasonable
    test_combinations = list(product(buy_sell, recovery_rates[:3], coupons, spreads_bps[:3], notionals[:2]))
    total = len(test_combinations)

    print(f"Running {total} cds_all_in_one test combinations...")

    for idx, (is_buy, rr, coupon, spread_bps, notional) in enumerate(test_combinations):
        spread = spread_bps / 10000.0
        credit_spreads = [spread] * 8  # flat spread curve

        test_name = f"cds_all_in_one_{'buy' if is_buy else 'sell'}_rr{int(rr*100)}_coupon{int(coupon)}_spread{spread_bps}_notional{notional}"

        try:
            f = cds_all_in_one(
                trade_date, effective_date, maturity_date, value_date, accrual_start_date,
                rr, coupon, notional, is_buy,
                EUR_SWAP_RATES, EUR_SWAP_TENORS, EUR_SWAP_MATURITIES,
                credit_spreads, credit_spread_tenors, spread_roll_tenors,
                imm_dates, scenario_shifts, 0  # verbose=0
            )

            pv_dirty, pv_clean, ai, cs01, dv01, duration_ms = f[0]
            pvbp6m, pvbp1y, pvbp2y, pvbp3y, pvbp4y, pvbp5y, pvbp7y, pvbp10y = f[1]
            par_spreads = f[2] if len(f) > 2 else None

            result = {
                'test_name': test_name,
                'inputs': {
                    'trade_date': trade_date,
                    'effective_date': effective_date,
                    'maturity_date': maturity_date,
                    'value_date': value_date,
                    'accrual_start_date': accrual_start_date,
                    'recovery_rate': rr,
                    'coupon': coupon,
                    'notional': notional,
                    'is_buy_protection': is_buy,
                    'spread_bps': spread_bps,
                    'market_data': 'EUR',
                },
                'outputs': {
                    'pv_dirty': pv_dirty,
                    'pv_clean': pv_clean,
                    'accrued_interest': ai,
                    'cs01': cs01,
                    'dv01': dv01,
                    'pvbp': {
                        '6M': pvbp6m, '1Y': pvbp1y, '2Y': pvbp2y, '3Y': pvbp3y,
                        '4Y': pvbp4y, '5Y': pvbp5y, '7Y': pvbp7y, '10Y': pvbp10y
                    },
                    'duration_ms': duration_ms,
                },
                'status': 'success'
            }

            if par_spreads:
                result['outputs']['par_spreads'] = list(par_spreads)

            results.append(result)

            if (idx + 1) % 10 == 0:
                print(f"  Completed {idx + 1}/{total}")

        except Exception as e:
            results.append({
                'test_name': test_name,
                'inputs': {'is_buy_protection': is_buy, 'recovery_rate': rr, 'coupon': coupon, 'spread_bps': spread_bps, 'notional': notional},
                'status': 'error',
                'error': str(e)
            })

    print(f"  Completed all {total} tests")
    return results


def capture_upfront_tests() -> List[Dict[str, Any]]:
    """Capture results from compute_isda_upfront across parameter combinations."""
    results = []
    holiday_file = create_holiday_file()

    try:
        # Test parameters
        spreads_bps = [25, 50, 100, 200, 500, 775, 1000]
        recovery_rates = [0.30, 0.40, 0.50]
        coupons = [100.0, 500.0]
        buy_sell = [0, 1]

        # Trade setup (from TestUpfrontFee3)
        trade_date = '31/08/2022'
        settle_date = '05/09/2022'
        accrual_start_date = '20/06/2022'
        maturity_date = '20/12/2026'
        notional = 12.0

        # Day count conventions
        swap_floating_dcc = 'ACT/360'
        swap_fixed_dcc = 'ACT/360'
        swap_fixed_freq = '1Y'
        swap_floating_freq = '1Y'
        is_rofr = 1

        test_combinations = list(product(buy_sell, recovery_rates, coupons, spreads_bps))
        total = len(test_combinations)

        print(f"Running {total} compute_isda_upfront test combinations...")

        for idx, (is_buy, rr, coupon, spread_bps) in enumerate(test_combinations):
            spread = spread_bps / 10000.0

            test_name = f"upfront_{'buy' if is_buy else 'sell'}_rr{int(rr*100)}_coupon{int(coupon)}_spread{spread_bps}"

            try:
                f = compute_isda_upfront(
                    trade_date, maturity_date, accrual_start_date, settle_date,
                    rr, coupon, notional, is_buy,
                    USD_SWAP_RATES, USD_SWAP_TENORS,
                    spread, is_rofr, holiday_file,
                    swap_floating_dcc, swap_fixed_dcc,
                    swap_fixed_freq, swap_floating_freq, 0
                )

                dirty_upfront, clean_upfront, accrued, status, duration_ms = f

                results.append({
                    'test_name': test_name,
                    'inputs': {
                        'trade_date': trade_date,
                        'maturity_date': maturity_date,
                        'accrual_start_date': accrual_start_date,
                        'settle_date': settle_date,
                        'recovery_rate': rr,
                        'coupon': coupon,
                        'notional': notional,
                        'is_buy_protection': is_buy,
                        'spread_bps': spread_bps,
                        'market_data': 'USD',
                        'swap_floating_dcc': swap_floating_dcc,
                        'swap_fixed_dcc': swap_fixed_dcc,
                    },
                    'outputs': {
                        'dirty_upfront': dirty_upfront,
                        'clean_upfront': clean_upfront,
                        'accrued_interest': accrued,
                        'status': status,
                        'duration_ms': duration_ms,
                    },
                    'status': 'success'
                })

                if (idx + 1) % 10 == 0:
                    print(f"  Completed {idx + 1}/{total}")

            except Exception as e:
                results.append({
                    'test_name': test_name,
                    'inputs': {'is_buy_protection': is_buy, 'recovery_rate': rr, 'coupon': coupon, 'spread_bps': spread_bps},
                    'status': 'error',
                    'error': str(e)
                })

        print(f"  Completed all {total} tests")

    finally:
        cleanup_holiday_file(holiday_file)

    return results


def capture_spread_from_upfront_tests() -> List[Dict[str, Any]]:
    """Capture round-trip spread -> upfront -> spread tests."""
    results = []
    holiday_file = create_holiday_file()

    try:
        # Test parameters
        spreads_bps = [50, 100, 200, 500, 775, 1000]
        recovery_rates = [0.30, 0.40, 0.50]
        coupons = [100.0, 500.0]

        # Trade setup
        trade_date = '10/10/2022'
        settle_date = '13/10/2022'
        accrual_start_date = '20/09/2022'
        maturity_date = '20/12/2027'
        notional = 1.0
        is_buy = 0

        swap_floating_dcc = 'ACT/360'
        swap_fixed_dcc = 'ACT/360'
        swap_fixed_freq = '1Y'
        swap_floating_freq = '1Y'
        is_rofr = 1

        test_combinations = list(product(recovery_rates, coupons, spreads_bps))
        total = len(test_combinations)

        print(f"Running {total} spread_from_upfront round-trip tests...")

        for idx, (rr, coupon, spread_bps) in enumerate(test_combinations):
            original_spread = spread_bps / 10000.0

            test_name = f"roundtrip_rr{int(rr*100)}_coupon{int(coupon)}_spread{spread_bps}"

            try:
                # Step 1: Compute upfront from spread
                f1 = compute_isda_upfront(
                    trade_date, maturity_date, accrual_start_date, settle_date,
                    rr, coupon, notional, is_buy,
                    HIGH_SWAP_RATES, HIGH_SWAP_TENORS,
                    original_spread, is_rofr, holiday_file,
                    swap_floating_dcc, swap_fixed_dcc,
                    swap_fixed_freq, swap_floating_freq, 0
                )

                dirty_upfront, clean_upfront, accrued, _, _ = f1

                # Step 2: Compute spread back from clean upfront
                f2_clean = calculate_spread_from_upfront_charge(
                    trade_date, maturity_date, accrual_start_date, settle_date,
                    rr, coupon, notional, is_buy,
                    HIGH_SWAP_RATES, HIGH_SWAP_TENORS,
                    clean_upfront, is_rofr, 1,  # is_clean=1
                    holiday_file,
                    swap_floating_dcc, swap_fixed_dcc,
                    swap_fixed_freq, swap_floating_freq, 0
                )
                spread_from_clean, _, _ = f2_clean

                # Step 3: Compute spread back from dirty upfront
                f2_dirty = calculate_spread_from_upfront_charge(
                    trade_date, maturity_date, accrual_start_date, settle_date,
                    rr, coupon, notional, is_buy,
                    HIGH_SWAP_RATES, HIGH_SWAP_TENORS,
                    dirty_upfront, is_rofr, 0,  # is_clean=0
                    holiday_file,
                    swap_floating_dcc, swap_fixed_dcc,
                    swap_fixed_freq, swap_floating_freq, 0
                )
                spread_from_dirty, _, _ = f2_dirty

                # Calculate round-trip errors
                error_clean = abs(spread_from_clean - original_spread)
                error_dirty = abs(spread_from_dirty - original_spread)

                results.append({
                    'test_name': test_name,
                    'inputs': {
                        'trade_date': trade_date,
                        'maturity_date': maturity_date,
                        'recovery_rate': rr,
                        'coupon': coupon,
                        'original_spread_bps': spread_bps,
                        'market_data': 'HIGH',
                    },
                    'outputs': {
                        'dirty_upfront': dirty_upfront,
                        'clean_upfront': clean_upfront,
                        'accrued_interest': accrued,
                        'spread_from_clean': spread_from_clean,
                        'spread_from_dirty': spread_from_dirty,
                        'roundtrip_error_clean': error_clean,
                        'roundtrip_error_dirty': error_dirty,
                    },
                    'status': 'success'
                })

            except Exception as e:
                results.append({
                    'test_name': test_name,
                    'inputs': {'recovery_rate': rr, 'coupon': coupon, 'spread_bps': spread_bps},
                    'status': 'error',
                    'error': str(e)
                })

        print(f"  Completed all {total} tests")

    finally:
        cleanup_holiday_file(holiday_file)

    return results


def sanity_check_results(results: Dict[str, List[Dict]]) -> Dict[str, Any]:
    """Perform sanity checks on captured results."""
    checks = {
        'sign_conventions': [],
        'symmetry': [],
        'roundtrip': [],
        'summary': {}
    }

    # Check cds_all_in_one sign conventions
    for r in results.get('cds_all_in_one', []):
        if r['status'] != 'success':
            continue

        is_buy = r['inputs']['is_buy_protection']
        pv_dirty = r['outputs']['pv_dirty']
        cs01 = r['outputs']['cs01']
        dv01 = r['outputs']['dv01']

        # Buy protection: expect negative PV, positive CS01
        # Sell protection: expect positive PV, negative CS01
        if is_buy == 1:
            pv_sign_ok = pv_dirty < 0
            cs01_sign_ok = cs01 > 0
        else:
            pv_sign_ok = pv_dirty > 0
            cs01_sign_ok = cs01 < 0

        if not (pv_sign_ok and cs01_sign_ok):
            checks['sign_conventions'].append({
                'test': r['test_name'],
                'issue': f"Sign mismatch: is_buy={is_buy}, pv_dirty={pv_dirty:.6f}, cs01={cs01:.6f}",
                'pv_sign_ok': pv_sign_ok,
                'cs01_sign_ok': cs01_sign_ok
            })

    # Check roundtrip errors
    for r in results.get('spread_from_upfront', []):
        if r['status'] != 'success':
            continue

        error_clean = r['outputs']['roundtrip_error_clean']
        error_dirty = r['outputs']['roundtrip_error_dirty']

        if error_clean > 1e-6 or error_dirty > 1e-6:
            checks['roundtrip'].append({
                'test': r['test_name'],
                'error_clean': error_clean,
                'error_dirty': error_dirty,
            })

    # Summary statistics
    total_tests = sum(len(v) for v in results.values())
    successful = sum(1 for v in results.values() for r in v if r['status'] == 'success')
    failed = total_tests - successful

    checks['summary'] = {
        'total_tests': total_tests,
        'successful': successful,
        'failed': failed,
        'sign_convention_issues': len(checks['sign_conventions']),
        'roundtrip_issues': len(checks['roundtrip']),
    }

    return checks


def main():
    """Main function to capture all baseline results."""
    print("=" * 70)
    print("CDS Pricer Baseline Capture")
    print("=" * 70)
    print()

    all_results = {}

    # Capture cds_all_in_one tests
    print("\n1. Capturing cds_all_in_one tests...")
    all_results['cds_all_in_one'] = capture_cds_all_in_one_tests()

    # Capture upfront tests
    print("\n2. Capturing compute_isda_upfront tests...")
    all_results['upfront'] = capture_upfront_tests()

    # Capture round-trip tests
    print("\n3. Capturing spread_from_upfront round-trip tests...")
    all_results['spread_from_upfront'] = capture_spread_from_upfront_tests()

    # Sanity checks
    print("\n4. Running sanity checks...")
    sanity = sanity_check_results(all_results)
    all_results['sanity_checks'] = sanity

    # Print summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"Total tests: {sanity['summary']['total_tests']}")
    print(f"Successful:  {sanity['summary']['successful']}")
    print(f"Failed:      {sanity['summary']['failed']}")
    print(f"Sign convention issues: {sanity['summary']['sign_convention_issues']}")
    print(f"Round-trip issues: {sanity['summary']['roundtrip_issues']}")

    if sanity['sign_conventions']:
        print("\nSign convention issues:")
        for issue in sanity['sign_conventions'][:5]:
            print(f"  - {issue['test']}: {issue['issue']}")
        if len(sanity['sign_conventions']) > 5:
            print(f"  ... and {len(sanity['sign_conventions']) - 5} more")

    if sanity['roundtrip']:
        print("\nRound-trip issues (error > 1e-6):")
        for issue in sanity['roundtrip'][:5]:
            print(f"  - {issue['test']}: clean={issue['error_clean']:.2e}, dirty={issue['error_dirty']:.2e}")

    # Save results
    output_file = 'baseline_results.json'
    with open(output_file, 'w') as f:
        json.dump(all_results, f, indent=2)

    print(f"\nResults saved to: {output_file}")
    print("=" * 70)

    return all_results


if __name__ == '__main__':
    main()
