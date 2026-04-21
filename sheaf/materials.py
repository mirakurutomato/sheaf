"""Academic material presets. Each is a frozen value, invoked by bare name.

    Surface(z=f) @ Chalkboard
    torus @ Blueprint
    mobius @ Glass

Materials are intentionally minimal at this stage: a name and a parameter dict.
The actual shading model is resolved by the vector pipeline (Month 2+) when
baking into TikZ / PGFPlots.

The vector pipeline reads its subset of ``Material.params`` through
:func:`resolve_vector_params`, which fills in defaults in a single place.
Both the TikZ emitter and the PGFPlots emitter consume the resulting
:class:`VectorParams` so the two backends cannot drift apart as the
material schema grows.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any

# ---------------------------------------------------------------------------
# Material preset
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Material:
    """A semantic material preset (Chalkboard, Blueprint, Glass, ...)."""

    name: str
    params: Mapping[str, Any] = field(default_factory=lambda: MappingProxyType({}))

    def __repr__(self) -> str:
        return self.name.capitalize()


def _preset(name: str, **params: Any) -> Material:
    return Material(name=name, params=MappingProxyType(dict(params)))


Chalkboard: Material = _preset(
    "chalkboard",
    surface_fill="#2b3a2e",
    wire_color="white",
    wire_width=0.3,
    alpha=1.0,
    hatch_pattern="crosshatch dots",
    note="chalky matte shading with white wireframe and chalk-dust hatching",
)

Blueprint: Material = _preset(
    "blueprint",
    surface_fill="#0b3d6b",
    wire_color="#d6ecff",
    wire_width=0.2,
    alpha=0.85,
    note="cyan-on-navy draughtsman's blueprint",
)

Glass: Material = _preset(
    "glass",
    surface_fill="#9cc8dd",
    wire_color="#2a8bbf",
    wire_width=0.15,
    alpha=0.55,
    boundary_glow=True,
    boundary_glow_color="#eaf6ff",
    note="translucent glass manifold with glowing open-boundary rim",
)


# ---------------------------------------------------------------------------
# Vector-pipeline parameter resolution
# ---------------------------------------------------------------------------


DEFAULT_SURFACE_FILL = "#c8cdd4"
"""Fallback surface fill when no :class:`Material` is supplied."""


@dataclass(frozen=True, slots=True)
class VectorParams:
    """Resolved material parameters for the TikZ / PGFPlots backends.

    Both emitters read this struct rather than ``Material.params`` so
    defaults and coercions live in one place.  Fields only widen over
    time — additions never change the meaning of existing ones.
    """

    surface_fill: str
    wire_color: str | None
    wire_width_pt: float
    alpha: float
    boundary_glow: bool
    boundary_glow_color: str
    hatch_pattern: str | None
    hatch_color: str

    @property
    def shows_edges(self) -> bool:
        return self.wire_color is not None

    @property
    def is_translucent(self) -> bool:
        return self.alpha < 1.0

    @property
    def has_hatch(self) -> bool:
        return self.hatch_pattern is not None


def resolve_vector_params(material: Material | None) -> VectorParams:
    """Return a :class:`VectorParams` for the vector emitters.

    When ``material`` is ``None``, every field falls back to its default:
    neutral surface fill, no wire, opaque, no boundary glow, no hatch.
    When ``material`` is given, its ``params`` override the defaults; any
    key not supplied by ``params`` keeps its default.  Derived defaults
    (e.g. ``boundary_glow_color`` falling back to ``wire_color`` when set)
    are resolved here so the emitters see a fully-populated record.
    """
    p = material.params if material is not None else {}

    surface_fill = p.get("surface_fill", DEFAULT_SURFACE_FILL)
    wire_color = p.get("wire_color")
    wire_width_pt = float(p.get("wire_width", 0.3))
    alpha = float(p.get("alpha", 1.0))

    boundary_glow = bool(p.get("boundary_glow", False))
    boundary_glow_color = p.get("boundary_glow_color")
    if boundary_glow_color is None:
        boundary_glow_color = wire_color if wire_color is not None else surface_fill

    hatch_pattern = p.get("hatch_pattern")
    hatch_color = p.get("hatch_color")
    if hatch_color is None:
        hatch_color = wire_color if wire_color is not None else surface_fill

    return VectorParams(
        surface_fill=surface_fill,
        wire_color=wire_color,
        wire_width_pt=wire_width_pt,
        alpha=alpha,
        boundary_glow=boundary_glow,
        boundary_glow_color=boundary_glow_color,
        hatch_pattern=hatch_pattern,
        hatch_color=hatch_color,
    )
