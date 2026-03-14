from email.message import Message
from urllib.error import HTTPError

import pytest

import btcticker.font_sources as font_sources
from btcticker.font_sources import (
    DEFAULT_FONT_SPECS,
    download_font_url,
    download_google_font,
    ensure_default_fonts,
)


class FakeFontManager:
    def __init__(self, font_dir, missing_fonts=None):
        self.font_dir = str(font_dir)
        self.missing_fonts = set(missing_fonts or [])

    def list_font_directories(self):
        return [self.font_dir]

    def get_full_path(self, font_name):
        if font_name in self.missing_fonts:
            raise FileNotFoundError(font_name)
        return f"{self.font_dir}/{font_name}"


class FakeResponse:
    def __init__(self, content=b"font-bytes"):
        self.content = content

    def read(self):
        return self.content

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_ensure_default_fonts_downloads_missing_entries(monkeypatch, tmp_path):
    missing = {
        DEFAULT_FONT_SPECS[0].font_name,
        DEFAULT_FONT_SPECS[-1].font_name,
    }
    fm = FakeFontManager(tmp_path, missing_fonts=missing)

    def fake_urlopen(url):
        font_name = url.rsplit("/", 1)[-1]
        filename = font_name.replace("%5B", "[").replace("%5D", "]").replace("%2C", ",")
        fm.missing_fonts.discard(filename)
        return FakeResponse()

    monkeypatch.setattr(font_sources, "urlopen", fake_urlopen)

    downloaded = ensure_default_fonts(fm)

    assert downloaded == [
        DEFAULT_FONT_SPECS[0].font_name,
        DEFAULT_FONT_SPECS[-1].font_name,
    ]
    assert (tmp_path / DEFAULT_FONT_SPECS[0].font_name).exists()
    assert (tmp_path / DEFAULT_FONT_SPECS[-1].font_name).exists()


def test_ensure_default_fonts_skips_existing_fonts(monkeypatch, tmp_path):
    fm = FakeFontManager(tmp_path, missing_fonts=[])

    def fail_urlopen(_url):
        raise AssertionError("urlopen should not be called")

    monkeypatch.setattr(font_sources, "urlopen", fail_urlopen)

    downloaded = ensure_default_fonts(fm)

    assert downloaded == []


def test_download_google_font_saves_font_and_returns_full_path(monkeypatch, tmp_path):
    fm = FakeFontManager(tmp_path, missing_fonts={"Roboto[wdth,wght].ttf"})

    def fake_urlopen(url):
        assert "raw.githubusercontent.com/google/fonts/main/ofl/roboto/" in url
        fm.missing_fonts.discard("Roboto[wdth,wght].ttf")
        return FakeResponse(b"roboto")

    monkeypatch.setattr(font_sources, "urlopen", fake_urlopen)

    full_path = download_google_font("ofl", "roboto", "Roboto[wdth,wght].ttf", fm)

    assert full_path == str(tmp_path / "Roboto[wdth,wght].ttf")
    assert (tmp_path / "Roboto[wdth,wght].ttf").read_bytes() == b"roboto"


def test_download_font_url_raises_for_rate_limit(monkeypatch, tmp_path):
    fm = FakeFontManager(tmp_path, missing_fonts={"font.ttf"})

    def fake_urlopen(url):
        raise HTTPError(url, 429, "Too Many Requests", hdrs=Message(), fp=None)

    monkeypatch.setattr(font_sources, "urlopen", fake_urlopen)

    with pytest.raises(ValueError, match="rate-limited"):
        download_font_url("https://example.com/font.ttf", fm)
