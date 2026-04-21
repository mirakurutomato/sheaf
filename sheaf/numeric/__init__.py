"""Numeric layer: SymPy expressions → NumPy-backed callables + analysis.

This is the bridge between the DSL (symbolic objects in `sheaf.objects`) and
the downstream mesh / vector pipelines. It provides:

* `compiled(obj)` — lower a DSL object into a `Compiled*` with a fast
  vectorised `.sample()` and a symbolic Jacobian kept for analysis.
* `singular_points(compiled_obj)` — grid-SVD search for parameter-space
  points where the Jacobian loses rank (Month 1 W2 delivery).

The symbolic Jacobian is retained on every `Compiled*` so Month 1 W3 can
reuse it for curvature-driven adaptive refinement without recompilation.
"""

from __future__ import annotations

from sheaf.numeric.analysis import (
    gradient_zeros,
    is_singular,
    singular_points,
)
from sheaf.numeric.compiler import (
    Compiled,
    CompiledCurve,
    CompiledImplicit,
    CompiledSurface,
    compiled,
)
from sheaf.numeric.curvature import (
    CriticalKind,
    CriticalPoint,
    classify_critical_points,
)
from sheaf.numeric.mesh import AdaptiveMesh, adaptive_mesh
from sheaf.numeric.topology import Topology, analyze, weld_duplicate_vertices

__all__ = [
    "AdaptiveMesh",
    "Compiled",
    "CompiledCurve",
    "CompiledImplicit",
    "CompiledSurface",
    "CriticalKind",
    "CriticalPoint",
    "Topology",
    "adaptive_mesh",
    "analyze",
    "classify_critical_points",
    "compiled",
    "gradient_zeros",
    "is_singular",
    "singular_points",
    "weld_duplicate_vertices",
]
