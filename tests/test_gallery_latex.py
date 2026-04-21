"""Gallery catalog — Month 3 W12 LaTeX gate (subset).

Three representative gallery items are compiled under both ``pdflatex`` and
``lualatex`` (via the parametrised ``compile_tex`` fixture).  The selection
exercises the features most likely to break a publication build:

* ``monkey_saddle`` — Chalkboard hatch (TikZ ``patterns`` library)
* ``mobius_strip`` — Glass boundary glow on an open surface (W10 strokes)
* ``klein_bottle`` — Blueprint on a closed, self-intersecting immersion

The remaining nine items are covered by the emit-only smoke in
:mod:`tests.test_gallery`; compiling every catalog entry under two engines
would double the CI gate with very little marginal coverage.
"""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

_EXAMPLES = Path(__file__).resolve().parents[1] / "examples"
if str(_EXAMPLES) not in sys.path:
    sys.path.insert(0, str(_EXAMPLES))

from gallery_catalog import GalleryItem, gallery_items  # noqa: E402

from sheaf.numeric import adaptive_mesh, compiled  # noqa: E402
from sheaf.vector import emit_tikz, tikz_document  # noqa: E402

_SUBSET = ("monkey_saddle", "mobius_strip", "klein_bottle")

_BY_NAME = {it.name: it for it in gallery_items()}
_GATE_ITEMS = tuple(_BY_NAME[name] for name in _SUBSET)


@pytest.mark.latex
@pytest.mark.parametrize("item", _GATE_ITEMS, ids=lambda it: it.name)
def test_gallery_item_compiles(compile_tex, item: GalleryItem) -> None:  # type: ignore[no-untyped-def]
    """Each representative gallery item must survive a real LaTeX run."""
    cs = compiled(item.surface)
    mesh = adaptive_mesh(cs, base_n=item.base_n, max_depth=item.max_depth)
    body = emit_tikz(mesh, item.camera, item.material)
    src = tikz_document(body)
    proc = compile_tex(src)
    assert proc.returncode == 0, (
        f"{item.name}: LaTeX compile failed\n"
        f"stdout:\n{proc.stdout[-1500:]}\n"
        f"stderr:\n{proc.stderr[-500:]}"
    )
