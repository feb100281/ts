from __future__ import annotations

import io
from pathlib import Path

import matplotlib
matplotlib.use("Agg")

import matplotlib.pyplot as plt
import pandas as pd
from matplotlib import colors as mcolors
from matplotlib.cm import ScalarMappable
from matplotlib.ticker import FuncFormatter

try:
    import geopandas as gpd
except ImportError:
    gpd = None


COLOR_BG = "#F4F8F6"
COLOR_BASE = "#E6ECE9"
COLOR_TEXT = "#18352F"
COLOR_MUTED = "#60746D"
COLOR_PRIMARY = "#006B4F"


WAREHOUSE_POINTS = {
    "Электросталь": (38.45, 55.78),
    "Тула": (37.62, 54.20),
    "Краснодар": (38.97, 45.04),
    "Коледино": (37.55, 55.39),
    "Екатеринбург - Перспективная 14": (60.61, 56.84),
    "Рязань (Тюшевское)": (39.74, 54.63),
    "Владимир WB": (40.41, 56.13),
    "Новосемейкино": (50.35, 53.37),
    "Невинномысск": (41.94, 44.63),
    "Воронеж WB": (39.20, 51.66),
    "Волгоград": (44.52, 48.71),
    "Котовск": (41.51, 52.59),
    "Склад СПБ Шушары Московское": (30.38, 59.81),
    "Сарапул WB": (53.80, 56.48),
    "Казань": (49.12, 55.79),
    "Белая дача": (37.85, 55.66),
    "Владивосток WB": (131.89, 43.12),
}


def get_russia_shapefile_path() -> Path:
    current_file = Path(__file__).resolve()

    shp_path = (
        current_file.parent.parent
        / "assets"
        / "maps"
        / "russia_regions"
        / "ne_10m_admin_1_states_provinces.shp"
    )

    if not shp_path.exists():
        raise FileNotFoundError(f"Shapefile не найден: {shp_path}")

    return shp_path


def format_number(value: float) -> str:
    value = float(value or 0)

    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f} млн шт"
    if value >= 1_000:
        return f"{value / 1_000:.1f} тыс шт"
    return f"{value:,.0f} шт".replace(",", " ")


def _format_tick(value, _pos=None):
    value = float(value or 0)

    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f} млн"
    if value >= 1_000:
        return f"{value / 1_000:.0f} тыс"
    return f"{value:,.0f}".replace(",", " ")


def _load_russia_map():
    if gpd is None:
        raise ImportError("Установите geopandas: pip install geopandas")

    gdf = gpd.read_file(get_russia_shapefile_path())

    for col in ["adm0_a3", "ADM0_A3", "sov_a3", "SOV_A3"]:
        if col in gdf.columns:
            filtered = gdf[gdf[col].astype(str).str.upper().eq("RUS")].copy()
            if not filtered.empty:
                return filtered

    for col in ["admin", "ADMIN", "geonunit", "GEOUNIT"]:
        if col in gdf.columns:
            filtered = gdf[
                gdf[col].astype(str).str.upper().str.contains("RUSSIA|RUSSIAN", na=False)
            ].copy()
            if not filtered.empty:
                return filtered

    return gdf


def _build_cmap():
    return mcolors.LinearSegmentedColormap.from_list(
        "warehouse_green",
        ["#DDEBE5", "#9CC5B8", "#4F927F", COLOR_PRIMARY],
        N=256,
    )


