"""Primitive DSL objects: Surface, Implicit, Curve, Axes, Label.

All inherit `Renderable` and therefore support `+`, `@`, `>>` uniformly.
`Implicit` additionally supports CSG operators `&`, `|`, `-`, `^`.

The actual symbolic → numeric → mesh compilation is deferred to Month 1 W2.
This module currently captures the DSL surface (attribute schema + operator
overloads) so that downstream layers can rely on a stable type contract.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Literal

import sympy as sp

from sheaf.core import Renderable

type Expr = sp.Expr | sp.Basic
type Domain = dict[sp.Symbol, tuple[float, float]]
type Vec3 = tuple[float, float, float]


# ---------------------------------------------------------------------------
# Surface (explicit or parametric)
# ---------------------------------------------------------------------------


class Surface(Renderable):
    """A 2-manifold in R^3, specified either explicitly or parametrically.

    Explicit form:
        Surface(z=x**2 - y**2)                     # free symbols of `z`
        Surface(z=x**2 - y**2, x=(-2, 2), y=(-2, 2))

    Parametric form:
        Surface((f(u,v), g(u,v), h(u,v)), u=(0, 1), v=(0, 1))

    Domains not supplied are inferred in W2 from the expression (or fall back
    to [-1, 1] for each free symbol).
    """

    __slots__ = ("kind", "exprs", "domain")

    kind: Literal["explicit", "parametric"]
    exprs: tuple[Expr, ...]
    domain: Domain

    def __init__(
        self,
        parametric: tuple[Expr, Expr, Expr] | None = None,
        /,
        *,
        z: Expr | None = None,
        **domain: tuple[float, float],
    ) -> None:
        if parametric is not None and z is not None:
            raise ValueError("Surface: pass either `z=` or a parametric tuple, not both")
        if parametric is None and z is None:
            raise ValueError("Surface: `z=` or a parametric tuple is required")

        parsed_domain: Domain = {sp.Symbol(k): tuple(map(float, v)) for k, v in domain.items()}  # type: ignore[misc]

        if z is not None:
            self.kind = "explicit"
            self.exprs = (sp.sympify(z),)
        else:
            assert parametric is not None
            if len(parametric) != 3:
                raise ValueError("Surface: parametric tuple must have 3 components")
            self.kind = "parametric"
            self.exprs = tuple(sp.sympify(e) for e in parametric)

        self.domain = parsed_domain

    def free_symbols(self) -> set[sp.Symbol]:
        syms: set[sp.Symbol] = set()
        for e in self.exprs:
            syms |= e.free_symbols  # type: ignore[arg-type]
        return syms

    def __repr__(self) -> str:
        if self.kind == "explicit":
            return f"Surface(z={self.exprs[0]})"
        return f"Surface({self.exprs})"


# ---------------------------------------------------------------------------
# Implicit surface (zero set of a scalar field) with CSG operators
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class _CSG:
    op: Literal["and", "or", "sub", "xor"]
    left: Implicit
    right: Implicit


class Implicit(Renderable):
    """Zero set {x ∈ R^3 : f(x) = 0} of a scalar field, supporting CSG."""

    __slots__ = ("_def",)

    def __init__(self, expr_or_op: Expr | _CSG) -> None:
        self._def: Expr | _CSG = expr_or_op if isinstance(expr_or_op, _CSG) else sp.sympify(expr_or_op)

    def __and__(self, other: object) -> Implicit:
        if isinstance(other, Implicit):
            return Implicit(_CSG("and", self, other))
        return NotImplemented  # type: ignore[return-value]

    def __or__(self, other: object) -> Implicit:
        if isinstance(other, Implicit):
            return Implicit(_CSG("or", self, other))
        return NotImplemented  # type: ignore[return-value]

    def __sub__(self, other: object) -> Implicit:
        if isinstance(other, Implicit):
            return Implicit(_CSG("sub", self, other))
        return NotImplemented  # type: ignore[return-value]

    def __xor__(self, other: object) -> Implicit:
        if isinstance(other, Implicit):
            return Implicit(_CSG("xor", self, other))
        return NotImplemented  # type: ignore[return-value]

    def __repr__(self) -> str:
        if isinstance(self._def, _CSG):
            sym = {"and": "&", "or": "|", "sub": "-", "xor": "^"}[self._def.op]
            return f"Implicit({self._def.left} {sym} {self._def.right})"
        return f"Implicit({self._def} == 0)"


# ---------------------------------------------------------------------------
# Curve, Axes, Label
# ---------------------------------------------------------------------------


class Curve(Renderable):
    """A 1-manifold in R^3, parametrized by a single scalar."""

    __slots__ = ("exprs", "domain")

    def __init__(
        self,
        parametric: tuple[Expr, Expr, Expr],
        /,
        **domain: tuple[float, float],
    ) -> None:
        if len(parametric) != 3:
            raise ValueError("Curve: parametric tuple must have 3 components")
        self.exprs: tuple[Expr, ...] = tuple(sp.sympify(e) for e in parametric)
        self.domain: Domain = {sp.Symbol(k): tuple(map(float, v)) for k, v in domain.items()}  # type: ignore[misc]

    def __repr__(self) -> str:
        return f"Curve({self.exprs})"


class Axes(Renderable):
    """Coordinate axes. Auto-fits to the bounding box of the scene if `range` omitted."""

    __slots__ = ("range",)

    def __init__(self, *, range: tuple[float, float] | None = None) -> None:  # noqa: A002
        self.range: tuple[float, float] | None = range

    def __repr__(self) -> str:
        return f"Axes(range={self.range!r})"


class Label(Renderable):
    """A LaTeX text label anchored at a 3D point."""

    __slots__ = ("text", "at", "anchor", "extra")

    def __init__(
        self,
        text: str,
        *,
        at: Vec3 = (0.0, 0.0, 0.0),
        anchor: str = "center",
        **extra: Any,
    ) -> None:
        self.text = text
        self.at = at
        self.anchor = anchor
        self.extra = extra

    def __repr__(self) -> str:
        return f"Label({self.text!r}, at={self.at!r})"
