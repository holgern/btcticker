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


def generate_fiat(snapshot: MarketSnapshot, config, mode: str) -> list[str]:
    line_str = [" ", " ", " ", " ", " ", " ", " ", " "]
    metrics = compute_mempool_metrics(snapshot)

    if mode == "newblock":
        line_str[0] = "%s - %s - %s" % (
            get_current_price(snapshot, "fiat", with_symbol=True),
            get_minutes_between_blocks(metrics),
            get_current_time(snapshot),
        )
        line_str[1] = get_fees_string(snapshot, config.show_best_fees)
        line_str[2] = "%d blks %d txs" % (metrics.mempool_blocks, metrics.mempool_count)
        if metrics.retarget_date is not None:
            line_str[3] = "%d blk %.2f%% %s" % (
                get_remaining_blocks(metrics),
                (metrics.retarget_multiplier * 100 - 100),
                metrics.retarget_date.strftime("%d.%b %H:%M"),
            )
        else:
            line_str[3] = "%d blk %.2f%%" % (
                get_remaining_blocks(metrics),
                (metrics.retarget_multiplier * 100 - 100),
            )
        line_str[4] = get_current_block_height(metrics)
        return line_str

    if mode == "fiat":
        if config.show_block_time:
            line_str[0] = "%s-%s-%d min" % (
                get_current_block_height(metrics),
                get_last_block_time_from_metrics(metrics, date_and_time=False),
                int(metrics.last_block_seconds_ago / 60),
            )
        else:
            line_str[0] = (
                f"{get_current_block_height(metrics)} - {get_minutes_between_blocks(metrics)} - "
                f"{get_current_time(snapshot)}"
            )
        line_str[2] = "lb -%d:%d" % (
            int(metrics.last_block_seconds_ago / 60),
            metrics.last_block_seconds_ago % 60,
        )
        line_str[3] = "%d blk" % get_remaining_blocks(metrics)
        line_str[4] = get_current_price(snapshot, "sat_per_fiat", with_symbol=True)
        line_str[5] = get_symbol(snapshot)
        line_str[7] = get_current_price(snapshot, "fiat")
    elif mode == "height":
        if config.show_block_time:
            line_str[0] = "%s-%s-%d min" % (
                get_current_price(snapshot, "fiat", with_symbol=True),
                get_last_block_time_from_metrics(metrics, date_and_time=False),
                int(metrics.last_block_seconds_ago / 60),
            )
        else:
            line_str[0] = "{} - {} - {}".format(
                get_current_price(snapshot, "fiat", with_symbol=True),
                get_minutes_between_blocks(metrics),
                get_current_time(snapshot),
            )
        line_str[2] = "lb -%d:%d" % (
            int(metrics.last_block_seconds_ago / 60),
            metrics.last_block_seconds_ago % 60,
        )
        line_str[3] = "%d blk" % get_remaining_blocks(metrics)
        line_str[4] = get_current_price(snapshot, "sat_per_fiat", with_symbol=True)
        line_str[7] = get_current_block_height(metrics)
    elif mode == "satfiat":
        if config.show_block_time:
            line_str[0] = "%s-%s-%d min" % (
                get_current_block_height(metrics),
                get_last_block_time_from_metrics(metrics, date_and_time=False),
                int(metrics.last_block_seconds_ago / 60),
            )
        else:
            line_str[0] = (
                f"{get_current_block_height(metrics)} - {get_minutes_between_blocks(metrics)} - "
                f"{get_current_time(snapshot)}"
            )
        line_str[2] = "lb -%d:%d" % (
            int(metrics.last_block_seconds_ago / 60),
            metrics.last_block_seconds_ago % 60,
        )
        line_str[3] = "%d blk" % get_remaining_blocks(metrics)
        line_str[4] = get_current_price(snapshot, "fiat", with_symbol=True)
        line_str[5] = f"sat/{get_symbol(snapshot)}"
        line_str[7] = get_current_price(snapshot, "sat_per_fiat")
    elif mode == "moscowtime":
        if config.show_block_time:
            line_str[0] = "%s-%s-%d min" % (
                get_current_block_height(metrics),
                get_last_block_time_from_metrics(metrics, date_and_time=False),
                int(metrics.last_block_seconds_ago / 60),
            )
        else:
            line_str[0] = (
                f"{get_current_block_height(metrics)} - {get_minutes_between_blocks(metrics)} - "
                f"{get_current_time(snapshot)}"
            )
        line_str[2] = "lb -%d:%d" % (
            int(metrics.last_block_seconds_ago / 60),
            metrics.last_block_seconds_ago % 60,
        )
        line_str[3] = "%d blk" % get_remaining_blocks(metrics)
        line_str[4] = get_current_price(snapshot, "fiat", with_symbol=True)
        line_str[5] = "sat"
        line_str[6] = price_change_string(snapshot, False)
        line_str[7] = get_current_price(snapshot, "moscow_time_usd")
        line_str[1] = get_fees_string(snapshot, config.show_best_fees)
        return line_str
    elif mode == "usd":
        if config.show_block_time:
            line_str[0] = "%s-%s-%d min" % (
                get_current_block_height(metrics),
                get_last_block_time_from_metrics(metrics, date_and_time=False),
                int(metrics.last_block_seconds_ago / 60),
            )
        else:
            line_str[0] = (
                f"{get_current_block_height(metrics)} - {get_minutes_between_blocks(metrics)} - "
                f"{get_current_time(snapshot)}"
            )
        line_str[2] = "lb -%d:%d" % (
            int(metrics.last_block_seconds_ago / 60),
            metrics.last_block_seconds_ago % 60,
        )
        line_str[3] = "%d blk" % get_remaining_blocks(metrics)
        line_str[4] = get_current_price(snapshot, "fiat", with_symbol=True)
        line_str[5] = "$"
        line_str[7] = get_current_price(snapshot, "usd")

    line_str[1] = get_fees_string(snapshot, config.show_best_fees)
    line_str[6] = price_change_string(snapshot, False)
    return line_str
