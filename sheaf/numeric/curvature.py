"""Hessian-eigenvalue critical-point classification — Month 2 W6.

For an explicit surface ``z = f(u, v)``, the critical points of the height
field are the natural semantic anchors for lighting: a true local extremum
deserves a warm / cool key light pointing down at it; a saddle deserves a
rim light skimming across it to reveal the crossing curvatures.

Critical points are located by cell-wise sign-change detection on the two
gradient components (a 2-D intermediate-value search — the direct analogue
of :func:`sheaf.numeric.analysis.gradient_zeros` for implicit fields).  At
each centroid the closed-form Hessian is evaluated and its two eigenvalues
classify the point:

* both positive              → ``"minimum"``
* both negative              → ``"maximum"``
* opposite signs             → ``"saddle"``
* ``det H ≈ 0``              → ``"degenerate"``  (monkey saddle, inflection)

Parametric surfaces (sphere, torus, Möbius) do not have a canonical
``f(u, v)`` height field; their critical-point story is an intrinsic-
curvature story (Gauss / mean curvature extremes) that lands with the
vector-material system in W10.  Calling this routine on a parametric
surface raises :class:`NotImplementedError`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np
import sympy as sp
from scipy import ndimage

from sheaf.numeric.compiler import CompiledSurface

CriticalKind = Literal["minimum", "maximum", "saddle", "degenerate"]


@dataclass(frozen=True, slots=True)
class CriticalPoint:
    """A stationary point of ``z = f(u, v)`` with its Hessian classification.

    ``eigenvalues`` are returned in ascending order (the convention of
    :func:`numpy.linalg.eigvalsh`), so ``eigenvalues[0] <= eigenvalues[1]``.
    """

    param: tuple[float, float]
    point: tuple[float, float, float]
    eigenvalues: tuple[float, float]
    kind: CriticalKind


def classify_critical_points(
    surface: CompiledSurface,
    *,
    n: int = 65,
    det_atol: float = 1e-6,
) -> list[CriticalPoint]:
    """Return every critical point of ``z = f(u, v)`` with its Hessian type.

    Parameters
    ----------
    n:
        Grid resolution for sign-change detection — ``n × n`` parameter
        samples, ``(n−1) × (n−1)`` cells.  Must be ≥ 2.
    det_atol:
        Determinant tolerance below which a critical point is flagged
        ``"degenerate"`` rather than classified by eigenvalue sign.

    Raises
    ------
    NotImplementedError
        If ``surface`` is parametric (intrinsic-curvature classification
        lands in W10).
    """
    if not _is_explicit(surface):
        raise NotImplementedError(
            "classify_critical_points restricts to explicit z = f(u, v); "
            "parametric Gauss / mean curvature analysis lands in W10."
        )
    if n < 2:
        raise ValueError(f"n must be >= 2, got {n}")

    u, v = surface.params
    f_expr = surface.exprs_sym[2]

    fu = sp.diff(f_expr, u)
    fv = sp.diff(f_expr, v)
    fuu = sp.diff(fu, u)
    fuv = sp.diff(fu, v)
    fvv = sp.diff(fv, v)

    fu_fn = sp.lambdify((u, v), fu, modules="numpy")
    fv_fn = sp.lambdify((u, v), fv, modules="numpy")
    fuu_fn = sp.lambdify((u, v), fuu, modules="numpy")
    fuv_fn = sp.lambdify((u, v), fuv, modules="numpy")
    fvv_fn = sp.lambdify((u, v), fvv, modules="numpy")
    f_fn = sp.lambdify((u, v), f_expr, modules="numpy")

    uu, vv = surface.parameter_grid(n)
    fu_grid = np.broadcast_to(fu_fn(uu, vv), uu.shape).astype(float)
    fv_grid = np.broadcast_to(fv_fn(uu, vv), uu.shape).astype(float)

    centroids = _gradient_zero_cells(fu_grid, fv_grid, uu, vv)
    if len(centroids) == 0:
        return []

    out: list[CriticalPoint] = []
    for u0, v0 in centroids:
        h_uu = float(fuu_fn(u0, v0))
        h_uv = float(fuv_fn(u0, v0))
        h_vv = float(fvv_fn(u0, v0))
        H = np.array([[h_uu, h_uv], [h_uv, h_vv]], dtype=float)
        eigs = np.linalg.eigvalsh(H)  # ascending, real (symmetric input)
        det = float(eigs[0] * eigs[1])
        if abs(det) < det_atol:
            kind: CriticalKind = "degenerate"
        elif det < 0:
            kind = "saddle"
        elif eigs[0] > 0:
            kind = "minimum"
        else:
            kind = "maximum"
        z0 = float(f_fn(u0, v0))
        out.append(
            CriticalPoint(
                param=(float(u0), float(v0)),
                point=(float(u0), float(v0), z0),
                eigenvalues=(float(eigs[0]), float(eigs[1])),
                kind=kind,
            )
        )
    return out


def _is_explicit(surface: CompiledSurface) -> bool:
    """A surface is explicit when it carries the promoted ``(u, v, f(u,v))`` form."""
    u, v = surface.params
    return surface.exprs_sym[0] == u and surface.exprs_sym[1] == v


def _gradient_zero_cells(
    fu: np.ndarray, fv: np.ndarray, uu: np.ndarray, vv: np.ndarray
) -> np.ndarray:
    """IVT cells: both gradient components straddle zero across the 2×2 corners.

    ``uu``, ``vv`` are the ``(n, n)`` parameter grids; the returned cell
    centroids are in parameter space and average the 4 corner coordinates
    of every cell in the connected component.
    """
    corners_u = np.stack(
        [fu[:-1, :-1], fu[:-1, 1:], fu[1:, :-1], fu[1:, 1:]], axis=0
    )
    corners_v = np.stack(
        [fv[:-1, :-1], fv[:-1, 1:], fv[1:, :-1], fv[1:, 1:]], axis=0
    )
    mask = (
        (corners_u.min(axis=0) <= 0)
        & (corners_u.max(axis=0) >= 0)
        & (corners_v.min(axis=0) <= 0)
        & (corners_v.max(axis=0) >= 0)
    )
    if not mask.any():
        return np.empty((0, 2), dtype=float)

    uu_cells = 0.25 * (uu[:-1, :-1] + uu[:-1, 1:] + uu[1:, :-1] + uu[1:, 1:])
    vv_cells = 0.25 * (vv[:-1, :-1] + vv[:-1, 1:] + vv[1:, :-1] + vv[1:, 1:])
    structure = np.ones((3, 3), dtype=bool)
    labels, num = ndimage.label(mask, structure=structure)
    reps = np.empty((num, 2), dtype=float)
    for k in range(1, num + 1):
        sel = labels == k
        reps[k - 1, 0] = uu_cells[sel].mean()
        reps[k - 1, 1] = vv_cells[sel].mean()
    return reps
