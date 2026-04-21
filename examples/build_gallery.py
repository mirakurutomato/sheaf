"""Emit every catalog entry as a standalone .tex (and .pdf when pdflatex is on PATH).

Run from the repo root::

    .venv/Scripts/python examples/build_gallery.py

For each :class:`~gallery_catalog.GalleryItem` the script

1. lowers the declarative :class:`~sheaf.Surface` into an adaptive mesh
   through the Months 1 + 2 pipeline,
2. projects through the item's :class:`~sheaf.vector.Camera` and emits a
   W8 TikZ body with the declared :class:`~sheaf.materials.Material`,
3. writes ``examples/gallery/tex/<name>.tex`` (a compilable ``standalone``
   document),
4. if ``pdflatex`` is on ``PATH``, compiles to
   ``examples/gallery/tex/<name>.pdf``.

The output directory is deliberately nested (``tex/`` under ``gallery/``) so
the W12 raster previews from ``examples/gallery.py`` are not overwritten.
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "examples"))

from gallery_catalog import GalleryItem, gallery_items  # noqa: E402

from sheaf.numeric import adaptive_mesh, compiled  # noqa: E402
from sheaf.vector import emit_tikz, tikz_document  # noqa: E402

OUT_DIR = REPO_ROOT / "examples" / "gallery" / "tex"


def render_item(item: GalleryItem) -> tuple[str, int, int]:
    """Run the full DSL → TikZ pipeline for one item.

    Returns ``(standalone_source, n_points, n_triangles)``.
    """
    cs = compiled(item.surface)
    mesh = adaptive_mesh(cs, base_n=item.base_n, max_depth=item.max_depth)
    body = emit_tikz(mesh, item.camera, item.material)
    return tikz_document(body), mesh.n_vertices, mesh.n_triangles


def _compile(source: str, dst_pdf: Path) -> bool:
    pdflatex = shutil.which("pdflatex")
    if pdflatex is None:
        return False
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        (tmp_path / "fig.tex").write_text(source, encoding="utf-8")
        proc = subprocess.run(
            [pdflatex, "-interaction=nonstopmode", "-halt-on-error", "fig.tex"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            return False
        (tmp_path / "fig.pdf").replace(dst_pdf)
        return True


def run() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    items = gallery_items()
    have_pdflatex = shutil.which("pdflatex") is not None

    print(f"Rendering {len(items)} items to {OUT_DIR}")
    print(f"pdflatex: {'on PATH' if have_pdflatex else 'not found; .tex only'}")
    print("=" * 72)
    header = f"{'name':<20} {'pts':>6} {'tris':>6} {'chars':>8} {'time':>7}"
    print(header)
    print("-" * len(header))

    for item in items:
        t0 = time.perf_counter()
        source, n_pts, n_tris = render_item(item)
        elapsed = time.perf_counter() - t0

        tex_path = OUT_DIR / f"{item.name}.tex"
        tex_path.write_text(source, encoding="utf-8")

        pdf_mark = ""
        if have_pdflatex:
            pdf_path = OUT_DIR / f"{item.name}.pdf"
            pdf_mark = " [pdf]" if _compile(source, pdf_path) else " [FAIL]"

        print(
            f"{item.name:<20} {n_pts:>6} {n_tris:>6} "
            f"{len(source):>8} {elapsed:>6.2f}s{pdf_mark}"
        )

    print("=" * 72)
    print(f"tex files: {OUT_DIR}/*.tex")
    if have_pdflatex:
        print(f"pdfs:      {OUT_DIR}/*.pdf")


if __name__ == "__main__":
    run()
