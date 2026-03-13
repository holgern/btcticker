from __future__ import annotations

import importlib
import importlib.util
import sys
from pathlib import Path


def _ensure_pyccxt_importable() -> None:
    if importlib.util.find_spec("pyccxt") is not None:
        return

    workspace_root = Path(__file__).resolve().parents[3]
    candidate = workspace_root.parent / "pyccxt"
    if candidate.exists():
        sys.path.append(str(candidate))


_ensure_pyccxt_importable()

_pyccxt = importlib.import_module("pyccxt")
_pyccxt_exceptions = importlib.import_module("pyccxt.exceptions")

Exchange = _pyccxt.Exchange
ExchangeInitializationError = _pyccxt_exceptions.ExchangeInitializationError
ExchangeNotFoundError = _pyccxt_exceptions.ExchangeNotFoundError
MarketLoadError = _pyccxt_exceptions.MarketLoadError

__all__ = [
    "Exchange",
    "ExchangeInitializationError",
    "ExchangeNotFoundError",
    "MarketLoadError",
]
