"""Demonstrate Hessian-eigenvalue classification + accent-light placement.

Run from the repo root:

    .venv/Scripts/python examples/critical_points.py

Prints the critical points of five canonical surfaces with their Hessian
eigenvalues, classification, and the accent-light descriptors that would
be handed to the preview driver (PyVista wiring lands in W10).
"""

from __future__ import annotations

import sympy as sp
from sympy.abc import x, y

from sheaf import Surface
from sheaf.numeric import classify_critical_points, compiled
from sheaf.preview import accent_lights

# Canonical gallery: one surface per Hessian signature we handle, plus one
# case that *has no* critical points at all.
CASES: list[tuple[str, sp.Expr]] = [
    ("paraboloid      z = x^2 + y^2",         x**2 + y**2),
    ("inverted        z = -(x^2 + y^2)",      -(x**2 + y**2)),
    ("hyperbolic      z = x^2 - y^2",         x**2 - y**2),
    ("monkey saddle   z = x^3 - 3*x*y^2",     x**3 - 3 * x * y**2),
    ("tilted plane    z = 2x + 3y",           2 * x + 3 * y),
]

BBOX = ((-1.0, 1.0), (-1.0, 1.0), (-1.0, 1.0))


def _fmt_triple(t: tuple[float, ...]) -> str:
    return "(" + ", ".join(f"{v:+.4f}" for v in t) + ")"


def run() -> None:
    for name, expr in CASES:
        print("=" * 72)
        print(name)
        surface = Surface(z=expr, x=(-1, 1), y=(-1, 1))
        cps = classify_critical_points(compiled(surface))
        if not cps:
            print("  (no critical points in the domain)")
            continue
        for cp in cps:
            e0, e1 = cp.eigenvalues
            print(
                f"  [{cp.kind:<10}]  param={_fmt_triple(cp.param)}  "
                f"point={_fmt_triple(cp.point)}  eigs=({e0:+.4f}, {e1:+.4f})"
            )
        lights = accent_lights(cps, BBOX)
        if not lights:
            print("  (no accent lights - degenerate classification)")
        for lt in lights:
            print(
                f"    light[{lt.kind:<3}] pos={_fmt_triple(lt.position)}  "
                f"target={_fmt_triple(lt.target)}  color={lt.color}  "
                f"intensity={lt.intensity:.2f}"
            )


if __name__ == "__main__":
    run()
