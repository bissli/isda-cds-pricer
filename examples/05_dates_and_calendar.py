#!/usr/bin/env python3
"""
Date Utilities and Calendar Functions
=====================================

This example demonstrates:
1. Date parsing from various formats
2. Year fraction calculations (day count conventions)
3. Business day adjustments
4. Date arithmetic

The library uses opendate.Date for all date operations.
"""

from datetime import date

from isda import BadDayConvention, Calendar, DayCountConvention
from isda import add_business_days, add_days, add_months, add_years
from isda import adjust_date, is_business_day, parse_date, year_fraction


def fmt(d) -> str:
    """Format date as MM/DD/YYYY."""
    return f'{d.month:02d}/{d.day:02d}/{d.year}'


print('=' * 70)
print('ISDA CDS Standard Model - Date Utilities')
print('=' * 70)
print()

# =============================================================================
# Date Parsing
# =============================================================================

print('-' * 70)
print('Date Parsing')
print('-' * 70)
print()

print('The library accepts dates in multiple formats:')
print()

formats = [
    ('DD/MM/YYYY', '31/08/2022'),
    ('YYYY-MM-DD', '2022-08-31'),
    ('MM/DD/YYYY', '08/31/2022'),
    ('date object', date(2022, 8, 31)),
]

print(f"{'Format':<16} {'Input':<16} {'Parsed':>14}")
print('-' * 50)

for format_name, input_val in formats:
    d = parse_date(input_val)
    print(f'{format_name:<16} {str(input_val):<16} {fmt(d):>14}')

print()

# =============================================================================
# Year Fractions (Day Count Conventions)
# =============================================================================

print('-' * 70)
print('Year Fractions - Day Count Conventions')
print('-' * 70)
print()

start = parse_date('2024-01-01')
end = parse_date('2024-04-01')  # April 1 = 91 days (leap year)

print(f'Period: {fmt(start)} to {fmt(end)} (91 calendar days)')
print()

conventions = [
    (DayCountConvention.ACT_360, 'ACT/360', '91/360'),
    (DayCountConvention.ACT_365F, 'ACT/365F', '91/365'),
    (DayCountConvention.ACT_365, 'ACT/365', '91/365'),
    (DayCountConvention.THIRTY_360, '30/360', '90/360'),
]

print(f"{'Convention':<12} {'Formula':<12} {'Year Fraction':>16}")
print('-' * 44)

for conv, name, formula in conventions:
    yf = year_fraction(start, end, conv)
    print(f'{name:<12} {formula:<12} {yf:>16.10f}')

print()
print('ACT/360 is standard for CDS premium accruals')
print('30/360 counts 30 days per month (90 days for 3 months)')
print()

# Full year comparison
print('Full Year Comparison (2024 is a leap year = 366 days):')
print()

start_year = parse_date('2024-01-01')
end_year = parse_date('2025-01-01')

print(f"{'Convention':<12} {'Year Fraction':>16}")
print('-' * 32)

for conv, name, _ in conventions[:3]:
    yf = year_fraction(start_year, end_year, conv)
    print(f'{name:<12} {yf:>16.10f}')

print()

# =============================================================================
# Business Days
# =============================================================================

print('-' * 70)
print('Business Day Functions')
print('-' * 70)
print()

# Test dates (using ISO format for clarity)
test_dates = [
    ('2024-01-15', 'Monday'),     # Martin Luther King Jr. Day week
    ('2024-01-18', 'Thursday'),
    ('2024-01-19', 'Friday'),
    ('2024-01-20', 'Saturday'),
    ('2024-01-21', 'Sunday'),
    ('2024-01-22', 'Monday'),
]

print('Checking if dates are business days:')
print()
print(f"{'Date':<14} {'Day':<12} {'Business Day?':>15}")
print('-' * 44)

for date_str, day_name in test_dates:
    d = parse_date(date_str)
    is_bd = is_business_day(d)
    status = 'Yes' if is_bd else 'No'
    print(f'{fmt(d):<14} {day_name:<12} {status:>15}')

print()
print('Note: Default calendar excludes weekends only (no holidays)')
print()

# =============================================================================
# Bad Day Conventions
# =============================================================================

print('-' * 70)
print('Bad Day Conventions')
print('-' * 70)
print()

# Saturday date
saturday = parse_date('2024-01-20')
print(f'Original date: {fmt(saturday)} (Saturday)')
print()

conventions = [
    (BadDayConvention.NONE, 'None'),
    (BadDayConvention.FOLLOWING, 'Following'),
    (BadDayConvention.PRECEDING, 'Preceding'),
    (BadDayConvention.MODIFIED_FOLLOWING, 'Modified Following'),
]

print(f"{'Convention':<22} {'Adjusted Date':>16} {'Day':>12}")
print('-' * 54)

