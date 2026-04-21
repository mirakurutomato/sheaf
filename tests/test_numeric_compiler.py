"""Compilation: DSL → NumPy-backed callables."""

from __future__ import annotations

import numpy as np
import sympy as sp
from sympy.abc import phi, t, theta, x, y, z

from sheaf import Curve, Implicit, Surface
from sheaf.numeric import (
    CompiledCurve,
    CompiledImplicit,
    CompiledSurface,
    compiled,
)

# ---------------------------------------------------------------------------
# Explicit surface
# ---------------------------------------------------------------------------


def test_explicit_surface_compiles_and_samples() -> None:
    s = Surface(z=x * y)
    c = compiled(s)
    assert isinstance(c, CompiledSurface)
    X, Y, Z = c.sample(n=11)
    assert X.shape == Y.shape == Z.shape == (11, 11)
    # Spot check: z = x * y at (0.5, 0.5)
    i = np.argmin(np.abs(X[:, 0] - 0.5))
    j = np.argmin(np.abs(Y[0, :] - 0.5))
    assert abs(Z[i, j] - (X[i, j] * Y[i, j])) < 1e-12


def test_explicit_surface_respects_user_domain() -> None:
    s = Surface(z=x**2 + y**2, x=(-3.0, 3.0), y=(-2.0, 2.0))
    c = compiled(s)
    X, Y, _ = c.sample(n=7)
    assert X.min() == -3.0 and X.max() == 3.0
    assert Y.min() == -2.0 and Y.max() == 2.0


# ---------------------------------------------------------------------------
# Parametric surface
# ---------------------------------------------------------------------------


def test_parametric_sphere_samples_on_unit_sphere() -> None:
    s = Surface(
        (sp.sin(phi) * sp.cos(theta), sp.sin(phi) * sp.sin(theta), sp.cos(phi)),
        phi=(0.0, float(sp.pi)),
        theta=(0.0, float(2 * sp.pi)),
    )
    c = compiled(s)
    X, Y, Z = c.sample(n=32)
    r = np.sqrt(X**2 + Y**2 + Z**2)
    assert np.allclose(r, 1.0, atol=1e-12)


def test_parametric_mobius_compiles() -> None:
    from sympy.abc import u, v

    mobius = Surface(
        (
            (1 + v / 2 * sp.cos(u / 2)) * sp.cos(u),
            (1 + v / 2 * sp.cos(u / 2)) * sp.sin(u),
            v / 2 * sp.sin(u / 2),
        ),
        u=(0.0, float(2 * sp.pi)),
        v=(-1.0, 1.0),
    )
    c = compiled(mobius)
    assert isinstance(c, CompiledSurface)
    X, Y, Z = c.sample(n=16)
    assert X.shape == (16, 16)
    assert np.isfinite(X).all() and np.isfinite(Y).all() and np.isfinite(Z).all()


# ---------------------------------------------------------------------------
# Curve
# ---------------------------------------------------------------------------


def test_curve_helix_samples_on_unit_cylinder() -> None:
    helix = Curve((sp.cos(t), sp.sin(t), t / 4), t=(0.0, float(4 * sp.pi)))
    c = compiled(helix)
    assert isinstance(c, CompiledCurve)
    pts = c.sample(n=64)
    assert pts.shape == (64, 3)
    r2 = pts[:, 0] ** 2 + pts[:, 1] ** 2
    assert np.allclose(r2, 1.0, atol=1e-12)


# ---------------------------------------------------------------------------
# Implicit
# ---------------------------------------------------------------------------


def test_implicit_sphere_evaluate_and_gradient() -> None:
    sphere = Implicit(x**2 + y**2 + z**2 - 1)
    c = compiled(sphere)
    assert isinstance(c, CompiledImplicit)
    # On-surface point
    f_value = c.evaluate(np.array(1.0), np.array(0.0), np.array(0.0))
    assert float(f_value) == 0.0
    # Gradient at (1, 0, 0) = (2, 0, 0)
    g = c.gradient_fn(np.array(1.0), np.array(0.0), np.array(0.0))
    assert g.shape[-2:] == (3, 1)
    assert np.allclose(g.reshape(3), [2.0, 0.0, 0.0])


def test_implicit_vectorised_over_meshgrid() -> None:
    sphere = Implicit(x**2 + y**2 + z**2 - 1)
    c = compiled(sphere)
    X, Y, Z = np.meshgrid(
        np.linspace(-1, 1, 5),
        np.linspace(-1, 1, 5),
        np.linspace(-1, 1, 5),
        indexing="ij",
    )
    f = c.evaluate(X, Y, Z)
    assert f.shape == X.shape
    # Expected equation: f = x²+y²+z² - 1
    assert np.allclose(f, X**2 + Y**2 + Z**2 - 1)


def test_implicit_rejects_variables_outside_xyz() -> None:
    import pytest
    from sympy.abc import a

    with pytest.raises(ValueError, match="subset"):
        compiled(Implicit(a**2 + x**2 - 1))


def test_implicit_csg_raises_for_now() -> None:
    import pytest

    sphere = Implicit(x**2 + y**2 + z**2 - 1)
    cube = Implicit(x**4 + y**4 + z**4 - 1)
    with pytest.raises(NotImplementedError, match="CSG"):
        compiled(sphere & cube)
