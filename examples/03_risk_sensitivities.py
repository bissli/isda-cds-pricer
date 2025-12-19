#!/usr/bin/env python3
"""
Risk Sensitivities (CS01 and DV01)
==================================

This example demonstrates how to calculate and interpret
key risk metrics for CDS positions:

- CS01: Credit Spread 01 - PV change for 1bp spread increase
- DV01: Dollar Value 01 - PV change for 1bp rate increase

These metrics are essential for:
- Hedging credit and interest rate risk
- Risk limit monitoring
- P&L attribution
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
print('ISDA CDS Standard Model - Risk Sensitivities')
print('=' * 70)
print()

# =============================================================================
# CS01 - Credit Spread Sensitivity
# =============================================================================

print('-' * 70)
print('CS01: Credit Spread Sensitivity')
print('-' * 70)
print()

maturity = '12/20/2026'
notional = 10_000_000
recovery = 0.40
coupon = 100

# Different spread levels
spreads_bps = [50, 100, 200, 500, 1000]

print('CS01 measures P&L for a 1bp increase in credit spread')
print()
print(f"{'Spread (bps)':<14} {'CS01 ($)':>14} {'CS01/MM':>14} {'Direction':>12}")
print('-' * 58)

for spread_bps in spreads_bps:
    spread = spread_bps / 10000

    buy_result = pricer.price_cds(
        maturity_date=maturity,
        par_spread=spread,
        coupon_rate=coupon,
        notional=notional,
        recovery_rate=recovery,
        is_buy_protection=True,
    )

    # CS01 is already in dollars for the position
    cs01_dollar = buy_result.cs01
    # CS01 per million notional = cs01 / notional * 1,000,000
    cs01_per_mm = buy_result.cs01 / notional * 1_000_000

    direction = 'Gains' if buy_result.cs01 > 0 else 'Loses'

    print(f'{spread_bps:>8}       ${cs01_dollar:>12,.2f} ${cs01_per_mm:>12,.2f}   {direction}')

print()
print('Protection Buyer: Gains when spreads widen (positive CS01)')
print('Protection Seller: Loses when spreads widen (negative CS01)')
print()

# =============================================================================
# DV01 - Interest Rate Sensitivity
# =============================================================================

print('-' * 70)
print('DV01: Interest Rate Sensitivity')
print('-' * 70)
print()

spread = 0.0200  # 200 bps

print('DV01 measures P&L for a 1bp parallel shift in interest rates')
print()
print(f"{'Position':<20} {'DV01 ($)':>14} {'DV01/MM':>14}")
print('-' * 50)

buy_result = pricer.price_cds(
    maturity_date=maturity,
    par_spread=spread,
    coupon_rate=coupon,
    notional=notional,
    recovery_rate=recovery,
    is_buy_protection=True,
)

sell_result = pricer.price_cds(
    maturity_date=maturity,
    par_spread=spread,
    coupon_rate=coupon,
    notional=notional,
    recovery_rate=recovery,
    is_buy_protection=False,
)

buy_dv01_mm = buy_result.dv01 / notional * 1_000_000
sell_dv01_mm = sell_result.dv01 / notional * 1_000_000
print(f"{'Buy Protection':<20} ${buy_result.dv01:>12,.2f} ${buy_dv01_mm:>12,.2f}")
print(f"{'Sell Protection':<20} ${sell_result.dv01:>12,.2f} ${sell_dv01_mm:>12,.2f}")
print()
print('Note: CDS have relatively low interest rate sensitivity')
print('compared to equivalent-maturity bonds.')
print()

# =============================================================================
# Sensitivity Across Maturities
# =============================================================================

print('-' * 70)
print('Risk Sensitivities Across Maturities')
print('-' * 70)
print()

maturities = [
    ('12/20/2023', '1Y'),
    ('12/20/2024', '2Y'),
    ('12/20/2025', '3Y'),
    ('12/20/2026', '4Y'),
    ('12/20/2027', '5Y'),
    ('12/20/2029', '7Y'),
    ('12/20/2032', '10Y'),
]

print(f'Spread: 200 bps, Coupon: 100 bps, Notional: ${notional:,.0f}')
print()
print(f"{'Tenor':<8} {'CS01 ($)':>14} {'DV01 ($)':>14} {'CS01/DV01':>12}")
print('-' * 52)

for mat_date, tenor in maturities:
    result = pricer.price_cds(
        maturity_date=mat_date,
        par_spread=spread,
        coupon_rate=coupon,
        notional=notional,
        recovery_rate=recovery,
        is_buy_protection=True,
    )

    # CS01 and DV01 are already in dollars for the position
    cs01_dollar = result.cs01
    dv01_dollar = result.dv01
    ratio = cs01_dollar / abs(dv01_dollar) if dv01_dollar != 0 else 0

    print(f'{tenor:<8} ${cs01_dollar:>12,.2f} ${dv01_dollar:>12,.2f}   {ratio:>10.1f}x')

print()
print('CS01 increases approximately linearly with maturity')
print('The CS01/DV01 ratio indicates credit vs rate risk profile')
print()

# =============================================================================
# Hedging Example
# =============================================================================

print('-' * 70)
print('Hedging Example: Portfolio CS01')
print('-' * 70)
print()

# A portfolio of CDS positions
portfolio = [
    {'maturity': '12/20/2024', 'spread': 0.0150, 'notional': 5_000_000, 'is_buy': True, 'name': 'Corp A'},
    {'maturity': '12/20/2025', 'spread': 0.0300, 'notional': 8_000_000, 'is_buy': True, 'name': 'Corp B'},
    {'maturity': '12/20/2026', 'spread': 0.0200, 'notional': 3_000_000, 'is_buy': False, 'name': 'Corp C'},
]

print(f"{'Name':<10} {'Direction':<10} {'Notional':>14} {'Spread':>10} {'CS01 ($)':>14}")
print('-' * 64)

total_cs01 = 0

for pos in portfolio:
    result = pricer.price_cds(
        maturity_date=pos['maturity'],
        par_spread=pos['spread'],
        coupon_rate=coupon,
        notional=pos['notional'],
        recovery_rate=recovery,
        is_buy_protection=pos['is_buy'],
    )

    # CS01 is already in dollars for the position's notional
    cs01_dollar = result.cs01
    total_cs01 += cs01_dollar
    direction = 'Buy Prot' if pos['is_buy'] else 'Sell Prot'

    print(f"{pos['name']:<10} {direction:<10} ${pos['notional']:>12,.0f}   {pos['spread']*10000:>6.0f}bp ${cs01_dollar:>12,.2f}")

print('-' * 64)
print(f"{'Portfolio Total':<36} {' ':>10} ${total_cs01:>12,.2f}")
print()
print(f'Net Portfolio CS01: ${total_cs01:,.2f}')
print()
if total_cs01 > 0:
    print('Portfolio is NET LONG credit risk (benefits from spread tightening)')
else:
    print('Portfolio is NET SHORT credit risk (benefits from spread widening)')
print()

# =============================================================================
# P&L Estimation
# =============================================================================

print('-' * 70)
print('P&L Estimation from Spread Move')
print('-' * 70)
print()

# Single position
result = pricer.price_cds(
    maturity_date='12/20/2026',
    par_spread=0.0200,
    coupon_rate=100,
    notional=10_000_000,
    recovery_rate=0.40,
    is_buy_protection=True,
)

# CS01 is already in dollars for the $10MM notional
cs01 = result.cs01

spread_moves = [-50, -25, -10, 10, 25, 50, 100]

print('Starting Position: Buy Protection, 200 bps, $10MM notional')
print(f'CS01: ${cs01:,.2f}')
print()
print(f"{'Spread Move (bps)':<20} {'Est. P&L':>14} {'Interpretation':>20}")
print('-' * 58)

for move in spread_moves:
    pnl = cs01 * move
    interp = 'Profit' if pnl > 0 else 'Loss'
    direction = 'widening' if move > 0 else 'tightening'
    print(f'{move:>+10} ({direction:>10}) ${pnl:>12,.2f}       {interp}')

print()
print('Note: This is a linear approximation. For large moves,')
print('convexity effects become significant.')
print()

print('=' * 70)
print('Example Complete')
print('=' * 70)
