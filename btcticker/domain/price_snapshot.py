from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime


@dataclass(slots=True)
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
