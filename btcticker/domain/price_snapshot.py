from __future__ import annotations
import sys

from dataclasses import dataclass
from datetime import datetime

DATACLASS_KWARGS = {"slots": True} if sys.version_info >= (3, 10) else {}

@dataclass(**DATACLASS_KWARGS)
class PriceSnapshot:
    fiat: str
    fiat_price: float | None
    usd_price: float | None
    sat_per_fiat: float | None
    sat_per_usd: float | None
    timestamp: datetime | None = None

    @property
    def has_fiat_price(self) -> bool:
        return self.fiat_price is not None

    @property
    def has_usd_price(self) -> bool:
        return self.usd_price is not None
