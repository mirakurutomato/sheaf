"""Hessian-driven accent lighting — Month 2 W6 validation.

These tests operate on :class:`~sheaf.numeric.curvature.CriticalPoint`
fixtures directly: the lighting mapping is pure data and independent of
any rendering backend.  The rendering-side integration (wiring into the
PyVista driver) lands with the material rewrite in W10.
"""

from __future__ import annotations

from sympy.abc import x, y

from sheaf import Surface
from sheaf.numeric import CriticalPoint, classify_critical_points, compiled
from sheaf.preview import AccentLight, accent_lights


def _unit_bbox() -> tuple[
    tuple[float, float], tuple[float, float], tuple[float, float]
]:
    return ((-1.0, 1.0), (-1.0, 1.0), (-1.0, 1.0))


# ---------------------------------------------------------------------------
# Empty / degenerate short-circuits
# ---------------------------------------------------------------------------


def test_no_critical_points_gives_no_lights() -> None:
    assert accent_lights([], _unit_bbox()) == []


def test_degenerate_point_is_skipped() -> None:
    """A degenerate Hessian (monkey saddle) leaves the default ambient alone."""
    deg = CriticalPoint(
        param=(0.0, 0.0),
        point=(0.0, 0.0, 0.0),
        eigenvalues=(0.0, 0.0),
        kind="degenerate",
    )
    assert accent_lights([deg], _unit_bbox()) == []


# ---------------------------------------------------------------------------
# Per-kind lighting grammar
# ---------------------------------------------------------------------------


def test_minimum_gets_warm_key_from_above() -> None:
    """Minimum → warm key light positioned above the point (+z offset)."""
    bowl = Surface(z=x**2 + y**2, x=(-1, 1), y=(-1, 1))
    cps = classify_critical_points(compiled(bowl))
    lights = accent_lights(cps, _unit_bbox())
    assert len(lights) == 1
    light = lights[0]
    assert isinstance(light, AccentLight)
    assert light.kind == "key"
    assert light.position[2] > cps[0].point[2], "key light must be above the minimum"
    # Warm colour: red > blue in hex.
    r = int(light.color[1:3], 16)
    b = int(light.color[5:7], 16)
    assert r > b, f"key light should be warm, got {light.color}"


def test_maximum_gets_cool_rim_from_below() -> None:
    """Maximum → cool rim light positioned below the point (−z offset)."""
    hill = Surface(z=-(x**2 + y**2), x=(-1, 1), y=(-1, 1))
    cps = classify_critical_points(compiled(hill))
    lights = accent_lights(cps, _unit_bbox())
    assert len(lights) == 1
    light = lights[0]
    assert light.kind == "rim"
    assert light.position[2] < cps[0].point[2], "rim light must be below the maximum"
    r = int(light.color[1:3], 16)
    b = int(light.color[5:7], 16)
    assert b > r, f"rim light should be cool, got {light.color}"


def test_saddle_gets_neutral_grazing_rim() -> None:
    """Saddle → neutral rim offset to one side for a grazing shadow terminator."""
    saddle = Surface(z=x**2 - y**2, x=(-1, 1), y=(-1, 1))
    cps = classify_critical_points(compiled(saddle))
    lights = accent_lights(cps, _unit_bbox())
    assert len(lights) == 1
    light = lights[0]
    assert light.kind == "rim"
    # Neutral: |r − b| small; roughly grey.
    r = int(light.color[1:3], 16)
    g = int(light.color[3:5], 16)
    b = int(light.color[5:7], 16)
    assert abs(r - b) < 16 and abs(r - g) < 16, f"saddle rim should be neutral, got {light.color}"


def test_target_always_equals_critical_point() -> None:
    """Each light must aim at its critical point; otherwise the accent misses."""
    for expr, kind in (
        (x**2 + y**2, "minimum"),
        (-(x**2 + y**2), "maximum"),
        (x**2 - y**2, "saddle"),
    ):
        surf = Surface(z=expr, x=(-1, 1), y=(-1, 1))
        cps = classify_critical_points(compiled(surf))
        lights = accent_lights(cps, _unit_bbox())
        assert len(lights) == 1, f"expected 1 light for {kind}"
        assert lights[0].target == cps[0].point


def test_offset_scales_with_bounding_box_diagonal() -> None:
    """Doubling the bbox doubles the offset magnitude of every accent."""
    bowl = Surface(z=x**2 + y**2, x=(-1, 1), y=(-1, 1))
    cps = classify_critical_points(compiled(bowl))
    small = accent_lights(cps, ((-1.0, 1.0), (-1.0, 1.0), (-1.0, 1.0)))
    large = accent_lights(cps, ((-2.0, 2.0), (-2.0, 2.0), (-2.0, 2.0)))
    dz_small = small[0].position[2] - cps[0].point[2]
    dz_large = large[0].position[2] - cps[0].point[2]
    assert abs(dz_large - 2.0 * dz_small) < 1e-9, "offset must be linear in diagonal"
