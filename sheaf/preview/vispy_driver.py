"""VisPy (OpenGL) preview driver — for large meshes / GPU-heavy scenes.

Stub: real implementation arrives in Month 1 W4.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from sheaf.preview.driver import PreviewDriver

if TYPE_CHECKING:
    from sheaf.core import Renderable


class VisPyDriver(PreviewDriver):
    name = "vispy"

    def show(self, obj: Renderable) -> None:
        raise NotImplementedError(
            "VisPy preview arrives in Month 1 W4 (after the adaptive mesh engine)."
        )
