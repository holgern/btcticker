import sys
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

DATACLASS_KWARGS = {"slots": True} if sys.version_info >= (3, 10) else {}


@dataclass(**DATACLASS_KWARGS)
class PriceHistoryPoint:
    timestamp: datetime | None
    price: float


@dataclass(**DATACLASS_KWARGS)
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


@dataclass(**DATACLASS_KWARGS)
class PriceHistory:
    prices: list[PriceHistoryPoint] = field(default_factory=list)
    ohlc: list[OHLCPoint] = field(default_factory=list)

    def as_timeseries(self) -> list[float]:
        return [point.price for point in self.prices]

    def as_ohlc_rows(self) -> list[dict[str, Any]]:
        return [point.as_row() for point in self.ohlc]
