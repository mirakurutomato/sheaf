"""Smoke test: the public surface imports cleanly and __all__ resolves."""

from __future__ import annotations

import sheaf


def test_public_api_resolves() -> None:
    for name in sheaf.__all__:
        assert hasattr(sheaf, name), f"sheaf.{name} missing"


def test_version_is_string() -> None:
    assert isinstance(sheaf.__version__, str)
    assert sheaf.__version__.count(".") >= 2
