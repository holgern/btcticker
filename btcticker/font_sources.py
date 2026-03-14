from dataclasses import dataclass
from pathlib import Path
from typing import Protocol, cast
from urllib.error import HTTPError, URLError
from urllib.parse import quote, unquote, urlsplit
from urllib.request import urlopen


class FontManagerLike(Protocol):
    def list_font_directories(self) -> list[str]: ...

    def get_full_path(self, font_name: str) -> str: ...


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


def _font_name_from_url(url: str) -> str:
    font_name = unquote(Path(urlsplit(url).path).name)
    if not font_name:
        raise ValueError(f"Could not determine font file name from URL: {url}")
    return font_name


def _primary_font_directory(font_manager: FontManagerLike) -> Path:
    directories = font_manager.list_font_directories()
    if not directories:
        raise ValueError("No font directories configured")
    return Path(directories[0]).expanduser()


def _download_to_font_directory(
    font_url: str,
    font_manager: FontManagerLike,
    *,
    expected_font_name: str | None = None,
) -> str:
    font_name = expected_font_name or _font_name_from_url(font_url)
    target_dir = _primary_font_directory(font_manager)
    target_dir.mkdir(parents=True, exist_ok=True)
    target_path = target_dir / font_name

    if not target_path.exists():
        try:
            with urlopen(font_url) as response, target_path.open("wb") as font_file:
                font_file.write(response.read())
        except HTTPError as exc:
            if exc.code == 404:
                raise ValueError(f"Font file not found at URL: {font_url}") from exc
            if exc.code == 429:
                raise ValueError(
                    "Font download was rate-limited by the remote server. "
                    "Please try again later."
                ) from exc
            raise ValueError(
                f"Font download failed with HTTP status {exc.code}: {font_url}"
            ) from exc
        except URLError as exc:
            raise ValueError(
                "Failed to load font. This may be due to a lack of internet connection."
            ) from exc

    try:
        return font_manager.get_full_path(font_name)
    except FileNotFoundError as exc:
        raise ValueError(
            f"Downloaded font could not be found after download: {font_name}"
        ) from exc


def _google_font_url(part1: str, part2: str, font_name: str) -> str:
    return (
        "https://raw.githubusercontent.com/google/fonts/main/"
        f"{quote(part1)}/{quote(part2)}/{quote(font_name)}"
    )


def ensure_default_fonts(font_manager: FontManagerLike | None = None) -> list[str]:
    fm = _get_font_manager(font_manager)
    downloaded: list[str] = []

    for spec in DEFAULT_FONT_SPECS:
        try:
            fm.get_full_path(spec.font_name)
        except FileNotFoundError:
            _download_to_font_directory(
                _google_font_url(spec.part1, spec.part2, spec.font_name),
                fm,
                expected_font_name=spec.font_name,
            )
            downloaded.append(spec.font_name)

    return downloaded


def download_google_font(
    part1: str,
    part2: str,
    font_name: str,
    font_manager: FontManagerLike | None = None,
) -> str:
    fm = _get_font_manager(font_manager)
    return _download_to_font_directory(
        _google_font_url(part1, part2, font_name),
        fm,
        expected_font_name=font_name,
    )


def download_font_url(url: str, font_manager: FontManagerLike | None = None) -> str:
    fm = _get_font_manager(font_manager)
    return _download_to_font_directory(url, fm)
