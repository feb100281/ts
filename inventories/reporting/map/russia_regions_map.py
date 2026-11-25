# # inventories/reporting/map/russia_regions_map.py
# from __future__ import annotations

# import io
# import re

# import matplotlib
# matplotlib.use("Agg")

# import matplotlib.pyplot as plt
# import pandas as pd
# from matplotlib import colors as mcolors
# from matplotlib.cm import ScalarMappable
# from matplotlib.ticker import FuncFormatter

# try:
#     import geopandas as gpd
# except ImportError:
#     gpd = None

# from .map_config import (
#     COLOR_BG,
#     COLOR_BASE,
#     COLOR_TEXT,
#     COLOR_MUTED,
#     COLOR_PRIMARY,
#     COLOR_BORDER,
#     COLOR_BORDER_DARK,
#     COLOR_LABEL_BG,
#     WAREHOUSE_REGIONS,
#     LABEL_POINTS,
#     DISTRICT_KEYWORDS,
#     COUNTRIES_CONFIG,
#     get_russia_shapefile_path,
#     get_world_shapefile_path,
# )


# def format_number(value: float) -> str:
#     value = float(value or 0)
#     if value >= 1_000_000:
#         return f"{value / 1_000_000:.1f} млн шт"
#     if value >= 1_000:
#         return f"{value / 1_000:.1f} тыс шт"
#     return f"{value:,.0f} шт".replace(",", " ")


# def format_number_compact(value: float) -> str:
#     value = float(value or 0)
#     if value >= 1_000_000:
#         return f"{value / 1_000_000:.1f} млн"
#     if value >= 1_000:
#         return f"{value / 1_000:.0f} тыс"
#     return f"{value:,.0f}".replace(",", " ")


# def _format_tick(value, _pos=None):
#     value = float(value or 0)
#     if value >= 1_000_000:
#         return f"{value / 1_000_000:.1f} млн"
#     if value >= 1_000:
#         return f"{value / 1_000:.0f} тыс"
#     return f"{value:,.0f}".replace(",", " ")


# def _build_cmap():
#     return mcolors.LinearSegmentedColormap.from_list(
#         "stock_green",
#         ["#EEF5F1", "#DCEBE4", "#BFD8CF", "#8FB8AA", "#4E8B7A", COLOR_PRIMARY],
#         N=256,
#     )


# def _clean_text(value: object) -> str:
#     s = str(value or "").lower()
#     s = s.replace("’", "'")
#     s = re.sub(r"[^a-zа-яё0-9]+", " ", s)
#     return re.sub(r"\s+", " ", s).strip()


# def _find_name_col(gdf: pd.DataFrame) -> str:
#     candidates = [
#         "name", "NAME", "name_en", "NAME_EN",
#         "name_local", "NAME_LOCAL", "region",
#         "province", "gn_name", "GN_NAME",
#     ]
#     for col in candidates:
#         if col in gdf.columns:
#             return col
#     raise ValueError(f"Не найдена колонка с названием региона. Колонки: {list(gdf.columns)}")


# def _filter_russia_if_possible(gdf):
#     candidates = [
#         "adm0_a3", "ADM0_A3",
#         "iso_a2", "ISO_A2",
#         "admin", "ADMIN",
#         "geonunit", "GEOUNIT",
#         "sov_a3", "SOV_A3",
#     ]

#     for col in candidates:
#         if col not in gdf.columns:
#             continue

#         values = gdf[col].astype(str).str.upper()

#         if col.upper() in {"ADM0_A3", "SOV_A3"}:
#             mask = values.eq("RUS")
#         elif col.upper() == "ISO_A2":
#             mask = values.eq("RU")
#         else:
#             mask = values.str.contains(
#                 "RUSSIA|RUSSIAN FEDERATION|РОССИЯ|RUS",
#                 regex=True,
#                 na=False,
#             )

#         filtered = gdf[mask].copy()
#         if not filtered.empty:
#             return filtered

#     return gdf


# def _detect_district(region_name: object) -> str | None:
#     text = _clean_text(region_name)
#     for district, keywords in DISTRICT_KEYWORDS.items():
#         for keyword in keywords:
#             if keyword in text:
#                 return district
#     return None