for conv, name in conventions:
    adjusted = adjust_date(saturday, conv)
    day_name = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][adjusted.weekday()]
    print(f'{name:<22} {fmt(adjusted):>16}   {day_name:>10}')

print()

# Month-end example
print('Month-End Example (Modified Following):')
print()

# February 29, 2020 is Saturday (leap year)
feb_29 = parse_date('2020-02-29')
adjusted = adjust_date(feb_29, BadDayConvention.MODIFIED_FOLLOWING)

print(f'  Original: {fmt(feb_29)} (Saturday, month end)')
print('  Following would give: 03/02/2020 (Monday, different month)')
print(f'  Modified Following: {fmt(adjusted)} (Friday, same month)')
print()
print('Modified Following falls back to preceding if following crosses month boundary')
print()

# =============================================================================
# Date Arithmetic
# =============================================================================

print('-' * 70)
print('Date Arithmetic')
print('-' * 70)
print()

base = parse_date('2024-01-31')
print(f'Base date: {fmt(base)}')
print()

print('Adding Calendar Days:')
print(f'  + 1 day:   {fmt(add_days(base, 1))}')
print(f'  + 30 days: {fmt(add_days(base, 30))}')
print(f'  - 10 days: {fmt(add_days(base, -10))}')
print()

print('Adding Months (end-of-month handling):')
print(f'  + 1 month: {fmt(add_months(base, 1))}  (Feb only has 29 days in 2024)')
print(f'  + 2 months: {fmt(add_months(base, 2))}')
print(f'  + 12 months: {fmt(add_months(base, 12))}')
print()

print('Adding Years:')
print(f'  + 1 year:  {fmt(add_years(base, 1))}')
print(f'  + 5 years: {fmt(add_years(base, 5))}')
print()

# Leap year handling
feb_29_2024 = parse_date('2024-02-29')
print(f'Leap Year Handling (from {fmt(feb_29_2024)}):')
print(f'  + 1 year:  {fmt(add_years(feb_29_2024, 1))}  (2025 has no Feb 29)')
print(f'  + 4 years: {fmt(add_years(feb_29_2024, 4))}  (2028 is a leap year)')
print()

# =============================================================================
# Business Day Arithmetic
# =============================================================================

print('-' * 70)
print('Business Day Arithmetic')
print('-' * 70)
print()

friday = parse_date('2024-01-19')  # Friday
print(f'Starting from: {fmt(friday)} (Friday)')
print()

print(f"{'Operation':<24} {'Result':>14} {'Day':>10}")
print('-' * 52)

operations = [
    (1, '+ 1 business day'),
    (2, '+ 2 business days'),
    (5, '+ 5 business days'),
    (-1, '- 1 business day'),
    (-5, '- 5 business days'),
]

for days, desc in operations:
    result = add_business_days(friday, days)
    day_name = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun'][result.weekday()]
    print(f'{desc:<24} {fmt(result):>14}   {day_name:>8}')

print()
print('Business day arithmetic skips weekends')
print()

# =============================================================================
# Custom Calendar with Holidays
# =============================================================================

print('-' * 70)
print('Custom Calendar with Holidays')
print('-' * 70)
print()

# Create calendar with US holidays
holidays = {
    date(2024, 1, 1),   # New Year's Day
    date(2024, 1, 15),  # MLK Day
    date(2024, 7, 4),   # Independence Day
    date(2024, 12, 25),  # Christmas
}

cal = Calendar(holidays=holidays)

print('Calendar with US holidays (sample):')
for h in sorted(holidays):
    print(f"  {h.strftime('%m/%d/%Y')} - Holiday")
print()

# Test dates around holidays
test_dates = [
    parse_date('2024-01-15'),  # MLK Day (Monday)
    parse_date('2024-07-04'),  # Independence Day (Thursday)
]

print(f"{'Date':<14} {'Is Business Day?':>20}")
print('-' * 38)

for d in test_dates:
    is_bd = cal.is_business_day(d)
    status = 'Yes' if is_bd else 'No (Holiday)'
    print(f'{fmt(d):<14} {status:>20}')

print()

# Business days with holiday calendar
jan_12 = parse_date('2024-01-12')  # Friday before MLK weekend
print(f'Adding business days from {fmt(jan_12)} (Friday before MLK Day):')
print()

result_default = add_business_days(jan_12, 2)  # Default calendar
result_holiday = cal.add_business_days(jan_12, 2)  # Holiday calendar

print(f'  + 2 days (default calendar): {fmt(result_default)} (skips weekend)')
print(f'  + 2 days (with MLK holiday):  {fmt(result_holiday)} (skips weekend + MLK)')
print()

print('=' * 70)
print('Example Complete')
print('=' * 70)
