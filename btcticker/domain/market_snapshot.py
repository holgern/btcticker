from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from btcticker.domain.price_snapshot import PriceSnapshot


@dataclass(slots=True)
class MarketSnapshot:
    price_snapshot: PriceSnapshot
    mempool: dict[str, Any]
    price_now: str
    price_change: str
    days_ago: int
    timeseries: list[float] = field(default_factory=list)
    ohlc_history: Any = None
    current_time: datetime = field(default_factory=datetime.now)
