import sys
import types
from types import SimpleNamespace
from typing import cast

import pytest

import btcticker.cli as cli


def _install_fake_piltext(monkeypatch, rendered_output="rendered"):
    call_data = {}

    class FakeFontManager:
        def __init__(self, fontdirs=None):
            self.fontdirs = [fontdirs] if isinstance(fontdirs, str) else fontdirs

        def list_font_directories(self):
            if self.fontdirs:
                return self.fontdirs
            return ["/tmp/piltext-fonts"]

    fake_piltext = types.ModuleType("piltext")
    fake_piltext.FontManager = FakeFontManager

    fake_ascii_art = types.ModuleType("piltext.ascii_art")

    def fake_display_readable_text(texts, width, line_spacing, center):
        call_data["texts"] = texts
        call_data["width"] = width
        call_data["line_spacing"] = line_spacing
        call_data["center"] = center
        return rendered_output

    fake_ascii_art.display_readable_text = fake_display_readable_text

    monkeypatch.setitem(sys.modules, "piltext", fake_piltext)
    monkeypatch.setitem(sys.modules, "piltext.ascii_art", fake_ascii_art)

    return call_data


def _install_fake_ticker(monkeypatch):
    class FakeTicker:
        def __init__(self, config, width, height, price_provider=None):
            self.width = width
            self.height = height
            self.price_provider = price_provider

        def set_days_ago(self, days_ago):
            self.days_ago = days_ago

        def refresh(self):
            return None

        def generate_fiat(self, mode):
            return [f"mode={mode}"]

    fake_ticker_module = types.ModuleType("btcticker.ticker")
    fake_ticker_module.Ticker = FakeTicker
    monkeypatch.setitem(sys.modules, "btcticker.ticker", fake_ticker_module)


def _install_fake_image_ticker(monkeypatch, call_data):
    class FakeImage:
        def save(self, path, format=None):
            call_data["saved_path"] = str(path)
            call_data["saved_format"] = format
            with open(path, "wb") as handle:
                handle.write(b"png")

    class FakeTicker:
        def __init__(self, config, width, height, price_provider=None):
            call_data["width"] = width
            call_data["height"] = height
            call_data["price_provider"] = price_provider

        def set_days_ago(self, days_ago):
            call_data["days_ago"] = days_ago

        def refresh(self):
            call_data["refreshed"] = True

        def build(self, mode="fiat", layout="all", mirror=True):
            call_data["build"] = {
                "mode": mode,
                "layout": layout,
                "mirror": mirror,
            }

        def get_image(self):
            return FakeImage()

    fake_ticker_module = types.ModuleType("btcticker.ticker")
    fake_ticker_module.Ticker = FakeTicker
    monkeypatch.setitem(sys.modules, "btcticker.ticker", fake_ticker_module)


def test_text_command_uses_config_selected_layout(monkeypatch, capsys, tmp_path):
    call_data = _install_fake_piltext(monkeypatch, rendered_output="text output")
    monkeypatch.chdir(tmp_path)
    (tmp_path / "my-config.ini").write_text("[Main]\n\n[Fonts]\n", encoding="utf-8")

    ticker_data = {}
    provider = object()

    class FakeTicker:
        def __init__(self, config, width, height, price_provider=None):
            ticker_data["width"] = width
            ticker_data["height"] = height
            ticker_data["price_provider"] = price_provider

        def set_days_ago(self, days_ago):
            ticker_data["days_ago"] = days_ago

        def refresh(self):
            ticker_data["refreshed"] = True

        def generate_fiat(self, mode):
            ticker_data["mode"] = mode
            return ["line a", "line b"]

    fake_ticker_module = types.ModuleType("btcticker.ticker")
    fake_ticker_module.Ticker = FakeTicker
    monkeypatch.setitem(sys.modules, "btcticker.ticker", fake_ticker_module)

    class FakeConfig:
        def __init__(self, path):
            assert path == "my-config.ini"
            self.main = SimpleNamespace(
                mode_list="fiat,usd",
                start_mode_ind=1,
                layout_list="all,fiat",
                start_layout_ind=1,
                days_list="1,3,7",
                start_days_ind=2,
                epd_type="2in7_V2",
                orientation=0,
            )

    monkeypatch.setattr(cli, "Config", FakeConfig)
    monkeypatch.setattr(cli, "build_price_provider", lambda config, days_ago: provider)

    exit_code = cli.main(["text", "--config", "my-config.ini", "--line-spacing", "0"])

    assert exit_code == 0
    assert ticker_data == {
        "width": 264,
        "height": 176,
        "price_provider": provider,
        "days_ago": 7,
        "refreshed": True,
        "mode": "usd",
    }
    assert call_data == {
        "texts": ["line a", "line b"],
        "width": 80,
        "line_spacing": 0,
        "center": True,
    }
    assert capsys.readouterr().out.strip() == "text output"


