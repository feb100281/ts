# gear/app/daily_sales/daily_brief/presentation/pages/stocks_charts.py


from __future__ import annotations

import base64
import io
import re

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

from inventories.reporting.map.map_config import (
    COUNTRIES_CONFIG,
    DISTRICT_KEYWORDS,
    LABEL_POINTS,
    WAREHOUSE_REGIONS,
    get_russia_shapefile_path,
    get_world_shapefile_path,
)

from ...helpers import number


# =============================================================================
# ПАЛИТРА ТОВАРНОГО РАЗВОРОТА
# =============================================================================


COLOR_PAPER = "#FFFDF7"

COLOR_TEXT = "#14213D"
COLOR_MUTED = "#667085"

COLOR_BORDER = "#D7DCE2"
COLOR_BORDER_DARK = "#8E96A3"

COLOR_MAP_EMPTY = "#F0ECE6"
COLOR_MAP_LIGHT = "#F9EDEF"
COLOR_MAP_SOFT = "#EFC9D1"
COLOR_MAP_MIDDLE = "#DC8D9D"
COLOR_MAP_PRIMARY = "#E85D75"
COLOR_MAP_DARK = "#973B50"

COLOR_LABEL_BG = "#FFFDF9"


# =============================================================================
# ПОЛОЖЕНИЯ ПОДПИСЕЙ СТРАН
# =============================================================================
#
# Эти координаты относятся только к карте daily_brief.
# Они немного отличаются от географических центров стран,
# чтобы подписи не накладывались друг на друга.
# =============================================================================


COUNTRY_LABEL_POINTS = {
    "Беларусь": (
        25.0,
        52.8,
    ),
    "Грузия": (
        42.2,
        42.0,
    ),
    "Армения": (
        46.2,
        39.6,
    ),
    "Казахстан": (
        66.0,
        48.6,
    ),
    "Узбекистан": (
        64.4,
        41.0,
    ),
    "Таджикистан": (
        73.3,
        38.6,
    ),
}


# =============================================================================
# ОБЩИЕ ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =============================================================================


def _data_uri(
    fig,
    *,
    facecolor: str = COLOR_PAPER,
    dpi: int = 180,
    pad_inches: float = 0.08,
) -> str:
    """
    Сохраняет matplotlib Figure в PNG и возвращает
    готовый base64 data URI.

    Его можно напрямую вставлять в HTML:

        <img src="data:image/png;base64,...">
    """

    buffer = io.BytesIO()

    fig.savefig(
        buffer,
        format="png",
        dpi=dpi,
        bbox_inches="tight",
        facecolor=facecolor,
        pad_inches=pad_inches,
    )

    plt.close(fig)

    buffer.seek(0)

    encoded = base64.b64encode(
        buffer.read()
    ).decode(
        "ascii"
    )

    return (
        "data:image/png;base64,"
        + encoded
    )


def _compact_number(
    value,
    *,
    digits: int = 1,
) -> str:
    """
    Компактное форматирование чисел для подписей карты.

    Примеры:
        1250       -> 1,2 тыс
        1520000    -> 1,5 млн
        850        -> 850
    """

    value = float(
        value
        or 0
    )

    if abs(value) >= 1_000_000:
        return (
            f"{value / 1_000_000:.{digits}f} млн"
            .replace(".", ",")
        )

    if abs(value) >= 1_000:
        return (
            f"{value / 1_000:.{digits}f} тыс"
            .replace(".", ",")
        )

    return (
        f"{value:,.0f}"
        .replace(",", " ")
    )


def _compact_tick(
    value,
    _pos=None,
) -> str:
    """
    Формат значений на цветовой шкале карты.
    """

    value = float(
        value
        or 0
    )

    if abs(value) >= 1_000_000:
        return (
            f"{value / 1_000_000:.1f} млн"
            .replace(".", ",")
        )

    if abs(value) >= 1_000:
        return (
            f"{value / 1_000:.0f} тыс"
            .replace(".", ",")
        )

    return (
        f"{value:,.0f}"
        .replace(",", " ")
    )


