import sys
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from btcticker.domain.price_snapshot import PriceSnapshot

DATACLASS_KWARGS = {"slots": True} if sys.version_info >= (3, 10) else {}

@dataclass(**DATACLASS_KWARGS)
class MarketSnapshot:
    price_snapshot: PriceSnapshot
    mempool: dict[str, Any]
    price_now: str
    price_change: str
    days_ago: int
    timeseries: list[float] = field(default_factory=list)
    ohlc_history: list[dict[str, Any]] = field(default_factory=list)
    current_time: datetime = field(default_factory=datetime.now)
