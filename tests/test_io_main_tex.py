"""``main.tex`` preamble parser — Month 3 W9.

These tests pin down the regex behaviour of
:func:`sheaf.io.parse_main_tex` so that downstream figure code can rely
on the returned :class:`PaperContext` for sizing and engine selection.
We feed source strings rather than real files where possible to keep
the tests hermetic; one round-trip test exercises file I/O via
``tmp_path``.
"""

from __future__ import annotations

import pytest

from sheaf.io import PaperContext, parse_main_tex
from sheaf.io.main_tex import parse_main_tex_source


def _doc(preamble: str) -> str:
    return preamble + "\n\\begin{document}\nhi\n\\end{document}\n"


# ---------------------------------------------------------------------------
# documentclass + class options
# ---------------------------------------------------------------------------


def test_documentclass_only_uses_article_defaults() -> None:
    ctx = parse_main_tex_source(_doc("\\documentclass{article}"))
    assert ctx.documentclass == "article"
    assert ctx.class_options == ()
    assert ctx.font_size_pt == 10
    assert ctx.textwidth_pt == pytest.approx(345.0)


def test_eleven_point_article_textwidth() -> None:
    ctx = parse_main_tex_source(_doc("\\documentclass[11pt,a4paper]{article}"))
    assert ctx.font_size_pt == 11
    assert ctx.textwidth_pt == pytest.approx(360.0)
    assert "a4paper" in ctx.class_options


def test_amsart_twelve_point_uses_amsart_table() -> None:
    ctx = parse_main_tex_source(_doc("\\documentclass[12pt]{amsart}"))
    assert ctx.documentclass == "amsart"
    assert ctx.font_size_pt == 12
    assert ctx.textwidth_pt == pytest.approx(410.0)


def test_unknown_class_falls_back_to_article10() -> None:
    ctx = parse_main_tex_source(_doc("\\documentclass{tufte-handout}"))
    assert ctx.textwidth_pt == pytest.approx(345.0)


def test_missing_documentclass_raises() -> None:
    with pytest.raises(ValueError, match="documentclass"):
        parse_main_tex_source("\\begin{document}\\end{document}\n")


# ---------------------------------------------------------------------------
# geometry overrides
# ---------------------------------------------------------------------------


def test_geometry_textwidth_in_inches_overrides_class_default() -> None:
    src = _doc(
        "\\documentclass{article}\n"
        "\\usepackage[textwidth=5in,top=1in]{geometry}"
    )
    ctx = parse_main_tex_source(src)
    # 5 in = 5 * 72.27 pt = 361.35 pt
    assert ctx.textwidth_pt == pytest.approx(5 * 72.27, abs=1e-6)
    assert ctx.geometry_options["textwidth"] == "5in"
    assert ctx.geometry_options["top"] == "1in"


def test_geometry_textwidth_in_centimetres() -> None:
    src = _doc(
        "\\documentclass{article}\n"
        "\\usepackage[textwidth=12.7cm]{geometry}"
    )
    ctx = parse_main_tex_source(src)
    # 12.7 cm = 12.7 * 72.27 / 2.54 pt = 361.35 pt
    assert ctx.textwidth_pt == pytest.approx(12.7 * 72.27 / 2.54, abs=1e-6)


def test_geometry_alias_width_is_recognised() -> None:
    src = _doc(
        "\\documentclass{article}\n"
        "\\usepackage[width=400pt]{geometry}"
    )
    ctx = parse_main_tex_source(src)
    assert ctx.textwidth_pt == pytest.approx(400.0)


# ---------------------------------------------------------------------------
# fontspec / engine recommendation
# ---------------------------------------------------------------------------


def test_no_fontspec_recommends_pdflatex() -> None:
    ctx = parse_main_tex_source(_doc("\\documentclass{article}"))
    assert ctx.has_fontspec is False
    assert ctx.recommended_engine == "pdflatex"


def test_fontspec_present_recommends_lualatex() -> None:
    src = _doc(
        "\\documentclass{article}\n"
        "\\usepackage{fontspec}"
    )
    ctx = parse_main_tex_source(src)
    assert ctx.has_fontspec is True
    assert ctx.recommended_engine == "lualatex"


def test_unicode_math_also_triggers_engine_switch() -> None:
    src = _doc(
        "\\documentclass{article}\n"
        "\\usepackage{unicode-math}"
    )
    ctx = parse_main_tex_source(src)
    assert ctx.has_fontspec is True
    assert ctx.recommended_engine == "lualatex"


# ---------------------------------------------------------------------------
# Comment + multi-package handling
# ---------------------------------------------------------------------------


def test_comments_are_stripped_so_commented_packages_are_ignored() -> None:
    src = _doc(
        "\\documentclass{article}\n"
        "% \\usepackage{fontspec}  this is a comment, not a package\n"
        "\\usepackage{amsmath}"
    )
    ctx = parse_main_tex_source(src)
    assert "fontspec" not in ctx.packages
    assert "amsmath" in ctx.packages
    assert ctx.has_fontspec is False


def test_multi_package_in_one_usepackage_is_split() -> None:
    src = _doc(
        "\\documentclass{article}\n"
        "\\usepackage{amsmath, amssymb, amsthm}"
    )
    ctx = parse_main_tex_source(src)
    assert ctx.packages == ("amsmath", "amssymb", "amsthm")


def test_escaped_percent_is_not_treated_as_comment() -> None:
    # The "\%" should survive comment stripping; we test that the
    # documentclass after it still parses correctly.
    src = _doc(
        "\\title{50\\% off}\n"
        "\\documentclass{article}\n"
    )
    ctx = parse_main_tex_source(src)
    assert ctx.documentclass == "article"


# ---------------------------------------------------------------------------
# File round-trip
# ---------------------------------------------------------------------------


def test_parse_main_tex_reads_file_from_disk(tmp_path) -> None:  # type: ignore[no-untyped-def]
    path = tmp_path / "main.tex"
    path.write_text(
        _doc("\\documentclass[11pt]{amsart}\n\\usepackage{fontspec}"),
        encoding="utf-8",
    )
    ctx = parse_main_tex(path)
    assert isinstance(ctx, PaperContext)
    assert ctx.documentclass == "amsart"
    assert ctx.font_size_pt == 11
    assert ctx.has_fontspec is True