def _format_report_date(
    value,
) -> str:
    """
    Приводит дату отчёта к формату ДД.ММ.ГГГГ.
    """

    parsed = pd.to_datetime(
        value,
        errors="coerce",
    )

    if pd.isna(parsed):
        return str(
            value
            or ""
        )

    return parsed.strftime(
        "%d.%m.%Y"
    )


def _clean_text(
    value,
) -> str:
    """
    Нормализует название территории.

    Используется при сопоставлении названий
    административных регионов из shapefile
    с укрупнёнными складскими зонами.
    """

    text = (
        str(
            value
            or ""
        )
        .lower()
        .replace("ё", "е")
        .replace("’", "'")
    )

    text = re.sub(
        r"[^a-zа-я0-9]+",
        " ",
        text,
    )

    return re.sub(
        r"\s+",
        " ",
        text,
    ).strip()


# =============================================================================
# ЦВЕТОВАЯ ШКАЛА
# =============================================================================


def _build_brief_map_cmap():
    """
    Кораллово-бордовая палитра карты daily_brief.
    """

    return (
        mcolors.LinearSegmentedColormap.from_list(
            "daily_brief_inventory",
            [
                COLOR_MAP_LIGHT,
                COLOR_MAP_SOFT,
                COLOR_MAP_MIDDLE,
                COLOR_MAP_PRIMARY,
                COLOR_MAP_DARK,
            ],
            N=256,
        )
    )


# =============================================================================
# SHAPEFILE — ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# =============================================================================


def _find_name_column(
    frame: pd.DataFrame,
) -> str:
    """
    Находит в shapefile колонку,
    содержащую название территории.
    """

    candidates = [
        "name",
        "NAME",
        "name_en",
        "NAME_EN",
        "name_local",
        "NAME_LOCAL",
        "region",
        "REGION",
        "province",
        "PROVINCE",
        "gn_name",
        "GN_NAME",
    ]

    for column in candidates:
        if column in frame.columns:
            return column

    raise ValueError(
        "Не найдена колонка с названием территории. "
        f"Колонки: {list(frame.columns)}"
    )


def _filter_russia(
    frame,
):
    """
    Оставляет российские административные регионы,
    если shapefile содержит соответствующий код страны.

    Если определить код страны невозможно,
    возвращается исходный набор геометрий.
    """

    checks = {
        "adm0_a3": (
            "RUS",
        ),
        "ADM0_A3": (
            "RUS",
        ),
        "sov_a3": (
            "RUS",
        ),
        "SOV_A3": (
            "RUS",
        ),
        "iso_a2": (
            "RU",
        ),
        "ISO_A2": (
            "RU",
        ),
    }

    for column, values in checks.items():
        if column not in frame.columns:
            continue

        result = frame[
            frame[column]
            .astype(str)
            .str.upper()
            .isin(values)
        ].copy()

        if not result.empty:
            return result

    for column in [
        "admin",
        "ADMIN",
        "geonunit",
        "GEOUNIT",
    ]:
        if column not in frame.columns:
            continue

        result = frame[
            frame[column]
            .astype(str)
            .str.upper()
            .str.contains(
                "RUSSIA|RUSSIAN",
                na=False,
            )
        ].copy()

        if not result.empty:
            return result

    return frame.copy()


def _detect_warehouse_region(
    shape_name,
) -> str | None:
    """
    Определяет укрупнённую складскую зону
    по названию административного региона shapefile.
    """

    cleaned_name = _clean_text(
        shape_name
    )

    for district, keywords in (
        DISTRICT_KEYWORDS.items()
    ):
        for keyword in keywords:
            cleaned_keyword = (
                _clean_text(
                    keyword
                )
            )

            if (
                cleaned_keyword
                and cleaned_keyword
                in cleaned_name
            ):
                return district

    return None


# =============================================================================
# ГЕОМЕТРИЯ РОССИИ
# =============================================================================


