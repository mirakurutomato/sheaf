"""Jacobian-rank analysis → parameter-space singular set.

A singular point of a parametric surface (u, v) → (X, Y, Z) is where the
3×2 Jacobian J drops below rank 2 — equivalently, its smallest singular
value hits zero.  The singular *set* is generally a 0- or 1-dimensional
submanifold of parameter space (isolated cusps vs. whole meridians); this
module returns one representative per connected component, detected via
a grid SVD sweep followed by `scipy.ndimage.label`.

For an implicit surface {F = 0}, singular points additionally require
F = 0 (the ∇F = 0 locus of a sphere does not lie on it, for example).

Grid-based detection is deliberately backend-first: it always works, even
for expressions where SymPy's `solve` chokes.  Symbolic refinement lands
in Month 1 W3 alongside the adaptive mesh engine.
"""

from __future__ import annotations

from typing import cast

import numpy as np
from scipy import ndimage

from sheaf.numeric.compiler import (
    CompiledCurve,
    CompiledImplicit,
    CompiledSurface,
)

# ---------------------------------------------------------------------------
# Surface singularities: rank-deficient Jacobian
# ---------------------------------------------------------------------------


def singular_points(
    compiled: CompiledSurface,
    *,
    n: int = 64,
    atol: float = 1e-8,
) -> np.ndarray:
    """Return parameter-space points where the surface Jacobian has rank < 2.

    Connected components of the singular mask are collapsed to their centroid,
    so a whole meridian of poles counts as one point.

    Parameters
    ----------
    n:
        Grid resolution per axis (total N² samples).
    atol:
        Tolerance on the smallest singular value of the 3×2 Jacobian.

    Returns
    -------
    ndarray of shape (K, 2) with (u, v) coordinates of singular points.
    """
    uu, vv = compiled.parameter_grid(n)
    J = compiled.jacobian_fn(uu, vv)  # shape (n, n, 3, 2)
    sv_small = _smallest_singular_value(J)  # shape (n, n)
    mask = sv_small < atol
    return _component_centroids_2d(mask, uu, vv)


def is_singular(
    compiled: CompiledSurface | CompiledCurve,
    *params: float,
    atol: float = 1e-8,
) -> bool:
    """Pointwise test: does the Jacobian lose rank at the given parameter(s)?"""
    if isinstance(compiled, CompiledSurface):
        if len(params) != 2:
            raise ValueError("CompiledSurface.is_singular expects (u, v)")
        J = compiled.jacobian_fn(*params)  # shape (3, 2)
        sv = np.linalg.svd(J, compute_uv=False)
        return bool(sv.min() < atol)
    if isinstance(compiled, CompiledCurve):
        if len(params) != 1:
            raise ValueError("CompiledCurve.is_singular expects (t,)")
        tan = compiled.tangent_fn(*params)  # shape (3, 1)
        return bool(np.linalg.norm(tan) < atol)
    raise TypeError(f"is_singular not defined for {type(compiled).__name__}")


# ---------------------------------------------------------------------------
# Implicit singularities: ∇F = 0 on the zero set F = 0
# ---------------------------------------------------------------------------


def gradient_zeros(
    compiled: CompiledImplicit,
    bbox: tuple[tuple[float, float], tuple[float, float], tuple[float, float]],
    *,
    n: int = 48,
    value_atol: float = 1e-2,
    grad_atol: float = 1e-6,
) -> np.ndarray:
    """Return (x, y, z) points where F ≈ 0 and ∇F ≈ 0.

    The `value_atol` is intentionally looser than `grad_atol` because the
    zero set is sampled on a grid: a true surface point is rarely exactly
    on a grid node.  Tighten both via a local refinement pass in W3.
    """
    (x0, x1), (y0, y1), (z0, z1) = bbox
    xs = np.linspace(x0, x1, n)
    ys = np.linspace(y0, y1, n)
    zs = np.linspace(z0, z1, n)
    X, Y, Z = np.meshgrid(xs, ys, zs, indexing="ij")
    F = compiled.evaluate(X, Y, Z)
    G = compiled.gradient_fn(X, Y, Z)  # shape (n, n, n, 3, 1)
    if G.shape[-1] == 1:
        G = G[..., 0]
    g_norm = np.linalg.norm(G, axis=-1)  # shape (n, n, n)
    mask = (np.abs(F) < value_atol) & (g_norm < grad_atol)
    return _component_centroids_3d(mask, X, Y, Z)


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _smallest_singular_value(jac: np.ndarray) -> np.ndarray:
    """Return the smallest singular value at every point of a batched 3×2 Jacobian."""
    if jac.shape[-2:] != (3, 2):
        raise ValueError(f"expected trailing shape (3, 2), got {jac.shape}")
    sv = np.linalg.svd(jac, compute_uv=False)  # shape (..., 2)
    return cast(np.ndarray, sv[..., -1])


def _component_centroids_2d(
    mask: np.ndarray, uu: np.ndarray, vv: np.ndarray
) -> np.ndarray:
    """One (u, v) centroid per connected component of a 2D boolean mask.

    Uses 8-connectivity so diagonal grid neighbours are treated as one
    component — important for singular *curves* that pass through the grid
    at oblique angles.
    """
    if not mask.any():
        return np.empty((0, 2), dtype=float)
    structure = np.ones((3, 3), dtype=bool)  # 8-connectivity
    labels, num = ndimage.label(mask, structure=structure)
    reps = np.empty((num, 2), dtype=float)
    for k in range(1, num + 1):
        sel = labels == k
        reps[k - 1, 0] = uu[sel].mean()
        reps[k - 1, 1] = vv[sel].mean()
    return reps


def _component_centroids_3d(
    mask: np.ndarray, X: np.ndarray, Y: np.ndarray, Z: np.ndarray
) -> np.ndarray:
    """One (x, y, z) centroid per connected component of a 3D boolean mask."""
    if not mask.any():
        return np.empty((0, 3), dtype=float)
    structure = np.ones((3, 3, 3), dtype=bool)  # 26-connectivity
    labels, num = ndimage.label(mask, structure=structure)
    reps = np.empty((num, 3), dtype=float)
    for k in range(1, num + 1):
        sel = labels == k
        reps[k - 1, 0] = X[sel].mean()
        reps[k - 1, 1] = Y[sel].mean()
        reps[k - 1, 2] = Z[sel].mean()
    return reps
