from btcticker.domain.market_snapshot import MarketSnapshot
from btcticker.layouts.common import (
    compute_mempool_metrics,
    get_current_block_height,
    get_current_price,
    get_fee_string,
    get_last_block_time3,
    get_next_difficulty_string,
    get_sat_per_fiat,
    get_symbol,
    price_change_string,
    usd_value,
)


def _fiat_usd_sats_line(snapshot: MarketSnapshot) -> str:
    return (
        f"${usd_value(snapshot)} - {get_sat_per_fiat(snapshot) or 0:.0f} "
        f"/{get_symbol(snapshot)} - {snapshot.price_snapshot.sat_per_usd or 0:.0f} /$"
    )


def generate_ohlc(snapshot: MarketSnapshot, _config, mode: str) -> list[str]:
    line_str = ["", "", "", "", "", "", ""]
    metrics = compute_mempool_metrics(snapshot)

    if mode == "fiat":
        line_str[0] = get_current_block_height(metrics)
        line_str[1] = get_last_block_time3(metrics)
        line_str[4] = _fiat_usd_sats_line(snapshot)
        line_str[5] = price_change_string(snapshot, get_symbol(snapshot))
        line_str[6] = get_current_price(snapshot, "fiat")
    elif mode in {"height", "newblock"}:
        line_str[0] = get_current_price(snapshot, "fiat", with_symbol=True)
        line_str[1] = get_last_block_time3(metrics)
        line_str[4] = _fiat_usd_sats_line(snapshot)
        line_str[5] = price_change_string(snapshot, "")
        line_str[6] = get_current_block_height(metrics)
    elif mode == "satfiat":
        line_str[0] = get_current_block_height(metrics)
        line_str[1] = get_last_block_time3(metrics)
        line_str[4] = (
            get_symbol(snapshot)
            + get_current_price(snapshot, "fiat")
            + " - $"
            + usd_value(snapshot)
            + " - %.0f /$" % (snapshot.price_snapshot.sat_per_usd or 0)
        )
        line_str[5] = price_change_string(snapshot, f"/{get_symbol(snapshot)}")
        line_str[6] = get_current_price(snapshot, "sat_per_fiat")
    elif mode == "moscowtime":
        line_str[0] = get_current_block_height(metrics)
        line_str[1] = get_last_block_time3(metrics)
        line_str[4] = (
            get_symbol(snapshot)
            + get_current_price(snapshot, "fiat")
            + " - $"
            + usd_value(snapshot)
            + f" - {(get_sat_per_fiat(snapshot) or 0):.0f} /{get_symbol(snapshot)}"
        )
        line_str[5] = price_change_string(snapshot, "/$")
        line_str[6] = "%.0f" % (snapshot.price_snapshot.sat_per_usd or 0)
    elif mode == "usd":
        line_str[0] = get_current_block_height(metrics)
        line_str[1] = get_last_block_time3(metrics)
        line_str[4] = (
            get_symbol(snapshot)
            + get_current_price(snapshot, "fiat")
            + (
                f" - {get_sat_per_fiat(snapshot) or 0:.0f} /{get_symbol(snapshot)}"
                f" - {snapshot.price_snapshot.sat_per_usd or 0:.0f} /$"
            )
        )
        line_str[5] = price_change_string(snapshot, "$")
        line_str[6] = usd_value(snapshot)

    line_str[2] = get_fee_string(snapshot, _config.show_best_fees)
    line_str[3] = get_next_difficulty_string(
        metrics,
        show_clock=False,
        retarget_date=metrics.retarget_date,
    )
    return line_str
