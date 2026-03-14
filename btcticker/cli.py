from __future__ import annotations

import os
import shlex
import shutil
import subprocess
import sys
from collections.abc import Callable, Iterable
from configparser import ConfigParser
from pathlib import Path
from typing import Annotated, Any, Protocol, cast

import click
import typer
from rich import box
from rich.console import Console
from rich.live import Live
from rich.table import Table

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

DEFAULT_CONSOLE_WIDTH = 200

ConfigPathOption = Annotated[
    str | None,
    typer.Option("--config", help="Path to config.ini"),
]
LocalOption = Annotated[
    bool,
    typer.Option("--local", help=f"Use local ./{LOCAL_CONFIG_FILENAME}"),
]
GlobalOption = Annotated[
    bool,
    typer.Option("--global", help=f"Use global ~/{GLOBAL_CONFIG_SUFFIX}"),
]

app = typer.Typer(pretty_exceptions_enable=False)
config_app = typer.Typer(
    help="Show or manage btcticker config files",
    invoke_without_command=True,
    pretty_exceptions_enable=False,
)
app.add_typer(config_app, name="config")


class TickerLike(Protocol):
    def set_days_ago(self, days_ago: int) -> None: ...

    def refresh(self) -> None: ...

    def build(
        self, mode: str = "fiat", layout: str = "all", mirror: bool = True
    ) -> None: ...

    def get_image(self) -> Any: ...


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
    if sum(bool(value) for value in (selected_path, use_local, use_global)) > 1:
        raise ValueError("Use only one of --config, --local, or --global")

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
    if config.has_option("Main", "price_service"):
        raise ValueError(
            "'price_service' is no longer supported. Migrate your config to "
            "'price_provider=pyccxt' and set 'exchange', 'symbol', and "
            "'usd_symbol'."
        )
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

    raise ValueError(
        f"Unknown price provider '{provider_name}'. Available providers: pyccxt"
    )


def _build_ticker(config: Config, days_ago: int) -> TickerLike:
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


def _generate_lines(ticker: Any, layout: str, mode: str) -> list[str]:
    if layout not in LAYOUT_SPECS:
        available_layouts = ", ".join(sorted(LAYOUT_SPECS.keys()))
        raise ValueError(
            f"Unknown layout '{layout}'. Available layouts: {available_layouts}"
        )

    generator_name = cast(str, LAYOUT_SPECS[layout]["generator"])
    generate = cast(Callable[[str], list[str]], getattr(ticker, generator_name))
    return generate(mode)


def _console(*, stderr: bool = False) -> Console:
    return Console(stderr=stderr, width=DEFAULT_CONSOLE_WIDTH)


def _build_table(headers: list[str], rows: list[list[str]]) -> Table:
    table = Table(box=box.ASCII, header_style="bold")
    for header in headers:
        table.add_column(header, no_wrap=True)
    for row in rows:
        table.add_row(*row)
    return table


def _render_text_output(output: str, console: Console) -> None:
    if console.is_terminal:
        with Live(console=console, auto_refresh=False) as live:
            live.update(output, refresh=True)
        return

    console.print(output, highlight=False, markup=False, soft_wrap=True)


def _run_layouts() -> int:
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
                cast(str, spec["generator"]),
                cast(str, spec["draw"]),
                str(spec["text_rows"]),
                cast(str, spec["newblock"]),
                default_positions.get(layout, "-"),
                ",".join(SUPPORTED_MODES),
            ]
        )

    _console().print(_build_table(headers, rows))
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


def _run_config_show(*, use_local_config: bool, use_global_config: bool) -> int:
    config_path = _resolve_config_path(
        selected_path=None,
        use_local=use_local_config,
        use_global=use_global_config,
        require_exists=False,
        strict_local=True,
    )
    console = _console()
    console.print(f"Config path: {config_path}", highlight=False, markup=False)
    console.print(
        f"Exists: {'yes' if config_path.exists() else 'no'}",
        highlight=False,
        markup=False,
    )
    console.print(
        _build_table(
            headers=["section", "key", "value", "source"],
            rows=_config_value_rows(config_path),
        )
    )
    return 0


