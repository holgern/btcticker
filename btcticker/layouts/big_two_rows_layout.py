from __future__ import annotations

from btcticker.domain.market_snapshot import MarketSnapshot
from btcticker.layouts.common import (
    compute_mempool_metrics,
    generate_line_str,
    get_current_block_height,
    get_current_price,
    get_current_time,
    get_minutes_between_blocks,
    get_symbol,
    usd_value,
)


def generate_big_two_rows(snapshot: MarketSnapshot, _config, mode: str) -> list[str]:
    metrics = compute_mempool_metrics(snapshot)
    price_parts = (snapshot.price_now or "n/a").split(",")
    left = price_parts[0]
    right = price_parts[1] if len(price_parts) > 1 else ""
    price_parts_usd = format(int(float(usd_value(snapshot) or 0)), ",").split(",")
    usd_left = price_parts_usd[0]
    usd_right = price_parts_usd[1] if len(price_parts_usd) > 1 else ""
    lines = {
        "fiat": [
            ("t", get_symbol(snapshot) + left),
            ("n", ""),
            (
                "t",
                f"{get_current_block_height(metrics)} - {get_minutes_between_blocks(metrics)} - {get_current_time(snapshot)}",
            ),
            ("n", ""),
            ("t", right),
        ],
        "height": [
            ("t", get_current_block_height(metrics)[:3]),
            ("n", ""),
            (
                "t",
                f"{get_current_price(snapshot, 'fiat', with_symbol=True).replace(get_symbol(snapshot) + left + right, get_symbol(snapshot) + (snapshot.price_now or 'n/a')) if right else get_current_price(snapshot, 'fiat', with_symbol=True)} - {get_minutes_between_blocks(metrics)} - {get_current_time(snapshot)}",
            ),
            ("n", ""),
            ("t", get_current_block_height(metrics)[3:]),
        ],
        "satfiat": [
            ("t", f"sat/{get_symbol(snapshot)}"),
            ("n", ""),
            (
                "t",
                f"{get_symbol(snapshot) + (snapshot.price_now or 'n/a')} - {get_minutes_between_blocks(metrics)} - {get_current_time(snapshot)}",
            ),
            ("n", ""),
            ("t", get_current_price(snapshot, "sat_per_fiat")),
        ],
        "moscowtime": [
            ("t", "sat/$"),
            ("n", ""),
            (
                "t",
                f"{get_symbol(snapshot) + (snapshot.price_now or 'n/a')} - {get_minutes_between_blocks(metrics)} - {get_current_time(snapshot)}",
            ),
            ("n", ""),
            ("t", get_current_price(snapshot, "moscow_time_usd")),
        ],
        "usd": [
            ("t", "$" + usd_left),
            ("n", ""),
            (
                "t",
                f"{get_current_block_height(metrics)} - {get_minutes_between_blocks(metrics)} - {get_current_time(snapshot)}",
            ),
            ("n", ""),
            ("t", usd_right or right),
        ],
    }
    lines["newblock"] = lines["height"]
    return generate_line_str(lines, mode, snapshot, metrics)