# def _prepare_russia_geometries():
#     shp_path = get_russia_shapefile_path()
#     if not shp_path.exists():
#         raise FileNotFoundError(f"Shapefile России не найден: {shp_path}")

#     gdf = gpd.read_file(shp_path)
#     gdf = _filter_russia_if_possible(gdf)

#     name_col = _find_name_col(gdf)
#     gdf["district"] = gdf[name_col].apply(_detect_district)

#     matched_count = int(gdf["district"].notna().sum())
#     if matched_count == 0:
#         raise ValueError(
#             f"Не удалось сопоставить регионы. Примеры: {gdf[name_col].head(10).tolist()}"
#         )

#     gdf = gdf[gdf["district"].notna() & gdf.geometry.notna()].copy()
#     districts = gdf.dissolve(by="district", as_index=False)
#     districts = districts[districts.geometry.notna()].copy()

#     return districts


# def _prepare_countries_geometries():
#     shp_path = get_world_shapefile_path()
#     if not shp_path.exists():
#         return None

#     gdf = gpd.read_file(shp_path)

#     country_col = None
#     for col in ["ADMIN", "NAME", "SOVEREIGNT", "admin", "name", "NAME_EN", "name_en", "COUNTRY"]:
#         if col in gdf.columns:
#             country_col = col
#             break

#     if country_col is None:
#         return None

#     country_names_en = [cfg["name_en"] for cfg in COUNTRIES_CONFIG.values()]
#     countries_gdf = gdf[gdf[country_col].isin(country_names_en)].copy()

#     if countries_gdf.empty:
#         return None

#     name_to_ru = {cfg["name_en"]: name_ru for name_ru, cfg in COUNTRIES_CONFIG.items()}
#     countries_gdf["name_ru"] = countries_gdf[country_col].map(name_to_ru)

#     return countries_gdf


# def _label_box(ax, x, y, title, value, warehouses, in_transit, *, fontsize=8.8, zorder=20):
#     text = (
#         f"{title}\n"
#         f"{format_number(value)}\n"
#         f"скл.: {int(warehouses or 0)}  ·  в пути: {format_number_compact(in_transit)}"
#     )

#     ax.text(
#         x,
#         y,
#         text,
#         ha="center",
#         va="center",
#         fontsize=fontsize,
#         color=COLOR_TEXT,
#         fontweight="semibold",
#         linespacing=1.15,
#         zorder=zorder,
#         bbox=dict(
#             boxstyle="round,pad=0.36,rounding_size=0.12",
#             facecolor=COLOR_LABEL_BG,
#             edgecolor=COLOR_BORDER_DARK,
#             linewidth=0.75,
#             alpha=0.97,
#         ),
#     )


# def _country_label_position(country_name: str):
#     """
#     Ручные позиции подписей, чтобы мелкие страны не накладывались друг на друга.
#     """
#     positions = {
#         "Беларусь": (25.0, 52.8),
#         "Грузия": (42.2, 42.0),
#         "Армения": (46.2, 39.6),
#         "Казахстан": (66.0, 48.6),
#         "Узбекистан": (64.4, 41.0),
#         "Таджикистан": (73.3, 38.6),
#     }
#     return positions.get(country_name, COUNTRIES_CONFIG[country_name]["center"])


# def _prepare_stats(region_stats: pd.DataFrame) -> pd.DataFrame:
#     region_stats = region_stats.copy()

#     required_cols = ["регион", "на_складе", "в_пути", "складов", "итого"]
#     for col in required_cols:
#         if col not in region_stats.columns:
#             raise ValueError(f"В region_stats отсутствует колонка: {col}")

#     region_stats["регион"] = region_stats["регион"].astype(str).str.strip()
#     region_stats["на_складе"] = pd.to_numeric(region_stats["на_складе"], errors="coerce").fillna(0)
#     region_stats["в_пути"] = pd.to_numeric(region_stats["в_пути"], errors="coerce").fillna(0)
#     region_stats["складов"] = pd.to_numeric(region_stats["складов"], errors="coerce").fillna(0).astype(int)
#     region_stats["итого"] = pd.to_numeric(region_stats["итого"], errors="coerce").fillna(0)

#     return region_stats


