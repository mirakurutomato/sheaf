"""Curvature-driven adaptive triangular meshing.

Implements **Rivara longest-edge bisection** (LEB): a refinement scheme that
is always conforming (no T-junctions) and terminates because propagating to
a neighbour always follows strictly-longer edges until the shared edge is
the longest for both triangles.

**Refinement indicator** (composite, backend-only):

* ``chord_error`` — distance between the surface at a triangle's parametric
  centroid and the linear average of the three surface corners, normalised
  by the maximum 3D edge length.  Captures intrinsic bending in R³.
* ``sigma_min(J)`` — smallest singular value of the 3×2 Jacobian at every
  sampled (u, v).  Near a parametric degeneracy (sphere pole, cone apex,
  Möbius seam) this drops to zero while chord error stays quiet, so the two
  indicators cover disjoint failure modes.

A triangle is refined whenever either indicator exceeds its threshold and
the triangle's largest edge is still above ``min_edge``.  The refinement
loop halts when no triangle is flagged or ``max_triangles`` is hit.

This is the mesh backend for the Month 1 validation gate: saddle / sphere
/ Möbius should exhibit ≥2× vertex density in a neighbourhood of any
singular point compared with a benign region.
"""

from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass

import numpy as np

from sheaf.numeric.compiler import CompiledSurface


@dataclass(frozen=True, slots=True)
class AdaptiveMesh:
    """A conforming triangular mesh in parameter space paired with its 3D embedding.

    Attributes
    ----------
    params:
        ``(N, 2)`` array of (u, v) vertex coordinates.
    points:
        ``(N, 3)`` array of (x, y, z) 3D coordinates — ``eval_fn`` evaluated
        at every row of ``params``.
    triangles:
        ``(M, 3)`` integer array of vertex indices into ``params``/``points``.
    """

    params: np.ndarray
    points: np.ndarray
    triangles: np.ndarray

    @property
    def n_vertices(self) -> int:
        return int(self.params.shape[0])

    @property
    def n_triangles(self) -> int:
        return int(self.triangles.shape[0])


# ---------------------------------------------------------------------------
# Public entry point
# ---------------------------------------------------------------------------


def adaptive_mesh(
    compiled: CompiledSurface,
    *,
    chord_eps: float = 5e-3,
    sv_eps: float = 1e-3,
    base_n: int = 8,
    max_depth: int = 7,
    max_triangles: int = 50_000,
) -> AdaptiveMesh:
    """Build a curvature-adapted mesh of a parametric surface via Rivara LEB.

    Parameters
    ----------
    chord_eps:
        Max allowed chord error as a fraction of the triangle's 3D diameter.
        Smaller → more refinement on bent regions.
    sv_eps:
        Threshold on the smallest singular value of the Jacobian.  Anything
        smaller triggers refinement to resolve parametric degeneracies (poles).
    base_n:
        Initial uniform grid is ``base_n × base_n`` quads (``2·base_n²`` tris).
    max_depth:
        Cap on bisections measured in halvings of the initial parameter edge.
    max_triangles:
        Hard ceiling to prevent runaway near true singularities.
    """
    (u0, u1), (v0, v1) = compiled.domain
    min_edge = max(u1 - u0, v1 - v0) / (base_n * 2**max_depth)

    verts, tris = _base_mesh((u0, u1), (v0, v1), base_n)
    refiner = _Refiner(verts, tris)

    def severity(tri: tuple[int, int, int]) -> float:
        return _severity(tri, refiner.verts, compiled, chord_eps, sv_eps, min_edge)

    # Each pass: rank triangles by severity and refine worst-first until the
    # pass queue empties or budget is spent.  Priority ordering guarantees the
    # ceiling never starves the true singularities for chord-error noise.
    while refiner.n_triangles < max_triangles:
        ranked: list[tuple[float, int]] = []
        for tid, tri in refiner.tris.items():
            sev = severity(tri)
            if sev > 0.0:
                ranked.append((sev, tid))
        if not ranked:
            break
        ranked.sort(reverse=True)
        for _, tid in ranked:
            if refiner.n_triangles >= max_triangles:
                break
            refiner.refine(tid)

    return _finalise(compiled, refiner)


