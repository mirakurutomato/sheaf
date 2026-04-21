"""sheaf — declarative 3D graphics DSL for LaTeX papers.

Operator semantics (see README):
    A + B           scene composition
    A @ M           material application
    A >> Paper(...) render to LaTeX artifact
    A & B, A | B, A - B, A ^ B   CSG on Implicit surfaces
"""

from sheaf.core import Renderable, Styled
from sheaf.materials import Blueprint, Chalkboard, Glass, Material
from sheaf.objects import Axes, Curve, Implicit, Label, Surface
from sheaf.paper import Paper, PaperArtifact
from sheaf.scene import Scene

__version__ = "0.0.1"

__all__ = [
    "Axes",
    "Blueprint",
    "Chalkboard",
    "Curve",
    "Glass",
    "Implicit",
    "Label",
    "Material",
    "Paper",
    "PaperArtifact",
    "Renderable",
    "Scene",
    "Styled",
    "Surface",
    "__version__",
]