# def build_russia_regions_map(region_stats: pd.DataFrame, report_date: str) -> io.BytesIO:
#     if gpd is None:
#         raise ImportError("Установите geopandas: pip install geopandas")

#     if region_stats.empty:
#         raise ValueError("Нет данных для построения карты")

#     region_stats = _prepare_stats(region_stats)

#     russia_stats = region_stats[region_stats["регион"].isin(WAREHOUSE_REGIONS)].copy()
#     countries_stats = region_stats[region_stats["регион"].isin(COUNTRIES_CONFIG.keys())].copy()
#     unmapped_stats = region_stats[
#         ~(
#             region_stats["регион"].isin(WAREHOUSE_REGIONS)
#             | region_stats["регион"].isin(COUNTRIES_CONFIG.keys())
#         )
#     ].copy()

#     russia_districts = _prepare_russia_geometries()
#     countries_geoms = _prepare_countries_geometries()

#     fig, ax = plt.subplots(figsize=(20, 9.5), dpi=200)
#     fig.patch.set_facecolor(COLOR_BG)
#     ax.set_facecolor(COLOR_BG)

#     cmap = _build_cmap()

#     russia_with_data = russia_districts.merge(
#         russia_stats[["регион", "на_складе", "в_пути", "складов", "итого"]],
#         how="left",
#         left_on="district",
#         right_on="регион",
#     )

#     for col in ["итого", "на_складе", "в_пути", "складов"]:
#         russia_with_data[col] = russia_with_data[col].fillna(0)

#     russia_with_data["складов"] = russia_with_data["складов"].astype(int)

#     countries_with_data = None
#     if countries_geoms is not None and not countries_geoms.empty:
#         countries_with_data = countries_geoms.merge(
#             countries_stats[["регион", "на_складе", "в_пути", "складов", "итого"]],
#             how="left",
#             left_on="name_ru",
#             right_on="регион",
#         )

#         for col in ["итого", "на_складе", "в_пути", "складов"]:
#             countries_with_data[col] = countries_with_data[col].fillna(0)

#         countries_with_data["складов"] = countries_with_data["складов"].astype(int)

#     all_values = []
#     all_values.extend(russia_with_data.loc[russia_with_data["итого"] > 0, "итого"].tolist())

#     if countries_with_data is not None:
#         all_values.extend(countries_with_data.loc[countries_with_data["итого"] > 0, "итого"].tolist())

#     if all_values:
#         vmin = max(float(min(all_values)), 1)
#         vmax = float(max(all_values))
#         norm = mcolors.PowerNorm(gamma=0.42, vmin=vmin, vmax=vmax)
#     else:
#         norm = mcolors.Normalize(vmin=0, vmax=1)

#     # Фон стран
#     if countries_with_data is not None and not countries_with_data.empty:
#         countries_with_data.plot(
#             ax=ax,
#             color=COLOR_BASE,
#             edgecolor=COLOR_BORDER,
#             linewidth=0.7,
#             zorder=1,
#         )

#     # Фон российских округов
#     russia_with_data.plot(
#         ax=ax,
#         color=COLOR_BASE,
#         edgecolor=COLOR_BORDER,
#         linewidth=0.8,
#         zorder=2,
#     )

#     # Заливка стран с остатками
#     if countries_with_data is not None and not countries_with_data.empty:
#         colored_countries = countries_with_data[countries_with_data["итого"] > 0].copy()
#         if not colored_countries.empty:
#             colored_countries.plot(
#                 ax=ax,
#                 column="итого",
#                 cmap=cmap,
#                 norm=norm,
#                 edgecolor=COLOR_BORDER_DARK,
#                 linewidth=0.95,
#                 zorder=4,
#             )

#     # Заливка российских округов с остатками
#     colored_russia = russia_with_data[russia_with_data["итого"] > 0].copy()
#     if not colored_russia.empty:
#         colored_russia.plot(
#             ax=ax,
#             column="итого",
#             cmap=cmap,
#             norm=norm,
#             edgecolor="#F8FBF9",
#             linewidth=1.25,
#             zorder=5,
#         )

#         # Внешняя обводка окрашенных регионов
#         colored_russia.boundary.plot(
#             ax=ax,
#             color=COLOR_BORDER_DARK,
#             linewidth=0.55,
#             zorder=6,
#         )

