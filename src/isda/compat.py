"""
Backward-compatible API for existing code.

This module provides functions that match the signatures of the original
C++ ISDA library, making it easy to migrate existing code.

The main functions are:
- cds_all_in_one: Full CDS pricing with all outputs
- compute_isda_upfront: Calculate upfront payment
- calculate_spread_from_upfront_charge: Inverse of upfront calculation
- cds_index_all_in_one: Index CDS pricing
"""

import time
from typing import Any

from .cds import CDS, CDSContract
from .credit_curve import bootstrap_credit_curve
from .curves import CreditCurve, ZeroCurve
from .dates import parse_date
from .imm import previous_imm_date
from .pricer import CDSPricer
from .tenor import parse_tenor
from .zero_curve import bootstrap_zero_curve


def cds_all_in_one(
    trade_date: str,
    effective_date: str,
    maturity_date: str,
    value_date: str,
    accrual_start_date: str,
    recovery_rate: float,
    coupon: float,  # In basis points
    notional: float,
    is_buy_protection: int,  # 1 = buy, 0 = sell
    swap_rates: list[float],
    swap_tenors: list[str],
    swap_maturity_dates: list[str],
    credit_spreads: list[float],
    credit_spread_tenors: list[str],
    spread_roll_tenors: list[str],
    imm_dates: list[str],
    scenario_shifts: list[float],
    verbose: int = 0,
) -> tuple[tuple, tuple, Any]:
    """
    Backward-compatible full CDS pricing function.

    This replicates the signature of the original C++ cds_all_in_one function.

    Args:
        trade_date: Trade date (DD/MM/YYYY)
        effective_date: Effective date (DD/MM/YYYY)
        maturity_date: Maturity date (DD/MM/YYYY)
        value_date: Valuation date (DD/MM/YYYY)
        accrual_start_date: Accrual start date (DD/MM/YYYY)
        recovery_rate: Recovery rate (decimal, e.g., 0.4)
        coupon: Coupon in basis points (e.g., 100)
        notional: Notional amount
        is_buy_protection: 1 for buy protection, 0 for sell
        swap_rates: List of swap rates
        swap_tenors: List of swap tenor strings
        swap_maturity_dates: List of swap maturity dates
        credit_spreads: List of credit spreads (decimal)
        credit_spread_tenors: List of credit spread tenors
        spread_roll_tenors: Roll scenario tenors (unused in Python)
        imm_dates: IMM dates (unused in Python, calculated internally)
        scenario_shifts: Spread scenario shifts (unused in Python)
        verbose: Verbosity level

    Returns
        Tuple of:
        - (pv_dirty, pv_clean, ai, cs01, dv01, duration_ms)
        - (pvbp_6m, pvbp_1y, pvbp_2y, pvbp_3y, pvbp_4y, pvbp_5y, pvbp_7y, pvbp_10y)
        - Par spreads tuple (optional)
    """
    start_time = time.time()

    # Parse dates
    td = parse_date(trade_date)
    vd = parse_date(value_date)
    mat = parse_date(maturity_date)
    acc_start = parse_date(accrual_start_date)

    # Build zero curve
    zero_curve = bootstrap_zero_curve(
        base_date=td,
        swap_rates=swap_rates,
        swap_tenors=swap_tenors,
        swap_maturity_dates=swap_maturity_dates,
    )

    # Build credit curve
    credit_curve = bootstrap_credit_curve(
        base_date=td,
        par_spreads=credit_spreads,
        spread_tenors=credit_spread_tenors,
        zero_curve=zero_curve,
        recovery_rate=recovery_rate,
    )

    # Convert coupon to decimal
    coupon_decimal = coupon / 10000.0

    # Create contract
    contract = CDSContract(
        trade_date=td,
        maturity_date=mat,
        accrual_start_date=acc_start,
        coupon_rate=coupon_decimal,
        notional=notional,
        recovery_rate=recovery_rate,
        is_buy_protection=(is_buy_protection == 1),
    )

    # Create and price CDS
    cds = CDS(
        contract=contract,
        discount_curve=zero_curve,
        credit_curve=credit_curve,
    )

    result = cds.price(value_date=vd)

    duration_ms = (time.time() - start_time) * 1000

    # Calculate PVBP for each tenor
    pvbp_tenors = ['6M', '1Y', '2Y', '3Y', '4Y', '5Y', '7Y', '10Y']
    pvbps = []

    for tenor in pvbp_tenors:
        t = parse_tenor(tenor)
        pvbp_mat = t.add_to_date(td)
        pvbp = _calculate_pvbp(vd, td, pvbp_mat, zero_curve, credit_curve, notional)
        pvbps.append(pvbp)

    # Main results tuple
    main_results = (
        result.pv_dirty,
        result.pv_clean,
        result.accrued_interest,
        result.cs01,
        result.dv01,
        duration_ms,
    )

    # PVBP results tuple
    pvbp_results = tuple(pvbps)

    # Par spread results (placeholder)
    par_spread_results = tuple([result.par_spread or 0.0] * 15)

    return main_results, pvbp_results, par_spread_results


