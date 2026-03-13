import datetime
from collections.abc import Sequence
from typing import Any

import matplotlib.dates as mdates
import matplotlib.pyplot as plt
import matplotlib.units as munits
import mplfinance as mpf
import numpy as np
import numpy.typing as npt
from matplotlib.backends.backend_agg import FigureCanvasAgg
from matplotlib.figure import Figure
from PIL import Image


def makeSpark(
    pricestack: Sequence[float],
    figsize_pixel: tuple[int, int] = (170, 51),
    dpi: int = 17,
) -> Image.Image:
    # Draw and save the sparkline that represents historical data

    # Subtract the mean from the sparkline to make the
    # mean appear on the plot (it's really the x axis)
    values = np.asarray(pricestack, dtype=float)
    x = values - np.mean(values)
    figsize = (figsize_pixel[0] / dpi, figsize_pixel[1] / dpi)
    fig = Figure(figsize=figsize, dpi=dpi)
    ax = fig.add_subplot()
    canvas = FigureCanvasAgg(fig)
    ax.plot(x, color="k", linewidth=6)
    ax.plot(len(x) - 1, x[-1], color="r", marker="o")

    # Remove the Y axis
    for _, v in ax.spines.items():
        v.set_visible(False)
    ax.set_xticks([])
    ax.set_yticks([])
    ax.axhline(c="k", linewidth=4, linestyle=(0, (5, 2, 1, 2)))
    canvas.draw()
    buf = canvas.buffer_rgba()
    X: npt.NDArray[np.uint8] = np.asarray(buf)
    im = Image.fromarray(X)

    return im


def makeCandle(
    ohlc: Any,
    figsize_pixel: tuple[int, int] = (170, 51),
    dpi: int = 17,
    plot_type: str = "candle",
    x_axis: bool = True,
) -> Image.Image:
    figsize = (figsize_pixel[0] / dpi, figsize_pixel[1] / dpi)
    converter = mdates.ConciseDateConverter()
    munits.registry[np.datetime64] = converter
    munits.registry[datetime.date] = converter
    munits.registry[datetime.datetime] = converter

    fig = mpf.figure(figsize=figsize, dpi=dpi, constrained_layout=True)
    ax = fig.add_subplot(1, 1, 1)
    ax.set_facecolor("white")
    canvas = FigureCanvasAgg(fig)

    mpf.plot(ohlc, type=plot_type, ax=ax, ylabel="")
    ax.grid(True, linewidth=0.5, color="#000000", linestyle="-")
    if not x_axis:
        ax.set_xticklabels([])

    canvas.draw()
    buf = canvas.buffer_rgba()
    X: npt.NDArray[np.uint8] = np.asarray(buf)
    im = Image.fromarray(X)
    plt.close("all")

    return im
