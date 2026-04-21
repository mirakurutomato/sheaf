"""PGFPlots backend — Month 3 W9.

Where the W8 :func:`sheaf.vector.tikz.emit_tikz` lays down per-triangle
``\\fill`` paths under our own BSP painter, this backend lowers an
:class:`~sheaf.numeric.mesh.AdaptiveMesh` into a single PGFPlots
``\\addplot3 [patch, patch type=triangle]`` directive.  PGFPlots then
runs its own painter under the supplied ``view={azimuth}{elevation}``,
which we derive from the W8 :class:`~sheaf.vector.camera.Camera` so the
two backends remain visually consistent.

Each consecutive triple of coordinates inside the ``coordinates {...}``
block defines one triangle; for ``M`` triangles we emit ``3·M`` points.
Material parameters surface as the fill colour, optional edge colour,
line width, and ``fill opacity``.
"""

from __future__ import annotations

import math

from sheaf.materials import Material
from sheaf.numeric.mesh import AdaptiveMesh
from sheaf.vector.camera import Camera
from sheaf.vector.tikz import _DEFAULT_FILL, _hex6


def view_from_camera(camera: Camera) -> tuple[float, float]:
    """Return PGFPlots ``(azimuth, elevation)`` in degrees.

    Convention: ``azimuth`` rotates about ``+z`` from the ``+x`` axis;
    ``elevation`` is the angle the view direction makes with the
    ``xy``-plane.  Both are derived from the unit vector pointing from
    the camera target to its position (``Camera.forward``).
    """
    d = camera.forward()
    azimuth = math.degrees(math.atan2(float(d[1]), float(d[0])))
    elevation = math.degrees(math.asin(max(-1.0, min(1.0, float(d[2])))))
    return azimuth, elevation


def emit_pgfplots(
    mesh: AdaptiveMesh,
    camera: Camera | None = None,
    material: Material | None = None,
    *,
    axis_options: str = "axis equal image, hide axis",
) -> str:
    """Return a ``tikzpicture``+``axis`` body rendering ``mesh`` as a
    PGFPlots triangle-patch plot.

    ``camera`` defaults to :meth:`Camera.isometric`.  ``axis_options``
    is appended verbatim to the ``\\begin{axis}[...]`` option list.
    """
    cam = camera if camera is not None else Camera.isometric()
    az, el = view_from_camera(cam)

    fill_hex = _hex6(
        material.params["surface_fill"] if material else _DEFAULT_FILL
    )
    edge_raw = material.params.get("wire_color") if material else None
    alpha = float(material.params.get("alpha", 1.0)) if material else 1.0
    wire_width_pt = (
        float(material.params.get("wire_width", 0.3)) if material else 0.3
    )
    shows_edges = edge_raw is not None

    plot_opts: list[str] = [
        "patch",
        "patch type=triangle",
        "shader=flat",
        "fill=sheaffill",
    ]
    if shows_edges:
        plot_opts.append("draw=sheafedge")
        plot_opts.append(f"line width={wire_width_pt:.3f}pt")
    else:
        plot_opts.append("draw=none")
    if alpha < 1.0:
        plot_opts.append(f"fill opacity={alpha:.3f}")

    lines: list[str] = ["\\begin{tikzpicture}"]
    lines.append(f"  \\definecolor{{sheaffill}}{{HTML}}{{{fill_hex}}}")
    if shows_edges:
        edge_hex = _hex6(edge_raw)
        lines.append(f"  \\definecolor{{sheafedge}}{{HTML}}{{{edge_hex}}}")
    lines.append(
        f"  \\begin{{axis}}[view={{{az:.3f}}}{{{el:.3f}}}, {axis_options}]"
    )
    lines.append(f"    \\addplot3[{', '.join(plot_opts)}]")
    lines.append("      coordinates {")
    coords = mesh.points[mesh.triangles].reshape(-1, 3)
    for x, y, z in coords:
        lines.append(f"        ({x:.5f},{y:.5f},{z:.5f})")
    lines.append("      };")
    lines.append("  \\end{axis}")
    lines.append("\\end{tikzpicture}")
    return "\n".join(lines) + "\n"


def pgfplots_document(
    body: str, *, border_pt: int = 2, compat: str = "1.18"
) -> str:
    """Wrap ``body`` in a minimal compilable ``standalone`` document.

    ``compat`` selects the ``\\pgfplotsset{compat=...}`` level; ``1.18``
    is the latest stable as of TeX Live 2025 and is silently downgraded
    by older PGFPlots installs.
    """
    return (
        f"\\documentclass[tikz,border={border_pt}pt]{{standalone}}\n"
        "\\usepackage{pgfplots}\n"
        f"\\pgfplotsset{{compat={compat}}}\n"
        "\\begin{document}\n"
        f"{body}"
        "\\end{document}\n"
    )