def compute_isda_upfront(
    trade_date: str,
    maturity_date: str,
    accrual_start_date: str,
    settle_date: str,
    recovery_rate: float,
    coupon_rate: float,  # In basis points
    notional: float,
    is_buy_protection: int,
    swap_rates: list[float],
    swap_tenors: list[str],
    par_spread: float,  # Decimal
    is_rofr: int = 0,
    holiday_filename: str = '',
    swap_floating_dcc: str = 'ACT/360',
    swap_fixed_dcc: str = 'ACT/365F',
    swap_fixed_freq: str = '1Y',
    swap_floating_freq: str = '6M',
    verbose: int = 0,
) -> tuple[float, float, float, float]:
    """
    Backward-compatible upfront calculation.

    Args:
        trade_date: Trade date (DD/MM/YYYY)
        maturity_date: Maturity date (DD/MM/YYYY)
        accrual_start_date: Accrual start date (DD/MM/YYYY)
        settle_date: Settlement date (DD/MM/YYYY)
        recovery_rate: Recovery rate (decimal)
        coupon_rate: Coupon in basis points
        notional: Notional amount
        is_buy_protection: 1 for buy, 0 for sell
        swap_rates: Swap rates
        swap_tenors: Swap tenors
        par_spread: Par CDS spread (decimal)
        is_rofr: Restructuring flag (unused)
        holiday_filename: Holiday file (unused)
        swap_floating_dcc: Floating leg day count
        swap_fixed_dcc: Fixed leg day count
        swap_fixed_freq: Fixed leg frequency
        swap_floating_freq: Floating leg frequency
        verbose: Verbosity level

    Returns
        Tuple of (dirty_upfront, clean_upfront, accrued_interest, duration_ms)
    """
    start_time = time.time()

    # Create pricer
    pricer = CDSPricer(
        trade_date=trade_date,
        swap_rates=swap_rates,
        swap_tenors=swap_tenors,
    )

    # Calculate upfront
    dirty, clean, accrued = pricer.compute_upfront(
        maturity_date=maturity_date,
        par_spread=par_spread,
        coupon_rate=coupon_rate,
        notional=notional,
        recovery_rate=recovery_rate,
        is_buy_protection=(is_buy_protection == 1),
        accrual_start_date=accrual_start_date,
    )

    duration_ms = (time.time() - start_time) * 1000

    return dirty, clean, accrued, duration_ms


