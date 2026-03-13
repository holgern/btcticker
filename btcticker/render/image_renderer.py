from __future__ import annotations

from piltext import FontManager, ImageDrawer, TextGrid

from btcticker.chart import makeCandle, makeSpark
from btcticker.font_sources import ensure_default_fonts


class ImageRenderer:
    def __init__(
        self,
        config,
        width,
        height,
        *,
        font_manager=None,
        image=None,
    ) -> None:
        self.config = config
        self.width = width
        self.height = height

        if font_manager is None:
            self.font_manager = FontManager(
                default_font_size=20,
                default_font_name=config.fonts.font_side,
            )
            ensure_default_fonts(self.font_manager)
        else:
            self.font_manager = font_manager

        self.image = image or ImageDrawer(width, height, font_manager=self.font_manager)

    def change_size(self, width, height):
        self.width = width
        self.height = height
        self.image.change_size(width, height)

    def initialize(self):
        self.image.initialize()
        draw = getattr(self.image, "draw", None)
        if draw is not None and hasattr(draw, "ink"):
            draw.ink = 0

    def finalize(self, *, mirror=True, orientation=0, inverted=False):
        self.image.finalize(
            mirror=mirror,
            orientation=orientation,
            inverted=inverted,
        )

    def show(self):
        self.image.show()

    def draw_message(self, message):
        y = 0
        for line in message.split("\n"):
            _, height, _ = self.image.draw_text(
                line,
                (0, y),
                end=(self.width - 1, self.height - 1),
                font_name=self.config.fonts.font_buttom,
                anchor="lt",
            )
            y += height

    def draw_all(self, line_str, pricestack, mode):
        if mode == "newblock":
            grid = TextGrid(8, 4, self.image, margin_x=1, margin_y=1)
            grid.merge((0, 0), (1, 3))
            grid.merge((2, 0), (2, 3))
            grid.merge((3, 0), (3, 3))
            grid.merge((4, 0), (4, 3))
            grid.merge((5, 0), (7, 3))
            grid.set_text(0, line_str[0], font_name=self.config.fonts.font_console)
            grid.set_text(1, line_str[1], font_name=self.config.fonts.font_fee)
            grid.set_text(2, line_str[2], font_name=self.config.fonts.font_side)
            grid.set_text(3, line_str[3], font_name=self.config.fonts.font_side)
            grid.set_text(
                4, line_str[4], font_name=self.config.fonts.font_buttom, anchor="rs"
            )
            return

        grid = TextGrid(21, 6, self.image, margin_x=1, margin_y=1)
        grid.merge((0, 0), (2, 5))
        grid.merge((3, 0), (4, 5))
        grid.merge((5, 2), (10, 5))
        grid.merge((5, 0), (6, 1))
        grid.merge((7, 0), (8, 1))
        grid.merge((9, 0), (10, 1))
        grid.merge((11, 0), (12, 1))
        grid.merge((11, 3), (12, 5))
        grid.merge((13, 0), (20, 5))
        start_img, end_img = grid.get_grid((5, 2), convert_to_pixel=True)
        spark_image = makeSpark(
            pricestack,
            figsize_pixel=(end_img[0] - start_img[0], end_img[1] - start_img[1]),
        )

        grid.set_text((0, 0), line_str[0], font_name=self.config.fonts.font_top)
        grid.set_text((3, 0), line_str[1], font_name=self.config.fonts.font_fee)
        grid.paste_image((5, 2), spark_image, anchor="rs")
        grid.set_text((5, 0), line_str[2], font_name=self.config.fonts.font_side)
        grid.set_text((7, 0), line_str[3], font_name=self.config.fonts.font_side)
        grid.set_text((9, 0), line_str[4], font_name=self.config.fonts.font_side)
        grid.set_text((11, 0), line_str[5], font_name=self.config.fonts.font_side)
        grid.set_text((11, 3), line_str[6], font_name=self.config.fonts.font_fee)
        grid.set_text(
            (13, 0),
            line_str[7],
            font_name=self.config.fonts.font_buttom,
            anchor="rs",
        )

    def draw_fiat(self, line_str, pricestack, mode):
        if mode == "newblock":
            grid = TextGrid(8, 4, self.image, margin_x=1, margin_y=1)
            grid.merge((0, 0), (1, 3))
            grid.merge((2, 0), (2, 3))
            grid.merge((3, 0), (3, 3))
            grid.merge((4, 0), (4, 3))
            grid.merge((5, 0), (7, 3))
            grid.set_text(0, line_str[0], font_name=self.config.fonts.font_console)
            grid.set_text(1, line_str[1], font_name=self.config.fonts.font_fee)
            grid.set_text(2, line_str[2], font_name=self.config.fonts.font_side)
            grid.set_text(3, line_str[3], font_name=self.config.fonts.font_side)
            grid.set_text(
                4, line_str[4], font_name=self.config.fonts.font_buttom, anchor="rs"
            )
            return

        grid = TextGrid(22, 6, self.image, margin_x=1, margin_y=1)
        grid.merge((0, 0), (2, 5))
        grid.merge((3, 0), (4, 5))
        grid.merge((5, 2), (10, 5))
        grid.merge((5, 0), (6, 1))
        grid.merge((7, 0), (8, 1))
        grid.merge((9, 0), (10, 1))
        grid.merge((11, 0), (12, 1))
        grid.merge((11, 3), (12, 5))
        grid.merge((13, 0), (21, 5))
        start_img, end_img = grid.get_grid((5, 2), convert_to_pixel=True)
        spark_image = makeSpark(
            pricestack,
            figsize_pixel=(end_img[0] - start_img[0], end_img[1] - start_img[1]),
        )

        grid.set_text((0, 0), line_str[0], font_name=self.config.fonts.font_top)
        grid.set_text((3, 0), line_str[1], font_name=self.config.fonts.font_fee)
        grid.paste_image((5, 2), spark_image, anchor="rs")
        grid.set_text((5, 0), line_str[2], font_name=self.config.fonts.font_side)
        grid.set_text((7, 0), line_str[3], font_name=self.config.fonts.font_side)
        grid.set_text((9, 0), line_str[4], font_name=self.config.fonts.font_side)
        grid.set_text((11, 0), line_str[5], font_name=self.config.fonts.font_side)
        grid.set_text((11, 3), line_str[6], font_name=self.config.fonts.font_fee)
        grid.set_text(
            (13, 0),
            line_str[7],
            font_name=self.config.fonts.font_buttom,
            anchor="rs",
        )

    def draw_fiat_height(self, line_str):
        grid = TextGrid(8, 4, self.image, margin_x=1, margin_y=1)
        grid.merge((0, 0), (1, 3))
        grid.merge((2, 0), (2, 3))
        grid.merge((3, 0), (3, 3))
        grid.merge((4, 0), (4, 3))
        grid.merge((5, 0), (7, 3))
        grid.set_text(0, line_str[0], font_name=self.config.fonts.font_console)
        grid.set_text(1, line_str[1], font_name=self.config.fonts.font_fee)
        grid.set_text(2, line_str[2], font_name=self.config.fonts.font_side)
        grid.set_text(3, line_str[3], font_name=self.config.fonts.font_side)
        grid.set_text(
            4, line_str[4], font_name=self.config.fonts.font_buttom, anchor="rs"
        )

    def draw_mempool(self, line_str):
        grid = TextGrid(7, 4, self.image, margin_x=1, margin_y=1)
        grid.merge((0, 0), (1, 3))
        grid.merge((2, 0), (2, 3))
        grid.merge((3, 0), (3, 3))
        grid.merge((4, 0), (6, 3))
        grid.set_text(0, line_str[0], font_name=self.config.fonts.font_console)
        grid.set_text(1, line_str[1], font_name=self.config.fonts.font_side)
        grid.set_text(2, line_str[2], font_name=self.config.fonts.font_side)
        grid.set_text(3, line_str[3], font_name=self.config.fonts.font_big, anchor="rs")

    def draw_ohlc(self, line_str, ohlc_data):
        w = 6
        dpi = int(480 / w)

        if self.width > 450 and self.height > self.width:
            grid = TextGrid(35, 6, self.image, margin_x=1, margin_y=1)
            grid.merge((0, 0), (2, 5))
            grid.merge((3, 0), (4, 5))
            grid.merge((5, 0), (20, 5))
            grid.merge((21, 0), (22, 5))
            grid.merge((23, 0), (24, 5))
            grid.merge((25, 0), (26, 5))
            grid.merge((27, 0), (28, 5))
            grid.merge((29, 0), (34, 5))
            start_img, end_img = grid.get_grid((5, 0), convert_to_pixel=True)
            ohlc_image = makeCandle(
                ohlc_data,
                figsize_pixel=(end_img[0] - start_img[0], end_img[1] - start_img[1]),
                dpi=dpi,
                x_axis=False,
            )

            grid.set_text((0, 0), line_str[0], font_name=self.config.fonts.font_console)
            grid.set_text((3, 0), line_str[1], font_name=self.config.fonts.font_side)
            grid.paste_image((5, 0), ohlc_image, anchor="rs")
            grid.set_text((21, 0), line_str[2], font_name=self.config.fonts.font_fee)
            grid.set_text((23, 0), line_str[3], font_name=self.config.fonts.font_side)
            grid.set_text((25, 0), line_str[4], font_name=self.config.fonts.font_side)
            grid.set_text((27, 0), line_str[5], font_name=self.config.fonts.font_side)
            grid.set_text(
                (29, 0),
                line_str[6],
                font_name=self.config.fonts.font_buttom,
                anchor="rs",
            )
            return

        grid = TextGrid(21, 6, self.image, margin_x=1, margin_y=1)
        grid.merge((0, 0), (4, 5))
        grid.merge((5, 0), (20, 5))
        start_img, end_img = grid.get_grid((5, 0), convert_to_pixel=True)
        ohlc_image = makeCandle(
            ohlc_data,
            figsize_pixel=(end_img[0] - start_img[0], end_img[1] - start_img[1]),
            dpi=dpi,
            x_axis=False,
        )

        grid.set_text((0, 0), line_str[0], font_name=self.config.fonts.font_console)
        grid.paste_image((5, 0), ohlc_image, anchor="rs")

    def draw_big_two_rows(self, line_str):
        grid = TextGrid(9, 4, self.image, margin_x=1, margin_y=1)
        grid.merge((0, 0), (3, 3))
        grid.merge((4, 0), (4, 3))
        grid.merge((5, 0), (8, 3))
        grid.set_text(0, line_str[0], font_name=self.config.fonts.font_console)
        grid.set_text(1, line_str[1], font_name=self.config.fonts.font_fee)
        grid.set_text(
            2, line_str[2], font_name=self.config.fonts.font_console, anchor="rs"
        )

    def draw_one_number(self, line_str):
        grid = TextGrid(8, 4, self.image, margin_x=10, margin_y=10)
        grid.merge((2, 0), (4, 3))
        grid.merge((5, 0), (7, 3))
        grid.set_text(0, line_str[0], font_name=self.config.fonts.font_fee)
        grid.set_text(1, line_str[1], font_name=self.config.fonts.font_fee)

    def draw_big_one_row(self, line_str):
        grid = TextGrid(9, 4, self.image, margin_x=1, margin_y=1)
        grid.merge((0, 0), (0, 3))
        grid.merge((1, 0), (1, 3))
        grid.merge((2, 0), (8, 3))
        grid.set_text(0, line_str[0], font_name=self.config.fonts.font_console)
        grid.set_text(1, line_str[1], font_name=self.config.fonts.font_fee)
        grid.set_text(2, line_str[2], font_name=self.config.fonts.font_big, anchor="rs")

    def get_image(self):
        return self.image.image_handler.image
