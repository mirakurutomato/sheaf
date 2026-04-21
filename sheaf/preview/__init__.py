"""Interactive preview backends (raster, developer-only).

The final LaTeX artifact pipeline never touches these. PyVista is the default;
VisPy is available for large-mesh / GPU-heavy cases.

    from sheaf import Surface
    from sheaf.preview import preview, screenshot
    preview(Surface(z=x*y))                       # interactive window
    screenshot(Surface(z=x*y), "monkey.png")      # off-screen PNG
"""

from __future__ import annotations

from sheaf.preview.driver import PreviewDriver, preview, screenshot

__all__ = ["PreviewDriver", "preview", "screenshot"]
