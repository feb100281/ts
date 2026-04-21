# # budget/reporting/pdf/charts/sales_country_map_chart.py

# from __future__ import annotations

# from pathlib import Path

# import matplotlib.pyplot as plt
# import pandas as pd
# from matplotlib import colors as mcolors
# from matplotlib.cm import ScalarMappable
# from matplotlib.ticker import FuncFormatter

# from budget.reporting.pdf.charts.base import fig_to_base64
# from budget.reporting.pdf.charts.styles import (
#     COLOR_BG,
#     COLOR_BORDER,
#     COLOR_GRID,
#     COLOR_MUTED,
#     COLOR_PRIMARY,
#     COLOR_TEXT,
#     COLOR_BAR_SOFT,
#     COLOR_BAR_SOFT_EDGE,
#     COLOR_LINE_SOFT_BG,
# )

# try:
#     import geopandas as gpd
# except ImportError:  # pragma: no cover
#     gpd = None


# ISO2_TO_ISO3 = {
#     "RU": "RUS",
#     "BY": "BLR",
#     "KZ": "KAZ",
#     "AM": "ARM",
#     "KG": "KGZ",
#     "UZ": "UZB",
#     "GE": "GEO",
#     "TJ": "TJK",
# }

# # Координаты подписей — чтобы текст красиво лег на карту
# LABEL_POINTS = {
#     "RUS": (105, 63),
#     "BLR": (28, 54.3),
#     "KAZ": (67, 48.8),
#     "ARM": (45.1, 40.4),
#     "KGZ": (75.1, 41.6),
#     "UZB": (64.7, 41.6),
#     "GEO": (43.7, 42.3),
#     "TJK": (71.3, 39.2),
# }


# def _format_money_short(value: float) -> str:
#     value = float(value or 0)

#     if value >= 1_000_000_000:
#         return f"{value / 1_000_000_000:.1f} млрд ₽"
#     if value >= 1_000_000:
#         return f"{value / 1_000_000:.1f} млн ₽"
#     if value >= 1_000:
#         return f"{value / 1_000:.1f} тыс ₽"
#     return f"{value:,.0f} ₽".replace(",", " ")


# def _format_money_tick(value: float, _pos=None) -> str:
#     value = float(value or 0)

#     if value >= 1_000_000_000:
#         return f"{value / 1_000_000_000:.1f} млрд"
#     if value >= 1_000_000:
#         return f"{value / 1_000_000:.0f} млн"
#     if value >= 1_000:
#         return f"{value / 1_000:.0f} тыс"
#     return f"{value:,.0f}".replace(",", " ")


# def _build_plot_df(sales_by_country: list[dict]) -> pd.DataFrame:
#     rows = []

#     for row in sales_by_country or []:
#         code2 = str(row.get("country_code") or "").upper().strip()
#         code3 = ISO2_TO_ISO3.get(code2)

#         if not code3:
#             continue

#         sales_amount = float(row.get("sales_amount") or 0)
#         share_pct = float(row.get("share_pct") or 0)

#         if sales_amount <= 0:
#             continue

#         rows.append(
#             {
#                 "country_code": code2,
#                 "iso_a3": code3,
#                 "country_name": row.get("country_name") or code2,
#                 "sales_amount": sales_amount,
#                 "share_pct": share_pct,
#             }
#         )

#     return pd.DataFrame(rows)


# def _get_shapefile_path() -> Path:
#     """
#     Ищем локальный shapefile внутри проекта.
#     """
#     current_file = Path(__file__).resolve()

#     shp_path = (
#         current_file.parent.parent
#         / "assets"
#         / "maps"
#         / "ne_110m_admin_0_countries"
#         / "ne_110m_admin_0_countries.shp"
#     )

#     if not shp_path.exists():
#         raise RuntimeError(
#             "Не найден shapefile карты стран.\n"
#             f"Ожидаемый путь:\n{shp_path}\n\n"
#             "Положи туда Natural Earth shapefile "
#             "'ne_110m_admin_0_countries.shp' вместе с .shx/.dbf/.prj"
#         )

