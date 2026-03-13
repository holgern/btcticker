from __future__ import annotations

import argparse
import os
import shlex
import shutil
import subprocess
import warnings
from configparser import ConfigParser
from collections.abc import Iterable
from pathlib import Path

from btcticker.config import Config, FontsConfig, MainConfig
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

LOCAL_CONFIG_FILENAME = "config.ini"
GLOBAL_CONFIG_SUFFIX = Path(".config") / "btcticker" / "config.ini"

SUPPORTED_MODES = ("fiat", "height", "satfiat", "moscowtime", "usd", "newblock")

LAYOUT_SPECS = {
    "all": {
        "generator": "generate_all",
        "draw": "draw_all",
        "text_rows": 8,
        "newblock": "custom",
    },
    "fiat": {
        "generator": "generate_fiat",
        "draw": "draw_fiat",
        "text_rows": 8,
        "newblock": "custom",
    },
    "fiatheight": {
        "generator": "generate_fiat_height",
        "draw": "draw_fiat_height",
        "text_rows": 5,
        "newblock": "alias(height)",
    },
    "big_one_row": {
        "generator": "generate_big_one_row",
        "draw": "draw_big_one_row",
        "text_rows": 3,
        "newblock": "alias(height)",
    },
    "big_two_rows": {
        "generator": "generate_big_two_rows",
        "draw": "draw_big_two_rows",
        "text_rows": 3,
        "newblock": "alias(height)",
    },
    "one_number": {
        "generator": "generate_one_number",
        "draw": "draw_one_number",
        "text_rows": 2,
        "newblock": "alias(height)",
    },
    "mempool": {
        "generator": "generate_mempool",
        "draw": "draw_mempool",
        "text_rows": 4,
        "newblock": "alias(height)",
    },
    "ohlc": {
        "generator": "generate_ohlc",
        "draw": "draw_ohlc",
        "text_rows": 7,
        "newblock": "alias(height)",
    },
}


