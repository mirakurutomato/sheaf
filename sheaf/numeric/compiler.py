"""Lower a DSL object into a NumPy-backed callable with symbolic metadata.

A `Compiled*` bundles

* a vectorised numeric evaluator (`eval_fn`) suitable for meshgrid sampling,
* a vectorised Jacobian / gradient (`jacobian_fn`) returning arrays shaped
  so that `np.linalg.svd` along the last two axes yields singular values
  at every grid point,
* the original symbolic expressions and SymPy Jacobian, retained for
  downstream symbolic analysis (curvature, singularity solving).

The explicit form `Surface(z=f(x,y))` is internally promoted to parametric
`(x, y) -> (x, y, f(x,y))`, so callers need only handle one surface shape.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Protocol

import numpy as np
import sympy as sp

from sheaf.objects import Curve, Implicit, Surface

type Domain1 = tuple[float, float]
type Domain2 = tuple[Domain1, Domain1]
type Domain3 = tuple[Domain1, Domain1, Domain1]


class _VarArgCallable(Protocol):
    def __call__(self, *args: Any) -> Any: ...


# ---------------------------------------------------------------------------
# Compiled object hierarchy
# ---------------------------------------------------------------------------


class Compiled:
    """Base marker for all compiled forms."""


@dataclass(frozen=True, slots=True)
class CompiledSurface(Compiled):
    """2-parameter → 3-vector map with a 3x2 Jacobian at every point."""

    eval_fn: _VarArgCallable  # (u, v) -> tuple[ndarray, ndarray, ndarray]
    jacobian_fn: _VarArgCallable  # (u, v) -> ndarray shape (..., 3, 2)
    params: tuple[sp.Symbol, sp.Symbol]
    domain: Domain2
    exprs_sym: tuple[sp.Expr, sp.Expr, sp.Expr]
    jacobian_sym: sp.Matrix

    def sample(self, n: int = 50) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Uniform (n × n) grid in parameter space → 3 arrays of shape (n, n)."""
        (u0, u1), (v0, v1) = self.domain
        uu, vv = np.meshgrid(
            np.linspace(u0, u1, n), np.linspace(v0, v1, n), indexing="ij"
        )
        x, y, z = self.eval_fn(uu, vv)
        shape = uu.shape
        return (
            np.broadcast_to(np.asarray(x, dtype=float), shape).copy(),
            np.broadcast_to(np.asarray(y, dtype=float), shape).copy(),
            np.broadcast_to(np.asarray(z, dtype=float), shape).copy(),
        )

    def parameter_grid(self, n: int = 50) -> tuple[np.ndarray, np.ndarray]:
        (u0, u1), (v0, v1) = self.domain
        return np.meshgrid(
            np.linspace(u0, u1, n), np.linspace(v0, v1, n), indexing="ij"
        )


@dataclass(frozen=True, slots=True)
class CompiledCurve(Compiled):
    """1-parameter → 3-vector map with a 3x1 tangent Jacobian."""

    eval_fn: _VarArgCallable  # (t,) -> tuple[ndarray, ndarray, ndarray]
    tangent_fn: _VarArgCallable  # (t,) -> ndarray shape (..., 3)
    param: sp.Symbol
    domain: Domain1
    exprs_sym: tuple[sp.Expr, sp.Expr, sp.Expr]
    tangent_sym: sp.Matrix

    def sample(self, n: int = 200) -> np.ndarray:
        """Return an (n, 3) array of points along the curve."""
        t0, t1 = self.domain
        t = np.linspace(t0, t1, n)
        x, y, z = self.eval_fn(t)
        shape = t.shape
        return np.stack(
            (
                np.broadcast_to(np.asarray(x, dtype=float), shape).copy(),
                np.broadcast_to(np.asarray(y, dtype=float), shape).copy(),
                np.broadcast_to(np.asarray(z, dtype=float), shape).copy(),
            ),
            axis=-1,
        )


