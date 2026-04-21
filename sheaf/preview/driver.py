"""Abstract preview driver + dispatcher.

Drivers are instantiated lazily so that importing `sheaf.preview` does not
pull in PyVista / VisPy. The real driver bodies (which import heavy GUI
libraries) arrive in Month 1 W4.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Literal

if TYPE_CHECKING:
    from sheaf.core import Renderable

type Backend = Literal["pyvista", "vispy"]


class PreviewDriver(ABC):
    """Contract every preview backend must satisfy."""

    name: str

    @abstractmethod
    def show(self, obj: Renderable) -> None:
        """Open an interactive window rendering `obj`."""


def _make_driver(backend: Backend) -> PreviewDriver:
    match backend:
        case "pyvista":
            from sheaf.preview.pyvista_driver import PyVistaDriver

            return PyVistaDriver()
        case "vispy":
            from sheaf.preview.vispy_driver import VisPyDriver

            return VisPyDriver()
        case _:
            raise ValueError(f"unknown preview backend: {backend!r}")


def preview(obj: Renderable, *, backend: Backend = "pyvista") -> None:
    """Open an interactive preview of `obj` using the requested backend."""
    _make_driver(backend).show(obj)


def screenshot(
    obj: Renderable,
    path: str,
    *,
    size: tuple[int, int] = (1600, 1200),
    backend: Backend = "pyvista",
) -> str:
    """Render `obj` off-screen and save a PNG to `path`. Returns `path`."""
    driver = _make_driver(backend)
    if not hasattr(driver, "screenshot"):
        raise NotImplementedError(f"backend {backend!r} has no screenshot() yet")
    return driver.screenshot(obj, path, size=size)  # type: ignore[attr-defined]
