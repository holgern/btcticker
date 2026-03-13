from __future__ import annotations

from btcticker.domain.market_snapshot import MarketSnapshot
from btcticker.layouts.common import (
    compute_mempool_metrics,
    generate_line_str,
    get_current_block_height,
    get_current_price,
    get_current_time,
    get_fee_string,
    get_fees_string,
    get_last_block_time2,
    get_last_block_time_from_metrics,
    get_minutes_between_blocks,
    get_remaining_blocks,
    get_symbol,
)


def generate_big_one_row(snapshot: MarketSnapshot, config, mode: str) -> list[str]:
    metrics = compute_mempool_metrics(snapshot)
    lines = {
        "fiat": [
            (
                "t",
                "%s - %d - %s - %s"
                % (
                    get_current_block_height(metrics),
                    get_remaining_blocks(metrics),
                    get_minutes_between_blocks(metrics),
                    get_current_time(snapshot),
                ),
            ),
            ("n", ""),
            (
                "t",
                get_symbol(snapshot)
                + " "
                + get_fee_string(snapshot, config.show_best_fees),
            ),
            ("n", ""),
            ("t", get_current_price(snapshot, "fiat")),
        ],
        "height": [
            (
                "t",
                "%s - %d - %s - %s"
                % (
                    get_current_price(snapshot, "fiat", with_symbol=True),
                    get_remaining_blocks(metrics),
                    get_minutes_between_blocks(metrics),
                    get_current_time(snapshot),
                ),
            ),
            ("n", ""),
            ("t", get_fee_string(snapshot, config.show_best_fees)),
            ("n", ""),
            ("t", get_current_block_height(metrics)),
        ],
        "satfiat": [
            (
                "t",
                "%s - %d - %s - %s"
                % (
                    get_current_block_height(metrics),
                    get_remaining_blocks(metrics),
                    get_minutes_between_blocks(metrics),
                    get_current_time(snapshot),
                ),
            ),
            ("n", ""),
            (
                "t",
                f"/{get_symbol(snapshot)} "
                + get_fee_string(snapshot, config.show_best_fees),
            ),
            ("n", ""),
            ("t", get_current_price(snapshot, "sat_per_fiat")),
        ],
        "moscowtime": [
            (
                "t",
                "%s - %d - %s - %s"
                % (
                    get_current_block_height(metrics),
                    get_remaining_blocks(metrics),
                    get_minutes_between_blocks(metrics),
                    get_current_time(snapshot),
                ),
            ),
            ("n", ""),
            ("t", "/$ " + get_fee_string(snapshot, config.show_best_fees)),
            ("n", ""),
            ("t", get_current_price(snapshot, "sat_per_fiat")),
        ],
        "usd": [
            (
                "t",
                "%s - %d - %s - %s"
                % (
                    get_current_block_height(metrics),
                    get_remaining_blocks(metrics),
                    get_minutes_between_blocks(metrics),
                    get_current_time(snapshot),
                ),
            ),
            ("n", ""),
            ("t", "$ " + get_fee_string(snapshot, config.show_best_fees)),
            ("n", ""),
            ("t", get_current_price(snapshot, "usd")),
        ],
    }

    if config.show_block_time:
        lines["fiat"][0] = (
            "t",
            f"{get_current_block_height(metrics)} - {get_last_block_time_from_metrics(metrics)} - {get_last_block_time2(metrics)}",
        )
        lines["height"][0] = (
            "t",
            "{} - {} - {}".format(
                get_current_price(snapshot, "fiat", with_symbol=True),
                get_last_block_time_from_metrics(metrics),
                get_last_block_time2(metrics),
            ),
        )
        lines["satfiat"][0] = (
            "t",
            f"{get_current_block_height(metrics)} - {get_last_block_time_from_metrics(metrics)} - {get_last_block_time2(metrics)}",
        )
        lines["moscowtime"][0] = (
            "t",
            f"{get_current_block_height(metrics)} - {get_last_block_time_from_metrics(metrics)} - {get_last_block_time2(metrics)}",
        )
        lines["usd"][0] = (
            "t",
            f"{get_current_block_height(metrics)} - {get_last_block_time_from_metrics(metrics)} - {get_last_block_time2(metrics)}",
        )

    lines["newblock"] = lines["height"]
    return generate_line_str(lines, mode, snapshot, metrics)
