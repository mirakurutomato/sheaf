"""Gallery catalog — Month 3 W12.

Twelve curated surfaces that together exercise every branch of the vector
pipeline built in Months 1-3:

* explicit ``z=f(x,y)`` (Months 1) vs. parametric ``(u,v)->R^3`` (Month 1)
* open bounded surfaces (glass boundary glow on) vs. closed ones (glow off)
* orientable vs. non-orientable (Möbius, Klein) parametrisations
* isolated singularities (monkey saddle, Whitney umbrella) vs. smooth bulk
* all three shipped materials (Chalkboard, Blueprint, Glass) — four each

The roadmap listed "geodesic" and "Gauss map" as further examples; those
require a ``Curve`` vector emitter, which is not part of the W8/W9 pipeline.
Deferred to a future milestone and noted in ``docs/gallery.md``.

Each entry is a :class:`GalleryItem` that ``build_gallery.py`` and
``tests/test_gallery.py`` iterate over uniformly, so adding a new surface
is a one-line diff in this file.

This module is **importable-only** — running it directly prints a one-line
summary of every catalog entry but does not produce any rendered output.
The build driver lives in ``examples/build_gallery.py``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import sympy as sp
from sympy.abc import u, v, x, y

from sheaf import Blueprint, Chalkboard, Glass, Material, Surface
from sheaf.vector import Camera

type Engine = Literal["tikz", "pgfplots"]


@dataclass(frozen=True, slots=True)
class GalleryItem:
    """A single publication-grade figure recipe.

    Attributes
    ----------
    name:
        Short slug used as the output filename stem.
    title:
        Human-readable title for documentation.
    surface:
        The :class:`~sheaf.Surface` (explicit or parametric).
    material:
        The :class:`~sheaf.materials.Material` preset.
    camera:
        The :class:`~sheaf.vector.Camera` to project through.
    base_n / max_depth:
        Adaptive-mesh resolution knobs.  Kept per-item so a cheap smoke
        test can iterate the whole catalog in seconds while a real gallery
        build can turn the dial up.
    description:
        One-line description used in ``docs/gallery.md``.
    """

    name: str
    title: str
    surface: Surface
    material: Material
    camera: Camera
    base_n: int
    max_depth: int
    description: str


def _explicit_saddle() -> Surface:
    return Surface(z=x**3 - 3 * x * y**2, x=(-1, 1), y=(-1, 1))


def _explicit_hyperbolic() -> Surface:
    return Surface(z=x**2 - y**2, x=(-1, 1), y=(-1, 1))


def _explicit_paraboloid() -> Surface:
    return Surface(z=x**2 + y**2, x=(-1, 1), y=(-1, 1))


def _mobius() -> Surface:
    radius = sp.Rational(1)
    return Surface(
        (
            (radius + v / 2 * sp.cos(u / 2)) * sp.cos(u),
            (radius + v / 2 * sp.cos(u / 2)) * sp.sin(u),
            v / 2 * sp.sin(u / 2),
        ),
        u=(0.0, float(2 * sp.pi)),
        v=(-0.4, 0.4),
    )


def _torus() -> Surface:
    big = sp.Rational(2)
    small = sp.Rational(7, 10)
    return Surface(
        (
            (big + small * sp.cos(v)) * sp.cos(u),
            (big + small * sp.cos(v)) * sp.sin(u),
            small * sp.sin(v),
        ),
        u=(0.0, float(2 * sp.pi)),
        v=(0.0, float(2 * sp.pi)),
    )


def _klein_bottle() -> Surface:
    """Figure-8 (Lawson) immersion of the Klein bottle.

    ``r`` controls the overall radius; the parametrisation closes up
    along ``u`` at 2π and self-identifies with a twist along ``v``.  The
    mesher treats the domain as a rectangle, which is what we want for a
    single-view publication figure (the seam is visually informative).
    """
    r = sp.Rational(2)
    expr = (
        (r + sp.cos(u / 2) * sp.sin(v) - sp.sin(u / 2) * sp.sin(2 * v)) * sp.cos(u),
        (r + sp.cos(u / 2) * sp.sin(v) - sp.sin(u / 2) * sp.sin(2 * v)) * sp.sin(u),
        sp.sin(u / 2) * sp.sin(v) + sp.cos(u / 2) * sp.sin(2 * v),
    )
    return Surface(
        expr,
        u=(0.0, float(2 * sp.pi)),
        v=(0.0, float(2 * sp.pi)),
    )


def _sphere() -> Surface:
    return Surface(
        (sp.sin(u) * sp.cos(v), sp.sin(u) * sp.sin(v), sp.cos(u)),
        u=(0.0, float(sp.pi)),
        v=(0.0, float(2 * sp.pi)),
    )


def _helicoid() -> Surface:
    return Surface(
        (v * sp.cos(u), v * sp.sin(u), u / 2),
        u=(-float(sp.pi), float(sp.pi)),
        v=(-1.0, 1.0),
    )


def _enneper() -> Surface:
    return Surface(
        (
            u - u**3 / 3 + u * v**2,
            v - v**3 / 3 + v * u**2,
            u**2 - v**2,
        ),
        u=(-1.0, 1.0),
        v=(-1.0, 1.0),
    )


def _dini() -> Surface:
    """Dini's surface — a pseudospherical surface of revolution-with-twist.

    ``v`` is kept away from 0 and π because the parametrisation involves
    ``ln tan(v/2)`` which diverges at both ends.  The chosen window gives
    two full turns along ``u`` and a clean pseudospherical strip along v.
    """
    a = sp.Rational(1, 5)
    expr = (
        sp.cos(u) * sp.sin(v),
        sp.sin(u) * sp.sin(v),
        sp.cos(v) + sp.ln(sp.tan(v / 2)) + a * u,
    )
    return Surface(
        expr,
        u=(0.0, float(4 * sp.pi)),
        v=(0.6, 1.5),
    )


def _whitney_umbrella() -> Surface:
    """Whitney umbrella: ``(u*v, u, v**2)`` — the canonical A^2/2 singularity."""
    return Surface(
        (u * v, u, v**2),
        u=(-1.0, 1.0),
        v=(-1.0, 1.0),
    )


def _catenoid() -> Surface:
    return Surface(
        (sp.cosh(v) * sp.cos(u), sp.cosh(v) * sp.sin(u), v),
        u=(0.0, float(2 * sp.pi)),
        v=(-1.0, 1.0),
    )


def gallery_items() -> tuple[GalleryItem, ...]:
    """Return the full 12-item catalog."""
    cam_small = Camera.isometric(distance=6.0)
    cam_medium = Camera.isometric(distance=10.0)
    cam_large = Camera.isometric(distance=16.0)

    return (
        GalleryItem(
            name="monkey_saddle",
            title="Monkey saddle",
            surface=_explicit_saddle(),
            material=Chalkboard,
            camera=cam_small,
            base_n=5,
            max_depth=0,
            description=(
                "Explicit cubic z=x^3-3xy^2 with a degenerate critical "
                "point at the origin — the canonical three-fold saddle."
            ),
        ),
        GalleryItem(
            name="hyperbolic_saddle",
            title="Hyperbolic paraboloid",
            surface=_explicit_hyperbolic(),
            material=Blueprint,
            camera=cam_small,
            base_n=6,
            max_depth=0,
            description=(
                "Explicit quadratic z=x^2-y^2 — the baseline non-degenerate "
                "saddle, used here to sanity-check the blueprint material."
            ),
        ),
        GalleryItem(
            name="paraboloid",
            title="Elliptic paraboloid",
            surface=_explicit_paraboloid(),
            material=Chalkboard,
            camera=cam_small,
            base_n=5,
            max_depth=0,
            description=(
                "Explicit z=x^2+y^2 with Chalkboard finish — the same "
                "surface used by the Month 2 LaTeX gate, here shown as a "
                "publication-grade cut-out."
            ),
        ),
        GalleryItem(
            name="mobius_strip",
            title="Möbius strip",
            surface=_mobius(),
            material=Glass,
            camera=cam_small,
            base_n=6,
            max_depth=0,
            description=(
                "Non-orientable bounded strip; Glass surfaces its two open "
                "boundary circles as an accent glow (W10)."
            ),
        ),
        GalleryItem(
            name="torus",
            title="Torus",
            surface=_torus(),
            material=Glass,
            camera=cam_medium,
            base_n=8,
            max_depth=0,
            description=(
                "Closed orientable genus-1 surface.  Topologically boundary-"
                "free: Glass emits the translucent fill without glow strokes."
            ),
        ),
        GalleryItem(
            name="klein_bottle",
            title="Klein bottle (figure-8 immersion)",
            surface=_klein_bottle(),
            material=Blueprint,
            camera=cam_medium,
            base_n=8,
            max_depth=0,
            description=(
                "The Lawson figure-8 immersion of the Klein bottle into R^3; "
                "the visible seams at u=0 and u=2π are artefacts of drawing "
                "a rectangular parameter patch of a genuinely non-embeddable "
                "surface and carry useful topological information."
            ),
        ),
        GalleryItem(
            name="sphere",
            title="Unit sphere",
            surface=_sphere(),
            material=Chalkboard,
            camera=cam_small,
            base_n=6,
            max_depth=0,
            description=(
                "Unit sphere sampled on its (θ, φ) patch.  Closed after "
                "seam-welding (Month 2 W5); the mesher's pole handling is "
                "exercised by the Chalkboard edges."
            ),
        ),
        GalleryItem(
            name="helicoid",
            title="Helicoid",
            surface=_helicoid(),
            material=Blueprint,
            camera=cam_small,
            base_n=6,
            max_depth=0,
            description=(
                "Ruled minimal surface (x,y,z) = (v cos u, v sin u, u/2).  "
                "Blueprint renders the wireframe characteristic of "
                "architectural drawings."
            ),
        ),
        GalleryItem(
            name="enneper",
            title="Enneper surface",
            surface=_enneper(),
            material=Glass,
            camera=cam_small,
            base_n=6,
            max_depth=0,
            description=(
                "Classical complete minimal surface with two self-"
                "intersections.  The painter's algorithm resolves the "
                "visible lobe without any special-casing."
            ),
        ),
        GalleryItem(
            name="dini",
            title="Dini's surface",
            surface=_dini(),
            material=Chalkboard,
            camera=cam_medium,
            base_n=8,
            max_depth=0,
            description=(
                "Pseudospherical spiral with Gaussian curvature K=-1.  The "
                "parametrisation skirts the log(tan(v/2)) pole at v=0 by "
                "clipping v to [0.6, 1.5]."
            ),
        ),
        GalleryItem(
            name="whitney_umbrella",
            title="Whitney umbrella",
            surface=_whitney_umbrella(),
            material=Blueprint,
            camera=cam_small,
            base_n=6,
            max_depth=0,
            description=(
                "(uv, u, v^2) — the simplest self-intersecting algebraic "
                "surface; the Jacobian rank drops along the v-axis, which "
                "the mesher refines toward automatically."
            ),
        ),
        GalleryItem(
            name="catenoid",
            title="Catenoid",
            surface=_catenoid(),
            material=Glass,
            camera=cam_large,
            base_n=6,
            max_depth=0,
            description=(
                "Surface of revolution of a catenary; minimal, complete, "
                "and (topologically) an open cylinder — Glass highlights "
                "the two circular boundaries with a glow pass."
            ),
        ),
    )


def _print_summary() -> None:
    items = gallery_items()
    print(f"Sheaf gallery: {len(items)} curated surfaces")
    print("=" * 72)
    print(f"{'#':>2}  {'name':<20} {'material':<11} {'kind':<11} title")
    print("-" * 72)
    for i, it in enumerate(items, start=1):
        title_ascii = it.title.encode("ascii", errors="replace").decode("ascii")
        print(
            f"{i:>2}  {it.name:<20} {it.material.name:<11} "
            f"{it.surface.kind:<11} {title_ascii}"
        )
    print("=" * 72)
    print("This module is data-only.  Render the catalog with:")
    print("    python examples/build_gallery.py")


if __name__ == "__main__":
    _print_summary()