def test_text_command_accepts_root_config_option(monkeypatch, capsys, tmp_path):
    call_data = _install_fake_piltext(monkeypatch, rendered_output="text output")
    monkeypatch.chdir(tmp_path)
    config_path = tmp_path / "my-config.ini"
    config_path.write_text("[Main]\n\n[Fonts]\n", encoding="utf-8")

    ticker_data = {}
    provider = object()

    class FakeTicker:
        def __init__(self, config, width, height, price_provider=None):
            ticker_data["width"] = width
            ticker_data["height"] = height
            ticker_data["price_provider"] = price_provider

        def set_days_ago(self, days_ago):
            ticker_data["days_ago"] = days_ago

        def refresh(self):
            ticker_data["refreshed"] = True

        def generate_fiat(self, mode):
            ticker_data["mode"] = mode
            return ["line a", "line b"]

    fake_ticker_module = types.ModuleType("btcticker.ticker")
    fake_ticker_module.Ticker = FakeTicker
    monkeypatch.setitem(sys.modules, "btcticker.ticker", fake_ticker_module)

    class FakeConfig:
        def __init__(self, path):
            assert path == str(config_path)
            self.main = SimpleNamespace(
                mode_list="fiat,usd",
                start_mode_ind=1,
                layout_list="all,fiat",
                start_layout_ind=1,
                days_list="1,3,7",
                start_days_ind=2,
                epd_type="2in7_V2",
                orientation=0,
            )

    monkeypatch.setattr(cli, "Config", FakeConfig)
    monkeypatch.setattr(cli, "build_price_provider", lambda config, days_ago: provider)

    exit_code = cli.main(["--config", str(config_path), "text", "--line-spacing", "0"])

    assert exit_code == 0
    assert ticker_data == {
        "width": 264,
        "height": 176,
        "price_provider": provider,
        "days_ago": 7,
        "refreshed": True,
        "mode": "usd",
    }
    assert call_data == {
        "texts": ["line a", "line b"],
        "width": 80,
        "line_spacing": 0,
        "center": True,
    }
    assert capsys.readouterr().out.strip() == "text output"


def test_download_command_downloads_default_set(monkeypatch, capsys):
    _install_fake_piltext(monkeypatch)
    monkeypatch.setattr(cli, "ensure_default_fonts", lambda _: ["A.ttf", "B.ttf"])

    exit_code = cli.main(["download"])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "Downloaded default btcticker fonts" in output
    assert "- A.ttf" in output
    assert "- B.ttf" in output


def test_download_command_accepts_root_config_option(monkeypatch, capsys):
    _install_fake_piltext(monkeypatch)
    monkeypatch.setattr(cli, "ensure_default_fonts", lambda _: ["A.ttf"])

    exit_code = cli.main(["--config", "missing.ini", "download"])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "Downloaded default btcticker fonts" in output
    assert "- A.ttf" in output


