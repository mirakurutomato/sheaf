"""Mesh topology analysis — Month 2 W5.

Given an :class:`~sheaf.numeric.mesh.AdaptiveMesh` this module answers the
purely combinatorial questions that drive semantic rendering downstream:

* **Where are the boundary edges?** — Glass material's boundary-glow effect
  (W10) reads this list directly.
* **Is the surface closed or open?** — closed surfaces admit a true inside /
  outside; open surfaces do not.
* **Is the mesh manifold?** — a CSG mis-cut (W8) can produce edges shared by
  ≥3 triangles.  We must detect that, not silently render garbage.
* **Is it orientable?** — Möbius vs. cylinder share all local properties but
  differ here; downstream rendering may highlight this.
* **How many connected components?** — for scenes composed of disjoint parts.

An optional preprocessing helper, :func:`weld_duplicate_vertices`, merges
geometrically-coincident vertices.  This alone is sufficient to recover the
true topology of parametric closed surfaces — sphere poles collapse, the
``u=0 / u=2π`` seam of a torus stitches — because the geometry itself
supplies the equivalence.  It is *not* sufficient for twisted identifications
such as a Möbius strip's boundary; that requires an explicit parametric
stitching pass and will land alongside the CSG-driven closure logic in W8.
"""

from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass

import numpy as np

from sheaf.numeric.mesh import AdaptiveMesh


@dataclass(frozen=True, slots=True)
class Topology:
    """Purely combinatorial summary of a triangle mesh.

    Every field is invariant under re-embedding: two isometric meshes produce
    identical :class:`Topology` values.
    """

    boundary_edges: np.ndarray
    """``(B, 2)`` int — vertex-index pairs on the open boundary (edges shared
    by exactly one triangle).  Sorted within each row."""

    non_manifold_edges: np.ndarray
    """``(N, 2)`` int — edges shared by ≥3 triangles.  Empty for every mesh
    produced by :mod:`sheaf.numeric.mesh`; non-empty outputs indicate CSG
    pathology that the vector pipeline must refuse to render."""

    components: int
    """Number of connected components under triangle-adjacency."""

    euler: int
    """``V − E + F``.  Topological invariant: ``2`` for a sphere, ``0`` for a
    torus, ``1`` for a disk, ``−2g + 2 − b`` for a genus-*g* surface with *b*
    boundary components."""

    is_closed: bool
    """No boundary edges."""

    is_manifold: bool
    """No non-manifold edges."""

    is_orientable: bool
    """A consistent triangle orientation exists across every component.
    Detected via BFS: conflict during re-visit ⇒ non-orientable."""


def analyze(mesh: AdaptiveMesh) -> Topology:
    """Run the full combinatorial analysis on ``mesh``."""
    tris = mesh.triangles
    if len(tris) == 0:
        empty = np.zeros((0, 2), dtype=np.int64)
        return Topology(empty, empty, 0, 0, True, True, True)

    edge_tris: dict[frozenset[int], list[int]] = defaultdict(list)
    for i, (a, b, c) in enumerate(tris):
        ai, bi, ci = int(a), int(b), int(c)
        for u, v in ((ai, bi), (bi, ci), (ci, ai)):
            edge_tris[frozenset((u, v))].append(i)

    boundary = [sorted(key) for key, owners in edge_tris.items() if len(owners) == 1]
    nonmanifold = [sorted(key) for key, owners in edge_tris.items() if len(owners) >= 3]
    boundary_arr = np.asarray(boundary, dtype=np.int64).reshape(-1, 2)
    nonmanifold_arr = np.asarray(nonmanifold, dtype=np.int64).reshape(-1, 2)

    # Connected components via union-find on triangle adjacency.
    parent = list(range(len(tris)))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for owners in edge_tris.values():
        for other in owners[1:]:
            ra, rb = find(owners[0]), find(other)
            if ra != rb:
                parent[ra] = rb
    components = len({find(i) for i in range(len(tris))})

    # Euler uses the count of vertices actually referenced by triangles: a
    # welded-but-unreferenced vertex must not distort χ.
    used_vertices = int(np.unique(tris).size)
    euler = used_vertices - len(edge_tris) + len(tris)

    return Topology(
        boundary_edges=boundary_arr,
        non_manifold_edges=nonmanifold_arr,
        components=components,
        euler=int(euler),
        is_closed=len(boundary_arr) == 0,
        is_manifold=len(nonmanifold_arr) == 0,
        is_orientable=_is_orientable(tris),
    )


