from btcticker.font_sources import DEFAULT_FONT_SPECS, ensure_default_fonts


class FakeFontManager:
    def __init__(self, missing_fonts=None):
        self.missing_fonts = set(missing_fonts or [])
        self.download_calls = []

    def get_full_path(self, font_name):
        if font_name in self.missing_fonts:
            raise FileNotFoundError(font_name)
        return f"/tmp/{font_name}"

    def download_google_font(self, part1, part2, font_name):
        self.download_calls.append((part1, part2, font_name))
        return f"/tmp/{font_name}"


def test_ensure_default_fonts_downloads_missing_entries():
    missing = {
        DEFAULT_FONT_SPECS[0].font_name,
        DEFAULT_FONT_SPECS[-1].font_name,
    }
    fm = FakeFontManager(missing_fonts=missing)

    downloaded = ensure_default_fonts(fm)

    assert downloaded == [
        DEFAULT_FONT_SPECS[0].font_name,
        DEFAULT_FONT_SPECS[-1].font_name,
    ]
    assert fm.download_calls == [
        (
            DEFAULT_FONT_SPECS[0].part1,
            DEFAULT_FONT_SPECS[0].part2,
            DEFAULT_FONT_SPECS[0].font_name,
        ),
        (
            DEFAULT_FONT_SPECS[-1].part1,
            DEFAULT_FONT_SPECS[-1].part2,
            DEFAULT_FONT_SPECS[-1].font_name,
        ),
    ]


def test_ensure_default_fonts_skips_existing_fonts():
    fm = FakeFontManager(missing_fonts=[])

    downloaded = ensure_default_fonts(fm)

    assert downloaded == []
    assert fm.download_calls == []
