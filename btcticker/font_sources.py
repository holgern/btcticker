from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol, cast


class FontManagerLike(Protocol):
    def list_font_directories(self) -> list[str]: ...

    def get_full_path(self, font_name: str) -> str: ...

    def download_google_font(self, part1: str, part2: str, font_name: str) -> str: ...

    def download_font(self, font_url: str) -> str: ...


@dataclass(frozen=True)
class GoogleFontSpec:
    part1: str
    part2: str
    font_name: str


DEFAULT_FONT_SPECS = (
    GoogleFontSpec("ofl", "audiowide", "Audiowide-Regular.ttf"),
    GoogleFontSpec("ofl", "zendots", "ZenDots-Regular.ttf"),
    GoogleFontSpec("ofl", "bigshouldersdisplay", "BigShouldersDisplay[wght].ttf"),
    GoogleFontSpec("ofl", "roboto", "Roboto[wdth,wght].ttf"),
    GoogleFontSpec("ofl", "quantico", "Quantico-Bold.ttf"),
)


def _get_font_manager(font_manager: FontManagerLike | None = None) -> FontManagerLike:
    if font_manager is not None:
        return font_manager

    from piltext import FontManager

    return cast(FontManagerLike, FontManager())


def list_default_font_names() -> list[str]:
    return [spec.font_name for spec in DEFAULT_FONT_SPECS]


def get_user_font_directories(font_manager: FontManagerLike | None = None) -> list[str]:
    fm = _get_font_manager(font_manager)
    return fm.list_font_directories()


def ensure_default_fonts(font_manager: FontManagerLike | None = None) -> list[str]:
    fm = _get_font_manager(font_manager)
    downloaded: list[str] = []

    for spec in DEFAULT_FONT_SPECS:
        try:
            fm.get_full_path(spec.font_name)
        except FileNotFoundError:
            fm.download_google_font(spec.part1, spec.part2, spec.font_name)
            downloaded.append(spec.font_name)

    return downloaded


def download_google_font(
    part1: str,
    part2: str,
    font_name: str,
    font_manager: FontManagerLike | None = None,
) -> str:
    fm = _get_font_manager(font_manager)
    return fm.download_google_font(part1, part2, font_name)


def download_font_url(url: str, font_manager: FontManagerLike | None = None) -> str:
    fm = _get_font_manager(font_manager)
    return fm.download_font(url)