#     if countries_with_data is not None and not countries_with_data.empty:
#         countries_with_data.boundary.plot(
#             ax=ax,
#             color=COLOR_BORDER_DARK,
#             linewidth=0.45,
#             zorder=7,
#             alpha=0.75,
#         )

#     # Подписи российских регионов
#     for _, row in russia_with_data.iterrows():
#         qty = float(row["итого"])
#         if qty <= 0:
#             continue

#         district = row["district"]
#         x, y = LABEL_POINTS.get(district, (None, None))

#         if x is None:
#             point = row.geometry.representative_point()
#             x, y = point.x, point.y

#         _label_box(
#             ax,
#             x,
#             y,
#             district,
#             qty,
#             int(row["складов"]),
#             float(row["в_пути"]),
#             fontsize=8.6 if len(district) < 20 else 8.0,
#         )

#     # Подписи стран
#     for _, row in countries_stats.iterrows():
#         country_name = row["регион"]
#         qty = float(row["итого"])

#         if qty <= 0 or country_name not in COUNTRIES_CONFIG:
#             continue

#         x, y = _country_label_position(country_name)

#         _label_box(
#             ax,
#             x,
#             y,
#             country_name,
#             qty,
#             int(row["складов"]),
#             float(row["в_пути"]),
#             fontsize=8.2,
#             zorder=25,
#         )

#     # Цветовая шкала
#     if all_values:
#         sm = ScalarMappable(norm=norm, cmap=cmap)
#         sm.set_array([])

#         cbar = fig.colorbar(
#             sm,
#             ax=ax,
#             orientation="vertical",
#             fraction=0.018,
#             pad=0.012,
#             shrink=0.72,
#         )

#         cbar.outline.set_edgecolor(COLOR_BORDER_DARK)
#         cbar.outline.set_linewidth(0.6)
#         cbar.ax.yaxis.set_major_formatter(FuncFormatter(_format_tick))
#         cbar.ax.tick_params(labelsize=8.5, colors=COLOR_MUTED, length=0)
#         cbar.set_label(
#             "Остатки, шт",
#             fontsize=9.5,
#             color=COLOR_TEXT,
#             labelpad=10,
#             fontweight="semibold",
#         )

#     ax.set_title(
#         f"География остатков товаров\nна {report_date}",
#         fontsize=18,
#         fontweight="bold",
#         color=COLOR_TEXT,
#         pad=18,
#         linespacing=1.05,
#     )

#     # Важно: обрезаем лишний низ и делаем карту крупнее.
#     # Раньше ylim начинался с 40, из-за этого Таджикистан был почти на границе,
#     # а ниже оставалось пустое поле. Теперь диапазон аккуратнее.
#     ax.set_xlim(20, 178)
#     ax.set_ylim(37.2, 75.8)

#     # Блок "не распределено" показываем только если есть сумма
#     if not unmapped_stats.empty and float(unmapped_stats["итого"].sum()) > 0:
#         unmapped_total = float(unmapped_stats["итого"].sum())

#         ax.text(
#             0.018,
#             0.035,
#             f"Не распределено: {format_number(unmapped_total)}",
#             transform=ax.transAxes,
#             ha="left",
#             va="bottom",
#             fontsize=8.5,
#             color=COLOR_MUTED,
#             zorder=30,
#             bbox=dict(
#                 boxstyle="round,pad=0.35,rounding_size=0.12",
#                 facecolor=COLOR_LABEL_BG,
#                 edgecolor=COLOR_BORDER,
#                 linewidth=0.7,
#                 alpha=0.96,
#             ),
#         )

#     ax.set_xticks([])
#     ax.set_yticks([])
#     ax.grid(False)

#     for spine in ax.spines.values():
#         spine.set_visible(False)

#     plt.subplots_adjust(left=0.015, right=0.965, top=0.88, bottom=0.035)

#     buffer = io.BytesIO()
#     fig.savefig(
#         buffer,
#         format="png",
#         dpi=200,
#         bbox_inches="tight",
#         facecolor=COLOR_BG,
#         pad_inches=0.12,
#     )
#     plt.close(fig)
#     buffer.seek(0)

#     return buffer


# build_regions_stock_map_png = build_russia_regions_map




# inventories/reporting/map/russia_regions_map.py
from __future__ import annotations

