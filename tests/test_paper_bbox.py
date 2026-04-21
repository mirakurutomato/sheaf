r"""Month 3 final gate — PDF bounding-box precision.

Roadmap (README, Month 3 validation): "ユーザーの実 main.tex に組み込んだ
状態で lualatex コンパイル成功 + バウンディングボックス誤差 1pt 未満".

This module verifies the bounding-box half of that statement directly
on the emitted standalone PDF: the ``MediaBox`` read out of the PDF
must equal the value we predicted from the projected mesh extent and
the emitter's ``scale_cm`` × ``border_pt`` parameters within **±1 pt**,
under both ``pdflatex`` and ``lualatex``.

The implementation deliberately avoids external PDF libraries.  Every
modern LaTeX engine stores ``/MediaBox`` inside a compressed object
stream near the document catalogue; a short zlib + regex walk is
enough to recover it.  Adding ``pypdf`` would buy a cleaner lookup for
exotic PDF features (annotations, inheritance), none of which apply to
the one-page standalone documents we emit.
"""

from __future__ import annotations

import re
import zlib
from pathlib import Path

import numpy as np
import pytest
from sympy.abc import x, y

from sheaf import Chalkboard, Surface
from sheaf.numeric import adaptive_mesh, compiled
from sheaf.vector import Camera, emit_tikz, tikz_document

_PT_PER_CM = 72.27 / 2.54  # TeX point per centimetre
_SCALE_CM = 2.0  # matches ``sheaf.vector.emit_tikz`` default
_BORDER_PT = 2  # matches ``sheaf.vector.tikz_document`` default


# ---------------------------------------------------------------------------
# PDF MediaBox extraction
# ---------------------------------------------------------------------------


_MEDIABOX_RE = re.compile(
    rb"/MediaBox\s*\[\s*([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s+([-\d.]+)\s*\]"
)
_STREAM_RE = re.compile(rb"stream\r?\n(.*?)\r?\nendstream", re.DOTALL)


def _read_mediabox(pdf_path: Path) -> tuple[float, float, float, float]:
    """Return ``(x0, y0, x1, y1)`` of the first page's MediaBox, in points.

    The PDFs produced by our pipeline are always single-page ``standalone``
    documents, so the first match is authoritative.
    """
    data = pdf_path.read_bytes()
    match = _MEDIABOX_RE.search(data)
    if match is None:
        for chunk in _STREAM_RE.finditer(data):
            try:
                decompressed = zlib.decompress(chunk.group(1))
            except zlib.error:
                continue
            match = _MEDIABOX_RE.search(decompressed)
            if match is not None:
                break
    if match is None:
        raise RuntimeError(f"no MediaBox found in {pdf_path}")
    return tuple(float(match.group(i)) for i in range(1, 5))  # type: ignore[return-value]


# ---------------------------------------------------------------------------
# Expected MediaBox: projected mesh extent × scale_cm + border
# ---------------------------------------------------------------------------


def _expected_mediabox(
    mesh_points: np.ndarray, camera: Camera
) -> tuple[float, float]:
    """Return the expected ``(width_pt, height_pt)`` of the standalone PDF."""
    projected = camera.project(mesh_points)
    xs, ys = projected[:, 0], projected[:, 1]
    width_cm = float(xs.max() - xs.min()) * _SCALE_CM
    height_cm = float(ys.max() - ys.min()) * _SCALE_CM
    width_pt = width_cm * _PT_PER_CM + 2 * _BORDER_PT
    height_pt = height_cm * _PT_PER_CM + 2 * _BORDER_PT
    return width_pt, height_pt


# ---------------------------------------------------------------------------
# Month 3 gate
# ---------------------------------------------------------------------------


@pytest.mark.latex
def test_paper_mediabox_matches_projection_within_1pt(compile_tex, tmp_path) -> None:  # type: ignore[no-untyped-def]
    """The standalone PDF's MediaBox equals the projected extent within 1 pt.

    The test runs twice (``pdflatex`` / ``lualatex``) through the
    parametrised ``latex_engine`` fixture; it also implicitly gates
    engine agreement since both must match the *same* computed
    expectation within tolerance.
    """
    cs = compiled(Surface(z=x**2 + y**2, x=(-1, 1), y=(-1, 1)))
    mesh = adaptive_mesh(cs, base_n=4, max_depth=0)
    camera = Camera.isometric(distance=6.0)

    body = emit_tikz(mesh, camera, Chalkboard)
    src = tikz_document(body, border_pt=_BORDER_PT)

    proc = compile_tex(src)
    assert proc.returncode == 0, (
        f"compile failed: stdout={proc.stdout[-1000:]!r} stderr={proc.stderr[-400:]!r}"
    )

    x0, y0, x1, y1 = _read_mediabox(tmp_path / "doc.pdf")
    measured_w = x1 - x0
    measured_h = y1 - y0
    expected_w, expected_h = _expected_mediabox(mesh.points, camera)

    assert abs(measured_w - expected_w) < 1.0, (
        f"width drift: measured={measured_w:.3f}pt expected={expected_w:.3f}pt"
    )
    assert abs(measured_h - expected_h) < 1.0, (
        f"height drift: measured={measured_h:.3f}pt expected={expected_h:.3f}pt"
    )
