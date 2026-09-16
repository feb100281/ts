# budget/reporting/pdf/charts/base.py

import base64
from io import BytesIO

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

from budget.reporting.pdf.charts.styles import COLOR_BORDER


def fig_to_base64(fig) -> str:
    buffer = BytesIO()
    fig.savefig(buffer, format="png", bbox_inches="tight", facecolor="white")
    plt.close(fig)
    buffer.seek(0)
    return base64.b64encode(buffer.read()).decode("utf-8")


def remove_inner_frame(ax, keep_bottom=True):
    ax.spines["top"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.spines["right"].set_visible(False)

    if keep_bottom:
        ax.spines["bottom"].set_visible(True)
        ax.spines["bottom"].set_color(COLOR_BORDER)
        ax.spines["bottom"].set_linewidth(0.8)
    else:
        ax.spines["bottom"].set_visible(False)