def _prepare_russia_district_geometries():
    """
    Загружает административные регионы России
    и объединяет их в складские зоны,
    определённые в map_config.py.
    """

    if gpd is None:
        raise ImportError(
            "Для построения карты установите geopandas: "
            "pip install geopandas"
        )

    shapefile_path = (
        get_russia_shapefile_path()
    )

    if not shapefile_path.exists():
        raise FileNotFoundError(
            "Shapefile регионов России не найден: "
            f"{shapefile_path}"
        )

    frame = gpd.read_file(
        shapefile_path
    )

    frame = _filter_russia(
        frame
    )

    if frame.empty:
        raise ValueError(
            "После фильтрации в shapefile "
            "не осталось регионов России."
        )

    name_column = _find_name_column(
        frame
    )

    frame = frame.copy()

    frame["warehouse_region"] = (
        frame[name_column]
        .apply(
            _detect_warehouse_region
        )
    )

    frame = frame[
        frame[
            "warehouse_region"
        ].notna()
    ].copy()

    if frame.empty:
        raise ValueError(
            "Не удалось сопоставить административные "
            "регионы со складскими зонами из map_config.py."
        )

    # Исправляет возможные некорректные геометрии.
    frame["geometry"] = (
        frame.geometry.buffer(0)
    )

    dissolved = frame.dissolve(
        by="warehouse_region",
        as_index=False,
    )

    return dissolved


# =============================================================================
# ГЕОМЕТРИЯ ДРУГИХ СТРАН
# =============================================================================


def _prepare_country_geometries():
    """
    Загружает геометрию стран,
    перечисленных в COUNTRIES_CONFIG.
    """

    if gpd is None:
        raise ImportError(
            "Для построения карты установите geopandas: "
            "pip install geopandas"
        )

    shapefile_path = (
        get_world_shapefile_path()
    )

    if not shapefile_path.exists():
        raise FileNotFoundError(
            "Мировой shapefile не найден: "
            f"{shapefile_path}"
        )

    world = gpd.read_file(
        shapefile_path
    )

    name_column = _find_name_column(
        world
    )

    rows = []

    for russian_name, config in (
        COUNTRIES_CONFIG.items()
    ):
        english_name = str(
            config.get(
                "name_en",
                "",
            )
        ).strip()

        if not english_name:
            continue

        mask = (
            world[name_column]
            .astype(str)
            .str.strip()
            .str.casefold()
            .eq(
                english_name.casefold()
            )
        )

        selected = world[
            mask
        ].copy()

        if selected.empty:
            continue

        geometry = (
            selected.geometry
            .buffer(0)
            .unary_union
        )

        rows.append(
            {
                "warehouse_region": (
                    russian_name
                ),
                "geometry": geometry,
            }
        )

    if not rows:
        return gpd.GeoDataFrame(
            columns=[
                "warehouse_region",
                "geometry",
            ],
            geometry="geometry",
            crs=world.crs,
        )

    return gpd.GeoDataFrame(
        rows,
        geometry="geometry",
        crs=world.crs,
    )


# =============================================================================
# ПОДГОТОВКА ДАННЫХ PAYLOAD
# =============================================================================


