#!/usr/bin/env python3
"""
Upfront and Spread Calculations
===============================

This example demonstrates:
1. Computing upfront payments from par spreads
2. Computing par spreads from upfront charges
3. Round-trip validation (spread -> upfront -> spread)

In the standard CDS market:
- Contracts trade with fixed coupons (100 or 500 bps)
- The difference between par spread and coupon is settled upfront
"""

from isda import CDSPricer

# =============================================================================
# Setup
# =============================================================================

trade_date = '08/31/2022'

swap_rates = [
    0.002979, 0.006419, 0.01165, 0.017617, 0.024417, 0.026917,
    0.028, 0.028583, 0.029083, 0.02945, 0.029917, 0.030167,
    0.030417, 0.031417, 0.0305, 0.028917,
]

swap_tenors = [
    '1M', '3M', '6M', '1Y', '2Y', '3Y', '4Y', '5Y',
    '6Y', '7Y', '8Y', '9Y', '10Y', '15Y', '20Y', '30Y',
]

pricer = CDSPricer(
    trade_date=trade_date,
    swap_rates=swap_rates,
    swap_tenors=swap_tenors,
)

print('=' * 70)
print('ISDA CDS Standard Model - Upfront Calculations')
print('=' * 70)
print()

# =============================================================================
# Compute Upfront from Spread
# =============================================================================

print('-' * 70)
print('Computing Upfront from Par Spread')
print('-' * 70)
print()

maturity = '12/20/2026'
notional = 10_000_000
recovery = 0.40

# Test different spread levels
spreads_bps = [50, 100, 200, 500, 1000]

print('With 100 bps Fixed Coupon:')
print()
print(f"{'Spread (bps)':<14} {'Dirty Upfront':>16} {'Clean Upfront':>16} {'Accrued':>14}")
print('-' * 64)

for spread_bps in spreads_bps:
    spread = spread_bps / 10000  # Convert bps to decimal

    dirty, clean, accrued = pricer.compute_upfront(
        maturity_date=maturity,
        par_spread=spread,
        coupon_rate=100,
        notional=notional,
        recovery_rate=recovery,
    )

    print(f'{spread_bps:>8}       ${dirty:>14,.2f} ${clean:>14,.2f} ${accrued:>12,.2f}')

print()
print('Interpretation:')
print('  - Spread < Coupon: Protection buyer RECEIVES upfront (positive)')
print('  - Spread > Coupon: Protection buyer PAYS upfront (negative)')
print()

# =============================================================================
# Compare 100 vs 500 bps Coupons
# =============================================================================

print('-' * 70)
print('100 bps vs 500 bps Coupon Comparison')
print('-' * 70)
print()

spread = 0.0200  # 200 bps

dirty_100, clean_100, _ = pricer.compute_upfront(
    maturity_date=maturity,
    par_spread=spread,
    coupon_rate=100,
    notional=notional,
    recovery_rate=recovery,
)

dirty_500, clean_500, _ = pricer.compute_upfront(
    maturity_date=maturity,
    par_spread=spread,
    coupon_rate=500,
    notional=notional,
    recovery_rate=recovery,
)

print(f'Par Spread: 200 bps, Notional: ${notional:,.0f}')
print()
print(f"{'Coupon':<12} {'Dirty Upfront':>16} {'Clean Upfront':>16}")
print('-' * 46)
print(f"{'100 bps':<12} ${dirty_100:>14,.2f} ${clean_100:>14,.2f}")
print(f"{'500 bps':<12} ${dirty_500:>14,.2f} ${clean_500:>14,.2f}")
print()
print('Note: With 200 bps spread:')
print('  - 100 bps coupon: Buyer pays (spread > coupon)')
print('  - 500 bps coupon: Buyer receives (spread < coupon)')
print()

# =============================================================================
# Compute Spread from Upfront
# =============================================================================

print('-' * 70)
print('Computing Spread from Upfront Charge')
print('-' * 70)
print()

# Start with known upfronts and recover the spread
# Note: compute_spread_from_upfront expects upfront as fraction of notional
# Negative = buyer pays, Positive = buyer receives
test_upfronts_pct = [-0.05, -0.02, -0.01, 0, 0.01, 0.02]

print(f'Coupon: 100 bps, Notional: ${notional:,.0f}')
print()
print(f"{'Dirty Upfront':>14} {'Implied Spread (bps)':>22}")
print('-' * 40)

for upfront_pct in test_upfronts_pct:
    upfront_dollars = upfront_pct * notional
    spread = pricer.compute_spread_from_upfront(
        maturity_date=maturity,
        upfront_charge=upfront_pct,  # As fraction of notional
        coupon_rate=100,
        notional=notional,
        recovery_rate=recovery,
        is_clean=False,  # Using dirty upfront
    )
    print(f'${upfront_dollars:>12,.0f}   {spread * 10000:>18.2f}')

print()

# =============================================================================
# Round-Trip Validation
# =============================================================================

print('-' * 70)
print('Round-Trip Validation: Spread -> Upfront -> Spread')
print('-' * 70)
print()

original_spreads = [0.0050, 0.0100, 0.0200, 0.0500, 0.0775]

print(f"{'Original (bps)':<16} {'Upfront ($)':>14} {'Recovered (bps)':>18} {'Error (bps)':<12}")
print('-' * 64)

for original_spread in original_spreads:
    # Step 1: Compute upfront from spread (returns dollar amount)
    dirty_upfront, _, _ = pricer.compute_upfront(
        maturity_date=maturity,
        par_spread=original_spread,
        coupon_rate=100,
        notional=notional,
        recovery_rate=recovery,
    )

    # Step 2: Recover spread from upfront (expects fraction of notional)
    upfront_pct = dirty_upfront / notional
    recovered_spread = pricer.compute_spread_from_upfront(
        maturity_date=maturity,
        upfront_charge=upfront_pct,
        coupon_rate=100,
        notional=notional,
        recovery_rate=recovery,
        is_clean=False,
    )

    error = (recovered_spread - original_spread) * 10000

    print(f'{original_spread * 10000:>10.0f}       ${dirty_upfront:>12,.0f}   {recovered_spread * 10000:>14.4f}     {error:>8.6f}')

print()
print('The round-trip error should be negligible (< 0.001 bps)')
print()

# =============================================================================
# Recovery Rate Impact
# =============================================================================

print('-' * 70)
print('Impact of Recovery Rate on Upfront')
print('-' * 70)
print()

spread = 0.0300  # 300 bps
recovery_rates = [0.20, 0.30, 0.40, 0.50, 0.60]

print('Spread: 300 bps, Coupon: 100 bps')
print()
print(f"{'Recovery Rate':<14} {'Clean Upfront':>16} {'% of Notional':>15}")
print('-' * 48)

for rr in recovery_rates:
    _, clean_upfront, _ = pricer.compute_upfront(
        maturity_date=maturity,
        par_spread=spread,
        coupon_rate=100,
        notional=notional,
        recovery_rate=rr,
    )
    pct = clean_upfront / notional * 100
    print(f'{rr:>8.0%}       ${clean_upfront:>14,.2f}   {pct:>12.2f}%')

print()
print('Higher recovery = lower expected loss = smaller upfront for same spread')
print()

print('=' * 70)
print('Example Complete')
print('=' * 70)
