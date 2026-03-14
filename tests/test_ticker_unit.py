import importlib
import sys
import types
from datetime import datetime
from types import SimpleNamespace

import pytest


def _load_ticker_module(monkeypatch):
    fake_price_pkg = types.ModuleType("btcpriceticker")
    fake_price_mod = types.ModuleType("btcpriceticker.price")

    class StubPrice:
        def __init__(self, *args, **kwargs):
            self.days_ago = kwargs.get("days_ago", 1)
            self.min_refresh_time = 0
            self.ohlc = []
            self.price = {"usd": 0.0, "sat_usd": 0.0, "sat_fiat": 0.0}

        def set_days_ago(self, days_ago):
            self.days_ago = days_ago

        def refresh(self):
            return None

        def get_price_now(self):
            return "0"

        def get_price_change(self):
            return "0%"

        def get_timeseries_list(self):
            return [0.0]

    fake_price_mod.Price = StubPrice
    fake_price_pkg.price = fake_price_mod
    monkeypatch.setitem(sys.modules, "btcpriceticker", fake_price_pkg)
    monkeypatch.setitem(sys.modules, "btcpriceticker.price", fake_price_mod)

    fake_piltext = types.ModuleType("piltext")

    class StubFontManager:
        def __init__(self, *args, **kwargs):
            return None

    class StubImageDrawer:
        def __init__(self, *args, **kwargs):
            self.finalize_calls = []
            self.image_handler = SimpleNamespace(image="image")

        def initialize(self):
            return None

        def finalize(self, **kwargs):
            self.finalize_calls.append(kwargs)

        def draw_text(self, text, pos, end=None, font_name=None, anchor="lt"):
            return len(text), 10, 10

        def change_size(self, width, height):
            return None

        def show(self):
            return None

    class StubTextGrid:
        def __init__(self, *args, **kwargs):
            return None

        def merge(self, *args, **kwargs):
            return None

        def set_text(self, *args, **kwargs):
            return None

        def paste_image(self, *args, **kwargs):
            return None

        def get_grid(self, *args, **kwargs):
            return (0, 0), (10, 10)

    fake_piltext.FontManager = StubFontManager
    fake_piltext.ImageDrawer = StubImageDrawer
    fake_piltext.TextGrid = StubTextGrid
    monkeypatch.setitem(sys.modules, "piltext", fake_piltext)

    fake_chart = types.ModuleType("btcticker.chart")
    fake_chart.makeCandle = lambda *args, **kwargs: "candle-image"
    fake_chart.makeSpark = lambda *args, **kwargs: "spark-image"
    monkeypatch.setitem(sys.modules, "btcticker.chart", fake_chart)

    sys.modules.pop("btcticker.ticker", None)
    return importlib.import_module("btcticker.ticker")


@pytest.fixture
def ticker_module(monkeypatch):
    return _load_ticker_module(monkeypatch)


def test_ticker_builds_pyccxt_provider_when_none_injected(ticker_module, monkeypatch):
    calls = {}

    class FakeProvider:
        def __init__(self, **kwargs):
            calls["init"] = kwargs
            self.days_ago = kwargs["days_ago"]
            self.min_refresh_time = kwargs["min_refresh_time"]

        def set_days_ago(self, days_ago):
            calls["set_days_ago"] = days_ago
            self.days_ago = days_ago

        def refresh(self):
            return None

        def get_price_now(self):
            return "0"

        def get_price_change(self):
            return "0%"

        def get_timeseries_list(self):
            return [0.0]

        def get_ohlc_history(self):
            return []

        def get_snapshot(self):
            return None

    monkeypatch.setattr(ticker_module, "PyCCXTPriceProvider", FakeProvider)

    config = SimpleNamespace(
        main=SimpleNamespace(
            fiat="eur",
            symbol="",
            usd_symbol="BTC/USD",
            exchange="kraken",
            interval="1h",
            enable_ohlc=True,
            ccxt_timeout=30000,
            price_refresh_seconds=10,
            mempool_api_url="https://mempool.space/api",
            inverted=False,
            orientation=0,
            price_provider="pyccxt",
        )
    )
    renderer = SimpleNamespace(font_manager="fonts", image="image")

    ticker = ticker_module.Ticker(
        config,
        264,
        176,
        days_ago=3,
        mempool=SimpleNamespace(),
        renderer=renderer,
    )

    assert calls["init"] == {
        "exchange_name": "kraken",
        "fiat_symbol": "BTC/EUR",
        "usd_symbol": "BTC/USD",
        "interval": "1h",
        "days_ago": 3,
        "enable_ohlc": True,
        "timeout_ms": 30000,
        "min_refresh_time": 10,
    }
    assert calls["set_days_ago"] == 3
    assert ticker.price_provider is ticker.price


