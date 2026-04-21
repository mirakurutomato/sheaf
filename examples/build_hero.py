"""Render a handful of catalog surfaces at hero-grade mesh density.

The catalog in :mod:`gallery_catalog` is deliberately CI-budget — every item
meshes under 512 triangles so the smoke + LaTeX gate run fast.  README hero
images want denser meshes so the hatch pattern, boundary glow, and curvature
read at the displayed size.  This driver takes a 4-item subset, bumps each
item's ``base_n`` / ``max_depth``, compiles the PDF, and rasterises with
``pdftoppm`` at 300 dpi into ``examples/gallery/hero/<name>.png``.

Requires ``pdflatex`` and ``pdftoppm`` on ``PATH`` (both shipped with
TeX Live).  Run from the repo root::

    .venv/Scripts/python examples/build_hero.py
"""

from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "examples"))

from gallery_catalog import GalleryItem, gallery_items  # noqa: E402

from sheaf.numeric import adaptive_mesh, compiled  # noqa: E402
from sheaf.vector import emit_tikz, tikz_document  # noqa: E402

OUT_DIR = REPO_ROOT / "examples" / "gallery" / "hero"
DPI = 300


@dataclass(frozen=True, slots=True)
class HeroOverride:
    name: str
    base_n: int
    max_depth: int


HEROES: tuple[HeroOverride, ...] = (
    HeroOverride("monkey_saddle", base_n=9, max_depth=1),
    HeroOverride("torus", base_n=14, max_depth=0),
    HeroOverride("mobius_strip", base_n=12, max_depth=1),
    HeroOverride("helicoid", base_n=11, max_depth=1),
)


def _render_pdf(item: GalleryItem, override: HeroOverride, dst: Path) -> None:
    cs = compiled(item.surface)
    mesh = adaptive_mesh(cs, base_n=override.base_n, max_depth=override.max_depth)
    body = emit_tikz(mesh, item.camera, item.material)
    src = tikz_document(body)

    pdflatex = shutil.which("pdflatex")
    if pdflatex is None:
        raise RuntimeError("pdflatex is required for hero rendering")
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        (tmp_path / "fig.tex").write_text(src, encoding="utf-8")
        proc = subprocess.run(
            [pdflatex, "-interaction=nonstopmode", "-halt-on-error", "fig.tex"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            raise RuntimeError(
                f"pdflatex failed for {item.name}: {proc.stdout[-800:]}"
            )
        (tmp_path / "fig.pdf").replace(dst)
    print(
        f"  [pdf] {item.name} "
        f"({mesh.n_triangles} tris, base_n={override.base_n}, depth={override.max_depth})",
        flush=True,
    )


def _rasterise(pdf: Path, png: Path) -> None:
    pdftoppm = shutil.which("pdftoppm")
    if pdftoppm is None:
        raise RuntimeError("pdftoppm is required (ships with TeX Live)")
    stem = png.with_suffix("")
    proc = subprocess.run(
        [pdftoppm, "-png", "-r", str(DPI), "-singlefile", str(pdf), str(stem)],
        capture_output=True,
        text=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"pdftoppm failed on {pdf}: {proc.stderr[-400:]}")
    print(f"  [png] {png.name}", flush=True)


def run() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    by_name = {it.name: it for it in gallery_items()}

    for hero in HEROES:
        if hero.name not in by_name:
            raise KeyError(f"{hero.name!r} missing from catalog")
        item = by_name[hero.name]
        print(f"rendering {item.name} ({item.material.name})", flush=True)
        pdf_path = OUT_DIR / f"{hero.name}.pdf"
        png_path = OUT_DIR / f"{hero.name}.png"
        _render_pdf(item, hero, pdf_path)
        _rasterise(pdf_path, png_path)
        pdf_path.unlink()

    print(f"done: {OUT_DIR}")


if __name__ == "__main__":
    run()
