from __future__ import annotations

from datetime import datetime, timedelta, timezone
from math import ceil
from typing import Any, cast

from btcticker.domain.price_snapshot import PriceSnapshot
from btcticker.providers._pyccxt_compat import (
    Exchange,
    ExchangeInitializationError,
    ExchangeNotFoundError,
    MarketLoadError,
)
from btcticker.providers.base import (
    PriceHistoryUnavailableError,
    PriceMarketNotFoundError,
    PriceProviderError,
    PriceSnapshotIncompleteError,
)

Market = Any
TickerData = Any

INTERVAL_ALIASES = {
    "1h": "1h",
    "4h": "4h",
    "1d": "1d",
}


class PyCCXTPriceProvider:
    _exchange_cache: dict[tuple[str, int, int], Exchange] = {}

    def __init__(
        self,
        exchange_name: str,
        fiat_symbol: str,
        usd_symbol: str,
        interval: str,
        days_ago: int,
        enable_ohlc: bool,
        timeout_ms: int = 30000,
        min_refresh_time: int = 10,
    ) -> None:
        self.exchange_name = exchange_name.lower()
        self.fiat_symbol = fiat_symbol.upper()
        self.usd_symbol = usd_symbol.upper()
        self.interval = self._normalize_interval(interval)
        self.days_ago = days_ago
        self.enable_ohlc = enable_ohlc
        self.timeout_ms = timeout_ms
        self.min_refresh_time = min_refresh_time

        self._exchange = self._get_or_create_exchange()
        self._fiat_market = self._get_market(self.fiat_symbol)
        self._usd_market = self._get_market(self.usd_symbol, required=False)
        self._snapshot: PriceSnapshot | None = None
        self._price_now = "0"
        self._price_change = "0%"
        self._timeseries: list[float] = []
        self._ohlc_history: list[dict[str, Any]] = []
        self._last_refresh: datetime | None = None

    def set_days_ago(self, days_ago: int) -> None:
        self.days_ago = days_ago
        self._price_change = self._format_price_change(days_ago)

    def set_min_refresh_time(self, min_refresh_time: int) -> None:
        self.min_refresh_time = min_refresh_time
        self._exchange.min_refresh_time = min_refresh_time
        if self._fiat_market is not None:
            self._fiat_market.min_refresh_time = min_refresh_time
        if self._usd_market is not None:
            self._usd_market.min_refresh_time = min_refresh_time

    def refresh(self) -> None:
        if self._is_cache_fresh():
            return

        fiat_ticker = self._fetch_ticker(self._fiat_market, self.fiat_symbol)
        usd_ticker = self._fetch_ticker(
            self._usd_market, self.usd_symbol, required=False
        )

        self._timeseries = self._fetch_price_history()
        self._ohlc_history = self._fetch_ohlc() if self.enable_ohlc else []
        self._snapshot = self._build_snapshot(fiat_ticker, usd_ticker)
        self._price_now = self._format_price_now(self._snapshot.fiat_price)
        self._price_change = self._format_price_change(self.days_ago)
        self._last_refresh = datetime.now(timezone.utc)

    def get_snapshot(self) -> PriceSnapshot:
        if self._snapshot is None:
            self.refresh()
        if self._snapshot is None:
            raise PriceSnapshotIncompleteError("price snapshot is unavailable")
        return self._snapshot

    def get_price_now(self) -> str:
        if self._snapshot is None:
            self.refresh()
        return self._price_now

    def get_price_change(self) -> str:
        if self._snapshot is None:
            self.refresh()
        return self._price_change

    def get_timeseries_list(self) -> list[float]:
        if self._snapshot is None:
            self.refresh()
        return list(self._timeseries)

    def get_ohlc_history(self) -> list[dict[str, Any]]:
        if self._snapshot is None:
            self.refresh()
        return list(self._ohlc_history)

    def _get_or_create_exchange(self) -> Exchange:
        cache_key = (self.exchange_name, self.timeout_ms, self.min_refresh_time)
        exchange = self._exchange_cache.get(cache_key)
        if exchange is not None:
            return exchange

        try:
            exchange = Exchange(
                exchange_name=self.exchange_name,
                timeout=self.timeout_ms,
                min_refresh_time=self.min_refresh_time,
            )
        except (
            ExchangeInitializationError,
            ExchangeNotFoundError,
            MarketLoadError,
        ) as exc:
            raise PriceProviderError(str(exc)) from exc

        self._exchange_cache[cache_key] = exchange
        return exchange

    def _get_market(self, symbol: str, required: bool = True) -> Market | None:
        market = cast(Market | None, self._exchange.get_market(symbol))
        if market is None and required:
            raise PriceMarketNotFoundError(
                f"Market '{symbol}' not found on exchange '{self.exchange_name}'"
            )
        return market

    def _fetch_ticker(
        self,
        market: Market | None,
        symbol: str,
        required: bool = True,
    ) -> TickerData | None:
        if market is None:
            if required:
                raise PriceMarketNotFoundError(
                    f"Market '{symbol}' not found on exchange '{self.exchange_name}'"
                )
            return None

        ticker = market.get_ticker()
        if ticker is None or ticker.last is None:
            if required:
                raise PriceSnapshotIncompleteError(
                    f"Ticker data for '{symbol}' is missing a last price"
                )
            return None
        return ticker

    def _fetch_price_history(self) -> list[float]:
        if self._fiat_market is None:
            raise PriceMarketNotFoundError(
                f"Market '{self.fiat_symbol}' not found on exchange '{self.exchange_name}'"
            )

        fiat_market = self._fiat_market

        since = self._history_since(self.days_ago)
        limit = max(2, self._history_limit(self.days_ago))
        if not fiat_market.fetch_ohlc(
            timeframe=self.interval, since=since, limit=limit
        ):
            raise PriceHistoryUnavailableError(
                f"Unable to fetch price history for '{self.fiat_symbol}'"
            )

        rows = fiat_market.get_price_history()
        prices = [float(row["price"]) for row in rows if row.get("price") is not None]
        if not prices:
            raise PriceHistoryUnavailableError(
                f"Empty price history for '{self.fiat_symbol}'"
            )
        return prices

    def _fetch_ohlc(self) -> list[dict[str, Any]]:
        if self._fiat_market is None:
            return []

        fiat_market = self._fiat_market

        since = self._history_since(max(self.days_ago, 1))
        limit = max(2, self._history_limit(max(self.days_ago, 1)))
        if not fiat_market.fetch_ohlc(
            timeframe=self.interval, since=since, limit=limit
        ):
            return []
        return list(fiat_market.get_ohlc_history() or [])

    def _build_snapshot(
        self,
        fiat_ticker: TickerData,
        usd_ticker: TickerData | None,
    ) -> PriceSnapshot:
        fiat_price = float(fiat_ticker.last)
        usd_price = (
            float(usd_ticker.last)
            if usd_ticker and usd_ticker.last is not None
            else None
        )
        timestamp_ms = fiat_ticker.timestamp or getattr(usd_ticker, "timestamp", None)
        return PriceSnapshot(
            fiat=self.fiat_symbol.split("/")[-1].lower(),
            fiat_price=fiat_price,
            usd_price=usd_price,
            sat_per_fiat=self._compute_sats(fiat_price),
            sat_per_usd=self._compute_sats(usd_price),
            timestamp=self._coerce_timestamp(timestamp_ms),
        )

    def _format_price_change(self, days_ago: int) -> str:
        if not self._timeseries:
            return "0%"

        latest = self._timeseries[-1]
        reference_index = 0
        if len(self._timeseries) > 1:
            reference_index = max(
                0, len(self._timeseries) - self._history_limit(days_ago)
            )
        reference_price = self._timeseries[reference_index]
        if reference_price == 0:
            return "0%"
        change = ((latest - reference_price) / reference_price) * 100
        return f"{change:+.1f}%"

    def _format_price_now(self, price: float | None) -> str:
        if price is None:
            return "0"
        return f"{price:,.0f}" if price > 1000 else f"{price:.5g}"

    def _is_cache_fresh(self) -> bool:
        if self._last_refresh is None:
            return False
        return (
            datetime.now(timezone.utc) - self._last_refresh
        ).total_seconds() < self.min_refresh_time

    def _history_since(self, days_ago: int) -> int:
        delta = self._timeframe_delta(self.interval)
        periods = max(2, self._history_limit(days_ago))
        since = datetime.now(timezone.utc) - (delta * periods)
        return int(since.timestamp() * 1000)

    def _history_limit(self, days_ago: int) -> int:
        delta = self._timeframe_delta(self.interval)
        if delta.total_seconds() <= 0:
            return 2
        periods = ceil((max(days_ago, 1) * 86400) / delta.total_seconds()) + 1
        return max(2, periods)

    @staticmethod
    def _compute_sats(price: float | None) -> float | None:
        if price in (None, 0):
            return None
        assert price is not None
        return 100_000_000 / price

    @staticmethod
    def _coerce_timestamp(value: Any) -> datetime | None:
        if value is None:
            return None
        if isinstance(value, datetime):
            return value
        if isinstance(value, (int, float)):
            timestamp = float(value)
            if timestamp > 10_000_000_000:
                timestamp /= 1000
            return datetime.fromtimestamp(timestamp, tz=timezone.utc)
        return None

    @staticmethod
    def _timeframe_delta(interval: str) -> timedelta:
        unit = interval[-1]
        value = int(interval[:-1])
        mapping = {
            "m": timedelta(minutes=value),
            "h": timedelta(hours=value),
            "d": timedelta(days=value),
            "w": timedelta(weeks=value),
        }
        return mapping.get(unit, timedelta(hours=1))

    @staticmethod
    def _normalize_interval(interval: str) -> str:
        normalized = INTERVAL_ALIASES.get(interval, interval)
        if normalized not in INTERVAL_ALIASES.values():
            supported_values = ", ".join(sorted(INTERVAL_ALIASES))
            raise PriceProviderError(
                f"Unsupported interval '{interval}'. "
                f"Supported values: {supported_values}"
            )
        return normalized
