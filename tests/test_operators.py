"""Operator semantics — the DSL surface that future phases must not break.

These tests pin down exactly how `+`, `@`, `>>`, and CSG operators dispatch,
so that later changes to the rendering pipeline cannot silently alter the
user-visible syntax.
"""

from __future__ import annotations

import sympy as sp
from sympy.abc import t, u, v, x, y, z

from sheaf import (
    Axes,
    Blueprint,
    Chalkboard,
    Curve,
    Glass,
    Implicit,
    Label,
    Paper,
    PaperArtifact,
    Scene,
    Styled,
    Surface,
)

# ---------------------------------------------------------------------------
# @  :  material application
# ---------------------------------------------------------------------------


def test_matmul_wraps_surface_in_styled() -> None:
    s = Surface(z=x**2 - y**2) @ Chalkboard
    assert isinstance(s, Styled)
    assert isinstance(s.base, Surface)
    assert s.materials == (Chalkboard,)


def test_matmul_chains_flatten() -> None:
    s = Surface(z=x * y) @ Chalkboard @ Blueprint
    assert isinstance(s, Styled)
    assert s.materials == (Chalkboard, Blueprint)
    assert isinstance(s.base, Surface)  # base is not nested Styled


def test_matmul_on_implicit_works_too() -> None:
    sphere = Implicit(x**2 + y**2 + z**2 - 1)
    styled = sphere @ Glass
    assert isinstance(styled, Styled)
    assert styled.materials == (Glass,)


# ---------------------------------------------------------------------------
# +  :  scene composition
# ---------------------------------------------------------------------------


def test_add_two_renderables_yields_scene() -> None:
    scene = Axes() + Surface(z=x * y)
    assert isinstance(scene, Scene)
    assert len(scene) == 2


def test_add_flattens_nested_scenes() -> None:
    scene = Axes() + Surface(z=x * y) + Curve((sp.cos(t), sp.sin(t), t), t=(0, 1))
    assert isinstance(scene, Scene)
    assert len(scene) == 3  # not 2-nested


def test_add_preserves_styling_mid_composition_without_parens() -> None:
    """Central elegance test: `@` must bind tighter than `+`."""
    scene = Axes() + Surface(z=x * y) @ Chalkboard + Label("$p$", at=(0, 0, 0))
    assert isinstance(scene, Scene)
    assert len(scene) == 3
    assert isinstance(scene.items[1], Styled)  # Surface @ Chalkboard
    assert isinstance(scene.items[0], Axes)
    assert isinstance(scene.items[2], Label)


# ---------------------------------------------------------------------------
# >>  :  render to Paper
# ---------------------------------------------------------------------------


def test_rshift_to_paper_returns_artifact() -> None:
    art = Surface(z=x * y) @ Chalkboard >> Paper("main.tex", label="fig:a")
    assert isinstance(art, PaperArtifact)
    assert art.label == "fig:a"


def test_rshift_respects_precedence_against_plus() -> None:
    """`A + B @ C >> Paper()` must parse as `((A + (B @ C)) >> Paper())`."""
    art = Axes() + Surface(z=x * y) @ Chalkboard >> Paper()
    assert isinstance(art, PaperArtifact)


# ---------------------------------------------------------------------------
# CSG on Implicit:  &  |  -  ^
# ---------------------------------------------------------------------------


def test_csg_intersection_produces_implicit() -> None:
    torus = Implicit((x**2 + y**2 + z**2 + 3) ** 2 - 16 * (x**2 + y**2))
    sphere = Implicit(x**2 + y**2 + z**2 - 4)
    both = torus & sphere
    assert isinstance(both, Implicit)


def test_csg_union_difference_xor_all_produce_implicit() -> None:
    a = Implicit(x**2 + y**2 + z**2 - 1)
    b = Implicit((x - 0.5) ** 2 + y**2 + z**2 - 1)
    assert isinstance(a | b, Implicit)
    assert isinstance(a - b, Implicit)
    assert isinstance(a ^ b, Implicit)


# ---------------------------------------------------------------------------
# Parametric surface / curve construction
# ---------------------------------------------------------------------------


def test_parametric_mobius_strip_constructs() -> None:
    mobius = Surface(
        (
            (1 + v / 2 * sp.cos(u / 2)) * sp.cos(u),
            (1 + v / 2 * sp.cos(u / 2)) * sp.sin(u),
            v / 2 * sp.sin(u / 2),
        ),
        u=(0, 2 * sp.pi),
        v=(-1, 1),
    )
    assert mobius.kind == "parametric"
    assert len(mobius.exprs) == 3


def test_surface_rejects_both_forms() -> None:
    import pytest

    with pytest.raises(ValueError, match="not both"):
        Surface((x, y, z), z=x)  # type: ignore[arg-type]


def test_surface_requires_one_form() -> None:
    import pytest

    with pytest.raises(ValueError, match="required"):
        Surface()
