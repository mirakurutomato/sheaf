"""PGFPlots emitter — Month 3 W9 validation.

Mirrors :mod:`tests.test_vector_tikz` for the second vector backend.
The unit tests cover the deterministic parts (camera→view conversion,
emitter envelope, coordinate count, material option translation); the
parametrised LaTeX gate test is the W9 deliverable: the emitted body
must compile under both ``pdflatex`` and ``lualatex`` for every shipped
material preset.
"""

from __future__ import annotations

import math

import numpy as np
import pytest
from sympy.abc import x, y

from sheaf import Blueprint, Chalkboard, Glass, Surface
from sheaf.numeric import adaptive_mesh, compiled
from sheaf.numeric.mesh import AdaptiveMesh
from sheaf.vector import Camera, emit_pgfplots, pgfplots_document, view_from_camera

# ---------------------------------------------------------------------------
# view_from_camera
# ---------------------------------------------------------------------------


def test_isometric_camera_yields_canonical_view() -> None:
    az, el = view_from_camera(Camera.isometric(distance=10.0))
    assert az == pytest.approx(45.0, abs=1e-6)
    assert el == pytest.approx(math.degrees(math.asin(1 / math.sqrt(3))), abs=1e-6)


def test_top_down_camera_has_ninety_degree_elevation() -> None:
    cam = Camera(
        position=np.array([0.0, 0.0, 5.0]),
        target=np.array([0.0, 0.0, 0.0]),
        up=np.array([0.0, 1.0, 0.0]),
    )
    _, el = view_from_camera(cam)
    assert el == pytest.approx(90.0, abs=1e-6)


def test_side_camera_has_zero_elevation() -> None:
    cam = Camera(
        position=np.array([5.0, 0.0, 0.0]),
        target=np.array([0.0, 0.0, 0.0]),
        up=np.array([0.0, 0.0, 1.0]),
    )
    az, el = view_from_camera(cam)
    assert az == pytest.approx(0.0, abs=1e-6)
    assert el == pytest.approx(0.0, abs=1e-6)


# ---------------------------------------------------------------------------
# emit_pgfplots — output shape and syntax
# ---------------------------------------------------------------------------


def _simple_mesh() -> AdaptiveMesh:
    return adaptive_mesh(
        compiled(Surface(z=x * y, x=(-1, 1), y=(-1, 1))),
        base_n=4,
        max_depth=0,
    )


def test_emit_pgfplots_wraps_in_axis_inside_tikzpicture() -> None:
    body = emit_pgfplots(_simple_mesh())
    assert body.startswith("\\begin{tikzpicture}")
    assert "\\begin{axis}" in body
    assert "\\end{axis}" in body
    assert body.rstrip().endswith("\\end{tikzpicture}")


def test_emit_pgfplots_emits_three_coords_per_triangle() -> None:
    mesh = _simple_mesh()
    body = emit_pgfplots(mesh)
    # Coordinates are rendered as "(x,y,z)" lines after the opening "{".
    coord_lines = [
        line for line in body.splitlines() if line.lstrip().startswith("(")
    ]
    assert len(coord_lines) == 3 * len(mesh.triangles)


def test_emit_pgfplots_uses_patch_triangle_directive() -> None:
    body = emit_pgfplots(_simple_mesh(), Camera.isometric())
    assert "patch type=triangle" in body
    assert "shader=flat" in body


def test_emit_pgfplots_defines_material_fill() -> None:
    body = emit_pgfplots(_simple_mesh(), Camera.isometric(), Chalkboard)
    assert "\\definecolor{sheaffill}{HTML}{2b3a2e}" in body
    assert "fill=sheaffill" in body


def test_emit_pgfplots_emits_edge_color_for_chalkboard() -> None:
    body = emit_pgfplots(_simple_mesh(), Camera.isometric(), Chalkboard)
    assert "\\definecolor{sheafedge}{HTML}{ffffff}" in body
    assert "draw=sheafedge" in body


def test_emit_pgfplots_omits_edge_for_material_without_wire() -> None:
    from types import MappingProxyType

    from sheaf.materials import Material

    plain = Material(
        name="plain",
        params=MappingProxyType({"surface_fill": "#ff00ff", "alpha": 1.0}),
    )
    body = emit_pgfplots(_simple_mesh(), Camera.isometric(), plain)
    assert "sheafedge" not in body
    assert "draw=none" in body


