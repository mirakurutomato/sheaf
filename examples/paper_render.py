"""End-to-end ``>> Paper`` example showing both backends + main.tex sync.

Run from the repo root::

    .venv/Scripts/python examples/paper_render.py

The script:

1. writes a tiny synthetic ``main.tex`` with ``amsart`` + ``geometry`` so
   the parser has something concrete to bite on,
2. renders ``z = x^2 + y^2 - x*y`` once via the W8 TikZ backend and once
   via the W9 PGFPlots backend, both pointing at the synthetic main.tex,
3. echoes the parsed :class:`PaperContext`, the chosen engine, and a
   peek at the emitted body for each backend,
4. drops the standalone source for both backends into
   ``examples/gallery/paper_<engine>.tex`` and, when ``pdflatex`` and
   ``lualatex`` are on PATH, the matching PDF.
"""

from __future__ import annotations

import shutil
import subprocess
import tempfile
from pathlib import Path

from sympy.abc import x, y

from sheaf import Chalkboard, Paper, Surface

OUT_DIR = Path(__file__).parent / "gallery"


def _write_synthetic_main_tex(path: Path) -> None:
    path.write_text(
        "\\documentclass[11pt]{amsart}\n"
        "\\usepackage[textwidth=5in]{geometry}\n"
        "\\usepackage{fontspec}  % triggers the lualatex hint\n"
        "\\begin{document}\n"
        "Hello, sheaf.\n"
        "\\end{document}\n",
        encoding="utf-8",
    )


def _compile(source: str, engine: str, dst_pdf: Path) -> bool:
    binary = shutil.which(engine)
    if binary is None:
        return False
    with tempfile.TemporaryDirectory() as tmp:
        tmp_path = Path(tmp)
        (tmp_path / "fig.tex").write_text(source, encoding="utf-8")
        proc = subprocess.run(
            [binary, "-interaction=nonstopmode", "-halt-on-error", "fig.tex"],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            check=False,
        )
        if proc.returncode != 0:
            print(f"  {engine}: compile FAILED")
            return False
        (tmp_path / "fig.pdf").replace(dst_pdf)
        return True


def run() -> None:
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    main = OUT_DIR / "paper_main.tex"
    _write_synthetic_main_tex(main)

    expr = x**2 + y**2 - x * y
    surface = Surface(z=expr, x=(-1, 1), y=(-1, 1))

    for engine in ("tikz", "pgfplots"):
        artifact = surface @ Chalkboard >> Paper(
            main, engine=engine, label=f"fig:{engine}"
        )
        ctx = artifact.context
        print("=" * 72)
        print(f"engine:        {engine}")
        if ctx is not None:
            print(f"documentclass: {ctx.documentclass} ({ctx.font_size_pt}pt)")
            print(f"textwidth:     {ctx.textwidth_pt:.1f} pt")
            print(f"engine hint:   {ctx.recommended_engine}")
        print(f"body length:   {len(artifact.body):,} chars")
        tex_dst = OUT_DIR / f"paper_{engine}.tex"
        tex_dst.write_text(artifact.source, encoding="utf-8")
        print(f"tex saved:     {tex_dst}")

        latex = "lualatex" if engine == "pgfplots" else "pdflatex"
        pdf_dst = OUT_DIR / f"paper_{engine}.pdf"
        if _compile(artifact.source, latex, pdf_dst):
            print(f"pdf saved:     {pdf_dst}")
        else:
            print(f"{latex}:      not on PATH - skipping compile step")


if __name__ == "__main__":
    run()
