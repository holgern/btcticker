from __future__ import annotations

from btcticker.domain.market_snapshot import MarketSnapshot
from btcticker.layouts.common import (
    compute_mempool_metrics,
    get_current_block_height,
    get_current_price,
    get_current_time,
    get_fees_string,
    get_last_block_time_from_metrics,
    get_minutes_between_blocks,
    get_remaining_blocks,
    get_symbol,
    price_change_string,
)


def _newblock_count_line(metrics) -> str:
    return f"{metrics.mempool_blocks} blks {metrics.mempool_count} txs"


def _newblock_difficulty_line(metrics) -> str:
    remaining_blocks = get_remaining_blocks(metrics)
    multiplier = metrics.retarget_multiplier * 100 - 100
    if metrics.retarget_date is not None:
        return (
            f"{remaining_blocks} blk {multiplier:.2f}% "
            f"{metrics.retarget_date.strftime('%d.%b %H:%M')}"
        )
    return f"{remaining_blocks} blk {multiplier:.2f}%"


def _block_time_header(left: str, metrics) -> str:
    return (
        f"{left}-"
        f"{get_last_block_time_from_metrics(metrics, date_and_time=False)}-"
        f"{int(metrics.last_block_seconds_ago / 60)} min"
    )


def _clock_header(snapshot: MarketSnapshot, left: str, metrics) -> str:
    return (
        f"{left} - {get_minutes_between_blocks(metrics)} - {get_current_time(snapshot)}"
    )


def _last_block_age(metrics) -> str:
    return (
        f"lb -{int(metrics.last_block_seconds_ago / 60)}:"
        f"{metrics.last_block_seconds_ago % 60}"
    )


def _remaining_blocks(metrics) -> str:
    return f"{get_remaining_blocks(metrics)} blk"


def generate_fiat(snapshot: MarketSnapshot, config, mode: str) -> list[str]:
    line_str = [" ", " ", " ", " ", " ", " ", " ", " "]
    metrics = compute_mempool_metrics(snapshot)

    if mode == "newblock":
        line_str[0] = _clock_header(
            snapshot,
            get_current_price(snapshot, "fiat", with_symbol=True),
            metrics,
        )
        line_str[1] = get_fees_string(snapshot, config.show_best_fees)
        line_str[2] = _newblock_count_line(metrics)
        line_str[3] = _newblock_difficulty_line(metrics)
        line_str[4] = get_current_block_height(metrics)
        return line_str

    if mode == "fiat":
        if config.show_block_time:
            line_str[0] = _block_time_header(get_current_block_height(metrics), metrics)
        else:
            line_str[0] = _clock_header(
                snapshot,
                get_current_block_height(metrics),
                metrics,
            )
        line_str[2] = _last_block_age(metrics)
        line_str[3] = _remaining_blocks(metrics)
        line_str[4] = get_current_price(snapshot, "sat_per_fiat", with_symbol=True)
        line_str[5] = get_symbol(snapshot)
        line_str[7] = get_current_price(snapshot, "fiat")
    elif mode == "height":
        if config.show_block_time:
            line_str[0] = _block_time_header(
                get_current_price(snapshot, "fiat", with_symbol=True),
                metrics,
            )
        else:
            line_str[0] = _clock_header(
                snapshot,
                get_current_price(snapshot, "fiat", with_symbol=True),
                metrics,
            )
        line_str[2] = _last_block_age(metrics)
        line_str[3] = _remaining_blocks(metrics)
        line_str[4] = get_current_price(snapshot, "sat_per_fiat", with_symbol=True)
        line_str[7] = get_current_block_height(metrics)
    elif mode == "satfiat":
        if config.show_block_time:
            line_str[0] = _block_time_header(get_current_block_height(metrics), metrics)
        else:
            line_str[0] = _clock_header(
                snapshot,
                get_current_block_height(metrics),
                metrics,
            )
        line_str[2] = _last_block_age(metrics)
        line_str[3] = _remaining_blocks(metrics)
        line_str[4] = get_current_price(snapshot, "fiat", with_symbol=True)
        line_str[5] = f"sat/{get_symbol(snapshot)}"
        line_str[7] = get_current_price(snapshot, "sat_per_fiat")
    elif mode == "moscowtime":
        if config.show_block_time:
            line_str[0] = _block_time_header(get_current_block_height(metrics), metrics)
        else:
            line_str[0] = _clock_header(
                snapshot,
                get_current_block_height(metrics),
                metrics,
            )
        line_str[2] = _last_block_age(metrics)
        line_str[3] = _remaining_blocks(metrics)
        line_str[4] = get_current_price(snapshot, "fiat", with_symbol=True)
        line_str[5] = "sat"
        line_str[6] = price_change_string(snapshot, False)
        line_str[7] = get_current_price(snapshot, "moscow_time_usd")
        line_str[1] = get_fees_string(snapshot, config.show_best_fees)
        return line_str
    elif mode == "usd":
        if config.show_block_time:
            line_str[0] = _block_time_header(get_current_block_height(metrics), metrics)
        else:
            line_str[0] = _clock_header(
                snapshot,
                get_current_block_height(metrics),
                metrics,
            )
        line_str[2] = _last_block_age(metrics)
        line_str[3] = _remaining_blocks(metrics)
        line_str[4] = get_current_price(snapshot, "fiat", with_symbol=True)
        line_str[5] = "$"
        line_str[7] = get_current_price(snapshot, "usd")

    line_str[1] = get_fees_string(snapshot, config.show_best_fees)
    line_str[6] = price_change_string(snapshot, False)
    return line_str