def test_download_command_downloads_custom_google_font(monkeypatch, capsys):
    _install_fake_piltext(monkeypatch)
    monkeypatch.setattr(
        cli,
        "download_google_font",
        lambda part1, part2, font_name, _: f"/tmp/{part1}/{part2}/{font_name}",
    )

    exit_code = cli.main(
        [
            "download",
            "--part1",
            "ofl",
            "--part2",
            "roboto",
            "--font-name",
            "Roboto[wdth,wght].ttf",
        ]
    )

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "Downloaded Google Font" in output
    assert "Roboto[wdth,wght].ttf" in output


def test_download_command_rejects_mixed_url_and_google_options(monkeypatch):
    _install_fake_piltext(monkeypatch)

    with pytest.raises(SystemExit) as exc:
        cli.main(
            [
                "download",
                "--url",
                "https://example.org/font.ttf",
                "--part1",
                "ofl",
            ]
        )

    assert exc.value.code == 1


def test_layouts_command_prints_layout_table(capsys):
    exit_code = cli.main(["layouts"])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert "layout" in output
    assert "generator" in output
    assert "default_pos" in output
    assert "fiatheight" in output
    assert "generate_fiat_height" in output
    assert "draw_fiat_height" in output
    assert "big_two_rows" in output
    assert "alias(height)" in output
    assert "fiat,height,satfiat,moscowtime,usd,newblock" in output


def test_text_command_uses_local_config_by_default(monkeypatch, tmp_path):
    _install_fake_piltext(monkeypatch)
    _install_fake_ticker(monkeypatch)
    monkeypatch.setattr(cli, "build_price_provider", lambda config, days_ago: object())
    monkeypatch.chdir(tmp_path)
    local_config = tmp_path / "config.ini"
    local_config.write_text("[Main]\n\n[Fonts]\n", encoding="utf-8")

    seen = {}

    class FakeConfig:
        def __init__(self, path):
            seen["path"] = path
            self.main = SimpleNamespace(epd_type="2in7_V2", orientation=0)

    monkeypatch.setattr(cli, "Config", FakeConfig)

    exit_code = cli.main(["text", "--layout", "fiat", "--mode", "fiat", "--days", "1"])

    assert exit_code == 0
    assert seen["path"] == str(local_config)


def test_text_command_falls_back_to_global_config(monkeypatch, tmp_path):
    _install_fake_piltext(monkeypatch)
    _install_fake_ticker(monkeypatch)
    monkeypatch.setattr(cli, "build_price_provider", lambda config, days_ago: object())
    monkeypatch.chdir(tmp_path)
    global_config = tmp_path / ".config" / "btcticker" / "config.ini"
    global_config.parent.mkdir(parents=True)
    global_config.write_text("[Main]\n\n[Fonts]\n", encoding="utf-8")
    monkeypatch.setattr(cli, "_get_global_config_path", lambda: global_config)

    seen = {}

    class FakeConfig:
        def __init__(self, path):
            seen["path"] = path
            self.main = SimpleNamespace(epd_type="2in7_V2", orientation=0)

    monkeypatch.setattr(cli, "Config", FakeConfig)

    exit_code = cli.main(["text", "--layout", "fiat", "--mode", "fiat", "--days", "1"])

    assert exit_code == 0
    assert seen["path"] == str(global_config)


def test_text_command_local_flag_fails_when_missing(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)

    with pytest.raises(SystemExit) as exc:
        cli.main(["text", "--local", "--layout", "fiat", "--mode", "fiat"])

    assert exc.value.code == 1
    assert "Local config file not found" in capsys.readouterr().err


def test_config_command_global_scope_shows_path(monkeypatch, tmp_path, capsys):
    global_config = tmp_path / ".config" / "btcticker" / "config.ini"
    monkeypatch.setattr(cli, "_get_global_config_path", lambda: global_config)

    exit_code = cli.main(["config", "--global"])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert f"Config path: {global_config}" in output
    assert "section" in output
    assert "source" in output


