"""BSP painter's-algorithm hidden-surface removal — Month 2 W7 validation.

Every test asserts a property of the painter's output that is invariant
under rotation / scaling of the scene — no pixel-level or floating-point-
tolerant counts against a rendered image.
"""

from __future__ import annotations

import numpy as np
import pytest

from sheaf.numeric.mesh import AdaptiveMesh
from sheaf.vector import build_bsp, paint, painter_sort
from sheaf.vector.bsp import Plane, _split_triangle

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _tri(a: tuple[float, float, float], b: tuple[float, float, float],
         c: tuple[float, float, float]) -> np.ndarray:
    return np.asarray([a, b, c], dtype=float)


def _area(tri: np.ndarray) -> float:
    e1 = tri[1] - tri[0]
    e2 = tri[2] - tri[0]
    return 0.5 * float(np.linalg.norm(np.cross(e1, e2)))


def _centroid(tri: np.ndarray) -> np.ndarray:
    return tri.mean(axis=0)


def _outward_normal(tri: np.ndarray) -> np.ndarray:
    e1 = tri[1] - tri[0]
    e2 = tri[2] - tri[0]
    n = np.cross(e1, e2)
    return n / np.linalg.norm(n)


# ---------------------------------------------------------------------------
# Trivial cases
# ---------------------------------------------------------------------------


def test_empty_input_builds_no_tree() -> None:
    assert build_bsp([]) is None
    assert paint(None, np.array([0.0, 0.0, 1.0])) == []


def test_single_triangle_round_trips() -> None:
    """A single triangle is emitted unchanged for any view."""
    t = _tri((0, 0, 0), (1, 0, 0), (0, 1, 0))
    tree = build_bsp([t])
    out = paint(tree, np.array([0.0, 0.0, 5.0]))
    assert len(out) == 1
    assert np.allclose(out[0], t)


def test_deterministic_output() -> None:
    """Same input → same output (list-based BSP is fully deterministic)."""
    tris = [
        _tri((0, 0, 0), (1, 0, 0), (0, 1, 0)),
        _tri((0, 0, 1), (1, 0, 1), (0, 1, 1)),
        _tri((0, 0, -1), (1, 0, -1), (0, 1, -1)),
    ]
    view = np.array([5.0, 5.0, 5.0])
    a = paint(build_bsp(tris), view)
    b = paint(build_bsp(tris), view)
    assert len(a) == len(b)
    for fa, fb in zip(a, b, strict=True):
        assert np.allclose(fa, fb)


# ---------------------------------------------------------------------------
# Parallel, non-intersecting triangles: view dictates order
# ---------------------------------------------------------------------------


def test_two_parallel_triangles_swap_order_with_view() -> None:
    """A pair of parallel z-stacked triangles reverses under view flip."""
    lo = _tri((0, 0, 0), (1, 0, 0), (0, 1, 0))
    hi = _tri((0, 0, 1), (1, 0, 1), (0, 1, 1))
    tree = build_bsp([lo, hi])

    above = paint(tree, np.array([0.0, 0.0, 10.0]))
    assert len(above) == 2
    # From +z, the z=0 triangle is back-facing → painted first.
    assert np.allclose(above[0], lo)
    assert np.allclose(above[1], hi)

    below = paint(tree, np.array([0.0, 0.0, -10.0]))
    assert len(below) == 2
    # Flipped view → order reverses.
    assert np.allclose(below[0], hi)
    assert np.allclose(below[1], lo)


# ---------------------------------------------------------------------------
# Splitting: Sutherland-Hodgman clip correctness
# ---------------------------------------------------------------------------


def test_spanning_triangle_area_is_conserved_by_split() -> None:
    """Splitting preserves the total surface area (no mass loss / gain)."""
    # Triangle straddling the xy-plane.
    t = _tri((0, 0, -1), (1, 0, 1), (0, 1, 1))
    plane = Plane(normal=np.array([0.0, 0.0, 1.0]), offset=0.0)
    front, back = _split_triangle(t, plane, eps=1e-9)
    total = sum(_area(f) for f in front) + sum(_area(f) for f in back)
    assert abs(total - _area(t)) < 1e-9


def test_split_fragments_lie_strictly_on_one_side() -> None:
    """Every fragment's vertices land on the correct half-space."""
    t = _tri((0, 0, -1), (1, 0, 1), (0, 1, 1))
    plane = Plane(normal=np.array([0.0, 0.0, 1.0]), offset=0.0)
    front, back = _split_triangle(t, plane, eps=1e-9)
    for f in front:
        assert (plane.signed_distance(f) >= -1e-9).all()
    for b in back:
        assert (plane.signed_distance(b) <= 1e-9).all()


