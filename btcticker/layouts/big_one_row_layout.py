from __future__ import annotations

from btcticker.domain.market_snapshot import MarketSnapshot
from btcticker.layouts.common import (
    compute_mempool_metrics,
    generate_line_str,
    get_current_block_height,
    get_current_price,
    get_current_time,
    get_fee_string,
    get_last_block_time2,
    get_last_block_time_from_metrics,
    get_minutes_between_blocks,
    get_remaining_blocks,
    get_symbol,
)


def _header(left: str, metrics, snapshot: MarketSnapshot) -> str:
    return (
        f"{left} - {get_remaining_blocks(metrics)} - "
        f"{get_minutes_between_blocks(metrics)} - {get_current_time(snapshot)}"
    )


def _block_time_header(left: str, metrics) -> str:
    return (
        f"{left} - {get_last_block_time_from_metrics(metrics)} - "
        f"{get_last_block_time2(metrics)}"
    )


def generate_big_one_row(snapshot: MarketSnapshot, config, mode: str) -> list[str]:
    metrics = compute_mempool_metrics(snapshot)
    lines = {
        "fiat": [
            (
                "t",
                _header(get_current_block_height(metrics), metrics, snapshot),
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
                _header(
                    get_current_price(snapshot, "fiat", with_symbol=True),
                    metrics,
                    snapshot,
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
                _header(get_current_block_height(metrics), metrics, snapshot),
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
                _header(get_current_block_height(metrics), metrics, snapshot),
            ),
            ("n", ""),
            ("t", "/$ " + get_fee_string(snapshot, config.show_best_fees)),
            ("n", ""),
            ("t", get_current_price(snapshot, "sat_per_fiat")),
        ],
        "usd": [
            (
                "t",
                _header(get_current_block_height(metrics), metrics, snapshot),
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
            _block_time_header(get_current_block_height(metrics), metrics),
        )
        lines["height"][0] = (
            "t",
            _block_time_header(
                get_current_price(snapshot, "fiat", with_symbol=True),
                metrics,
            ),
        )
        lines["satfiat"][0] = (
            "t",
            _block_time_header(get_current_block_height(metrics), metrics),
        )
        lines["moscowtime"][0] = (
            "t",
            _block_time_header(get_current_block_height(metrics), metrics),
        )
        lines["usd"][0] = (
            "t",
            _block_time_header(get_current_block_height(metrics), metrics),
        )

    lines["newblock"] = lines["height"]
    return generate_line_str(lines, mode, snapshot, metrics)
