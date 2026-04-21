"""Sanity check for the LaTeX compile fixture.

Runs a minimal TikZ document through each available engine to confirm the
harness wiring end-to-end. If no engine is in PATH the entire module is
skipped via fixture-level `pytest.skip`.
"""

from __future__ import annotations

import pytest


@pytest.mark.latex
def test_minimal_tikz_compiles(compile_tex, tikz_document) -> None:  # type: ignore[no-untyped-def]
    src = tikz_document(
        r"\begin{tikzpicture}\draw (0,0) -- (1,1);\end{tikzpicture}"
    )
    proc = compile_tex(src)
    assert proc.returncode == 0, (
        f"LaTeX compile failed:\nstdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    )