def build_warehouses_stock_map_png(
    warehouse_stats: pd.DataFrame,
    report_date: str,
) -> io.BytesIO:
    if warehouse_stats.empty:
        raise ValueError("Нет данных по складам для построения карты")

    df = warehouse_stats.copy()
    df["склад"] = df["склад"].astype(str).str.strip()
    df["итого"] = pd.to_numeric(df["итого"], errors="coerce").fillna(0)

    coords = (
        pd.DataFrame.from_dict(
            WAREHOUSE_POINTS,
            orient="index",
            columns=["lon", "lat"],
        )
        .reset_index()
        .rename(columns={"index": "склад"})
    )

    df = df.merge(coords, how="left", on="склад")

    missing = df[df["lon"].isna()]["склад"].dropna().unique().tolist()
    if missing:
        print("Нет координат для складов:")
        for x in missing:
            print(" -", x)

    df = df[df["lon"].notna() & df["lat"].notna() & (df["итого"] > 0)].copy()

    if df.empty:
        raise ValueError(
            "После сопоставления складов с координатами не осталось данных. "
            "Проверь WAREHOUSE_POINTS."
        )

    russia = _load_russia_map()

    fig, ax = plt.subplots(figsize=(15.2, 7.6), dpi=180)
    fig.patch.set_facecolor(COLOR_BG)
    ax.set_facecolor(COLOR_BG)
    ax.set_aspect("auto")

    russia.plot(
        ax=ax,
        color=COLOR_BASE,
        edgecolor="#FFFFFF",
        linewidth=0.75,
        zorder=1,
    )

    max_qty = float(df["итого"].max())
    min_qty = float(df["итого"].min())

    if max_qty > min_qty:
        norm = mcolors.PowerNorm(gamma=0.45, vmin=min_qty, vmax=max_qty)
    else:
        norm = mcolors.Normalize(vmin=0, vmax=max_qty)

    cmap = _build_cmap()

    sizes = 90 + 900 * (df["итого"] / max_qty) ** 0.55

    scatter = ax.scatter(
        df["lon"],
        df["lat"],
        s=sizes,
        c=df["итого"],
        cmap=cmap,
        norm=norm,
        edgecolors="#FFFFFF",
        linewidths=1.4,
        alpha=0.92,
        zorder=4,
    )

    # Подписи топ-складов
    label_df = df.sort_values("итого", ascending=False).head(12).copy()

    for _, row in label_df.iterrows():
        x = float(row["lon"])
        y = float(row["lat"])
        name = str(row["склад"])
        qty = float(row["итого"])

        ax.text(
            x + 1.2,
            y + 0.45,
            f"{name}\n{format_number(qty)}",
            ha="left",
            va="center",
            fontsize=7.8,
            color=COLOR_TEXT,
            fontweight=600,
            linespacing=1.05,
            zorder=6,
            bbox=dict(
                boxstyle="round,pad=0.25,rounding_size=0.12",
                facecolor="#FAFAF8",
                edgecolor="#B6C4BD",
                linewidth=0.75,
                alpha=0.96,
            ),
        )

    cbar = fig.colorbar(
        scatter,
        ax=ax,
        orientation="vertical",
        fraction=0.025,
        pad=0.015,
        shrink=0.72,
    )

    cbar.outline.set_edgecolor("#AAB7B0")
    cbar.outline.set_linewidth(0.8)
    cbar.ax.yaxis.set_major_formatter(FuncFormatter(_format_tick))
    cbar.ax.tick_params(labelsize=8, colors=COLOR_MUTED, length=0)
    cbar.set_label("Остатки, шт", fontsize=9, color=COLOR_TEXT, labelpad=8)

    ax.set_xlim(25, 145)
    ax.set_ylim(40, 75)

    ax.set_title(
        f"География остатков товаров по складам\nна {report_date}",
        fontsize=17,
        fontweight="bold",
        color=COLOR_TEXT,
        pad=18,
    )

    total_qty = df["итого"].sum()
    warehouses_count = df["склад"].nunique()

    ax.text(
        0.0,
        -0.04,
        f"Размер точки отражает величину товарного остатка. "
        f"На карте показано складов: {warehouses_count}. "
        f"Остаток по отображенным складам: {format_number(total_qty)}.",
        transform=ax.transAxes,
        ha="left",
        va="top",
        fontsize=9,
        color=COLOR_MUTED,
    )

    ax.set_xticks([])
    ax.set_yticks([])
    ax.grid(False)

    for spine in ax.spines.values():
        spine.set_visible(False)

    plt.tight_layout(pad=0.4)

    buffer = io.BytesIO()
    fig.savefig(
        buffer,
        format="png",
        dpi=180,
        bbox_inches="tight",
        facecolor=COLOR_BG,
    )
    plt.close(fig)
    buffer.seek(0)

    return buffer