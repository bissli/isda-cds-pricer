"""
CDS contract representation and pricing.

Provides the main CDS class that combines all components to price
a Credit Default Swap.
"""

from dataclasses import dataclass, field

from opendate import Date

from .contingent_leg import contingent_leg_pv
from .curves import CreditCurve, ZeroCurve
from .enums import AccrualOnDefault, BadDayConvention, DayCountConvention
from .enums import PaymentFrequency
from .fee_leg import calculate_accrued_interest, fee_leg_pv, risky_annuity
from .schedule import generate_cds_schedule


@dataclass
class CDSContract:
    """
    Represents a CDS contract specification.

    This captures the contractual terms of a CDS trade.
    """

    trade_date: Date
    maturity_date: Date
    accrual_start_date: Date
    coupon_rate: float  # As decimal (e.g., 0.01 for 100bps)
    notional: float = 1.0
    recovery_rate: float = 0.4
    is_buy_protection: bool = True

    # Payment conventions (defaults to ISDA standard)
    payment_frequency: PaymentFrequency = PaymentFrequency.QUARTERLY
    day_count: DayCountConvention = DayCountConvention.ACT_360
    bad_day_convention: BadDayConvention = BadDayConvention.MODIFIED_FOLLOWING


@dataclass
class CDSPricingResult:
    """
    Results from pricing a CDS.

    Contains all relevant pricing outputs including sensitivities.
    """

    # Core PV metrics
    pv_dirty: float  # Full PV including accrued
    pv_clean: float  # PV excluding accrued
    accrued_interest: float

    # Leg values
    fee_leg_pv: float
    contingent_leg_pv: float

    # Risk metrics
    cs01: float  # Credit spread sensitivity (PV change per 1bp spread move)
    dv01: float  # Interest rate sensitivity (PV change per 1bp rate move)

    # Additional metrics
    par_spread: float | None = None
    risky_annuity: float | None = None

    # PVBP by tenor (optional)
    pvbp: dict[str, float] = field(default_factory=dict)

    def __repr__(self) -> str:
        return (
            f'CDSPricingResult(\n'
            f'  pv_dirty={self.pv_dirty:.6f},\n'
            f'  pv_clean={self.pv_clean:.6f},\n'
            f'  accrued={self.accrued_interest:.6f},\n'
            f'  cs01={self.cs01 * 1e6:.2f} (per MM),\n'
            f'  dv01={self.dv01 * 1e6:.2f} (per MM)\n'
            f')'
        )


