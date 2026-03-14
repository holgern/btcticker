from btcticker.domain.market_snapshot import MarketSnapshot
from btcticker.layouts.common import (
    compute_mempool_metrics,
    get_current_block_height,
    get_current_price,
    get_next_difficulty_string,
    get_sat_per_fiat,
    get_symbol,
)


def _last_block_age(metrics) -> str:
    return (
        f"lb -{int(metrics.last_block_seconds_ago / 60)}:"
        f"{metrics.last_block_seconds_ago % 60}"
    )


def generate_mempool(snapshot: MarketSnapshot, _config, mode: str) -> list[str]:
    line_str = ["", "", "", ""]
    metrics = compute_mempool_metrics(snapshot)

    if mode == "fiat":
        line_str[0] = get_current_price(snapshot, "fiat")
        line_str[2] = (
            f"{get_current_block_height(metrics)} - "
            f"{get_sat_per_fiat(snapshot) or 0:.0f} /{get_symbol(snapshot)} - "
            f"{_last_block_age(metrics)}"
        )
    elif mode in {"height", "newblock"}:
        line_str[0] = get_current_block_height(metrics)
        line_str[2] = (
            f"{get_current_price(snapshot, 'fiat', with_symbol=True)} - "
            f"{get_sat_per_fiat(snapshot) or 0:.0f} /{get_symbol(snapshot)} - "
            f"{_last_block_age(metrics)}"
        )
    elif mode == "satfiat":
        line_str[0] = get_current_price(snapshot, "sat_per_fiat", with_symbol=True)
        line_str[2] = (
            f"{get_current_price(snapshot, 'fiat', with_symbol=True)} - "
            f"{get_current_block_height(metrics)} - {_last_block_age(metrics)}"
        )
    elif mode == "moscowtime":
        line_str[0] = get_current_price(snapshot, "sat_per_usd", shorten=True)
        line_str[2] = (
            f"{get_current_price(snapshot, 'fiat', with_symbol=True)} - "
            f"{get_current_block_height(metrics)} - {_last_block_age(metrics)}"
        )
    elif mode == "usd":
        line_str[0] = get_current_price(snapshot, "usd")
        line_str[2] = (
            f"{get_current_price(snapshot, 'fiat', with_symbol=True)} - "
            f"{get_current_block_height(metrics)} - {_last_block_age(metrics)}"
        )

    line_str[1] = get_next_difficulty_string(metrics)
    best_fees = snapshot.mempool.get("bestFees", {})
    if float(best_fees.get("hourFee", 0.0)) > 10:
        line_str[3] = (
            f"{best_fees.get('hourFee', 0)} "
            f"{best_fees.get('halfHourFee', 0)} "
            f"{best_fees.get('fastestFee', 0)}"
        )
    else:
        line_str[3] = "{:.1f} {:.1f} {:.1f}".format(
            float(best_fees.get("hourFee", 0.0)),
            float(best_fees.get("halfHourFee", 0.0)),
            float(best_fees.get("fastestFee", 0.0)),
        )
    return line_str
