# Gallery — Month 3 W12

Twelve curated surfaces covering explicit graphs, parametric embeddings,
closed topology, non-orientable strips, isolated singularities, and
every shipped material preset.  The canonical definitions live at
[`examples/gallery_catalog.py`](../examples/gallery_catalog.py); the
build driver that emits each item as a standalone `.tex` (and `.pdf`
when `pdflatex` is on `PATH`) is
[`examples/build_gallery.py`](../examples/build_gallery.py).

```sh
.venv/Scripts/python examples/build_gallery.py
```

Run that to regenerate everything.  Individual items can also be
constructed in a REPL by iterating over `gallery_items()`.

## Catalog

| # | Name | Surface | Material | Notes |
|---|------|---------|----------|-------|
| 1 | [`monkey_saddle`](#1-monkey-saddle)         | explicit `z = x³ − 3xy²`              | Chalkboard | order-3 singularity at the origin |
| 2 | [`hyperbolic_saddle`](#2-hyperbolic-saddle) | explicit `z = x² − y²`                 | Blueprint  | non-degenerate saddle baseline |
| 3 | [`paraboloid`](#3-paraboloid)               | explicit `z = x² + y²`                 | Chalkboard | convex bowl; Month 2 gate subject |
| 4 | [`mobius_strip`](#4-mobius-strip)           | parametric `u ∈ [0, 2π], v ∈ [−0.4, 0.4]` | Glass  | non-orientable; exercises glow |
| 5 | [`torus`](#5-torus)                         | parametric `(u, v) ∈ [0, 2π]²`         | Glass      | closed genus-1; no glow |
| 6 | [`klein_bottle`](#6-klein-bottle)           | figure-8 immersion, `(u, v) ∈ [0, 2π]²` | Blueprint | non-orientable immersion, visible seams |
| 7 | [`sphere`](#7-sphere)                       | `(θ, φ)` patch                         | Chalkboard | closed after seam-welding |
| 8 | [`helicoid`](#8-helicoid)                   | `(v cos u, v sin u, u/2)`              | Blueprint  | ruled minimal surface |
| 9 | [`enneper`](#9-enneper)                     | classical cubic parametric minimal      | Glass      | self-intersecting lobes |
| 10 | [`dini`](#10-dini)                         | pseudospherical spiral                 | Chalkboard | `K = −1`; v-clipped |
| 11 | [`whitney_umbrella`](#11-whitney-umbrella) | `(uv, u, v²)`                          | Blueprint  | `A²/2` singularity |
| 12 | [`catenoid`](#12-catenoid)                 | `(cosh v cos u, cosh v sin u, v)`      | Glass      | open cylinder; glow on both rims |

## Usage pattern

Every item follows the same pipeline — DSL object → numeric compile →
adaptive mesh → painter-ordered vector body → standalone document:

```python
from sheaf import Chalkboard, Surface
from sheaf.numeric import adaptive_mesh, compiled
from sheaf.vector import Camera, emit_tikz, tikz_document
from sympy.abc import x, y

surface = Surface(z=x**3 - 3*x*y**2, x=(-1, 1), y=(-1, 1))
mesh    = adaptive_mesh(compiled(surface), base_n=5, max_depth=0)
body    = emit_tikz(mesh, Camera.isometric(distance=6.0), Chalkboard)
source  = tikz_document(body)  # compilable standalone
```

The `sheaf.paper.Paper` facade wraps the same pipeline and adds host
`main.tex` parsing:

```python
from sheaf import Chalkboard, Paper, Surface
from sympy.abc import x, y

artifact = Surface(z=x**2 + y**2) @ Chalkboard >> Paper("main.tex")
open("fig.tex", "w").write(artifact.source)
```

## Per-item notes

### 1. Monkey saddle

`z = x³ − 3xy²` on `[−1, 1]²`.  The critical point at the origin has
rank-zero Jacobian; the refinement indicator concentrates triangles
around it automatically.  Chalkboard's hatch pattern disambiguates the
three saddle lobes.

### 2. Hyperbolic saddle

`z = x² − y²` on `[−1, 1]²`.  A baseline quadratic surface used to
sanity-check the Blueprint preset and the mesher's default density on
smooth geometry.

### 3. Paraboloid

`z = x² + y²` on `[−1, 1]²` — the same surface the Month 2 LaTeX gate
compiles.  Rendered here under Chalkboard so the hatch and wireframe
cues read clearly.

### 4. Möbius strip

`u ∈ [0, 2π], v ∈ [−0.4, 0.4]`:

$$x = (1 + \tfrac{v}{2}\cos\tfrac{u}{2})\cos u,\quad y = (1 + \tfrac{v}{2}\cos\tfrac{u}{2})\sin u,\quad z = \tfrac{v}{2}\sin\tfrac{u}{2}.$$

The seam at `u = 0 = 2π` is not identified by the mesher; that shows
the underlying parameter patch honestly — Glass's boundary glow pass
highlights the two open-edge circles the strip inherits from its
fundamental domain.

### 5. Torus

Major radius `R = 2`, minor `r = 0.7`, both angles sweep `[0, 2π]`.
After seam-welding (Month 2 W5) the surface has no boundary — the
Glass material therefore emits translucent fill but zero glow strokes,
a behaviour locked by `test_emit_tikz_glass_on_closed_mesh_emits_no_glow_strokes`.

### 6. Klein bottle

Lawson figure-8 immersion `R³`-embedded:

$$\begin{aligned}
x &= (r + \cos\tfrac{u}{2}\sin v - \sin\tfrac{u}{2}\sin 2v)\cos u, \\
y &= (r + \cos\tfrac{u}{2}\sin v - \sin\tfrac{u}{2}\sin 2v)\sin u, \\
z &= \sin\tfrac{u}{2}\sin v + \cos\tfrac{u}{2}\sin 2v.
\end{aligned}$$

The bottle genuinely cannot embed in `R³`; the seams at `u = 0` and
`v = 0` are intrinsic to any rectangular parameter patch and carry
topological information worth showing.

### 7. Sphere

`(sin θ cos φ, sin θ sin φ, cos θ)`, `θ ∈ [0, π]`, `φ ∈ [0, 2π]`.  The
poles are parametric degeneracies (rank-1 Jacobian); the mesher refines
away from them automatically.  Chalkboard edges expose the resulting
latitude-spaced meshing pattern.

### 8. Helicoid

`(v cos u, v sin u, u/2)` on `u ∈ [−π, π]`, `v ∈ [−1, 1]`: a classical
ruled minimal surface.  Blueprint emphasises the straight rulings.

### 9. Enneper surface

Cubic parametric minimal surface on `[−1, 1]²`.  Self-intersects when
the domain is extended; the restricted patch avoids that but still
shows the characteristic four-fold symmetry.  Glass lets the overlapping
lobes read as overlapping rather than being flattened by fill.

### 10. Dini's surface

`(cos u sin v, sin u sin v, cos v + ln tan(v/2) + 0.2 u)` on
`u ∈ [0, 4π]`, `v ∈ [0.6, 1.5]`.  Pseudospherical (Gaussian curvature
`K = −1`); the `v` clip avoids the log pole at `v = 0`.

### 11. Whitney umbrella

`(u·v, u, v²)` on `[−1, 1]²`.  The Jacobian rank drops to 1 along
`{u = 0}`; one of the simplest self-intersecting algebraic surfaces.
Blueprint draws the rulings and the axis of self-intersection clearly.

### 12. Catenoid

`(cosh v cos u, cosh v sin u, v)` on `u ∈ [0, 2π]`, `v ∈ [−1, 1]`.
Surface of revolution of a catenary; a complete minimal surface
topologically equivalent to an open cylinder.  Glass's boundary glow
surfaces both circular rims.

## Omissions (roadmap items deferred)

The Month 1 roadmap listed "geodesic" and "Gauss map" as further
gallery targets.  Both need a vector emitter for `sheaf.Curve` — the
DSL object compiles to a `CompiledCurve` today but the W8/W9 emitters
only accept `AdaptiveMesh`.  That plumbing is a W13+ item; until then
the gallery stays surface-only.
