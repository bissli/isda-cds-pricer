#!/usr/bin/env python3
"""
IMM Dates for CDS
=================

This example demonstrates IMM (International Monetary Market) date
handling for CDS contracts.

CDS contracts typically mature on IMM dates:
- March 20
- June 20
- September 20
- December 20

This standardization improves liquidity by having common maturity dates.
"""

from datetime import date

from isda import imm_date_vector, imm_dates_for_tenors, is_imm_date
from isda import next_imm_date, parse_date, previous_imm_date


def fmt(d) -> str:
    """Format date as MM/DD/YYYY."""
    return f'{d.month:02d}/{d.day:02d}/{d.year}'


print('=' * 70)
print('ISDA CDS Standard Model - IMM Dates')
print('=' * 70)
print()

# =============================================================================
# What is an IMM Date?
# =============================================================================

print('-' * 70)
print('IMM Date Definition')
print('-' * 70)
print()

print('IMM dates for CDS are the 20th of:')
print('  - March (Q1)')
print('  - June (Q2)')
print('  - September (Q3)')
print('  - December (Q4)')
print()

# Check various dates
test_dates = [
    '03/20/2024',
    '06/20/2024',
    '09/20/2024',
    '12/20/2024',
    '03/15/2024',
    '01/20/2024',
    '06/21/2024',
]

print(f"{'Date':<14} {'Is IMM?':>10}")
print('-' * 28)

for date_str in test_dates:
    d = parse_date(date_str)
    is_imm = is_imm_date(d)
    status = 'Yes' if is_imm else 'No'
    print(f'{fmt(d):<14} {status:>10}')

print()

# =============================================================================
# Next and Previous IMM Dates
# =============================================================================

print('-' * 70)
print('Finding Next and Previous IMM Dates')
print('-' * 70)
print()

reference_dates = [
    '01/15/2024',  # Mid-January
    '03/19/2024',  # Day before IMM
    '03/20/2024',  # On IMM date
    '03/21/2024',  # Day after IMM
    '07/01/2024',  # Start of Q3
    '11/15/2024',  # Mid-November
]

print(f"{'Reference':<14} {'Previous IMM':>14} {'Next IMM':>14}")
print('-' * 46)

for date_str in reference_dates:
    d = parse_date(date_str)
    prev_imm = previous_imm_date(d)
    next_imm = next_imm_date(d)
    print(f'{fmt(d):<14} {fmt(prev_imm):>14} {fmt(next_imm):>14}')

print()
print("Note: If on an IMM date, 'previous' returns that date")
print()

# =============================================================================
# IMM Dates for Standard Tenors
# =============================================================================

print('-' * 70)
print('IMM Dates for Standard CDS Tenors')
print('-' * 70)
print()

trade_date = parse_date('08/31/2022')
print(f'Trade Date: {fmt(trade_date)}')
print()

# Standard CDS tenors (in years)
tenors_years = [0.5, 1, 2, 3, 5, 7, 10]
tenor_labels = ['6M', '1Y', '2Y', '3Y', '5Y', '7Y', '10Y']

imm_dates_result = imm_dates_for_tenors(trade_date, tenors_years)

print(f"{'Tenor':<8} {'IMM Maturity':>14} {'Approx Years':>14}")
print('-' * 40)

for label, imm_date_str in imm_dates_result:
    # Parse the IMM date from string
    imm_date = parse_date(imm_date_str)
    # Calculate approximate years to maturity
    days = (date(imm_date.year, imm_date.month, imm_date.day) -
            date(trade_date.year, trade_date.month, trade_date.day)).days
    years = days / 365.25
    print(f'{label:<8} {fmt(imm_date):>14} {years:>12.2f}Y')

print()
print('CDS maturities roll to the next IMM date after the tenor date')
print()

# =============================================================================
# IMM Date Vector (Multiple Dates)
# =============================================================================

print('-' * 70)
print('Generating IMM Date Vectors')
print('-' * 70)
print()

# Generate IMM dates from a starting point using tenor list
start = parse_date('2024-01-01')
# Use quarter tenors to get next 8 IMM dates (0.25Y = 3M)
tenors = [0.25, 0.5, 0.75, 1.0, 1.25, 1.5, 1.75, 2.0]
imm_vector = imm_date_vector(start, tenors)

