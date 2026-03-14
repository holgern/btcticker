import math
import sys
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from babel import numbers

from btcticker.domain.market_snapshot import MarketSnapshot

DATACLASS_KWARGS = {"slots": True} if sys.version_info >= (3, 10) else {}


@dataclass(**DATACLASS_KWARGS)
class MempoolMetrics:
    current_height: int
    last_height: int
    last_block_time: datetime
    last_block_seconds_ago: int
    minutes_between_blocks: float
    mean_time_diff: float
    remaining_blocks: int
    retarget_multiplier: float
    retarget_date: datetime | None
    mempool_blocks: int
    mempool_count: int


def currency_symbol(fiat: str) -> str:
    try:
        return numbers.get_currency_symbol(fiat.upper(), locale="en")
    except Exception:
        return fiat.upper()


def compute_mempool_metrics(snapshot: MarketSnapshot) -> MempoolMetrics:
    mempool = snapshot.mempool
    now = snapshot.current_time
    last_block = mempool.get("last_block") or {}
    last_timestamp = last_block.get("timestamp") or 0
    last_height = int(last_block.get("height") or mempool.get("height") or 0)
    last_block_time = datetime.fromtimestamp(last_timestamp) if last_timestamp else now
    last_block_seconds_ago = max(int((now - last_block_time).total_seconds()), 0)
    minutes_between_blocks = float(mempool.get("minutes_between_blocks") or 0)
    mean_time_diff = minutes_between_blocks * 60

    remaining_blocks = 0
    retarget_multiplier = 1.0
    retarget_date = None
    retarget_block = mempool.get("retarget_block")
    if retarget_block is not None:
        retarget_height = int(retarget_block.get("height") or 0)
        remaining_blocks = max(2016 - (last_height - retarget_height), 0)
        last_retarget_timestamp = retarget_block.get("timestamp") or 0
        difficulty_epoch_duration = minutes_between_blocks * 60 * remaining_blocks + (
            last_timestamp - last_retarget_timestamp
        )
        if difficulty_epoch_duration > 0:
            retarget_multiplier = 14 * 24 * 60 * 60 / difficulty_epoch_duration
            retarget_timestamp = difficulty_epoch_duration + last_retarget_timestamp
            retarget_date = datetime.fromtimestamp(retarget_timestamp)

    return MempoolMetrics(
        current_height=int(mempool.get("height") or 0),
        last_height=last_height,
        last_block_time=last_block_time,
        last_block_seconds_ago=last_block_seconds_ago,
        minutes_between_blocks=minutes_between_blocks,
        mean_time_diff=mean_time_diff,
        remaining_blocks=remaining_blocks,
        retarget_multiplier=retarget_multiplier,
        retarget_date=retarget_date,
        mempool_blocks=math.ceil(float(mempool.get("vsize") or 0) / 1e6),
        mempool_count=int(mempool.get("count") or 0),
    )


def format_fee_range(min_fee: list[float]) -> str:
    padded = list(min_fee) + [0.0] * max(0, 7 - len(min_fee))
    return "{:.1f}-{:.1f}-{:.1f}-{:.1f}-{:.1f}-{:.1f}-{:.1f}".format(*tuple(padded[:7]))


def format_best_fee(best_fees: dict[str, float], template: str) -> str:
    return template % (
        float(best_fees.get("hourFee", 0.0)),
        float(best_fees.get("halfHourFee", 0.0)),
        float(best_fees.get("fastestFee", 0.0)),
    )


def get_fees_string(snapshot: MarketSnapshot, show_best_fees: bool) -> str:
    mempool = snapshot.mempool
    if show_best_fees:
        return format_best_fee(
            mempool.get("bestFees", {}),
            "low: %.1f med: %.1f high: %.1f",
        )
    return format_fee_range(mempool.get("minFee", []))


def get_fee_string(snapshot: MarketSnapshot, show_best_fees: bool) -> str:
    mempool = snapshot.mempool
    if show_best_fees:
        return format_best_fee(
            mempool.get("bestFees", {}),
            "Fees: L %.1f M %.1f H %.1f",
        )
    return format_fee_range(mempool.get("minFee", []))


