"""Emit a TikZ figure for a quadratic surface and (optionally) compile it.

Run from the repo root::

    .venv/Scripts/python examples/tikz_emit.py

Pipeline:

* compile ``z = x^2 + y^2`` over ``[-1, 1]^2`` into a coarse adaptive mesh
  (refinement disabled so the example fits in a printable PDF and stays
  readable as raw TikZ),
* sort it back-to-front through the BSP painter,
* render under the ``Chalkboard`` material with the isometric camera,
* write ``examples/gallery/tikz_emit.tex`` (a minimal ``standalone`` doc),
* if ``pdflatex`` is on ``PATH``, compile it to
  ``examples/gallery/tikz_emit.pdf``.

The text echo at the end shows the figure's size budget so it is easy to
see when the BSP+TikZ pipeline starts producing too many ``\\fill`` paths
for the surrounding paper.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from sympy.abc import x, y

from sheaf import Chalkboard, Surface
from sheaf.numeric import adaptive_mesh, compiled
from sheaf.vector import Camera, emit_tikz, tikz_document

OUT_DIR = Path(__file__).parent / "gallery"


def run() -> None:
    surface = compiled(Surface(z=x**2 + y**2, x=(-1, 1), y=(-1, 1)))
    mesh = adaptive_mesh(surface, base_n=4, max_depth=0)
    camera = Camera.isometric(distance=6.0)

    body = emit_tikz(mesh, camera, Chalkboard)
    src = tikz_document(body)

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    tex_path = OUT_DIR / "tikz_emit.tex"
    tex_path.write_text(src, encoding="utf-8")

    fill_count = body.count("\\fill")
    print("=" * 72)
    print(f"mesh:       {len(mesh.points)} pts, {len(mesh.triangles)} tris")
    print(f"emitted:    {fill_count} \\fill paths, {len(src):,} chars")
    print(f"tex saved:  {tex_path}")

    pdflatex = shutil.which("pdflatex")
    if pdflatex is None:
        print("pdflatex:   not on PATH - skipping compile step")
        return

    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        (tmp_path / "fig.tex").write_text(src, encoding="utf-8")
        proc = subprocess.run(
            [
                pdflatex,
                "-interaction=nonstopmode",
                "-halt-on-error",
                "fig.tex",
            ],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            print("pdflatex:   FAILED")
            print(proc.stdout[-1500:])
            return
        pdf_dst = OUT_DIR / "tikz_emit.pdf"
        (tmp_path / "fig.pdf").replace(pdf_dst)
        print(f"pdf saved:  {pdf_dst}")


if __name__ == "__main__":
    run()
