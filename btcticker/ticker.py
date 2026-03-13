import math
import time
from datetime import datetime

from btcticker.domain.market_snapshot import MarketSnapshot
from btcticker.domain.price_snapshot import PriceSnapshot
from btcticker.layouts import (
    generate_all as build_all_layout,
    generate_big_one_row as build_big_one_row_layout,
    generate_big_two_rows as build_big_two_rows_layout,
    generate_fiat as build_fiat_layout,
    generate_fiat_height as build_fiat_height_layout,
    generate_mempool as build_mempool_layout,
    generate_ohlc as build_ohlc_layout,
    generate_one_number as build_one_number_layout,
)
from btcticker.layouts.common import (
    compute_mempool_metrics,
    generate_line_str as build_token_lines,
    get_current_block_height as current_block_height,
    get_current_price as format_current_price,
    get_fee_short_string as format_fee_short_string,
    get_fee_string as format_fee_string,
    get_fees_string as format_fees_string,
    get_last_block_time2 as format_last_block_age,
    get_last_block_time3 as format_last_block_time_ago,
    get_last_block_time_from_metrics,
    get_line_token_value,
    get_minutes_between_blocks as format_minutes_between_blocks,
    get_next_difficulty_string as format_next_difficulty,
    get_remaining_blocks as remaining_blocks_value,
    get_sat_per_fiat as sat_per_fiat_value,
    get_symbol as format_symbol,
    price_change_string as format_price_change_string,
)
from btcticker.mempool import Mempool
from btcticker.providers import PyCCXTPriceProvider
from btcticker.render import ImageRenderer


