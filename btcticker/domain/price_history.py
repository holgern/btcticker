from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass(slots=True)
class PriceHistoryPoint:
    timestamp: datetime | None
    price: float


@dataclass(slots=True)
class OHLCPoint:
    timestamp: datetime | None
    open: float
    high: float
    low: float
    close: float
    volume: float | None = None

    def as_row(self) -> dict[str, Any]:
        return {
            "Open": self.open,
            "High": self.high,
            "Low": self.low,
            "Close": self.close,
            "Volume": self.volume,
            "Timestamp": self.timestamp,
        }


@dataclass(slots=True)
class PriceHistory:
    prices: list[PriceHistoryPoint] = field(default_factory=list)
    ohlc: list[OHLCPoint] = field(default_factory=list)

    def as_timeseries(self) -> list[float]:
        return [point.price for point in self.prices]

    def as_ohlc_rows(self) -> list[dict[str, Any]]:
        return [point.as_row() for point in self.ohlc]
