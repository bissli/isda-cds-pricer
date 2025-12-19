"""
High-level CDS Pricer API.

Provides a clean, user-friendly interface for pricing CDS contracts.
"""

import datetime
import functools
import inspect
from typing import Union

from opendate import Date

from .cds import CDS, CDSContract, CDSPricingResult
from .credit_curve import bootstrap_credit_curve
from .credit_curve_isda import bootstrap_credit_curve_isda
from .curves import CreditCurve
from .enums import DayCountConvention, PaymentFrequency
from .root_finding import brent
from .zero_curve import bootstrap_zero_curve

DateLike = Union[Date, str, datetime.date, datetime.datetime]


def ensure_date(value: DateLike) -> Date:
    """Convert a date-like value to a Date object."""
    if isinstance(value, Date):
        return value
    if isinstance(value, str):
        return Date.parse(value)
    result = Date.instance(value)
    if result is None:
        raise TypeError(f'Cannot convert {type(value).__name__} to Date: {value}')
    return result


def ensure_dates(*param_names: str):
    """
    Decorator that converts specified parameters to Date objects.

    Args:
        *param_names: Names of parameters to convert to Date objects.
                      None values are passed through unchanged.
    """
    def decorator(func):
        sig = inspect.signature(func)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            bound = sig.bind(*args, **kwargs)
            bound.apply_defaults()

            for name in param_names:
                if name in bound.arguments and bound.arguments[name] is not None:
                    bound.arguments[name] = ensure_date(bound.arguments[name])

            return func(*bound.args, **bound.kwargs)
        return wrapper
    return decorator