def test_config_command_uses_root_config_option(tmp_path, capsys):
    config_path = tmp_path / "custom.ini"

    exit_code = cli.main(["--config", str(config_path), "config"])

    assert exit_code == 0
    output = capsys.readouterr().out
    assert f"Config path: {config_path}" in output


def test_config_command_local_scope_fails_when_missing(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)

    with pytest.raises(SystemExit) as exc:
        cli.main(["config", "--local"])

    assert exc.value.code == 1
    assert "Local config file not found" in capsys.readouterr().err


def test_config_create_fails_if_file_exists(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    local_config = tmp_path / "config.ini"
    local_config.write_text("[Main]\n\n[Fonts]\n", encoding="utf-8")

    with pytest.raises(SystemExit) as exc:
        cli.main(["config", "create", "--local"])

    assert exc.value.code == 1
    assert "Config file already exists" in capsys.readouterr().err


def test_config_create_global_writes_default_file(monkeypatch, tmp_path):
    global_config = tmp_path / ".config" / "btcticker" / "config.ini"
    monkeypatch.setattr(cli, "_get_global_config_path", lambda: global_config)

    exit_code = cli.main(["config", "create", "--global"])

    assert exit_code == 0
    content = global_config.read_text(encoding="utf-8")
    assert "[Main]" in content
    assert "[Fonts]" in content
    assert "price_service" not in content


def test_config_edit_uses_default_editor(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    local_config = tmp_path / "config.ini"
    local_config.write_text("[Main]\n\n[Fonts]\n", encoding="utf-8")
    monkeypatch.setenv("VISUAL", "")
    monkeypatch.setenv("EDITOR", "fake-editor --wait")

    calls = {}

    def fake_run(command, check):
        calls["command"] = command
        calls["check"] = check
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    exit_code = cli.main(["config", "edit", "--local"])

    assert exit_code == 0
    assert calls["check"] is False
    assert calls["command"] == ["fake-editor", "--wait", str(local_config)]


def test_config_edit_accepts_root_config_option(monkeypatch, tmp_path):
    config_path = tmp_path / "custom.ini"
    config_path.write_text("[Main]\n\n[Fonts]\n", encoding="utf-8")
    monkeypatch.setenv("VISUAL", "")
    monkeypatch.setenv("EDITOR", "fake-editor --wait")

    calls = {}

    def fake_run(command, check):
        calls["command"] = command
        calls["check"] = check
        return SimpleNamespace(returncode=0)

    monkeypatch.setattr(cli.subprocess, "run", fake_run)

    exit_code = cli.main(["--config", str(config_path), "config", "edit"])

    assert exit_code == 0
    assert calls["check"] is False
    assert calls["command"] == ["fake-editor", "--wait", str(config_path)]


def test_root_and_command_config_options_cannot_be_combined(
    monkeypatch, tmp_path, capsys
):
    _install_fake_piltext(monkeypatch)
    monkeypatch.chdir(tmp_path)
    config_path = tmp_path / "custom.ini"
    config_path.write_text("[Main]\n\n[Fonts]\n", encoding="utf-8")

    with pytest.raises(SystemExit) as exc:
        cli.main(
            [
                "--config",
                str(config_path),
                "text",
                "--local",
                "--layout",
                "fiat",
                "--mode",
                "fiat",
            ]
        )

    assert exc.value.code == 1
    assert "Use only one of --config, --local, or --global" in capsys.readouterr().err


def test_image_command_writes_default_output(monkeypatch, tmp_path, capsys):
    monkeypatch.chdir(tmp_path)
    local_config = tmp_path / "config.ini"
    local_config.write_text("[Main]\n\n[Fonts]\n", encoding="utf-8")
    call_data = {}
    _install_fake_image_ticker(monkeypatch, call_data)

    class FakeConfig:
        def __init__(self, path):
            assert path == str(local_config)
            self.main = SimpleNamespace(
                mode_list="fiat,usd",
                start_mode_ind=0,
                layout_list="all,fiat",
                start_layout_ind=0,
                days_list="1,3,7",
                start_days_ind=1,
                epd_type="2in7_V2",
                orientation=0,
            )

    monkeypatch.setattr(cli, "Config", FakeConfig)
    monkeypatch.setattr(
        cli, "build_price_provider", lambda config, days_ago: "provider"
    )

    exit_code = cli.main(["image"])

    assert exit_code == 0
    assert call_data["days_ago"] == 3
    assert call_data["build"] == {"mode": "fiat", "layout": "all", "mirror": True}
    assert call_data["saved_format"] == "PNG"
    assert call_data["saved_path"] == "btcticker.png"
    assert (tmp_path / "btcticker.png").exists()
    assert "Saved image to: btcticker.png" in capsys.readouterr().out


def test_image_command_respects_custom_output_and_values(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)
    local_config = tmp_path / "config.ini"
    local_config.write_text("[Main]\n\n[Fonts]\n", encoding="utf-8")
    call_data = {}
    _install_fake_image_ticker(monkeypatch, call_data)

    class FakeConfig:
        def __init__(self, path):
            assert path == str(local_config)
            self.main = SimpleNamespace(
                mode_list="fiat,usd",
                start_mode_ind=0,
                layout_list="all,fiat",
                start_layout_ind=0,
                days_list="1,3,7",
                start_days_ind=0,
                epd_type="2in7_V2",
                orientation=0,
            )

    monkeypatch.setattr(cli, "Config", FakeConfig)
    monkeypatch.setattr(
        cli, "build_price_provider", lambda config, days_ago: "provider"
    )
    output_path = tmp_path / "out" / "custom-name"

    exit_code = cli.main(
        [
            "image",
            "--layout",
            "fiat",
            "--mode",
            "usd",
            "--days",
            "7",
            "--output",
            str(output_path),
        ]
    )

    assert exit_code == 0
    assert call_data["days_ago"] == 7
    assert call_data["build"] == {"mode": "usd", "layout": "fiat", "mirror": True}
    assert call_data["saved_path"] == str(output_path)
    assert output_path.exists()


def test_build_price_provider_uses_pyccxt_defaults(monkeypatch):
    calls = {}

    class FakeProvider:
        def __init__(self, **kwargs):
            calls.update(kwargs)

    monkeypatch.setattr(cli, "_resolve_provider_name", lambda config: "pyccxt")
    monkeypatch.setattr(
        "btcticker.providers.PyCCXTPriceProvider",
        FakeProvider,
    )

    config = SimpleNamespace(
        main=SimpleNamespace(
            fiat="eur",
            symbol="",
            usd_symbol="BTC/USD",
            exchange="kraken",
            interval="1h",
            enable_ohlc=True,
            ccxt_timeout=30000,
            price_refresh_seconds=10,
        )
    )

    cli.build_price_provider(cast(cli.Config, config), 3)

    assert calls == {
        "exchange_name": "kraken",
        "fiat_symbol": "BTC/EUR",
        "usd_symbol": "BTC/USD",
        "interval": "1h",
        "days_ago": 3,
        "enable_ohlc": True,
        "timeout_ms": 30000,
        "min_refresh_time": 10,
    }


def test_resolve_provider_name_fails_for_legacy_price_service(tmp_path):
    config_path = tmp_path / "config.ini"
    config_path.write_text(
        "[Main]\nprice_service = coingecko\n\n[Fonts]\n",
        encoding="utf-8",
    )
    config = cli.Config(path=str(config_path))

    with pytest.raises(ValueError, match="price_service"):
        cli._resolve_provider_name(config)


def test_build_price_provider_rejects_unknown_provider():
    config = SimpleNamespace(
        has_option=lambda *_args: False,
        main=SimpleNamespace(price_provider="legacy"),
    )

    with pytest.raises(ValueError, match="Unknown price provider"):
        cli.build_price_provider(cast(cli.Config, config), 1)
