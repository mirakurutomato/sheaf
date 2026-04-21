"""Shared pytest fixtures.

The LaTeX compilation harness is central to sheaf's validation strategy
(see CLAUDE.md): a test that merely runs Python code is not sufficient — the
emitted TikZ/PGFPlots must survive a real `pdflatex` / `lualatex` run with
correct bounding boxes. This conftest provides:

* `latex_engine` — parametrised fixture over available engines
* `compile_tex`  — callable: write a .tex string, compile, return artifacts
* `tikz_document` — wraps a TikZ body in a minimal standalone document
"""

from __future__ import annotations

import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path
from typing import Literal

import pytest

type Engine = Literal["pdflatex", "lualatex"]

_ENGINES: tuple[Engine, ...] = ("pdflatex", "lualatex")


def _engine_available(engine: Engine) -> bool:
    return shutil.which(engine) is not None


@pytest.fixture(params=_ENGINES, ids=list(_ENGINES))
def latex_engine(request: pytest.FixtureRequest) -> Engine:
    engine: Engine = request.param
    if not _engine_available(engine):
        pytest.skip(f"{engine} not available in PATH")
    return engine


@pytest.fixture
def compile_tex(
    tmp_path: Path, latex_engine: Engine
) -> Callable[[str], subprocess.CompletedProcess[str]]:
    """Write `src` to tmp_path/doc.tex and compile with the parametrised engine.

    Returns the CompletedProcess. On success, `tmp_path/doc.pdf` exists.
    """

    def _compile(src: str) -> subprocess.CompletedProcess[str]:
        tex = tmp_path / "doc.tex"
        tex.write_text(src, encoding="utf-8")
        proc = subprocess.run(
            [
                latex_engine,
                "-interaction=nonstopmode",
                "-halt-on-error",
                "doc.tex",
            ],
            cwd=tmp_path,
            capture_output=True,
            text=True,
            timeout=60,
        )
        return proc

    return _compile


@pytest.fixture
def tikz_document() -> Callable[[str], str]:
    """Wrap a TikZ body in a minimal standalone document for compilation tests."""

    def _wrap(body: str) -> str:
        return (
            "\\documentclass[tikz,border=2pt]{standalone}\n"
            "\\usepackage{tikz}\n"
            "\\begin{document}\n"
            f"{body}\n"
            "\\end{document}\n"
        )

    return _wrap