@dataclass(frozen=True, slots=True)
class CompiledImplicit(Compiled):
    """Scalar field F(x,y,z) with its gradient ∇F (singularity = zero set of ∇F ∩ zero set of F)."""

    eval_fn: _VarArgCallable  # (x, y, z) -> ndarray
    gradient_fn: _VarArgCallable  # (x, y, z) -> ndarray shape (..., 3)
    vars: tuple[sp.Symbol, sp.Symbol, sp.Symbol]
    expr_sym: sp.Expr
    gradient_sym: sp.Matrix

    def evaluate(self, x: np.ndarray, y: np.ndarray, z: np.ndarray) -> np.ndarray:
        shape = np.broadcast_shapes(np.shape(x), np.shape(y), np.shape(z))
        return np.broadcast_to(
            np.asarray(self.eval_fn(x, y, z), dtype=float), shape
        ).copy()

    def gradient(self, x: np.ndarray, y: np.ndarray, z: np.ndarray) -> np.ndarray:
        return self.gradient_fn(x, y, z)


# ---------------------------------------------------------------------------
# Dispatcher
# ---------------------------------------------------------------------------


def compiled(obj: Surface | Curve | Implicit) -> Compiled:
    """Lower a DSL object into its numeric form."""
    if isinstance(obj, Surface):
        return _compile_surface(obj)
    if isinstance(obj, Curve):
        return _compile_curve(obj)
    if isinstance(obj, Implicit):
        return _compile_implicit(obj)
    raise TypeError(f"cannot compile {type(obj).__name__}")


# ---------------------------------------------------------------------------
# Per-kind compilers
# ---------------------------------------------------------------------------


def _compile_surface(s: Surface) -> CompiledSurface:
    if s.kind == "explicit":
        # Promote z=f(x,y) to parametric (x, y) -> (x, y, f(x,y))
        (z_expr,) = s.exprs
        params = _two_params(s, z_expr)
        p0, p1 = params
        exprs: tuple[sp.Expr, sp.Expr, sp.Expr] = (p0, p1, z_expr)
    else:
        exprs = s.exprs  # type: ignore[assignment]
        params = _two_params(s, *exprs)

    domain = _two_domain(params, s.domain)
    eval_fn = _lambdify_tuple(params, exprs)
    jac_sym = sp.Matrix([[sp.diff(e, p) for p in params] for e in exprs])
    jac_fn = _lambdify_matrix(params, jac_sym)
    return CompiledSurface(
        eval_fn=eval_fn,
        jacobian_fn=jac_fn,
        params=params,
        domain=domain,
        exprs_sym=exprs,
        jacobian_sym=jac_sym,
    )


def _compile_curve(c: Curve) -> CompiledCurve:
    free: set[sp.Symbol] = set()
    for e in c.exprs:
        free |= e.free_symbols  # type: ignore[arg-type]
    param_syms = tuple(c.domain.keys()) if c.domain else tuple(sorted(free, key=str))
    if len(param_syms) != 1:
        raise ValueError(
            f"Curve requires exactly one parameter, got {len(param_syms)} "
            f"({[str(s) for s in param_syms]!r})"
        )
    (param,) = param_syms
    domain = c.domain.get(param, (-1.0, 1.0))
    exprs = c.exprs
    eval_fn = _lambdify_tuple((param,), exprs)
    tangent_sym = sp.Matrix([sp.diff(e, param) for e in exprs])
    tangent_fn = _lambdify_matrix((param,), tangent_sym)
    return CompiledCurve(
        eval_fn=eval_fn,
        tangent_fn=tangent_fn,
        param=param,
        domain=domain,
        exprs_sym=exprs,  # type: ignore[arg-type]
        tangent_sym=tangent_sym,
    )