def _split_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _as_config_string(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return str(value).lower()
    return str(value)


def _get_local_config_path() -> Path:
    return Path.cwd() / LOCAL_CONFIG_FILENAME


def _get_global_config_path() -> Path:
    return Path.home() / GLOBAL_CONFIG_SUFFIX


def _resolve_default_config_path() -> Path:
    local_path = _get_local_config_path()
    if local_path.exists():
        return local_path
    return _get_global_config_path()


def _resolve_config_path(
    selected_path: str | None,
    use_local: bool,
    use_global: bool,
    *,
    require_exists: bool,
    strict_local: bool,
) -> Path:
    if selected_path:
        config_path = Path(selected_path).expanduser()
    elif use_local:
        config_path = _get_local_config_path()
    elif use_global:
        config_path = _get_global_config_path()
    else:
        config_path = _resolve_default_config_path()

    if strict_local and use_local and not config_path.exists():
        raise ValueError(f"Local config file not found: {config_path}")
    if require_exists and not config_path.exists():
        raise ValueError(f"Config file not found: {config_path}")
    return config_path


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


def _derive_symbol(config: Config) -> str:
    return config.main.symbol or f"BTC/{config.main.fiat.upper()}"


def _resolve_provider_name(config: Config) -> str:
    has_provider = config.has_option("Main", "price_provider")
    has_service = config.has_option("Main", "price_service") and bool(
        config.main.price_service
    )

    if has_provider:
        provider_name = config.main.price_provider
        if has_service:
            warnings.warn(
                "'price_service' is deprecated; use 'price_provider', 'exchange', "
                "'symbol', and 'usd_symbol' instead.",
                DeprecationWarning,
                stacklevel=2,
            )
        return provider_name

    if has_service:
        warnings.warn(
            "'price_service' is deprecated; using the legacy btcpriceticker adapter.",
            DeprecationWarning,
            stacklevel=2,
        )
        return "btcpriceticker"

    return config.main.price_provider


def build_price_provider(config: Config, days_ago: int):
    provider_name = _resolve_provider_name(config)
    if provider_name == "pyccxt":
        from btcticker.providers import PyCCXTPriceProvider

        return PyCCXTPriceProvider(
            exchange_name=config.main.exchange,
            fiat_symbol=_derive_symbol(config),
            usd_symbol=config.main.usd_symbol or "BTC/USD",
            interval=config.main.interval,
            days_ago=days_ago,
            enable_ohlc=config.main.enable_ohlc,
            timeout_ms=config.main.ccxt_timeout,
            min_refresh_time=config.main.price_refresh_seconds,
        )

    if provider_name in {"btcpriceticker", "legacy"}:
        from btcticker.providers import BTCPriceTickerProvider

        return BTCPriceTickerProvider(
            fiat=config.main.fiat,
            service=config.main.price_service or "coingecko",
            interval=config.main.interval,
            days_ago=days_ago,
            enable_ohlc=config.main.enable_ohlc,
            min_refresh_time=config.main.price_refresh_seconds,
        )

    raise ValueError(
        f"Unknown price provider '{provider_name}'. Available providers: "
        "pyccxt, btcpriceticker"
    )


def _build_ticker(config: Config, days_ago: int):
    from btcticker.ticker import Ticker

    height, width = _get_display_size(config.main.epd_type)
    price_provider = build_price_provider(config, days_ago)
    if config.main.orientation in (90, 270):
        ticker = Ticker(config, height, width, price_provider=price_provider)
    else:
        ticker = Ticker(config, width, height, price_provider=price_provider)
    ticker.set_days_ago(days_ago)
    ticker.refresh()
    return ticker


def _generate_lines(ticker, layout: str, mode: str) -> list[str]:
    if layout not in LAYOUT_SPECS:
        available_layouts = ", ".join(sorted(LAYOUT_SPECS.keys()))
        raise ValueError(
            f"Unknown layout '{layout}'. Available layouts: {available_layouts}"
        )

    generate = getattr(ticker, LAYOUT_SPECS[layout]["generator"])
    return generate(mode)


def _format_table(headers: list[str], rows: list[list[str]]) -> str:
    widths = [len(header) for header in headers]
    for row in rows:
        for index, value in enumerate(row):
            widths[index] = max(widths[index], len(value))

    header_line = " | ".join(
        header.ljust(widths[index]) for index, header in enumerate(headers)
    )
    separator = "-+-".join("-" * width for width in widths)
    body_lines = [
        " | ".join(value.ljust(widths[index]) for index, value in enumerate(row))
        for row in rows
    ]
    return "\n".join([header_line, separator, *body_lines])


def _run_layouts(_args: argparse.Namespace) -> int:
    default_layouts = _split_csv(MainConfig().layout_list)
    default_positions = {name: str(index) for index, name in enumerate(default_layouts)}

    headers = [
        "layout",
        "generator",
        "draw",
        "text_rows",
        "newblock",
        "default_pos",
        "modes",
    ]
    rows: list[list[str]] = []

    for layout, spec in LAYOUT_SPECS.items():
        rows.append(
            [
                layout,
                spec["generator"],
                spec["draw"],
                str(spec["text_rows"]),
                spec["newblock"],
                default_positions.get(layout, "-"),
                ",".join(SUPPORTED_MODES),
            ]
        )

    print(_format_table(headers, rows))
    return 0


def _build_default_config_text() -> str:
    main_values = MainConfig().model_dump()
    font_values = FontsConfig().model_dump()
    lines = ["[Main]"]
    for key, value in main_values.items():
        lines.append(f"{key} = {_as_config_string(value)}")
    lines.append("")
    lines.append("[Fonts]")
    for key, value in font_values.items():
        lines.append(f"{key} = {_as_config_string(value)}")
    lines.append("")
    return "\n".join(lines)


def _pick_editor() -> str:
    for env_var in ("VISUAL", "EDITOR"):
        value = os.environ.get(env_var)
        if value:
            return value

    for fallback in ("nano", "vi"):
        editor = shutil.which(fallback)
        if editor:
            return editor

    raise ValueError("No editor configured. Set VISUAL or EDITOR.")


def _config_value_rows(config_path: Path) -> list[list[str]]:
    parser = ConfigParser()
    if config_path.exists():
        parser.read(config_path)

    rows: list[list[str]] = []
    section_values = {
        "Main": MainConfig().model_dump(),
        "Fonts": FontsConfig().model_dump(),
    }
    for section_name, defaults in section_values.items():
        for key, default_value in defaults.items():
            if section_name in parser and key in parser[section_name]:
                rows.append([section_name, key, parser[section_name][key], "file"])
            else:
                rows.append(
                    [section_name, key, _as_config_string(default_value), "default"]
                )

    return rows


def _run_config_show(args: argparse.Namespace) -> int:
    config_path = _resolve_config_path(
        selected_path=None,
        use_local=args.use_local_config,
        use_global=args.use_global_config,
        require_exists=False,
        strict_local=True,
    )
    print(f"Config path: {config_path}")
    print(f"Exists: {'yes' if config_path.exists() else 'no'}")
    print(
        _format_table(
            headers=["section", "key", "value", "source"],
            rows=_config_value_rows(config_path),
        )
    )
    return 0


def _run_config_create(args: argparse.Namespace) -> int:
    config_path = _resolve_config_path(
        selected_path=None,
        use_local=args.use_local_config,
        use_global=args.use_global_config,
        require_exists=False,
        strict_local=False,
    )
    if config_path.exists():
        raise ValueError(
            f"Config file already exists: {config_path}. "
            "Use 'btcticker config edit' or remove it first."
        )

    config_path.parent.mkdir(parents=True, exist_ok=True)
    config_path.write_text(_build_default_config_text(), encoding="utf-8")
    print(f"Created config file: {config_path}")
    return 0


def _run_config_edit(args: argparse.Namespace) -> int:
    config_path = _resolve_config_path(
        selected_path=None,
        use_local=args.use_local_config,
        use_global=args.use_global_config,
        require_exists=True,
        strict_local=True,
    )
    editor = _pick_editor()
    command = [*shlex.split(editor), str(config_path)]
    completed = subprocess.run(command, check=False)
    if completed.returncode != 0:
        raise ValueError(f"Editor exited with status {completed.returncode}")
    return 0


def _run_config(args: argparse.Namespace) -> int:
    if args.config_action == "edit":
        return _run_config_edit(args)
    if args.config_action == "create":
        return _run_config_create(args)
    return _run_config_show(args)


def _run_text(args: argparse.Namespace) -> int:
    from piltext.ascii_art import display_readable_text

    config_path = _resolve_config_path(
        selected_path=args.config,
        use_local=args.use_local_config,
        use_global=args.use_global_config,
        require_exists=True,
        strict_local=True,
    )
    config = Config(path=str(config_path))
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


def _run_image(args: argparse.Namespace) -> int:
    config_path = _resolve_config_path(
        selected_path=args.config,
        use_local=args.use_local_config,
        use_global=args.use_global_config,
        require_exists=True,
        strict_local=True,
    )
    config = Config(path=str(config_path))
    mode = _resolve_mode(config, args.mode)
    layout = _resolve_layout(config, args.layout)
    days = _resolve_days(config, args.days)

    ticker = _build_ticker(config, days)
    ticker.build(mode=mode, layout=layout, mirror=True)

    output_path = Path(args.output).expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ticker.get_image().save(output_path, format="PNG")
    print(f"Saved image to: {output_path}")
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


def _add_scope_options(
    parser: argparse.ArgumentParser, include_config_path: bool
) -> None:
    scope_group = parser.add_mutually_exclusive_group()
    if include_config_path:
        scope_group.add_argument("--config", help="Path to config.ini")
    scope_group.add_argument(
        "--local",
        dest="use_local_config",
        action="store_true",
        help=f"Use local ./{LOCAL_CONFIG_FILENAME}",
    )
    scope_group.add_argument(
        "--global",
        dest="use_global_config",
        action="store_true",
        help=f"Use global ~/{GLOBAL_CONFIG_SUFFIX}",
    )


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="btcticker")
    subparsers = parser.add_subparsers(dest="command", required=True)

    text_parser = subparsers.add_parser(
        "text",
        help="Render ticker text output for a layout",
    )
    _add_scope_options(text_parser, include_config_path=True)
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

    image_parser = subparsers.add_parser(
        "image",
        help="Render and save ticker as PNG image",
    )
    _add_scope_options(image_parser, include_config_path=True)
    image_parser.add_argument("--layout", help="Layout to render")
    image_parser.add_argument("--mode", help="Ticker mode to render")
    image_parser.add_argument("--days", type=int, help="Days ago for price history")
    image_parser.add_argument(
        "--output",
        "-o",
        default="btcticker.png",
        help="Output PNG file path (default: btcticker.png)",
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

    subparsers.add_parser(
        "layouts",
        help="List available layouts as a table",
    )

    config_parser = subparsers.add_parser(
        "config",
        help="Show or manage btcticker config files",
    )
    _add_scope_options(config_parser, include_config_path=False)
    config_subparsers = config_parser.add_subparsers(dest="config_action")

    config_edit_parser = config_subparsers.add_parser(
        "edit",
        help="Open selected config file in editor",
    )
    _add_scope_options(config_edit_parser, include_config_path=False)

    config_create_parser = config_subparsers.add_parser(
        "create",
        help="Create selected config file with defaults",
    )
    _add_scope_options(config_create_parser, include_config_path=False)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    try:
        if args.command == "text":
            return _run_text(args)
        if args.command == "image":
            return _run_image(args)
        if args.command == "download":
            return _run_download(args)
        if args.command == "layouts":
            return _run_layouts(args)
        if args.command == "config":
            return _run_config(args)
        parser.print_help()
        return 1
    except Exception as exc:
        parser.exit(status=1, message=f"Error: {exc}\n")


if __name__ == "__main__":
    raise SystemExit(main())