def get_fee_short_string(
    symbol: str,
    snapshot: MarketSnapshot,
    metrics: MempoolMetrics,
) -> str:
    best_fees = snapshot.mempool.get("bestFees", {})
    hour_fee = float(best_fees.get("hourFee", 0.0))
    half_hour_fee = float(best_fees.get("halfHourFee", 0.0))
    fastest_fee = float(best_fees.get("fastestFee", 0.0))

    if len(symbol) > 0 and half_hour_fee > 10:
        return (
            f"{symbol} - lb -{int(metrics.last_block_seconds_ago / 60)}:"
            f"{metrics.last_block_seconds_ago % 60} - l {hour_fee:.0f} "
            f"m {half_hour_fee:.0f} h {fastest_fee:.0f}"
        )
    if len(symbol) > 0 and half_hour_fee < 10:
        return (
            f"{symbol} - lb -{int(metrics.last_block_seconds_ago / 60)}:"
            f"{metrics.last_block_seconds_ago % 60} - l {hour_fee:.1f} "
            f"m {half_hour_fee:.1f} h {fastest_fee:.1f}"
        )
    if half_hour_fee < 10:
        return (
            f"lb -{int(metrics.last_block_seconds_ago / 60)}:"
            f"{metrics.last_block_seconds_ago % 60} - l {hour_fee:.1f} "
            f"m  {half_hour_fee:.1f} h {fastest_fee:.1f}"
        )
    return (
        f"lb -{int(metrics.last_block_seconds_ago / 60)}:"
        f"{metrics.last_block_seconds_ago % 60} - l {hour_fee:.0f} "
        f"m  {half_hour_fee:.0f} h {fastest_fee:.0f}"
    )


def get_next_difficulty_string(
    metrics: MempoolMetrics,
    *,
    show_clock: bool = True,
    retarget_date: datetime | None = None,
) -> str:
    t_min = metrics.mean_time_diff // 60
    t_sec = metrics.mean_time_diff % 60
    if show_clock:
        return (
            f"{metrics.remaining_blocks} blk "
            f"{(metrics.retarget_multiplier * 100 - 100):.1f} % | "
            f"{get_last_block_time_from_metrics(metrics, date_and_time=False)} "
            f"-{int(metrics.last_block_seconds_ago / 60)} min"
        )
    if retarget_date is not None:
        return (
            f"{metrics.remaining_blocks} blk "
            f"{(metrics.retarget_multiplier * 100 - 100):.2f}% "
            f"{retarget_date.strftime('%d.%b %H:%M')}"
        )
    return (
        f"{metrics.remaining_blocks} blk "
        f"{(metrics.retarget_multiplier * 100 - 100):.0f} % "
        f"{int(t_min)}:{int(t_sec)}"
    )


def get_symbol(snapshot: MarketSnapshot) -> str:
    return currency_symbol(snapshot.price_snapshot.fiat)


def get_current_block_height(metrics: MempoolMetrics) -> str:
    return str(metrics.current_height)


def get_sat_per_fiat(snapshot: MarketSnapshot) -> float | None:
    return snapshot.price_snapshot.sat_per_fiat


def get_remaining_blocks(metrics: MempoolMetrics) -> int:
    return metrics.remaining_blocks


def get_minutes_between_blocks(metrics: MempoolMetrics) -> str:
    t_min = metrics.mean_time_diff // 60
    t_sec = metrics.mean_time_diff % 60
    return f"{int(t_min)}:{int(t_sec)}"


def get_last_block_time_from_metrics(
    metrics: MempoolMetrics,
    *,
    date_and_time: bool = True,
) -> str:
    if date_and_time:
        return str(metrics.last_block_time.strftime("%d.%b %H:%M"))
    return str(metrics.last_block_time.strftime("%H:%M"))


def get_last_block_time2(metrics: MempoolMetrics) -> str:
    return (
        f"{int(metrics.last_block_seconds_ago / 60)}:"
        f"{metrics.last_block_seconds_ago % 60} min"
    )


def get_current_time(snapshot: MarketSnapshot) -> str:
    return snapshot.current_time.strftime("%H:%M")


def get_last_block_time3(metrics: MempoolMetrics) -> str:
    return (
        f"{get_last_block_time_from_metrics(metrics)} "
        f"({int(metrics.last_block_seconds_ago / 60)}:"
        f"{metrics.last_block_seconds_ago % 60} min ago)"
    )


