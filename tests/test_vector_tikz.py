"""TikZ emitter — Month 2 W8 validation (+ Month 2 gate).

Unit tests cover the deterministic parts (camera projection, emitter
syntax, fragment-count / fill-count coupling).  The gate test
``test_surface_tikz_document_compiles_under_pdflatex`` is the Month 2
deliverable: a real surface goes through adaptive mesh → BSP sort →
TikZ → ``pdflatex`` without error.  The test skips if no LaTeX engine
is on ``PATH``.
"""

from __future__ import annotations

import numpy as np
import pytest
from sympy.abc import x, y

from sheaf import Blueprint, Chalkboard, Glass, Surface
from sheaf.numeric import adaptive_mesh, compiled
from sheaf.numeric.mesh import AdaptiveMesh
from sheaf.vector import Camera, emit_tikz, tikz_document
from sheaf.vector.tikz import _hex6

# ---------------------------------------------------------------------------
# Camera projection
# ---------------------------------------------------------------------------


def test_camera_projects_target_to_origin() -> None:
    cam = Camera(
        position=np.array([1.0, 1.0, 1.0]),
        target=np.array([0.0, 0.0, 0.0]),
        up=np.array([0.0, 0.0, 1.0]),
    )
    xy = cam.project(np.array([[0.0, 0.0, 0.0]]))
    assert xy.shape == (1, 2)
    assert np.allclose(xy, 0.0, atol=1e-12)


def test_camera_basis_is_orthonormal() -> None:
    cam = Camera.isometric(distance=4.0)
    r, u, f = cam.basis()
    for v in (r, u, f):
        assert abs(np.linalg.norm(v) - 1.0) < 1e-12
    assert abs(float(r @ u)) < 1e-12
    assert abs(float(r @ f)) < 1e-12
    assert abs(float(u @ f)) < 1e-12


def test_isometric_camera_view_direction_is_diagonal() -> None:
    cam = Camera.isometric(distance=10.0)
    expected = np.array([1.0, 1.0, 1.0]) / np.sqrt(3.0)
    assert np.allclose(cam.forward(), expected, atol=1e-12)


def test_parallel_up_and_view_direction_raises() -> None:
    bad = Camera(
        position=np.array([0.0, 0.0, 1.0]),
        target=np.array([0.0, 0.0, 0.0]),
        up=np.array([0.0, 0.0, 1.0]),
    )
    with pytest.raises(ValueError, match="parallel"):
        bad.project(np.zeros((1, 3)))


# ---------------------------------------------------------------------------
# Hex colour normalisation
# ---------------------------------------------------------------------------


def test_hex6_accepts_long_form() -> None:
    assert _hex6("#AABBCC") == "aabbcc"


def test_hex6_expands_short_form() -> None:
    assert _hex6("#abc") == "aabbcc"


def test_hex6_resolves_named_colors() -> None:
    assert _hex6("white") == "ffffff"
    assert _hex6("BLACK") == "000000"


def test_hex6_rejects_unknown_name() -> None:
    with pytest.raises(ValueError, match="not a hex"):
        _hex6("puce")


# ---------------------------------------------------------------------------
# emit_tikz — output shape and syntax
# ---------------------------------------------------------------------------


def _simple_mesh() -> AdaptiveMesh:
    return adaptive_mesh(
        compiled(Surface(z=x * y, x=(-1, 1), y=(-1, 1))), base_n=4
    )


def test_emit_tikz_wraps_in_tikzpicture() -> None:
    body = emit_tikz(_simple_mesh(), Camera.isometric(distance=5.0))
    assert body.startswith("\\begin{tikzpicture}")
    assert body.rstrip().endswith("\\end{tikzpicture}")


def test_emit_tikz_defines_fill_color() -> None:
    body = emit_tikz(_simple_mesh(), Camera.isometric(distance=5.0), Chalkboard)
    assert "\\definecolor{sheaffill}{HTML}{2b3a2e}" in body


def test_emit_tikz_emits_edge_color_for_chalkboard() -> None:
    """Chalkboard's wire_color = "white" must round-trip to #ffffff."""
    body = emit_tikz(_simple_mesh(), Camera.isometric(distance=5.0), Chalkboard)
    assert "\\definecolor{sheafedge}{HTML}{ffffff}" in body
    assert "draw=sheafedge" in body


def test_emit_tikz_omits_edge_for_material_without_wire() -> None:
    """A material lacking wire_color must not reference sheafedge."""
    from types import MappingProxyType

    from sheaf.materials import Material

    plain = Material(
        name="plain",
        params=MappingProxyType({"surface_fill": "#ff00ff", "alpha": 1.0}),
    )
    body = emit_tikz(_simple_mesh(), Camera.isometric(distance=5.0), plain)
    assert "sheafedge" not in body
    assert "draw=" not in body


def test_emit_tikz_fill_count_matches_bsp_fragment_count() -> None:
    """Every BSP fragment gets exactly one \\fill command."""
    from sheaf.vector.bsp import painter_sort

    mesh = _simple_mesh()
    cam = Camera.isometric(distance=5.0)
    fragments = painter_sort(mesh, np.asarray(cam.position, dtype=float))
    body = emit_tikz(mesh, cam)
    assert body.count("\\fill") == len(fragments)


def test_emit_tikz_glass_includes_opacity() -> None:
    """Glass.alpha = 0.55 must surface as TikZ ``fill opacity=0.550``."""
    body = emit_tikz(_simple_mesh(), Camera.isometric(distance=5.0), Glass)
    assert "fill opacity=0.550" in body


def test_emit_tikz_blueprint_carries_expected_hex() -> None:
    body = emit_tikz(_simple_mesh(), Camera.isometric(distance=5.0), Blueprint)
    assert "\\definecolor{sheaffill}{HTML}{0b3d6b}" in body


# ---------------------------------------------------------------------------
# Month 2 gate — pdflatex / lualatex real compilation
# ---------------------------------------------------------------------------


@pytest.mark.latex
def test_minimal_emitted_body_compiles(compile_tex) -> None:  # type: ignore[no-untyped-def]
    """One very coarse surface → TikZ → standalone pdflatex compile.

    This is the W8 Month 2 gate: if this test fails the vector pipeline
    is not publication-ready.  ``max_depth=0`` keeps the mesh at the
    base resolution so the gate validates the *pipeline* rather than
    BSP-on-22k-triangle throughput (a Month 3 W12 perf concern)."""
    mesh = adaptive_mesh(
        compiled(Surface(z=x**2 + y**2, x=(-1, 1), y=(-1, 1))),
        base_n=4,
        max_depth=0,
    )
    body = emit_tikz(mesh, Camera.isometric(distance=6.0), Chalkboard)
    src = tikz_document(body)
    proc = compile_tex(src)
    assert proc.returncode == 0, (
        f"LaTeX compile failed:\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    )


@pytest.mark.latex
@pytest.mark.parametrize(
    "material", [Chalkboard, Blueprint, Glass], ids=lambda m: m.name
)
def test_every_material_compiles_under_tikz(compile_tex, material) -> None:  # type: ignore[no-untyped-def]
    """Every shipped material preset must survive a real LaTeX compile."""
    mesh = adaptive_mesh(
        compiled(Surface(z=x * y, x=(-1, 1), y=(-1, 1))),
        base_n=3,
        max_depth=0,
    )
    body = emit_tikz(mesh, Camera.isometric(distance=5.0), material)
    src = tikz_document(body)
    proc = compile_tex(src)
    assert proc.returncode == 0, (
        f"{material.name}: compile failed\n{proc.stdout}\n{proc.stderr}"
    )
