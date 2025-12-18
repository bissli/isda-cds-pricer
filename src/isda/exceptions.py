"""
Custom exceptions for the ISDA CDS pricer.
"""


class CDSError(Exception):
    """Base exception for all CDS pricer errors."""


class DateError(CDSError):
    """Error related to date operations."""


class CurveError(CDSError):
    """Error related to curve construction or interpolation."""


class BootstrapError(CurveError):
    """Error during curve bootstrapping."""


class InterpolationError(CurveError):
    """Error during curve interpolation."""


class PricingError(CDSError):
    """Error during CDS pricing."""


class ConvergenceError(CDSError):
    """Root finding failed to converge."""


class CalendarError(CDSError):
    """Error related to calendar/business day operations."""


class TenorError(CDSError):
    """Error parsing or handling tenors."""
