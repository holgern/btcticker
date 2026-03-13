from datetime import datetime, timezone
from types import SimpleNamespace

import pytest

from btcticker.providers import (
    BTCPriceTickerProvider,
    PriceHistoryUnavailableError,
    PriceMarketNotFoundError,
    PyCCXTPriceProvider,
)


class FakeLegacyPrice:
    def __init__(self, **kwargs):
        self.kwargs = kwargs
        self.days_ago = kwargs["days_ago"]
        self.min_refresh_time = 120
        self.price = {
            "fiat": 43000.0,
            "usd": 44000.0,
            "sat_fiat": 2325.0,
            "sat_usd": 2272.0,
        }
        self.ohlc = [{"Close": 43000.0}]

    def set_days_ago(self, days_ago):
        self.days_ago = days_ago

    def refresh(self):
        return None

    def get_price_now(self):
        return "43,000"

    def get_price_change(self):
        return "+2.5%"

    def get_timeseries_list(self):
        return [42000.0, 43000.0]

    def get_timestamp(self):
        return 1700000000


def test_btcpriceticker_provider_exposes_normalized_snapshot(monkeypatch):
    monkeypatch.setattr(
        "btcticker.providers.btcpriceticker_provider.Price",
        FakeLegacyPrice,
    )

    provider = BTCPriceTickerProvider(
        fiat="eur",
        service="coingecko",
        interval="1h",
        days_ago=3,
        enable_ohlc=True,
    )

    snapshot = provider.get_snapshot()

    assert snapshot.fiat == ""
    assert snapshot.fiat_price == 43000.0
    assert snapshot.usd_price == 44000.0
    assert snapshot.sat_per_fiat == 2325.0
    assert snapshot.sat_per_usd == 2272.0
    assert provider.get_price_now() == "43,000"
    assert provider.get_price_change() == "+2.5%"
    assert provider.get_timeseries_list() == [42000.0, 43000.0]
    assert provider.get_ohlc_history() == [{"Close": 43000.0}]
    provider.set_days_ago(5)
    assert provider.days_ago == 5


class FakeTicker:
    def __init__(self, last, timestamp=1700000000000):
        self.last = last
        self.timestamp = timestamp


class FakeMarket:
    def __init__(
        self,
        symbol,
        last_price,
        *,
        fetch_ohlc_result=True,
        history_rows=None,
        ohlc_rows=None,
    ):
        self.symbol = symbol
        self.ticker = FakeTicker(last_price)
        self.fetch_calls = []
        self.fetch_ohlc_result = fetch_ohlc_result
        self.history_rows = history_rows or [
            {"timestamp": datetime(2024, 1, 1, tzinfo=timezone.utc), "price": 42000.0},
            {"timestamp": datetime(2024, 1, 2, tzinfo=timezone.utc), "price": 43000.0},
        ]
        self.ohlc_rows = ohlc_rows or [
            {
                "Open": 42000.0,
                "High": 43100.0,
                "Low": 41900.0,
                "Close": 43000.0,
                "Volume": 10.0,
                "Timestamp": datetime(2024, 1, 2, tzinfo=timezone.utc),
            }
        ]
        self.min_refresh_time = 0

    def get_ticker(self):
        return self.ticker

    def fetch_ohlc(self, timeframe="1h", since=None, limit=None):
        self.fetch_calls.append(
            {"timeframe": timeframe, "since": since, "limit": limit}
        )
        return self.fetch_ohlc_result

    def get_price_history(self):
        return list(self.history_rows)

    def get_ohlc_history(self):
        return list(self.ohlc_rows)


class FakeExchange:
    def __init__(self, exchange_name, timeout, min_refresh_time):
        self.exchange_name = exchange_name
        self.timeout = timeout
        self.min_refresh_time = min_refresh_time
        self.ccxt_exchange = SimpleNamespace(has={"fetchOHLCV": True})
        self._markets = {
            "BTC/EUR": FakeMarket("BTC/EUR", 43000.0),
            "BTC/USD": FakeMarket("BTC/USD", 44000.0),
        }

    def get_market(self, symbol):
        return self._markets.get(symbol)


