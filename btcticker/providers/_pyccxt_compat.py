from __future__ import annotations

import sys
from pathlib import Path


def _ensure_pyccxt_importable() -> None:
    try:
        import pyccxt  # noqa: F401

        return
    except ModuleNotFoundError:
        pass

    workspace_root = Path(__file__).resolve().parents[3]
    candidate = workspace_root.parent / "pyccxt"
    if candidate.exists():
        sys.path.append(str(candidate))


_ensure_pyccxt_importable()

from pyccxt import Exchange  # type: ignore[import-not-found]
from pyccxt.exceptions import (  # type: ignore[import-not-found]
    ExchangeInitializationError,
    ExchangeNotFoundError,
    MarketLoadError,
)

__all__ = [
    "Exchange",
    "ExchangeInitializationError",
    "ExchangeNotFoundError",
    "MarketLoadError",
]
