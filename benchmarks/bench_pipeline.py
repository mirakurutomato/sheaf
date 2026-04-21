"""Timing harness for the full DSL → vector pipeline — Month 3 W12.

Not part of CI.  Run from the repo root::

    .venv/Scripts/python benchmarks/bench_pipeline.py

For each ``(surface, base_n, max_depth)`` the script measures the four
pipeline phases in isolation:

1. **compile**  — symbolic → NumPy callable (``sheaf.numeric.compiled``)
2. **mesh**     — Rivara LEB refinement (``sheaf.numeric.adaptive_mesh``)
3. **BSP+emit** — painter-ordered TikZ body (``sheaf.vector.emit_tikz``)
4. **document** — wrap in a compilable standalone (``tikz_document``)

Triangle throughput is reported as ``tris / s`` for the BSP-dominated
phase; ``docs/performance.md`` snapshots the most recent baseline.

The surfaces chosen intentionally stress different parts of the mesher:

* Paraboloid — smooth convex, near-uniform density, reveals the BSP's
  average-case cost.
* Monkey saddle — a single degenerate critical point at the origin,
  forces the refinement indicator to concentrate triangles near 0.
* Torus — genuine 2π-periodic parametric bounds, closed in both
  directions once seam-welded.
"""

from __future__ import annotations

import time
from dataclasses import dataclass

import sympy as sp
from sympy.abc import u, v, x, y

from sheaf import Blueprint, Chalkboard, Glass, Material, Surface
from sheaf.numeric import adaptive_mesh, compiled
from sheaf.vector import Camera, emit_tikz, tikz_document


@dataclass(frozen=True, slots=True)
class Case:
    name: str
    surface: Surface
    material: Material
    base_n: int
    max_depth: int


def _paraboloid() -> Surface:
    return Surface(z=x**2 + y**2, x=(-1, 1), y=(-1, 1))


def _monkey_saddle() -> Surface:
    return Surface(z=x**3 - 3 * x * y**2, x=(-1, 1), y=(-1, 1))


def _torus() -> Surface:
    return Surface(
        (
            (sp.Rational(2) + sp.Rational(7, 10) * sp.cos(v)) * sp.cos(u),
            (sp.Rational(2) + sp.Rational(7, 10) * sp.cos(v)) * sp.sin(u),
            sp.Rational(7, 10) * sp.sin(v),
        ),
        u=(0.0, float(2 * sp.pi)),
        v=(0.0, float(2 * sp.pi)),
    )


def _cases() -> tuple[Case, ...]:
    pb, ms, tr = _paraboloid(), _monkey_saddle(), _torus()
    return (
        Case("paraboloid   coarse", pb, Chalkboard, base_n=4, max_depth=0),
        Case("paraboloid   medium", pb, Chalkboard, base_n=6, max_depth=1),
        Case("paraboloid   fine  ", pb, Chalkboard, base_n=8, max_depth=2),
        Case("monkey saddle coarse", ms, Blueprint, base_n=4, max_depth=0),
        Case("monkey saddle medium", ms, Blueprint, base_n=6, max_depth=1),
        Case("monkey saddle fine  ", ms, Blueprint, base_n=8, max_depth=2),
        Case("torus         coarse", tr, Glass, base_n=6, max_depth=0),
        Case("torus         medium", tr, Glass, base_n=10, max_depth=0),
        Case("torus         fine  ", tr, Glass, base_n=14, max_depth=0),
    )


def _measure(case: Case) -> tuple[int, float, float, float, float, int]:
    """Return ``(n_triangles, t_compile, t_mesh, t_emit, t_doc, body_chars)``."""
    t0 = time.perf_counter()
    cs = compiled(case.surface)
    t1 = time.perf_counter()
    mesh = adaptive_mesh(cs, base_n=case.base_n, max_depth=case.max_depth)
    t2 = time.perf_counter()
    body = emit_tikz(mesh, Camera.isometric(distance=6.0), case.material)
    t3 = time.perf_counter()
    src = tikz_document(body)
    t4 = time.perf_counter()
    return (mesh.n_triangles, t1 - t0, t2 - t1, t3 - t2, t4 - t3, len(src))


def run() -> None:
    cases = _cases()
    header = (
        f"{'case':<24} {'tris':>6} {'compile':>9} {'mesh':>8} "
        f"{'emit':>9} {'doc':>7} {'tri/s (emit)':>14} {'kB':>7}"
    )
    print("=" * len(header), flush=True)
    print(header, flush=True)
    print("-" * len(header), flush=True)
    for case in cases:
        tris, tc, tm, te, td, src_bytes = _measure(case)
        throughput = tris / te if te > 0 else float("inf")
        print(
            f"{case.name:<24} {tris:>6} "
            f"{tc * 1000:>7.1f}ms {tm * 1000:>6.1f}ms "
            f"{te * 1000:>7.1f}ms {td * 1000:>5.1f}ms "
            f"{throughput:>12,.0f}  {src_bytes / 1024:>7.0f}",
            flush=True,
        )
    print("=" * len(header), flush=True)


if __name__ == "__main__":
    run()
