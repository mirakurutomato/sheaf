"""PyVista (VTK) preview driver — default interactive backend.

Translates DSL objects (Surface, Curve, Styled, Scene) into PyVista meshes
with material-aware styling (Chalkboard / Blueprint / Glass).  Used for
interactive inspection during development; the publication-grade vector
pipeline lands in Month 2 W7–W8.

Rendering defaults prioritise academic clarity: white background, SSAA,
smooth shading, and a single warm key light plus cool fill for depth cues.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

import pyvista as pv

from sheaf.materials import Material
from sheaf.preview.driver import PreviewDriver

if TYPE_CHECKING:
    from sheaf.core import Renderable


class PyVistaDriver(PreviewDriver):
    name = "pyvista"

    def show(
        self,
        obj: Renderable,
        *,
        size: tuple[int, int] = (1024, 768),
        title: str = "sheaf preview",
    ) -> None:
        """Open an interactive window rendering `obj`."""
        plotter = self._build(obj, size=size, title=title, off_screen=False)
        plotter.show()

    def screenshot(
        self,
        obj: Renderable,
        path: str,
        *,
        size: tuple[int, int] = (1600, 1200),
    ) -> str:
        """Render `obj` headlessly and save a high-DPI PNG to `path`."""
        plotter = self._build(obj, size=size, title="", off_screen=True)
        plotter.screenshot(path, return_img=False, transparent_background=False)
        plotter.close()
        return path

    # ------------------------------------------------------------------
    # Scene assembly
    # ------------------------------------------------------------------

    def _build(
        self,
        obj: Renderable,
        *,
        size: tuple[int, int],
        title: str,
        off_screen: bool,
    ) -> pv.Plotter:
        plotter = pv.Plotter(off_screen=off_screen, window_size=list(size), title=title)
        plotter.set_background("white")
        plotter.enable_anti_aliasing("ssaa")
        self._add(plotter, obj, material=None)
        self._light_scene(plotter)
        plotter.camera_position = "iso"
        plotter.reset_camera(bounds=plotter.bounds)
        plotter.camera.zoom(1.25)
        return plotter

    def _add(
        self,
        plotter: pv.Plotter,
        obj: Renderable,
        *,
        material: Material | None,
    ) -> None:
        from sheaf.core import Styled
        from sheaf.objects import Curve, Surface
        from sheaf.scene import Scene

        if isinstance(obj, Scene):
            for item in obj.items:
                self._add(plotter, item, material=material)
            return
        if isinstance(obj, Styled):
            self._add(plotter, obj.base, material=obj.materials[-1])
            return
        if isinstance(obj, Surface):
            self._add_surface(plotter, obj, material)
            return
        if isinstance(obj, Curve):
            self._add_curve(plotter, obj, material)
            return
        # Axes / Label are no-ops for the W3 preview; land with TikZ codegen.

    def _add_surface(
        self, plotter: pv.Plotter, surface: Any, material: Material | None
    ) -> None:
        import numpy as np

        from sheaf.numeric import adaptive_mesh, compiled

        c = compiled(surface)
        mesh = adaptive_mesh(c, base_n=6, chord_eps=8e-3, max_depth=5)
        faces = np.empty((mesh.n_triangles, 4), dtype=np.int64)
        faces[:, 0] = 3
        faces[:, 1:] = mesh.triangles
        poly = pv.PolyData(mesh.points, faces=faces.ravel())
        kwargs = _surface_kwargs(material)
        plotter.add_mesh(poly, **kwargs)

    def _add_curve(
        self, plotter: pv.Plotter, curve: Any, material: Material | None
    ) -> None:
        from sheaf.numeric import compiled

        c = compiled(curve)
        pts = c.sample(n=400)
        poly = pv.lines_from_points(pts)
        kwargs = _curve_kwargs(material)
        plotter.add_mesh(poly, **kwargs)

    def _light_scene(self, plotter: pv.Plotter) -> None:
        """Two-point studio lighting: warm key above-right, cool fill below-left."""
        plotter.remove_all_lights()
        key = pv.Light(position=(2, 2, 3), focal_point=(0, 0, 0), color="#fff4e0")
        key.intensity = 0.9
        fill = pv.Light(position=(-2, -1, 1), focal_point=(0, 0, 0), color="#d6e4ff")
        fill.intensity = 0.35
        ambient = pv.Light(light_type="headlight", color="white")
        ambient.intensity = 0.15
        for light in (key, fill, ambient):
            plotter.add_light(light)


# ---------------------------------------------------------------------------
# Material → PyVista kwargs
# ---------------------------------------------------------------------------


def _surface_kwargs(material: Material | None) -> dict[str, Any]:
    if material is None:
        return dict(
            color="#c8cdd4",
            smooth_shading=True,
            specular=0.2,
            specular_power=15,
            ambient=0.25,
            diffuse=0.85,
        )
    name = material.name
    p = material.params
    if name == "chalkboard":
        return dict(
            color=p["surface_fill"],
            smooth_shading=True,
            show_edges=True,
            edge_color=p["wire_color"],
            line_width=p["wire_width"] * 3,
            opacity=p["alpha"],
            ambient=0.2,
            diffuse=0.9,
            specular=0.05,
        )
    if name == "blueprint":
        return dict(
            color=p["surface_fill"],
            smooth_shading=True,
            show_edges=True,
            edge_color=p["wire_color"],
            line_width=p["wire_width"] * 3,
            opacity=p["alpha"],
            ambient=0.3,
            diffuse=0.7,
            specular=0.1,
        )
    if name == "glass":
        return dict(
            color=p["surface_fill"],
            smooth_shading=True,
            opacity=p["alpha"],
            ambient=0.35,
            diffuse=0.55,
            specular=1.0,
            specular_power=40,
        )
    return dict(color="#888888", smooth_shading=True)


def _curve_kwargs(material: Material | None) -> dict[str, Any]:
    if material is None:
        return dict(color="#1a1a1a", line_width=5, render_lines_as_tubes=True)
    # A curve's "material" maps to an ink colour — legible on white paper.
    color = {
        "chalkboard": "#2b3a2e",
        "blueprint": "#0b3d6b",
        "glass": "#1a5f7a",
    }.get(material.name, "#1a1a1a")
    return dict(color=color, line_width=6, render_lines_as_tubes=True)
