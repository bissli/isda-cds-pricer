#!/usr/bin/env python3
"""
Basic CDS Pricing Example
=========================

This example demonstrates the fundamental use of the ISDA CDS pricer
to price a single-name Credit Default Swap.

A CDS is a financial derivative that provides protection against
credit events (default) of a reference entity.
"""

from isda import CDSPricer

# =============================================================================
# Market Data Setup
# =============================================================================

# Trade date - the date on which we're pricing
trade_date = '08/31/2022'

# Interest rate swap curve (used for discounting)
# These are par swap rates for various tenors
swap_rates = [
    0.002979,   # 1M
    0.006419,   # 3M
    0.01165,    # 6M
    0.017617,   # 1Y
    0.024417,   # 2Y
    0.026917,   # 3Y
    0.028,      # 4Y
    0.028583,   # 5Y
    0.029083,   # 6Y
    0.02945,    # 7Y
    0.029917,   # 8Y
    0.030167,   # 9Y
    0.030417,   # 10Y
    0.031417,   # 15Y
    0.0305,     # 20Y
    0.028917,   # 30Y
]

swap_tenors = [
    '1M', '3M', '6M', '1Y', '2Y', '3Y', '4Y', '5Y',
    '6Y', '7Y', '8Y', '9Y', '10Y', '15Y', '20Y', '30Y',
]

# =============================================================================
# Create the Pricer
# =============================================================================

print('=' * 70)
print('ISDA CDS Standard Model - Basic Pricing Example')
print('=' * 70)
print()

pricer = CDSPricer(
    trade_date=trade_date,
    swap_rates=swap_rates,
    swap_tenors=swap_tenors,
)

print(f'Trade Date:     {trade_date}')
print(f'Swap Curve:     {len(swap_rates)} points')
print()

# =============================================================================
# Price a CDS
# =============================================================================

print('-' * 70)
print('Pricing a 5-Year CDS')
print('-' * 70)
print()

# CDS contract parameters
maturity_date = '12/20/2026'
par_spread = 0.0065        # 65 basis points (market spread)
coupon_rate = 100          # 100 bps (standard coupon)
notional = 10_000_000      # $10 million
recovery_rate = 0.40       # 40% recovery assumption

result = pricer.price_cds(
    maturity_date=maturity_date,
    par_spread=par_spread,
    coupon_rate=coupon_rate,
    notional=notional,
    recovery_rate=recovery_rate,
    is_buy_protection=True,
)

print('Contract Details:')
print(f'  Maturity:        {maturity_date}')
print(f'  Par Spread:      {par_spread * 10000:.0f} bps')
print(f'  Coupon:          {coupon_rate} bps')
print(f'  Notional:        ${notional:,.0f}')
print(f'  Recovery Rate:   {recovery_rate:.0%}')
print('  Position:        Buy Protection')
print()

print('Valuation Results:')
print(f'  PV (Dirty):      ${result.pv_dirty:>15,.2f}')
print(f'  PV (Clean):      ${result.pv_clean:>15,.2f}')
print(f'  Accrued Int:     ${result.accrued_interest:>15,.2f}')
print()

print('Risk Metrics:')
cs01_per_mm = result.cs01 / notional * 1_000_000
dv01_per_mm = result.dv01 / notional * 1_000_000
print(f'  CS01:            ${result.cs01:>15,.2f} (${cs01_per_mm:,.2f} per MM)')
print(f'  DV01:            ${result.dv01:>15,.2f} (${dv01_per_mm:,.2f} per MM)')
print()

# =============================================================================
# Buy vs Sell Protection
# =============================================================================

print('-' * 70)
print('Buy vs Sell Protection Comparison')
print('-' * 70)
print()

buy_result = pricer.price_cds(
    maturity_date=maturity_date,
    par_spread=par_spread,
    coupon_rate=coupon_rate,
    notional=notional,
    recovery_rate=recovery_rate,
    is_buy_protection=True,
)

sell_result = pricer.price_cds(
    maturity_date=maturity_date,
    par_spread=par_spread,
    coupon_rate=coupon_rate,
    notional=notional,
    recovery_rate=recovery_rate,
    is_buy_protection=False,
)

print(f"{'Metric':<20} {'Buy Protection':>18} {'Sell Protection':>18}")
print('-' * 58)
print(f"{'PV (Dirty)':<20} ${buy_result.pv_dirty:>15,.2f}  ${sell_result.pv_dirty:>15,.2f}")
print(f"{'PV (Clean)':<20} ${buy_result.pv_clean:>15,.2f}  ${sell_result.pv_clean:>15,.2f}")
buy_cs01_mm = buy_result.cs01 / notional * 1_000_000
sell_cs01_mm = sell_result.cs01 / notional * 1_000_000
print(f"{'CS01 (per MM)':<20} ${buy_cs01_mm:>15,.2f}  ${sell_cs01_mm:>15,.2f}")
print()
print('Note: Buy/Sell PVs are symmetric (opposite signs)')
print()

# =============================================================================
# Different Maturities
# =============================================================================

print('-' * 70)
print('CDS Pricing Across Maturities')
print('-' * 70)
print()

maturities = [
    ('12/20/2023', '1Y'),
    ('12/20/2024', '2Y'),
    ('12/20/2025', '3Y'),
    ('12/20/2026', '4Y'),
    ('12/20/2027', '5Y'),
]

print(f"{'Maturity':<12} {'Tenor':<6} {'PV Dirty':>14} {'PV Clean':>14} {'CS01/MM':>12}")
print('-' * 62)

for mat_date, tenor in maturities:
    r = pricer.price_cds(
        maturity_date=mat_date,
        par_spread=par_spread,
        coupon_rate=coupon_rate,
        notional=notional,
        recovery_rate=recovery_rate,
        is_buy_protection=True,
    )
    cs01_mm = r.cs01 / notional * 1_000_000
    print(f'{mat_date:<12} {tenor:<6} ${r.pv_dirty:>12,.2f} ${r.pv_clean:>12,.2f} ${cs01_mm:>10,.2f}')

print()
print('=' * 70)
print('Example Complete')
print('=' * 70)