# ---------------------------------------------------------------------------
# Base mesh
# ---------------------------------------------------------------------------


def _base_mesh(
    u_range: tuple[float, float],
    v_range: tuple[float, float],
    n: int,
) -> tuple[list[tuple[float, float]], list[tuple[int, int, int]]]:
    """Uniform ``n × n`` quad grid, each quad split into two CCW triangles."""
    (u0, u1), (v0, v1) = u_range, v_range
    us = np.linspace(u0, u1, n + 1)
    vs = np.linspace(v0, v1, n + 1)
    verts: list[tuple[float, float]] = [(float(u), float(v)) for v in vs for u in us]
    tris: list[tuple[int, int, int]] = []
    stride = n + 1
    for j in range(n):
        for i in range(n):
            v00 = i + j * stride
            v10 = (i + 1) + j * stride
            v01 = i + (j + 1) * stride
            v11 = (i + 1) + (j + 1) * stride
            tris.append((v00, v10, v11))
            tris.append((v00, v11, v01))
    return verts, tris


# ---------------------------------------------------------------------------
# Refinement indicator
# ---------------------------------------------------------------------------


def _severity(
    tri: tuple[int, int, int],
    verts: list[tuple[float, float]],
    compiled: CompiledSurface,
    chord_eps: float,
    sv_eps: float,
    min_edge: float,
) -> float:
    """Return 0 if ``tri`` does not need refinement, else a positive severity.

    Severity is used to prioritise refinement when the triangle budget is
    tight.  A degenerate 3D scale (pole) dominates; otherwise the larger of
    the chord-error ratio and the Jacobian-rank deficit is used.
    """
    a, b, c = tri
    pa, pb, pc = verts[a], verts[b], verts[c]
    max_edge = math.sqrt(
        max(
            (pa[0] - pb[0]) ** 2 + (pa[1] - pb[1]) ** 2,
            (pb[0] - pc[0]) ** 2 + (pb[1] - pc[1]) ** 2,
            (pc[0] - pa[0]) ** 2 + (pc[1] - pa[1]) ** 2,
        )
    )
    if max_edge < min_edge:
        return 0.0

    cu = (pa[0] + pb[0] + pc[0]) / 3.0
    cv = (pa[1] + pb[1] + pc[1]) / 3.0

    sa = np.asarray(compiled.eval_fn(pa[0], pa[1]), dtype=float).reshape(3)
    sb = np.asarray(compiled.eval_fn(pb[0], pb[1]), dtype=float).reshape(3)
    sc = np.asarray(compiled.eval_fn(pc[0], pc[1]), dtype=float).reshape(3)
    sm = np.asarray(compiled.eval_fn(cu, cv), dtype=float).reshape(3)

    linear = (sa + sb + sc) / 3.0
    chord = float(np.linalg.norm(sm - linear))
    scale = max(
        float(np.linalg.norm(sa - sb)),
        float(np.linalg.norm(sb - sc)),
        float(np.linalg.norm(sc - sa)),
    )
    if scale < 1e-14:
        return 1e9  # 3D-degenerate triangle dominates any other signal.

    chord_severity = (chord / scale) / chord_eps
    jac = np.asarray(compiled.jacobian_fn(cu, cv), dtype=float).reshape(3, 2)
    sv_min = float(np.linalg.svd(jac, compute_uv=False)[-1])
    sv_severity = sv_eps / max(sv_min, 1e-12)

    worst = max(chord_severity, sv_severity)
    return worst if worst > 1.0 else 0.0


# ---------------------------------------------------------------------------
# Rivara longest-edge bisection
# ---------------------------------------------------------------------------