def _make_ticker(ticker_module, show_best_fees=True, show_block_time=False):
    ticker = ticker_module.Ticker.__new__(ticker_module.Ticker)

    ticker.config = SimpleNamespace(
        main=SimpleNamespace(
            fiat="usd",
            show_best_fees=show_best_fees,
            show_block_time=show_block_time,
        ),
        fonts=SimpleNamespace(
            font_buttom="Roboto-Medium.ttf",
            font_console="ZenDots-Regular.ttf",
            font_big="BigShouldersDisplay-SemiBold.ttf",
            font_side="Roboto-Medium.ttf",
            font_top="PixelSplitter-Bold.ttf",
            font_fee="Audiowide-Regular.ttf",
        ),
    )
    ticker.fiat = "usd"
    ticker.width = 264
    ticker.height = 176
    ticker.orientation = 0
    ticker.inverted = False

    ticker.price = SimpleNamespace(
        price={"usd": 43567.0, "sat_usd": 2295.0, "sat_fiat": 2400.0},
        days_ago=3,
        min_refresh_time=0,
        get_price_now=lambda: "43,567",
        get_price_change=lambda: "+3.2%",
        get_timeseries_list=lambda: [1.0, 2.0, 3.0],
        set_days_ago=lambda days_ago: None,
        refresh=lambda: None,
        ohlc=[],
    )

    mempool_data = {
        "height": 840000,
        "count": 321000,
        "vsize": 2300000,
        "minFee": [1.1, 2.2, 3.3, 4.4, 5.5, 6.6, 7.7],
        "bestFees": {"fastestFee": 3.4, "halfHourFee": 2.3, "hourFee": 1.2},
        "last_block": {"timestamp": 1700000000, "height": 840000},
        "retarget_block": {"timestamp": 1699000000, "height": 838656},
        "minutes_between_blocks": 9.5,
    }
    ticker.mempool = SimpleNamespace(getData=lambda: mempool_data, refresh=lambda: None)

    ticker.image = SimpleNamespace(
        initialize=lambda: None,
        finalize=lambda **kwargs: None,
        change_size=lambda width, height: None,
        show=lambda: None,
        image_handler=SimpleNamespace(image="image"),
    )

    return ticker, mempool_data


def test_generate_line_str_handles_tokens(ticker_module):
    ticker, _ = _make_ticker(ticker_module)
    lines = {
        "fiat": [
            ("t", "height: "),
            ("s", "_current_block_height_"),
            ("n", ""),
            ("t", ""),
            ("t", "ok"),
        ]
    }

    assert ticker.generate_line_str(lines, "fiat") == ["height: 840000", " ok"]


def test_get_current_price_variants(ticker_module):
    ticker, _ = _make_ticker(ticker_module)

    assert ticker.get_current_price("fiat") == "43567"
    assert ticker.get_current_price("fiat", with_symbol=True) == "$43567"
    assert ticker.get_current_price("usd") == "43567"
    assert ticker.get_current_price("usd", with_symbol=True) == "$43567"
    assert (
        ticker.get_current_price("sat_per_fiat", with_symbol=True, shorten=False)
        == "2400 sat/$"
    )
    assert ticker.get_current_price("sat_per_usd", shorten=False) == "2295 sat/$"


