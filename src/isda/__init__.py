"""
ISDA CDS Pricer - Pure Python Implementation

A clean, academic implementation of the ISDA CDS Standard Model for pricing
Credit Default Swaps.

Basic Usage:
    >>> from isda import CDSPricer
    >>>
    >>> pricer = CDSPricer(
    ...     trade_date='31/08/2022',
    ...     swap_rates=[0.002979, 0.006419, 0.01165, ...],
    ...     swap_tenors=['1M', '3M', '6M', '1Y', ...]
    ... )
    >>>
    >>> result = pricer.price_cds(
    ...     maturity_date='20/12/2026',
    ...     par_spread=0.0065,
    ...     coupon_rate=100,  # bps
    ...     notional=12_000_000,
    ...     recovery_rate=0.4
    ... )
    >>>
    >>> print(f"PV: {result.pv_dirty:.2f}")
    >>> print(f"CS01: {result.cs01 * 1e6:.2f} per MM")
"""

__version__ = '1.0.0'

# Calendar
from .calendar import Calendar, add_business_days, adjust_date, is_business_day
# CDS classes
from .cds import CDS, CDSContract, CDSPricingResult
# Backward-compatible API (for migrating from C++ version)
from .compat import calculate_spread_from_upfront_charge, cds_all_in_one
from .compat import cds_index_all_in_one, compute_isda_upfront
from .credit_curve import bootstrap_credit_curve
from .credit_curve import credit_curve_from_hazard_rates
# Curve classes
from .curves import CreditCurve, Curve, ZeroCurve
# Date utilities
from .dates import add_days, add_months, add_years, parse_date, year_fraction
# Enumerations
from .enums import AccrualOnDefault, BadDayConvention, DayCountConvention
from .enums import PaymentFrequency, StubMethod
# IMM dates
from .imm import imm_date_vector  # backward compatible
from .imm import imm_dates_for_tenors, is_imm_date, next_imm_date
from .imm import previous_imm_date
# Main pricer API
from .pricer import CDSPricer, price_cds_simple
# Schedule
from .schedule import CDSSchedule, CouponPeriod, generate_cds_schedule
# Tenor parsing
from .tenor import Tenor, parse_tenor, tenor_to_date
from .zero_curve import bootstrap_zero_curve, build_zero_curve_from_rates

__all__ = [
    # Version
    '__version__',
    # Main API
    'CDSPricer',
    'price_cds_simple',
    # CDS classes
    'CDS',
    'CDSContract',
    'CDSPricingResult',
    # Curves
    'Curve',
    'ZeroCurve',
    'CreditCurve',
    'bootstrap_zero_curve',
    'build_zero_curve_from_rates',
    'bootstrap_credit_curve',
    'credit_curve_from_hazard_rates',
    # Enums
    'DayCountConvention',
    'BadDayConvention',
    'StubMethod',
    'AccrualOnDefault',
    'PaymentFrequency',
    # Dates
    'parse_date',
    'year_fraction',
    'add_months',
    'add_days',
    'add_years',
    # Calendar
    'Calendar',
    'is_business_day',
    'adjust_date',
    'add_business_days',
    # Schedule
    'CDSSchedule',
    'CouponPeriod',
    'generate_cds_schedule',
    # IMM
    'next_imm_date',
    'previous_imm_date',
    'imm_dates_for_tenors',
    'is_imm_date',
    'imm_date_vector',
    # Tenor
    'Tenor',
    'parse_tenor',
    'tenor_to_date',
    # Backward-compatible API
    'cds_all_in_one',
    'compute_isda_upfront',
    'calculate_spread_from_upfront_charge',
    'cds_index_all_in_one',
]
