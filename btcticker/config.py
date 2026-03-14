from __future__ import annotations
from configparser import ConfigParser
from pathlib import Path
from typing import Any, TypeVar

from pydantic import BaseModel, ConfigDict, ValidationError, field_validator


class ConfigurationException(ValueError):
    """Configuration Exception."""


class MainConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    fiat: str = "eur"
    mode_list: str = "fiat,height,satfiat,moscowtime,usd"
    start_mode_ind: int = 0
    mode_shifting: bool = False
    days_list: str = "1,3,7"
    start_days_ind: int = 0
    days_shifting: bool = False
    layout_list: str = "all,fiat,fiatheight,big_one_row,one_number,mempool,ohlc"
    start_layout_ind: int = 0
    layout_shifting: bool = False
    loglevel: str = "WARNING"
    orientation: int = 0
    interval: str = "1h"
    price_provider: str = "pyccxt"
    exchange: str = "kraken"
    symbol: str = ""
    usd_symbol: str = "BTC/USD"
    ccxt_timeout: int = 30000
    price_refresh_seconds: int = 10
    enable_ohlc: bool = True
    inverted: bool = False
    show_block_height: bool = False
    update_on_new_block: bool = True
    mempool_api_url: str = (
        "https://mempool.space/api/,https://mempool.emzy.de/api/,"
        "https://mempool.bitcoin-21.org/api/"
    )
    epd_type: str = "2in7_V2"
    show_best_fees: bool = True
    show_block_time: bool = True

    @field_validator("fiat", "price_provider", "exchange", mode="before")
    @classmethod
    def _normalize_lowercase(cls, value: Any) -> Any:
        if value is None:
            return value
        return str(value).strip().lower()

    @field_validator("symbol", "usd_symbol", mode="before")
    @classmethod
    def _normalize_symbol(cls, value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip().upper()


class FontsConfig(BaseModel):
    model_config = ConfigDict(extra="ignore")

    font_dir: str = ""
    font_buttom: str = "Audiowide-Regular.ttf"
    font_console: str = "ZenDots-Regular.ttf"
    font_big: str = "BigShouldersDisplay[wght].ttf"
    font_side: str = "Roboto[wdth,wght].ttf"
    font_side_size: int = 20
    font_top: str = "Quantico-Bold.ttf"
    font_top_size: int = 18
    font_fee: str = "Audiowide-Regular.ttf"
    font_fee_size: int = 14

    @field_validator("font_dir", mode="before")
    @classmethod
    def _normalize_font_dir(cls, value: Any) -> str:
        if value is None:
            return ""
        return str(value).strip()


ConfigSection = TypeVar("ConfigSection", bound=BaseModel)


class Config:
    def __init__(self, path: str = "config.ini") -> None:
        self.path = Path(path).expanduser()
        self.__config = ConfigParser()
        parsed_files = self.__config.read(self.path)
        if not parsed_files:
            raise ConfigurationException(f"Config file not found: {path}")

        self.path = self.path.resolve()

        self.main = self._load_section("Main", MainConfig)
        self.fonts = self._load_section("Fonts", FontsConfig)

    def has_option(self, section_name: str, option_name: str) -> bool:
        return self.__config.has_option(section_name, option_name)

    @property
    def resolved_font_dir(self) -> Path | None:
        raw_font_dir = self.fonts.font_dir.strip()
        if not raw_font_dir:
            return None
        font_dir = Path(raw_font_dir).expanduser()
        if font_dir.is_absolute():
            return font_dir
        return (self.path.parent / font_dir).resolve()

    def _load_section(
        self,
        section_name: str,
        model: type[ConfigSection],
    ) -> ConfigSection:
        if section_name not in self.__config:
            raise ConfigurationException(f"Missing section: {section_name}")

        try:
            return model(**self.__config[section_name])
        except ValidationError as exc:
            raise ConfigurationException(
                f"Invalid configuration in section: {section_name}"
            ) from exc
