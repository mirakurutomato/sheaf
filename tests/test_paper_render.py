"""End-to-end Paper.render dispatch — Month 3 W9.

Now that :meth:`sheaf.paper.Paper.render` actually drives the figure
pipeline, we exercise it for both backends and verify the
``PaperContext`` round-trips off a real ``main.tex`` file.

These tests do **not** require LaTeX — they only check the produced
:class:`PaperArtifact` payload.  The W8 / W9 LaTeX-gate suites already
guarantee the emitted strings compile.
"""

from __future__ import annotations

from sympy.abc import x, y

from sheaf import Chalkboard, Paper, PaperArtifact, Surface


def test_render_tikz_returns_artifact_with_tikz_body() -> None:
    art = Surface(z=x * y) @ Chalkboard >> Paper(label="fig:saddle")
    assert isinstance(art, PaperArtifact)
    assert art.engine == "tikz"
    assert art.label == "fig:saddle"
    assert art.body.startswith("\\begin{tikzpicture}")
    assert "\\definecolor{sheaffill}{HTML}{2b3a2e}" in art.body
    assert art.source.startswith("\\documentclass[tikz,border=2pt]{standalone}")
    assert "\\usepackage{tikz}" in art.source
    assert art.context is None  # no path → no parsing


def test_render_pgfplots_uses_pgfplots_document_wrapper() -> None:
    art = Surface(z=x**2 + y**2) @ Chalkboard >> Paper(engine="pgfplots")
    assert art.engine == "pgfplots"
    assert "\\begin{axis}" in art.body
    assert "patch type=triangle" in art.body
    assert "\\usepackage{pgfplots}" in art.source
    assert "\\pgfplotsset{compat=" in art.source


def test_render_inherits_existing_main_tex_context(tmp_path) -> None:  # type: ignore[no-untyped-def]
    main = tmp_path / "main.tex"
    main.write_text(
        "\\documentclass[11pt]{amsart}\n"
        "\\usepackage{fontspec}\n"
        "\\begin{document}\nhi\\end{document}\n",
        encoding="utf-8",
    )
    art = Surface(z=x * y) @ Chalkboard >> Paper(main)
    assert art.context is not None
    assert art.context.documentclass == "amsart"
    assert art.context.font_size_pt == 11
    assert art.context.has_fontspec is True
    assert art.context.recommended_engine == "lualatex"


def test_render_skips_context_for_nonexistent_path() -> None:
    """The legacy ``Paper("main.tex")`` test exercises this path."""
    art = Surface(z=x * y) @ Chalkboard >> Paper("definitely-not-a-file.tex")
    assert art.context is None


def test_render_without_material_uses_default_fill() -> None:
    art = Surface(z=x * y) >> Paper()
    assert art.body.count("\\fill") > 0
    # Default fill is the W8 `_DEFAULT_FILL` "#c8cdd4".
    assert "\\definecolor{sheaffill}{HTML}{c8cdd4}" in art.body


def test_render_picks_last_material_when_chained() -> None:
    from sheaf import Blueprint
    art = Surface(z=x * y) @ Chalkboard @ Blueprint >> Paper()
    # Blueprint fill is "#0b3d6b" — chained `@` flattens, last wins.
    assert "\\definecolor{sheaffill}{HTML}{0b3d6b}" in art.body
