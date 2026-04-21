"""Singular-point detection via Jacobian-rank (surface) and gradient (implicit)."""

from __future__ import annotations

import numpy as np
import sympy as sp
from sympy.abc import phi, t, theta, x, y, z

from sheaf import Curve, Implicit, Surface
from sheaf.numeric import compiled, gradient_zeros, is_singular, singular_points
from sheaf.numeric.compiler import CompiledCurve, CompiledSurface

# ---------------------------------------------------------------------------
# Surface: rank-deficient Jacobian
# ---------------------------------------------------------------------------


def test_explicit_surface_has_full_rank_everywhere() -> None:
    """z = f(x,y) promoted to (x,y) -> (x,y,f) always has rank-2 Jacobian:
    the (x,y) block alone is the 2x2 identity."""
    monkey = Surface(z=x**3 - 3 * x * y**2, x=(-1, 1), y=(-1, 1))
    c = compiled(monkey)
    assert isinstance(c, CompiledSurface)
    pts = singular_points(c, n=32)
    assert pts.shape[0] == 0


def test_parametric_sphere_has_two_polar_singularities() -> None:
    """(sin φ cos θ, sin φ sin θ, cos φ): Jacobian rank drops at φ=0 and φ=π."""
    sphere = Surface(
        (sp.sin(phi) * sp.cos(theta), sp.sin(phi) * sp.sin(theta), sp.cos(phi)),
        phi=(0.0, float(sp.pi)),
        theta=(0.0, float(2 * sp.pi)),
    )
    c = compiled(sphere)
    # params order = alphabetical: (phi, theta) — so pts columns are (phi, theta)
    pts = singular_points(c, n=64, atol=1e-8)
    # Two clusters, one near phi=0, one near phi=pi
    assert pts.shape[0] == 2
    phis = np.sort(pts[:, 0])
    assert abs(phis[0] - 0.0) < 0.1
    assert abs(phis[1] - float(sp.pi)) < 0.1


def test_is_singular_pointwise_sphere_pole() -> None:
    sphere = Surface(
        (sp.sin(phi) * sp.cos(theta), sp.sin(phi) * sp.sin(theta), sp.cos(phi)),
        phi=(0.0, float(sp.pi)),
        theta=(0.0, float(2 * sp.pi)),
    )
    c = compiled(sphere)
    # args order matches params order = (phi, theta)
    assert is_singular(c, 0.0, 1.3)  # north pole: phi=0
    assert is_singular(c, float(sp.pi), 2.1)  # south pole: phi=pi
    assert not is_singular(c, float(sp.pi / 2), 0.0)  # equator: full rank


# ---------------------------------------------------------------------------
# Curve: zero tangent (cusp)
# ---------------------------------------------------------------------------


def test_curve_cusp_detected_by_zero_tangent() -> None:
    """(t², t³, 0): tangent = (2t, 3t², 0) vanishes at t=0 (a cusp)."""
    cusp = Curve((t**2, t**3, sp.Integer(0)), t=(-1.0, 1.0))
    c = compiled(cusp)
    assert isinstance(c, CompiledCurve)
    assert is_singular(c, 0.0)
    assert not is_singular(c, 0.5)


# ---------------------------------------------------------------------------
# Implicit: gradient zeros on the surface
# ---------------------------------------------------------------------------


def test_cone_implicit_has_apex_singularity() -> None:
    """x² + y² - z² = 0: gradient (2x, 2y, -2z) vanishes at origin, and F(0)=0."""
    cone = Implicit(x**2 + y**2 - z**2)
    c = compiled(cone)
    pts = gradient_zeros(c, bbox=((-1, 1), (-1, 1), (-1, 1)), n=33)
    assert pts.shape[0] == 1
    assert np.allclose(pts[0], [0.0, 0.0, 0.0], atol=1e-10)


def test_sphere_implicit_has_no_singularities() -> None:
    """∇F = (2x, 2y, 2z) vanishes only at origin, which is not on the unit sphere."""
    sphere = Implicit(x**2 + y**2 + z**2 - 1)
    c = compiled(sphere)
    pts = gradient_zeros(c, bbox=((-1.2, 1.2), (-1.2, 1.2), (-1.2, 1.2)), n=25)
    assert pts.shape[0] == 0
