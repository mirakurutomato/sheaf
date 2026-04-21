"""TikZ code generator — Month 2 W8 + Month 3 W10.

Takes an :class:`~sheaf.numeric.mesh.AdaptiveMesh`, a
:class:`~sheaf.vector.camera.Camera`, and an optional
:class:`~sheaf.materials.Material`, and emits a ``\\begin{tikzpicture}``
body whose ``\\fill`` / ``\\draw`` commands are ordered back-to-front by
the W7 BSP painter.

The output is a fragment: callers who want a compilable artefact pass the
body through :func:`tikz_document` (or plug into their own
``main.tex``).  Colours are defined per-figure with ``\\definecolor`` so
callers never have to touch the preamble.

Design choices
--------------

* **Orthographic projection** — axonometric parallel rays, the natural
  choice for publication figures; no perspective foreshortening.
* **World cm = TikZ cm** — the picture is scaled by ``scale_cm``; the
  default ``2.0`` keeps typical unit-cube figures around 4 cm wide.
* **Edges** — drawn only for materials that define a ``wire_color`` (the
  semantic cue of Chalkboard and Blueprint); transparent / glass-type
  materials emit fills alone.
* **Hatch overlay** (W10) — when the material sets ``hatch_pattern``,
  a second ``\\fill`` pass stamps that TikZ pattern on top of the solid
  fill, giving Chalkboard its chalk-dust texture.
* **Boundary glow** (W10) — when the material sets ``boundary_glow``,
  the open-boundary edges of the mesh are drawn on top in an accent
  colour, ``≈2×`` wire width.  Closed meshes (sphere / torus) emit no
  extra strokes because their topology has no boundary.
"""

from __future__ import annotations

import numpy as np

from sheaf.materials import (
    DEFAULT_SURFACE_FILL,
    Material,
    VectorParams,
    resolve_vector_params,
)
from sheaf.numeric.mesh import AdaptiveMesh
from sheaf.vector.bsp import painter_sort
from sheaf.vector.camera import Camera

# Kept for backwards-compat with ``sheaf.vector.pgfplots`` imports.
_DEFAULT_FILL = DEFAULT_SURFACE_FILL

_NAMED_COLORS = {
    "white": "ffffff",
    "black": "000000",
    "red": "ff0000",
    "green": "00ff00",
    "blue": "0000ff",
}


def emit_tikz(
    mesh: AdaptiveMesh,
    camera: Camera,
    material: Material | None = None,
    *,
    scale_cm: float = 2.0,
) -> str:
    """Return a TikZ picture body rendering ``mesh`` under painter's order.

    The body is ``\\begin{tikzpicture}...\\end{tikzpicture}`` — wrap with
    :func:`tikz_document` for a standalone compilable file.
    """
    params = resolve_vector_params(material)

    fragments = painter_sort(mesh, np.asarray(camera.position, dtype=float))
    projected = [camera.project(f) for f in fragments]

    lines: list[str] = [f"\\begin{{tikzpicture}}[scale={scale_cm:.5f}]"]
    lines.extend(_color_definitions(params))

    fill_options = _fill_options(params)
    hatch_options = _hatch_options(params) if params.has_hatch else None

    for tri2 in projected:
        path = " -- ".join(f"({p[0]:.5f},{p[1]:.5f})" for p in tri2)
        lines.append(f"  \\fill[{fill_options}] {path} -- cycle;")
        if hatch_options is not None:
            lines.append(f"  \\fill[{hatch_options}] {path} -- cycle;")

    if params.boundary_glow:
        lines.extend(_boundary_glow_strokes(mesh, camera, params))

    lines.append("\\end{tikzpicture}")
    return "\n".join(lines) + "\n"


def tikz_document(body: str, *, border_pt: int = 2) -> str:
    """Wrap ``body`` in a minimal compilable ``standalone`` document.

    The ``patterns`` TikZ library is always loaded so hatch-bearing
    materials (W10 Chalkboard) compile without a preamble tweak.
    """
    return (
        f"\\documentclass[tikz,border={border_pt}pt]{{standalone}}\n"
        "\\usepackage{tikz}\n"
        "\\usetikzlibrary{patterns}\n"
        "\\begin{document}\n"
        f"{body}"
        "\\end{document}\n"
    )


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _color_definitions(params: VectorParams) -> list[str]:
    defs = [f"  \\definecolor{{sheaffill}}{{HTML}}{{{_hex6(params.surface_fill)}}}"]
    if params.shows_edges:
        defs.append(f"  \\definecolor{{sheafedge}}{{HTML}}{{{_hex6(params.wire_color)}}}")
    if params.has_hatch:
        defs.append(f"  \\definecolor{{sheafhatch}}{{HTML}}{{{_hex6(params.hatch_color)}}}")
    if params.boundary_glow:
        defs.append(
            f"  \\definecolor{{sheafglow}}{{HTML}}{{{_hex6(params.boundary_glow_color)}}}"
        )
    return defs


def _fill_options(params: VectorParams) -> str:
    opts = ["fill=sheaffill"]
    if params.is_translucent:
        opts.append(f"fill opacity={params.alpha:.3f}")
    if params.shows_edges:
        opts.append("draw=sheafedge")
        opts.append(f"line width={params.wire_width_pt:.3f}pt")
    return ", ".join(opts)


def _hatch_options(params: VectorParams) -> str:
    opts = [f"pattern={params.hatch_pattern}", "pattern color=sheafhatch"]
    if params.is_translucent:
        opts.append(f"fill opacity={params.alpha:.3f}")
    return ", ".join(opts)


def _boundary_glow_strokes(
    mesh: AdaptiveMesh, camera: Camera, params: VectorParams
) -> list[str]:
    from sheaf.numeric.topology import analyze

    topo = analyze(mesh)
    if len(topo.boundary_edges) == 0:
        return []
    glow_width = params.wire_width_pt * 2.0
    pts2 = camera.project(mesh.points)
    out: list[str] = []
    for a, b in topo.boundary_edges:
        ax, ay = pts2[int(a)]
        bx, by = pts2[int(b)]
        out.append(
            f"  \\draw[draw=sheafglow, line width={glow_width:.3f}pt] "
            f"({ax:.5f},{ay:.5f}) -- ({bx:.5f},{by:.5f});"
        )
    return out


def _hex6(color: str) -> str:
    """Normalise a ``"#RRGGBB"`` or named colour to a 6-hex-digit string."""
    if color.startswith("#"):
        h = color[1:]
        if len(h) == 3:
            h = "".join(ch * 2 for ch in h)
        if len(h) != 6:
            raise ValueError(f"unsupported hex colour {color!r}")
        return h.lower()
    lower = color.lower()
    if lower in _NAMED_COLORS:
        return _NAMED_COLORS[lower]
    raise ValueError(
        f"material colour {color!r} is not a hex literal nor a known name"
    )
