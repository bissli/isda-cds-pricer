#!/usr/bin/env python3
"""
Curve Building and Analysis
===========================

This example demonstrates:
1. Building zero curves from swap rates
2. Creating credit curves from CDS spreads
3. Extracting discount factors and survival probabilities
4. Forward rate analysis

Understanding curves is fundamental to CDS pricing.
"""


from isda import CreditCurve, ZeroCurve
from isda import bootstrap_credit_curve, bootstrap_zero_curve, parse_date

print('=' * 70)
print('ISDA CDS Standard Model - Curve Building')
print('=' * 70)
print()

# =============================================================================
# Building a Zero Curve
# =============================================================================

print('-' * 70)
print('Building Zero Curve from Swap Rates')
print('-' * 70)
print()

trade_date = parse_date('08/31/2022')

# Market data: swap rates and tenors
swap_rates = [
    0.002979, 0.006419, 0.01165, 0.017617, 0.024417, 0.026917,
    0.028, 0.028583, 0.029083, 0.02945, 0.029917, 0.030167,
    0.030417, 0.031417, 0.0305, 0.028917,
]

swap_tenors = [
    '1M', '3M', '6M', '1Y', '2Y', '3Y', '4Y', '5Y',
    '6Y', '7Y', '8Y', '9Y', '10Y', '15Y', '20Y', '30Y',
]

# Bootstrap zero curve
zero_curve = bootstrap_zero_curve(
    base_date=trade_date,
    swap_rates=swap_rates,
    swap_tenors=swap_tenors,
)

print('Input Swap Rates:')
print(f"{'Tenor':<8} {'Swap Rate':>12}")
print('-' * 22)
for tenor, rate in zip(swap_tenors[:8], swap_rates[:8]):
    print(f'{tenor:<8} {rate*100:>10.4f}%')
print('...')
print()

# =============================================================================
# Discount Factors
# =============================================================================

print('-' * 70)
print('Discount Factors from Zero Curve')
print('-' * 70)
print()

print(f"{'Year Frac':<12} {'Discount Factor':>16} {'Zero Rate':>14}")
print('-' * 46)

time_points = [0.25, 0.5, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0]

for t in time_points:
    df = zero_curve.discount_factor(t)
    # Implied zero rate: -ln(df) / t
    zero_rate = -1 * (df ** (-1/t) - 1) if t > 0 else 0
    zero_rate_cont = -1 * (1/t) * (df - 1) / df if t > 0 and df > 0 else 0

    print(f'{t:<12.2f} {df:>16.8f}   {zero_curve.rate(t)*100:>10.4f}%')

print()
print('Note: Discount factors decrease over time due to time value of money')
print()

# =============================================================================
# Forward Rates
# =============================================================================

print('-' * 70)
print('Forward Rates')
print('-' * 70)
print()

print(f"{'Period':<16} {'Forward Rate':>14}")
print('-' * 34)

periods = [(0, 1), (1, 2), (2, 3), (3, 4), (4, 5), (5, 7), (7, 10)]

for t1, t2 in periods:
    fwd = zero_curve.forward_rate(t1, t2)
    print(f"{t1}Y - {t2}Y{' ' * (8 - len(str(t1)) - len(str(t2)))} {fwd*100:>12.4f}%")

print()
print('Forward rates represent implied future spot rates')
print()

# =============================================================================
# Building a Credit Curve
# =============================================================================

print('-' * 70)
print('Building Credit Curve from CDS Spreads')
print('-' * 70)
print()

# CDS market spreads for different tenors
cds_spreads = [0.0080, 0.0120, 0.0150, 0.0170, 0.0185]  # 80, 120, 150, 170, 185 bps
cds_tenors = ['1Y', '2Y', '3Y', '5Y', '7Y']
recovery_rate = 0.40

credit_curve = bootstrap_credit_curve(
    base_date=trade_date,
    par_spreads=cds_spreads,
    spread_tenors=cds_tenors,
    zero_curve=zero_curve,
    recovery_rate=recovery_rate,
)

print('Input CDS Spreads:')
print(f"{'Tenor':<8} {'Spread (bps)':>14}")
print('-' * 24)
for tenor, spread in zip(cds_tenors, cds_spreads):
    print(f'{tenor:<8} {spread*10000:>12.0f}')

