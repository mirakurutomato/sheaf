"""Academic material presets. Each is a frozen value, invoked by bare name.

    Surface(z=f) @ Chalkboard
    torus @ Blueprint
    mobius @ Glass

Materials are intentionally minimal at this stage: a name and a parameter dict.
The actual shading model is resolved by the vector pipeline (Month 2+) when
baking into TikZ / PGFPlots.
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass, field
from types import MappingProxyType
from typing import Any


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
    note="chalky matte shading with white wireframe",
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
    note="translucent glass manifold with glowing self-intersection boundary",
)