#     return shp_path


# def _get_world_gdf():
#     if gpd is None:
#         raise ImportError(
#             "Для карты продаж нужен geopandas. Установи: pip install geopandas"
#         )

#     shp_path = _get_shapefile_path()
#     return gpd.read_file(shp_path)


# def _normalize_world_columns(world: pd.DataFrame) -> pd.DataFrame:
#     world = world.copy()

#     iso_col = None
#     name_col = None

#     for candidate in ("ISO_A3", "iso_a3", "ADM0_A3", "adm0_a3"):
#         if candidate in world.columns:
#             iso_col = candidate
#             break

#     for candidate in ("ADMIN", "admin", "NAME", "name", "NAME_LONG", "name_long"):
#         if candidate in world.columns:
#             name_col = candidate
#             break

#     if not iso_col:
#         raise ValueError(
#             f"В shapefile не найдена колонка ISO-кода. Колонки: {list(world.columns)}"
#         )

#     if not name_col:
#         raise ValueError(
#             f"В shapefile не найдена колонка названия страны. Колонки: {list(world.columns)}"
#         )

#     world = world.rename(columns={iso_col: "iso_a3_src", name_col: "country_name_src"})
#     return world


# def _pick_label_xy(geom, iso_a3: str) -> tuple[float, float]:
#     if iso_a3 in LABEL_POINTS:
#         return LABEL_POINTS[iso_a3]

#     try:
#         pt = geom.representative_point()
#         return pt.x, pt.y
#     except Exception:
#         centroid = geom.centroid
#         return centroid.x, centroid.y


# def _build_sales_cmap():
#     """
#     Фирменный зелёный градиент без грязных и желтых тонов.
#     """
#     return mcolors.LinearSegmentedColormap.from_list(
#         "sales_clean_green",
#         [
#             "#F4F8F6",
#             COLOR_LINE_SOFT_BG,
#             "#DCE9E4",
#             "#C7DBD4",
#             "#A8C5BC",
#             COLOR_BAR_SOFT,
#             "#4F7F74",
#             COLOR_PRIMARY,
#         ],
#         N=256,
#     )


# def _compute_ticks(vmin: float, vmax: float) -> list[float]:
#     """
#     Аккуратные тики для colorbar без scientific notation.
#     """
#     if vmax <= 0:
#         return [0]

#     candidates = []

#     # Для удобства чтения в рублях
#     steps = [
#         100_000,
#         250_000,
#         500_000,
#         1_000_000,
#         2_500_000,
#         5_000_000,
#         10_000_000,
#         25_000_000,
#         50_000_000,
#         100_000_000,
#         250_000_000,
#         500_000_000,
#         1_000_000_000,
#     ]

#     for step in steps:
#         ticks = []
#         cur = 0
#         while cur <= vmax:
#             ticks.append(cur)
#             cur += step

#         if 4 <= len(ticks) <= 7:
#             candidates = ticks
#             break

#     if not candidates:
#         candidates = [0, vmin, vmax / 2, vmax]

#     ticks = sorted({float(t) for t in candidates if vmin <= float(t) <= vmax or float(t) == 0})

#     if vmin > 0 and all(abs(t - vmin) > 1e-9 for t in ticks):
#         ticks = [vmin] + ticks

#     if all(abs(t - vmax) > 1e-9 for t in ticks):
#         ticks.append(vmax)

#     ticks = sorted(set(ticks))
#     return ticks


# def build_sales_country_map_base64(
#     sales_by_country: list[dict],
#     label_mode: str = "share",  # "share" | "amount"
# ) -> str | None:
#     if not sales_by_country:
#         return None

#     df = _build_plot_df(sales_by_country)
#     if df.empty:
#         return None

#     world = _get_world_gdf()
#     world = _normalize_world_columns(world)

#     # Регион СНГ + запас вокруг
#     region = world.cx[20:110, 35:70].copy()