class CDSPricer:
    """
    High-level CDS pricing engine.

    This class provides a clean API for pricing CDS contracts by handling
    curve construction internally.

    Example:
        >>> pricer = CDSPricer(
        ...     trade_date=Date.parse('31/08/2022'),
        ...     swap_rates=[0.002979, 0.006419, 0.01165, ...],
        ...     swap_tenors=['1M', '3M', '6M', '1Y', ...]
        ... )
        >>> result = pricer.price_cds(
        ...     maturity_date=Date.parse('20/12/2026'),
        ...     par_spread=0.0065,
        ...     coupon_rate=100,  # bps
        ...     notional=12_000_000,
        ...     recovery_rate=0.4
        ... )
    """

    def __init__(
        self,
        trade_date: DateLike,
        swap_rates: list[float],
        swap_tenors: list[str],
        swap_maturity_dates: list[Date] | None = None,
        fixed_day_count: DayCountConvention = DayCountConvention.THIRTY_360,
        mm_day_count: DayCountConvention = DayCountConvention.ACT_360,
    ):
        """
        Initialize the pricer with market data.

        Args:
            trade_date: Trade/valuation date
            swap_rates: List of swap/money market rates
            swap_tenors: List of tenor strings
            swap_maturity_dates: Optional explicit maturity dates
            fixed_day_count: Day count for swap fixed leg (default 30/360 per ISDA)
            mm_day_count: Day count for money market rates (default ACT/360 per ISDA)
        """
        self.trade_date = ensure_date(trade_date)

        # Bootstrap the zero curve using ISDA conventions
        self.zero_curve = bootstrap_zero_curve(
            base_date=self.trade_date,
            swap_rates=swap_rates,
            swap_tenors=swap_tenors,
            swap_maturity_dates=swap_maturity_dates,
            fixed_day_count=fixed_day_count,
            mm_day_count=mm_day_count,
        )

    def build_credit_curve(
        self,
        par_spreads: list[float],
        spread_tenors: list[str],
        recovery_rate: float = 0.4,
    ) -> CreditCurve:
        """
        Build a credit curve from par CDS spreads.

        Args:
            par_spreads: List of par CDS spreads (as decimals)
            spread_tenors: List of tenor strings
            recovery_rate: Recovery rate assumption

        Returns
            Bootstrapped CreditCurve
        """
        return bootstrap_credit_curve(
            base_date=self.trade_date,
            par_spreads=par_spreads,
            spread_tenors=spread_tenors,
            zero_curve=self.zero_curve,
            recovery_rate=recovery_rate,
        )

    @ensure_dates('maturity_date', 'accrual_start_date', 'value_date')
    def price_cds(
        self,
        maturity_date: DateLike,
        par_spread: float,
        coupon_rate: float,  # In basis points
        notional: float,
        recovery_rate: float = 0.4,
        is_buy_protection: bool = True,
        accrual_start_date: DateLike | None = None,
        value_date: DateLike | None = None,
        spread_tenors: list[str] | None = None,
    ) -> CDSPricingResult:
        """
        Price a single CDS contract.

        Args:
            maturity_date: CDS maturity date
            par_spread: Par CDS spread (as decimal, e.g., 0.0065 for 65bps)
            coupon_rate: Coupon rate in basis points (e.g., 100 for 100bps)
            notional: Notional amount
            recovery_rate: Recovery rate (e.g., 0.4 for 40%)
            is_buy_protection: True for buying protection, False for selling
            accrual_start_date: Start of first accrual period (default: previous IMM)
            value_date: Valuation date (default: trade date)
            spread_tenors: Tenors for credit curve (default: standard set)

        Returns
            CDSPricingResult with all pricing metrics
        """
        # Apply defaults for None values
        if value_date is None:
            value_date = self.trade_date
        if accrual_start_date is None:
            from .imm import previous_imm_date
            accrual_start_date = previous_imm_date(self.trade_date)

        # Build credit curve using ISDA methodology
        # This creates a single-point curve bootstrapped to match the par spread
        credit_curve = bootstrap_credit_curve_isda(
            base_date=self.trade_date,
            par_spread=par_spread,
            maturity_date=maturity_date,
            zero_curve=self.zero_curve,
            recovery_rate=recovery_rate,
            accrual_start_date=accrual_start_date,
            payment_frequency=PaymentFrequency.QUARTERLY,
            day_count=DayCountConvention.ACT_360,
        )

        # Convert coupon from bps to decimal
        coupon_decimal = coupon_rate / 10000.0

        # Create contract
        contract = CDSContract(
            trade_date=self.trade_date,
            maturity_date=maturity_date,
            accrual_start_date=accrual_start_date,
            coupon_rate=coupon_decimal,
            notional=notional,
            recovery_rate=recovery_rate,
            is_buy_protection=is_buy_protection,
        )

        # Create and price CDS
        cds = CDS(
            contract=contract,
            discount_curve=self.zero_curve,
            credit_curve=credit_curve,
        )

        return cds.price(value_date=value_date)

    def compute_upfront(
        self,
        maturity_date: DateLike,
        par_spread: float,
        coupon_rate: float,  # In basis points
        notional: float,
        recovery_rate: float = 0.4,
        is_buy_protection: bool = True,
        accrual_start_date: DateLike | None = None,
    ) -> tuple[float, float, float]:
        """
        Compute the upfront payment for a CDS.

        Returns
            Tuple of (dirty_upfront, clean_upfront, accrued_interest)
            Positive values mean payment FROM protection buyer
        """
        result = self.price_cds(
            maturity_date=maturity_date,
            par_spread=par_spread,
            coupon_rate=coupon_rate,
            notional=notional,
            recovery_rate=recovery_rate,
            is_buy_protection=is_buy_protection,
            accrual_start_date=accrual_start_date,
        )

        # ISDA convention: upfront = contingent_leg_pv - fee_leg_pv
        # This is exactly what pv_dirty represents (already computed in CDS.price())
        # Positive upfront: buyer pays (spread > coupon)
        # Negative upfront: buyer receives (spread < coupon)
        dirty_upfront = result.pv_dirty
        clean_upfront = result.pv_clean

        return dirty_upfront, clean_upfront, result.accrued_interest

    def compute_spread_from_upfront(
        self,
        maturity_date: DateLike,
        upfront_charge: float,  # As fraction of notional
        coupon_rate: float,  # In basis points
        notional: float,
        recovery_rate: float = 0.4,
        is_buy_protection: bool = True,
        accrual_start_date: DateLike | None = None,
        is_clean: bool = False,
    ) -> float:
        """
        Compute the par spread implied by an upfront charge.

        Args:
            maturity_date: CDS maturity date
            upfront_charge: Upfront payment as fraction of notional
            coupon_rate: Running coupon in basis points
            notional: Notional amount
            recovery_rate: Recovery rate
            is_buy_protection: True for buying protection
            accrual_start_date: Accrual start date
            is_clean: If True, upfront_charge is clean (excludes accrued)

        Returns
            Implied par spread (as decimal)
        """
        # Target PV based on upfront
        # In our convention: upfront = pv_dirty (positive = buyer pays)
        # So we find spread such that pv_dirty = upfront_charge * notional
        target_pv = upfront_charge * notional

        # Objective function: find spread such that PV = target
        def objective(spread: float) -> float:
            result = self.price_cds(
                maturity_date=maturity_date,
                par_spread=spread,
                coupon_rate=coupon_rate,
                notional=notional,
                recovery_rate=recovery_rate,
                is_buy_protection=is_buy_protection,
                accrual_start_date=accrual_start_date,
            )
            if is_clean:
                return result.pv_clean - target_pv
            return result.pv_dirty - target_pv

        # Use Brent's method with reasonable bounds
        try:
            spread = brent(objective, 0.0001, 0.5, tol=1e-10)
        except Exception:
            spread = brent(objective, 1e-6, 1.0, tol=1e-10)

        return spread


def price_cds_simple(
    trade_date: DateLike,
    maturity_date: DateLike,
    swap_rates: list[float],
    swap_tenors: list[str],
    par_spread: float,
    coupon_rate: float,
    notional: float = 1.0,
    recovery_rate: float = 0.4,
    is_buy_protection: bool = True,
) -> CDSPricingResult:
    """
    Simple function to price a CDS with minimal inputs.

    This is a convenience function that creates a CDSPricer internally.

    Args:
        trade_date: Trade date
        maturity_date: Maturity date
        swap_rates: Swap curve rates
        swap_tenors: Swap curve tenors
        par_spread: Par CDS spread (decimal)
        coupon_rate: Coupon in basis points
        notional: Notional amount
        recovery_rate: Recovery rate
        is_buy_protection: Buy or sell protection

    Returns
        CDSPricingResult
    """
    pricer = CDSPricer(
        trade_date=trade_date,
        swap_rates=swap_rates,
        swap_tenors=swap_tenors,
    )

    return pricer.price_cds(
        maturity_date=maturity_date,
        par_spread=par_spread,
        coupon_rate=coupon_rate,
        notional=notional,
        recovery_rate=recovery_rate,
        is_buy_protection=is_buy_protection,
    )