def test_crossing_triangles_produce_more_than_two_fragments() -> None:
    """Two orthogonal triangles that cross must split into ≥ 3 fragments."""
    horizontal = _tri((-1, -1, 0), (1, -1, 0), (0, 1, 0))
    vertical = _tri((0, -1, -1), (0, 1, -1), (0, 0, 1))
    fragments = paint(build_bsp([horizontal, vertical]), np.array([5.0, 5.0, 5.0]))
    assert len(fragments) >= 3


# ---------------------------------------------------------------------------
# Convex body: painter's correctness certificate
# ---------------------------------------------------------------------------


def _tetrahedron_triangles() -> list[np.ndarray]:
    """Outward-oriented tetrahedron with vertices at the origin + 3 axis points."""
    v0 = np.array([0.0, 0.0, 0.0])
    v1 = np.array([1.0, 0.0, 0.0])
    v2 = np.array([0.0, 1.0, 0.0])
    v3 = np.array([0.0, 0.0, 1.0])
    # Outward winding verified by checking normals point away from centroid.
    centroid = (v0 + v1 + v2 + v3) / 4
    raw = [
        (v1, v3, v2),  # opposite v0
        (v0, v2, v3),  # opposite v1
        (v0, v3, v1),  # opposite v2
        (v0, v1, v2),  # opposite v3
    ]
    out: list[np.ndarray] = []
    for a, b, c in raw:
        tri = np.stack((a, b, c))
        n = _outward_normal(tri)
        if float(n @ (_centroid(tri) - centroid)) < 0:
            tri = np.stack((a, c, b))  # flip
        out.append(tri)
    return out


def test_convex_tetrahedron_back_faces_paint_before_front_faces() -> None:
    """For a convex body, BSP painter order must place every back-facing
    triangle before every front-facing one: no back can occlude a front."""
    tris = _tetrahedron_triangles()
    view = np.array([5.0, 5.0, 5.0])
    fragments = paint(build_bsp(tris), view)
    assert len(fragments) == 4  # no splitting on a convex body

    def is_back(tri: np.ndarray) -> bool:
        n = _outward_normal(tri)
        return float(n @ (view - _centroid(tri))) < 0

    facings = [is_back(f) for f in fragments]
    # All True (back) must precede all False (front).
    first_front = next((i for i, b in enumerate(facings) if not b), len(facings))
    assert all(facings[:first_front]), "back-facing triangles must come first"
    assert not any(facings[first_front:]), "front-facing must not appear before back"
    # Sanity: from (5, 5, 5), 3 faces are back-facing and 1 is front-facing.
    assert facings.count(True) == 3
    assert facings.count(False) == 1


# ---------------------------------------------------------------------------
# AdaptiveMesh integration
# ---------------------------------------------------------------------------


def test_painter_sort_on_adaptive_mesh_preserves_triangle_count() -> None:
    """A non-self-intersecting mesh goes through BSP with no splits."""
    # Two disjoint triangles: no splits can happen.
    pts = np.array(
        [[0, 0, 0], [1, 0, 0], [0, 1, 0], [5, 5, 5], [6, 5, 5], [5, 6, 5]],
        dtype=float,
    )
    params = np.zeros((6, 2), dtype=float)
    tris = np.array([[0, 1, 2], [3, 4, 5]], dtype=np.int64)
    mesh = AdaptiveMesh(params=params, points=pts, triangles=tris)
    fragments = painter_sort(mesh, np.array([0.0, 0.0, 20.0]))
    assert len(fragments) == 2


def test_degenerate_triangles_are_dropped() -> None:
    """Zero-area triangles do not crash BSP construction and are skipped."""
    good = _tri((0, 0, 0), (1, 0, 0), (0, 1, 0))
    degen = _tri((0, 0, 0), (1, 0, 0), (2, 0, 0))  # colinear
    fragments = paint(build_bsp([good, degen]), np.array([0.0, 0.0, 5.0]))
    assert len(fragments) == 1
    assert np.allclose(fragments[0], good)


def test_view_on_plane_does_not_error() -> None:
    """View point exactly on a splitter plane must still produce a valid order."""
    tris = [
        _tri((-1, -1, 0), (1, -1, 0), (0, 1, 0)),
        _tri((-1, -1, 1), (1, -1, 1), (0, 1, 1)),
    ]
    # View exactly on the plane z=0.
    fragments = paint(build_bsp(tris), np.array([0.0, 0.0, 0.0]))
    assert len(fragments) == 2


# ---------------------------------------------------------------------------
# Plane arithmetic
# ---------------------------------------------------------------------------


def test_plane_signed_distance_matches_dot_minus_offset() -> None:
    plane = Plane(normal=np.array([0.0, 0.0, 1.0]), offset=2.0)
    pts = np.array([[0, 0, 0], [0, 0, 2], [0, 0, 5], [0, 0, -3]], dtype=float)
    d = plane.signed_distance(pts)
    assert d.tolist() == pytest.approx([-2.0, 0.0, 3.0, -5.0])
