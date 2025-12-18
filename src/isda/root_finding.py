"""
Root finding algorithms for curve bootstrapping.

Implements Brent's method which combines bisection with inverse quadratic
interpolation for fast convergence.
"""

from collections.abc import Callable

from .exceptions import ConvergenceError


def brent(
    f: Callable[[float], float],
    a: float,
    b: float,
    tol: float = 1e-12,
    max_iter: int = 100,
) -> float:
    """
    Find a root of f using Brent's method.

    Brent's method combines bisection, secant method, and inverse quadratic
    interpolation for guaranteed convergence with superlinear speed.

    Args:
        f: Function to find root of
        a: Lower bound of search interval (f(a) and f(b) must have opposite signs)
        b: Upper bound of search interval
        tol: Tolerance for convergence
        max_iter: Maximum number of iterations

    Returns
        x such that f(x) ≈ 0

    Raises
        ConvergenceError: If f(a) and f(b) have the same sign, or max_iter exceeded
    """
    fa = f(a)
    fb = f(b)

    if fa * fb > 0:
        raise ConvergenceError(
            f'Function values at bounds must have opposite signs: '
            f'f({a})={fa}, f({b})={fb}'
        )

    if abs(fa) < abs(fb):
        a, b = b, a
        fa, fb = fb, fa

    c = a
    fc = fa
    mflag = True
    d = 0.0

    for _ in range(max_iter):
        if abs(fb) < tol:
            return b

        if abs(b - a) < tol:
            return b

        # Inverse quadratic interpolation
        if fc not in {fa, fb}:
            s = (
                a * fb * fc / ((fa - fb) * (fa - fc))
                + b * fa * fc / ((fb - fa) * (fb - fc))
                + c * fa * fb / ((fc - fa) * (fc - fb))
            )
        else:
            # Secant method
            s = b - fb * (b - a) / (fb - fa)

        # Conditions for accepting s
        cond1 = not ((3 * a + b) / 4 < s < b or b < s < (3 * a + b) / 4)
        cond2 = mflag and abs(s - b) >= abs(b - c) / 2
        cond3 = not mflag and abs(s - b) >= abs(c - d) / 2
        cond4 = mflag and abs(b - c) < tol
        cond5 = not mflag and abs(c - d) < tol

        if cond1 or cond2 or cond3 or cond4 or cond5:
            # Bisection
            s = (a + b) / 2
            mflag = True
        else:
            mflag = False

        fs = f(s)
        d = c
        c = b
        fc = fb

        if fa * fs < 0:
            b = s
            fb = fs
        else:
            a = s
            fa = fs

        if abs(fa) < abs(fb):
            a, b = b, a
            fa, fb = fb, fa

    raise ConvergenceError(f"Brent's method did not converge in {max_iter} iterations")


def newton_raphson(
    f: Callable[[float], float],
    df: Callable[[float], float],
    x0: float,
    tol: float = 1e-12,
    max_iter: int = 50,
) -> float:
    """
    Find a root using Newton-Raphson method.

    Args:
        f: Function to find root of
        df: Derivative of f
        x0: Initial guess
        tol: Tolerance for convergence
        max_iter: Maximum iterations

    Returns
        x such that f(x) ≈ 0
    """
    x = x0

    for _ in range(max_iter):
        fx = f(x)
        if abs(fx) < tol:
            return x

        dfx = df(x)
        if abs(dfx) < 1e-14:
            raise ConvergenceError('Newton-Raphson: derivative too small')

        x -= fx / dfx

    raise ConvergenceError(f'Newton-Raphson did not converge in {max_iter} iterations')


def secant(
    f: Callable[[float], float],
    x0: float,
    x1: float,
    tol: float = 1e-12,
    max_iter: int = 50,
) -> float:
    """
    Find a root using the secant method.

    Args:
        f: Function to find root of
        x0: First initial guess
        x1: Second initial guess
        tol: Tolerance for convergence
        max_iter: Maximum iterations

    Returns
        x such that f(x) ≈ 0
    """
    f0 = f(x0)
    f1 = f(x1)

    for _ in range(max_iter):
        if abs(f1) < tol:
            return x1

        if abs(f1 - f0) < 1e-14:
            raise ConvergenceError('Secant method: function values too close')

        x2 = x1 - f1 * (x1 - x0) / (f1 - f0)
        x0, x1 = x1, x2
        f0, f1 = f1, f(x2)

    raise ConvergenceError(f'Secant method did not converge in {max_iter} iterations')


def bisection(
    f: Callable[[float], float],
    a: float,
    b: float,
    tol: float = 1e-12,
    max_iter: int = 100,
) -> float:
    """
    Find a root using the bisection method.

    Simple but guaranteed to converge if f(a) and f(b) have opposite signs.

    Args:
        f: Function to find root of
        a: Lower bound
        b: Upper bound
        tol: Tolerance
        max_iter: Maximum iterations

    Returns
        x such that f(x) ≈ 0
    """
    fa = f(a)
    fb = f(b)

    if fa * fb > 0:
        raise ConvergenceError(
            f'Function values at bounds must have opposite signs: '
            f'f({a})={fa}, f({b})={fb}'
        )

    for _ in range(max_iter):
        mid = (a + b) / 2
        fmid = f(mid)

        if abs(fmid) < tol or abs(b - a) < tol:
            return mid

        if fa * fmid < 0:
            b = mid
            fb = fmid
        else:
            a = mid
            fa = fmid

    raise ConvergenceError(f'Bisection did not converge in {max_iter} iterations')


def find_root(
    f: Callable[[float], float],
    a: float,
    b: float,
    tol: float = 1e-12,
    max_iter: int = 100,
    method: str = 'brent',
) -> float:
    """
    Find a root of f in [a, b].

    Args:
        f: Function to find root of
        a: Lower bound
        b: Upper bound
        tol: Tolerance
        max_iter: Maximum iterations
        method: 'brent' or 'bisection'

    Returns
        x such that f(x) ≈ 0
    """
    if method == 'brent':
        return brent(f, a, b, tol, max_iter)
    elif method == 'bisection':
        return bisection(f, a, b, tol, max_iter)
    else:
        raise ValueError(f'Unknown root finding method: {method}')