def _is_orientable(tris: np.ndarray) -> bool:
    """BFS over triangle adjacency, flipping neighbours to agree with the root.

    Invariant: two triangles sharing an edge are *consistently* oriented iff
    they traverse that edge in opposite directions.  If a later visit demands
    a sign that contradicts a previously-assigned one, the mesh is
    non-orientable.
    """
    n = len(tris)
    edge_owners: dict[frozenset[int], list[int]] = defaultdict(list)
    for i, (a, b, c) in enumerate(tris):
        for u, v in ((int(a), int(b)), (int(b), int(c)), (int(c), int(a))):
            edge_owners[frozenset((u, v))].append(i)

    # sign[i] ∈ {0 (unvisited), +1 (keep), −1 (flip)}
    sign = np.zeros(n, dtype=np.int8)

    for root in range(n):
        if sign[root] != 0:
            continue
        sign[root] = 1
        q: deque[int] = deque([root])
        while q:
            t = q.popleft()
            tv = [int(x) for x in tris[t]]
            if sign[t] == -1:
                tv = tv[::-1]
            t_edges = [(tv[i], tv[(i + 1) % 3]) for i in range(3)]
            for u, v in t_edges:
                for other in edge_owners[frozenset((u, v))]:
                    if other == t:
                        continue
                    ov = [int(x) for x in tris[other]]
                    other_edges = [(ov[i], ov[(i + 1) % 3]) for i in range(3)]
                    # Consistent ⇔ 'other' traverses (v, u) as-is.
                    if (v, u) in other_edges:
                        needed = 1
                    elif (u, v) in other_edges:
                        needed = -1
                    else:  # pragma: no cover — frozenset match guarantees membership
                        continue
                    if sign[other] == 0:
                        sign[other] = needed
                        q.append(other)
                    elif sign[other] != needed:
                        return False
    return True


def weld_duplicate_vertices(mesh: AdaptiveMesh, eps: float = 1e-9) -> AdaptiveMesh:
    """Merge vertices whose 3D coordinates coincide within ``eps``.

    Degenerate triangles produced by the merge (any two of the three corners
    collapse to the same index) are dropped — a pole on a sphere triangulated
    from a UV grid loses its fan of degenerate tris after welding.
    """
    from scipy.spatial import KDTree

    pts = mesh.points
    n = len(pts)
    if n == 0:
        return mesh

    tree = KDTree(pts)
    pairs = tree.query_pairs(r=eps, output_type="ndarray")

    parent = list(range(n))

    def find(x: int) -> int:
        while parent[x] != x:
            parent[x] = parent[parent[x]]
            x = parent[x]
        return x

    for i, j in pairs:
        ri, rj = find(int(i)), find(int(j))
        if ri != rj:
            parent[ri] = rj

    roots = np.array([find(i) for i in range(n)], dtype=np.int64)
    unique_roots, inv = np.unique(roots, return_inverse=True)

    new_points = pts[unique_roots]
    new_params = mesh.params[unique_roots]
    new_tris = inv[mesh.triangles]

    keep = (
        (new_tris[:, 0] != new_tris[:, 1])
        & (new_tris[:, 1] != new_tris[:, 2])
        & (new_tris[:, 0] != new_tris[:, 2])
    )
    new_tris = new_tris[keep]

    return AdaptiveMesh(params=new_params, points=new_points, triangles=new_tris)