class _Refiner:
    """Rivara LEB over a mutable triangle soup indexed by stable triangle ids."""

    __slots__ = ("verts", "tris", "_next_id", "_edge_tris", "_edge_midpoint")

    def __init__(
        self,
        verts: list[tuple[float, float]],
        tris: list[tuple[int, int, int]],
    ) -> None:
        self.verts: list[tuple[float, float]] = list(verts)
        self.tris: dict[int, tuple[int, int, int]] = {}
        self._next_id: int = 0
        self._edge_tris: dict[frozenset[int], set[int]] = defaultdict(set)
        self._edge_midpoint: dict[frozenset[int], int] = {}
        for t in tris:
            self._register(t)

    @property
    def n_triangles(self) -> int:
        return len(self.tris)

    # -- primitive ops -------------------------------------------------------

    def _register(self, t: tuple[int, int, int]) -> int:
        tid = self._next_id
        self._next_id += 1
        self.tris[tid] = t
        for e in _tri_edges(t):
            self._edge_tris[e].add(tid)
        return tid

    def _drop(self, tid: int) -> None:
        t = self.tris.pop(tid)
        for e in _tri_edges(t):
            self._edge_tris[e].discard(tid)

    def _longest_edge(self, tid: int) -> tuple[int, int]:
        a, b, c = self.tris[tid]
        pa, pb, pc = self.verts[a], self.verts[b], self.verts[c]
        pairs = ((a, b, pa, pb), (b, c, pb, pc), (c, a, pc, pa))
        best = max(
            pairs,
            key=lambda q: (q[2][0] - q[3][0]) ** 2 + (q[2][1] - q[3][1]) ** 2,
        )
        return best[0], best[1]

    def _midpoint_index(self, key: frozenset[int]) -> int:
        if key in self._edge_midpoint:
            return self._edge_midpoint[key]
        a, b = tuple(key)
        pa, pb = self.verts[a], self.verts[b]
        m = len(self.verts)
        self.verts.append(((pa[0] + pb[0]) / 2.0, (pa[1] + pb[1]) / 2.0))
        self._edge_midpoint[key] = m
        return m

    def _bisect_edge(self, key: frozenset[int]) -> None:
        """Split every triangle that currently shares edge ``key`` through its midpoint."""
        a_val, b_val = tuple(key)
        m = self._midpoint_index(key)
        for old_tid in list(self._edge_tris[key]):
            if old_tid not in self.tris:
                continue
            old = self.tris[old_tid]
            # Walk the cycle to find a, b, c in winding order.
            i = old.index(a_val)
            j = old.index(b_val)
            c = next(v for v in old if v != a_val and v != b_val)
            self._drop(old_tid)
            if (i + 1) % 3 == j:
                # cycle is a → b → c: split into (a, m, c), (m, b, c)
                self._register((a_val, m, c))
                self._register((m, b_val, c))
            else:
                # cycle is b → a → c: split into (b, m, c), (m, a, c)
                self._register((b_val, m, c))
                self._register((m, a_val, c))

    # -- Rivara propagation --------------------------------------------------

    def refine(self, seed: int) -> None:
        """Bisect ``seed`` along its longest edge, propagating to conform."""
        stack = [seed]
        while stack:
            tid = stack[-1]
            if tid not in self.tris:
                stack.pop()
                continue
            a, b = self._longest_edge(tid)
            key = frozenset({a, b})
            neighbours = self._edge_tris[key] - {tid}
            if not neighbours:
                self._bisect_edge(key)
                stack.pop()
                continue
            n = next(iter(neighbours))
            na, nb = self._longest_edge(n)
            if frozenset({na, nb}) == key:
                self._bisect_edge(key)  # splits both tid and n
                stack.pop()
            else:
                stack.append(n)


def _tri_edges(t: tuple[int, int, int]) -> tuple[frozenset[int], ...]:
    a, b, c = t
    return (frozenset({a, b}), frozenset({b, c}), frozenset({c, a}))


# ---------------------------------------------------------------------------
# Finalisation
# ---------------------------------------------------------------------------


def _finalise(compiled: CompiledSurface, refiner: _Refiner) -> AdaptiveMesh:
    params = np.asarray(refiner.verts, dtype=float)
    uu = params[:, 0]
    vv = params[:, 1]
    xs, ys, zs = compiled.eval_fn(uu, vv)
    shape: tuple[int, ...] = uu.shape
    xs_arr, ys_arr, zs_arr = (
        np.broadcast_to(np.asarray(a, dtype=float), shape) for a in (xs, ys, zs)
    )
    points = np.stack((xs_arr, ys_arr, zs_arr), axis=-1)
    tris_arr = np.array(list(refiner.tris.values()), dtype=np.int64)
    return AdaptiveMesh(params=params, points=points, triangles=tris_arr)


__all__: list[str] = ["AdaptiveMesh", "adaptive_mesh"]
