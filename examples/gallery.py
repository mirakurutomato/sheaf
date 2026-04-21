"""Render the sheaf preview gallery (PNG screenshots).

Run from the repo root:

    .venv/Scripts/python examples/gallery.py

Outputs land in `examples/gallery/*.png`.
"""

from __future__ import annotations

from pathlib import Path

import sympy as sp
from sympy.abc import phi, t, theta, u, v, x, y

from sheaf import Blueprint, Chalkboard, Curve, Glass, Surface
from sheaf.preview import screenshot

OUT = Path(__file__).parent / "gallery"
OUT.mkdir(exist_ok=True)


def monkey_saddle() -> None:
    """z = x³ − 3xy² — the classic umbilic at the origin, in chalk."""
    saddle = Surface(z=x**3 - 3 * x * y**2, x=(-1.2, 1.2), y=(-1.2, 1.2))
    screenshot(saddle @ Chalkboard, str(OUT / "monkey_saddle.png"))


def torus() -> None:
    """Parametric torus dressed in blueprint cyan-on-navy."""
    R, r = 1.0, 0.35
    torus_surf = Surface(
        (
            (R + r * sp.cos(v)) * sp.cos(u),
            (R + r * sp.cos(v)) * sp.sin(u),
            r * sp.sin(v),
        ),
        u=(0.0, float(2 * sp.pi)),
        v=(0.0, float(2 * sp.pi)),
    )
    screenshot(torus_surf @ Blueprint, str(OUT / "torus.png"))


def mobius() -> None:
    """Möbius strip through translucent glass to expose the non-orientable twist."""
    strip = Surface(
        (
            (1 + v / 2 * sp.cos(u / 2)) * sp.cos(u),
            (1 + v / 2 * sp.cos(u / 2)) * sp.sin(u),
            v / 2 * sp.sin(u / 2),
        ),
        u=(0.0, float(2 * sp.pi)),
        v=(-1.0, 1.0),
    )
    screenshot(strip @ Glass, str(OUT / "mobius.png"))


def sphere_with_helix() -> None:
    """Sphere + helix composed through `+`, each carrying its own material."""
    sphere = Surface(
        (sp.sin(phi) * sp.cos(theta), sp.sin(phi) * sp.sin(theta), sp.cos(phi)),
        phi=(0.0, float(sp.pi)),
        theta=(0.0, float(2 * sp.pi)),
    )
    helix = Curve(
        (1.4 * sp.cos(4 * t), 1.4 * sp.sin(4 * t), 0.9 * sp.sin(2 * t)),
        t=(0.0, float(2 * sp.pi)),
    )
    scene = sphere @ Blueprint + helix @ Chalkboard
    screenshot(scene, str(OUT / "sphere_helix.png"))


def main() -> None:
    for fn in (monkey_saddle, torus, mobius, sphere_with_helix):
        print(f"rendering {fn.__name__}...")
        fn()
    print(f"done: {OUT}")


if __name__ == "__main__":
    main()