def test_emit_pgfplots_glass_includes_opacity() -> None:
    body = emit_pgfplots(_simple_mesh(), Camera.isometric(), Glass)
    assert "fill opacity=0.550" in body


def test_emit_pgfplots_view_string_carries_camera_angles() -> None:
    body = emit_pgfplots(_simple_mesh(), Camera.isometric(distance=4.0))
    az, el = view_from_camera(Camera.isometric(distance=4.0))
    assert f"view={{{az:.3f}}}{{{el:.3f}}}" in body


# ---------------------------------------------------------------------------
# W10 — Glass boundary glow and Chalkboard hatch degradation
# ---------------------------------------------------------------------------


def test_emit_pgfplots_glass_emits_boundary_glow_addplots() -> None:
    """``Glass`` on an open surface must surface accent edges as separate
    ``\\addplot3`` line plots after the patch directive."""
    body = emit_pgfplots(_simple_mesh(), Camera.isometric(), Glass)
    assert "\\definecolor{sheafglow}{HTML}{eaf6ff}" in body
    assert "draw=sheafglow" in body
    assert "no marks" in body
    assert "forget plot" in body


def test_emit_pgfplots_no_glow_when_material_disables_it() -> None:
    from types import MappingProxyType

    from sheaf.materials import Material

    plain = Material(
        name="plain",
        params=MappingProxyType(
            {"surface_fill": "#ff00ff", "boundary_glow": False}
        ),
    )
    body = emit_pgfplots(_simple_mesh(), Camera.isometric(), plain)
    assert "sheafglow" not in body


def test_emit_pgfplots_glass_on_closed_mesh_emits_no_glow_addplots() -> None:
    """A closed tetrahedron has no open boundary: the glow colour is
    defined but zero boundary ``\\addplot3`` commands are emitted."""
    points = np.array(
        [[1.0, 1.0, 1.0], [-1.0, -1.0, 1.0], [-1.0, 1.0, -1.0], [1.0, -1.0, -1.0]],
        dtype=float,
    )
    tris = np.array(
        [[0, 2, 1], [0, 1, 3], [0, 3, 2], [1, 2, 3]],
        dtype=np.int64,
    )
    params_ignored = np.zeros((4, 2))
    mesh = AdaptiveMesh(params=params_ignored, points=points, triangles=tris)
    body = emit_pgfplots(mesh, Camera.isometric(), Glass)
    assert "\\definecolor{sheafglow}" in body
    assert "draw=sheafglow" not in body


def test_emit_pgfplots_chalkboard_hatch_is_silently_dropped() -> None:
    """Chalkboard sets ``hatch_pattern`` but PGFPlots' flat patch shader
    cannot render it; the emitter must degrade to the solid fill rather
    than emit an invalid ``pattern=...`` directive that would explode
    under LaTeX compile."""
    body = emit_pgfplots(_simple_mesh(), Camera.isometric(), Chalkboard)
    assert "pattern=" not in body
    assert "sheafhatch" not in body
    # The solid fill is still present.
    assert "\\definecolor{sheaffill}{HTML}{2b3a2e}" in body


# ---------------------------------------------------------------------------
# Document wrapper
# ---------------------------------------------------------------------------


def test_pgfplots_document_loads_pgfplots_package() -> None:
    src = pgfplots_document("\\begin{tikzpicture}\\end{tikzpicture}\n")
    assert "\\usepackage{pgfplots}" in src
    assert "\\pgfplotsset{compat=" in src
    assert "\\documentclass[tikz,border=2pt]{standalone}" in src


# ---------------------------------------------------------------------------
# W9 LaTeX gate — real pdflatex / lualatex compilation
# ---------------------------------------------------------------------------


@pytest.mark.latex
@pytest.mark.parametrize(
    "material", [Chalkboard, Blueprint, Glass], ids=lambda m: m.name
)
def test_every_material_compiles_under_pgfplots(compile_tex, material) -> None:  # type: ignore[no-untyped-def]
    """Every shipped material must survive a real PGFPlots compile."""
    mesh = adaptive_mesh(
        compiled(Surface(z=x**2 + y**2, x=(-1, 1), y=(-1, 1))),
        base_n=3,
        max_depth=0,
    )
    body = emit_pgfplots(mesh, Camera.isometric(distance=6.0), material)
    src = pgfplots_document(body)
    proc = compile_tex(src)
    assert proc.returncode == 0, (
        f"{material.name}: PGFPlots compile failed\n"
        f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    )
