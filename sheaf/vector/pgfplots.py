"""PGFPlots backend — Month 3 W9 + Month 3 W10.

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

W10 additions
-------------

* **Boundary glow** — when the material sets ``boundary_glow``, each
  open-boundary edge is emitted as its own ``\\addplot3`` line segment
  in an accent colour, after the patch.  Closed meshes emit nothing
  extra.
* **Hatch pattern** — not supported by PGFPlots' ``shader=flat`` patch
  directive.  When the material sets ``hatch_pattern``, the PGFPlots
  emitter silently degrades to the solid fill (the TikZ emitter handles
  the hatch).  Callers can detect the mismatch by comparing the emitted
  bodies.
"""

from __future__ import annotations

import math

from sheaf.materials import Material, VectorParams, resolve_vector_params
from sheaf.numeric.mesh import AdaptiveMesh
from sheaf.vector.camera import Camera
from sheaf.vector.tikz import _hex6


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
    params = resolve_vector_params(material)

    lines: list[str] = ["\\begin{tikzpicture}"]
    lines.append(f"  \\definecolor{{sheaffill}}{{HTML}}{{{_hex6(params.surface_fill)}}}")
    if params.shows_edges:
        lines.append(
            f"  \\definecolor{{sheafedge}}{{HTML}}{{{_hex6(params.wire_color)}}}"
        )
    if params.boundary_glow:
        lines.append(
            f"  \\definecolor{{sheafglow}}{{HTML}}{{{_hex6(params.boundary_glow_color)}}}"
        )
    lines.append(
        f"  \\begin{{axis}}[view={{{az:.3f}}}{{{el:.3f}}}, {axis_options}]"
    )
    lines.append(f"    \\addplot3[{_patch_options(params)}]")
    lines.append("      coordinates {")
    coords = mesh.points[mesh.triangles].reshape(-1, 3)
    for x, y, z in coords:
        lines.append(f"        ({x:.5f},{y:.5f},{z:.5f})")
    lines.append("      };")

    if params.boundary_glow:
        lines.extend(_boundary_glow_addplots(mesh, params))

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


# ---------------------------------------------------------------------------
# Internals
# ---------------------------------------------------------------------------


def _patch_options(params: VectorParams) -> str:
    opts = ["patch", "patch type=triangle", "shader=flat", "fill=sheaffill"]
    if params.shows_edges:
        opts.append("draw=sheafedge")
        opts.append(f"line width={params.wire_width_pt:.3f}pt")
    else:
        opts.append("draw=none")
    if params.is_translucent:
        opts.append(f"fill opacity={params.alpha:.3f}")
    return ", ".join(opts)


def _boundary_glow_addplots(mesh: AdaptiveMesh, params: VectorParams) -> list[str]:
    """Emit one ``\\addplot3`` per open-boundary edge, in accent colour.

    Each edge is a two-point line plot carrying ``forget plot`` so it
    never enters any legend.  Closed meshes pass through with no output.
    """
    from sheaf.numeric.topology import analyze

    topo = analyze(mesh)
    if len(topo.boundary_edges) == 0:
        return []
    glow_width = params.wire_width_pt * 2.0
    style = (
        f"draw=sheafglow, line width={glow_width:.3f}pt, "
        "no marks, forget plot"
    )
    out: list[str] = []
    for a, b in topo.boundary_edges:
        pa = mesh.points[int(a)]
        pb = mesh.points[int(b)]
        out.append(f"    \\addplot3[{style}]")
        out.append(
            f"      coordinates {{ ({pa[0]:.5f},{pa[1]:.5f},{pa[2]:.5f}) "
            f"({pb[0]:.5f},{pb[1]:.5f},{pb[2]:.5f}) }};"
        )
    return out
