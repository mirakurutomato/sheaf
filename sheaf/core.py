"""Core ABCs and operator-overload machinery for the sheaf DSL.

The four user-facing operators are defined here on `Renderable` so that every
object in the DSL (surfaces, curves, scenes, labels, ...) composes uniformly:

    Renderable + Renderable       -> Scene               scene composition
    Renderable @ Material         -> Styled              material application
    Renderable >> Paper           -> PaperArtifact       render
    Implicit & | - ^ Implicit     -> Implicit            CSG (in sheaf.objects)

`@` is used for materials because Python evaluates it with the tightest binary
precedence, which lets expressions like

    Axes() + Surface(z=f) @ Chalkboard + Curve(...) >> Paper("main.tex")

evaluate as the user reads them, without parentheses.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from sheaf.materials import Material
    from sheaf.paper import PaperArtifact
    from sheaf.scene import Scene


class Renderable:
    """Anything that can participate in a scene or be rendered to a `Paper`.

    Not an ABC on purpose: subclasses simply inherit the operator overloads
    and add their own state.  The class exists solely to anchor the shared
    `+`, `@`, `>>` dispatch logic.
    """

    def __add__(self, other: object) -> Scene:
        from sheaf.scene import Scene

        if isinstance(other, Renderable):
            return Scene._compose(self, other)
        return NotImplemented  # type: ignore[return-value]

    def __radd__(self, other: object) -> Scene:
        from sheaf.scene import Scene

        if isinstance(other, Renderable):
            return Scene._compose(other, self)
        return NotImplemented  # type: ignore[return-value]

    def __matmul__(self, other: object) -> Styled:
        from sheaf.materials import Material

        if isinstance(other, Material):
            return Styled(self, other)
        return NotImplemented  # type: ignore[return-value]

    def __rshift__(self, other: object) -> PaperArtifact:
        from sheaf.paper import Paper

        if isinstance(other, Paper):
            return other.render(self)
        return NotImplemented  # type: ignore[return-value]


class Styled(Renderable):
    """A `Renderable` with an ordered chain of materials / filters applied.

    Chained applications flatten:
        (surface @ A) @ B  ==  Styled(surface, materials=(A, B))
    """

    __slots__ = ("base", "materials")

    def __init__(self, base: Renderable, *materials: Material) -> None:
        if isinstance(base, Styled):
            self.base: Renderable = base.base
            self.materials: tuple[Material, ...] = base.materials + materials
        else:
            self.base = base
            self.materials = materials

    def __matmul__(self, other: object) -> Styled:
        from sheaf.materials import Material

        if isinstance(other, Material):
            return Styled(self.base, *self.materials, other)
        return NotImplemented  # type: ignore[return-value]

    def __repr__(self) -> str:
        chain = " @ ".join(m.name for m in self.materials)
        return f"{self.base!r} @ {chain}"
