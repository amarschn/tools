"""Small statistical special functions used by the reliability calculators.

Kept dependency-free so the module runs unchanged inside Pyodide. The
implementations follow standard references:

* Regularized incomplete gamma: Press et al., Numerical Recipes 3rd ed., 6.2.
* Normal quantile: Acklam's rational approximation, refined with one Halley
  step against ``math.erf``.
* Chi-squared quantile: bracketed bisection on the chi-squared CDF, which is
  the regularized incomplete gamma function.
"""

from __future__ import annotations

import math
from typing import Callable

_SQRT2 = math.sqrt(2.0)
_SQRT2PI = math.sqrt(2.0 * math.pi)
_TINY = 1e-300


def normal_pdf(z: float) -> float:
    """Standard normal probability density at ``z``."""
    return math.exp(-0.5 * z * z) / _SQRT2PI


def normal_cdf(z: float) -> float:
    """Standard normal cumulative distribution at ``z``."""
    return 0.5 * (1.0 + math.erf(z / _SQRT2))


_ACKLAM_A = (
    -3.969683028665376e01,
    2.209460984245205e02,
    -2.759285104469687e02,
    1.383577518672690e02,
    -3.066479806614716e01,
    2.506628277459239e00,
)
_ACKLAM_B = (
    -5.447609879822406e01,
    1.615858368580409e02,
    -1.556989798598866e02,
    6.680131188771972e01,
    -1.328068155288572e01,
)
_ACKLAM_C = (
    -7.784894002430293e-03,
    -3.223964580411365e-01,
    -2.400758277161838e00,
    -2.549732539343734e00,
    4.374664141464968e00,
    2.938163982698783e00,
)
_ACKLAM_D = (
    7.784695709041462e-03,
    3.224671290700398e-01,
    2.445134137142996e00,
    3.754408661907416e00,
)


def normal_quantile(p: float) -> float:
    """Inverse standard normal CDF: the ``z`` with ``normal_cdf(z) == p``."""
    if not 0.0 < p < 1.0:
        raise ValueError("Probability must be strictly between 0 and 1.")

    p_low = 0.02425
    if p < p_low:
        q = math.sqrt(-2.0 * math.log(p))
        z = (
            ((((_ACKLAM_C[0] * q + _ACKLAM_C[1]) * q + _ACKLAM_C[2]) * q + _ACKLAM_C[3]) * q + _ACKLAM_C[4]) * q
            + _ACKLAM_C[5]
        ) / ((((_ACKLAM_D[0] * q + _ACKLAM_D[1]) * q + _ACKLAM_D[2]) * q + _ACKLAM_D[3]) * q + 1.0)
    elif p <= 1.0 - p_low:
        q = p - 0.5
        r = q * q
        z = (
            (((((_ACKLAM_A[0] * r + _ACKLAM_A[1]) * r + _ACKLAM_A[2]) * r + _ACKLAM_A[3]) * r + _ACKLAM_A[4]) * r + _ACKLAM_A[5])
            * q
        ) / (((((_ACKLAM_B[0] * r + _ACKLAM_B[1]) * r + _ACKLAM_B[2]) * r + _ACKLAM_B[3]) * r + _ACKLAM_B[4]) * r + 1.0)
    else:
        q = math.sqrt(-2.0 * math.log(1.0 - p))
        z = -(
            ((((_ACKLAM_C[0] * q + _ACKLAM_C[1]) * q + _ACKLAM_C[2]) * q + _ACKLAM_C[3]) * q + _ACKLAM_C[4]) * q
            + _ACKLAM_C[5]
        ) / ((((_ACKLAM_D[0] * q + _ACKLAM_D[1]) * q + _ACKLAM_D[2]) * q + _ACKLAM_D[3]) * q + 1.0)

    # One Halley refinement against the exact CDF.
    error = normal_cdf(z) - p
    if 0.0 < normal_pdf(z):
        u = error / normal_pdf(z)
        z -= u / (1.0 + 0.5 * z * u)
    return z


def _gamma_p_series(a: float, x: float) -> float:
    ap = a
    total = 1.0 / a
    delta = total
    for _ in range(2000):
        ap += 1.0
        delta *= x / ap
        total += delta
        if abs(delta) < abs(total) * 1e-16:
            break
    return total * math.exp(-x + a * math.log(x) - math.lgamma(a))


def _gamma_q_continued_fraction(a: float, x: float) -> float:
    b = x + 1.0 - a
    c = 1.0 / _TINY
    d = 1.0 / b
    h = d
    for i in range(1, 2000):
        an = -i * (i - a)
        b += 2.0
        d = an * d + b
        if abs(d) < _TINY:
            d = _TINY
        c = b + an / c
        if abs(c) < _TINY:
            c = _TINY
        d = 1.0 / d
        delta = d * c
        h *= delta
        if abs(delta - 1.0) < 1e-16:
            break
    return math.exp(-x + a * math.log(x) - math.lgamma(a)) * h


