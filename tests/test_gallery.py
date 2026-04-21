"""Gallery catalog — Month 3 W12 smoke tests.

Every entry in ``examples/gallery_catalog.py`` is exercised here *without*
invoking LaTeX.  The purpose is twofold:

* guarantee that the 12 curated figures never regress through silent
  pipeline changes (mesh shapes, emitter options, material defaults),
* keep the fast ``ci`` job fast — real ``pdflatex`` compilation for a
  representative subset lives in :mod:`tests.test_gallery_latex`.

The catalog lives outside the ``sheaf`` package (it is example code, not
library code), so this test file inserts ``examples/`` into ``sys.path``
at module load time.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
if str(_EXAMPLES) not in sys.path:
    sys.path.insert(0, str(_EXAMPLES))

from gallery_catalog import GalleryItem, gallery_items  # noqa: E402

from sheaf import Blueprint, Chalkboard, Glass  # noqa: E402
from sheaf.numeric import adaptive_mesh, compiled  # noqa: E402
from sheaf.vector import emit_tikz, tikz_document  # noqa: E402

_ITEMS = gallery_items()


# ---------------------------------------------------------------------------
# Catalog-level invariants
# ---------------------------------------------------------------------------


def test_gallery_has_at_least_twelve_items() -> None:
    assert len(_ITEMS) >= 12


def test_gallery_names_are_unique_slugs() -> None:
    names = [it.name for it in _ITEMS]
    assert len(set(names)) == len(names)
    for n in names:
        assert n.replace("_", "").isalnum(), f"non-slug name {n!r}"


def test_gallery_covers_all_three_materials() -> None:
    by_mat = {it.material.name for it in _ITEMS}
    assert by_mat == {Chalkboard.name, Blueprint.name, Glass.name}


def test_gallery_material_balance_is_at_least_three_per_preset() -> None:
    """Every shipped material must be represented by at least three
    items so a reader sees each finish across varied geometry."""
    counts: dict[str, int] = {}
    for it in _ITEMS:
        counts[it.material.name] = counts.get(it.material.name, 0) + 1
    for mat in (Chalkboard.name, Blueprint.name, Glass.name):
        assert counts.get(mat, 0) >= 3, f"material {mat} under-represented: {counts}"


def test_gallery_mixes_explicit_and_parametric_surfaces() -> None:
    kinds = {it.surface.kind for it in _ITEMS}
    assert "explicit" in kinds
    assert "parametric" in kinds


# ---------------------------------------------------------------------------
# Per-item pipeline smoke
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("item", _ITEMS, ids=lambda it: it.name)
def test_item_meshes_and_emits_tikz(item: GalleryItem) -> None:
    """Every catalog entry must lower into a non-empty mesh + TikZ body."""
    cs = compiled(item.surface)
    mesh = adaptive_mesh(cs, base_n=item.base_n, max_depth=item.max_depth)
    assert mesh.n_vertices > 0
    assert mesh.n_triangles > 0

    body = emit_tikz(mesh, item.camera, item.material)
    src = tikz_document(body)

    assert body.startswith("\\begin{tikzpicture}")
    assert body.rstrip().endswith("\\end{tikzpicture}")
    assert "\\definecolor{sheaffill}" in body

    assert "\\documentclass[tikz,border=2pt]{standalone}" in src
    assert "\\usetikzlibrary{patterns}" in src
    assert "\\begin{document}" in src
    assert "\\end{document}" in src


@pytest.mark.parametrize("item", _ITEMS, ids=lambda it: it.name)
def test_item_respects_material_signatures(item: GalleryItem) -> None:
    """Each material preset must leave its W10 fingerprint on the body."""
    cs = compiled(item.surface)
    mesh = adaptive_mesh(cs, base_n=item.base_n, max_depth=item.max_depth)
    body = emit_tikz(mesh, item.camera, item.material)

    if item.material.name == "chalkboard":
        # W10: Chalkboard is the only shipped preset that emits a hatch.
        assert "pattern=crosshatch dots" in body
    elif item.material.name == "glass":
        # Glass is always translucent.
        assert "fill opacity=" in body
    elif item.material.name == "blueprint":
        # Blueprint never emits a hatch, only a draw edge.
        assert "pattern=" not in body
        assert "draw=sheafedge" in body