#     region = region.merge(
#         df,
#         how="left",
#         left_on="iso_a3_src",
#         right_on="iso_a3",
#     )

#     fig, ax = plt.subplots(figsize=(13.8, 6.2), dpi=180)
#     fig.patch.set_facecolor(COLOR_BG)
#     ax.set_facecolor(COLOR_BG)

#     # Базовая карта
#     region.plot(
#         ax=ax,
#         color="#F5F6F4",
#         edgecolor="#C8CBC8",
#         linewidth=0.7,
#         zorder=1,
#     )

#     colored = region[region["sales_amount"].notna()].copy()

#     if not colored.empty:
#         cmap = _build_sales_cmap()

#         vmin = float(colored["sales_amount"].min())
#         vmax = float(colored["sales_amount"].max())

#         # PowerNorm вместо обычной Normalize:
#         # помогает странам с малыми продажами не пропадать на фоне РФ.
#         gamma = 0.38 if vmax > vmin else 1.0
#         norm = mcolors.PowerNorm(gamma=gamma, vmin=vmin, vmax=vmax)

#         colored.plot(
#             ax=ax,
#             column="sales_amount",
#             cmap=cmap,
#             norm=norm,
#             linewidth=1.1,
#             edgecolor=COLOR_BAR_SOFT_EDGE,
#             legend=False,
#             zorder=3,
#         )

#         sm = ScalarMappable(norm=norm, cmap=cmap)
#         sm.set_array([])

#         ticks = _compute_ticks(vmin, vmax)

#         cbar = fig.colorbar(
#             sm,
#             ax=ax,
#             orientation="vertical",
#             fraction=0.032,
#             pad=0.018,
#             shrink=0.76,
#             ticks=ticks,
#         )

#         cbar.outline.set_edgecolor(COLOR_BORDER)
#         cbar.outline.set_linewidth(0.8)
#         cbar.ax.yaxis.set_major_formatter(FuncFormatter(_format_money_tick))
#         cbar.ax.yaxis.offsetText.set_visible(False)
#         cbar.ax.tick_params(
#             labelsize=8.5,
#             colors=COLOR_MUTED,
#             length=0,
#             pad=4,
#         )
#         cbar.set_label(
#             "Продажи, ₽",
#             fontsize=9,
#             color=COLOR_TEXT,
#             labelpad=8,
#         )

#     ax.set_xlim(20, 110)
#     ax.set_ylim(35, 70)

#     ax.set_title(
#         "Карта продаж по странам",
#         fontsize=15,
#         color=COLOR_TEXT,
#         fontweight="bold",
#         pad=14,
#     )

#     # Аккуратная рамка области карты
#     ax.add_patch(
#         plt.Rectangle(
#             (20, 35),
#             90,
#             35,
#             fill=False,
#             edgecolor=COLOR_GRID,
#             linewidth=0.8,
#             zorder=2,
#         )
#     )

#     for _, row in colored.iterrows():
#         geom = row.geometry
#         iso_a3 = row.get("iso_a3") or row.get("iso_a3_src")
#         country_name = row.get("country_name") or row.get("country_name_src") or "—"
#         sales_amount = float(row.get("sales_amount") or 0)
#         share_pct = float(row.get("share_pct") or 0)

#         second_line = (
#             _format_money_short(sales_amount)
#             if label_mode == "amount"
#             else f"{share_pct:.2f}%"
#         )

#         x, y = _pick_label_xy(geom, iso_a3)

#         ax.text(
#             x,
#             y,
#             f"{country_name}\n{second_line}",
#             ha="center",
#             va="center",
#             fontsize=8.8,
#             color=COLOR_TEXT,
#             fontweight=600,
#             linespacing=1.12,
#             zorder=5,
#             bbox=dict(
#                 boxstyle="round,pad=0.28,rounding_size=0.12",
#                 facecolor="#FAFAF8",
#                 edgecolor=COLOR_BORDER,
#                 linewidth=0.85,
#                 alpha=0.96,
#             ),
#         )