@pytest.mark.parametrize(
    ("generator_name", "mode", "expected"),
    [
        (
            "generate_all",
            "fiat",
            [
                "840000 - 9:30 -",
                "low: 1.2 med: 2.3 high: 3.4",
                "$43567",
                "2295 /$",
                "/$2400",
                "$ ",
                "3day : +3.2%",
                "43567",
            ],
        ),
        (
            "generate_all",
            "newblock",
            [
                "$43567 - 9:30 -",
                "low: 1.2 med: 2.3 high: 3.4",
                "3 blks 321000 txs",
                "672 blk -12.5%",
                "840000",
                " ",
                " ",
                " ",
            ],
        ),
        (
            "generate_fiat",
            "height",
            [
                "$43567 -",
                "low: 1.2 med: 2.3 high: 3.4",
                "lb -",
                "672 blk",
                "/$2400",
                " ",
                "3day : +3.2%",
                "840000",
            ],
        ),
        (
            "generate_fiat_height",
            "usd",
            ["840000", "Fees: L 1.2 M 2.3 H 3.4", "672 blk -12.5 %", "/$2400", "43567"],
        ),
        (
            "generate_big_one_row",
            "satfiat",
            ["840000 - 672 -", "/$ Fees: L 1.2 M 2.3 H 3.4", "2400"],
        ),
        ("generate_big_two_rows", "moscowtime", ["sat/$", "$43,567 - 9:30 -", "2295"]),
        ("generate_one_number", "fiat", ["$43567", "Market price of bitcoin"]),
        (
            "generate_mempool",
            "usd",
            ["43567", "672 blk -12.5 %", "$43567 - 840000 - lb -", "1.2 2.3 3.4"],
        ),
        (
            "generate_ohlc",
            "satfiat",
            [
                "840000",
                "(",
                "Fees: L 1.2 M 2.3 H 3.4",
                "672 blk -12.54%",
                "$43567 - $43567 - 2295 /$",
                "/$   3d : +3.2%",
                "2400",
            ],
        ),
    ],
)
def test_layout_generators_cover_mode_matrix(
    ticker_module, generator_name, mode, expected
):
    ticker, _ = _make_ticker(ticker_module)

    actual = getattr(ticker, generator_name)(mode)

    assert len(actual) == len(expected)
    for actual_part, expected_part in zip(actual, expected):
        assert expected_part in actual_part


def test_layout_generators_toggle_block_time_and_fee_modes(ticker_module):
    ticker, _ = _make_ticker(
        ticker_module,
        show_best_fees=False,
        show_block_time=True,
    )

    assert ticker.generate_all("fiat")[0].startswith("840000-")
    assert ticker.generate_all("fiat")[1] == "1.1-2.2-3.3-4.4-5.5-6.6-7.7"
    assert ticker.generate_fiat("fiat")[0].startswith("840000-")
    assert ticker.generate_big_one_row("fiat")[1].endswith(
        "1.1-2.2-3.3-4.4-5.5-6.6-7.7"
    )


def test_fiat_height_uses_usd_specific_variant_when_fiat_is_usd(ticker_module):
    ticker, _ = _make_ticker(ticker_module)

    line_str = ticker.generate_fiat_height("fiat")
    expected_last_block_time = datetime.fromtimestamp(1700000000).strftime("%H:%M")

    assert line_str[0] == "840000"
    assert line_str[1] == "Fees: L 1.2 M 2.3 H 3.4"
    assert line_str[2].startswith(f"672 blk -12.5 % | {expected_last_block_time} -")
    assert line_str[3] == "/$2400"
    assert line_str[4] == "$43567"


def test_layouts_degrade_when_usd_values_are_missing(ticker_module):
    ticker, _ = _make_ticker(ticker_module)
    ticker.price.price["usd"] = None
    ticker.price.price["sat_usd"] = None

    assert ticker.get_current_price("usd") == "n/a"
    assert ticker.get_current_price("sat_per_usd") == "n/a /$"
    assert "n/a" in ticker.generate_all("usd")[7]


def test_generate_all_handles_missing_retarget_block(ticker_module):
    ticker, mempool_data = _make_ticker(ticker_module)
    mempool_data["retarget_block"] = None

    line_str = ticker.generate_all("fiat")

    assert line_str[0].startswith("840000 - 9:30 -")
    assert line_str[6] == "3day : +3.2%"


