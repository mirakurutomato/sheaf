"""BSP tree + painter's-algorithm hidden-surface removal — Month 2 W7.

The vector pipeline emits TikZ ``\\fill`` paths; unlike raster rendering
there is no z-buffer, so polygons must be drawn strictly back to front.
For arbitrarily intersecting triangles the only correct depth ordering is
produced by partitioning space with a Binary Space Partition tree.

Construction
------------

``build_bsp(triangles)`` picks the first triangle as the root, lifts it to
its supporting plane, and classifies every other triangle as one of:

* **FRONT** — all vertices on the positive-normal side,
* **BACK** — all vertices on the negative-normal side,
* **COPLANAR** — all vertices within ``eps`` of the plane,
* **SPANNING** — straddles the plane; split into front and back fragments
  by Sutherland-Hodgman-style clipping.

Recursion proceeds on the front list and the back list independently.

Painting
--------

``paint(node, view)`` walks the tree:  at every node it emits the *far*
sub-tree first, then the coplanar triangles, then the *near* sub-tree.
The resulting order is strict painter's order — any pair of triangles
whose screen projections overlap is emitted with the occluded one first.

Fragments are returned as ``(3, 3)`` float arrays of world-space vertices
rather than indices, because split fragments have no counterpart in the
original mesh vertex array.  ``painter_sort(mesh, view)`` is the ergonomic
one-shot entry point used by the TikZ emitter in W8.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

import numpy as np

from sheaf.numeric.mesh import AdaptiveMesh

Classification = Literal["FRONT", "BACK", "COPLANAR", "SPANNING"]

_DEFAULT_EPS = 1e-9


@dataclass(frozen=True, slots=True)
class Plane:
    """Oriented supporting plane ``{p : n·p = offset}``.  ``normal`` is unit."""

    normal: np.ndarray
    offset: float

    def signed_distance(self, points: np.ndarray) -> np.ndarray:
        """Signed distance of ``points`` (shape ``(..., 3)``) from the plane."""
        return np.asarray(points, dtype=float) @ self.normal - self.offset


@dataclass(slots=True)
class BSPNode:
    """One BSP tree node: a splitter plane plus its on-plane triangles."""

    plane: Plane
    coplanar: list[np.ndarray] = field(default_factory=list)
    front: BSPNode | None = None
    back: BSPNode | None = None


def build_bsp(
    triangles: list[np.ndarray],
    *,
    eps: float = _DEFAULT_EPS,
) -> BSPNode | None:
    """Construct a BSP tree from a list of ``(3, 3)`` triangle vertex arrays.

    Degenerate (zero-area) triangles are silently dropped.  Returns ``None``
    when the input list contains no non-degenerate triangles.
    """
    tris = [np.asarray(t, dtype=float) for t in triangles]
    return _build(tris, eps)


def paint(node: BSPNode | None, view: np.ndarray) -> list[np.ndarray]:
    """Back-to-front ordered list of triangle fragments seen from ``view``.

    ``view`` is a 3-vector (world-space view position).  The returned list
    has each entry a ``(3, 3)`` vertex array; concatenate with
    ``np.stack(result)`` for an ``(N, 3, 3)`` ndarray.
    """
    out: list[np.ndarray] = []
    _paint(node, np.asarray(view, dtype=float), out)
    return out


def painter_sort(
    mesh: AdaptiveMesh,
    view: np.ndarray,
    *,
    eps: float = _DEFAULT_EPS,
) -> list[np.ndarray]:
    """Build a BSP from ``mesh`` and return its painter-ordered fragments."""
    triangles = [mesh.points[t] for t in mesh.triangles]
    tree = build_bsp(triangles, eps=eps)
    return paint(tree, view)


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _build(triangles: list[np.ndarray], eps: float) -> BSPNode | None:
    """Iterative BSP construction.

    A recursive descent on curved meshes blows past Python's recursion
    limit because every split fragment can itself be split deeper down,
    so we drive the build with an explicit work stack instead.  Each work
    item attaches the produced node to ``parent.<side>`` (or to the root
    holder when ``parent is None``).
    """
    usable = [t for t in triangles if not _is_degenerate(t, eps)]
    if not usable:
        return None

    root_holder: dict[str, BSPNode | None] = {"root": None}
    work: list[tuple[BSPNode | None, str, list[np.ndarray]]] = [
        (None, "root", usable)
    ]

    while work:
        parent, side_key, tris = work.pop()
        clean = [t for t in tris if not _is_degenerate(t, eps)]
        if not clean:
            continue

        root_idx = _pick_root_index(clean, eps)
        root_tri = clean[root_idx]
        root_plane = _plane_from_triangle(root_tri)
        node = BSPNode(plane=root_plane, coplanar=[root_tri])
        front: list[np.ndarray] = []
        back: list[np.ndarray] = []

        # Vectorised classify of every other triangle in one numpy pass.
        stack = np.stack(clean)  # (m, 3, 3)
        d = stack @ root_plane.normal - root_plane.offset  # (m, 3)
        max_d = d.max(axis=1)
        min_d = d.min(axis=1)
        spanning_mask = (max_d > eps) & (min_d < -eps)
        coplanar_mask = (max_d <= eps) & (min_d >= -eps)
        front_mask = ~spanning_mask & ~coplanar_mask & (max_d > eps)
        back_mask = ~spanning_mask & ~coplanar_mask & (min_d < -eps)

        for i in range(len(clean)):
            if i == root_idx:
                continue
            tri = clean[i]
            if front_mask[i]:
                front.append(tri)
            elif back_mask[i]:
                back.append(tri)
            elif coplanar_mask[i]:
                node.coplanar.append(tri)
            else:  # spanning
                ff, bb = _split_triangle(tri, root_plane, eps)
                front.extend(ff)
                back.extend(bb)

        if parent is None:
            root_holder["root"] = node
        elif side_key == "front":
            parent.front = node
        else:
            parent.back = node

        if front:
            work.append((node, "front", front))
        if back:
            work.append((node, "back", back))

    return root_holder["root"]


def _paint(node: BSPNode | None, view: np.ndarray, out: list[np.ndarray]) -> None:
    """Iterative in-order painter traversal.

    Stack items are either a ``BSPNode`` (deferred expansion) or a list of
    triangles to emit verbatim.  Children are pushed in reversed order so
    the LIFO pop order matches the recursive ``back, coplanar, front`` (or
    ``front, coplanar, back``) sequence.
    """
    if node is None:
        return

    stack: list[BSPNode | list[np.ndarray]] = [node]
    while stack:
        item = stack.pop()
        if isinstance(item, list):
            out.extend(item)
            continue

        side = float(np.dot(item.plane.normal, view) - item.plane.offset)
        if side >= 0.0:
            far, near = item.back, item.front
        else:
            far, near = item.front, item.back

        if near is not None:
            stack.append(near)
        stack.append(item.coplanar)
        if far is not None:
            stack.append(far)


_ROOT_CANDIDATES = 8


def _pick_root_index(triangles: list[np.ndarray], eps: float) -> int:
    """Pick a splitter triangle that minimises the SPANNING count.

    Sampling at most ``_ROOT_CANDIDATES`` evenly-spaced candidates and
    evaluating them against every other triangle in a single vectorised
    pass keeps the heuristic O(K·n); a naive recursion that always
    picked ``[0]`` caused both fragment explosion and Python-level
    quadratic blow-up on curved meshes.
    """
    n = len(triangles)
    if n <= 1:
        return 0

    candidate_count = min(_ROOT_CANDIDATES, n)
    candidates = np.unique(np.linspace(0, n - 1, candidate_count, dtype=int))

    tris = np.stack(triangles)  # (n, 3, 3)

    normals = np.empty((candidates.size, 3))
    offsets = np.empty(candidates.size)
    for k, cand in enumerate(candidates):
        plane = _plane_from_triangle(triangles[int(cand)])
        normals[k] = plane.normal
        offsets[k] = plane.offset

    # distances[k, i, v] = signed distance of vertex v of tri i from plane k
    distances = np.einsum("kj,inj->kin", normals, tris) - offsets[:, None, None]
    has_pos = (distances > eps).any(axis=-1)
    has_neg = (distances < -eps).any(axis=-1)
    spanning = (has_pos & has_neg).sum(axis=-1)

    return int(candidates[int(np.argmin(spanning))])


def _plane_from_triangle(tri: np.ndarray) -> Plane:
    e1 = tri[1] - tri[0]
    e2 = tri[2] - tri[0]
    n = np.cross(e1, e2)
    norm = float(np.linalg.norm(n))
    if norm < 1e-14:
        raise ValueError(f"degenerate triangle has zero cross-product: {tri!r}")
    n = n / norm
    return Plane(normal=n, offset=float(np.dot(n, tri[0])))


def _is_degenerate(tri: np.ndarray, eps: float) -> bool:
    e1 = tri[1] - tri[0]
    e2 = tri[2] - tri[0]
    return float(np.linalg.norm(np.cross(e1, e2))) < eps


def _classify(
    tri: np.ndarray, plane: Plane, eps: float
) -> tuple[Classification, list[np.ndarray]]:
    d = plane.signed_distance(tri)
    front = bool(np.all(d > eps))
    back = bool(np.all(d < -eps))
    coplanar = bool(np.all(np.abs(d) <= eps))
    if front:
        return "FRONT", [tri]
    if back:
        return "BACK", [tri]
    if coplanar:
        return "COPLANAR", [tri]
    # Anything else touching both strict sides is SPANNING.  A tri with two
    # vertices on the plane and one off is classified strictly (front/back)
    # by the checks above since the "off" vertex's sign dominates.
    if np.any(d > eps) and np.any(d < -eps):
        return "SPANNING", []
    # Mixed coplanar + one-sided: treat as that side.
    if np.any(d > eps):
        return "FRONT", [tri]
    return "BACK", [tri]


def _split_triangle(
    tri: np.ndarray, plane: Plane, eps: float
) -> tuple[list[np.ndarray], list[np.ndarray]]:
    """Sutherland-Hodgman clip of ``tri`` against ``plane``.

    Returns ``(front_fragments, back_fragments)`` — each a list of
    ``(3, 3)`` triangles produced by fan-triangulating the clipped polygons.
    """
    d = plane.signed_distance(tri)
    front_poly: list[np.ndarray] = []
    back_poly: list[np.ndarray] = []

    for i in range(3):
        a = tri[i]
        b = tri[(i + 1) % 3]
        da = float(d[i])
        db = float(d[(i + 1) % 3])

        if da > eps:
            front_poly.append(a)
        elif da < -eps:
            back_poly.append(a)
        else:
            front_poly.append(a)
            back_poly.append(a)

        crosses = (da > eps and db < -eps) or (da < -eps and db > eps)
        if crosses:
            t = da / (da - db)
            cut = a + t * (b - a)
            front_poly.append(cut)
            back_poly.append(cut)

    return _fan(front_poly), _fan(back_poly)


def _fan(poly: list[np.ndarray]) -> list[np.ndarray]:
    """Fan-triangulate a convex polygon given as a list of vertices."""
    if len(poly) < 3:
        return []
    v0 = poly[0]
    return [np.stack((v0, poly[i], poly[i + 1])) for i in range(1, len(poly) - 1)]