print(f'Next 8 IMM dates from {fmt(start)}:')
print()

print(f"{'#':<4} {'IMM Date':>14} {'Quarter':>10}")
print('-' * 32)

for i, (label, imm_date_str) in enumerate(imm_vector, 1):
    imm = parse_date(imm_date_str)
    quarter = {3: 'Q1', 6: 'Q2', 9: 'Q3', 12: 'Q4'}[imm.month]
    print(f'{i:<4} {fmt(imm):>14} {quarter:>10}')

print()

# =============================================================================
# IMM Roll Dates
# =============================================================================

print('-' * 70)
print('IMM Roll Dates Throughout a Year')
print('-' * 70)
print()

print("Showing how the 'next IMM' changes throughout 2024:")
print()

sample_dates = [
    ('01/01/2024', 'Start of year'),
    ('03/19/2024', 'Before Q1 IMM'),
    ('03/20/2024', 'Q1 IMM date'),
    ('03/21/2024', 'After Q1 IMM'),
    ('06/01/2024', 'Start of Q2'),
    ('06/20/2024', 'Q2 IMM date'),
    ('09/01/2024', 'Start of Q3'),
    ('12/01/2024', 'Start of Q4'),
    ('12/20/2024', 'Q4 IMM date'),
    ('12/21/2024', 'After Q4 IMM'),
]

print(f"{'Date':<14} {'Description':<18} {'Next IMM':>14}")
print('-' * 50)

for date_str, desc in sample_dates:
    d = parse_date(date_str)
    next_imm = next_imm_date(d)
    print(f'{fmt(d):<14} {desc:<18} {fmt(next_imm):>14}')

print()

# =============================================================================
# On-the-Run vs Off-the-Run
# =============================================================================

print('-' * 70)
print('On-the-Run vs Off-the-Run CDS')
print('-' * 70)
print()

print("CDS liquidity is highest for 'on-the-run' contracts that mature")
print('on the next few IMM dates. As time passes, contracts become')
print("'off-the-run' and less liquid.")
print()

# Show how a 5Y CDS changes over time
print('Example: 5Y CDS maturity evolution')
print()

observation_dates = [
    '01/15/2024',
    '03/21/2024',  # Just rolled
    '06/21/2024',  # Rolled again
    '09/21/2024',
    '12/21/2024',
]

print(f"{'Observation':<14} {'5Y Maturity':>14} {'Status':<20}")
print('-' * 52)

for date_str in observation_dates:
    d = parse_date(date_str)
    # 5Y IMM date (pass numeric tenor in years)
    result = imm_dates_for_tenors(d, [5])[0]
    five_yr = parse_date(result[1])  # Extract date string from (label, date_str) tuple

    # Check if this is a "fresh" roll (within a few days of IMM)
    prev_imm = previous_imm_date(d)
    days_since_roll = (date(d.year, d.month, d.day) -
                       date(prev_imm.year, prev_imm.month, prev_imm.day)).days

    if days_since_roll <= 5:
        status = 'Just rolled (on-the-run)'
    elif days_since_roll <= 45:
        status = 'On-the-run'
    else:
        status = 'Seasoned'

    print(f'{fmt(d):<14} {fmt(five_yr):>14} {status:<20}')

print()
print('Market makers typically quote tighter spreads for on-the-run contracts')
print()

# =============================================================================
# Year-End Effects
# =============================================================================

print('-' * 70)
print('Year-End IMM Date Behavior')
print('-' * 70)
print()

print('At year end, IMM dates roll to the next year:')
print()

dec_dates = [
    '12/15/2024',
    '12/19/2024',
    '12/20/2024',
    '12/21/2024',
    '12/31/2024',
    '01/01/2025',
]

print(f"{'Date':<14} {'Next IMM':>14} {'Previous IMM':>14}")
print('-' * 46)

for date_str in dec_dates:
    d = parse_date(date_str)
    next_imm = next_imm_date(d)
    prev_imm = previous_imm_date(d)
    print(f'{fmt(d):<14} {fmt(next_imm):>14} {fmt(prev_imm):>14}')

print()

print('=' * 70)
print('Example Complete')
print('=' * 70)