def test_pyccxt_provider_refreshes_snapshot_and_reuses_exchange(monkeypatch):
    monkeypatch.setattr(
        "btcticker.providers.pyccxt_provider.Exchange",
        FakeExchange,
    )
    PyCCXTPriceProvider._exchange_cache.clear()

    provider = PyCCXTPriceProvider(
        exchange_name="kraken",
        fiat_symbol="BTC/EUR",
        usd_symbol="BTC/USD",
        interval="1h",
        days_ago=1,
        enable_ohlc=True,
    )
    provider.refresh()

    snapshot = provider.get_snapshot()
    assert snapshot.fiat == "eur"
    assert snapshot.fiat_price == 43000.0
    assert snapshot.usd_price == 44000.0
    assert round(snapshot.sat_per_fiat, 2) == round(100_000_000 / 43000.0, 2)
    assert round(snapshot.sat_per_usd, 2) == round(100_000_000 / 44000.0, 2)
    assert provider.get_price_now() == "43,000"
    assert provider.get_price_change() == "+2.4%"
    assert provider.get_timeseries_list() == [42000.0, 43000.0]
    assert provider.get_ohlc_history()[0]["Close"] == 43000.0

    provider2 = PyCCXTPriceProvider(
        exchange_name="kraken",
        fiat_symbol="BTC/EUR",
        usd_symbol="BTC/USD",
        interval="1h",
        days_ago=1,
        enable_ohlc=False,
    )
    assert provider._exchange is provider2._exchange


def test_pyccxt_provider_degrades_when_usd_market_missing(monkeypatch):
    class MissingUsdExchange(FakeExchange):
        def __init__(self, exchange_name, timeout, min_refresh_time):
            super().__init__(exchange_name, timeout, min_refresh_time)
            self._markets.pop("BTC/USD")

    monkeypatch.setattr(
        "btcticker.providers.pyccxt_provider.Exchange",
        MissingUsdExchange,
    )
    PyCCXTPriceProvider._exchange_cache.clear()

    provider = PyCCXTPriceProvider(
        exchange_name="kraken",
        fiat_symbol="BTC/EUR",
        usd_symbol="BTC/USD",
        interval="1h",
        days_ago=1,
        enable_ohlc=False,
    )
    provider.refresh()

    snapshot = provider.get_snapshot()
    assert snapshot.fiat_price == 43000.0
    assert snapshot.usd_price is None
    assert snapshot.sat_per_usd is None


def test_pyccxt_provider_raises_for_missing_primary_market(monkeypatch):
    monkeypatch.setattr(
        "btcticker.providers.pyccxt_provider.Exchange",
        FakeExchange,
    )
    PyCCXTPriceProvider._exchange_cache.clear()

    with pytest.raises(PriceMarketNotFoundError):
        PyCCXTPriceProvider(
            exchange_name="kraken",
            fiat_symbol="BTC/CHF",
            usd_symbol="BTC/USD",
            interval="1h",
            days_ago=1,
            enable_ohlc=False,
        )


def test_pyccxt_provider_raises_when_history_unavailable(monkeypatch):
    class NoHistoryExchange(FakeExchange):
        def __init__(self, exchange_name, timeout, min_refresh_time):
            super().__init__(exchange_name, timeout, min_refresh_time)
            self._markets["BTC/EUR"] = FakeMarket(
                "BTC/EUR",
                43000.0,
                fetch_ohlc_result=False,
            )

    monkeypatch.setattr(
        "btcticker.providers.pyccxt_provider.Exchange",
        NoHistoryExchange,
    )
    PyCCXTPriceProvider._exchange_cache.clear()

    provider = PyCCXTPriceProvider(
        exchange_name="kraken",
        fiat_symbol="BTC/EUR",
        usd_symbol="BTC/USD",
        interval="1h",
        days_ago=1,
        enable_ohlc=True,
    )

    with pytest.raises(PriceHistoryUnavailableError):
        provider.refresh()
