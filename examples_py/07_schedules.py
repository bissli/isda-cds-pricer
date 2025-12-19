#!/usr/bin/env python3
"""
CDS Payment Schedules
=====================

This example demonstrates how to generate and analyze CDS payment
schedules, including:

1. Quarterly premium payment schedules
2. Accrual period calculations
3. Stub period handling
4. Accrued interest calculations

Understanding schedules is key to pricing the fee leg of a CDS.
"""

from datetime import date

from isda import CDSSchedule, PaymentFrequency
from isda import generate_cds_schedule, parse_date
from isda.schedule import calculate_accrued_interest, get_accrued_days


def fmt(d) -> str:
    """Format date as MM/DD/YYYY."""
    return f'{d.month:02d}/{d.day:02d}/{d.year}'


print('=' * 70)
print('ISDA CDS Standard Model - Payment Schedules')
print('=' * 70)
print()

# =============================================================================
# Basic Schedule Generation
# =============================================================================

print('-' * 70)
print('Basic Quarterly Schedule')
print('-' * 70)
print()

accrual_start = parse_date('2022-09-21')
maturity_date = parse_date('2024-12-20')

schedule = CDSSchedule(
    accrual_start=accrual_start,
    maturity=maturity_date,
    frequency=PaymentFrequency.QUARTERLY,
)

print(f'Accrual Start:  {fmt(accrual_start)}')
print(f'Maturity Date:  {fmt(maturity_date)}')
print('Frequency:      Quarterly')
print(f'Number of Periods: {len(schedule)}')
print()

print(f"{'#':<4} {'Accrual Start':>14} {'Accrual End':>14} {'Payment':>14} {'Year Frac':>12}")
print('-' * 64)

for i, period in enumerate(schedule, 1):
    print(f'{i:<4} {fmt(period.accrual_start):>14} {fmt(period.accrual_end):>14} '
          f'{fmt(period.payment_date):>14} {period.year_fraction:>12.6f}')

print()

# =============================================================================
# Schedule with Stub Period
# =============================================================================

print('-' * 70)
print('Schedule with Front Stub')
print('-' * 70)
print()

# Start date that doesn't align with IMM cycle
accrual_start = parse_date('2022-08-31')  # Not an IMM date
maturity_date = parse_date('2024-12-20')   # IMM date

schedule = generate_cds_schedule(
    accrual_start=accrual_start,
    maturity=maturity_date,
    frequency=PaymentFrequency.QUARTERLY,
)

print(f'Accrual Start:  {fmt(accrual_start)} (non-IMM)')
print(f'Maturity Date:  {fmt(maturity_date)} (IMM)')
print()

print(f"{'#':<4} {'Accrual Start':>14} {'Accrual End':>14} {'Days':>8} {'Year Frac':>12} {'Type':>10}")
print('-' * 70)

for i, period in enumerate(schedule, 1):
    # Calculate days in period
    days = (date(period.accrual_end.year, period.accrual_end.month, period.accrual_end.day) -
            date(period.accrual_start.year, period.accrual_start.month, period.accrual_start.day)).days

    # Identify stub vs regular
    period_type = 'Stub' if i == 1 and days < 85 else 'Regular'

    print(f'{i:<4} {fmt(period.accrual_start):>14} {fmt(period.accrual_end):>14} '
          f'{days:>8} {period.year_fraction:>12.6f} {period_type:>10}')

print()
print('The first period is shorter (stub) because it starts mid-cycle')
print()

# =============================================================================
# Different Frequencies
# =============================================================================

print('-' * 70)
print('Comparing Payment Frequencies')
print('-' * 70)
print()

effective = parse_date('2024-03-20')
maturity = parse_date('2026-03-20')

frequencies = [
    (PaymentFrequency.QUARTERLY, 'Quarterly (3M)'),
    (PaymentFrequency.SEMI_ANNUAL, 'Semi-Annual (6M)'),
    (PaymentFrequency.ANNUAL, 'Annual (12M)'),
]

print(f'Period: {fmt(effective)} to {fmt(maturity)} (2 years)')
print()

for freq, name in frequencies:
    sched = CDSSchedule(
        accrual_start=effective,
        maturity=maturity,
        frequency=freq,
    )
    print(f'{name}:')
    print(f'  Number of payments: {len(sched)}')
    print(f'  Typical year fraction per period: {sched[0].year_fraction:.6f}')
    print()

print('Quarterly is standard for CDS (4 payments per year)')
print()

# =============================================================================
# Accrued Interest Calculation
# =============================================================================

print('-' * 70)
print('Accrued Interest Calculation')
print('-' * 70)
print()

accrual_start = parse_date('2024-03-20')
maturity_date = parse_date('2027-03-20')
coupon_rate = 100  # bps
notional = 10_000_000

schedule = CDSSchedule(
    accrual_start=accrual_start,
    maturity=maturity_date,
    frequency=PaymentFrequency.QUARTERLY,
)

