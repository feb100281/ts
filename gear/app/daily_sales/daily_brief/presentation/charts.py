# gear/app/daily_sales/daily_brief/presentation/charts.py

from __future__ import annotations

import base64
import io
import re
from datetime import datetime

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
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

from ..helpers import (
    fmt_money,
    number,
)


# =============================================================================
# ОБЩАЯ ПАЛИТРА ГАЗЕТЫ
#
# Эти цвета используются только в daily_brief.
# Настройки обычной зелёной карты не затрагиваются.
# =============================================================================

COLOR_PAPER = "#FFFDF7"
COLOR_PAPER_SECONDARY = "#FBF7F1"

COLOR_TEXT = "#14213D"
COLOR_MUTED = "#667085"

COLOR_ACCENT = "#E85D75"
COLOR_ACCENT_DARK = "#9D3E52"

COLOR_BORDER = "#D7DCE2"
COLOR_BORDER_DARK = "#8E96A3"

COLOR_MAP_EMPTY = "#F0ECE6"
COLOR_MAP_LIGHT = "#F9EDEF"
COLOR_MAP_SOFT = "#EFC9D1"
COLOR_MAP_MIDDLE = "#DC8D9D"
COLOR_MAP_PRIMARY = "#E85D75"
COLOR_MAP_DARK = "#973B50"

COLOR_LABEL_BG = "#FFFDF9"


MONTHS_RU = {
    "01": "Янв",
    "02": "Фев",
    "03": "Мар",
    "04": "Апр",
    "05": "Май",
    "06": "Июн",
    "07": "Июл",
    "08": "Авг",
    "09": "Сен",
    "10": "Окт",
    "11": "Ноя",
    "12": "Дек",
}


# Положения подписей стран именно для газетной карты.
# Они немного отличаются от центров геометрий, чтобы подписи
# не накладывались друг на друга.
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
    Сохраняет matplotlib Figure в base64 data URI.

    Такой URI можно напрямую вставить в HTML:

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


def _money_tick(
    value,
    _pos=None,
) -> str:
    value = float(
        value
        or 0
    )

    if abs(value) >= 1_000_000:
        return (
            f"{value / 1_000_000:.0f} млн"
        )

    if abs(value) >= 1_000:
        return (
            f"{value / 1_000:.0f} тыс"
        )

    return (
        f"{value:,.0f}"
        .replace(",", " ")
    )


