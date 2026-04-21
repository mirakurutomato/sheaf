"""Visual regression — Month 1 W4 delivery.

The vector pipeline (TikZ / PGFPlots) lands in Month 2. Until then, "visual
regression" means two complementary things:

1. **Material translation** is pure-Python and deterministic — test that the
   semantic preset (`Chalkboard`, `Blueprint`, `Glass`) maps to the expected
   PyVista kwargs.  Breaks show up here before any pixels are touched.

2. **End-to-end preview rendering** must actually paint the surface in the
   right hue family.  A headless screenshot is cropped, the dominant non-
   background colour is measured, and we assert it sits inside the material's
   expected hue region.

Why not pixel-exact regression at this stage?  VTK / GPU driver variation
makes byte-identity cross-machine unreachable; the deterministic pixel-diff
target is the PDF output from the Month 3 vector pipeline (ghostscript + PIL).
"""

from __future__ import annotations

import numpy as np
import pytest
from sympy.abc import x, y

pytest.importorskip("pyvista")
_Image = pytest.importorskip("PIL.Image")

from sheaf import Blueprint, Chalkboard, Glass, Material, Surface  # noqa: E402
from sheaf.preview import screenshot  # noqa: E402
from sheaf.preview.pyvista_driver import _curve_kwargs, _surface_kwargs  # noqa: E402

pytestmark = pytest.mark.preview


# ---------------------------------------------------------------------------
# Material → kwargs (deterministic, no rendering)
# ---------------------------------------------------------------------------


def test_surface_kwargs_none_is_neutral_grey() -> None:
    """No material → neutral mid-grey, diffuse-dominated plastic-ish shading."""
    k = _surface_kwargs(None)
    assert k["color"] == "#c8cdd4"
    assert k["smooth_shading"] is True
    assert k["diffuse"] > k["ambient"]
    assert k["specular"] > 0


@pytest.mark.parametrize(
    "material,shows_edges",
    [(Chalkboard, True), (Blueprint, True), (Glass, False)],
    ids=["chalkboard", "blueprint", "glass"],
)
def test_surface_kwargs_honours_material_contract(
    material: Material, shows_edges: bool
) -> None:
    """Chalk / Blueprint expose a wireframe; Glass is translucent without edges."""
    k = _surface_kwargs(material)
    assert k["color"] == material.params["surface_fill"]
    assert k.get("show_edges", False) is shows_edges
    assert k["opacity"] == material.params["alpha"]
    assert k["smooth_shading"] is True


def test_curve_kwargs_stay_ink_dark() -> None:
    """Curves must read as ink on white paper: luminance well below mid-grey."""
    for m in (None, Chalkboard, Blueprint, Glass):
        k = _curve_kwargs(m)
        r, g, b = (int(k["color"][i : i + 2], 16) for i in (1, 3, 5))
        luminance = 0.2126 * r + 0.7152 * g + 0.0722 * b
        assert luminance < 120, f"{k['color']} luma {luminance:.0f} too bright for paper"
        assert k["render_lines_as_tubes"] is True
        assert k["line_width"] >= 5


# ---------------------------------------------------------------------------
# End-to-end rendering regression
# ---------------------------------------------------------------------------


def _hex_to_rgb(h: str) -> tuple[int, int, int]:
    return int(h[1:3], 16), int(h[3:5], 16), int(h[5:7], 16)


def _load_rgb(path: str) -> np.ndarray:
    return np.asarray(_Image.open(path).convert("RGB"), dtype=np.float32)


@pytest.mark.parametrize(
    "material", [Chalkboard, Blueprint, Glass], ids=lambda m: m.name
)
def test_screenshot_contains_material_hue(tmp_path, material: Material) -> None:
    """Render a paraboloid per material and assert the PNG carries a visible
    fraction of pixels in that material's hue family.  Guards against regressions
    in material dispatch, camera framing, lighting, and mesh visibility."""
    bowl = Surface(z=x**2 + y**2, x=(-1, 1), y=(-1, 1))
    png = tmp_path / f"{material.name}.png"
    screenshot(bowl @ material, str(png), size=(400, 400))
    assert png.exists() and png.stat().st_size > 1_000

    img = _load_rgb(str(png))
    target = np.asarray(_hex_to_rgb(material.params["surface_fill"]), dtype=np.float32)
    # Pixel-wise distance from the target fill colour.  Lighting + edges shift
    # individual pixels; a 60-unit tolerance accepts shaded material while
    # still rejecting default grey (≥130 away) and pure white (≥250 away).
    dist = np.linalg.norm(img - target, axis=-1)
    matching_frac = float((dist < 60.0).mean())
    assert matching_frac > 0.03, (
        f"material={material.name}: only {matching_frac:.2%} of pixels near "
        f"expected colour {material.params['surface_fill']}"
    )


def test_screenshot_is_not_blank(tmp_path) -> None:
    """Sanity: the saved PNG has meaningful variance (the scene actually rendered).
    A blank or single-colour image has near-zero per-channel std; shaded geometry
    easily clears 15 units."""
    bowl = Surface(z=x**2 + y**2, x=(-1, 1), y=(-1, 1))
    png = tmp_path / "variance.png"
    screenshot(bowl @ Chalkboard, str(png), size=(300, 300))
    img = _load_rgb(str(png))
    assert img.std() > 15.0, f"image looks blank (std={img.std():.1f})"
