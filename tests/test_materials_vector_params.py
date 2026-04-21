"""Material → VectorParams resolution — Month 3 W10.

Both the TikZ emitter and the PGFPlots emitter pull their per-figure
defaults from :func:`sheaf.materials.resolve_vector_params`.  These
tests lock the defaults and the derivation rules so the two emitters
cannot silently drift apart.
"""

from __future__ import annotations

from types import MappingProxyType

from sheaf.materials import (
    DEFAULT_SURFACE_FILL,
    Blueprint,
    Chalkboard,
    Glass,
    Material,
    resolve_vector_params,
)


def test_resolve_with_no_material_uses_defaults() -> None:
    p = resolve_vector_params(None)
    assert p.surface_fill == DEFAULT_SURFACE_FILL
    assert p.wire_color is None
    assert p.wire_width_pt == 0.3
    assert p.alpha == 1.0
    assert p.boundary_glow is False
    assert p.hatch_pattern is None
    assert p.shows_edges is False
    assert p.is_translucent is False
    assert p.has_hatch is False


def test_resolve_chalkboard_carries_hatch_and_no_glow() -> None:
    p = resolve_vector_params(Chalkboard)
    assert p.surface_fill == "#2b3a2e"
    assert p.wire_color == "white"
    assert p.alpha == 1.0
    assert p.is_translucent is False
    assert p.has_hatch is True
    assert p.hatch_pattern == "crosshatch dots"
    # Hatch colour derives from wire_color when unspecified.
    assert p.hatch_color == "white"
    assert p.boundary_glow is False


def test_resolve_blueprint_has_neither_hatch_nor_glow() -> None:
    p = resolve_vector_params(Blueprint)
    assert p.has_hatch is False
    assert p.boundary_glow is False
    assert p.is_translucent is True
    assert p.alpha == 0.85


def test_resolve_glass_has_boundary_glow_with_explicit_colour() -> None:
    p = resolve_vector_params(Glass)
    assert p.boundary_glow is True
    assert p.boundary_glow_color == "#eaf6ff"
    assert p.is_translucent is True
    assert p.has_hatch is False


def test_boundary_glow_colour_defaults_to_wire_colour_when_absent() -> None:
    """A custom material that flips ``boundary_glow`` on but omits the
    explicit accent colour must fall back to ``wire_color``."""
    m = Material(
        name="custom",
        params=MappingProxyType(
            {
                "surface_fill": "#222222",
                "wire_color": "#ff8800",
                "boundary_glow": True,
            }
        ),
    )
    p = resolve_vector_params(m)
    assert p.boundary_glow_color == "#ff8800"


def test_boundary_glow_colour_falls_back_to_surface_fill_without_wire() -> None:
    m = Material(
        name="custom",
        params=MappingProxyType(
            {"surface_fill": "#112233", "boundary_glow": True}
        ),
    )
    p = resolve_vector_params(m)
    assert p.boundary_glow_color == "#112233"


def test_hatch_colour_defaults_to_wire_colour_when_absent() -> None:
    m = Material(
        name="custom",
        params=MappingProxyType(
            {
                "surface_fill": "#222222",
                "wire_color": "#ffffff",
                "hatch_pattern": "north east lines",
            }
        ),
    )
    p = resolve_vector_params(m)
    assert p.hatch_color == "#ffffff"


def test_explicit_boundary_glow_colour_overrides_derivation() -> None:
    m = Material(
        name="custom",
        params=MappingProxyType(
            {
                "surface_fill": "#222222",
                "wire_color": "#ff8800",
                "boundary_glow": True,
                "boundary_glow_color": "#ffffff",
            }
        ),
    )
    p = resolve_vector_params(m)
    assert p.boundary_glow_color == "#ffffff"


def test_alpha_and_wire_width_are_floats() -> None:
    m = Material(
        name="custom",
        params=MappingProxyType(
            {"surface_fill": "#222222", "alpha": 1, "wire_width": 1}
        ),
    )
    p = resolve_vector_params(m)
    assert isinstance(p.alpha, float)
    assert isinstance(p.wire_width_pt, float)
    assert p.alpha == 1.0
    assert p.wire_width_pt == 1.0
