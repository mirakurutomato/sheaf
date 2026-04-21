"""Topology analysis — Month 2 W5 validation.

Every canonical surface has a closed-form topological invariant.  These tests
are written against those invariants directly, not against mesh counts:

* plane / disk          ``χ = 1``,  1 boundary loop,  orientable
* sphere (welded)       ``χ = 2``,  closed,            orientable
* torus (welded)        ``χ = 0``,  closed,            orientable
* Gaussian peak (disk)  ``χ = 1``,  1 boundary loop,  orientable
* two disjoint tris     components = 2
"""

from __future__ import annotations

import numpy as np
import sympy as sp
from sympy.abc import phi, theta, u, v, x, y

from sheaf import Surface
from sheaf.numeric import (
    AdaptiveMesh,
    adaptive_mesh,
    analyze,
    compiled,
    weld_duplicate_vertices,
)

# ---------------------------------------------------------------------------
# Open surfaces — χ = 1, one boundary loop, orientable
# ---------------------------------------------------------------------------


def test_plane_is_open_disk() -> None:
    """A flat square is topologically a closed disk: χ = 1, orientable, 1 boundary."""
    plane = Surface(z=sp.Integer(0) * x + sp.Integer(0) * y, x=(-1, 1), y=(-1, 1))
    mesh = adaptive_mesh(compiled(plane), base_n=4)
    t = analyze(mesh)
    assert t.euler == 1
    assert t.components == 1
    assert t.is_orientable
    assert not t.is_closed
    assert t.is_manifold
    # 4×4 grid: 4·4 = 16 perimeter edges.
    assert len(t.boundary_edges) == 16


def test_gaussian_peak_is_open_disk() -> None:
    """A smooth bump on a square has the same χ=1 topology as the plane."""
    peak = Surface(z=sp.exp(-6 * (x**2 + y**2)), x=(-1, 1), y=(-1, 1))
    mesh = adaptive_mesh(compiled(peak), base_n=4, chord_eps=5e-3, max_depth=4)
    t = analyze(mesh)
    assert t.euler == 1
    assert t.components == 1
    assert t.is_orientable
    assert not t.is_closed
    assert t.is_manifold


# ---------------------------------------------------------------------------
# Closed surfaces — require welding to collapse parametric seams
# ---------------------------------------------------------------------------


def test_sphere_welds_to_chi_equals_two() -> None:
    """Sphere triangulated on a UV grid has 4 boundary chains in parameter
    space (φ=0, φ=π, θ=0, θ=2π).  Welding collapses poles to a single point
    and stitches the θ-seam, leaving the true sphere topology: χ = 2."""
    sphere = Surface(
        (sp.sin(phi) * sp.cos(theta), sp.sin(phi) * sp.sin(theta), sp.cos(phi)),
        phi=(0.0, float(sp.pi)),
        theta=(0.0, float(2 * sp.pi)),
    )
    mesh = adaptive_mesh(compiled(sphere), base_n=8, chord_eps=1e-2, sv_eps=5e-2, max_depth=4)
    welded = weld_duplicate_vertices(mesh, eps=1e-6)
    t = analyze(welded)
    assert t.is_closed, f"sphere should have no boundary, got {len(t.boundary_edges)} edges"
    assert t.is_orientable
    assert t.is_manifold
    assert t.components == 1
    assert t.euler == 2, f"sphere χ = 2, got {t.euler}"


def test_torus_welds_to_chi_equals_zero() -> None:
    """Torus: both u and v are 2π-periodic.  Welding stitches both seams
    ⇒ closed, orientable, χ = 0."""
    R, r = 1.0, 0.35
    torus = Surface(
        (
            (R + r * sp.cos(v)) * sp.cos(u),
            (R + r * sp.cos(v)) * sp.sin(u),
            r * sp.sin(v),
        ),
        u=(0.0, float(2 * sp.pi)),
        v=(0.0, float(2 * sp.pi)),
    )
    mesh = adaptive_mesh(compiled(torus), base_n=12, chord_eps=5e-3, max_depth=3)
    welded = weld_duplicate_vertices(mesh, eps=1e-6)
    t = analyze(welded)
    assert t.is_closed, f"torus should have no boundary, got {len(t.boundary_edges)} edges"
    assert t.is_orientable
    assert t.is_manifold
    assert t.components == 1
    assert t.euler == 0, f"torus χ = 0, got {t.euler}"