class CDS:
    """
    A CDS instrument with full pricing capability.

    This is the main class for pricing a CDS. It holds both the contract
    terms and the market data needed for pricing.
    """

    def __init__(
        self,
        contract: CDSContract,
        discount_curve: ZeroCurve,
        credit_curve: CreditCurve,
    ):
        """
        Initialize a CDS for pricing.

        Args:
            contract: CDS contract specification
            discount_curve: Zero rate curve for discounting
            credit_curve: Credit curve for survival probabilities
        """
        self.contract = contract
        self.discount_curve = discount_curve
        self.credit_curve = credit_curve

        # Generate the payment schedule
        self.schedule = generate_cds_schedule(
            accrual_start=contract.accrual_start_date,
            maturity=contract.maturity_date,
            frequency=contract.payment_frequency,
            day_count=contract.day_count,
            bad_day=contract.bad_day_convention,
        )

    def price(
        self,
        value_date: Date,
        include_accrual_on_default: bool = True,
        compute_sensitivities: bool = True,
    ) -> CDSPricingResult:
        """
        Price the CDS as of a given value date.

        Args:
            value_date: Valuation date (Date object)
            include_accrual_on_default: Include accrual on default in fee leg
            compute_sensitivities: Compute CS01 and DV01

        Returns
            CDSPricingResult with all pricing metrics
        """
        accrual_mode = (
            AccrualOnDefault.ACCRUED_TO_DEFAULT
            if include_accrual_on_default
            else AccrualOnDefault.NONE
        )

        # Calculate fee leg PV
        fee_pv = fee_leg_pv(
            value_date=value_date,
            schedule=self.schedule,
            coupon_rate=self.contract.coupon_rate,
            discount_curve=self.discount_curve,
            credit_curve=self.credit_curve,
            notional=self.contract.notional,
            accrual_on_default=accrual_mode,
        )

        # Calculate contingent leg PV
        cont_pv = contingent_leg_pv(
            value_date=value_date,
            maturity_date=self.contract.maturity_date,
            discount_curve=self.discount_curve,
            credit_curve=self.credit_curve,
            recovery_rate=self.contract.recovery_rate,
            notional=self.contract.notional,
        )

        # Calculate accrued interest
        accrued = calculate_accrued_interest(
            value_date=value_date,
            schedule=self.schedule,
            coupon_rate=self.contract.coupon_rate,
            notional=self.contract.notional,
        )

        # PV from protection buyer's perspective
        # Buy protection: pay premium (fee leg), receive protection (contingent leg)
        # Sell protection: receive premium (fee leg), pay protection (contingent leg)
        # Relationship: dirty = clean + accrued, so clean = dirty - accrued
        if self.contract.is_buy_protection:
            pv_dirty = cont_pv - fee_pv
            pv_clean = pv_dirty - accrued
        else:
            pv_dirty = fee_pv - cont_pv
            pv_clean = pv_dirty + accrued

        # Calculate sensitivities
        cs01 = 0.0
        dv01 = 0.0
        if compute_sensitivities:
            cs01 = self._compute_cs01(value_date, accrual_mode)
            dv01 = self._compute_dv01(value_date, accrual_mode)

        # Calculate risky annuity
        ra = risky_annuity(
            value_date=value_date,
            schedule=self.schedule,
            discount_curve=self.discount_curve,
            credit_curve=self.credit_curve,
        )

        # Calculate par spread
        if ra > 0:
            par_spread = cont_pv / (ra * self.contract.notional)
        else:
            par_spread = None

        return CDSPricingResult(
            pv_dirty=pv_dirty,
            pv_clean=pv_clean,
            accrued_interest=accrued,
            fee_leg_pv=fee_pv,
            contingent_leg_pv=cont_pv,
            cs01=cs01,
            dv01=dv01,
            par_spread=par_spread,
            risky_annuity=ra,
        )

    def _compute_cs01(
        self,
        value_date: Date,
        accrual_mode: AccrualOnDefault,
        bump_size: float = 0.0001,  # 1bp
    ) -> float:
        """
        Compute CS01 (credit spread sensitivity).

        CS01 is the change in PV for a 1bp parallel shift in credit spreads.
        """
        # Bump hazard rates up
        original_rates = self.credit_curve._values.copy()

        # Calculate bumped survival at each time
        # Bumping hazard rate by bump_size means survival falls by exp(-bump * t)
        bumped_rates = original_rates + bump_size
        self.credit_curve._values = bumped_rates

        # Recalculate PV
        fee_pv_up = fee_leg_pv(
            value_date, self.schedule, self.contract.coupon_rate,
            self.discount_curve, self.credit_curve,
            self.contract.notional, accrual_mode,
        )
        cont_pv_up = contingent_leg_pv(
            value_date, self.contract.maturity_date,
            self.discount_curve, self.credit_curve,
            self.contract.recovery_rate, self.contract.notional,
        )

        if self.contract.is_buy_protection:
            pv_up = cont_pv_up - fee_pv_up
        else:
            pv_up = fee_pv_up - cont_pv_up

        # Restore original rates
        self.credit_curve._values = original_rates

        # Calculate original PV
        fee_pv = fee_leg_pv(
            value_date, self.schedule, self.contract.coupon_rate,
            self.discount_curve, self.credit_curve,
            self.contract.notional, accrual_mode,
        )
        cont_pv = contingent_leg_pv(
            value_date, self.contract.maturity_date,
            self.discount_curve, self.credit_curve,
            self.contract.recovery_rate, self.contract.notional,
        )

        if self.contract.is_buy_protection:
            pv_base = cont_pv - fee_pv
        else:
            pv_base = fee_pv - cont_pv

        return pv_up - pv_base

    def _compute_dv01(
        self,
        value_date: Date,
        accrual_mode: AccrualOnDefault,
        bump_size: float = 0.0001,  # 1bp
    ) -> float:
        """
        Compute DV01 (interest rate sensitivity).

        DV01 is the change in PV for a 1bp parallel shift in interest rates.
        """
        # Bump zero rates up
        original_rates = self.discount_curve._values.copy()
        bumped_rates = original_rates + bump_size
        self.discount_curve._values = bumped_rates

        # Recalculate PV
        fee_pv_up = fee_leg_pv(
            value_date, self.schedule, self.contract.coupon_rate,
            self.discount_curve, self.credit_curve,
            self.contract.notional, accrual_mode,
        )
        cont_pv_up = contingent_leg_pv(
            value_date, self.contract.maturity_date,
            self.discount_curve, self.credit_curve,
            self.contract.recovery_rate, self.contract.notional,
        )

        if self.contract.is_buy_protection:
            pv_up = cont_pv_up - fee_pv_up
        else:
            pv_up = fee_pv_up - cont_pv_up

        # Restore original rates
        self.discount_curve._values = original_rates

        # Calculate original PV
        fee_pv = fee_leg_pv(
            value_date, self.schedule, self.contract.coupon_rate,
            self.discount_curve, self.credit_curve,
            self.contract.notional, accrual_mode,
        )
        cont_pv = contingent_leg_pv(
            value_date, self.contract.maturity_date,
            self.discount_curve, self.credit_curve,
            self.contract.recovery_rate, self.contract.notional,
        )

        if self.contract.is_buy_protection:
            pv_base = cont_pv - fee_pv
        else:
            pv_base = fee_pv - cont_pv

        return pv_up - pv_base