def _prepare_map_stats(
    regions: list[dict],
) -> pd.DataFrame:
    """
    Приводит данные payload к единому формату карты.

    Итоговые поля:
        region
        on_hand
        in_transit
        warehouses
        total_qty
    """

    frame = pd.DataFrame(
        regions
        or []
    )

    if frame.empty:
        return frame

    rename_candidates = {
        "name": "region",
        "регион": "region",

        "warehouse_count": (
            "warehouses"
        ),
        "warehouses_count": (
            "warehouses"
        ),
        "складов": "warehouses",

        "warehouse_quantity": (
            "on_hand"
        ),
        "на_складе": "on_hand",

        "in_transit_quantity": (
            "in_transit"
        ),
        "в_пути": "in_transit",

        "stock_quantity": (
            "total_qty"
        ),
        "total_quantity": (
            "total_qty"
        ),
        "итого": "total_qty",
    }

    rename_map = {}

    for source, target in (
        rename_candidates.items()
    ):
        if (
            source in frame.columns
            and target not in frame.columns
        ):
            rename_map[source] = target

    if rename_map:
        frame = frame.rename(
            columns=rename_map
        )

    required = [
        "region",
        "on_hand",
        "in_transit",
        "warehouses",
        "total_qty",
    ]

    for column in required:
        if column not in frame.columns:
            if column == "region":
                frame[column] = ""
            else:
                frame[column] = 0

    frame["region"] = (
        frame["region"]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    for column in [
        "on_hand",
        "in_transit",
        "warehouses",
        "total_qty",
    ]:
        frame[column] = pd.to_numeric(
            frame[column],
            errors="coerce",
        ).fillna(0)

    # Если total_qty почему-то не заполнен,
    # восстанавливаем его как склад + товар в пути.
    missing_total = (
        frame["total_qty"]
        <= 0
    )

    frame.loc[
        missing_total,
        "total_qty",
    ] = (
        frame.loc[
            missing_total,
            "on_hand",
        ]
        + frame.loc[
            missing_total,
            "in_transit",
        ]
    )

    frame = frame[
        frame["region"].ne("")
        & frame["total_qty"].gt(0)
    ].copy()

    return frame


# =============================================================================
# ПОДПИСИ НА КАРТЕ
# =============================================================================


def _draw_map_label(
    ax,
    *,
    x: float,
    y: float,
    name: str,
    total_qty: float,
    warehouses: int,
    in_transit: float,
    fontsize: float = 6.4,
):
    """
    Рисует газетную подпись региона или страны.
    """

    label = (
        f"{name}\n"
        f"{_compact_number(total_qty)} шт\n"
        f"скл.: {warehouses}"
        f" · в пути: "
        f"{_compact_number(in_transit, digits=0)}"
    )

    ax.text(
        x,
        y,
        label,
        ha="center",
        va="center",
        fontsize=fontsize,
        color=COLOR_TEXT,
        fontweight="bold",
        linespacing=1.12,
        zorder=8,
        bbox={
            "boxstyle": (
                "square,pad=0.28"
            ),
            "facecolor": (
                COLOR_LABEL_BG
            ),
            "edgecolor": (
                COLOR_BORDER_DARK
            ),
            "linewidth": 0.55,
            "alpha": 0.97,
        },
    )


# =============================================================================
# КАРТА ОСТАТКОВ
# =============================================================================


def stock_map(
    regions: list[dict],
    report_date: str,
    summary: dict,
) -> str | None:
    """
    Газетная карта распределения товарного запаса.

    Использует:
    - общие shapefile проекта;
    - справочник регионов inventories.reporting.map.map_config;
    - данные об остатках из payload daily_brief.

    Не использует и не изменяет стандартную зелёную карту проекта.

    Возвращает:
        PNG в формате base64 data URI.

    Если карту построить невозможно:
        None
    """

    if not regions:
        return None

    if gpd is None:
        print(
            "DAILY BRIEF MAP: geopandas не установлен"
        )

        return None

    try:
        # ---------------------------------------------------------------------
        # Данные
        # ---------------------------------------------------------------------

        stats = _prepare_map_stats(
            regions
        )

        if stats.empty:
            return None

        russia_stats = stats[
            stats["region"].isin(
                WAREHOUSE_REGIONS
            )
        ].copy()

        country_stats = stats[
            stats["region"].isin(
                COUNTRIES_CONFIG.keys()
            )
        ].copy()

        if (
            russia_stats.empty
            and country_stats.empty
        ):
            print(
                "DAILY BRIEF MAP: нет строк с регионами, "
                "которые известны map_config.py"
            )

            return None

        # ---------------------------------------------------------------------
        # Геометрия
        # ---------------------------------------------------------------------

        russia_geometries = (
            _prepare_russia_district_geometries()
        )

        country_geometries = (
            _prepare_country_geometries()
        )

        stats_index = (
            stats.set_index(
                "region"
            )
        )

        # ---------------------------------------------------------------------
        # Значения для российских складских зон
        # ---------------------------------------------------------------------

        russia_geometries = (
            russia_geometries.copy()
        )

        russia_geometries[
            "total_qty"
        ] = (
            russia_geometries[
                "warehouse_region"
            ]
            .map(
                stats_index[
                    "total_qty"
                ]
            )
            .fillna(0)
        )

        # ---------------------------------------------------------------------
        # Значения для стран
        # ---------------------------------------------------------------------

        if not country_geometries.empty:
            country_geometries = (
                country_geometries.copy()
            )

            country_geometries[
                "total_qty"
            ] = (
                country_geometries[
                    "warehouse_region"
                ]
                .map(
                    stats_index[
                        "total_qty"
                    ]
                )
                .fillna(0)
            )

        # ---------------------------------------------------------------------
        # Цветовая шкала
        # ---------------------------------------------------------------------

        maximum = float(
            max(
                stats[
                    "total_qty"
                ].max(),
                1,
            )
        )

        cmap = (
            _build_brief_map_cmap()
        )

        # PowerNorm позволяет Центральному региону
        # не «поглотить» цветом остальные территории.
        norm = mcolors.PowerNorm(
            gamma=0.42,
            vmin=0,
            vmax=maximum,
        )

        # ---------------------------------------------------------------------
        # Figure
        # ---------------------------------------------------------------------

        fig, ax = plt.subplots(
            figsize=(
                17.5,
                6.8,
            ),
            dpi=180,
        )

        fig.patch.set_facecolor(
            COLOR_PAPER
        )

        ax.set_facecolor(
            COLOR_PAPER
        )

        # ---------------------------------------------------------------------
        # Базовая геометрия России
        # ---------------------------------------------------------------------

        russia_geometries.plot(
            ax=ax,
            color=COLOR_MAP_EMPTY,
            edgecolor=COLOR_BORDER,
            linewidth=0.38,
            zorder=1,
        )

        # ---------------------------------------------------------------------
        # Российские зоны с остатком
        # ---------------------------------------------------------------------

        russia_with_stock = (
            russia_geometries[
                russia_geometries[
                    "total_qty"
                ] > 0
            ].copy()
        )

        if not russia_with_stock.empty:
            russia_with_stock.plot(
                ax=ax,
                column="total_qty",
                cmap=cmap,
                norm=norm,
                edgecolor=COLOR_BORDER_DARK,
                linewidth=0.48,
                zorder=3,
            )

        # ---------------------------------------------------------------------
        # Другие страны
        # ---------------------------------------------------------------------

        if not country_geometries.empty:
            country_geometries.plot(
                ax=ax,
                color=COLOR_MAP_EMPTY,
                edgecolor=COLOR_BORDER,
                linewidth=0.42,
                zorder=2,
            )

            countries_with_stock = (
                country_geometries[
                    country_geometries[
                        "total_qty"
                    ] > 0
                ].copy()
            )

            if not countries_with_stock.empty:
                countries_with_stock.plot(
                    ax=ax,
                    column="total_qty",
                    cmap=cmap,
                    norm=norm,
                    edgecolor=(
                        COLOR_BORDER_DARK
                    ),
                    linewidth=0.48,
                    zorder=4,
                )

        # ---------------------------------------------------------------------
        # Заголовок карты
        # ---------------------------------------------------------------------

        date_label = (
            _format_report_date(
                report_date
            )
        )

        ax.text(
            0.5,
            1.075,
            "РАСПРЕДЕЛЕНИЕ ТОВАРНОГО ЗАПАСА",
            transform=ax.transAxes,
            ha="center",
            va="bottom",
            color=COLOR_TEXT,
            fontsize=11.3,
            fontweight="bold",
            family="serif",
        )

        ax.text(
            0.5,
            1.035,
            f"на {date_label}",
            transform=ax.transAxes,
            ha="center",
            va="bottom",
            color=COLOR_MUTED,
            fontsize=7.5,
        )

        # ---------------------------------------------------------------------
        # Общие показатели
        # ---------------------------------------------------------------------

        summary = summary or {}

        total_warehouses = int(
            number(
                summary.get(
                    "warehouses",
                    stats[
                        "warehouses"
                    ].sum(),
                )
            )
        )

        total_on_hand = number(
            summary.get(
                "on_hand",
                stats[
                    "on_hand"
                ].sum(),
            )
        )

        total_in_transit = number(
            summary.get(
                "in_transit",
                stats[
                    "in_transit"
                ].sum(),
            )
        )

        total_quantity = number(
            summary.get(
                "total_qty",
                stats[
                    "total_qty"
                ].sum(),
            )
        )

        header_text = (
            f"Складов: {total_warehouses}"
            f"   |   На складах: "
            f"{_compact_number(total_on_hand)} шт"
            f"   |   В пути: "
            f"{_compact_number(total_in_transit)} шт"
            f"   |   Всего: "
            f"{_compact_number(total_quantity)} шт"
        )

        ax.text(
            0.5,
            0.995,
            header_text,
            transform=ax.transAxes,
            ha="center",
            va="top",
            color=COLOR_TEXT,
            fontsize=7.8,
            fontweight="bold",
        )

        # ---------------------------------------------------------------------
        # Подписи российских складских зон
        # ---------------------------------------------------------------------

        for region_name, point in (
            LABEL_POINTS.items()
        ):
            if (
                region_name
                not in stats_index.index
            ):
                continue

            row = stats_index.loc[
                region_name
            ]

            # Если случайно присутствуют дубли региона.
            if isinstance(
                row,
                pd.DataFrame,
            ):
                row = row.iloc[0]

            total_qty = number(
                row.get(
                    "total_qty"
                )
            )

            if total_qty <= 0:
                continue

            longitude, latitude = (
                point
            )

            _draw_map_label(
                ax,
                x=float(
                    longitude
                ),
                y=float(
                    latitude
                ),
                name=region_name,
                total_qty=total_qty,
                warehouses=int(
                    number(
                        row.get(
                            "warehouses"
                        )
                    )
                ),
                in_transit=number(
                    row.get(
                        "in_transit"
                    )
                ),
                fontsize=6.25,
            )

        # ---------------------------------------------------------------------
        # Подписи стран
        # ---------------------------------------------------------------------

        for country_name, config in (
            COUNTRIES_CONFIG.items()
        ):
            if (
                country_name
                not in stats_index.index
            ):
                continue

            row = stats_index.loc[
                country_name
            ]

            if isinstance(
                row,
                pd.DataFrame,
            ):
                row = row.iloc[0]

            total_qty = number(
                row.get(
                    "total_qty"
                )
            )

            if total_qty <= 0:
                continue

            longitude, latitude = (
                COUNTRY_LABEL_POINTS.get(
                    country_name,
                    config.get(
                        "center"
                    ),
                )
            )

            _draw_map_label(
                ax,
                x=float(
                    longitude
                ),
                y=float(
                    latitude
                ),
                name=country_name,
                total_qty=total_qty,
                warehouses=int(
                    number(
                        row.get(
                            "warehouses"
                        )
                    )
                ),
                in_transit=number(
                    row.get(
                        "in_transit"
                    )
                ),
                fontsize=5.9,
            )

        # ---------------------------------------------------------------------
        # Цветовая шкала
        # ---------------------------------------------------------------------

        scalar = ScalarMappable(
            norm=norm,
            cmap=cmap,
        )

        scalar.set_array([])

        colorbar = fig.colorbar(
            scalar,
            ax=ax,
            orientation="vertical",
            fraction=0.017,
            pad=0.012,
            shrink=0.68,
        )

        colorbar.outline.set_edgecolor(
            COLOR_BORDER_DARK
        )

        colorbar.outline.set_linewidth(
            0.45
        )

        colorbar.ax.yaxis.set_major_formatter(
            FuncFormatter(
                _compact_tick
            )
        )

        colorbar.ax.tick_params(
            labelsize=6.1,
            colors=COLOR_MUTED,
            length=0,
        )

        colorbar.set_label(
            "Остатки, шт",
            fontsize=6.5,
            color=COLOR_TEXT,
            labelpad=5,
        )

        # ---------------------------------------------------------------------
        # Географические пределы
        # ---------------------------------------------------------------------

        ax.set_xlim(
            20,
            150,
        )

        ax.set_ylim(
            35,
            76,
        )

        ax.set_xticks([])
        ax.set_yticks([])

        ax.grid(
            False
        )

        for spine in ax.spines.values():
            spine.set_visible(
                False
            )

        plt.tight_layout(
            pad=0.35
        )

        # ---------------------------------------------------------------------
        # PNG -> data URI
        # ---------------------------------------------------------------------

        return _data_uri(
            fig,
            facecolor=COLOR_PAPER,
            dpi=180,
            pad_inches=0.01,
        )

    except Exception as exc:
        # Реальную причину оставляем в консоли Django,
        # чтобы ошибка карты не ломала весь daily brief.
        print(
            "DAILY BRIEF MAP ERROR:",
            f"{type(exc).__name__}: {exc}",
        )

        return None