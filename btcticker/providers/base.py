from __future__ import annotations

from typing import Any, Protocol

from btcticker.domain.price_snapshot import PriceSnapshot


class PriceProviderError(Exception):
    """Base exception for price provider failures."""


class PriceMarketNotFoundError(PriceProviderError):
    """Raised when a configured market does not exist."""


class PriceHistoryUnavailableError(PriceProviderError):
    """Raised when historical price data cannot be retrieved."""


class PriceSnapshotIncompleteError(PriceProviderError):
    """Raised when a provider cannot construct a usable current snapshot."""


class LegacyPriceProviderUnavailableError(PriceProviderError):
    """Raised when the optional btcpriceticker adapter cannot be used."""


class PriceProvider(Protocol):
    days_ago: int
    min_refresh_time: int

    def set_days_ago(self, days_ago: int) -> None: ...

    def set_min_refresh_time(self, min_refresh_time: int) -> None: ...

    def refresh(self) -> None: ...

    def get_snapshot(self) -> PriceSnapshot: ...

    def get_price_now(self) -> str: ...

    def get_price_change(self) -> str: ...

    def get_timeseries_list(self) -> list[float]: ...

    def get_ohlc_history(self) -> list[dict[str, Any]] | Any: ...