def gamma_p(a: float, x: float) -> float:
    """Regularized lower incomplete gamma function P(a, x)."""
    if a <= 0.0:
        raise ValueError("Shape parameter a must be positive.")
    if x < 0.0:
        raise ValueError("Argument x must be non-negative.")
    if x == 0.0:
        return 0.0
    if x < a + 1.0:
        return _gamma_p_series(a, x)
    return 1.0 - _gamma_q_continued_fraction(a, x)


def chi2_cdf(x: float, dof: float) -> float:
    """Chi-squared CDF with ``dof`` degrees of freedom."""
    if dof <= 0:
        raise ValueError("Degrees of freedom must be positive.")
    if x <= 0.0:
        return 0.0
    return gamma_p(0.5 * dof, 0.5 * x)


def chi2_quantile(p: float, dof: float) -> float:
    """Chi-squared quantile: the ``x`` with ``chi2_cdf(x, dof) == p``.

    Uses bracketed bisection, which is slower than a Newton iteration but
    cannot diverge in the far tails where the reliability bounds live.
    """
    if not 0.0 < p < 1.0:
        raise ValueError("Probability must be strictly between 0 and 1.")
    if dof <= 0:
        raise ValueError("Degrees of freedom must be positive.")

    lo = 0.0
    hi = max(dof + 10.0, 1.0)
    for _ in range(200):
        if chi2_cdf(hi, dof) >= p:
            break
        hi *= 2.0
    else:  # pragma: no cover - unreachable for finite p < 1
        raise ArithmeticError("Failed to bracket the chi-squared quantile.")

    for _ in range(200):
        mid = 0.5 * (lo + hi)
        if chi2_cdf(mid, dof) < p:
            lo = mid
        else:
            hi = mid
        if hi - lo < 1e-12 * max(1.0, hi):
            break
    return 0.5 * (lo + hi)


def nelder_mead(
    objective: Callable[[list[float]], float],
    start: list[float],
    step: list[float] | None = None,
    max_iterations: int = 2000,
    tolerance: float = 1e-10,
) -> list[float]:
    """Minimize ``objective`` over a small parameter vector.

    A plain Nelder-Mead simplex search. Used for the two-parameter maximum
    likelihood fits where no closed form exists (censored lognormal data).
    """
    n = len(start)
    if n == 0:
        raise ValueError("Starting point must have at least one dimension.")
    if step is None:
        step = [0.1 if s == 0.0 else 0.1 * abs(s) for s in start]

    simplex = [list(start)]
    for i in range(n):
        point = list(start)
        point[i] += step[i]
        simplex.append(point)
    values = [objective(p) for p in simplex]

    for _ in range(max_iterations):
        order = sorted(range(n + 1), key=lambda i: values[i])
        simplex = [simplex[i] for i in order]
        values = [values[i] for i in order]

        if abs(values[-1] - values[0]) <= tolerance * (abs(values[0]) + tolerance):
            break

        centroid = [sum(p[i] for p in simplex[:-1]) / n for i in range(n)]
        worst = simplex[-1]

        reflected = [centroid[i] + 1.0 * (centroid[i] - worst[i]) for i in range(n)]
        f_reflected = objective(reflected)

        if f_reflected < values[0]:
            expanded = [centroid[i] + 2.0 * (centroid[i] - worst[i]) for i in range(n)]
            f_expanded = objective(expanded)
            if f_expanded < f_reflected:
                simplex[-1], values[-1] = expanded, f_expanded
            else:
                simplex[-1], values[-1] = reflected, f_reflected
        elif f_reflected < values[-2]:
            simplex[-1], values[-1] = reflected, f_reflected
        else:
            contracted = [centroid[i] + 0.5 * (worst[i] - centroid[i]) for i in range(n)]
            f_contracted = objective(contracted)
            if f_contracted < values[-1]:
                simplex[-1], values[-1] = contracted, f_contracted
            else:
                best = simplex[0]
                for j in range(1, n + 1):
                    simplex[j] = [best[i] + 0.5 * (simplex[j][i] - best[i]) for i in range(n)]
                    values[j] = objective(simplex[j])

    best_index = min(range(n + 1), key=lambda i: values[i])
    return simplex[best_index]


def invert_2x2(matrix: list[list[float]]) -> list[list[float]]:
    """Invert a 2x2 matrix. Raises if the matrix is singular."""
    (a, b), (c, d) = matrix[0], matrix[1]
    det = a * d - b * c
    if det == 0.0 or not math.isfinite(det):
        raise ArithmeticError("Matrix is singular; cannot invert.")
    return [[d / det, -b / det], [-c / det, a / det]]
