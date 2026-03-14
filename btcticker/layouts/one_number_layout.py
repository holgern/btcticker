from btcticker.domain.market_snapshot import MarketSnapshot
from btcticker.layouts.common import (
    compute_mempool_metrics,
    generate_line_str,
    get_symbol,
)


def generate_one_number(snapshot: MarketSnapshot, _config, mode: str) -> list[str]:
    metrics = compute_mempool_metrics(snapshot)
    lines = {
        "fiat": [
            ("s", "_current_price_fiat_symbol_"),
            ("n", ""),
            ("t", "Market price of bitcoin"),
        ],
        "height": [
            ("s", "_current_block_height_"),
            ("n", ""),
            ("t", "Number of blocks in the blockchain"),
        ],
        "newblock": [
            ("s", "_current_block_height_"),
            ("n", ""),
            ("t", "Number of blocks in the blockchain"),
        ],
        "satfiat": [
            ("s", "_sat_per_fiat_with_symbol_"),
            ("n", ""),
            ("t", f"Value of one {get_symbol(snapshot)} in sats"),
        ],
        "moscowtime": [
            ("s", "_moscow_time_usd_"),
            ("n", ""),
            ("t", "moscow time"),
        ],
        "usd": [
            ("s", "_current_price_usd_"),
            ("n", ""),
            ("t", "Market price of bitcoin"),
        ],
    }
    return generate_line_str(lines, mode, snapshot, metrics)