def _compact_number(
    value,
    *,
    digits: int = 1,
) -> str:
    """
    Компактное форматирование для подписей карты.
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
    Формат подписей шкалы карты.
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


def _month_label(
    label: str,
) -> str:
    try:
        month, year = str(
            label
        ).split(".")

        return (
            f"{MONTHS_RU.get(month, month)} "
            f"{year}"
        )

    except Exception:
        return str(
            label
        )


def _format_report_date(
    value,
) -> str:
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
    Нормализация названий регионов из shapefile.
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
# ТЕПЛОВОЙ КАЛЕНДАРЬ
# =============================================================================
def heat_calendar(rows: list[dict]) -> str:
    rows = list(rows or [])

    if not rows:
        return '<div class="empty">Нет данных</div>'

    month_names = {
        1: "янв",
        2: "фев",
        3: "мар",
        4: "апр",
        5: "май",
        6: "июн",
        7: "июл",
        8: "авг",
        9: "сен",
        10: "окт",
        11: "ноя",
        12: "дек",
    }

    # -------------------------------------------------------------------------
    # Подготовка данных
    # -------------------------------------------------------------------------

    prepared_rows = []

    for row in rows:
        parsed_date = pd.to_datetime(
            row.get("date_from"),
            errors="coerce",
        )

        if pd.isna(parsed_date):
            continue

        prepared_rows.append(
            {
                # Убираем время, чтобы одна дата не разбивалась
                # на несколько разных значений.
                "date": parsed_date.normalize(),
                "amount": number(
                    row.get("amount")
                ),
            }
        )

    if not prepared_rows:
        return '<div class="empty">Нет данных</div>'

    # Если на одну дату пришло несколько строк,
    # объединяем их в одно дневное значение.
    daily_amounts = {}

    for item in prepared_rows:
        current_date = item["date"]

        daily_amounts[current_date] = (
            daily_amounts.get(
                current_date,
                0,
            )
            + item["amount"]
        )

    prepared_rows = [
        {
            "date": current_date,
            "amount": amount,
        }
        for current_date, amount
        in daily_amounts.items()
    ]

    prepared_rows.sort(
        key=lambda item: item["date"]
    )

    # Последние 35 закрытых дней с данными.
    prepared_rows = prepared_rows[-35:]

    if not prepared_rows:
        return '<div class="empty">Нет данных</div>'

    values = [
        item["amount"]
        for item in prepared_rows
    ]

    minimum = min(values)
    maximum = max(values)
    value_range = maximum - minimum

    amount_by_date = {
        item["date"]: item["amount"]
        for item in prepared_rows
    }

    first_data_date = prepared_rows[0]["date"]
    last_data_date = prepared_rows[-1]["date"]

    # -------------------------------------------------------------------------
    # Настоящие календарные границы
    #
    # weekday():
    #   понедельник = 0
    #   вторник     = 1
    #   среда       = 2
    #   ...
    #   воскресенье = 6
    # -------------------------------------------------------------------------

    calendar_start = (
        first_data_date
        - pd.Timedelta(
            days=first_data_date.weekday()
        )
    )

    calendar_end = (
        last_data_date
        + pd.Timedelta(
            days=6 - last_data_date.weekday()
        )
    )

    calendar_dates = pd.date_range(
        start=calendar_start,
        end=calendar_end,
        freq="D",
    )

    calendar_weeks = [
        list(
            calendar_dates[index:index + 7]
        )
        for index in range(
            0,
            len(calendar_dates),
            7,
        )
    ]

    # -------------------------------------------------------------------------
    # Формирование HTML
    # -------------------------------------------------------------------------

    grid_cells = []
    previous_week_total = None

    for week_dates in calendar_weeks:
        week_values = []

        for current_date in week_dates:
            value = amount_by_date.get(
                current_date
            )

            # Дата входит в календарную неделю,
            # но отсутствует среди последних 35 дней.
            if value is None:
                grid_cells.append(
                    """
                    <div class="heat-cell heat-cell-empty"></div>
                    """
                )
                continue

            week_values.append(value)

            # Уровень цвета относительно min–max
            # среди отображаемых дней.
            if value_range > 0:
                normalized = (
                    value - minimum
                ) / value_range
            else:
                normalized = 0

            level = min(
                5,
                max(
                    0,
                    int(
                        round(
                            normalized * 5
                        )
                    ),
                ),
            )

            month_label = month_names.get(
                current_date.month,
                "",
            )

            date_label = (
                f"{current_date.day} "
                f"{month_label}"
            )

            grid_cells.append(
                f"""
                <div class="heat-cell heat-{level}">
                    <b class="heat-date">
                        {date_label}
                    </b>

                    <span class="heat-value">
                        {fmt_money(value)}
                    </span>
                </div>
                """
            )

        # ---------------------------------------------------------------------
        # Итог календарной недели
        # ---------------------------------------------------------------------

        week_total = sum(
            week_values
        )

        if not week_values:
            grid_cells.append(
                """
                <div class="heat-week-total heat-week-total-empty"></div>
                """
            )
            continue

        if (
            previous_week_total is not None
            and previous_week_total != 0
        ):
            week_change = (
                week_total
                / previous_week_total
                - 1
            ) * 100

            if week_change > 0:
                change_class = "up"
                arrow = "▲"

            elif week_change < 0:
                change_class = "down"
                arrow = "▼"

            else:
                change_class = "neutral"
                arrow = "—"

            change_html = f"""
                <div class="heat-week-change {change_class}">
                    {arrow} {abs(week_change):.1f}%
                </div>
            """

        else:
            change_html = """
                <div class="heat-week-change neutral">
                    база
                </div>
            """

        grid_cells.append(
            f"""
            <div class="heat-week-total">
                <div class="heat-week-total-label">
                    Итого
                </div>

                <div class="heat-week-total-value">
                    {fmt_money(week_total)}
                </div>

                {change_html}
            </div>
            """
        )

        previous_week_total = week_total

    return (
        """
        <div class="heat-calendar">

            <div class="heat-calendar-head">
                <span>Пн</span>
                <span>Вт</span>
                <span>Ср</span>
                <span>Чт</span>
                <span>Пт</span>
                <span>Сб</span>
                <span>Вс</span>
                <span class="heat-week-head">Неделя</span>
            </div>

            <div class="heat-calendar-grid">
        """
        + "".join(grid_cells)
        + """
            </div>

            <div class="heat-legend">
                Светлее — ниже выручка · насыщеннее — выше
            </div>

        </div>
        """
    )


# =============================================================================
# КОРРЕЛЯЦИЯ КОЛИЧЕСТВА И ЦЕНЫ
# =============================================================================


def daily_qty_price_scatter(
    rows: list[dict],
) -> str | None:
    if not rows:
        return None

    quantity = np.array(
        [
            number(
                row.get(
                    "sales_qty"
                )
            )
            for row in rows
        ],
        dtype=float,
    )

    price = np.array(
        [
            number(
                row.get(
                    "avg_price"
                )
            )
            for row in rows
        ],
        dtype=float,
    )

    labels = [
        str(
            row.get(
                "date_label"
            )
            or ""
        )
        for row in rows
    ]

    valid = (
        quantity > 0
    ) & (
        price > 0
    )

    quantity = quantity[
        valid
    ]

    price = price[
        valid
    ]

    labels = [
        label
        for label, is_valid
        in zip(
            labels,
            valid,
        )
        if is_valid
    ]

    if len(quantity) < 5:
        return None

    fig, ax = plt.subplots(
        figsize=(
            8.6,
            4.8,
        ),
        dpi=180,
    )

    fig.patch.set_facecolor(
        COLOR_PAPER
    )

    ax.set_facecolor(
        COLOR_PAPER
    )

    ax.scatter(
        quantity,
        price,
        s=48,
        color="#FF78A5",
        edgecolors="white",
        linewidths=0.8,
        alpha=0.68,
        zorder=4,
    )

    if np.unique(
        quantity
    ).size > 1:
        trend = np.polyfit(
            quantity,
            price,
            1,
        )

        x_line = np.linspace(
            quantity.min(),
            quantity.max(),
            200,
        )

        ax.plot(
            x_line,
            np.poly1d(
                trend
            )(
                x_line
            ),
            color=COLOR_TEXT,
            linewidth=2.2,
            zorder=3,
        )

    correlation = (
        np.corrcoef(
            quantity,
            price,
        )[0, 1]
        if (
            np.unique(
                quantity
            ).size > 1
            and np.unique(
                price
            ).size > 1
        )
        else np.nan
    )

    indices = sorted(
        set(
            np.argsort(
                quantity
            )[-3:].tolist()
            +
            np.argsort(
                price
            )[-3:].tolist()
        )
    )

    for index in indices:
        ax.text(
            quantity[index],
            price[index],
            labels[index],
            fontsize=6.6,
            color="#5F6B7A",
            bbox={
                "facecolor": "#FFFFFF",
                "edgecolor": "none",
                "pad": 0.18,
                "alpha": 0.88,
            },
        )

    correlation_text = (
        f"Корреляция: {correlation:.2f}"
        if np.isfinite(
            correlation
        )
        else "Корреляция: н/д"
    ).replace(
        ".",
        ",",
    )

    ax.text(
        0.98,
        0.95,
        correlation_text,
        transform=ax.transAxes,
        ha="right",
        va="top",
        fontsize=8,
        fontweight="bold",
        bbox={
            "facecolor": "#F4F0E6",
            "edgecolor": "none",
            "pad": 0.35,
        },
    )

    ax.set_title(
        (
            "Количество продаж и средняя цена: "
            "последние 90 дней"
        ),
        fontsize=11,
        color=COLOR_TEXT,
        pad=11,
        fontweight="bold",
    )

    ax.set_xlabel(
        "Количество продаж за день, шт.",
        fontsize=8,
    )

    ax.set_ylabel(
        "Средняя цена, руб./шт.",
        fontsize=8,
    )

    ax.xaxis.set_major_formatter(
        FuncFormatter(
            lambda x, _position: (
                f"{x:,.0f}"
                .replace(",", " ")
            )
        )
    )

    ax.yaxis.set_major_formatter(
        FuncFormatter(
            _money_tick
        )
    )

    ax.grid(
        True,
        linewidth=0.55,
        color=COLOR_BORDER,
        alpha=0.65,
    )

    for spine in ax.spines.values():
        spine.set_visible(
            False
        )

    ax.tick_params(
        labelsize=7.5
    )

    fig.tight_layout()

    return _data_uri(
        fig
    )


# =============================================================================
# ПРОДАЖИ И ЦЕНА ЗА 12 МЕСЯЦЕВ
# =============================================================================


def sales_12m_chart(
    rows: list[dict],
) -> str | None:
    if not rows:
        return None

    labels = [
        _month_label(
            row.get(
                "month_label"
            )
        )
        for row in rows
    ]

    net_values = [
        number(
            row.get(
                "net_amount"
            )
        )
        for row in rows
    ]

    average_prices = [
        number(
            row.get(
                "avg_price"
            )
        )
        for row in rows
    ]

    if not any(
        net_values
    ):
        return None

    x = np.arange(
        len(labels)
    )

    fig, ax1 = plt.subplots(
        figsize=(
            10.6,
            4.7,
        ),
        dpi=180,
    )

    fig.patch.set_facecolor(
        COLOR_PAPER
    )

    ax1.set_facecolor(
        COLOR_PAPER
    )

    bars = ax1.bar(
        x,
        net_values,
        color="#F7A7BC",
        edgecolor=COLOR_ACCENT,
        linewidth=0.7,
        width=0.72,
        zorder=3,
    )

    ax1.set_title(
        (
            "Чистая выручка и средняя цена "
            "за 12 месяцев"
        ),
        fontsize=11,
        color=COLOR_TEXT,
        pad=12,
        fontweight="bold",
    )

    ax1.set_xticks(
        x
    )

    ax1.set_xticklabels(
        labels,
        rotation=35,
        ha="right",
        fontsize=7.2,
    )

    ax1.yaxis.set_major_formatter(
        FuncFormatter(
            _money_tick
        )
    )

    ax1.tick_params(
        axis="y",
        labelsize=7.2,
        length=0,
    )

    ax1.grid(
        axis="y",
        linewidth=0.55,
        color=COLOR_BORDER,
        alpha=0.65,
        zorder=0,
    )

    for spine in ax1.spines.values():
        spine.set_visible(
            False
        )

    maximum = (
        max(
            net_values
        )
        or 1
    )

    for rectangle, value in zip(
        bars,
        net_values,
    ):
        ax1.text(
            rectangle.get_x()
            + rectangle.get_width()
            / 2,
            rectangle.get_height()
            + maximum
            * 0.012,
            _money_tick(
                value
            ),
            ha="center",
            va="bottom",
            fontsize=6.2,
            fontweight="bold",
        )

    ax2 = ax1.twinx()

    ax2.plot(
        x,
        average_prices,
        color=COLOR_TEXT,
        marker="o",
        markerfacecolor="#9BFF57",
        markeredgecolor=COLOR_TEXT,
        linewidth=2.1,
        markersize=5,
        zorder=4,
    )

    ax2.yaxis.set_major_formatter(
        FuncFormatter(
            _money_tick
        )
    )

    ax2.tick_params(
        axis="y",
        labelsize=7.2,
    )

    for spine in ax2.spines.values():
        spine.set_visible(
            False
        )

    fig.tight_layout()

    return _data_uri(
        fig
    )


# =============================================================================
# КАРТА ДЛЯ ГАЗЕТЫ
#
# ВАЖНО:
# этот код не меняет inventories.reporting.map.
# Он только использует общие shapefile и справочники регионов.
# =============================================================================


def _build_brief_map_cmap():
    """
    Кораллово-бордовая палитра карты газеты.
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


