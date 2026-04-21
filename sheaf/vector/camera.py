"""Orthographic axonometric camera — Month 2 W8.

Projects ``(N, 3)`` world-space points to ``(N, 2)`` screen-space coordinates
using a right-handed view frame derived from ``position``, ``target``, and
``up``.  Parallel projection is the natural default for publication figures:
no perspective foreshortening, parallel lines in space stay parallel on page.

For painter's-algorithm sorting (:mod:`sheaf.vector.bsp`), use ``position``
directly as the ``view`` argument — the BSP compares signed distances, and
an orthographic view point simulates the limit "infinitely far along
``view_dir``" as long as ``position`` sits well outside the scene's
bounding box.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np


@dataclass(frozen=True, slots=True)
class Camera:
    """Orthographic axonometric camera.

    ``right × up = −forward`` (right-handed), with ``forward`` pointing from
    scene to camera, so ``project(target) == (0, 0)``.
    """

    position: np.ndarray
    target: np.ndarray
    up: np.ndarray

    @classmethod
    def isometric(
        cls,
        center: tuple[float, float, float] | np.ndarray = (0.0, 0.0, 0.0),
        distance: float = 10.0,
    ) -> Camera:
        """Classical isometric axonometric: equal angles to all three axes."""
        c = np.asarray(center, dtype=float)
        direction = np.array([1.0, 1.0, 1.0]) / np.sqrt(3.0)
        return cls(
            position=c + distance * direction,
            target=c,
            up=np.array([0.0, 0.0, 1.0]),
        )

    def forward(self) -> np.ndarray:
        """Unit vector pointing FROM ``target`` TO ``position``."""
        d = np.asarray(self.position, dtype=float) - np.asarray(self.target, dtype=float)
        norm = float(np.linalg.norm(d))
        if norm < 1e-12:
            raise ValueError("camera position coincides with target")
        return d / norm

    def basis(self) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Return the screen basis ``(right, up, forward)`` in world space."""
        f = self.forward()
        up_w = np.asarray(self.up, dtype=float)
        r = np.cross(up_w, f)
        r_norm = float(np.linalg.norm(r))
        if r_norm < 1e-10:
            raise ValueError("camera up is parallel to view direction")
        r = r / r_norm
        u = np.cross(f, r)
        return r, u, f

    def project(self, points: np.ndarray) -> np.ndarray:
        """Project ``(..., 3)`` world points to ``(..., 2)`` screen coordinates."""
        r, u, _ = self.basis()
        rel = np.asarray(points, dtype=float) - np.asarray(self.target, dtype=float)
        x = rel @ r
        y = rel @ u
        return np.stack((x, y), axis=-1)