def _run_config_create(*, use_local_config: bool, use_global_config: bool) -> int:
    config_path = _resolve_config_path(
        selected_path=None,
        use_local=use_local_config,
        use_global=use_global_config,
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
    _console().print(
        f"Created config file: {config_path}", highlight=False, markup=False
    )
    return 0


def _run_config_edit(*, use_local_config: bool, use_global_config: bool) -> int:
    config_path = _resolve_config_path(
        selected_path=None,
        use_local=use_local_config,
        use_global=use_global_config,
        require_exists=True,
        strict_local=True,
    )
    editor = _pick_editor()
    command = [*shlex.split(editor), str(config_path)]
    completed = subprocess.run(command, check=False)
    if completed.returncode != 0:
        raise ValueError(f"Editor exited with status {completed.returncode}")
    return 0


def _run_text(
    *,
    config: str | None,
    use_local_config: bool,
    use_global_config: bool,
    layout: str | None,
    mode: str | None,
    days: int | None,
    width: int,
    line_spacing: int,
    no_center: bool,
    header: bool,
) -> int:
    from piltext.ascii_art import display_readable_text

    config_path = _resolve_config_path(
        selected_path=config,
        use_local=use_local_config,
        use_global=use_global_config,
        require_exists=True,
        strict_local=True,
    )
    config_obj = Config(path=str(config_path))
    mode = _resolve_mode(config_obj, mode)
    layout = _resolve_layout(config_obj, layout)
    days = _resolve_days(config_obj, days)

    ticker = _build_ticker(config_obj, days)
    lines = _generate_lines(ticker, layout, mode)
    console = _console()

    if header:
        console.print(
            f"layout={layout} mode={mode} days={days}", highlight=False, markup=False
        )

    output = display_readable_text(
        lines,
        width=width,
        line_spacing=line_spacing,
        center=not no_center,
    )
    _render_text_output(output, console)
    return 0


def _run_image(
    *,
    config: str | None,
    use_local_config: bool,
    use_global_config: bool,
    layout: str | None,
    mode: str | None,
    days: int | None,
    output: str,
) -> int:
    config_path = _resolve_config_path(
        selected_path=config,
        use_local=use_local_config,
        use_global=use_global_config,
        require_exists=True,
        strict_local=True,
    )
    config_obj = Config(path=str(config_path))
    mode = _resolve_mode(config_obj, mode)
    layout = _resolve_layout(config_obj, layout)
    days = _resolve_days(config_obj, days)

    ticker = _build_ticker(config_obj, days)
    ticker.build(mode=mode, layout=layout)

    output_path = Path(output).expanduser()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    ticker.get_image().save(output_path, format="PNG")
    _console().print(f"Saved image to: {output_path}", highlight=False, markup=False)
    return 0


def _run_download(
    *,
    fontdir: str | None,
    url: str | None,
    part1: str | None,
    part2: str | None,
    font_name: str | None,
) -> int:
    from piltext import FontManager

    font_manager = FontManager(fontdirs=fontdir) if fontdir else FontManager()
    console = _console()

    if url and any([part1, part2, font_name]):
        raise ValueError("Use either --url or --part1/--part2/--font-name")

    if url:
        font_path = download_font_url(url, font_manager)
        console.print(
            f"Downloaded font from URL: {font_path}", highlight=False, markup=False
        )
    elif any([part1, part2, font_name]):
        if not all([part1, part2, font_name]):
            raise ValueError(
                "--part1, --part2 and --font-name must be provided together"
            )
        assert part1 is not None
        assert part2 is not None
        assert font_name is not None
        font_path = download_google_font(
            part1,
            part2,
            font_name,
            font_manager,
        )
        console.print(
            f"Downloaded Google Font: {font_path}", highlight=False, markup=False
        )
    else:
        downloaded = ensure_default_fonts(font_manager)
        if downloaded:
            console.print(
                "Downloaded default btcticker fonts:", highlight=False, markup=False
            )
            for font_name in downloaded:
                console.print(f"- {font_name}", highlight=False, markup=False)
        else:
            console.print(
                "All default btcticker fonts are already installed",
                highlight=False,
                markup=False,
            )

    directories = ", ".join(font_manager.list_font_directories())
    console.print(f"Font directories: {directories}", highlight=False, markup=False)
    return 0


@app.command(help="Render ticker text output for a layout")
def text(
    config: ConfigPathOption = None,
    use_local_config: LocalOption = False,
    use_global_config: GlobalOption = False,
    layout: Annotated[
        str | None, typer.Option("--layout", help="Layout to render")
    ] = None,
    mode: Annotated[
        str | None, typer.Option("--mode", help="Ticker mode to render")
    ] = None,
    days: Annotated[
        int | None, typer.Option("--days", help="Days ago for price history")
    ] = None,
    width: Annotated[int, typer.Option("--width", help="Output width")] = 80,
    line_spacing: Annotated[
        int,
        typer.Option("--line-spacing", help="Blank lines between text rows"),
    ] = 1,
    no_center: Annotated[
        bool,
        typer.Option("--no-center", help="Disable centered text output"),
    ] = False,
    header: Annotated[
        bool,
        typer.Option("--header", help="Show layout/mode header before output"),
    ] = False,
) -> int:
    return _run_text(
        config=config,
        use_local_config=use_local_config,
        use_global_config=use_global_config,
        layout=layout,
        mode=mode,
        days=days,
        width=width,
        line_spacing=line_spacing,
        no_center=no_center,
        header=header,
    )


@app.command(help="Render and save ticker as PNG image")
def image(
    config: ConfigPathOption = None,
    use_local_config: LocalOption = False,
    use_global_config: GlobalOption = False,
    layout: Annotated[
        str | None, typer.Option("--layout", help="Layout to render")
    ] = None,
    mode: Annotated[
        str | None, typer.Option("--mode", help="Ticker mode to render")
    ] = None,
    days: Annotated[
        int | None, typer.Option("--days", help="Days ago for price history")
    ] = None,
    output: Annotated[
        str,
        typer.Option(
            "--output",
            "-o",
            help="Output PNG file path (default: btcticker.png)",
        ),
    ] = "btcticker.png",
) -> int:
    return _run_image(
        config=config,
        use_local_config=use_local_config,
        use_global_config=use_global_config,
        layout=layout,
        mode=mode,
        days=days,
        output=output,
    )


@app.command(help="Download fonts to user font storage")
def download(
    fontdir: Annotated[
        str | None,
        typer.Option(
            "--fontdir",
            help="Custom font directory (defaults to piltext user directory)",
        ),
    ] = None,
    url: Annotated[
        str | None, typer.Option("--url", help="Direct URL to a font file")
    ] = None,
    part1: Annotated[
        str | None,
        typer.Option("--part1", help="Google Fonts category (e.g. ofl)"),
    ] = None,
    part2: Annotated[
        str | None,
        typer.Option("--part2", help="Google Fonts family (e.g. roboto)"),
    ] = None,
    font_name: Annotated[
        str | None,
        typer.Option("--font-name", help="Google Fonts file name"),
    ] = None,
) -> int:
    return _run_download(
        fontdir=fontdir,
        url=url,
        part1=part1,
        part2=part2,
        font_name=font_name,
    )


@app.command(help="List available layouts as a table")
def layouts() -> int:
    return _run_layouts()


@config_app.callback()
def config(
    ctx: typer.Context,
    use_local_config: LocalOption = False,
    use_global_config: GlobalOption = False,
) -> int | None:
    if ctx.invoked_subcommand is not None:
        return None
    return _run_config_show(
        use_local_config=use_local_config,
        use_global_config=use_global_config,
    )


@config_app.command("edit", help="Open selected config file in editor")
def config_edit(
    use_local_config: LocalOption = False,
    use_global_config: GlobalOption = False,
) -> int:
    return _run_config_edit(
        use_local_config=use_local_config,
        use_global_config=use_global_config,
    )


@config_app.command("create", help="Create selected config file with defaults")
def config_create(
    use_local_config: LocalOption = False,
    use_global_config: GlobalOption = False,
) -> int:
    return _run_config_create(
        use_local_config=use_local_config,
        use_global_config=use_global_config,
    )


def main(argv: list[str] | None = None) -> int:
    try:
        result = app(
            args=argv,
            prog_name="btcticker",
            standalone_mode=False,
        )
        return 0 if result is None else int(result)
    except click.exceptions.Exit as exc:
        raise SystemExit(exc.exit_code) from exc
    except click.ClickException as exc:
        exc.show(file=sys.stderr)
        raise SystemExit(exc.exit_code) from exc
    except SystemExit:
        raise
    except Exception as exc:
        _console(stderr=True).print(
            f"Error: {exc}",
            highlight=False,
            markup=False,
        )
        raise SystemExit(1) from exc


if __name__ == "__main__":
    raise SystemExit(main())