import io
import re
from typing import Dict, Optional

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

from .map_config import (
    COLOR_BG,
    COLOR_BASE,
    COLOR_TEXT,
    COLOR_MUTED,
    COLOR_PRIMARY,
    COLOR_BORDER,
    COLOR_BORDER_DARK,
    COLOR_LABEL_BG,
    WAREHOUSE_REGIONS,
    LABEL_POINTS,
    DISTRICT_KEYWORDS,
    COUNTRIES_CONFIG,
    get_russia_shapefile_path,
    get_world_shapefile_path,
)


def format_number(value: float) -> str:
    value = float(value or 0)
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f} млн шт"
    if value >= 1_000:
        return f"{value / 1_000:.1f} тыс шт"
    return f"{value:,.0f} шт".replace(",", " ")


def format_number_compact(value: float) -> str:
    value = float(value or 0)
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f} млн"
    if value >= 1_000:
        return f"{value / 1_000:.0f} тыс"
    return f"{value:,.0f}".replace(",", " ")


def _format_tick(value, _pos=None):
    value = float(value or 0)
    if value >= 1_000_000:
        return f"{value / 1_000_000:.1f} млн"
    if value >= 1_000:
        return f"{value / 1_000:.0f} тыс"
    return f"{value:,.0f}".replace(",", " ")


def _build_cmap():
    return mcolors.LinearSegmentedColormap.from_list(
        "stock_green",
        ["#EEF5F1", "#DCEBE4", "#BFD8CF", "#8FB8AA", "#4E8B7A", COLOR_PRIMARY],
        N=256,
    )


def _clean_text(value: object) -> str:
    s = str(value or "").lower()
    s = s.replace("’", "'")
    s = re.sub(r"[^a-zа-яё0-9]+", " ", s)
    return re.sub(r"\s+", " ", s).strip()


def _find_name_col(gdf: pd.DataFrame) -> str:
    candidates = [
        "name", "NAME", "name_en", "NAME_EN",
        "name_local", "NAME_LOCAL", "region",
        "province", "gn_name", "GN_NAME",
    ]
    for col in candidates:
        if col in gdf.columns:
            return col
    raise ValueError(f"Не найдена колонка с названием региона. Колонки: {list(gdf.columns)}")


def _filter_russia_if_possible(gdf):
    candidates = [
        "adm0_a3", "ADM0_A3",
        "iso_a2", "ISO_A2",
        "admin", "ADMIN",
        "geonunit", "GEOUNIT",
        "sov_a3", "SOV_A3",
    ]

    for col in candidates:
        if col not in gdf.columns:
            continue

        values = gdf[col].astype(str).str.upper()

        if col.upper() in {"ADM0_A3", "SOV_A3"}:
            mask = values.eq("RUS")
        elif col.upper() == "ISO_A2":
            mask = values.eq("RU")
        else:
            mask = values.str.contains(
                "RUSSIA|RUSSIAN FEDERATION|РОССИЯ|RUS",
                regex=True,
                na=False,
            )

        filtered = gdf[mask].copy()
        if not filtered.empty:
            return filtered

    return gdf


def _detect_district(region_name: object) -> str | None:
    text = _clean_text(region_name)
    for district, keywords in DISTRICT_KEYWORDS.items():
        for keyword in keywords:
            if keyword in text:
                return district
    return None


def _prepare_russia_geometries():
    shp_path = get_russia_shapefile_path()
    if not shp_path.exists():
        raise FileNotFoundError(f"Shapefile России не найден: {shp_path}")

    gdf = gpd.read_file(shp_path)
    gdf = _filter_russia_if_possible(gdf)

    name_col = _find_name_col(gdf)
    gdf["district"] = gdf[name_col].apply(_detect_district)

    matched_count = int(gdf["district"].notna().sum())
    if matched_count == 0:
        raise ValueError(
            f"Не удалось сопоставить регионы. Примеры: {gdf[name_col].head(10).tolist()}"
        )

    gdf = gdf[gdf["district"].notna() & gdf.geometry.notna()].copy()
    districts = gdf.dissolve(by="district", as_index=False)
    districts = districts[districts.geometry.notna()].copy()

    return districts