#     subtitle = (
#         "Цветом выделены страны с продажами за последние 90 дней. "
#         + (
#             "Подписи показывают выручку."
#             if label_mode == "amount"
#             else "Подписи показывают долю в выручке."
#         )
#     )

#     ax.text(
#         0.0,
#         -0.065,
#         subtitle,
#         transform=ax.transAxes,
#         ha="left",
#         va="top",
#         fontsize=9,
#         color=COLOR_MUTED,
#     )

#     ax.grid(False)
#     ax.set_xticks([])
#     ax.set_yticks([])

#     for spine in ax.spines.values():
#         spine.set_visible(False)

#     fig.tight_layout()
#     return fig_to_base64(fig)





from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib import colors as mcolors
from matplotlib.cm import ScalarMappable
from matplotlib.ticker import FuncFormatter

from budget.reporting.pdf.charts.base import fig_to_base64
from budget.reporting.pdf.charts.styles import (
    COLOR_BG,
    COLOR_BORDER,
    COLOR_GRID,
    COLOR_MUTED,
    COLOR_PRIMARY,
    COLOR_TEXT,
    COLOR_BAR_SOFT,
    COLOR_BAR_SOFT_EDGE,
    COLOR_LINE_SOFT_BG,
)

try:
    import geopandas as gpd
except ImportError:  # pragma: no cover
    gpd = None


ISO2_TO_ISO3 = {
    "RU": "RUS",
    "BY": "BLR",
    "KZ": "KAZ",
    "AM": "ARM",
    "KG": "KGZ",
    "UZ": "UZB",
    "GE": "GEO",
    "TJ": "TJK",
}

# Координаты подписей — чтобы текст красиво лег на карту
LABEL_POINTS = {
    "RUS": (105, 63),
    "BLR": (28, 54.3),
    "KAZ": (67, 48.8),
    "ARM": (45.1, 40.4),
    "KGZ": (75.1, 41.6),
    "UZB": (64.7, 41.6),
    "GEO": (43.7, 42.3),
    "TJK": (71.3, 39.2),
}


def _format_money_short(value: float) -> str:
    value = float(value or 0)

    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.1f} млрд ₽"
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f} млн ₽"
    if value >= 1_000:
        return f"{value / 1_000:.1f} тыс ₽"
    return f"{value:,.0f} ₽".replace(",", " ")


def _format_money_tick(value: float, _pos=None) -> str:
    value = float(value or 0)

    if value >= 1_000_000_000:
        return f"{value / 1_000_000_000:.1f} млрд"
    if value >= 1_000_000:
        return f"{value / 1_000_000:.0f} млн"
    if value >= 1_000:
        return f"{value / 1_000:.0f} тыс"
    return f"{value:,.0f}".replace(",", " ")


def _build_plot_df(sales_by_country: list[dict]) -> pd.DataFrame:
    rows = []

    for row in sales_by_country or []:
        code2 = str(row.get("country_code") or "").upper().strip()
        code3 = ISO2_TO_ISO3.get(code2)

        if not code3:
            continue

        sales_amount = float(row.get("sales_amount") or 0)
        share_pct = float(row.get("share_pct") or 0)

        if sales_amount <= 0:
            continue

        rows.append(
            {
                "country_code": code2,
                "iso_a3": code3,
                "country_name": row.get("country_name") or code2,
                "sales_amount": sales_amount,
                "share_pct": share_pct,
            }
        )

    return pd.DataFrame(rows)


def _get_shapefile_path() -> Path:
    """
    Ищем локальный shapefile внутри проекта.
    """
    current_file = Path(__file__).resolve()

    shp_path = (
        current_file.parent.parent
        / "assets"
        / "maps"
        / "ne_110m_admin_0_countries"
        / "ne_110m_admin_0_countries.shp"
    )

    if not shp_path.exists():
        raise RuntimeError(
            "Не найден shapefile карты стран.\n"
            f"Ожидаемый путь:\n{shp_path}\n\n"
            "Положи туда Natural Earth shapefile "
            "'ne_110m_admin_0_countries.shp' вместе с .shx/.dbf/.prj"
        )

    return shp_path


