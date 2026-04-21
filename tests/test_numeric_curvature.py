"""Hessian-eigenvalue critical-point classification — Month 2 W6 validation.

Every test targets an analytically known critical-point signature, not a
numerical fingerprint of the grid sweep:

* ``z = x² + y²``          → one minimum at origin,  eigs ≈ (2, 2)
* ``z = −(x² + y²)``       → one maximum at origin,  eigs ≈ (−2, −2)
* ``z = x² − y²``          → one saddle at origin,   eigs ≈ (−2, 2)
* ``z = x³ − 3xy²``        → one degenerate point at origin (monkey saddle)
* ``z = 2x + 3y``          → no critical points
* parametric sphere        → raises NotImplementedError
"""

from __future__ import annotations

import math

import pytest
import sympy as sp
from sympy.abc import phi, theta, x, y

from sheaf import Surface
from sheaf.numeric import (
    CriticalPoint,
    classify_critical_points,
    compiled,
)


def _only(cps: list[CriticalPoint]) -> CriticalPoint:
    assert len(cps) == 1, f"expected exactly one critical point, got {len(cps)}"
    return cps[0]


# ---------------------------------------------------------------------------
# Non-degenerate classification: min / max / saddle
# ---------------------------------------------------------------------------


def test_paraboloid_has_one_minimum_at_origin() -> None:
    """``z = x² + y²``: H = 2I, both eigenvalues +2, minimum at origin."""
    bowl = Surface(z=x**2 + y**2, x=(-1, 1), y=(-1, 1))
    cps = classify_critical_points(compiled(bowl))
    cp = _only(cps)
    assert cp.kind == "minimum"
    assert math.isclose(cp.param[0], 0.0, abs_tol=1e-6)
    assert math.isclose(cp.param[1], 0.0, abs_tol=1e-6)
    assert math.isclose(cp.point[2], 0.0, abs_tol=1e-6)
    assert all(math.isclose(e, 2.0, abs_tol=1e-6) for e in cp.eigenvalues)


def test_inverted_paraboloid_has_one_maximum_at_origin() -> None:
    """``z = -(x² + y²)``: H = −2I, both eigenvalues −2, maximum at origin."""
    hill = Surface(z=-(x**2 + y**2), x=(-1, 1), y=(-1, 1))
    cp = _only(classify_critical_points(compiled(hill)))
    assert cp.kind == "maximum"
    assert all(math.isclose(e, -2.0, abs_tol=1e-6) for e in cp.eigenvalues)


def test_hyperbolic_paraboloid_is_classified_saddle() -> None:
    """``z = x² − y²``: Hessian diag(2, −2), opposite signs → saddle."""
    saddle = Surface(z=x**2 - y**2, x=(-1, 1), y=(-1, 1))
    cp = _only(classify_critical_points(compiled(saddle)))
    assert cp.kind == "saddle"
    # Ascending order: smaller first.
    assert math.isclose(cp.eigenvalues[0], -2.0, abs_tol=1e-6)
    assert math.isclose(cp.eigenvalues[1], 2.0, abs_tol=1e-6)


# ---------------------------------------------------------------------------
# Degenerate Hessian: monkey saddle
# ---------------------------------------------------------------------------


def test_monkey_saddle_origin_is_degenerate() -> None:
    """Monkey saddle ``z = x³ − 3xy²`` has Hessian = 0 at the origin.
    The classifier must fall through to ``"degenerate"`` rather than guess."""
    monkey = Surface(z=x**3 - 3 * x * y**2, x=(-1, 1), y=(-1, 1))
    cps = classify_critical_points(compiled(monkey))
    # There is exactly one critical point (origin) for the monkey saddle.
    cp = _only(cps)
    assert cp.kind == "degenerate"
    assert math.isclose(cp.param[0], 0.0, abs_tol=1e-6)
    assert math.isclose(cp.param[1], 0.0, abs_tol=1e-6)


# ---------------------------------------------------------------------------
# No critical points
# ---------------------------------------------------------------------------


def test_tilted_plane_has_no_critical_points() -> None:
    """``z = 2x + 3y``: gradient is constant (2, 3) ≠ 0, no critical points."""
    plane = Surface(z=2 * x + 3 * y, x=(-1, 1), y=(-1, 1))
    assert classify_critical_points(compiled(plane)) == []


# ---------------------------------------------------------------------------
# Parametric surfaces: not yet supported
# ---------------------------------------------------------------------------


def test_parametric_sphere_raises_not_implemented() -> None:
    """Parametric surfaces demand intrinsic-curvature analysis (W10)."""
    sphere = Surface(
        (sp.sin(phi) * sp.cos(theta), sp.sin(phi) * sp.sin(theta), sp.cos(phi)),
        phi=(0.0, float(sp.pi)),
        theta=(0.0, float(2 * sp.pi)),
    )
    with pytest.raises(NotImplementedError, match="parametric"):
        classify_critical_points(compiled(sphere))
