from btcticker.domain.market_snapshot import MarketSnapshot
from btcticker.layouts.common import (
    compute_mempool_metrics,
    get_current_block_height,
    get_current_price,
    get_fee_string,
    get_next_difficulty_string,
    get_sat_per_fiat,
    get_symbol,
    sat_per_usd_value,
    usd_value,
)


def _fiat_and_usd_line(snapshot: MarketSnapshot) -> str:
    return (
        f"{get_sat_per_fiat(snapshot) or 0:.0f} /{get_symbol(snapshot)} - "
        f"${usd_value(snapshot)} - {snapshot.price_snapshot.sat_per_usd or 0:.0f} /$"
    )


def generate_fiat_height(snapshot: MarketSnapshot, config, mode: str) -> list[str]:
    line_str = ["", "", "", "", ""]
    metrics = compute_mempool_metrics(snapshot)
    fiat_is_usd = snapshot.price_snapshot.fiat == "usd"

    if mode == "fiat":
        line_str[0] = get_current_block_height(metrics)
        if fiat_is_usd:
            line_str[3] = get_current_price(snapshot, "sat_per_fiat", with_symbol=True)
        else:
            line_str[3] = _fiat_and_usd_line(snapshot)
        line_str[4] = get_current_price(snapshot, "fiat", with_symbol=True)
    elif mode in {"height", "newblock"}:
        line_str[0] = get_current_price(snapshot, "fiat", with_symbol=True)
        if fiat_is_usd:
            line_str[3] = get_current_price(snapshot, "sat_per_fiat", with_symbol=True)
        else:
            line_str[3] = _fiat_and_usd_line(snapshot)
        line_str[4] = get_current_block_height(metrics)
    elif mode == "satfiat":
        line_str[0] = get_current_block_height(metrics)
        if fiat_is_usd:
            line_str[3] = get_current_price(snapshot, "fiat", with_symbol=True)
        else:
            line_str[3] = "{} - ${} - {:.0f} /$".format(
                get_current_price(snapshot, "fiat", with_symbol=True),
                usd_value(snapshot),
                snapshot.price_snapshot.sat_per_usd or 0,
            )
        line_str[4] = get_current_price(snapshot, "sat_per_fiat", with_symbol=True)
    elif mode == "moscowtime":
        line_str[0] = get_current_block_height(metrics)
        if fiat_is_usd:
            line_str[3] = get_current_price(snapshot, "fiat", with_symbol=True)
        else:
            line_str[3] = "{} - ${} - {:.0f} /$".format(
                get_current_price(snapshot, "fiat", with_symbol=True),
                usd_value(snapshot),
                snapshot.price_snapshot.sat_per_usd or 0,
            )
        line_str[4] = f"/${sat_per_usd_value(snapshot)}"
    elif mode == "usd":
        line_str[0] = get_current_block_height(metrics)
        if fiat_is_usd:
            line_str[3] = get_current_price(snapshot, "sat_per_fiat", with_symbol=True)
        else:
            line_str[3] = "{:.0f} /{} - {} - {:.0f} /$".format(
                get_sat_per_fiat(snapshot) or 0,
                get_symbol(snapshot),
                get_current_price(snapshot, "fiat", with_symbol=True),
                snapshot.price_snapshot.sat_per_usd or 0,
            )
        line_str[4] = get_current_price(snapshot, "usd")

    line_str[1] = get_fee_string(snapshot, config.show_best_fees)
    line_str[2] = get_next_difficulty_string(metrics)
    return line_str
