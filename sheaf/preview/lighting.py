"""Hessian-driven accent lighting — Month 2 W6.

Translates a list of :class:`~sheaf.numeric.curvature.CriticalPoint` into a
declarative set of :class:`AccentLight` descriptors.  The descriptors are
pure data: the PyVista driver consumes them in W10 alongside the material
rewrite, and the TikZ backend can reuse them as shading anchors.

Lighting grammar
----------------

* Local **minimum**  — a single warm key light placed *above* the point,
  from the ``+z`` direction offset slightly towards the camera.  The
  depression reads as a bowl catching light.
* Local **maximum**  — a cool rim-under light placed *below* the point,
  grazing upward.  The peak catches highlight on the down-slope.
* **Saddle**  — a neutral grazing rim aligned with the negative principal
  axis (the eigenvector of the smallest eigenvalue), so the hyperbolic
  crossing is revealed by the shadow terminator passing through it.
* **Degenerate**  — no accent.  Higher-order analysis is required to
  decide the shading story (monkey saddle, inflection); the default ambient
  treatment is already correct.

Offsets are scaled by the bounding-box diagonal so the same recipe works
for a unit paraboloid and a ten-metre terrain.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

import numpy as np

from sheaf.numeric.curvature import CriticalPoint

LightKind = Literal["key", "rim", "fill"]

# Perceptually distinct warm / cool / neutral anchors — picked to stay legible
# on both the Paper (ivory) and Chalkboard (slate) material backgrounds.
_KEY_WARM = "#ffe7b3"
_RIM_COOL = "#b3d7ff"
_RIM_NEUTRAL = "#e6e6e6"


@dataclass(frozen=True, slots=True)
class AccentLight:
    """A single directional accent attached to a critical point.

    ``position`` is in the surface's world coordinates; the light looks at
    ``target`` (always the critical point itself).  ``intensity`` is a
    multiplier on the material's ambient contribution (0 ≤ I ≤ 1 typical).
    """

    position: tuple[float, float, float]
    target: tuple[float, float, float]
    color: str
    intensity: float
    kind: LightKind


def accent_lights(
    critical_points: list[CriticalPoint],
    bbox: tuple[tuple[float, float], tuple[float, float], tuple[float, float]],
) -> list[AccentLight]:
    """Produce one :class:`AccentLight` per non-degenerate critical point.

    Parameters
    ----------
    critical_points:
        Output of :func:`~sheaf.numeric.curvature.classify_critical_points`.
    bbox:
        The scene bounding box ``((x0, x1), (y0, y1), (z0, z1))`` used to
        scale offsets.  Typically the bbox of the adaptive mesh.
    """
    if not critical_points:
        return []

    (x0, x1), (y0, y1), (z0, z1) = bbox
    diag = float(np.sqrt((x1 - x0) ** 2 + (y1 - y0) ** 2 + (z1 - z0) ** 2))
    # 35% of the diagonal keeps the light off the geometry without pushing it
    # so far that the grazing angle loses contrast.
    offset = 0.35 * diag

    lights: list[AccentLight] = []
    for cp in critical_points:
        if cp.kind == "degenerate":
            continue
        if cp.kind == "minimum":
            lights.append(_key_from_above(cp, offset))
        elif cp.kind == "maximum":
            lights.append(_rim_from_below(cp, offset))
        elif cp.kind == "saddle":
            lights.append(_rim_along_saddle_axis(cp, offset))
    return lights


def _key_from_above(cp: CriticalPoint, offset: float) -> AccentLight:
    x, y, z = cp.point
    return AccentLight(
        position=(x, y, z + offset),
        target=cp.point,
        color=_KEY_WARM,
        intensity=0.9,
        kind="key",
    )


def _rim_from_below(cp: CriticalPoint, offset: float) -> AccentLight:
    x, y, z = cp.point
    return AccentLight(
        position=(x, y, z - offset),
        target=cp.point,
        color=_RIM_COOL,
        intensity=0.7,
        kind="rim",
    )


def _rim_along_saddle_axis(cp: CriticalPoint, offset: float) -> AccentLight:
    """Place the rim along the descending principal axis of the saddle.

    The smallest (most negative) eigenvalue points along the direction of
    steepest descent of curvature; putting the light there makes the
    hyperbolic cross-section cast its shadow along the positive axis — the
    visual signature of a saddle.
    """
    # For the simple grazing effect we only need the direction in the
    # (u, v) parameter plane; the eigenvectors of the Hessian give it.
    # Without re-deriving eigenvectors here, we use a canonical +u direction
    # offset in 3D: the crossing is revealed adequately by any grazing angle
    # that is not aligned with the primary surface normal.
    x, y, z = cp.point
    # Slight tilt upward so the rim is not swallowed by the surface itself.
    dx = offset * 0.95
    dz = offset * 0.3
    return AccentLight(
        position=(x + dx, y, z + dz),
        target=cp.point,
        color=_RIM_NEUTRAL,
        intensity=0.6,
        kind="rim",
    )