def _get_world_gdf():
    if gpd is None:
        raise ImportError(
            "Для карты продаж нужен geopandas. Установи: pip install geopandas"
        )

    shp_path = _get_shapefile_path()
    return gpd.read_file(shp_path)


def _normalize_world_columns(world: pd.DataFrame) -> pd.DataFrame:
    world = world.copy()

    iso_col = None
    name_col = None

    for candidate in ("ISO_A3", "iso_a3", "ADM0_A3", "adm0_a3"):
        if candidate in world.columns:
            iso_col = candidate
            break

    for candidate in ("ADMIN", "admin", "NAME", "name", "NAME_LONG", "name_long"):
        if candidate in world.columns:
            name_col = candidate
            break

    if not iso_col:
        raise ValueError(
            f"В shapefile не найдена колонка ISO-кода. Колонки: {list(world.columns)}"
        )

    if not name_col:
        raise ValueError(
            f"В shapefile не найдена колонка названия страны. Колонки: {list(world.columns)}"
        )

    world = world.rename(columns={iso_col: "iso_a3_src", name_col: "country_name_src"})
    return world


def _pick_label_xy(geom, iso_a3: str) -> tuple[float, float]:
    if iso_a3 in LABEL_POINTS:
        return LABEL_POINTS[iso_a3]

    try:
        pt = geom.representative_point()
        return pt.x, pt.y
    except Exception:
        centroid = geom.centroid
        return centroid.x, centroid.y


def _build_sales_cmap():
    """
    Фирменный зелёный градиент без грязных и желтых тонов.
    """
    return mcolors.LinearSegmentedColormap.from_list(
        "sales_clean_green",
        [
            "#F4F8F6",
            COLOR_LINE_SOFT_BG,
            "#DCE9E4",
            "#C7DBD4",
            "#A8C5BC",
            COLOR_BAR_SOFT,
            "#4F7F74",
            COLOR_PRIMARY,
        ],
        N=256,
    )


def _compute_ticks(vmin: float, vmax: float) -> list[float]:
    """
    Аккуратные тики для colorbar без scientific notation.
    """
    if vmax <= 0:
        return [0]

    candidates = []

    # Для удобства чтения в рублях
    steps = [
        100_000,
        250_000,
        500_000,
        1_000_000,
        2_500_000,
        5_000_000,
        10_000_000,
        25_000_000,
        50_000_000,
        100_000_000,
        250_000_000,
        500_000_000,
        1_000_000_000,
    ]

    for step in steps:
        ticks = []
        cur = 0
        while cur <= vmax:
            ticks.append(cur)
            cur += step

        if 4 <= len(ticks) <= 7:
            candidates = ticks
            break

    if not candidates:
        candidates = [0, vmin, vmax / 2, vmax]

    ticks = sorted(
        {float(t) for t in candidates if vmin <= float(t) <= vmax or float(t) == 0}
    )

    if vmin > 0 and all(abs(t - vmin) > 1e-9 for t in ticks):
        ticks = [vmin] + ticks

    if all(abs(t - vmax) > 1e-9 for t in ticks):
        ticks.append(vmax)

    ticks = sorted(set(ticks))
    return ticks