def calculate_spread_from_upfront_charge(
    trade_date: str,
    maturity_date: str,
    accrual_start_date: str,
    settle_date: str,
    recovery_rate: float,
    coupon_rate: float,  # In basis points
    notional: float,
    is_buy_protection: int,
    swap_rates: list[float],
    swap_tenors: list[str],
    upfront_charge: float,  # As fraction of notional
    is_rofr: int = 0,
    holiday_filename: str = '',
    swap_floating_dcc: str = 'ACT/360',
    swap_fixed_dcc: str = 'ACT/365F',
    swap_fixed_freq: str = '1Y',
    swap_floating_freq: str = '6M',
    is_clean: int = 0,
    verbose: int = 0,
) -> tuple[float, float]:
    """
    Backward-compatible spread from upfront calculation.

    Args:
        Same as compute_isda_upfront, plus:
        upfront_charge: Upfront payment as fraction of notional
        is_clean: 1 if upfront is clean, 0 if dirty

    Returns
        Tuple of (implied_spread, duration_ms)
    """
    start_time = time.time()

    # Create pricer
    pricer = CDSPricer(
        trade_date=trade_date,
        swap_rates=swap_rates,
        swap_tenors=swap_tenors,
    )

    # Calculate implied spread
    spread = pricer.compute_spread_from_upfront(
        maturity_date=maturity_date,
        upfront_charge=upfront_charge,
        coupon_rate=coupon_rate,
        notional=notional,
        recovery_rate=recovery_rate,
        is_buy_protection=(is_buy_protection == 1),
        accrual_start_date=accrual_start_date,
        is_clean=(is_clean == 1),
    )

    duration_ms = (time.time() - start_time) * 1000

    return spread, duration_ms


def cds_index_all_in_one(
    trade_date: str,
    effective_date: str,
    maturity_date: str,
    value_date: str,
    accrual_start_date: str,
    recovery_rate_list: list[float],
    coupon: float,
    notional: float,
    is_buy_protection: int,
    swap_rates: list[float],
    swap_tenors: list[str],
    swap_maturity_dates: list[str],
    credit_spread_list: list[list[float]],
    credit_spread_tenors: list[str],
    spread_roll_tenors: list[str],
    imm_dates: list[str],
    scenario_shifts: list[float],
    verbose: int = 0,
) -> tuple[str, tuple[float, float, float, float]]:
    """
    Backward-compatible index CDS pricing.

    Prices an index as the average of individual name valuations.

    Args:
        recovery_rate_list: List of recovery rates for each name
        credit_spread_list: List of spread curves for each name

    Returns
        Tuple of (status, (pv_dirty, pv_clean, ai, duration_ms))
    """
    start_time = time.time()

    n_names = len(recovery_rate_list)

    total_pv_dirty = 0.0
    total_pv_clean = 0.0
    total_ai = 0.0

    for i in range(n_names):
        result = cds_all_in_one(
            trade_date=trade_date,
            effective_date=effective_date,
            maturity_date=maturity_date,
            value_date=value_date,
            accrual_start_date=accrual_start_date,
            recovery_rate=recovery_rate_list[i],
            coupon=coupon,
            notional=notional / n_names,  # Divide notional
            is_buy_protection=is_buy_protection,
            swap_rates=swap_rates,
            swap_tenors=swap_tenors,
            swap_maturity_dates=swap_maturity_dates,
            credit_spreads=credit_spread_list[i],
            credit_spread_tenors=credit_spread_tenors,
            spread_roll_tenors=spread_roll_tenors,
            imm_dates=imm_dates,
            scenario_shifts=scenario_shifts,
            verbose=verbose,
        )

        main_results = result[0]
        total_pv_dirty += main_results[0]
        total_pv_clean += main_results[1]
        total_ai += main_results[2]

    duration_ms = (time.time() - start_time) * 1000

    return 'OK', (total_pv_dirty, total_pv_clean, total_ai, duration_ms)


def _calculate_pvbp(
    value_date,
    trade_date,
    maturity_date,
    zero_curve: ZeroCurve,
    credit_curve: CreditCurve,
    notional: float,
) -> float:
    """Calculate PVBP for a given maturity."""

    acc_start = previous_imm_date(trade_date)

    contract = CDSContract(
        trade_date=trade_date,
        maturity_date=maturity_date,
        accrual_start_date=acc_start,
        coupon_rate=0.0001,  # 1bp
        notional=notional,
        recovery_rate=0.4,
        is_buy_protection=True,
    )

    cds = CDS(
        contract=contract,
        discount_curve=zero_curve,
        credit_curve=credit_curve,
    )

    result = cds.price(value_date=value_date, compute_sensitivities=False)

    # PVBP is the fee leg PV per 1bp of coupon
    return result.fee_leg_pv
