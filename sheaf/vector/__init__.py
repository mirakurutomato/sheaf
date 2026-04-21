"""Vector-output pipeline (Month 2 W7 → Month 3 W9).

Raster preview already renders meshes in ``sheaf.preview``; this module is
the separate pipeline that produces **depth-correct vector output** for
TikZ / PGFPlots.  Unlike raster drawing there is no z-buffer — every
polygon must be emitted in painter's order, which requires a global
back-to-front sort that handles arbitrarily intersecting triangles.

W7 delivers the core sorter (BSP tree + painter's traversal); W8 wires it
into a TikZ emitter; W9 adds the PGFPlots backend and ``main.tex`` parser.
"""

from __future__ import annotations

from sheaf.vector.bsp import (
    BSPNode,
    Plane,
    build_bsp,
    paint,
    painter_sort,
)
from sheaf.vector.camera import Camera
from sheaf.vector.pgfplots import emit_pgfplots, pgfplots_document, view_from_camera
from sheaf.vector.tikz import emit_tikz, tikz_document

__all__ = [
    "BSPNode",
    "Camera",
    "Plane",
    "build_bsp",
    "emit_pgfplots",
    "emit_tikz",
    "paint",
    "painter_sort",
    "pgfplots_document",
    "tikz_document",
    "view_from_camera",
]
