"""Demonstrate BSP painter's-algorithm back-to-front ordering.

Run from the repo root:

    .venv/Scripts/python examples/painter_order.py

Builds a tetrahedron + a single spanning triangle that cuts straight
through one face, then prints the painter's order for a fixed view.
The expected behaviour:

* 4 tetrahedron faces come out in the canonical back-first order for a
  convex body viewed from ``(5, 5, 5)`` (three back faces, then the one
  front face).
* The spanning triangle is split by BSP construction and the resulting
  fragments appear sandwiched between the tetrahedron faces they cross,
  demonstrating that BSP resolves inter-triangle occlusion, not just
  face-culling.
"""

from __future__ import annotations

import numpy as np

from sheaf.vector import build_bsp, paint


def _tri(a, b, c) -> np.ndarray:
    return np.asarray([a, b, c], dtype=float)


def _normal(tri: np.ndarray) -> np.ndarray:
    e1 = tri[1] - tri[0]
    e2 = tri[2] - tri[0]
    n = np.cross(e1, e2)
    return n / np.linalg.norm(n)


def _tetrahedron() -> list[np.ndarray]:
    v0 = np.array([0.0, 0.0, 0.0])
    v1 = np.array([1.0, 0.0, 0.0])
    v2 = np.array([0.0, 1.0, 0.0])
    v3 = np.array([0.0, 0.0, 1.0])
    centroid = (v0 + v1 + v2 + v3) / 4
    raw = [
        ("A  opp v0", v1, v3, v2),
        ("B  opp v1", v0, v2, v3),
        ("C  opp v2", v0, v3, v1),
        ("D  opp v3", v0, v1, v2),
    ]
    tris: list[np.ndarray] = []
    for _, a, b, c in raw:
        t = _tri(a, b, c)
        if float(_normal(t) @ (t.mean(0) - centroid)) < 0:
            t = _tri(a, c, b)
        tris.append(t)
    return tris


def run() -> None:
    view = np.array([5.0, 5.0, 5.0])

    # Part 1: convex tetrahedron — back faces must come first.
    tet = _tetrahedron()
    tree = build_bsp(tet)
    order = paint(tree, view)
    print("=" * 72)
    print("tetrahedron (convex) painter order from view (5, 5, 5):")
    for i, frag in enumerate(order):
        n = _normal(frag)
        centroid = frag.mean(0)
        facing = "back " if float(n @ (view - centroid)) < 0 else "front"
        print(f"  [{i}] {facing}  centroid={centroid}  normal={n.round(3)}")

    # Part 2: add a vertical slicing triangle through the tetrahedron body.
    slicer = _tri((-0.2, 0.3, -0.2), (1.2, 0.3, -0.2), (0.5, 0.3, 1.2))
    mixed_tree = build_bsp([*tet, slicer])
    order = paint(mixed_tree, view)
    print("=" * 72)
    print("tetrahedron + slicing triangle: fragments after BSP splitting:")
    for i, frag in enumerate(order):
        print(f"  [{i}] centroid={frag.mean(0).round(3)}")


if __name__ == "__main__":
    run()
