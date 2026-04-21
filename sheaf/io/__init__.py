"""I/O helpers for the host LaTeX paper (Month 3 W9 →).

The DSL ultimately renders into someone else's ``main.tex``; the modules
here read just enough of that file to size the figure correctly and pick
the right engine.  Parsing is intentionally regex-shallow — running real
TeX is the only way to compute exact dimensions, and we defer to that
through the compile harness when we need a ground truth.
"""

from __future__ import annotations

from sheaf.io.main_tex import PaperContext, parse_main_tex

__all__ = ["PaperContext", "parse_main_tex"]