# Calculate accrued at different settlement dates
settlement_dates = [
    '2024-03-21',  # 1 day into first period
    '2024-04-20',  # 1 month in
    '2024-05-20',  # 2 months in
    '2024-06-19',  # 1 day before end
    '2024-06-20',  # End of period (payment date)
]

print(f'Accrual Start: {fmt(accrual_start)}, First Period Ends: 06/20/2024')
print(f'Coupon: {coupon_rate} bps, Notional: ${notional:,.0f}')
print()

print(f"{'Settlement':<14} {'Days Accrued':>14} {'Accrued ($)':>14}")
print('-' * 46)

for settle_str in settlement_dates:
    settle = parse_date(settle_str)
    accrued_days, _ = get_accrued_days(settle, schedule)
    accrued_interest = calculate_accrued_interest(
        settle, schedule, coupon_rate / 10000, notional
    )
    print(f'{fmt(settle):<14} {accrued_days:>14} ${accrued_interest:>12,.2f}')

print()

# =============================================================================
# Full Period Breakdown
# =============================================================================

print('-' * 70)
print('Detailed Period Analysis')
print('-' * 70)
print()

effective = parse_date('2024-03-20')
maturity = parse_date('2025-03-20')
coupon_bps = 100
notional = 10_000_000

schedule = CDSSchedule(
    accrual_start=effective,
    maturity=maturity,
    frequency=PaymentFrequency.QUARTERLY,
)

print(f'1-Year CDS: {fmt(effective)} to {fmt(maturity)}')
print(f'Coupon: {coupon_bps} bps on ${notional:,.0f}')
print()

total_premium = 0

print(f"{'Period':<10} {'Accrual Range':<30} {'Year Frac':>12} {'Premium ($)':>14}")
print('-' * 70)

for i, period in enumerate(schedule, 1):
    premium = notional * (coupon_bps / 10000) * period.year_fraction
    total_premium += premium

    range_str = f'{fmt(period.accrual_start)} - {fmt(period.accrual_end)}'
    print(f'Q{i:<9} {range_str:<30} {period.year_fraction:>12.6f} ${premium:>12,.2f}')

print('-' * 70)
print(f"{'Total':<10} {'':<30} {sum(p.year_fraction for p in schedule):>12.6f} ${total_premium:>12,.2f}")
print()

annual_premium = notional * (coupon_bps / 10000)
print(f'Expected annual premium (simple): ${annual_premium:,.2f}')
print(f'Actual annual premium (ACT/360):  ${total_premium:,.2f}')
print(f'Difference due to ACT/360 convention: ${total_premium - annual_premium:,.2f}')
print()

# =============================================================================
# Payment Date Adjustments
# =============================================================================

print('-' * 70)
print('Payment Date Business Day Adjustment')
print('-' * 70)
print()

# Create a schedule where a payment date falls on weekend
effective = parse_date('2024-06-20')  # Thursday
maturity = parse_date('2025-09-20')   # Saturday!

schedule = CDSSchedule(
    accrual_start=effective,
    maturity=maturity,
    frequency=PaymentFrequency.QUARTERLY,
)

print('When payment dates fall on weekends, they are adjusted:')
print()

print(f"{'#':<4} {'Accrual End':>14} {'Unadjusted Pay':>16} {'Adjusted Pay':>14} {'Day':>8}")
print('-' * 62)

for i, period in enumerate(schedule, 1):
    # The accrual end is the unadjusted date
    unadj = period.accrual_end
    adj = period.payment_date

    day_name = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][adj.weekday()]

    # Check if adjustment was made
    adjusted = 'same' if unadj == adj else 'adjusted'

    print(f'{i:<4} {fmt(unadj):>14} {fmt(unadj):>16} {fmt(adj):>14} {day_name:>8}')

print()
print('Payment dates are adjusted using Modified Following convention')
print('(move to next business day, unless it crosses month boundary)')
print()

# =============================================================================
# Schedule Iteration Examples
# =============================================================================

print('-' * 70)
print('Working with Schedule Objects')
print('-' * 70)
print()

schedule = CDSSchedule(
    accrual_start=parse_date('2024-03-20'),
    maturity=parse_date('2026-03-20'),
    frequency=PaymentFrequency.QUARTERLY,
)

print('Schedule supports iteration and indexing:')
print()

print(f'  len(schedule):      {len(schedule)}')
print(f'  schedule[0]:        Period from {fmt(schedule[0].accrual_start)} to {fmt(schedule[0].accrual_end)}')
print(f'  schedule[-1]:       Period from {fmt(schedule[-1].accrual_start)} to {fmt(schedule[-1].accrual_end)}')
print(f'  schedule.periods:   List of {len(schedule.periods)} CouponPeriod objects')
print()

print('Iterating over schedule:')
for i, period in enumerate(list(schedule)[:3]):  # First 3 periods
    print(f'  Period {i+1}: {fmt(period.accrual_start)} to {fmt(period.accrual_end)}')
print('  ...')
print()

print('=' * 70)
print('Example Complete')
print('=' * 70)