def _format_whole_number(value: float | None, placeholder: str = "n/a") -> str:
    if value is None:
        return placeholder
    return format(int(value), "")


def get_current_price(
    snapshot: MarketSnapshot,
    kind: str,
    *,
    with_symbol: bool = False,
    shorten: bool = True,
) -> str:
    price_snapshot = snapshot.price_snapshot
    symbol_string = get_symbol(snapshot)

    if kind == "fiat":
        price_str = snapshot.price_now.replace(",", "") if snapshot.price_now else "n/a"
        if with_symbol:
            price_str = symbol_string + price_str
        return price_str
    if kind == "usd":
        price_str = _format_whole_number(price_snapshot.usd_price)
        if with_symbol:
            return "$" + price_str
        return price_str
    if kind == "moscow_time_usd":
        return _format_whole_number(price_snapshot.sat_per_usd)
    if kind == "sat_per_fiat":
        sat_per_fiat = _format_whole_number(price_snapshot.sat_per_fiat)
        if with_symbol and shorten:
            return f"/{symbol_string}{sat_per_fiat}"
        if with_symbol and not shorten:
            return f"{sat_per_fiat} sat/{symbol_string}"
        return sat_per_fiat
    if kind == "sat_per_usd":
        sat_per_usd = _format_whole_number(price_snapshot.sat_per_usd)
        if shorten:
            return f"{sat_per_usd} /$"
        return f"{sat_per_usd} sat/$"
    return "n/a"


def price_change_string(snapshot: MarketSnapshot, prefix_symbol: str | bool) -> str:
    if prefix_symbol:
        return f"{prefix_symbol}   {snapshot.days_ago}d : {snapshot.price_change}"
    return f"{snapshot.days_ago}day : {snapshot.price_change}"


def get_line_token_value(
    token: str,
    snapshot: MarketSnapshot,
    metrics: MempoolMetrics,
) -> str:
    if token == "empty":
        return ""
    if token == "_current_block_height_":
        return get_current_block_height(metrics)
    if token == "_sat_per_fiat_with_symbol_":
        return get_current_price(snapshot, "sat_per_fiat", with_symbol=True)
    if token == "_moscow_time_usd_":
        return get_current_price(snapshot, "moscow_time_usd")
    if token == "_current_price_usd_":
        return get_current_price(snapshot, "usd")
    if token == "_current_price_fiat_symbol_":
        return get_current_price(snapshot, "fiat", with_symbol=True)
    if token == "_minutes_between_blocks_":
        return get_minutes_between_blocks(metrics)
    if token == "_current_time_":
        return get_current_time(snapshot)
    if token == "_current_price_fiat_symbol_left_part_":
        price_parts = (snapshot.price_now or "n/a").split(",")
        return get_symbol(snapshot) + price_parts[0]
    if token == "_current_price_fiat_symbol_right_part_":
        price_parts = (snapshot.price_now or "n/a").split(",")
        return price_parts[1] if len(price_parts) > 1 else ""
    return token


def generate_line_str(
    lines: dict[str, list[tuple[str, str]]],
    mode: str,
    snapshot: MarketSnapshot,
    metrics: MempoolMetrics,
) -> list[str]:
    line_str = []
    line = ""
    for sym, value in lines[mode]:
        if sym == "n":
            line_str.append(line)
            line = ""
        elif sym == "t":
            line += value if value != "" else " "
        elif sym == "s":
            line += get_line_token_value(value, snapshot, metrics)
    if line != "":
        line_str.append(line)
    return line_str


def usd_value(snapshot: MarketSnapshot) -> str:
    return _format_whole_number(snapshot.price_snapshot.usd_price)


def sat_per_usd_value(snapshot: MarketSnapshot) -> str:
    return _format_whole_number(snapshot.price_snapshot.sat_per_usd)


def sat_per_fiat_value(snapshot: MarketSnapshot) -> str:
    return _format_whole_number(snapshot.price_snapshot.sat_per_fiat)


def ohlc_history(snapshot: MarketSnapshot) -> Any:
    return snapshot.ohlc_history
