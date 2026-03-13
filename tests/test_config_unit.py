import textwrap

import pytest

from btcticker.config import Config, ConfigurationException


def test_config_reads_values_from_ini(tmp_path):
    config_path = tmp_path / "config.ini"
    config_path.write_text(
        textwrap.dedent(
            """
            [Main]
            fiat = usd
            show_best_fees = false
            start_mode_ind = 2

            [Fonts]
            font_buttom = Demo-Regular.ttf
            font_side_size = 22
            """
        ),
        encoding="utf-8",
    )

    config = Config(path=str(config_path))

    assert config.main.fiat == "usd"
    assert config.main.show_best_fees is False
    assert config.main.start_mode_ind == 2
    assert config.fonts.font_buttom == "Demo-Regular.ttf"
    assert config.fonts.font_side_size == 22


def test_config_raises_when_file_is_missing(tmp_path):
    missing_path = tmp_path / "does-not-exist.ini"

    with pytest.raises(ConfigurationException, match="Config file not found"):
        Config(path=str(missing_path))


def test_config_raises_when_required_section_is_missing(tmp_path):
    config_path = tmp_path / "config.ini"
    config_path.write_text(
        textwrap.dedent(
            """
            [Main]
            fiat = usd
            """
        ),
        encoding="utf-8",
    )

    with pytest.raises(ConfigurationException, match="Missing section: Fonts"):
        Config(path=str(config_path))


def test_config_reads_new_provider_fields_and_normalizes_values(tmp_path):
    config_path = tmp_path / "config.ini"
    config_path.write_text(
        textwrap.dedent(
            """
            [Main]
            fiat = usd
            price_provider = PYCCXT
            exchange = KRAKEN
            symbol = btc/usd
            usd_symbol = btc/usdt
            ccxt_timeout = 45000
            price_refresh_seconds = 12

            [Fonts]
            """
        ),
        encoding="utf-8",
    )

    config = Config(path=str(config_path))

    assert config.main.price_provider == "pyccxt"
    assert config.main.exchange == "kraken"
    assert config.main.symbol == "BTC/USD"
    assert config.main.usd_symbol == "BTC/USDT"
    assert config.main.ccxt_timeout == 45000
    assert config.main.price_refresh_seconds == 12
