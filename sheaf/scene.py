"""Scene: an ordered composition of Renderables."""

from __future__ import annotations

from sheaf.core import Renderable


class Scene(Renderable):
    """Ordered collection of renderables. Formed implicitly via `+`."""

    __slots__ = ("items",)

    def __init__(self, items: list[Renderable] | None = None) -> None:
        self.items: list[Renderable] = list(items) if items else []

    @classmethod
    def _compose(cls, left: Renderable, right: Renderable) -> Scene:
        items: list[Renderable] = []
        items.extend(left.items if isinstance(left, Scene) else [left])
        items.extend(right.items if isinstance(right, Scene) else [right])
        return cls(items)

    def __iter__(self):
        return iter(self.items)

    def __len__(self) -> int:
        return len(self.items)

    def __repr__(self) -> str:
        inner = ", ".join(repr(i) for i in self.items)
        return f"Scene([{inner}])"
