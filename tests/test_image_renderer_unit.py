import importlib
import sys
import types
from types import SimpleNamespace


def _load_image_renderer_module(monkeypatch):
    calls = {}

    fake_pil = types.ModuleType("PIL")
    fake_image_module = types.ModuleType("PIL.Image")

    class StubImage:
        pass

    fake_image_module.Image = StubImage
    fake_pil.Image = fake_image_module
    monkeypatch.setitem(sys.modules, "PIL", fake_pil)
    monkeypatch.setitem(sys.modules, "PIL.Image", fake_image_module)

    fake_piltext = types.ModuleType("piltext")

    class StubFontManager:
        def __init__(self, **kwargs):
            calls["font_manager_kwargs"] = kwargs

    class StubImageDrawer:
        def __init__(self, *args, **kwargs):
            calls["image_drawer_kwargs"] = kwargs

    class StubTextGrid:
        def __init__(self, *args, **kwargs):
            return None

    fake_piltext.FontManager = StubFontManager
    fake_piltext.ImageDrawer = StubImageDrawer
    fake_piltext.TextGrid = StubTextGrid
    monkeypatch.setitem(sys.modules, "piltext", fake_piltext)

    fake_chart = types.ModuleType("btcticker.chart")
    fake_chart.makeCandle = lambda *args, **kwargs: None
    fake_chart.makeSpark = lambda *args, **kwargs: None
    monkeypatch.setitem(sys.modules, "btcticker.chart", fake_chart)

    sys.modules.pop("btcticker.render.image_renderer", None)
    module = importlib.import_module("btcticker.render.image_renderer")
    monkeypatch.setattr(
        module,
        "ensure_default_fonts",
        lambda font_manager: calls.setdefault("ensure_default_fonts", font_manager),
    )
    return module, calls


def test_image_renderer_passes_resolved_font_dir_to_font_manager(monkeypatch, tmp_path):
    image_renderer, calls = _load_image_renderer_module(monkeypatch)
    font_dir = tmp_path / "fonts"

    config = SimpleNamespace(
        fonts=SimpleNamespace(font_side="Roboto-Medium.ttf"),
        resolved_font_dir=font_dir,
    )

    renderer = image_renderer.ImageRenderer(config, 264, 176)

    assert calls["font_manager_kwargs"] == {
        "default_font_size": 20,
        "default_font_name": "Roboto-Medium.ttf",
        "fontdirs": str(font_dir),
    }
    assert calls["image_drawer_kwargs"]["font_manager"] is renderer.font_manager
    assert calls["ensure_default_fonts"] is renderer.font_manager


def test_image_renderer_omits_fontdirs_when_font_dir_is_unset(monkeypatch):
    image_renderer, calls = _load_image_renderer_module(monkeypatch)

    config = SimpleNamespace(
        fonts=SimpleNamespace(font_side="Roboto-Medium.ttf"),
        resolved_font_dir=None,
    )

    image_renderer.ImageRenderer(config, 264, 176)

    assert calls["font_manager_kwargs"] == {
        "default_font_size": 20,
        "default_font_name": "Roboto-Medium.ttf",
    }
