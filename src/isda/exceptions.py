"""
Custom exceptions for the ISDA CDS pricer.
"""


class CDSError(Exception):
    """Base exception for all CDS pricer errors."""


class CurveError(CDSError):
    """Error related to curve construction or interpolation."""


class BootstrapError(CurveError):
    """Error during curve bootstrapping."""


class InterpolationError(CurveError):
    """Error during curve interpolation."""


class ConvergenceError(CDSError):
    """Root finding failed to converge."""
