import sys
import types
from types import SimpleNamespace

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


def test_text_command_uses_config_selected_layout(monkeypatch, capsys):
    call_data = _install_fake_piltext(monkeypatch, rendered_output="text output")

    ticker_data = {}

    class FakeTicker:
        def __init__(self, config, width, height):
            ticker_data["width"] = width
            ticker_data["height"] = height

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

    exit_code = cli.main(["text", "--config", "my-config.ini", "--line-spacing", "0"])

    assert exit_code == 0
    assert ticker_data == {
        "width": 264,
        "height": 176,
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