def build_sales_country_map_base64(
    sales_by_country: list[dict],
    label_mode: str = "share",  # "share" | "amount"
) -> str | None:
    if not sales_by_country:
        return None

    df = _build_plot_df(sales_by_country)
    if df.empty:
        return None

    world = _get_world_gdf()
    world = _normalize_world_columns(world)

    # Регион СНГ + запас вокруг
    region = world.cx[20:110, 35:70].copy()

    region = region.merge(
        df,
        how="left",
        left_on="iso_a3_src",
        right_on="iso_a3",
    )

    # Уменьшили высоту, чтобы блок помещался на страницу
    fig, ax = plt.subplots(figsize=(13.8, 4.5), dpi=180)
    fig.patch.set_facecolor(COLOR_BG)
    ax.set_facecolor(COLOR_BG)
    ax.set_aspect("auto")

    # Базовая карта
    region.plot(
        ax=ax,
        color="#F5F6F4",
        edgecolor="#C8CBC8",
        linewidth=0.7,
        zorder=1,
    )

    colored = region[region["sales_amount"].notna()].copy()

    if not colored.empty:
        cmap = _build_sales_cmap()

        vmin = float(colored["sales_amount"].min())
        vmax = float(colored["sales_amount"].max())

        # PowerNorm вместо обычной Normalize:
        # помогает странам с малыми продажами не пропадать на фоне РФ.
        gamma = 0.38 if vmax > vmin else 1.0
        norm = mcolors.PowerNorm(gamma=gamma, vmin=vmin, vmax=vmax)

        colored.plot(
            ax=ax,
            column="sales_amount",
            cmap=cmap,
            norm=norm,
            linewidth=1.1,
            edgecolor=COLOR_BAR_SOFT_EDGE,
            legend=False,
            zorder=3,
        )

        sm = ScalarMappable(norm=norm, cmap=cmap)
        sm.set_array([])

        ticks = _compute_ticks(vmin, vmax)

        cbar = fig.colorbar(
            sm,
            ax=ax,
            orientation="vertical",
            fraction=0.032,
            pad=0.018,
            shrink=0.74,
            ticks=ticks,
        )

        cbar.outline.set_edgecolor(COLOR_BORDER)
        cbar.outline.set_linewidth(0.8)
        cbar.ax.yaxis.set_major_formatter(FuncFormatter(_format_money_tick))
        cbar.ax.yaxis.offsetText.set_visible(False)
        cbar.ax.tick_params(
            labelsize=8.0,
            colors=COLOR_MUTED,
            length=0,
            pad=4,
        )
        cbar.set_label(
            "Продажи, ₽",
            fontsize=8.5,
            color=COLOR_TEXT,
            labelpad=7,
        )

    ax.set_xlim(20, 110)
    ax.set_ylim(35, 70)

    # Заголовок удален, т.к. он формируется в другом месте

    # Аккуратная рамка области карты
    ax.add_patch(
        plt.Rectangle(
            (20, 35),
            90,
            35,
            fill=False,
            edgecolor=COLOR_GRID,
            linewidth=0.8,
            zorder=2,
        )
    )

    for _, row in colored.iterrows():
        geom = row.geometry
        iso_a3 = row.get("iso_a3") or row.get("iso_a3_src")
        country_name = row.get("country_name") or row.get("country_name_src") or "—"
        sales_amount = float(row.get("sales_amount") or 0)
        share_pct = float(row.get("share_pct") or 0)

        second_line = (
            _format_money_short(sales_amount)
            if label_mode == "amount"
            else f"{share_pct:.2f}%"
        )

        x, y = _pick_label_xy(geom, iso_a3)

        ax.text(
            x,
            y,
            f"{country_name}\n{second_line}",
            ha="center",
            va="center",
            fontsize=8.4,
            color=COLOR_TEXT,
            fontweight=600,
            linespacing=1.08,
            zorder=5,
            bbox=dict(
                boxstyle="round,pad=0.24,rounding_size=0.12",
                facecolor="#FAFAF8",
                edgecolor=COLOR_BORDER,
                linewidth=0.8,
                alpha=0.96,
            ),
        )

    subtitle = (
        "Цветом выделены страны с продажами за последние 90 дней. "
        + (
            "Подписи показывают выручку."
            if label_mode == "amount"
            else "Подписи показывают долю в выручке."
        )
    )

    ax.text(
        0.0,
        -0.045,
        subtitle,
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=8.5,
        color=COLOR_MUTED,
    )

    ax.grid(False)
    ax.set_xticks([])
    ax.set_yticks([])

    for spine in ax.spines.values():
        spine.set_visible(False)

    fig.tight_layout(pad=0.3)
    return fig_to_base64(fig)