"""Minimal LaTeX preamble parser — Month 3 W9.

Reads ``\\documentclass``, ``\\usepackage{geometry}`` options, and
engine-relevant package hints (``fontspec``, ``unicode-math``) out of a
``main.tex`` file.  This is **not** a full TeX parser: it strips comments
with a regex and walks usepackage declarations, ignoring conditionals,
``\\input``, and run-time dimension expressions.  The job is just to
return enough metadata that the figure pipeline can size the output and
pick a compiler that matches the surrounding paper.

The :class:`PaperContext` it returns is a frozen, hashable record so it
can flow downstream into rendering pipelines without further parsing.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

# Default ``\textwidth`` in printer's points for the standard LaTeX
# classes at 10/11/12pt.  These match the values baked into the standard
# class files (``article.cls`` etc.) for the default ``letterpaper``
# size and are rounded to the nearest pt.  ``geometry`` package overrides
# always win when present.
_TEXTWIDTH_DEFAULTS: dict[tuple[str, int], float] = {
    ("article", 10): 345.0,
    ("article", 11): 360.0,
    ("article", 12): 390.0,
    ("report", 10): 345.0,
    ("report", 11): 360.0,
    ("report", 12): 390.0,
    ("book", 10): 345.0,
    ("book", 11): 360.0,
    ("book", 12): 390.0,
    ("amsart", 10): 360.0,
    ("amsart", 11): 380.0,
    ("amsart", 12): 410.0,
}

# 1in = 72.27pt (TeX point), 1bp = 1/72in (PostScript point).
_UNIT_TO_PT: dict[str, float] = {
    "pt": 1.0,
    "bp": 72.27 / 72.0,
    "in": 72.27,
    "cm": 72.27 / 2.54,
    "mm": 72.27 / 25.4,
    "pc": 12.0,
}

_FONTSPEC_PACKAGES: frozenset[str] = frozenset({"fontspec", "unicode-math"})

_COMMENT_RE = re.compile(r"(?<!\\)%.*$", re.MULTILINE)
_DOCUMENTCLASS_RE = re.compile(
    r"\\documentclass\s*(?:\[([^\]]*)\])?\s*\{([^}]+)\}"
)
_USEPACKAGE_RE = re.compile(
    r"\\usepackage\s*(?:\[([^\]]*)\])?\s*\{([^}]+)\}"
)
_DIM_RE = re.compile(r"\s*(-?\d+(?:\.\d+)?)\s*([a-zA-Z]+)\s*")


@dataclass(frozen=True, slots=True)
class PaperContext:
    """Decoded ``main.tex`` preamble metadata.

    Attributes
    ----------
    documentclass:
        The class name (``"article"``, ``"amsart"``, ...).
    class_options:
        Original ``\\documentclass`` options, in source order.
    font_size_pt:
        ``10``, ``11``, or ``12`` — the base font size (LaTeX default 10).
    geometry_options:
        Key/value mapping from ``\\usepackage[...]{geometry}``; flag-only
        options map to an empty string.
    packages:
        Every package loaded via ``\\usepackage``, in source order.
    has_fontspec:
        True iff ``fontspec`` (or ``unicode-math``) is requested, in
        which case only ``lualatex`` / ``xelatex`` will compile the doc.
    textwidth_pt:
        Best-effort estimate of ``\\textwidth`` in printer's points, used
        as a sizing hint by the figure backends.  ``geometry`` overrides
        the class default when both are present.
    """

    documentclass: str
    class_options: tuple[str, ...]
    font_size_pt: int
    geometry_options: dict[str, str]
    packages: tuple[str, ...]
    has_fontspec: bool
    textwidth_pt: float

    @property
    def recommended_engine(self) -> str:
        """``"lualatex"`` when fontspec is loaded, else ``"pdflatex"``."""
        return "lualatex" if self.has_fontspec else "pdflatex"


def parse_main_tex(path: str | Path) -> PaperContext:
    """Read ``path`` and return a :class:`PaperContext`.

    Raises ``FileNotFoundError`` if ``path`` does not exist, and
    ``ValueError`` if no ``\\documentclass`` declaration is present.
    """
    text = Path(path).read_text(encoding="utf-8", errors="replace")
    return parse_main_tex_source(text)


def parse_main_tex_source(text: str) -> PaperContext:
    """Same as :func:`parse_main_tex` but takes the source string directly.

    Useful for tests and for callers that already hold the document in
    memory.
    """
    src = _strip_comments(text)

    cls_match = _DOCUMENTCLASS_RE.search(src)
    if cls_match is None:
        raise ValueError("no \\documentclass declaration found")
    options = _split_options(cls_match.group(1))
    documentclass = cls_match.group(2).strip()
    font_size = _font_size_from_options(options)

    packages: list[str] = []
    geometry_options: dict[str, str] = {}
    has_fontspec = False
    for pkg_match in _USEPACKAGE_RE.finditer(src):
        opts = _split_options(pkg_match.group(1))
        for raw in pkg_match.group(2).split(","):
            pkg = raw.strip()
            if not pkg:
                continue
            packages.append(pkg)
            if pkg in _FONTSPEC_PACKAGES:
                has_fontspec = True
            if pkg == "geometry":
                geometry_options.update(_options_to_map(opts))

    textwidth_pt = _resolve_textwidth_pt(documentclass, font_size, geometry_options)

    return PaperContext(
        documentclass=documentclass,
        class_options=tuple(options),
        font_size_pt=font_size,
        geometry_options=dict(geometry_options),
        packages=tuple(packages),
        has_fontspec=has_fontspec,
        textwidth_pt=textwidth_pt,
    )


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _strip_comments(text: str) -> str:
    return _COMMENT_RE.sub("", text)


def _split_options(opts: str | None) -> list[str]:
    if not opts:
        return []
    return [o.strip() for o in opts.split(",") if o.strip()]


def _options_to_map(opts: list[str]) -> dict[str, str]:
    out: dict[str, str] = {}
    for opt in opts:
        if "=" in opt:
            key, val = opt.split("=", 1)
            out[key.strip()] = val.strip()
        else:
            out[opt] = ""
    return out


def _font_size_from_options(options: list[str]) -> int:
    for opt in options:
        if opt.endswith("pt") and opt[:-2].isdigit():
            return int(opt[:-2])
    return 10


def _parse_dimension_pt(text: str) -> float | None:
    m = _DIM_RE.fullmatch(text)
    if m is None:
        return None
    val = float(m.group(1))
    unit = m.group(2).lower()
    if unit not in _UNIT_TO_PT:
        return None
    return val * _UNIT_TO_PT[unit]


def _resolve_textwidth_pt(
    documentclass: str, font_size_pt: int, geom: dict[str, str]
) -> float:
    for key in ("textwidth", "width", "totalwidth"):
        if key in geom:
            pt = _parse_dimension_pt(geom[key])
            if pt is not None:
                return pt
    return _TEXTWIDTH_DEFAULTS.get(
        (documentclass, font_size_pt),
        _TEXTWIDTH_DEFAULTS[("article", 10)],
    )
