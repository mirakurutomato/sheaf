"""Adaptive mesh (Rivara LEB) — Month 1 validation gate.

The gate: near a singularity / pole, vertex density must exceed the density
of a benign region by ≥ 2×.  Every asserted inequality in this file is the
concrete form of that gate.
"""

from __future__ import annotations

import numpy as np
import sympy as sp
from sympy.abc import phi, theta, u, v, x, y

from sheaf import Surface
from sheaf.numeric import adaptive_mesh, compiled
from sheaf.numeric.compiler import CompiledSurface

# ---------------------------------------------------------------------------
# Conformance + sanity
# ---------------------------------------------------------------------------


def test_adaptive_mesh_of_plane_is_uniform() -> None:
    """A flat plane z = 0 has zero curvature everywhere: no refinement beyond base."""
    plane = Surface(z=sp.Integer(0) * x + sp.Integer(0) * y, x=(-1, 1), y=(-1, 1))
    c = compiled(plane)
    assert isinstance(c, CompiledSurface)
    mesh = adaptive_mesh(c, base_n=4)
    # Base grid: 4×4 quads = 32 triangles
    assert mesh.n_triangles == 32
    assert mesh.n_vertices == 25
    # Vertices of degenerate plane embedding: x = u, y = v, z = 0
    assert np.allclose(mesh.points[:, 2], 0.0)
    assert np.allclose(mesh.points[:, 0], mesh.params[:, 0])
    assert np.allclose(mesh.points[:, 1], mesh.params[:, 1])


def test_adaptive_mesh_triangles_are_conforming() -> None:
    """No T-junctions: every interior edge is shared by exactly two triangles."""
    s = Surface(z=x**2 + y**2, x=(-1, 1), y=(-1, 1))
    c = compiled(s)
    mesh = adaptive_mesh(c, base_n=4, chord_eps=1e-2, max_depth=4)
    from collections import Counter

    edges = Counter()
    for t in mesh.triangles:
        a, b, c_ = int(t[0]), int(t[1]), int(t[2])
        edges[frozenset((a, b))] += 1
        edges[frozenset((b, c_))] += 1
        edges[frozenset((c_, a))] += 1
    # Every edge is shared by 1 (boundary) or 2 (interior) triangles — never 3+
    assert all(count in (1, 2) for count in edges.values())


# ---------------------------------------------------------------------------
# Month 1 validation gate: density at singular points
# ---------------------------------------------------------------------------


def test_sphere_pole_density_exceeds_equator() -> None:
    """Sphere: polar meridian (φ=0, φ=π) are parametric singularities.
    Vertex density in the polar band must be ≥ 2× the equatorial density."""
    sphere = Surface(
        (sp.sin(phi) * sp.cos(theta), sp.sin(phi) * sp.sin(theta), sp.cos(phi)),
        phi=(0.0, float(sp.pi)),
        theta=(0.0, float(2 * sp.pi)),
    )
    c = compiled(sphere)
    mesh = adaptive_mesh(c, base_n=8, chord_eps=1e-2, sv_eps=5e-2, max_depth=5)
    phis = mesh.params[:, 0]
    band = 0.1  # radians — sized to the refinement zone
    polar = np.sum((phis < band) | (phis > float(sp.pi) - band))
    equator = np.sum(
        (phis > float(sp.pi) / 2 - band) & (phis < float(sp.pi) / 2 + band)
    )
    # Two polar bands vs one equator band → halve the polar count.
    polar_density = polar / 2
    assert polar_density > 2 * equator, (
        f"polar density {polar_density} not ≥ 2× equator density {equator}"
    )


def test_gaussian_peak_origin_density_exceeds_boundary() -> None:
    """A tall Gaussian bump has curvature concentrated at the origin and
    decaying to zero at the boundary.  Chord-error refinement must deliver
    density at origin ≥ 2× the boundary density."""
    peak = Surface(z=sp.exp(-6 * (x**2 + y**2)), x=(-1, 1), y=(-1, 1))
    c = compiled(peak)
    mesh = adaptive_mesh(c, base_n=4, chord_eps=5e-3, max_depth=6)
    r = np.linalg.norm(mesh.params, axis=1)
    origin_r = 0.3
    ring_lo, ring_hi = 0.8, float(np.sqrt(2))
    origin_density = np.sum(r < origin_r) / (np.pi * origin_r**2)
    ring_density = np.sum((r > ring_lo) & (r < ring_hi)) / (
        np.pi * (ring_hi**2 - ring_lo**2)
    )
    assert origin_density > 2 * ring_density, (
        f"origin density {origin_density:.1f} not ≥ 2× ring density {ring_density:.1f}"
    )


def test_monkey_saddle_compiles_and_meshes_without_explosion() -> None:
    """z = x³ − 3xy² is a harmonic cubic: its umbilic at the origin is invisible
    to chord-error refinement (principal-direction ambiguity, ∇²z = 0 in trace).
    That singularity lands in W6 with the Hessian-eigenvalue indicator; here we
    only verify the mesh is well-formed and bounded."""
    saddle = Surface(z=x**3 - 3 * x * y**2, x=(-1.0, 1.0), y=(-1.0, 1.0))
    c = compiled(saddle)
    mesh = adaptive_mesh(c, base_n=6, chord_eps=5e-3, max_depth=5)
    assert np.isfinite(mesh.points).all()
    assert mesh.n_triangles > 2 * 6**2  # at least one refinement pass past base


def test_mobius_strip_meshes_without_degeneracy() -> None:
    """Möbius: no closed-form singularity gate, but the mesh must exist, be
    finite-valued, and use the adaptive budget rather than degenerate to base."""
    strip = Surface(
        (
            (1 + v / 2 * sp.cos(u / 2)) * sp.cos(u),
            (1 + v / 2 * sp.cos(u / 2)) * sp.sin(u),
            v / 2 * sp.sin(u / 2),
        ),
        u=(0.0, float(2 * sp.pi)),
        v=(-1.0, 1.0),
    )
    c = compiled(strip)
    mesh = adaptive_mesh(c, base_n=6, chord_eps=5e-3, max_depth=4)
    assert np.isfinite(mesh.points).all()
    # Base would be 2 * 6² = 72 triangles; refinement must push us well above.
    assert mesh.n_triangles > 72
