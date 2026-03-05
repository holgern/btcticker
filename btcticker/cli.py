from __future__ import annotations

import argparse
from collections.abc import Iterable

from btcticker.config import Config
from btcticker.font_sources import (
    download_font_url,
    download_google_font,
    ensure_default_fonts,
)

DISPLAY_SIZES = {
    "2in7": (176, 264),
    "2in7_V2": (176, 264),
    "2in7_4gray": (176, 264),
    "2in9_V2": (128, 296),
    "7in5_V2": (480, 800),
}


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _select_from_list(values: Iterable[str], index: int, fallback: str) -> str:
    value_list = list(values)
    if not value_list:
        return fallback
    normalized_index = min(max(index, 0), len(value_list) - 1)
    return value_list[normalized_index]


def _resolve_mode(config: Config, selected_mode: str | None) -> str:
    if selected_mode:
        return selected_mode
    return _select_from_list(
        _split_csv(config.main.mode_list),
        config.main.start_mode_ind,
        "fiat",
    )


def _resolve_layout(config: Config, selected_layout: str | None) -> str:
    if selected_layout:
        return selected_layout
    return _select_from_list(
        _split_csv(config.main.layout_list),
        config.main.start_layout_ind,
        "all",
    )


def _resolve_days(config: Config, selected_days: int | None) -> int:
    if selected_days is not None:
        return selected_days

    day_values = _split_csv(config.main.days_list)
    selected = _select_from_list(day_values, config.main.start_days_ind, "1")
    return int(selected)


def _get_display_size(epd_type: str) -> tuple[int, int]:
    return DISPLAY_SIZES.get(epd_type, (528, 880))


def _build_ticker(config: Config, days_ago: int):
    from btcticker.ticker import Ticker

    height, width = _get_display_size(config.main.epd_type)
    if config.main.orientation in (90, 270):
        ticker = Ticker(config, height, width)
    else:
        ticker = Ticker(config, width, height)
    ticker.set_days_ago(days_ago)
    ticker.refresh()
    return ticker


def _generate_lines(ticker, layout: str, mode: str) -> list[str]:
    generators = {
        "all": "generate_all",
        "fiat": "generate_fiat",
        "fiatheight": "generate_fiat_height",
        "big_one_row": "generate_big_one_row",
        "big_two_rows": "generate_big_two_rows",
        "one_number": "generate_one_number",
        "mempool": "generate_mempool",
        "ohlc": "generate_ohlc",
    }

    if layout not in generators:
        available_layouts = ", ".join(sorted(generators.keys()))
        raise ValueError(
            f"Unknown layout '{layout}'. Available layouts: {available_layouts}"
        )

    generate = getattr(ticker, generators[layout])
    return generate(mode)


def _run_text(args: argparse.Namespace) -> int:
    from piltext.ascii_art import display_readable_text

    config = Config(path=args.config)
    mode = _resolve_mode(config, args.mode)
    layout = _resolve_layout(config, args.layout)
    days = _resolve_days(config, args.days)

    ticker = _build_ticker(config, days)
    lines = _generate_lines(ticker, layout, mode)

    if args.header:
        print(f"layout={layout} mode={mode} days={days}")

    output = display_readable_text(
        lines,
        width=args.width,
        line_spacing=args.line_spacing,
        center=not args.no_center,
    )
    print(output)
    return 0


def _run_download(args: argparse.Namespace) -> int:
    from piltext import FontManager

    font_manager = FontManager(fontdirs=args.fontdir) if args.fontdir else FontManager()

    if args.url and any([args.part1, args.part2, args.font_name]):
        raise ValueError("Use either --url or --part1/--part2/--font-name")

    if args.url:
        font_path = download_font_url(args.url, font_manager)
        print(f"Downloaded font from URL: {font_path}")
    elif any([args.part1, args.part2, args.font_name]):
        if not all([args.part1, args.part2, args.font_name]):
            raise ValueError(
                "--part1, --part2 and --font-name must be provided together"
            )
        font_path = download_google_font(
            args.part1,
            args.part2,
            args.font_name,
            font_manager,
        )
        print(f"Downloaded Google Font: {font_path}")
    else:
        downloaded = ensure_default_fonts(font_manager)
        if downloaded:
            print("Downloaded default btcticker fonts:")
            for font_name in downloaded:
                print(f"- {font_name}")
        else:
            print("All default btcticker fonts are already installed")

    directories = ", ".join(font_manager.list_font_directories())
    print(f"Font directories: {directories}")
    return 0


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="btcticker")
    subparsers = parser.add_subparsers(dest="command", required=True)

    text_parser = subparsers.add_parser(
        "text",
        help="Render ticker text output for a layout",
    )
    text_parser.add_argument(
        "--config", default="config.ini", help="Path to config.ini"
    )
    text_parser.add_argument("--layout", help="Layout to render")
    text_parser.add_argument("--mode", help="Ticker mode to render")
    text_parser.add_argument("--days", type=int, help="Days ago for price history")
    text_parser.add_argument("--width", type=int, default=80, help="Output width")
    text_parser.add_argument(
        "--line-spacing",
        type=int,
        default=1,
        help="Blank lines between text rows",
    )
    text_parser.add_argument(
        "--no-center",
        action="store_true",
        help="Disable centered text output",
    )
    text_parser.add_argument(
        "--header",
        action="store_true",
        help="Show layout/mode header before output",
    )

    download_parser = subparsers.add_parser(
        "download",
        help="Download fonts to user font storage",
    )
    download_parser.add_argument(
        "--fontdir",
        help="Custom font directory (defaults to piltext user directory)",
    )
    download_parser.add_argument("--url", help="Direct URL to a font file")
    download_parser.add_argument("--part1", help="Google Fonts category (e.g. ofl)")
    download_parser.add_argument("--part2", help="Google Fonts family (e.g. roboto)")
    download_parser.add_argument("--font-name", help="Google Fonts file name")

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "text":
            return _run_text(args)
        if args.command == "download":
            return _run_download(args)
        parser.print_help()
        return 1
    except Exception as exc:
        parser.exit(status=1, message=f"Error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
