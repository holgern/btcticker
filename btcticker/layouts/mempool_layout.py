from __future__ import annotations

from btcticker.domain.market_snapshot import MarketSnapshot
from btcticker.layouts.common import (
    compute_mempool_metrics,
    get_current_block_height,
    get_current_price,
    get_next_difficulty_string,
    get_sat_per_fiat,
    get_symbol,
)


def generate_mempool(snapshot: MarketSnapshot, _config, mode: str) -> list[str]:
    line_str = ["", "", "", ""]
    metrics = compute_mempool_metrics(snapshot)

    if mode == "fiat":
        line_str[0] = get_current_price(snapshot, "fiat")
        line_str[2] = "%s - %.0f /%s - lb -%d:%d" % (
            get_current_block_height(metrics),
            get_sat_per_fiat(snapshot) or 0,
            get_symbol(snapshot),
            int(metrics.last_block_seconds_ago / 60),
            metrics.last_block_seconds_ago % 60,
        )
    elif mode in {"height", "newblock"}:
        line_str[0] = get_current_block_height(metrics)
        line_str[2] = "%s - %.0f /%s - lb -%d:%d" % (
            get_current_price(snapshot, "fiat", with_symbol=True),
            get_sat_per_fiat(snapshot) or 0,
            get_symbol(snapshot),
            int(metrics.last_block_seconds_ago / 60),
            metrics.last_block_seconds_ago % 60,
        )
    elif mode == "satfiat":
        line_str[0] = get_current_price(snapshot, "sat_per_fiat", with_symbol=True)
        line_str[2] = "%s - %s - lb -%d:%d" % (
            get_current_price(snapshot, "fiat", with_symbol=True),
            get_current_block_height(metrics),
            int(metrics.last_block_seconds_ago / 60),
            metrics.last_block_seconds_ago % 60,
        )
    elif mode == "moscowtime":
        line_str[0] = get_current_price(snapshot, "sat_per_usd", shorten=True)
        line_str[2] = "%s - %s - lb -%d:%d" % (
            get_current_price(snapshot, "fiat", with_symbol=True),
            get_current_block_height(metrics),
            int(metrics.last_block_seconds_ago / 60),
            metrics.last_block_seconds_ago % 60,
        )
    elif mode == "usd":
        line_str[0] = get_current_price(snapshot, "usd")
        line_str[2] = "%s - %s - lb -%d:%d" % (
            get_current_price(snapshot, "fiat", with_symbol=True),
            get_current_block_height(metrics),
            int(metrics.last_block_seconds_ago / 60),
            metrics.last_block_seconds_ago % 60,
        )

    line_str[1] = get_next_difficulty_string(metrics)
    best_fees = snapshot.mempool.get("bestFees", {})
    if float(best_fees.get("hourFee", 0.0)) > 10:
        line_str[3] = "%d %d %d" % (
            best_fees.get("hourFee", 0),
            best_fees.get("halfHourFee", 0),
            best_fees.get("fastestFee", 0),
        )
    else:
        line_str[3] = "{:.1f} {:.1f} {:.1f}".format(
            float(best_fees.get("hourFee", 0.0)),
            float(best_fees.get("halfHourFee", 0.0)),
            float(best_fees.get("fastestFee", 0.0)),
        )
    return line_str
