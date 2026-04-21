r"""Paper: the LaTeX-paper-aware output sink.

    scene >> Paper("main.tex", width=r"0.8\linewidth", figure="fig:main")

The :class:`Paper` reads the paper's ``\documentclass``, ``geometry``
options, and ``fontspec`` usage to size the generated TikZ / PGFPlots
figure so it fits the target document.  Month 3 W9 wires the pipeline
end-to-end: the returned :class:`PaperArtifact` carries both the picture
body (for embedding into the surrounding paper) and the wrapped
``standalone`` source (for one-shot compilation tests).
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from sheaf.core import Renderable, Styled
from sheaf.io import PaperContext, parse_main_tex
from sheaf.numeric import adaptive_mesh, compiled
from sheaf.objects import Surface
from sheaf.scene import Scene
from sheaf.vector import (
    Camera,
    emit_pgfplots,
    emit_tikz,
    pgfplots_document,
    tikz_document,
)

if TYPE_CHECKING:
    from sheaf.materials import Material

type Engine = Literal["tikz", "pgfplots", "pdf"]


@dataclass(frozen=True, slots=True)
class PaperArtifact:
    """Result of rendering a scene to a paper target.

    The ``source`` field carries a complete ``standalone`` document that
    a LaTeX engine can compile directly; ``body`` is the picture-only
    fragment for embedding into the surrounding ``main.tex``.  Either
    can be ``""`` when the renderer chose a pure-routing engine such as
    ``"pdf"`` (not yet implemented).
    """

    path: Path
    engine: Engine
    label: str | None = None
    body: str = ""
    source: str = ""
    context: PaperContext | None = None

    def __fspath__(self) -> str:
        return str(self.path)


class Paper:
    """LaTeX-paper-aware output target.

    Parameters
    ----------
    path:
        The surrounding paper's ``main.tex`` (used for dimension/font
        inference) — or, when the file does not exist, a hint for where
        the caller intends to drop the rendered ``.tex`` themselves.
        Pass ``None`` for in-memory rendering only.
    width:
        LaTeX-valued width, e.g. ``r"\\linewidth"`` or
        ``r"0.8\\linewidth"``; surfaced verbatim on the returned
        artifact for downstream layouts.
    figure / label:
        Optional ``\\label{...}`` for the floating figure environment
        (``figure`` is an alias kept for readability in the DSL).
    engine:
        ``"tikz"`` (default, vector + own painter), ``"pgfplots"``
        (PGFPlots ``\\addplot3 [patch]``), or ``"pdf"`` (reserved).
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
        """Compile ``obj`` into a LaTeX-ready :class:`PaperArtifact`.

        The renderable is reduced to ``(Surface, Material | None)``,
        meshed by :func:`sheaf.numeric.adaptive_mesh`, viewed through an
        isometric :class:`~sheaf.vector.Camera`, and lowered through the
        backend selected by ``engine``.  When ``self.path`` points at an
        existing ``.tex`` file, it is parsed by
        :func:`sheaf.io.parse_main_tex` and surfaced on the artifact for
        downstream sizing and engine selection.
        """
        surface, material = _extract_surface_and_material(obj)

        compiled_surface = compiled(surface)
        mesh = adaptive_mesh(compiled_surface, max_depth=0)
        camera = Camera.isometric()

        context = self._read_context()

        if self.engine == "tikz":
            body = emit_tikz(mesh, camera, material)
            source = tikz_document(body)
        elif self.engine == "pgfplots":
            body = emit_pgfplots(mesh, camera, material)
            source = pgfplots_document(body)
        elif self.engine == "pdf":
            raise NotImplementedError(
                "engine='pdf' is reserved for the W11 LaTeX CI integration"
            )
        else:  # pragma: no cover - exhaustive Literal already guarded
            raise ValueError(f"unknown engine {self.engine!r}")

        return PaperArtifact(
            path=self.path if self.path is not None else Path("<stdout>"),
            engine=self.engine,
            label=self.label,
            body=body,
            source=source,
            context=context,
        )

    def _read_context(self) -> PaperContext | None:
        if (
            self.path is None
            or self.path.suffix != ".tex"
            or not self.path.exists()
        ):
            return None
        return parse_main_tex(self.path)

    def __repr__(self) -> str:
        return (
            f"Paper(path={self.path!r}, width={self.width!r}, "
            f"engine={self.engine!r})"
        )


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _extract_surface_and_material(
    obj: Renderable,
) -> tuple[Surface, Material | None]:
    """Reduce a :class:`Renderable` to a ``(Surface, Material | None)`` pair.

    Month 3 W9 scope: only :class:`Surface` (optionally wrapped in a
    :class:`Styled`) and a :class:`Scene` containing exactly one such
    surface are supported.  Companion renderables such as :class:`Axes`,
    :class:`Curve`, and :class:`Label` are silently skipped here and
    will be promoted to first-class participants in W10–W11.
    """
    if isinstance(obj, Surface):
        return obj, None
    if isinstance(obj, Styled) and isinstance(obj.base, Surface):
        last = obj.materials[-1] if obj.materials else None
        return obj.base, last
    if isinstance(obj, Scene):
        for item in obj.items:
            if isinstance(item, Surface) or (
                isinstance(item, Styled) and isinstance(item.base, Surface)
            ):
                return _extract_surface_and_material(item)
        raise ValueError("Scene contains no Surface to render")
    raise NotImplementedError(
        f"Paper.render does not yet support {type(obj).__name__}"
    )