def _compile_implicit(im: Implicit) -> CompiledImplicit:
    from sheaf.objects import _CSG

    if isinstance(im._def, _CSG):
        raise NotImplementedError(
            "CSG compilation (signed-distance-based boolean on Implicit) "
            "arrives in Month 2 W5 with the manifold3d bridge."
        )
    expr = im._def
    free = tuple(sorted(expr.free_symbols, key=str))
    if len(free) > 3:
        raise ValueError(f"Implicit must have ≤3 variables, got {len(free)}: {free!r}")
    # Pad to exactly 3 vars (x, y, z order) using sympy symbols
    x, y, z = sp.symbols("x y z")
    vars_: tuple[sp.Symbol, sp.Symbol, sp.Symbol] = (x, y, z)
    if set(free) - {x, y, z}:
        raise ValueError(
            f"Implicit variables must be a subset of {{x, y, z}}, got {free!r}"
        )
    eval_fn = sp.lambdify(vars_, expr, modules="numpy")
    grad_sym = sp.Matrix([sp.diff(expr, v) for v in vars_])
    grad_fn = _lambdify_matrix(vars_, grad_sym)
    return CompiledImplicit(
        eval_fn=eval_fn,
        gradient_fn=grad_fn,
        vars=vars_,
        expr_sym=expr,
        gradient_sym=grad_sym,
    )


# ---------------------------------------------------------------------------
# Parameter / domain resolution
# ---------------------------------------------------------------------------


def _two_params(s: Surface, *exprs: sp.Expr) -> tuple[sp.Symbol, sp.Symbol]:
    """Pick exactly two parameters: user-supplied domain keys if any, else free symbols."""
    if s.domain:
        syms = tuple(s.domain.keys())
    else:
        free: set[sp.Symbol] = set()
        for e in exprs:
            free |= e.free_symbols  # type: ignore[arg-type]
        syms = tuple(sorted(free, key=str))
    if len(syms) != 2:
        raise ValueError(
            f"Surface requires exactly two parameters, got {len(syms)} "
            f"({[str(s) for s in syms]!r}). Provide them via kwargs "
            "(e.g. x=(-1, 1), y=(-1, 1))."
        )
    return syms  # type: ignore[return-value]


def _two_domain(
    params: tuple[sp.Symbol, sp.Symbol],
    user: dict[sp.Symbol, tuple[float, float]],
) -> Domain2:
    return (
        user.get(params[0], (-1.0, 1.0)),
        user.get(params[1], (-1.0, 1.0)),
    )


# ---------------------------------------------------------------------------
# Vectorised lambdify helpers
# ---------------------------------------------------------------------------


def _lambdify_tuple(
    params: tuple[sp.Symbol, ...],
    exprs: tuple[sp.Expr, ...],
) -> _VarArgCallable:
    """Return a callable producing a tuple of arrays, one per expr.

    Each entry is lambdified separately so that constant expressions broadcast
    correctly over array inputs (sympy.lambdify of a constant returns the scalar).
    """
    fns = [sp.lambdify(params, e, modules="numpy") for e in exprs]

    def call(*args: Any) -> tuple[np.ndarray, ...]:
        return tuple(f(*args) for f in fns)

    return call


def _lambdify_matrix(
    params: tuple[sp.Symbol, ...],
    matrix: sp.Matrix,
) -> _VarArgCallable:
    """Return a callable yielding an ndarray of shape (..., rows, cols).

    Entry-wise lambdify + explicit broadcast is used so that constant entries
    (e.g. the 1s in ∂x/∂x) do not collapse the output shape.
    """
    rows, cols = matrix.shape
    entries = [
        [sp.lambdify(params, matrix[i, j], modules="numpy") for j in range(cols)]
        for i in range(rows)
    ]

    def call(*args: Any) -> np.ndarray:
        shape = np.broadcast_shapes(*[np.shape(np.asarray(a)) for a in args])
        result = np.empty((*shape, rows, cols), dtype=float)
        for i in range(rows):
            for j in range(cols):
                val = entries[i][j](*args)
                result[..., i, j] = np.broadcast_to(val, shape)
        return result

    return call
