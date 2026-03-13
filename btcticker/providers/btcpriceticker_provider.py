from __future__ import annotations

from datetime import datetime
from typing import Any

from btcticker.domain.price_snapshot import PriceSnapshot
from btcticker.providers.base import LegacyPriceProviderUnavailableError

try:
    from btcpriceticker.price import Price
except Exception:  # pragma: no cover - optional dependency during migration
    Price = None


class BTCPriceTickerProvider:
    def __init__(
        self,
        fiat: str,
        service: str = "coingecko",
        interval: str = "1h",
        days_ago: int = 1,
        enable_ohlc: bool = False,
        min_refresh_time: int = 120,
    ) -> None:
        if Price is None:
            raise LegacyPriceProviderUnavailableError(
                "btcpriceticker is not installed; legacy provider is unavailable"
            )

        self._price = Price(
            fiat=fiat,
            service=service,
            interval=interval,
            days_ago=days_ago,
            enable_ohlc=enable_ohlc,
        )
        self._price.min_refresh_time = min_refresh_time

    @property
    def days_ago(self) -> int:
        return self._price.days_ago

    @property
    def min_refresh_time(self) -> int:
        return self._price.min_refresh_time

    def set_days_ago(self, days_ago: int) -> None:
        self._price.set_days_ago(days_ago)

    def set_min_refresh_time(self, min_refresh_time: int) -> None:
        self._price.min_refresh_time = min_refresh_time

    def refresh(self) -> None:
        self._price.refresh()

    def get_snapshot(self) -> PriceSnapshot:
        price = getattr(self._price, "price", {}) or {}
        return PriceSnapshot(
            fiat=getattr(self._price, "fiat", ""),
            fiat_price=self._as_float(price.get("fiat")),
            usd_price=self._as_float(price.get("usd")),
            sat_per_fiat=self._as_float(price.get("sat_fiat")),
            sat_per_usd=self._as_float(price.get("sat_usd")),
            timestamp=self._coerce_timestamp(self._price.get_timestamp()),
        )

    def get_price_now(self) -> str:
        return self._price.get_price_now()

    def get_price_change(self) -> str:
        return self._price.get_price_change()

    def get_timeseries_list(self) -> list[float]:
        return list(self._price.get_timeseries_list())

    def get_ohlc_history(self) -> Any:
        return getattr(self._price, "ohlc", [])

    def get_timestamp(self) -> datetime | None:
        return self._coerce_timestamp(self._price.get_timestamp())

    @staticmethod
    def _as_float(value: Any) -> float | None:
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    @staticmethod
    def _coerce_timestamp(value: Any) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, (int, float)):
            try:
                timestamp = float(value)
                if timestamp > 10_000_000_000:
                    timestamp = timestamp / 1000
                return datetime.fromtimestamp(timestamp)
            except (OverflowError, OSError, ValueError):
                return None
        return None