# ---------------------------------------------------------------------------
# Components and manifold-ness
# ---------------------------------------------------------------------------


def test_two_disjoint_triangles_have_two_components() -> None:
    """A mesh handed to analyze with two vertex-disjoint triangles is
    correctly flagged as two components."""
    pts = np.array(
        [[0, 0, 0], [1, 0, 0], [0, 1, 0], [5, 5, 0], [6, 5, 0], [5, 6, 0]],
        dtype=np.float64,
    )
    params = np.array([[0, 0], [1, 0], [0, 1], [5, 5], [6, 5], [5, 6]], dtype=np.float64)
    tris = np.array([[0, 1, 2], [3, 4, 5]], dtype=np.int64)
    mesh = AdaptiveMesh(params=params, points=pts, triangles=tris)
    t = analyze(mesh)
    assert t.components == 2
    assert t.is_orientable
    assert t.is_manifold
    # Each triangle contributes 3 boundary edges × 2 components.
    assert len(t.boundary_edges) == 6
    assert t.euler == 2  # two disks: 1 + 1


def test_non_manifold_edge_is_detected() -> None:
    """Three triangles glued along a common edge form a non-manifold T-junction."""
    pts = np.array(
        [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, 1], [-1, 0, 0]],
        dtype=np.float64,
    )
    params = np.zeros((5, 2), dtype=np.float64)
    # All three triangles share edge (0, 1).
    tris = np.array([[0, 1, 2], [0, 1, 3], [0, 1, 4]], dtype=np.int64)
    mesh = AdaptiveMesh(params=params, points=pts, triangles=tris)
    t = analyze(mesh)
    assert not t.is_manifold
    assert len(t.non_manifold_edges) == 1
    assert set(t.non_manifold_edges[0].tolist()) == {0, 1}


# ---------------------------------------------------------------------------
# Orientability
# ---------------------------------------------------------------------------


def test_explicit_mobius_band_is_non_orientable() -> None:
    """Three quads on two vertex rings, with the third quad's seam twisted
    so one ring's "up" becomes the other's "down".  BFS reaches the twisted
    triangle from two different neighbours that demand opposite signs —
    the conflict fires, proving the mesh is non-orientable."""
    # Geometry is irrelevant; only connectivity matters for orientability.
    pts = np.zeros((6, 3), dtype=np.float64)
    params = np.zeros((6, 2), dtype=np.float64)
    tris = np.array(
        [
            # Quad 0: ring-A[0,1] to ring-B[3,4]
            [0, 1, 4],
            [0, 4, 3],
            # Quad 1: ring-A[1,2] to ring-B[4,5]
            [1, 2, 5],
            [1, 5, 4],
            # Quad 2 — twist: vertex 3 takes the "top" slot vertex 0 held,
            # vertex 0 takes the "bottom" slot vertex 3 held.
            [2, 3, 0],
            [2, 0, 5],
        ],
        dtype=np.int64,
    )
    mesh = AdaptiveMesh(params=params, points=pts, triangles=tris)
    t = analyze(mesh)
    assert not t.is_orientable


def test_welded_parametric_mobius_is_non_orientable() -> None:
    """The Möbius parametrisation ``((1+v/2 cos(u/2)) cos u, ..., v/2 sin(u/2))``
    has a *geometric* twist-identification: the points ``(u=0, v)`` and
    ``(u=2π, −v)`` coincide in R³.  Welding therefore reproduces the
    Möbius topology without any parametric-seam logic: open (one boundary
    loop), connected, manifold, and — crucially — non-orientable.
    Open Möbius: ``χ = 0``."""
    strip = Surface(
        (
            (1 + v / 2 * sp.cos(u / 2)) * sp.cos(u),
            (1 + v / 2 * sp.cos(u / 2)) * sp.sin(u),
            v / 2 * sp.sin(u / 2),
        ),
        u=(0.0, float(2 * sp.pi)),
        v=(-1.0, 1.0),
    )
    mesh = adaptive_mesh(compiled(strip), base_n=6, chord_eps=5e-3, max_depth=3)
    welded = weld_duplicate_vertices(mesh, eps=1e-6)
    t = analyze(welded)
    assert not t.is_orientable
    assert t.is_manifold
    assert t.components == 1
    assert not t.is_closed
    assert t.euler == 0
