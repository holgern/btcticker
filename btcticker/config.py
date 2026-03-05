from configparser import ConfigParser

from pydantic import BaseModel, ValidationError


class ConfigurationException(ValueError):
    """Configuration Exception."""


class MainConfig(BaseModel):
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
    price_service: str = "coingecko"
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


class FontsConfig(BaseModel):
    font_buttom: str = "Audiowide-Regular.ttf"
    font_console: str = "ZenDots-Regular.ttf"
    font_big: str = "BigShouldersDisplay[wght].ttf"
    font_side: str = "Roboto[wdth,wght].ttf"
    font_side_size: int = 20
    font_top: str = "Quantico-Bold.ttf"
    font_top_size: int = 18
    font_fee: str = "Audiowide-Regular.ttf"
    font_fee_size: int = 14


class Config:
    def __init__(self, path="config.ini"):
        self.__config = ConfigParser()
        parsed_files = self.__config.read(path)
        if not parsed_files:
            raise ConfigurationException(f"Config file not found: {path}")

        self.main = self._load_section("Main", MainConfig)
        self.fonts = self._load_section("Fonts", FontsConfig)

    def _load_section(self, section_name, model):
        if section_name not in self.__config:
            raise ConfigurationException(f"Missing section: {section_name}")

        try:
            return model(**self.__config[section_name])
        except ValidationError as exc:
            raise ConfigurationException(
                f"Invalid configuration in section: {section_name}"
            ) from exc