class Ticker:
    def __init__(
        self,
        config,
        width,
        height,
        days_ago=1,
        mempool=None,
        price=None,
        price_provider=None,
        font_manager=None,
        image=None,
        renderer=None,
    ):
        provider = self._resolve_price_provider(
            config=config,
            days_ago=days_ago,
            price_provider=price_provider,
            price=price,
        )

        self.config = config
        self.height = height
        self.width = width
        self.fiat = config.main.fiat
        self.mempool = mempool or Mempool(api_url=config.main.mempool_api_url)
        self.price_provider = provider
        self.price = provider

        self.renderer = renderer or ImageRenderer(
            config,
            width,
            height,
            font_manager=font_manager,
            image=image,
        )
        self.font_manager = self.renderer.font_manager
        self.image = self.renderer.image
        self.inverted = config.main.inverted
        self.orientation = config.main.orientation
        self.set_days_ago(days_ago)

    @staticmethod
    def _derive_symbol(config):
        return config.main.symbol or f"BTC/{config.main.fiat.upper()}"

    @classmethod
    def _build_default_price_provider(cls, config, days_ago, provider_name=None):
        resolved_provider = provider_name or getattr(
            config.main, "price_provider", "pyccxt"
        )
        resolved_provider = str(resolved_provider).strip().lower()
        if resolved_provider != "pyccxt":
            raise ValueError(
                f"Unknown price provider '{resolved_provider}'. Available providers: pyccxt"
            )

        return PyCCXTPriceProvider(
            exchange_name=config.main.exchange,
            fiat_symbol=cls._derive_symbol(config),
            usd_symbol=config.main.usd_symbol or "BTC/USD",
            interval=config.main.interval,
            days_ago=days_ago,
            enable_ohlc=config.main.enable_ohlc,
            timeout_ms=config.main.ccxt_timeout,
            min_refresh_time=config.main.price_refresh_seconds,
        )

    @classmethod
    def _resolve_price_provider(cls, config, days_ago, price_provider=None, price=None):
        if price_provider is not None and not isinstance(price_provider, str):
            return price_provider
        if price is not None:
            return price
        return cls._build_default_price_provider(config, days_ago, price_provider)

    def _provider(self):
        provider = getattr(self, "price_provider", None) or getattr(self, "price", None)
        if provider is None:
            raise ValueError("Ticker has no price provider")
        return provider

    def _build_market_snapshot(self) -> MarketSnapshot:
        provider = self._provider()
        if hasattr(provider, "get_snapshot"):
            price_snapshot = provider.get_snapshot()
            price_now = provider.get_price_now()
            price_change = provider.get_price_change()
            timeseries = provider.get_timeseries_list()
            ohlc_history = provider.get_ohlc_history()
        else:
            current_price = getattr(provider, "price", {}) or {}
            price_snapshot = PriceSnapshot(
                fiat=self.fiat,
                fiat_price=self._coerce_float(current_price.get("fiat")),
                usd_price=self._coerce_float(current_price.get("usd")),
                sat_per_fiat=self._coerce_float(current_price.get("sat_fiat")),
                sat_per_usd=self._coerce_float(current_price.get("sat_usd")),
                timestamp=None,
            )
            price_now = provider.get_price_now()
            price_change = provider.get_price_change()
            timeseries = list(provider.get_timeseries_list())
            ohlc_history = getattr(provider, "ohlc", [])

        return MarketSnapshot(
            price_snapshot=price_snapshot,
            mempool=self.mempool.getData(),
            price_now=price_now,
            price_change=price_change,
            days_ago=getattr(provider, "days_ago", 1),
            timeseries=timeseries,
            ohlc_history=ohlc_history,
            current_time=datetime.now(),
        )

    @staticmethod
    def _coerce_float(value):
        if value is None:
            return None
        try:
            return float(value)
        except (TypeError, ValueError):
            return None

    def _format_fee_range(self, min_fee):
        from btcticker.layouts.common import format_fee_range

        return format_fee_range(min_fee)

    def _format_best_fee(self, best_fees, template):
        from btcticker.layouts.common import format_best_fee

        return format_best_fee(best_fees, template)

    def get_line_str(self, sym):
        snapshot = self._build_market_snapshot()
        metrics = compute_mempool_metrics(snapshot)
        return get_line_token_value(sym, snapshot, metrics)

    def generate_line_str(self, lines, mode):
        snapshot = self._build_market_snapshot()
        metrics = compute_mempool_metrics(snapshot)
        return build_token_lines(lines, mode, snapshot, metrics)

    def set_days_ago(self, days_ago):
        provider = self._provider()
        provider.set_days_ago(days_ago)

    def change_size(self, width, height):
        self.height = height
        self.width = width
        self.renderer.change_size(width, height)
        self.image = self.renderer.image

    def set_min_refresh_time(self, min_refresh_time):
        provider = self._provider()
        if hasattr(provider, "set_min_refresh_time"):
            provider.set_min_refresh_time(min_refresh_time)
        else:
            provider.min_refresh_time = min_refresh_time
        self.mempool.min_refresh_time = min_refresh_time

    def refresh(self):
        self.mempool.refresh()
        self._provider().refresh()

    def get_w_factor(self, w, factor=264):
        if w < 0:
            w = 0
        if w > factor:
            w = factor
        return int(w / factor * self.width)

    def get_h_factor(self, h, factor=176):
        if h < 0:
            h = 0
        if h > factor:
            h = factor
        return int(h / factor * self.height)

    def get_next_difficulty_string(
        self,
        remaining_blocks,
        retarget_mult,
        meanTimeDiff,
        time,
        retarget_date=None,
        show_clock=True,
        last_block_time=None,
        last_block_sec_ago=None,
    ):
        t_min = meanTimeDiff // 60
        t_sec = meanTimeDiff % 60
        if last_block_sec_ago is None:
            last_block_sec_ago = 0

        if show_clock:
            return "%d blk %.1f %% | %s -%d min" % (
                remaining_blocks,
                (retarget_mult * 100 - 100),
                self.get_last_block_time(date_and_time=False),
                int(last_block_sec_ago / 60),
            )
        if retarget_date is not None:
            return "%d blk %.2f%% %s" % (
                remaining_blocks,
                (retarget_mult * 100 - 100),
                retarget_date.strftime("%d.%b %H:%M"),
            )
        return "%d blk %.0f %% %d:%d" % (
            remaining_blocks,
            (retarget_mult * 100 - 100),
            t_min,
            t_sec,
        )

    def get_fees_string(self, mempool):
        snapshot = self._build_market_snapshot()
        snapshot.mempool = mempool
        return format_fees_string(snapshot, self.config.main.show_best_fees)

    def get_fee_string(self, mempool):
        snapshot = self._build_market_snapshot()
        snapshot.mempool = mempool
        return format_fee_string(snapshot, self.config.main.show_best_fees)

    def get_fee_short_string(self, symbol, mempool, last_block_sec_ago):
        snapshot = self._build_market_snapshot()
        snapshot.mempool = mempool
        metrics = compute_mempool_metrics(snapshot)
        metrics.last_block_seconds_ago = last_block_sec_ago
        return format_fee_short_string(symbol, snapshot, metrics)

    def build_message(self, message, mirror=True):
        if not isinstance(message, str):
            return
        self.initialize()
        self.renderer.draw_message(message)
        self.renderer.finalize(mirror=mirror)

    def initialize(self):
        if hasattr(self, "renderer") and self.renderer is not None:
            self.renderer.initialize()
            self.image = self.renderer.image
            return
        self.image.initialize()
        draw = getattr(self.image, "draw", None)
        if draw is not None and hasattr(draw, "ink"):
            draw.ink = 0

    def build(self, mode="fiat", layout="all", mirror=True):
        mempool = self.mempool.getData()
        if mempool["height"] < 0:
            return

        self.initialize()
        if layout == "big_two_rows":
            self.draw_big_two_rows(mode)
        elif layout == "big_one_row":
            self.draw_big_one_row(mode)
        elif layout == "one_number":
            self.draw_one_number(mode)
        elif layout == "fiat" or (layout == "all" and self.config.main.fiat == "usd"):
            self.draw_fiat(mode)
        elif layout == "fiatheight":
            self.draw_fiat_height(mode)
        elif layout == "ohlc":
            self.draw_ohlc(mode)
        elif layout == "mempool":
            self.draw_mempool(mode)
        else:
            self.draw_all(mode)

        if hasattr(self, "renderer") and self.renderer is not None:
            self.renderer.finalize(
                mirror=mirror,
                orientation=self.orientation,
                inverted=self.inverted,
            )
        else:
            self.image.finalize(
                mirror=mirror,
                orientation=self.orientation,
                inverted=self.inverted,
            )

    def show(self):
        if hasattr(self, "renderer") and self.renderer is not None:
            self.renderer.show()
        else:
            self.image.show()

    def get_current_price(self, symbol, with_symbol=False, shorten=True):
        return format_current_price(
            self._build_market_snapshot(),
            symbol,
            with_symbol=with_symbol,
            shorten=shorten,
        )

    def price_change_string(self, prefix_symbol):
        return format_price_change_string(self._build_market_snapshot(), prefix_symbol)

    def get_symbol(self):
        return format_symbol(self._build_market_snapshot())

    def get_current_block_height(self):
        return current_block_height(
            compute_mempool_metrics(self._build_market_snapshot())
        )

    def get_sat_per_fiat(self):
        return sat_per_fiat_value(self._build_market_snapshot())

    def get_remaining_blocks(self):
        return remaining_blocks_value(
            compute_mempool_metrics(self._build_market_snapshot())
        )

    def get_minutes_between_blocks(self):
        return format_minutes_between_blocks(
            compute_mempool_metrics(self._build_market_snapshot())
        )

    def get_last_block_time(self, date_and_time=True):
        return get_last_block_time_from_metrics(
            compute_mempool_metrics(self._build_market_snapshot()),
            date_and_time=date_and_time,
        )

    def get_last_block_time2(self):
        return format_last_block_age(
            compute_mempool_metrics(self._build_market_snapshot())
        )

    def get_current_time(self):
        return str(time.strftime("%H:%M"))

    def get_last_block_time3(self):
        return format_last_block_time_ago(
            compute_mempool_metrics(self._build_market_snapshot())
        )

    def generate_ohlc(self, mode):
        return build_ohlc_layout(self._build_market_snapshot(), self.config.main, mode)

    def draw_ohlc(self, mode):
        line_str = self.generate_ohlc(mode)
        self.renderer.draw_ohlc(line_str, self._build_market_snapshot().ohlc_history)

    def generate_all(self, mode):
        return build_all_layout(self._build_market_snapshot(), self.config.main, mode)

    def draw_all(self, mode):
        snapshot = self._build_market_snapshot()
        self.renderer.draw_all(self.generate_all(mode), snapshot.timeseries, mode)

    def generate_fiat(self, mode):
        return build_fiat_layout(self._build_market_snapshot(), self.config.main, mode)

    def draw_fiat(self, mode):
        snapshot = self._build_market_snapshot()
        self.renderer.draw_fiat(self.generate_fiat(mode), snapshot.timeseries, mode)

    def generate_fiat_height(self, mode):
        return build_fiat_height_layout(
            self._build_market_snapshot(), self.config.main, mode
        )

    def draw_fiat_height(self, mode):
        self.renderer.draw_fiat_height(self.generate_fiat_height(mode))

    def generate_mempool(self, mode):
        return build_mempool_layout(
            self._build_market_snapshot(), self.config.main, mode
        )

    def draw_mempool(self, mode):
        self.renderer.draw_mempool(self.generate_mempool(mode))

    def generate_big_two_rows(self, mode):
        return build_big_two_rows_layout(
            self._build_market_snapshot(), self.config.main, mode
        )

    def draw_big_two_rows(self, mode):
        self.renderer.draw_big_two_rows(self.generate_big_two_rows(mode))

    def generate_one_number(self, mode):
        return build_one_number_layout(
            self._build_market_snapshot(), self.config.main, mode
        )

    def draw_one_number(self, mode):
        self.renderer.draw_one_number(self.generate_one_number(mode))

    def generate_big_one_row(self, mode):
        return build_big_one_row_layout(
            self._build_market_snapshot(), self.config.main, mode
        )

    def draw_big_one_row(self, mode):
        self.renderer.draw_big_one_row(self.generate_big_one_row(mode))

    def get_image(self):
        if hasattr(self, "renderer") and self.renderer is not None:
            return self.renderer.get_image()
        return self.image.image_handler.image
