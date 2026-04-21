"""TikZ code generator — Month 2 W8.

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
"""

from __future__ import annotations

import numpy as np

from sheaf.materials import Material
from sheaf.numeric.mesh import AdaptiveMesh
from sheaf.vector.bsp import painter_sort
from sheaf.vector.camera import Camera

_DEFAULT_FILL = "#c8cdd4"

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
    fragments = painter_sort(mesh, np.asarray(camera.position, dtype=float))
    projected = [camera.project(f) for f in fragments]

    fill_hex = _hex6(
        material.params["surface_fill"] if material else _DEFAULT_FILL
    )
    edge_raw = material.params.get("wire_color") if material else None
    alpha = float(material.params.get("alpha", 1.0)) if material else 1.0
    wire_width_pt = (
        float(material.params.get("wire_width", 0.3)) if material else 0.3
    )
    shows_edges = edge_raw is not None

    lines: list[str] = [f"\\begin{{tikzpicture}}[scale={scale_cm:.5f}]"]
    lines.append(f"  \\definecolor{{sheaffill}}{{HTML}}{{{fill_hex}}}")
    if shows_edges:
        edge_hex = _hex6(edge_raw)
        lines.append(f"  \\definecolor{{sheafedge}}{{HTML}}{{{edge_hex}}}")

    fill_opts = ["fill=sheaffill"]
    if alpha < 1.0:
        fill_opts.append(f"fill opacity={alpha:.3f}")
    if shows_edges:
        fill_opts.append("draw=sheafedge")
        fill_opts.append(f"line width={wire_width_pt:.3f}pt")
    options = ", ".join(fill_opts)

    for tri2 in projected:
        path = " -- ".join(f"({p[0]:.5f},{p[1]:.5f})" for p in tri2)
        lines.append(f"  \\fill[{options}] {path} -- cycle;")

    lines.append("\\end{tikzpicture}")
    return "\n".join(lines) + "\n"


def tikz_document(body: str, *, border_pt: int = 2) -> str:
    """Wrap ``body`` in a minimal compilable ``standalone`` document."""
    return (
        f"\\documentclass[tikz,border={border_pt}pt]{{standalone}}\n"
        "\\usepackage{tikz}\n"
        "\\begin{document}\n"
        f"{body}"
        "\\end{document}\n"
    )


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


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
