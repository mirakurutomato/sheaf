# Performance baseline — Month 3 W12

This document records the first end-to-end timing pass on `sheaf`'s DSL →
vector pipeline.  The goal is **not** to set performance targets
(none of the M1–M3 gates specify a throughput requirement) but to give
future milestones a reference point against which regressions — or
genuine improvements — can be judged.

The harness lives at [`benchmarks/bench_pipeline.py`](../benchmarks/bench_pipeline.py)
and is explicitly excluded from CI; measure locally before and after any
change you suspect touches pipeline hot paths.

## Machine & environment

| Field | Value |
| --- | --- |
| Date | 2026-04-22 |
| CPU | Windows 11 x86-64 (user laptop) |
| Python | 3.12.10 |
| `sheaf` | 0.0.1 (W11 tip) |
| NumPy | 1.26+ |

Numbers below are single-shot; treat ±20% as noise.

## Per-phase timings

Three representative surfaces — a smooth convex paraboloid, the monkey
saddle with its order-3 singularity at the origin, and the torus as a
closed-periodic fixture — were swept through the pipeline at three
mesh budgets each.

| case                 | tris | compile | mesh    | emit (BSP+TikZ) | doc  | tri/s (emit) | kB body |
|----------------------|-----:|--------:|--------:|----------------:|-----:|-------------:|--------:|
| paraboloid   coarse  |  128 |   11 ms |    5 ms |           91 ms | 0 ms |        1,409 |      33 |
| paraboloid   medium  |  816 |    3 ms |   35 ms |        3,520 ms | 0 ms |          232 |     209 |
| paraboloid   fine    | 8192 |    2 ms |  400 ms |      272,377 ms | 0 ms |           30 |   2,101 |
| monkey saddle coarse |  128 |    6 ms |    5 ms |           76 ms | 0 ms |        1,675 |      41 |
| monkey saddle medium |  778 |    3 ms |   36 ms |          735 ms | 0 ms |        1,058 |     383 |
| monkey saddle fine   | 6296 |    2 ms |  761 ms |        8,570 ms | 0 ms |          735 |   3,692 |
| torus         coarse |  240 |    8 ms |    8 ms |          289 ms | 0 ms |          832 |      72 |
| torus         medium |  800 |    3 ms |   28 ms |        2,296 ms | 0 ms |          348 |     255 |
| torus         fine   | 1568 |    3 ms |   56 ms |        8,301 ms | 0 ms |          189 |     534 |

## Findings

### BSP is the dominant cost, and it's quadratic on some surfaces

The `emit` column — which subsumes BSP construction + painter sort +
TikZ codegen — accounts for **95–99.9 % of wall time** on every case
and scales **quadratically** in the number of input triangles.

The paraboloid is the pathological case: a 64 × scale-up in triangle
count (128 → 8192) inflates emit time by 3,000 × (91 ms → 272 s).  That
ratio is consistent with the worst-case `O(n²)` behaviour of BSP when
the splitting plane heuristic fails to partition the front cleanly —
exactly what happens on a smooth bowl-shaped surface where most
triangles sit on the same side of almost any cutting plane.

The monkey saddle scales better (≈ 113 × time for 50 × triangles), and
the torus sits in the middle — both benefit from their geometry
naturally separating triangles along the view direction.

### Mesh refinement is linear and already fast

Rivara LEB refinement (`sheaf.numeric.adaptive_mesh`) stayed linear in
triangle count across every case, hitting ~20 k triangles/s in
NumPy-bound loops.  It is not on any foreseeable critical path.

### Compile and document-wrap are free

Symbolic → NumPy lowering runs in a handful of milliseconds (the cost is
dominated by SymPy's `lambdify` cold-start; subsequent calls in the
same interpreter session reuse the cache).  Wrapping the body in a
standalone document is literal string concatenation and disappears
into the timing noise.

## Implications for the gallery

The [`examples/gallery/catalog.py`](../examples/gallery/catalog.py)
resolutions were chosen with this baseline in mind.  Every catalog item
uses `base_n ∈ {5, 6, 8}` and `max_depth = 0`, keeping individual emit
phases under one second on the reference machine.  The two LaTeX gate
subsets (Month 2 gate + W12 gallery subset) together stay under a
minute of wall time per engine.

Pushing to 10 k-triangle renders is possible but currently requires
minutes of patience — **not** a one-shot change for interactive
authoring.  Addressing this is the obvious next optimisation target.

## Next optimisation targets (future milestones)

1. **Bucket BSP splits by view-direction sign** to convert the inner
   `O(n)` scan to `O(log n)` when the surface is graph-like w.r.t. the
   view.  That alone would cut the paraboloid 8k case from minutes to
   seconds without changing output.
2. **Short-circuit triangle-triangle overlap** in painter's-algorithm
   tie-breaks; the current back-to-front test touches every pair.
3. **Cython/Numba hot loop** around the splitting plane intersection if
   the first two fail to move the needle.

None of the three are scoped into the current 12-week plan — they would
belong to a follow-up milestone once the DSL surface (Curve, Implicit,
Scene composition with multiple geometries) is complete.