def _find_name_column(
    frame: pd.DataFrame,
) -> str:
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
    если в shapefile присутствует соответствующая колонка.
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


def _prepare_russia_district_geometries():
    """
    Загружает административные регионы России
    и объединяет их в складские зоны из map_config.py.
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


def _prepare_country_geometries():
    """
    Загружает геометрию стран, перечисленных
    в COUNTRIES_CONFIG.
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


def _prepare_map_stats(
    regions: list[dict],
) -> pd.DataFrame:
    """
    Приводит данные payload к единому формату карты.
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
    Единая газетная подпись региона или страны.
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


def stock_map(
    regions: list[dict],
    report_date: str,
    summary: dict,
) -> str | None:
    """
    Отдельная карта для «Коммерческого обзора».

    Она:
    - использует общие shapefile проекта;
    - использует справочник регионов из map_config.py;
    - НЕ вызывает зелёный build_russia_regions_map();
    - НЕ меняет общие файлы inventories.reporting.map;
    - рисуется в тёмно-синей, коралловой и молочной гамме газеты.
    """

    if not regions:
        return None

    if gpd is None:
        print(
            "DAILY BRIEF MAP: geopandas не установлен"
        )

        return None

    try:
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

        # -------------------------------------------------------------
        # Присоединяем значения к российским зонам
        # -------------------------------------------------------------

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

        # -------------------------------------------------------------
        # Присоединяем значения к странам
        # -------------------------------------------------------------

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

        # Нелинейная шкала не даёт Центральному региону
        # полностью «поглотить» остальные зоны.
        norm = mcolors.PowerNorm(
            gamma=0.42,
            vmin=0,
            vmax=maximum,
        )

        fig, ax = plt.subplots(
            figsize=(
                15.4,
                6.1,
            ),
            dpi=180,
        )

        fig.patch.set_facecolor(
            COLOR_PAPER
        )

        ax.set_facecolor(
            COLOR_PAPER
        )

        # -------------------------------------------------------------
        # Российские зоны без значительного запаса
        # -------------------------------------------------------------

        russia_geometries.plot(
            ax=ax,
            color=COLOR_MAP_EMPTY,
            edgecolor=COLOR_BORDER,
            linewidth=0.38,
            zorder=1,
        )

        # -------------------------------------------------------------
        # Российские зоны с запасом
        # -------------------------------------------------------------

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

        # -------------------------------------------------------------
        # Страны
        # -------------------------------------------------------------

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

        # -------------------------------------------------------------
        # Заголовок карты
        # -------------------------------------------------------------

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

        # -------------------------------------------------------------
        # Общие показатели
        # -------------------------------------------------------------

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

        # -------------------------------------------------------------
        # Подписи российских складских зон
        # -------------------------------------------------------------

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

            # На случай случайных дублей.
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

        # -------------------------------------------------------------
        # Подписи стран
        # -------------------------------------------------------------

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

        # -------------------------------------------------------------
        # Компактная газетная шкала справа
        # -------------------------------------------------------------

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

        # -------------------------------------------------------------
        # Географические пределы
        # -------------------------------------------------------------

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
        ax.grid(False)

        for spine in ax.spines.values():
            spine.set_visible(
                False
            )

        plt.tight_layout(
            pad=0.35
        )

        return _data_uri(
            fig,
            facecolor=COLOR_PAPER,
            dpi=180,
            pad_inches=0.06,
        )

    except Exception as exc:
        # Не скрываем реальную причину.
        # Она будет видна в консоли Django.
        print(
            "DAILY BRIEF MAP ERROR:",
            f"{type(exc).__name__}: {exc}",
        )

        return None
    

def ytd_revenue_bloomberg_chart(
    rows: list[dict],
    report_date: str,
) -> str | None:
    """
    Bloomberg-style график накопленной чистой выручки YTD.

    Ожидаемые поля строки:
        date_from
        amount

    Можно передавать данные одновременно за текущий
    и предыдущий год.

    График:
    - текущий год — плотная тёмно-синяя линия;
    - предыдущий год — тонкая пунктирная коралловая линия;
    - в правой части показывается итог текущего года;
    - без тяжёлых осей и BI-оформления.
    """

    if not rows:
        return None

    frame = pd.DataFrame(
        rows
    )

    if frame.empty:
        return None

    date_column = None

    for candidate in [
        "date_from",
        "date",
        "report_date",
    ]:
        if candidate in frame.columns:
            date_column = candidate
            break

    amount_column = None

    for candidate in [
        "amount",
        "net_amount",
        "net_revenue",
        "revenue",
    ]:
        if candidate in frame.columns:
            amount_column = candidate
            break

    if not date_column or not amount_column:
        return None

    frame["date_value"] = pd.to_datetime(
        frame[date_column],
        errors="coerce",
    )

    frame["amount_value"] = pd.to_numeric(
        frame[amount_column],
        errors="coerce",
    ).fillna(0)

    frame = frame[
        frame["date_value"].notna()
    ].copy()

    if frame.empty:
        return None

    selected_date = pd.to_datetime(
        report_date,
        errors="coerce",
    )

    if pd.isna(selected_date):
        selected_date = frame[
            "date_value"
        ].max()

    current_year = int(
        selected_date.year
    )

    previous_year = (
        current_year
        - 1
    )

    # ---------------------------------------------------------------
    # Сводим к одному значению на день
    # ---------------------------------------------------------------

    daily = (
        frame
        .groupby(
            "date_value",
            as_index=False,
        )
        .agg(
            amount_value=(
                "amount_value",
                "sum",
            )
        )
        .sort_values(
            "date_value"
        )
    )

    daily["year"] = (
        daily["date_value"].dt.year
    )

    daily["day_of_year"] = (
        daily["date_value"].dt.dayofyear
    )

    # Високосный год не критичен для небольшого обзорного графика.
    # Ограничиваем прошлый год тем же календарным днём.
    selected_day_of_year = int(
        selected_date.dayofyear
    )

    current = daily[
        (
            daily["year"]
            == current_year
        )
        & (
            daily["day_of_year"]
            <= selected_day_of_year
        )
    ].copy()

    previous = daily[
        (
            daily["year"]
            == previous_year
        )
        & (
            daily["day_of_year"]
            <= selected_day_of_year
        )
    ].copy()

    if current.empty:
        return None

    current["running_amount"] = (
        current["amount_value"]
        .cumsum()
    )

    if not previous.empty:
        previous["running_amount"] = (
            previous["amount_value"]
            .cumsum()
        )

    # ---------------------------------------------------------------
    # Рисуем
    # ---------------------------------------------------------------

    fig, ax = plt.subplots(
        figsize=(
            8.8,
            3.5,
        ),
        dpi=180,
    )

    paper_color = "#FFFDF7"
    navy = "#14213D"
    coral = "#E85D75"
    muted = "#7A8494"
    grid_color = "#DDD9D2"

    fig.patch.set_facecolor(
        paper_color
    )

    ax.set_facecolor(
        paper_color
    )

    current_x = (
        current["day_of_year"]
        .to_numpy()
    )

    current_y = (
        current["running_amount"]
        .to_numpy()
    )

    ax.fill_between(
        current_x,
        current_y,
        0,
        color="#F3DCE2",
        alpha=0.55,
        zorder=1,
    )

    ax.plot(
        current_x,
        current_y,
        color=navy,
        linewidth=2.8,
        solid_capstyle="round",
        zorder=4,
    )

    ax.scatter(
        current_x[-1],
        current_y[-1],
        s=42,
        color="#FFD84D",
        edgecolor=navy,
        linewidth=1.2,
        zorder=6,
    )

    if not previous.empty:
        previous_x = (
            previous["day_of_year"]
            .to_numpy()
        )

        previous_y = (
            previous["running_amount"]
            .to_numpy()
        )

        ax.plot(
            previous_x,
            previous_y,
            color=coral,
            linewidth=1.7,
            linestyle=(0, (4, 3)),
            alpha=0.95,
            zorder=3,
        )

    # ---------------------------------------------------------------
    # Заголовок и итог справа
    # ---------------------------------------------------------------

    current_total = float(
        current_y[-1]
    )

    previous_total = (
        float(
            previous[
                "running_amount"
            ].iloc[-1]
        )
        if not previous.empty
        else 0
    )

    change_pct = (
        (
            current_total
            - previous_total
        )
        / abs(previous_total)
        * 100
        if previous_total
        else None
    )

    ax.text(
        0.0,
        1.13,
        "НАКОПЛЕННАЯ ВЫРУЧКА YTD",
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=7.2,
        color=coral,
        fontweight="bold",
    )

    ax.text(
        0.0,
        1.045,
        f"{current_year} против {previous_year}",
        transform=ax.transAxes,
        ha="left",
        va="bottom",
        fontsize=12,
        color=navy,
        fontweight="bold",
        family="serif",
    )

    current_total_text = (
        f"{current_total / 1_000_000:.1f} млн ₽"
        .replace(".", ",")
        if current_total < 1_000_000_000
        else
        f"{current_total / 1_000_000_000:.2f} млрд ₽"
        .replace(".", ",")
    )

    ax.text(
        1.0,
        1.07,
        current_total_text,
        transform=ax.transAxes,
        ha="right",
        va="bottom",
        fontsize=13,
        color=navy,
        fontweight="bold",
        family="serif",
    )

    if change_pct is not None:
        change_color = (
            "#12654F"
            if change_pct >= 0
            else "#B53C56"
        )

        change_symbol = (
            "▲"
            if change_pct >= 0
            else "▼"
        )

        ax.text(
            1.0,
            0.995,
            (
                f"{change_symbol} "
                f"{abs(change_pct):.1f}% год к году"
            ).replace(".", ","),
            transform=ax.transAxes,
            ha="right",
            va="bottom",
            fontsize=7.5,
            color=change_color,
            fontweight="bold",
        )

    # ---------------------------------------------------------------
    # Ось месяцев
    # ---------------------------------------------------------------

    month_positions = []
    month_labels = []

    for month in range(
        1,
        selected_date.month + 1,
    ):
        month_start = pd.Timestamp(
            year=current_year,
            month=month,
            day=1,
        )

        month_positions.append(
            month_start.dayofyear
        )

        month_labels.append(
            {
                1: "Янв",
                2: "Фев",
                3: "Мар",
                4: "Апр",
                5: "Май",
                6: "Июн",
                7: "Июл",
                8: "Авг",
                9: "Сен",
                10: "Окт",
                11: "Ноя",
                12: "Дек",
            }[month]
        )

    ax.set_xticks(
        month_positions
    )

    ax.set_xticklabels(
        month_labels,
        fontsize=7,
        color=muted,
    )

    ax.yaxis.set_major_formatter(
        FuncFormatter(
            lambda value, _pos: (
                f"{value / 1_000_000:.0f} млн"
                if abs(value) >= 1_000_000
                else f"{value:,.0f}"
                .replace(",", " ")
            )
        )
    )

    ax.tick_params(
        axis="y",
        labelsize=6.5,
        colors=muted,
        length=0,
    )

    ax.tick_params(
        axis="x",
        length=0,
        pad=4,
    )

    ax.grid(
        axis="y",
        color=grid_color,
        linewidth=0.5,
        alpha=0.65,
        zorder=0,
    )

    ax.set_xlim(
        1,
        selected_day_of_year + 4,
    )

    ymax = max(
        float(current_y.max()),
        (
            float(
                previous[
                    "running_amount"
                ].max()
            )
            if not previous.empty
            else 0
        ),
    )

    ax.set_ylim(
        0,
        ymax * 1.13
        if ymax
        else 1,
    )

    for spine in ax.spines.values():
        spine.set_visible(
            False
        )

    # ---------------------------------------------------------------
    # Легенда
    # ---------------------------------------------------------------

    ax.plot(
        [],
        [],
        color=navy,
        linewidth=2.5,
        label=str(current_year),
    )

    if not previous.empty:
        ax.plot(
            [],
            [],
            color=coral,
            linewidth=1.6,
            linestyle=(0, (4, 3)),
            label=str(previous_year),
        )

    legend = ax.legend(
        loc="upper left",
        bbox_to_anchor=(
            0.0,
            0.95,
        ),
        frameon=False,
        fontsize=6.7,
        ncol=2,
        handlelength=2.3,
        columnspacing=1.3,
    )

    for text in legend.get_texts():
        text.set_color(
            muted
        )

    fig.tight_layout(
        pad=0.5
    )

    return _data_uri(
        fig,
        facecolor=paper_color,
        dpi=180,
        pad_inches=0.04,
    )