def test_fee_strings_toggle_best_fee_mode(ticker_module):
    ticker, mempool_data = _make_ticker(ticker_module, show_best_fees=True)

    assert ticker.get_fees_string(mempool_data) == "low: 1.2 med: 2.3 high: 3.4"
    assert ticker.get_fee_string(mempool_data) == "Fees: L 1.2 M 2.3 H 3.4"

    ticker.config.main.show_best_fees = False
    assert ticker.get_fees_string(mempool_data) == "1.1-2.2-3.3-4.4-5.5-6.6-7.7"
    assert ticker.get_fee_string(mempool_data) == "1.1-2.2-3.3-4.4-5.5-6.6-7.7"


def test_get_next_difficulty_string_branches(ticker_module):
    ticker, _ = _make_ticker(ticker_module)
    ticker.get_last_block_time = lambda date_and_time=False: "12:00"

    with_clock = ticker.get_next_difficulty_string(
        10,
        1.05,
        615,
        None,
        show_clock=True,
        last_block_sec_ago=360,
    )
    with_date = ticker.get_next_difficulty_string(
        10,
        1.05,
        615,
        None,
        retarget_date=datetime(2024, 1, 1, 12, 30),
        show_clock=False,
    )
    plain = ticker.get_next_difficulty_string(
        10,
        1.05,
        615,
        None,
        show_clock=False,
    )

    assert with_clock == "10 blk 5.0 % | 12:00 -6 min"
    assert with_date == "10 blk 5.00% 01.Jan 12:30"
    assert plain == "10 blk 5 % 10:15"


def test_scale_helpers_clamp_to_bounds(ticker_module):
    ticker, _ = _make_ticker(ticker_module)

    assert ticker.get_w_factor(-1) == 0
    assert ticker.get_h_factor(-1) == 0
    assert ticker.get_w_factor(999) == ticker.width
    assert ticker.get_h_factor(999) == ticker.height


def test_build_dispatches_layout_and_finalizes_image(ticker_module):
    ticker, mempool_data = _make_ticker(ticker_module)
    calls = {}

    ticker.initialize = lambda: calls.setdefault("initialize", True)
    ticker.draw_ohlc = lambda mode: calls.setdefault("draw", ("ohlc", mode))
    ticker.draw_fiat = lambda mode: calls.setdefault("draw", ("fiat", mode))
    ticker.draw_all = lambda mode: calls.setdefault("draw", ("all", mode))
    ticker.draw_fiat_height = lambda mode: calls.setdefault(
        "draw", ("fiatheight", mode)
    )
    ticker.draw_big_one_row = lambda mode: calls.setdefault(
        "draw", ("big_one_row", mode)
    )
    ticker.draw_one_number = lambda mode: calls.setdefault("draw", ("one_number", mode))
    ticker.draw_mempool = lambda mode: calls.setdefault("draw", ("mempool", mode))
    ticker.image = SimpleNamespace(
        finalize=lambda **kwargs: calls.setdefault("finalize", kwargs),
        initialize=lambda: None,
    )

    ticker.build(mode="fiat", layout="ohlc", mirror=False)

    assert calls["initialize"] is True
    assert calls["draw"] == ("ohlc", "fiat")
    assert calls["finalize"] == {"mirror": False, "orientation": 0, "inverted": False}

    mempool_data["height"] = -1
    calls.clear()
    ticker.build(mode="fiat", layout="ohlc", mirror=False)
    assert calls == {}


def test_initialize_sets_default_text_ink_when_available(ticker_module):
    ticker, _ = _make_ticker(ticker_module)
    draw = SimpleNamespace(ink=-1)
    calls = {}
    ticker.image = SimpleNamespace(
        initialize=lambda: calls.setdefault("initialize", True),
        draw=draw,
    )

    ticker.initialize()

    assert calls["initialize"] is True
    assert draw.ink == 0


def test_initialize_handles_missing_draw_context(ticker_module):
    ticker, _ = _make_ticker(ticker_module)
    calls = {}
    ticker.image = SimpleNamespace(
        initialize=lambda: calls.setdefault("initialize", True),
    )

    ticker.initialize()

    assert calls["initialize"] is True