print()
print(f'Recovery Rate: {recovery_rate:.0%}')
print()

# =============================================================================
# Survival Probabilities
# =============================================================================

print('-' * 70)
print('Survival and Default Probabilities')
print('-' * 70)
print()

print(f"{'Year':<8} {'Survival Prob':>16} {'Cumulative Default':>20}")
print('-' * 48)

years = [0.5, 1.0, 2.0, 3.0, 5.0, 7.0, 10.0]

for y in years:
    surv = credit_curve.survival_probability(y)
    default = credit_curve.default_probability(y)
    print(f'{y:<8.1f} {surv*100:>14.4f}%    {default*100:>16.4f}%')

print()
print('Survival probability = 1 - Cumulative default probability')
print()

# =============================================================================
# Hazard Rates
# =============================================================================

print('-' * 70)
print('Hazard Rates (Instantaneous Default Intensity)')
print('-' * 70)
print()

print(f"{'Period':<16} {'Hazard Rate':>14} {'Annual Prob':>14}")
print('-' * 48)

# Calculate implied hazard rates between curve points
prev_t = 0
prev_surv = 1.0

for t in [1.0, 2.0, 3.0, 5.0, 7.0]:
    surv = credit_curve.survival_probability(t)
    if prev_surv > 0 and surv > 0:
        import math
        hazard = -math.log(surv / prev_surv) / (t - prev_t)
        annual_prob = 1 - math.exp(-hazard)
        print(f"{prev_t:.0f}Y - {t:.0f}Y{' ' * (8 - len(str(int(prev_t))) - len(str(int(t))))} {hazard*10000:>12.2f}bp   {annual_prob*100:>12.4f}%")
    prev_t = t
    prev_surv = surv

print()
print('Hazard rate represents instantaneous default probability per unit time')
print()

# =============================================================================
# Create Curves Directly
# =============================================================================

print('-' * 70)
print('Creating Curves Directly (Without Bootstrapping)')
print('-' * 70)
print()

# You can create curves directly from rates and times
times = [1.0, 2.0, 3.0, 5.0, 7.0, 10.0]
zero_rates = [0.025, 0.028, 0.029, 0.030, 0.031, 0.032]
hazard_rates = [0.015, 0.018, 0.020, 0.022, 0.024, 0.025]

direct_zero = ZeroCurve(base_date=trade_date, times=times, rates=zero_rates)
direct_credit = CreditCurve(base_date=trade_date, times=times, hazard_rates=hazard_rates)

print('Zero Curve (direct construction):')
print(f'  DF at 5Y: {direct_zero.discount_factor(5.0):.6f}')
print(f'  Rate at 5Y: {direct_zero.rate(5.0)*100:.4f}%')
print()

print('Credit Curve (direct construction):')
print(f'  Survival at 5Y: {direct_credit.survival_probability(5.0)*100:.4f}%')
print(f'  Default at 5Y: {direct_credit.default_probability(5.0)*100:.4f}%')
print()

# =============================================================================
# Curve Comparison
# =============================================================================

print('-' * 70)
print('Impact of Credit Quality on Survival')
print('-' * 70)
print()

# Create credit curves for different spread levels
spread_levels = {
    'Investment Grade (50bp)': 0.0050,
    'BBB (150bp)': 0.0150,
    'High Yield (500bp)': 0.0500,
    'Distressed (1500bp)': 0.1500,
}

print(f"{'Credit Quality':<26} {'1Y Surv':>10} {'3Y Surv':>10} {'5Y Surv':>10}")
print('-' * 60)

for name, spread in spread_levels.items():
    # Simple approximation: constant hazard rate = spread / (1 - recovery)
    hazard = spread / (1 - recovery_rate)
    import math

    surv_1y = math.exp(-hazard * 1)
    surv_3y = math.exp(-hazard * 3)
    surv_5y = math.exp(-hazard * 5)

    print(f'{name:<26} {surv_1y*100:>8.2f}% {surv_3y*100:>8.2f}% {surv_5y*100:>8.2f}%')

print()
print('Higher spreads imply lower survival probabilities')
print()

print('=' * 70)
print('Example Complete')
print('=' * 70)
