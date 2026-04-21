r"""Paper: the LaTeX-paper-aware output sink.

    scene >> Paper("main.tex", width=r"0.8\linewidth", figure="fig:main")

The `Paper` reads (in Month 3) the paper's documentclass, geometry, column
width, and fontspec to size the generated TikZ / PGFPlots figure so it fits
the target paper without visual drift.  For Month 1 W1 this is a skeleton:
rendering returns a sentinel artifact.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from sheaf.core import Renderable

type Engine = Literal["tikz", "pgfplots", "pdf"]


@dataclass(frozen=True, slots=True)
class PaperArtifact:
    """Result of rendering a scene to a paper target."""

    path: Path
    engine: Engine
    label: str | None = None

    def __fspath__(self) -> str:
        return str(self.path)


class Paper:
    """LaTeX-paper-aware output target.

    Parameters
    ----------
    path:
        Either the target .tex of the surrounding paper (`main.tex`) used for
        dimension/font inference, or a writable output path ending in
        `.tex` / `.pdf`.  If omitted, the paper context is ignored and output
        goes to stdout (useful for quick inspection).
    width:
        LaTeX-valued width, e.g. `r"\\linewidth"` or `r"0.8\\linewidth"`.
    figure:
        Optional `\\label{...}` value written inside a floating figure env.
    label:
        Alias for `figure=` (kept for readability in the DSL).
    engine:
        `"tikz"` (default, vector), `"pgfplots"`, or `"pdf"` (standalone).
    """

    __slots__ = ("path", "width", "label", "engine")

    def __init__(
        self,
        path: str | Path | None = None,
        *,
        width: str | None = None,
        figure: str | None = None,
        label: str | None = None,
        engine: Engine = "tikz",
    ) -> None:
        self.path: Path | None = Path(path) if path is not None else None
        self.width: str | None = width
        self.label: str | None = figure or label
        self.engine: Engine = engine

    def render(self, obj: Renderable) -> PaperArtifact:
        """Compile `obj` into a LaTeX-ready artifact.

        Month 1 W1 scaffold: the mesh → vector → codegen pipeline is not yet
        wired up. This stub returns a sentinel `PaperArtifact` so the
        `>> Paper(...)` syntax type-checks end-to-end.  The real body lands
        in Month 2 W8 (TikZ codegen) and Month 3 W9 (PGFPlots + main.tex sync).
        """
        _ = obj  # keep reference until pipeline is wired up
        return PaperArtifact(
            path=self.path if self.path is not None else Path("stdout"),
            engine=self.engine,
            label=self.label,
        )

    def __repr__(self) -> str:
        return f"Paper(path={self.path!r}, width={self.width!r}, engine={self.engine!r})"