def _prepare_countries_geometries():
    shp_path = get_world_shapefile_path()
    if not shp_path.exists():
        return None

    gdf = gpd.read_file(shp_path)

    country_col = None
    for col in ["ADMIN", "NAME", "SOVEREIGNT", "admin", "name", "NAME_EN", "name_en", "COUNTRY"]:
        if col in gdf.columns:
            country_col = col
            break

    if country_col is None:
        return None

    country_names_en = [cfg["name_en"] for cfg in COUNTRIES_CONFIG.values()]
    countries_gdf = gdf[gdf[country_col].isin(country_names_en)].copy()

    if countries_gdf.empty:
        return None

    name_to_ru = {cfg["name_en"]: name_ru for name_ru, cfg in COUNTRIES_CONFIG.items()}
    countries_gdf["name_ru"] = countries_gdf[country_col].map(name_to_ru)

    return countries_gdf


def _label_box(ax, x, y, title, value, warehouses, in_transit, *, fontsize=8.8, zorder=20):
    text = (
        f"{title}\n"
        f"{format_number(value)}\n"
        f"скл.: {int(warehouses or 0)}  ·  в пути: {format_number_compact(in_transit)}"
    )

    ax.text(
        x,
        y,
        text,
        ha="center",
        va="center",
        fontsize=fontsize,
        color=COLOR_TEXT,
        fontweight="semibold",
        linespacing=1.15,
        zorder=zorder,
        bbox=dict(
            boxstyle="round,pad=0.36,rounding_size=0.12",
            facecolor=COLOR_LABEL_BG,
            edgecolor=COLOR_BORDER_DARK,
            linewidth=0.75,
            alpha=0.97,
        ),
    )


def _country_label_position(country_name: str):
    positions = {
        "Беларусь": (25.0, 52.8),
        "Грузия": (42.2, 42.0),
        "Армения": (46.2, 39.6),
        "Казахстан": (66.0, 48.6),
        "Узбекистан": (64.4, 41.0),
        "Таджикистан": (73.3, 38.6),
    }
    return positions.get(country_name, COUNTRIES_CONFIG[country_name]["center"])


def _prepare_stats(region_stats: pd.DataFrame) -> pd.DataFrame:
    region_stats = region_stats.copy()

    required_cols = ["регион", "на_складе", "в_пути", "складов", "итого"]
    for col in required_cols:
        if col not in region_stats.columns:
            raise ValueError(f"В region_stats отсутствует колонка: {col}")

    region_stats["регион"] = region_stats["регион"].astype(str).str.strip()
    region_stats["на_складе"] = pd.to_numeric(region_stats["на_складе"], errors="coerce").fillna(0)
    region_stats["в_пути"] = pd.to_numeric(region_stats["в_пути"], errors="coerce").fillna(0)
    region_stats["складов"] = pd.to_numeric(region_stats["складов"], errors="coerce").fillna(0).astype(int)
    region_stats["итого"] = pd.to_numeric(region_stats["итого"], errors="coerce").fillna(0)

    return region_stats


def build_russia_regions_map(
    region_stats: pd.DataFrame, 
    report_date: str, 
    summary_stats: Optional[Dict] = None
) -> io.BytesIO:
    """
    Построение карты регионов с остатками товаров.
    
    Args:
        region_stats: DataFrame с колонками ['регион', 'на_складе', 'в_пути', 'складов', 'итого']
        report_date: Дата отчета в формате строки
        summary_stats: Словарь со сводной статистикой от get_summary_stats()
    
    Returns:
        BytesIO объект с PNG изображением карты
    """
    if gpd is None:
        raise ImportError("Установите geopandas: pip install geopandas")

    if region_stats.empty:
        raise ValueError("Нет данных для построения карты")

    region_stats = _prepare_stats(region_stats)

    russia_stats = region_stats[region_stats["регион"].isin(WAREHOUSE_REGIONS)].copy()
    countries_stats = region_stats[region_stats["регион"].isin(COUNTRIES_CONFIG.keys())].copy()
    unmapped_stats = region_stats[
        ~(
            region_stats["регион"].isin(WAREHOUSE_REGIONS)
            | region_stats["регион"].isin(COUNTRIES_CONFIG.keys())
        )
    ].copy()

    russia_districts = _prepare_russia_geometries()
    countries_geoms = _prepare_countries_geometries()

    fig, ax = plt.subplots(figsize=(20, 9.5), dpi=200)
    fig.patch.set_facecolor(COLOR_BG)
    ax.set_facecolor(COLOR_BG)

    cmap = _build_cmap()

    russia_with_data = russia_districts.merge(
        russia_stats[["регион", "на_складе", "в_пути", "складов", "итого"]],
        how="left",
        left_on="district",
        right_on="регион",
    )

    for col in ["итого", "на_складе", "в_пути", "складов"]:
        russia_with_data[col] = russia_with_data[col].fillna(0)

    russia_with_data["складов"] = russia_with_data["складов"].astype(int)

    countries_with_data = None
    if countries_geoms is not None and not countries_geoms.empty:
        countries_with_data = countries_geoms.merge(
            countries_stats[["регион", "на_складе", "в_пути", "складов", "итого"]],
            how="left",
            left_on="name_ru",
            right_on="регион",
        )

        for col in ["итого", "на_складе", "в_пути", "складов"]:
            countries_with_data[col] = countries_with_data[col].fillna(0)

        countries_with_data["складов"] = countries_with_data["складов"].astype(int)

    all_values = []
    all_values.extend(russia_with_data.loc[russia_with_data["итого"] > 0, "итого"].tolist())

    if countries_with_data is not None:
        all_values.extend(countries_with_data.loc[countries_with_data["итого"] > 0, "итого"].tolist())

    if all_values:
        vmin = max(float(min(all_values)), 1)
        vmax = float(max(all_values))
        norm = mcolors.PowerNorm(gamma=0.42, vmin=vmin, vmax=vmax)
    else:
        norm = mcolors.Normalize(vmin=0, vmax=1)

    # Фон стран
    if countries_with_data is not None and not countries_with_data.empty:
        countries_with_data.plot(
            ax=ax,
            color=COLOR_BASE,
            edgecolor=COLOR_BORDER,
            linewidth=0.7,
            zorder=1,
        )

    # Фон российских округов
    russia_with_data.plot(
        ax=ax,
        color=COLOR_BASE,
        edgecolor=COLOR_BORDER,
        linewidth=0.8,
        zorder=2,
    )

    # Заливка стран с остатками
    if countries_with_data is not None and not countries_with_data.empty:
        colored_countries = countries_with_data[countries_with_data["итого"] > 0].copy()
        if not colored_countries.empty:
            colored_countries.plot(
                ax=ax,
                column="итого",
                cmap=cmap,
                norm=norm,
                edgecolor=COLOR_BORDER_DARK,
                linewidth=0.95,
                zorder=4,
            )

    # Заливка российских округов с остатками
    colored_russia = russia_with_data[russia_with_data["итого"] > 0].copy()
    if not colored_russia.empty:
        colored_russia.plot(
            ax=ax,
            column="итого",
            cmap=cmap,
            norm=norm,
            edgecolor="#F8FBF9",
            linewidth=1.25,
            zorder=5,
        )

        colored_russia.boundary.plot(
            ax=ax,
            color=COLOR_BORDER_DARK,
            linewidth=0.55,
            zorder=6,
        )

    if countries_with_data is not None and not countries_with_data.empty:
        countries_with_data.boundary.plot(
            ax=ax,
            color=COLOR_BORDER_DARK,
            linewidth=0.45,
            zorder=7,
            alpha=0.75,
        )

    # Подписи российских регионов
    for _, row in russia_with_data.iterrows():
        qty = float(row["итого"])
        if qty <= 0:
            continue

        district = row["district"]
        x, y = LABEL_POINTS.get(district, (None, None))

        if x is None:
            point = row.geometry.representative_point()
            x, y = point.x, point.y

        _label_box(
            ax,
            x,
            y,
            district,
            qty,
            int(row["складов"]),
            float(row["в_пути"]),
            fontsize=8.6 if len(district) < 20 else 8.0,
        )

    # Подписи стран
    for _, row in countries_stats.iterrows():
        country_name = row["регион"]
        qty = float(row["итого"])

        if qty <= 0 or country_name not in COUNTRIES_CONFIG:
            continue

        x, y = _country_label_position(country_name)

        _label_box(
            ax,
            x,
            y,
            country_name,
            qty,
            int(row["складов"]),
            float(row["в_пути"]),
            fontsize=8.2,
            zorder=25,
        )

    # Цветовая шкала
    if all_values:
        sm = ScalarMappable(norm=norm, cmap=cmap)
        sm.set_array([])

        cbar = fig.colorbar(
            sm,
            ax=ax,
            orientation="vertical",
            fraction=0.018,
            pad=0.012,
            shrink=0.72,
        )

        cbar.outline.set_edgecolor(COLOR_BORDER_DARK)
        cbar.outline.set_linewidth(0.6)
        cbar.ax.yaxis.set_major_formatter(FuncFormatter(_format_tick))
        cbar.ax.tick_params(labelsize=8.5, colors=COLOR_MUTED, length=0)
        cbar.set_label(
            "Остатки, шт",
            fontsize=9.5,
            color=COLOR_TEXT,
            labelpad=10,
            fontweight="semibold",
        )

    # ─────────────────────────────────────────────────────────────────────────
    # Заголовок со сводной статистикой (строгий профессиональный стиль)
    # ─────────────────────────────────────────────────────────────────────────
    
    if summary_stats is not None:
        total_warehouses = summary_stats.get(
            "total_warehouses",
            0,
        )

        total_on_hand = summary_stats.get(
            "total_on_hand",
            0,
        )

        total_fbs = summary_stats.get(
            "total_fbs",
            0,
        )

        total_in_transit = summary_stats.get(
            "total_in_transit",
            0,
        )

        total_all = summary_stats.get(
            "total_quantity",
            0,
        )

        # ----------------------------------------------------------
        # Форматируем числа
        # ----------------------------------------------------------
        on_hand_str = format_number(
            total_on_hand
        )

        fbs_str = format_number(
            total_fbs
        )

        in_transit_str = format_number(
            total_in_transit
        )

        total_str = format_number(
            total_all
        )

        # ----------------------------------------------------------
        # Заголовок карты
        # ----------------------------------------------------------
        title_text = (
            f"География остатков товаров\n"
            f"на {report_date}\n"
            f"\n"
            f"Всего складов WB: {total_warehouses}"
            f"    |    "
            f"На складах WB: {on_hand_str}"
            f"    |    "
            f"FBS — наш склад: {fbs_str}"
            f"    |    "
            f"В пути: {in_transit_str}"
            f"    |    "
            f"Итого: {total_str}"
        )

        title_fontsize = 14
        title_linespace = 1.25
    else:
        title_text = f"География остатков товаров\nна {report_date}"
        title_fontsize = 18
        title_linespace = 1.05

    ax.set_title(
        title_text,
        fontsize=title_fontsize,
        fontweight="bold",
        color=COLOR_TEXT,
        pad=22,
        linespacing=title_linespace,
        fontfamily="sans-serif",
    )

    # Границы карты
    ax.set_xlim(20, 178)
    ax.set_ylim(37.2, 75.8)

    # Блок "не распределено"
    if not unmapped_stats.empty and float(unmapped_stats["итого"].sum()) > 0:
        unmapped_total = float(unmapped_stats["итого"].sum())

        ax.text(
            0.018,
            0.035,
            f"Не распределено: {format_number(unmapped_total)}",
            transform=ax.transAxes,
            ha="left",
            va="bottom",
            fontsize=8.5,
            color=COLOR_MUTED,
            zorder=30,
            bbox=dict(
                boxstyle="round,pad=0.35,rounding_size=0.12",
                facecolor=COLOR_LABEL_BG,
                edgecolor=COLOR_BORDER,
                linewidth=0.7,
                alpha=0.96,
            ),
        )

    ax.set_xticks([])
    ax.set_yticks([])
    ax.grid(False)

    for spine in ax.spines.values():
        spine.set_visible(False)

    plt.subplots_adjust(left=0.015, right=0.965, top=0.92, bottom=0.035)

    buffer = io.BytesIO()
    fig.savefig(
        buffer,
        format="png",
        dpi=200,
        bbox_inches="tight",
        facecolor=COLOR_BG,
        pad_inches=0.12,
    )
    plt.close(fig)
    buffer.seek(0)

    return buffer


build_regions_stock_map_png = build_russia_regions_map