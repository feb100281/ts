# # inventories/reporting/map/russia_regions_map.py
# from __future__ import annotations

# import io
# import re
# from pathlib import Path

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


# COLOR_BG = "#F4F8F6"
# COLOR_BASE = "#E6ECE9"
# COLOR_TEXT = "#18352F"
# COLOR_MUTED = "#60746D"
# COLOR_PRIMARY = "#006B4F"


# # Важно: это не регионы-склады WB, а наши укрупненные зоны из твоего запроса
# WAREHOUSE_REGIONS = [
#     "Центральный",
#     "Приволжский",
#     "Уральский",
#     "Южный и Северо-Кавказский",
#     "Дальневосточный и Сибирский",
# ]


# LABEL_POINTS = {
#     "Центральный": (38, 55),
#     "Приволжский": (50, 55),
#     "Уральский": (63, 60),
#     "Южный и Северо-Кавказский": (43, 45),
#     "Дальневосточный и Сибирский": (105, 61),
# }


# DISTRICT_KEYWORDS = {
#     "Центральный": [
#         "moscow", "moskva", "belgorod", "bryansk", "vladimir", "voronezh",
#         "ivanovo", "kaluga", "kostroma", "kursk", "lipetsk", "oryol",
#         "orel", "ryazan", "smolensk", "tambov", "tver", "tula", "yaroslavl",
#     ],
#     "Приволжский": [
#         "bashkortostan", "mari", "mordovia", "tatarstan", "udmurt",
#         "chuvash", "perm", "kirov", "nizhny", "novgorod", "orenburg",
#         "penza", "samara", "saratov", "ulyanovsk",
#     ],
#     "Уральский": [
#         "kurgan", "sverdlovsk", "tyumen", "chelyabinsk",
#         "khanty", "mansiy", "yamal", "nenets",
#     ],
#     "Южный и Северо-Кавказский": [
#         "adygey", "adygea", "kalmyk", "crimea", "krasnodar", "astrakhan",
#         "volgograd", "rostov", "dagestan", "ingush", "kabardin",
#         "balkar", "karachay", "cherkess", "ossetia", "chechnya",
#         "stavropol",
#     ],
#     "Дальневосточный и Сибирский": [
#         "altay", "altai", "buryat", "tuva", "tyva", "khakass",
#         "krasnoyarsk", "irkutsk", "kemerovo", "novosibirsk", "omsk",
#         "tomsk", "zabaykal", "transbaikal", "sakha", "yakutia",
#         "kamchatka", "primorye", "primorsky", "khabarovsk", "amur",
#         "magadan", "sakhalin", "jewish", "chukotka",
#     ],
# }


# def get_shapefile_path() -> Path:
#     current_file = Path(__file__).resolve()
#     shp_path = (
#         current_file.parent.parent
#         / "assets"
#         / "maps"
#         / "russia_regions"
#         / "ne_10m_admin_1_states_provinces.shp"
#     )

#     if not shp_path.exists():
#         raise FileNotFoundError(f"Shapefile не найден: {shp_path}")

#     return shp_path


# def format_number(value: float) -> str:
#     value = float(value or 0)

#     if value >= 1_000_000:
#         return f"{value / 1_000_000:.1f} млн шт"
#     if value >= 1_000:
#         return f"{value / 1_000:.1f} тыс шт"
#     return f"{value:,.0f} шт".replace(",", " ")


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
#         ["#EEF5F1", "#DCEBE4", "#BFD8CF", "#94BBAF", "#5D9283", COLOR_PRIMARY],
#         N=256,
#     )


# def _clean_text(value: object) -> str:
#     s = str(value or "").lower()
#     s = s.replace("’", "'")
#     s = re.sub(r"[^a-zа-яё0-9]+", " ", s)
#     return re.sub(r"\s+", " ", s).strip()


# def _find_name_col(gdf: pd.DataFrame) -> str:
#     candidates = [
#         "name",
#         "NAME",
#         "name_en",
#         "NAME_EN",
#         "name_local",
#         "NAME_LOCAL",
#         "region",
#         "province",
#         "gn_name",
#         "GN_NAME",
#     ]

#     for col in candidates:
#         if col in gdf.columns:
#             return col

#     raise ValueError(
#         f"Не найдена колонка с названием региона. Колонки shapefile: {list(gdf.columns)}"
#     )


# def _filter_russia_if_possible(gdf):
#     """
#     Фильтруем Россию аккуратно.
#     Если фильтр дал 0 строк — не применяем его, чтобы не убить всю карту.
#     """
#     candidates = [
#         "adm0_a3",
#         "ADM0_A3",
#         "iso_a2",
#         "ISO_A2",
#         "admin",
#         "ADMIN",
#         "geonunit",
#         "GEOUNIT",
#         "sov_a3",
#         "SOV_A3",
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
#             mask = values.str.contains("RUSSIA|RUSSIAN FEDERATION|РОССИЯ|RUS", regex=True, na=False)

#         filtered = gdf[mask].copy()

#         if not filtered.empty:
#             print(f"Фильтр России применен по колонке {col}: {len(filtered)} строк")
#             return filtered

#     print("Фильтр России не применен: подходящая колонка не найдена или дала 0 строк")
#     return gdf


# def _detect_district(region_name: object) -> str | None:
#     text = _clean_text(region_name)

#     for district, keywords in DISTRICT_KEYWORDS.items():
#         for keyword in keywords:
#             if keyword in text:
#                 return district

#     return None


# def _prepare_district_geometries():
#     shp_path = get_shapefile_path()
#     gdf = gpd.read_file(shp_path)

#     print("Shapefile:", shp_path)
#     print("Всего объектов в shapefile:", len(gdf))
#     print("Колонки shapefile:", list(gdf.columns))

#     gdf = _filter_russia_if_possible(gdf)

#     name_col = _find_name_col(gdf)

#     sample_names = gdf[name_col].dropna().astype(str).head(80).to_list()
#     print("Колонка названия региона:", name_col)
#     print("Примеры названий:", sample_names)

#     gdf["district"] = gdf[name_col].apply(_detect_district)

#     matched_count = int(gdf["district"].notna().sum())
#     print("Сопоставлено с нашими округами:", matched_count)

#     if matched_count == 0:
#         all_names = gdf[name_col].dropna().astype(str).head(150).to_list()
#         raise ValueError(
#             "Не удалось сопоставить ни один субъект РФ с округами. "
#             f"Колонка названия: {name_col}. "
#             f"Примеры значений: {all_names}"
#         )

#     unmatched = sorted(
#         gdf.loc[gdf["district"].isna(), name_col]
#         .dropna()
#         .astype(str)
#         .unique()
#         .tolist()
#     )

#     if unmatched:
#         print("Не сопоставлены объекты shapefile:")
#         for x in unmatched[:120]:
#             print(" -", x)

#     gdf = gdf[gdf["district"].notna()].copy()
#     gdf = gdf[gdf.geometry.notna()].copy()

#     if gdf.empty:
#         raise ValueError("После сопоставления не осталось валидной геометрии")

#     districts = gdf.dissolve(by="district", as_index=False)
#     districts = districts[districts.geometry.notna()].copy()

#     if districts.empty:
#         raise ValueError("После dissolve получился пустой GeoDataFrame")

#     return districts


# def build_russia_regions_map(region_stats: pd.DataFrame, report_date: str) -> io.BytesIO:
#     if gpd is None:
#         raise ImportError("Установите geopandas: pip install geopandas")

#     if region_stats.empty:
#         raise ValueError("Нет данных для построения карты")

#     region_stats = region_stats.copy()
#     region_stats["регион"] = region_stats["регион"].astype(str).str.strip()
#     region_stats["итого"] = pd.to_numeric(region_stats["итого"], errors="coerce").fillna(0)

#     print("Данные по складским регионам:")
#     print(region_stats)

#     districts = _prepare_district_geometries()

#     districts = districts.merge(
#         region_stats,
#         how="left",
#         left_on="district",
#         right_on="регион",
#     )

#     districts["итого"] = districts["итого"].fillna(0)

#     # Добавляем отсутствующие в данных регионы, чтобы сразу видеть проблему в консоли
#     missing_data = districts.loc[districts["регион"].isna(), "district"].tolist()
#     if missing_data:
#         print("Нет данных по складским регионам:")
#         for x in missing_data:
#             print(" -", x)

#     fig, ax = plt.subplots(figsize=(14.5, 7.2), dpi=180)
#     fig.patch.set_facecolor(COLOR_BG)
#     ax.set_facecolor(COLOR_BG)
#     ax.set_aspect("auto")

#     districts.plot(
#         ax=ax,
#         color=COLOR_BASE,
#         edgecolor="#FFFFFF",
#         linewidth=1.0,
#         zorder=1,
#     )

#     colored = districts[districts["итого"] > 0].copy()

#     if not colored.empty:
#         cmap = _build_cmap()

#         vmin = float(colored["итого"].min())
#         vmax = float(colored["итого"].max())

#         gamma = 0.45 if vmax > vmin else 1.0
#         norm = mcolors.PowerNorm(gamma=gamma, vmin=vmin, vmax=vmax)

#         colored.plot(
#             ax=ax,
#             column="итого",
#             cmap=cmap,
#             norm=norm,
#             edgecolor="#FFFFFF",
#             linewidth=1.35,
#             zorder=3,
#         )

#         sm = ScalarMappable(norm=norm, cmap=cmap)
#         sm.set_array([])

#         cbar = fig.colorbar(
#             sm,
#             ax=ax,
#             orientation="vertical",
#             fraction=0.025,
#             pad=0.015,
#             shrink=0.72,
#         )

#         cbar.outline.set_edgecolor("#AAB7B0")
#         cbar.outline.set_linewidth(0.8)
#         cbar.ax.yaxis.set_major_formatter(FuncFormatter(_format_tick))
#         cbar.ax.tick_params(labelsize=8, colors=COLOR_MUTED, length=0)
#         cbar.set_label("Остатки, шт", fontsize=9, color=COLOR_TEXT, labelpad=8)

#     for _, row in districts.iterrows():
#         district = row["district"]
#         qty = float(row["итого"] or 0)

#         if district in LABEL_POINTS:
#             x, y = LABEL_POINTS[district]
#         else:
#             point = row.geometry.representative_point()
#             x, y = point.x, point.y

#         ax.text(
#             x,
#             y,
#             f"{district}\n{format_number(qty)}",
#             ha="center",
#             va="center",
#             fontsize=8.5,
#             color=COLOR_TEXT,
#             fontweight=600,
#             linespacing=1.08,
#             zorder=5,
#             bbox=dict(
#                 boxstyle="round,pad=0.34,rounding_size=0.16",
#                 facecolor="#FAFAF8",
#                 edgecolor="#B6C4BD",
#                 linewidth=0.8,
#                 alpha=0.96,
#             ),
#         )

#     ax.set_xlim(20, 180)
#     ax.set_ylim(40, 76)

#     ax.set_title(
#         f"География остатков товаров по регионам России\nна {report_date}",
#         fontsize=17,
#         fontweight="bold",
#         color=COLOR_TEXT,
#         pad=18,
#     )

#     ax.text(
#         0.0,
#         -0.035,
#         "Цвет отражает величину товарных остатков. Данные агрегированы по складским регионам.",
#         transform=ax.transAxes,
#         ha="left",
#         va="top",
#         fontsize=9,
#         color=COLOR_MUTED,
#     )

#     ax.set_xticks([])
#     ax.set_yticks([])
#     ax.grid(False)

#     for spine in ax.spines.values():
#         spine.set_visible(False)

#     plt.tight_layout(pad=0.4)

#     buffer = io.BytesIO()
#     fig.savefig(
#         buffer,
#         format="png",
#         dpi=180,
#         bbox_inches="tight",
#         facecolor=COLOR_BG,
#     )
#     plt.close(fig)
#     buffer.seek(0)

#     return buffer


# # Алиас, если где-то в проекте осталось старое имя
# build_regions_stock_map_png = build_russia_regions_map






# # inventories/reporting/map/russia_regions_map.py
# from __future__ import annotations

# import io
# import re
# from pathlib import Path

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


# COLOR_BG = "#F4F8F6"
# COLOR_BASE = "#E6ECE9"
# COLOR_TEXT = "#18352F"
# COLOR_MUTED = "#60746D"
# COLOR_PRIMARY = "#006B4F"


# # Важно: это не регионы-склады WB, а наши укрупненные зоны из твоего запроса
# WAREHOUSE_REGIONS = [
#     "Центральный",
#     "Приволжский",
#     "Уральский",
#     "Южный и Северо-Кавказский",
#     "Дальневосточный и Сибирский",
# ]


# LABEL_POINTS = {
#     "Центральный": (38, 55),
#     "Приволжский": (50, 55),
#     "Уральский": (63, 60),
#     "Южный и Северо-Кавказский": (43, 45),
#     "Дальневосточный и Сибирский": (105, 61),
# }


# DISTRICT_KEYWORDS = {
#     "Центральный": [
#         "moscow", "moskva", "belgorod", "bryansk", "vladimir", "voronezh",
#         "ivanovo", "kaluga", "kostroma", "kursk", "lipetsk", "oryol",
#         "orel", "ryazan", "smolensk", "tambov", "tver", "tula", "yaroslavl",
#     ],
#     "Приволжский": [
#         "bashkortostan", "mari", "mordovia", "tatarstan", "udmurt",
#         "chuvash", "perm", "kirov", "nizhny", "novgorod", "orenburg",
#         "penza", "samara", "saratov", "ulyanovsk",
#     ],
#     "Уральский": [
#         "kurgan", "sverdlovsk", "tyumen", "chelyabinsk",
#         "khanty", "mansiy", "yamal", "nenets",
#     ],
#     "Южный и Северо-Кавказский": [
#         "adygey", "adygea", "kalmyk", "crimea", "krasnodar", "astrakhan",
#         "volgograd", "rostov", "dagestan", "ingush", "kabardin",
#         "balkar", "karachay", "cherkess", "ossetia", "chechnya",
#         "stavropol",
#     ],
#     "Дальневосточный и Сибирский": [
#         "altay", "altai", "buryat", "tuva", "tyva", "khakass",
#         "krasnoyarsk", "irkutsk", "kemerovo", "novosibirsk", "omsk",
#         "tomsk", "zabaykal", "transbaikal", "sakha", "yakutia",
#         "kamchatka", "primorye", "primorsky", "khabarovsk", "amur",
#         "magadan", "sakhalin", "jewish", "chukotka",
#     ],
# }


# def get_shapefile_path() -> Path:
#     current_file = Path(__file__).resolve()
#     shp_path = (
#         current_file.parent.parent
#         / "assets"
#         / "maps"
#         / "russia_regions"
#         / "ne_10m_admin_1_states_provinces.shp"
#     )

#     if not shp_path.exists():
#         raise FileNotFoundError(f"Shapefile не найден: {shp_path}")

#     return shp_path


# def format_number(value: float) -> str:
#     """Форматирование чисел для основного текста"""
#     value = float(value or 0)

#     if value >= 1_000_000:
#         return f"{value / 1_000_000:.1f} млн шт"
#     if value >= 1_000:
#         return f"{value / 1_000:.1f} тыс шт"
#     return f"{value:,.0f} шт".replace(",", " ")


# def format_number_compact(value: float) -> str:
#     """Компактный формат чисел для маленьких подписей"""
#     value = float(value or 0)
    
#     if value >= 1_000_000:
#         return f"{value / 1_000_000:.1f}M"
#     if value >= 1_000:
#         return f"{value / 1_000:.0f}K"
#     return f"{value:,.0f}".replace(",", " ")


# def format_warehouses(count: int) -> str:
#     """Форматирование количества складов с иконкой"""
#     if count == 0:
#         return "🏚️ 0"
#     elif count == 1:
#         return f"🏪 {count}"
#     else:
#         return f"🏭 {count}"


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
#         ["#EEF5F1", "#DCEBE4", "#BFD8CF", "#94BBAF", "#5D9283", COLOR_PRIMARY],
#         N=256,
#     )


# def _clean_text(value: object) -> str:
#     s = str(value or "").lower()
#     s = s.replace("’", "'")
#     s = re.sub(r"[^a-zа-яё0-9]+", " ", s)
#     return re.sub(r"\s+", " ", s).strip()


# def _find_name_col(gdf: pd.DataFrame) -> str:
#     candidates = [
#         "name",
#         "NAME",
#         "name_en",
#         "NAME_EN",
#         "name_local",
#         "NAME_LOCAL",
#         "region",
#         "province",
#         "gn_name",
#         "GN_NAME",
#     ]

#     for col in candidates:
#         if col in gdf.columns:
#             return col

#     raise ValueError(
#         f"Не найдена колонка с названием региона. Колонки shapefile: {list(gdf.columns)}"
#     )


# def _filter_russia_if_possible(gdf):
#     """
#     Фильтруем Россию аккуратно.
#     Если фильтр дал 0 строк — не применяем его, чтобы не убить всю карту.
#     """
#     candidates = [
#         "adm0_a3",
#         "ADM0_A3",
#         "iso_a2",
#         "ISO_A2",
#         "admin",
#         "ADMIN",
#         "geonunit",
#         "GEOUNIT",
#         "sov_a3",
#         "SOV_A3",
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
#             mask = values.str.contains("RUSSIA|RUSSIAN FEDERATION|РОССИЯ|RUS", regex=True, na=False)

#         filtered = gdf[mask].copy()

#         if not filtered.empty:
#             print(f"Фильтр России применен по колонке {col}: {len(filtered)} строк")
#             return filtered

#     print("Фильтр России не применен: подходящая колонка не найдена или дала 0 строк")
#     return gdf


# def _detect_district(region_name: object) -> str | None:
#     text = _clean_text(region_name)

#     for district, keywords in DISTRICT_KEYWORDS.items():
#         for keyword in keywords:
#             if keyword in text:
#                 return district

#     return None


# def _prepare_district_geometries():
#     shp_path = get_shapefile_path()
#     gdf = gpd.read_file(shp_path)

#     print("Shapefile:", shp_path)
#     print("Всего объектов в shapefile:", len(gdf))
#     print("Колонки shapefile:", list(gdf.columns))

#     gdf = _filter_russia_if_possible(gdf)

#     name_col = _find_name_col(gdf)

#     sample_names = gdf[name_col].dropna().astype(str).head(80).to_list()
#     print("Колонка названия региона:", name_col)
#     print("Примеры названий:", sample_names)

#     gdf["district"] = gdf[name_col].apply(_detect_district)

#     matched_count = int(gdf["district"].notna().sum())
#     print("Сопоставлено с нашими округами:", matched_count)

#     if matched_count == 0:
#         all_names = gdf[name_col].dropna().astype(str).head(150).to_list()
#         raise ValueError(
#             "Не удалось сопоставить ни один субъект РФ с округами. "
#             f"Колонка названия: {name_col}. "
#             f"Примеры значений: {all_names}"
#         )

#     unmatched = sorted(
#         gdf.loc[gdf["district"].isna(), name_col]
#         .dropna()
#         .astype(str)
#         .unique()
#         .tolist()
#     )

#     if unmatched:
#         print("Не сопоставлены объекты shapefile:")
#         for x in unmatched[:120]:
#             print(" -", x)

#     gdf = gdf[gdf["district"].notna()].copy()
#     gdf = gdf[gdf.geometry.notna()].copy()

#     if gdf.empty:
#         raise ValueError("После сопоставления не осталось валидной геометрии")

#     districts = gdf.dissolve(by="district", as_index=False)
#     districts = districts[districts.geometry.notna()].copy()

#     if districts.empty:
#         raise ValueError("После dissolve получился пустой GeoDataFrame")

#     return districts


# def build_russia_regions_map(region_stats: pd.DataFrame, report_date: str) -> io.BytesIO:
#     if gpd is None:
#         raise ImportError("Установите geopandas: pip install geopandas")

#     if region_stats.empty:
#         raise ValueError("Нет данных для построения карты")

#     # Подготовка данных
#     region_stats = region_stats.copy()
#     region_stats["регион"] = region_stats["регион"].astype(str).str.strip()
#     region_stats["на_складе"] = pd.to_numeric(region_stats["на_складе"], errors="coerce").fillna(0)
#     region_stats["в_пути"] = pd.to_numeric(region_stats["в_пути"], errors="coerce").fillna(0)
#     region_stats["складов"] = pd.to_numeric(region_stats["складов"], errors="coerce").fillna(0).astype(int)
#     region_stats["итого"] = pd.to_numeric(region_stats["итого"], errors="coerce").fillna(0)

#     print("\n" + "="*60)
#     print("Данные по складским регионам:")
#     print(region_stats.to_string(index=False))
#     print("="*60 + "\n")

#     # Загружаем геометрию
#     districts = _prepare_district_geometries()

#     # Объединяем с данными
#     districts = districts.merge(
#         region_stats,
#         how="left",
#         left_on="district",
#         right_on="регион",
#     )

#     districts["итого"] = districts["итого"].fillna(0)
#     districts["на_складе"] = districts["на_складе"].fillna(0)
#     districts["в_пути"] = districts["в_пути"].fillna(0)
#     districts["складов"] = districts["складов"].fillna(0).astype(int)

#     # Проверяем отсутствующие регионы
#     missing_data = districts.loc[districts["регион"].isna(), "district"].tolist()
#     if missing_data:
#         print("\n⚠️ НЕТ ДАННЫХ ПО СЛЕДУЮЩИМ РЕГИОНАМ:")
#         for x in missing_data:
#             print(f"   - {x}")
#         print()

#     # Создаем карту
#     fig, ax = plt.subplots(figsize=(14.5, 7.2), dpi=180)
#     fig.patch.set_facecolor(COLOR_BG)
#     ax.set_facecolor(COLOR_BG)
#     ax.set_aspect("auto")

#     # Базовый слой (все регионы)
#     districts.plot(
#         ax=ax,
#         color=COLOR_BASE,
#         edgecolor="#FFFFFF",
#         linewidth=1.0,
#         zorder=1,
#     )

#     # Цветной слой (только регионы с данными)
#     colored = districts[districts["итого"] > 0].copy()

#     if not colored.empty:
#         cmap = _build_cmap()

#         vmin = float(colored["итого"].min())
#         vmax = float(colored["итого"].max())

#         gamma = 0.45 if vmax > vmin else 1.0
#         norm = mcolors.PowerNorm(gamma=gamma, vmin=vmin, vmax=vmax)

#         colored.plot(
#             ax=ax,
#             column="итого",
#             cmap=cmap,
#             norm=norm,
#             edgecolor="#FFFFFF",
#             linewidth=1.35,
#             zorder=3,
#         )

#         # Colorbar
#         sm = ScalarMappable(norm=norm, cmap=cmap)
#         sm.set_array([])

#         cbar = fig.colorbar(
#             sm,
#             ax=ax,
#             orientation="vertical",
#             fraction=0.025,
#             pad=0.015,
#             shrink=0.72,
#         )

#         cbar.outline.set_edgecolor("#AAB7B0")
#         cbar.outline.set_linewidth(0.8)
#         cbar.ax.yaxis.set_major_formatter(FuncFormatter(_format_tick))
#         cbar.ax.tick_params(labelsize=8, colors=COLOR_MUTED, length=0)
#         cbar.set_label("Остатки, шт", fontsize=9, color=COLOR_TEXT, labelpad=8)

#     # Подписи регионов с расширенной информацией
#     for _, row in districts.iterrows():
#         district = row["district"]
#         qty = float(row["итого"] or 0)
#         on_hand = float(row["на_складе"] or 0)
#         in_transit = float(row["в_пути"] or 0)
#         warehouses = int(row["складов"] or 0)

#         # Координаты для подписи
#         if district in LABEL_POINTS:
#             x, y = LABEL_POINTS[district]
#         else:
#             point = row.geometry.representative_point()
#             x, y = point.x, point.y

#         # Формируем подписи
#         if qty > 0:
#             # Основной текст с общим количеством
#             main_text = f"{district}\n{format_number(qty)}"
            
#             # Дополнительная строка с деталями
#             warehouses_text = format_warehouses(warehouses)
#             transit_icon = "🚚" if in_transit > 0 else "📦"
#             transit_text = f"{transit_icon} {format_number_compact(in_transit)}"
            
#             sub_text = f"{warehouses_text}  |  {transit_text}"
            
#             # Основная подпись (сверху)
#             ax.text(
#                 x,
#                 y + 0.7,
#                 main_text,
#                 ha="center",
#                 va="center",
#                 fontsize=8.5,
#                 color=COLOR_TEXT,
#                 fontweight=600,
#                 linespacing=1.08,
#                 zorder=5,
#                 bbox=dict(
#                     boxstyle="round,pad=0.34,rounding_size=0.16",
#                     facecolor="#FAFAF8",
#                     edgecolor="#B6C4BD",
#                     linewidth=0.8,
#                     alpha=0.96,
#                 ),
#             )
            
#             # Дополнительная информация (снизу, меньше)
#             ax.text(
#                 x,
#                 y - 0.9,
#                 sub_text,
#                 ha="center",
#                 va="center",
#                 fontsize=6.5,
#                 color=COLOR_MUTED,
#                 fontweight=400,
#                 linespacing=1.2,
#                 zorder=5,
#                 alpha=0.9,
#             )
#         else:
#             # Регион без данных
#             ax.text(
#                 x,
#                 y,
#                 f"{district}\nнет данных",
#                 ha="center",
#                 va="center",
#                 fontsize=8.5,
#                 color=COLOR_MUTED,
#                 fontweight=500,
#                 linespacing=1.08,
#                 zorder=5,
#                 bbox=dict(
#                     boxstyle="round,pad=0.34,rounding_size=0.16",
#                     facecolor="#FAFAF8",
#                     edgecolor="#D0D8D3",
#                     linewidth=0.6,
#                     alpha=0.85,
#                 ),
#             )

#     # Настройки карты
#     ax.set_xlim(20, 180)
#     ax.set_ylim(40, 76)

#     # Заголовок
#     ax.set_title(
#         f"📊 География остатков товаров по регионам России\nна {report_date}",
#         fontsize=17,
#         fontweight="bold",
#         color=COLOR_TEXT,
#         pad=18,
#     )

#     # Легенда
#     legend_text = (
#         "🎨 Цвет → общие остатки (на складе + в пути)\n"
#         "🏪 → количество складов в регионе\n"
#         "🚚 → товары в пути к/от клиентов"
#     )
    
#     ax.text(
#         0.02,
#         0.02,
#         legend_text,
#         transform=ax.transAxes,
#         ha="left",
#         va="bottom",
#         fontsize=8,
#         color=COLOR_MUTED,
#         bbox=dict(
#             boxstyle="round,pad=0.3",
#             facecolor="#FAFAF8",
#             edgecolor="#B6C4BD",
#             linewidth=0.5,
#             alpha=0.85,
#         ),
#     )

#     # Убираем оси
#     ax.set_xticks([])
#     ax.set_yticks([])
#     ax.grid(False)

#     for spine in ax.spines.values():
#         spine.set_visible(False)

#     # Сохраняем
#     plt.tight_layout(pad=0.4)

#     buffer = io.BytesIO()
#     fig.savefig(
#         buffer,
#         format="png",
#         dpi=180,
#         bbox_inches="tight",
#         facecolor=COLOR_BG,
#     )
#     plt.close(fig)
#     buffer.seek(0)

#     return buffer


# # Алиас для обратной совместимости
# build_regions_stock_map_png = build_russia_regions_map





# # inventories/reporting/map/russia_regions_map.py
# from __future__ import annotations

# import io
# import re
# from pathlib import Path

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


# COLOR_BG = "#F4F8F6"
# COLOR_BASE = "#E6ECE9"
# COLOR_TEXT = "#18352F"
# COLOR_MUTED = "#60746D"
# COLOR_PRIMARY = "#006B4F"


# WAREHOUSE_REGIONS = [
#     "Центральный",
#     "Приволжский",
#     "Уральский",
#     "Южный и Северо-Кавказский",
#     "Дальневосточный и Сибирский",
# ]


# LABEL_POINTS = {
#     "Центральный": (38, 55),
#     "Приволжский": (50, 55),
#     "Уральский": (63, 60),
#     "Южный и Северо-Кавказский": (43, 45),
#     "Дальневосточный и Сибирский": (105, 61),
# }


# DISTRICT_KEYWORDS = {
#     "Центральный": [
#         "moscow", "moskva", "belgorod", "bryansk", "vladimir", "voronezh",
#         "ivanovo", "kaluga", "kostroma", "kursk", "lipetsk", "oryol",
#         "orel", "ryazan", "smolensk", "tambov", "tver", "tula", "yaroslavl",
#     ],
#     "Приволжский": [
#         "bashkortostan", "mari", "mordovia", "tatarstan", "udmurt",
#         "chuvash", "perm", "kirov", "nizhny", "novgorod", "orenburg",
#         "penza", "samara", "saratov", "ulyanovsk",
#     ],
#     "Уральский": [
#         "kurgan", "sverdlovsk", "tyumen", "chelyabinsk",
#         "khanty", "mansiy", "yamal", "nenets",
#     ],
#     "Южный и Северо-Кавказский": [
#         "adygey", "adygea", "kalmyk", "crimea", "krasnodar", "astrakhan",
#         "volgograd", "rostov", "dagestan", "ingush", "kabardin",
#         "balkar", "karachay", "cherkess", "ossetia", "chechnya",
#         "stavropol",
#     ],
#     "Дальневосточный и Сибирский": [
#         "altay", "altai", "buryat", "tuva", "tyva", "khakass",
#         "krasnoyarsk", "irkutsk", "kemerovo", "novosibirsk", "omsk",
#         "tomsk", "zabaykal", "transbaikal", "sakha", "yakutia",
#         "kamchatka", "primorye", "primorsky", "khabarovsk", "amur",
#         "magadan", "sakhalin", "jewish", "chukotka",
#     ],
# }


# def get_shapefile_path() -> Path:
#     current_file = Path(__file__).resolve()
#     shp_path = (
#         current_file.parent.parent
#         / "assets"
#         / "maps"
#         / "russia_regions"
#         / "ne_10m_admin_1_states_provinces.shp"
#     )

#     if not shp_path.exists():
#         raise FileNotFoundError(f"Shapefile не найден: {shp_path}")

#     return shp_path


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


# def format_warehouses(count: int) -> str:
#     return f"скл.: {int(count or 0)}"


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
#         ["#EEF5F1", "#DCEBE4", "#BFD8CF", "#94BBAF", "#5D9283", COLOR_PRIMARY],
#         N=256,
#     )


# def _clean_text(value: object) -> str:
#     s = str(value or "").lower()
#     s = s.replace("’", "'")
#     s = re.sub(r"[^a-zа-яё0-9]+", " ", s)
#     return re.sub(r"\s+", " ", s).strip()


# def _find_name_col(gdf: pd.DataFrame) -> str:
#     candidates = [
#         "name",
#         "NAME",
#         "name_en",
#         "NAME_EN",
#         "name_local",
#         "NAME_LOCAL",
#         "region",
#         "province",
#         "gn_name",
#         "GN_NAME",
#     ]

#     for col in candidates:
#         if col in gdf.columns:
#             return col

#     raise ValueError(
#         f"Не найдена колонка с названием региона. Колонки shapefile: {list(gdf.columns)}"
#     )


# def _filter_russia_if_possible(gdf):
#     candidates = [
#         "adm0_a3",
#         "ADM0_A3",
#         "iso_a2",
#         "ISO_A2",
#         "admin",
#         "ADMIN",
#         "geonunit",
#         "GEOUNIT",
#         "sov_a3",
#         "SOV_A3",
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
#             print(f"Фильтр России применен по колонке {col}: {len(filtered)} строк")
#             return filtered

#     print("Фильтр России не применен: подходящая колонка не найдена или дала 0 строк")
#     return gdf


# def _detect_district(region_name: object) -> str | None:
#     text = _clean_text(region_name)

#     for district, keywords in DISTRICT_KEYWORDS.items():
#         for keyword in keywords:
#             if keyword in text:
#                 return district

#     return None


# def _prepare_district_geometries():
#     shp_path = get_shapefile_path()
#     gdf = gpd.read_file(shp_path)

#     print("Shapefile:", shp_path)
#     print("Всего объектов в shapefile:", len(gdf))
#     print("Колонки shapefile:", list(gdf.columns))

#     gdf = _filter_russia_if_possible(gdf)

#     name_col = _find_name_col(gdf)

#     sample_names = gdf[name_col].dropna().astype(str).head(80).to_list()
#     print("Колонка названия региона:", name_col)
#     print("Примеры названий:", sample_names)

#     gdf["district"] = gdf[name_col].apply(_detect_district)

#     matched_count = int(gdf["district"].notna().sum())
#     print("Сопоставлено с нашими округами:", matched_count)

#     if matched_count == 0:
#         all_names = gdf[name_col].dropna().astype(str).head(150).to_list()
#         raise ValueError(
#             "Не удалось сопоставить ни один субъект РФ с округами. "
#             f"Колонка названия: {name_col}. "
#             f"Примеры значений: {all_names}"
#         )

#     unmatched = sorted(
#         gdf.loc[gdf["district"].isna(), name_col]
#         .dropna()
#         .astype(str)
#         .unique()
#         .tolist()
#     )

#     if unmatched:
#         print("Не сопоставлены объекты shapefile:")
#         for x in unmatched[:120]:
#             print(" -", x)

#     gdf = gdf[gdf["district"].notna()].copy()
#     gdf = gdf[gdf.geometry.notna()].copy()

#     if gdf.empty:
#         raise ValueError("После сопоставления не осталось валидной геометрии")

#     districts = gdf.dissolve(by="district", as_index=False)
#     districts = districts[districts.geometry.notna()].copy()

#     if districts.empty:
#         raise ValueError("После dissolve получился пустой GeoDataFrame")

#     return districts


# def _prepare_region_stats(region_stats: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
#     region_stats = region_stats.copy()

#     required_cols = ["регион", "на_складе", "в_пути", "складов", "итого"]
#     missing_cols = [col for col in required_cols if col not in region_stats.columns]

#     if missing_cols:
#         raise ValueError(f"В region_stats отсутствуют колонки: {missing_cols}")

#     region_stats["регион"] = region_stats["регион"].astype(str).str.strip()
#     region_stats["на_складе"] = pd.to_numeric(region_stats["на_складе"], errors="coerce").fillna(0)
#     region_stats["в_пути"] = pd.to_numeric(region_stats["в_пути"], errors="coerce").fillna(0)
#     region_stats["складов"] = pd.to_numeric(region_stats["складов"], errors="coerce").fillna(0).astype(int)
#     region_stats["итого"] = pd.to_numeric(region_stats["итого"], errors="coerce").fillna(0)

#     known_mask = region_stats["регион"].isin(WAREHOUSE_REGIONS)

#     mapped_stats = region_stats.loc[known_mask].copy()
#     unmapped_stats = region_stats.loc[~known_mask].copy()

#     return mapped_stats, unmapped_stats


# def _build_legend_text(unmapped_stats: pd.DataFrame) -> str:
#     legend_lines = [
#         "Цвет — общие остатки: на складе + в пути",
#         "скл. — количество складов в зоне",
#         "в пути — товары в пути к/от клиентов",
#     ]

#     if not unmapped_stats.empty:
#         unmapped_total = float(unmapped_stats["итого"].sum())
#         unmapped_warehouses = int(unmapped_stats["складов"].sum())

#         unmapped_names = (
#             unmapped_stats["регион"]
#             .dropna()
#             .astype(str)
#             .sort_values()
#             .tolist()
#         )

#         legend_lines += [
#             "",
#             "Требует проверки распределения:",
#             f"не распределено: {format_number(unmapped_total)}",
#             f"складов: {unmapped_warehouses}",
#         ]

#         if unmapped_names:
#             shown = unmapped_names[:5]
#             legend_lines.append("регионы: " + ", ".join(shown))

#             if len(unmapped_names) > 5:
#                 legend_lines.append(f"и еще регионов: {len(unmapped_names) - 5}")

#     return "\n".join(legend_lines)


# def build_russia_regions_map(region_stats: pd.DataFrame, report_date: str) -> io.BytesIO:
#     if gpd is None:
#         raise ImportError("Установите geopandas: pip install geopandas")

#     if region_stats.empty:
#         raise ValueError("Нет данных для построения карты")

#     mapped_stats, unmapped_stats = _prepare_region_stats(region_stats)

#     print("\n" + "=" * 60)
#     print("Данные по складским регионам:")
#     print(mapped_stats.to_string(index=False))
#     print("=" * 60 + "\n")

#     if not unmapped_stats.empty:
#         print("\nНЕ РАСПРЕДЕЛЕНЫ ПО УКРУПНЕННЫМ ЗОНАМ:")
#         print(unmapped_stats.to_string(index=False))
#         print()

#     districts = _prepare_district_geometries()

#     districts = districts.merge(
#         mapped_stats,
#         how="left",
#         left_on="district",
#         right_on="регион",
#     )

#     districts["итого"] = districts["итого"].fillna(0)
#     districts["на_складе"] = districts["на_складе"].fillna(0)
#     districts["в_пути"] = districts["в_пути"].fillna(0)
#     districts["складов"] = districts["складов"].fillna(0).astype(int)

#     missing_data = districts.loc[districts["регион"].isna(), "district"].tolist()

#     if missing_data:
#         print("\nНЕТ ДАННЫХ ПО СЛЕДУЮЩИМ ЗОНАМ:")
#         for x in missing_data:
#             print(f" - {x}")
#         print()

#     fig, ax = plt.subplots(figsize=(14.5, 7.2), dpi=180)
#     fig.patch.set_facecolor(COLOR_BG)
#     ax.set_facecolor(COLOR_BG)
#     ax.set_aspect("auto")

#     districts.plot(
#         ax=ax,
#         color=COLOR_BASE,
#         edgecolor="#FFFFFF",
#         linewidth=1.0,
#         zorder=1,
#     )

#     colored = districts[districts["итого"] > 0].copy()

#     if not colored.empty:
#         cmap = _build_cmap()

#         vmin = float(colored["итого"].min())
#         vmax = float(colored["итого"].max())

#         gamma = 0.45 if vmax > vmin else 1.0
#         norm = mcolors.PowerNorm(gamma=gamma, vmin=vmin, vmax=vmax)

#         colored.plot(
#             ax=ax,
#             column="итого",
#             cmap=cmap,
#             norm=norm,
#             edgecolor="#FFFFFF",
#             linewidth=1.35,
#             zorder=3,
#         )

#         sm = ScalarMappable(norm=norm, cmap=cmap)
#         sm.set_array([])

#         cbar = fig.colorbar(
#             sm,
#             ax=ax,
#             orientation="vertical",
#             fraction=0.025,
#             pad=0.015,
#             shrink=0.72,
#         )

#         cbar.outline.set_edgecolor("#AAB7B0")
#         cbar.outline.set_linewidth(0.8)
#         cbar.ax.yaxis.set_major_formatter(FuncFormatter(_format_tick))
#         cbar.ax.tick_params(labelsize=8, colors=COLOR_MUTED, length=0)
#         cbar.set_label("Остатки, шт", fontsize=9, color=COLOR_TEXT, labelpad=8)

#     for _, row in districts.iterrows():
#         district = row["district"]
#         qty = float(row["итого"] or 0)
#         in_transit = float(row["в_пути"] or 0)
#         warehouses = int(row["складов"] or 0)

#         if district in LABEL_POINTS:
#             x, y = LABEL_POINTS[district]
#         else:
#             point = row.geometry.representative_point()
#             x, y = point.x, point.y

#         if qty > 0:
#             main_text = f"{district}\n{format_number(qty)}"

#             warehouses_text = format_warehouses(warehouses)
#             transit_text = f"в пути: {format_number_compact(in_transit)}"
#             sub_text = f"{warehouses_text}  |  {transit_text}"

#             ax.text(
#                 x,
#                 y + 0.7,
#                 main_text,
#                 ha="center",
#                 va="center",
#                 fontsize=8.5,
#                 color=COLOR_TEXT,
#                 fontweight=600,
#                 linespacing=1.08,
#                 zorder=5,
#                 bbox=dict(
#                     boxstyle="round,pad=0.34,rounding_size=0.16",
#                     facecolor="#FAFAF8",
#                     edgecolor="#B6C4BD",
#                     linewidth=0.8,
#                     alpha=0.96,
#                 ),
#             )

#             ax.text(
#                 x,
#                 y - 0.9,
#                 sub_text,
#                 ha="center",
#                 va="center",
#                 fontsize=6.5,
#                 color=COLOR_MUTED,
#                 fontweight=400,
#                 linespacing=1.2,
#                 zorder=5,
#                 alpha=0.9,
#             )

#         else:
#             ax.text(
#                 x,
#                 y,
#                 f"{district}\nнет данных",
#                 ha="center",
#                 va="center",
#                 fontsize=8.5,
#                 color=COLOR_MUTED,
#                 fontweight=500,
#                 linespacing=1.08,
#                 zorder=5,
#                 bbox=dict(
#                     boxstyle="round,pad=0.34,rounding_size=0.16",
#                     facecolor="#FAFAF8",
#                     edgecolor="#D0D8D3",
#                     linewidth=0.6,
#                     alpha=0.85,
#                 ),
#             )

#     ax.set_xlim(20, 180)
#     ax.set_ylim(40, 76)

#     ax.set_title(
#         f"География остатков товаров по регионам России\nна {report_date}",
#         fontsize=17,
#         fontweight="bold",
#         color=COLOR_TEXT,
#         pad=18,
#     )

#     legend_text = _build_legend_text(unmapped_stats)

#     ax.text(
#         0.02,
#         0.02,
#         legend_text,
#         transform=ax.transAxes,
#         ha="left",
#         va="bottom",
#         fontsize=8,
#         color=COLOR_MUTED,
#         bbox=dict(
#             boxstyle="round,pad=0.3",
#             facecolor="#FAFAF8",
#             edgecolor="#B6C4BD",
#             linewidth=0.5,
#             alpha=0.88,
#         ),
#     )

#     ax.set_xticks([])
#     ax.set_yticks([])
#     ax.grid(False)

#     for spine in ax.spines.values():
#         spine.set_visible(False)

#     plt.tight_layout(pad=0.4)

#     buffer = io.BytesIO()
#     fig.savefig(
#         buffer,
#         format="png",
#         dpi=180,
#         bbox_inches="tight",
#         facecolor=COLOR_BG,
#     )
#     plt.close(fig)
#     buffer.seek(0)

#     return buffer


# build_regions_stock_map_png = build_russia_regions_map





# # inventories/reporting/map/russia_regions_map.py
# from __future__ import annotations

# import io
# import re
# from pathlib import Path

# import matplotlib
# matplotlib.use("Agg")

# import matplotlib.pyplot as plt
# import pandas as pd
# import numpy as np
# from matplotlib import colors as mcolors
# from matplotlib.cm import ScalarMappable
# from matplotlib.ticker import FuncFormatter
# from matplotlib.patches import Rectangle

# try:
#     import geopandas as gpd
# except ImportError:
#     gpd = None


# COLOR_BG = "#F4F8F6"
# COLOR_BASE = "#E6ECE9"
# COLOR_TEXT = "#18352F"
# COLOR_MUTED = "#60746D"
# COLOR_PRIMARY = "#006B4F"


# WAREHOUSE_REGIONS = [
#     "Центральный",
#     "Приволжский",
#     "Уральский",
#     "Южный и Северо-Кавказский",
#     "Дальневосточный и Сибирский",
#     "Северо-Западный",
# ]


# LABEL_POINTS = {
#     "Центральный": (38, 55),
#     "Приволжский": (50, 55),
#     "Уральский": (63, 60),
#     "Южный и Северо-Кавказский": (43, 45),
#     "Дальневосточный и Сибирский": (105, 61),
#     "Северо-Западный": (55, 62), 
# }


# DISTRICT_KEYWORDS = {
#     "Центральный": [
#         "moscow", "moskva", "belgorod", "bryansk", "vladimir", "voronezh",
#         "ivanovo", "kaluga", "kostroma", "kursk", "lipetsk", "oryol",
#         "orel", "ryazan", "smolensk", "tambov", "tver", "tula", "yaroslavl",
#     ],
#     "Приволжский": [
#         "bashkortostan", "mari", "mordovia", "tatarstan", "udmurt",
#         "chuvash", "perm", "kirov", "nizhny", "novgorod", "orenburg",
#         "penza", "samara", "saratov", "ulyanovsk",
#     ],
#     "Уральский": [
#         "kurgan", "sverdlovsk", "tyumen", "chelyabinsk",
#         "khanty", "mansiy", "yamal", "nenets",
#     ],
#     "Южный и Северо-Кавказский": [
#         "adygey", "adygea", "kalmyk", "crimea", "krasnodar", "astrakhan",
#         "volgograd", "rostov", "dagestan", "ingush", "kabardin",
#         "balkar", "karachay", "cherkess", "ossetia", "chechnya",
#         "stavropol",
#     ],
#     "Дальневосточный и Сибирский": [
#         "altay", "altai", "buryat", "tuva", "tyva", "khakass",
#         "krasnoyarsk", "irkutsk", "kemerovo", "novosibirsk", "omsk",
#         "tomsk", "zabaykal", "transbaikal", "sakha", "yakutia",
#         "kamchatka", "primorye", "primorsky", "khabarovsk", "amur",
#         "magadan", "sakhalin", "jewish", "chukotka",
#     ],
#     "Северо-Западный": [  
#         "st. petersburg", "saint petersburg", "leningrad", "kaliningrad",
#         "murmansk", "arkhangelsk", "novgorod", "pskov", "karelia",
#         "komi", "vologda",
#     ],
# }


# # Данные для отображения стран (прямоугольники)
# COUNTRIES_RECTANGLES = {
#     "Армения": {
#         "center": (45, 40.5),
#         "x": 44, "y": 38.5, "width": 3.5, "height": 3,
#     },
#     "Беларусь": {
#         "center": (28, 53.5),
#         "x": 23, "y": 51, "width": 10, "height": 5,
#     },
#     "Грузия": {
#         "center": (43.5, 42.2),
#         "x": 40, "y": 41, "width": 6.5, "height": 3,
#     },
#     "Казахстан": {
#         "center": (67, 48),
#         "x": 46, "y": 41, "width": 41, "height": 14,
#     },
#      "Узбекистан": {
#         "center": (66, 41.5),
#         "x": 56, "y": 37, "width": 18, "height": 9,
#     },
#      "Таджикистан": {  
#         "center": (71, 38.5),
#         "x": 67, "y": 36.5, "width": 8, "height": 4.5,
#     },
# }


# def get_shapefile_path() -> Path:
#     current_file = Path(__file__).resolve()
#     shp_path = (
#         current_file.parent.parent
#         / "assets"
#         / "maps"
#         / "russia_regions"
#         / "ne_10m_admin_1_states_provinces.shp"
#     )

#     if not shp_path.exists():
#         raise FileNotFoundError(f"Shapefile не найден: {shp_path}")

#     return shp_path


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


# def format_warehouses(count: int) -> str:
#     return f"скл.: {int(count or 0)}"


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
#         ["#EEF5F1", "#DCEBE4", "#BFD8CF", "#94BBAF", "#5D9283", COLOR_PRIMARY],
#         N=256,
#     )


# def _clean_text(value: object) -> str:
#     s = str(value or "").lower()
#     s = s.replace("’", "'")
#     s = re.sub(r"[^a-zа-яё0-9]+", " ", s)
#     return re.sub(r"\s+", " ", s).strip()


# def _find_name_col(gdf: pd.DataFrame) -> str:
#     candidates = [
#         "name",
#         "NAME",
#         "name_en",
#         "NAME_EN",
#         "name_local",
#         "NAME_LOCAL",
#         "region",
#         "province",
#         "gn_name",
#         "GN_NAME",
#     ]

#     for col in candidates:
#         if col in gdf.columns:
#             return col

#     raise ValueError(
#         f"Не найдена колонка с названием региона. Колонки shapefile: {list(gdf.columns)}"
#     )


# def _filter_russia_if_possible(gdf):
#     candidates = [
#         "adm0_a3",
#         "ADM0_A3",
#         "iso_a2",
#         "ISO_A2",
#         "admin",
#         "ADMIN",
#         "geonunit",
#         "GEOUNIT",
#         "sov_a3",
#         "SOV_A3",
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
#             print(f"Фильтр России применен по колонке {col}: {len(filtered)} строк")
#             return filtered

#     print("Фильтр России не применен: подходящая колонка не найдена или дала 0 строк")
#     return gdf


# def _detect_district(region_name: object) -> str | None:
#     text = _clean_text(region_name)

#     for district, keywords in DISTRICT_KEYWORDS.items():
#         for keyword in keywords:
#             if keyword in text:
#                 return district

#     return None


# def _prepare_district_geometries():
#     shp_path = get_shapefile_path()
#     gdf = gpd.read_file(shp_path)

#     print("Shapefile:", shp_path)
#     print("Всего объектов в shapefile:", len(gdf))
#     print("Колонки shapefile:", list(gdf.columns))

#     gdf = _filter_russia_if_possible(gdf)

#     name_col = _find_name_col(gdf)

#     sample_names = gdf[name_col].dropna().astype(str).head(80).to_list()
#     print("Колонка названия региона:", name_col)
#     print("Примеры названий:", sample_names)

#     gdf["district"] = gdf[name_col].apply(_detect_district)

#     matched_count = int(gdf["district"].notna().sum())
#     print("Сопоставлено с нашими округами:", matched_count)

#     if matched_count == 0:
#         all_names = gdf[name_col].dropna().astype(str).head(150).to_list()
#         raise ValueError(
#             "Не удалось сопоставить ни один субъект РФ с округами. "
#             f"Колонка названия: {name_col}. "
#             f"Примеры значений: {all_names}"
#         )

#     unmatched = sorted(
#         gdf.loc[gdf["district"].isna(), name_col]
#         .dropna()
#         .astype(str)
#         .unique()
#         .tolist()
#     )

#     if unmatched:
#         print("Не сопоставлены объекты shapefile:")
#         for x in unmatched[:120]:
#             print(" -", x)

#     gdf = gdf[gdf["district"].notna()].copy()
#     gdf = gdf[gdf.geometry.notna()].copy()

#     if gdf.empty:
#         raise ValueError("После сопоставления не осталось валидной геометрии")

#     districts = gdf.dissolve(by="district", as_index=False)
#     districts = districts[districts.geometry.notna()].copy()

#     if districts.empty:
#         raise ValueError("После dissolve получился пустой GeoDataFrame")

#     return districts


# def draw_country_rectangle(ax, country_name: str, color: str, alpha: float = 0.8):
#     """Рисует прямоугольник для страны"""
#     if country_name in COUNTRIES_RECTANGLES:
#         rect_data = COUNTRIES_RECTANGLES[country_name]
#         rect = Rectangle(
#             (rect_data["x"], rect_data["y"]),
#             rect_data["width"],
#             rect_data["height"],
#             facecolor=color,
#             edgecolor="#FFFFFF",
#             linewidth=1.5,
#             alpha=alpha,
#             zorder=2
#         )
#         ax.add_patch(rect)


# def build_russia_regions_map(region_stats: pd.DataFrame, report_date: str) -> io.BytesIO:
#     if gpd is None:
#         raise ImportError("Установите geopandas: pip install geopandas")

#     if region_stats.empty:
#         raise ValueError("Нет данных для построения карты")

#     # Подготавливаем данные
#     region_stats = region_stats.copy()
    
#     # Проверяем и преобразуем необходимые колонки
#     required_cols = ["регион", "на_складе", "в_пути", "складов", "итого"]
#     for col in required_cols:
#         if col not in region_stats.columns:
#             raise ValueError(f"В region_stats отсутствует колонка: {col}")
    
#     region_stats["регион"] = region_stats["регион"].astype(str).str.strip()
#     region_stats["на_складе"] = pd.to_numeric(region_stats["на_складе"], errors="coerce").fillna(0)
#     region_stats["в_пути"] = pd.to_numeric(region_stats["в_пути"], errors="coerce").fillna(0)
#     region_stats["складов"] = pd.to_numeric(region_stats["складов"], errors="coerce").fillna(0).astype(int)
#     region_stats["итого"] = pd.to_numeric(region_stats["итого"], errors="coerce").fillna(0)

#     # Разделяем на российские регионы и другие страны
#     russia_stats = region_stats[region_stats["регион"].isin(WAREHOUSE_REGIONS)].copy()
#     other_countries_stats = region_stats[region_stats["регион"].isin(COUNTRIES_RECTANGLES.keys())].copy()
#     unmapped_stats = region_stats[~(region_stats["регион"].isin(WAREHOUSE_REGIONS) | 
#                                      region_stats["регион"].isin(COUNTRIES_RECTANGLES.keys()))].copy()

#     print("\n" + "=" * 60)
#     print("Данные по российским складским регионам:")
#     print(russia_stats.to_string(index=False) if not russia_stats.empty else "Нет данных")
#     print("=" * 60 + "\n")

#     if not other_countries_stats.empty:
#         print("\nДАННЫЕ ПО ДРУГИМ СТРАНАМ:")
#         print(other_countries_stats.to_string(index=False))
#         print()

#     if not unmapped_stats.empty:
#         print("\nНЕ РАСПРЕДЕЛЕНЫ ПО УКРУПНЕННЫМ ЗОНАМ:")
#         print(unmapped_stats.to_string(index=False))
#         print()

#     # Получаем геометрии России
#     russia_districts = _prepare_district_geometries()

#     # Создаем фигуру - увеличиваем размер для лучшего отображения Дальнего Востока
#     fig, ax = plt.subplots(figsize=(16, 9), dpi=180)
#     fig.patch.set_facecolor(COLOR_BG)
#     ax.set_facecolor(COLOR_BG)
#     ax.set_aspect("auto")

#     # Рисуем фон для стран
#     for country_name in COUNTRIES_RECTANGLES.keys():
#         draw_country_rectangle(ax, country_name, COLOR_BASE, alpha=0.5)

#     # Рисуем Россию
#     russia_districts.plot(
#         ax=ax,
#         color=COLOR_BASE,
#         edgecolor="#FFFFFF",
#         linewidth=1.0,
#         zorder=1,
#     )

#     # Отрисовываем российские регионы с данными
#     russia_districts_with_data = russia_districts.merge(
#         russia_stats[["регион", "на_складе", "в_пути", "складов", "итого"]],
#         how="left",
#         left_on="district",
#         right_on="регион",
#     )
    
#     # Заполняем NaN значения
#     russia_districts_with_data["итого"] = russia_districts_with_data["итого"].fillna(0)
#     russia_districts_with_data["на_складе"] = russia_districts_with_data["на_складе"].fillna(0)
#     russia_districts_with_data["в_пути"] = russia_districts_with_data["в_пути"].fillna(0)
#     russia_districts_with_data["складов"] = russia_districts_with_data["складов"].fillna(0).astype(int)

#     # Собираем все значения для цветовой шкалы
#     all_values = []
#     if not russia_districts_with_data.empty:
#         all_values.extend(russia_districts_with_data[russia_districts_with_data["итого"] > 0]["итого"].tolist())
#     if not other_countries_stats.empty:
#         all_values.extend(other_countries_stats[other_countries_stats["итого"] > 0]["итого"].tolist())
    
#     # Создаем цветовую шкалу
#     cmap = _build_cmap()
#     if all_values:
#         vmin = float(min(all_values))
#         vmax = float(max(all_values))
#         gamma = 0.45 if vmax > vmin else 1.0
#         norm = mcolors.PowerNorm(gamma=gamma, vmin=vmin, vmax=vmax)
        
#         # Добавляем colorbar
#         sm = ScalarMappable(norm=norm, cmap=cmap)
#         sm.set_array([])
        
#         cbar = fig.colorbar(
#             sm,
#             ax=ax,
#             orientation="vertical",
#             fraction=0.02,
#             pad=0.015,
#             shrink=0.7,
#         )
        
#         cbar.outline.set_edgecolor("#AAB7B0")
#         cbar.outline.set_linewidth(0.8)
#         cbar.ax.yaxis.set_major_formatter(FuncFormatter(_format_tick))
#         cbar.ax.tick_params(labelsize=8, colors=COLOR_MUTED, length=0)
#         cbar.set_label("Остатки, шт", fontsize=9, color=COLOR_TEXT, labelpad=8)
#     else:
#         vmin, vmax = 0, 1
#         norm = mcolors.PowerNorm(gamma=0.45, vmin=vmin, vmax=vmax)

#     # Закрашиваем российские регионы
#     colored_russia = russia_districts_with_data[russia_districts_with_data["итого"] > 0].copy()
#     if not colored_russia.empty:
#         colored_russia.plot(
#             ax=ax,
#             column="итого",
#             cmap=cmap,
#             norm=norm,
#             edgecolor="#FFFFFF",
#             linewidth=1.35,
#             zorder=3,
#         )

#     # Закрашиваем страны
#     for _, country in other_countries_stats.iterrows():
#         country_name = country["регион"]
#         qty = float(country["итого"])
#         if qty > 0:
#             # Нормализуем значение для получения цвета
#             normalized = norm(qty)
#             color = cmap(normalized)
#             draw_country_rectangle(ax, country_name, color, alpha=0.8)

#     # Добавляем подписи для российских регионов
#     for _, row in russia_districts_with_data.iterrows():
#         district = row["district"]
#         qty = float(row["итого"] or 0)
#         in_transit = float(row["в_пути"] or 0)
#         warehouses = int(row["складов"] or 0)

#         if district in LABEL_POINTS:
#             x, y = LABEL_POINTS[district]
#         else:
#             try:
#                 point = row.geometry.representative_point()
#                 x, y = point.x, point.y
#             except:
#                 continue

#         if qty > 0:
#             main_text = f"{district}\n{format_number(qty)}"
#             warehouses_text = format_warehouses(warehouses)
#             transit_text = f"в пути: {format_number_compact(in_transit)}"
#             sub_text = f"{warehouses_text}  |  {transit_text}"

#             ax.text(
#                 x,
#                 y + 0.7,
#                 main_text,
#                 ha="center",
#                 va="center",
#                 fontsize=8.5,
#                 color=COLOR_TEXT,
#                 fontweight=600,
#                 linespacing=1.08,
#                 zorder=5,
#                 bbox=dict(
#                     boxstyle="round,pad=0.34,rounding_size=0.16",
#                     facecolor="#FAFAF8",
#                     edgecolor="#B6C4BD",
#                     linewidth=0.8,
#                     alpha=0.96,
#                 ),
#             )

#             ax.text(
#                 x,
#                 y - 0.9,
#                 sub_text,
#                 ha="center",
#                 va="center",
#                 fontsize=6.5,
#                 color=COLOR_MUTED,
#                 fontweight=400,
#                 linespacing=1.2,
#                 zorder=5,
#                 alpha=0.9,
#             )
#         else:
#             ax.text(
#                 x,
#                 y - 0.5,
#                 f"{district}",
#                 ha="center",
#                 va="center",
#                 fontsize=8.5,
#                 color=COLOR_MUTED,
#                 fontweight=500,
#                 linespacing=1.08,
#                 zorder=5,
#                 bbox=dict(
#                     boxstyle="round,pad=0.34,rounding_size=0.16",
#                     facecolor="#FAFAF8",
#                     edgecolor="#D0D8D3",
#                     linewidth=0.6,
#                     alpha=0.85,
#                 ),
#             )

#     # Добавляем подписи для стран
#     for _, country in other_countries_stats.iterrows():
#         country_name = country["регион"]
#         qty = float(country["итого"] or 0)
#         in_transit = float(country["в_пути"] or 0)
#         warehouses = int(country["складов"] or 0)
        
#         if country_name in COUNTRIES_RECTANGLES:
#             center = COUNTRIES_RECTANGLES[country_name]["center"]
#             x, y = center
            
#             if qty > 0:
#                 main_text = f"{country_name}\n{format_number(qty)}"
#                 warehouses_text = format_warehouses(warehouses)
#                 transit_text = f"в пути: {format_number_compact(in_transit)}"
#                 sub_text = f"{warehouses_text}  |  {transit_text}"
                
#                 ax.text(
#                     x,
#                     y + 1.2,
#                     main_text,
#                     ha="center",
#                     va="center",
#                     fontsize=9,
#                     color=COLOR_TEXT,
#                     fontweight=600,
#                     linespacing=1.08,
#                     zorder=5,
#                     bbox=dict(
#                         boxstyle="round,pad=0.34,rounding_size=0.16",
#                         facecolor="#FAFAF8",
#                         edgecolor="#B6C4BD",
#                         linewidth=0.8,
#                         alpha=0.96,
#                     ),
#                 )
                
#                 ax.text(
#                     x,
#                     y - 1.0,
#                     sub_text,
#                     ha="center",
#                     va="center",
#                     fontsize=7,
#                     color=COLOR_MUTED,
#                     fontweight=400,
#                     linespacing=1.2,
#                     zorder=5,
#                     alpha=0.9,
#                 )
#             else:
#                 ax.text(
#                     x,
#                     y,
#                     f"{country_name}\nнет данных",
#                     ha="center",
#                     va="center",
#                     fontsize=8.5,
#                     color=COLOR_MUTED,
#                     fontweight=400,
#                     linespacing=1.08,
#                     zorder=5,
#                     alpha=0.7,
#                 )

#     # ВАЖНО: ВОЗВРАЩАЕМ ПРАВИЛЬНЫЕ ГРАНИЦЫ ДЛЯ ВСЕЙ РОССИИ
#     # Было неправильно: ax.set_xlim(20, 110) - это обрезает Дальний Восток
#     # Правильно: ax.set_xlim(20, 180) - показывает всю Россию
#     ax.set_xlim(20, 180)
#     ax.set_ylim(40, 76)

#     ax.set_title(
#         f"География остатков товаров по регионам России и странам\nна {report_date}",
#         fontsize=17,
#         fontweight="bold",
#         color=COLOR_TEXT,
#         pad=18,
#     )

#     # Легенда
#     legend_lines = [
#         "Цвет — общие остатки: на складе + в пути",
#         "скл. — количество складов в зоне",
#         "в пути — товары в пути к/от клиентов",
#     ]

#     if not unmapped_stats.empty:
#         unmapped_total = float(unmapped_stats["итого"].sum())
#         unmapped_warehouses = int(unmapped_stats["складов"].sum())

#         unmapped_names = (
#             unmapped_stats["регион"]
#             .dropna()
#             .astype(str)
#             .sort_values()
#             .tolist()
#         )

#         legend_lines += [
#             "",
#             "Требует проверки распределения:",
#             f"не распределено: {format_number(unmapped_total)}",
#             f"складов: {unmapped_warehouses}",
#         ]

#         if unmapped_names:
#             shown = unmapped_names[:5]
#             legend_lines.append("регионы: " + ", ".join(shown))

#             if len(unmapped_names) > 5:
#                 legend_lines.append(f"и еще {len(unmapped_names) - 5}")

#     legend_text = "\n".join(legend_lines)

#     ax.text(
#         0.02,
#         0.02,
#         legend_text,
#         transform=ax.transAxes,
#         ha="left",
#         va="bottom",
#         fontsize=8,
#         color=COLOR_MUTED,
#         bbox=dict(
#             boxstyle="round,pad=0.3",
#             facecolor="#FAFAF8",
#             edgecolor="#B6C4BD",
#             linewidth=0.5,
#             alpha=0.88,
#         ),
#     )

#     ax.set_xticks([])
#     ax.set_yticks([])
#     ax.grid(False)

#     for spine in ax.spines.values():
#         spine.set_visible(False)

#     plt.tight_layout(pad=0.4)

#     buffer = io.BytesIO()
#     fig.savefig(
#         buffer,
#         format="png",
#         dpi=180,
#         bbox_inches="tight",
#         facecolor=COLOR_BG,
#     )
#     plt.close(fig)
#     buffer.seek(0)

#     return buffer


# build_regions_stock_map_png = build_russia_regions_map




# # inventories/reporting/map/russia_regions_map.py
# from __future__ import annotations

# import io
# import re
# from pathlib import Path

# import matplotlib
# matplotlib.use("Agg")

# import matplotlib.pyplot as plt
# import pandas as pd
# import numpy as np
# from matplotlib import colors as mcolors
# from matplotlib.cm import ScalarMappable
# from matplotlib.ticker import FuncFormatter

# try:
#     import geopandas as gpd
# except ImportError:
#     gpd = None

# from .map_config import (
#     COLOR_BG, COLOR_BASE, COLOR_TEXT, COLOR_MUTED, COLOR_PRIMARY,
#     WAREHOUSE_REGIONS, LABEL_POINTS, DISTRICT_KEYWORDS,
#     COUNTRIES_CONFIG, get_russia_shapefile_path, get_world_shapefile_path,
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


# def format_warehouses(count: int) -> str:
#     return f"скл.: {int(count or 0)}"


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
#         ["#EEF5F1", "#DCEBE4", "#BFD8CF", "#94BBAF", "#5D9283", COLOR_PRIMARY],
#         N=256,
#     )


# def _clean_text(value: object) -> str:
#     s = str(value or "").lower()
#     s = s.replace("’", "'")
#     s = re.sub(r"[^a-zа-яё0-9]+", " ", s)
#     return re.sub(r"\s+", " ", s).strip()


# def _find_name_col(gdf: pd.DataFrame) -> str:
#     candidates = ["name", "NAME", "name_en", "NAME_EN", "name_local", "NAME_LOCAL", "region", "province", "gn_name", "GN_NAME"]
#     for col in candidates:
#         if col in gdf.columns:
#             return col
#     raise ValueError(f"Не найдена колонка с названием региона. Колонки: {list(gdf.columns)}")


# def _filter_russia_if_possible(gdf):
#     candidates = ["adm0_a3", "ADM0_A3", "iso_a2", "ISO_A2", "admin", "ADMIN", "geonunit", "GEOUNIT", "sov_a3", "SOV_A3"]
#     for col in candidates:
#         if col not in gdf.columns:
#             continue
#         values = gdf[col].astype(str).str.upper()
#         if col.upper() in {"ADM0_A3", "SOV_A3"}:
#             mask = values.eq("RUS")
#         elif col.upper() == "ISO_A2":
#             mask = values.eq("RU")
#         else:
#             mask = values.str.contains("RUSSIA|RUSSIAN FEDERATION|РОССИЯ|RUS", regex=True, na=False)
#         filtered = gdf[mask].copy()
#         if not filtered.empty:
#             print(f"Фильтр России по колонке {col}: {len(filtered)} строк")
#             return filtered
#     print("Фильтр России не применен")
#     return gdf


# def _detect_district(region_name: object) -> str | None:
#     text = _clean_text(region_name)
#     for district, keywords in DISTRICT_KEYWORDS.items():
#         for keyword in keywords:
#             if keyword in text:
#                 return district
#     return None


# def _prepare_russia_geometries():
#     """Загружает и подготавливает геометрии регионов России"""
#     shp_path = get_russia_shapefile_path()
#     if not shp_path.exists():
#         raise FileNotFoundError(f"Shapefile России не найден: {shp_path}")
    
#     gdf = gpd.read_file(shp_path)
#     print(f"Shapefile России: {shp_path}")
#     print(f"Всего объектов: {len(gdf)}")
    
#     gdf = _filter_russia_if_possible(gdf)
#     name_col = _find_name_col(gdf)
    
#     gdf["district"] = gdf[name_col].apply(_detect_district)
#     matched_count = int(gdf["district"].notna().sum())
#     print(f"Сопоставлено с округами: {matched_count}")
    
#     if matched_count == 0:
#         raise ValueError(f"Не удалось сопоставить регионы. Примеры: {gdf[name_col].head(10).tolist()}")
    
#     gdf = gdf[gdf["district"].notna() & gdf.geometry.notna()].copy()
#     districts = gdf.dissolve(by="district", as_index=False)
#     districts = districts[districts.geometry.notna()].copy()
    
#     return districts


# def _prepare_countries_geometries():
#     """Загружает геометрии стран из world shapefile"""
#     shp_path = get_world_shapefile_path()
#     if not shp_path.exists():
#         print(f"Shapefile мира не найден: {shp_path}")
#         return None
    
#     gdf = gpd.read_file(shp_path)
    
#     # Выводим список колонок для отладки
#     print("Колонки shapefile мира:", list(gdf.columns))
    
#     # Пробуем разные возможные названия колонок
#     country_col = None
#     for col in ["ADMIN", "NAME", "SOVEREIGNT", "admin", "name", "NAME_EN", "name_en", "COUNTRY"]:
#         if col in gdf.columns:
#             country_col = col
#             print(f"Используем колонку: {country_col}")
#             break
    
#     if country_col is None:
#         print("Не найдена колонка с названиями стран. Доступные колонки:", list(gdf.columns))
#         return None
    
#     # Получаем названия стран на английском из конфига
#     country_names_en = [COUNTRIES_CONFIG[c]["name_en"] for c in COUNTRIES_CONFIG]
    
#     # Фильтруем нужные страны
#     mask = gdf[country_col].isin(country_names_en)
#     countries_gdf = gdf[mask].copy()
    
#     if countries_gdf.empty:
#         print(f"Страны не найдены. Искали: {country_names_en}")
#         print("Доступные страны в shapefile:", gdf[country_col].head(50).tolist())
#         return None
    
#     # Добавляем русские названия
#     name_to_ru = {COUNTRIES_CONFIG[c]["name_en"]: c for c in COUNTRIES_CONFIG}
#     countries_gdf["name_ru"] = countries_gdf[country_col].map(name_to_ru)
    
#     print(f"Загружено стран из shapefile: {len(countries_gdf)}")
#     for _, row in countries_gdf.iterrows():
#         print(f"  - {row[country_col]} -> {row['name_ru']}")
    
#     return countries_gdf

# def _format_label_text(qty: float, in_transit: float, warehouses: int, name: str, has_data: bool = True) -> tuple:
#     """Формирует текст подписи для региона/страны"""
#     if not has_data or qty == 0:
#         return f"{name}\nнет данных", None
    
#     main_text = f"{name}\n{format_number(qty)}"
#     warehouses_text = format_warehouses(warehouses)
#     transit_text = f"в пути: {format_number_compact(in_transit)}"
#     sub_text = f"{warehouses_text}  |  {transit_text}"
    
#     return main_text, sub_text


# def build_russia_regions_map(region_stats: pd.DataFrame, report_date: str) -> io.BytesIO:
#     if gpd is None:
#         raise ImportError("Установите geopandas: pip install geopandas")
    
#     if region_stats.empty:
#         raise ValueError("Нет данных для построения карты")
    
#     # Подготовка данных
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
    
#     # Разделяем данные
#     russia_stats = region_stats[region_stats["регион"].isin(WAREHOUSE_REGIONS)].copy()
#     countries_stats = region_stats[region_stats["регион"].isin(COUNTRIES_CONFIG.keys())].copy()
#     unmapped_stats = region_stats[~(region_stats["регион"].isin(WAREHOUSE_REGIONS) | 
#                                      region_stats["регион"].isin(COUNTRIES_CONFIG.keys()))].copy()
    

    
#     # Загружаем геометрии
#     russia_districts = _prepare_russia_geometries()
#     countries_geoms = _prepare_countries_geometries()
    
#     # Создаем фигуру
#     fig, ax = plt.subplots(figsize=(18, 10), dpi=180)
#     fig.patch.set_facecolor(COLOR_BG)
#     ax.set_facecolor(COLOR_BG)
    
#     # Рисуем страны (фон)
#     if countries_geoms is not None and not countries_geoms.empty:
#         countries_geoms.plot(ax=ax, color=COLOR_BASE, edgecolor="#FFFFFF", linewidth=0.8, zorder=1)
    
#     # Рисуем Россию
#     russia_districts.plot(ax=ax, color=COLOR_BASE, edgecolor="#FFFFFF", linewidth=1.0, zorder=2)
    
#     # Объединяем данные с геометриями России
#     russia_with_data = russia_districts.merge(
#         russia_stats[["регион", "на_складе", "в_пути", "складов", "итого"]],
#         how="left",
#         left_on="district",
#         right_on="регион",
#     )
#     for col in ["итого", "на_складе", "в_пути", "складов"]:
#         russia_with_data[col] = russia_with_data[col].fillna(0)
#     russia_with_data["складов"] = russia_with_data["складов"].astype(int)
    
#     # Собираем все значения для цветовой шкалы
#     all_values = []
#     if not russia_with_data.empty:
#         all_values.extend(russia_with_data[russia_with_data["итого"] > 0]["итого"].tolist())
#     if not countries_stats.empty:
#         all_values.extend(countries_stats[countries_stats["итого"] > 0]["итого"].tolist())
    
#     # Цветовая шкала
#     cmap = _build_cmap()
#     if all_values:
#         vmin, vmax = float(min(all_values)), float(max(all_values))
#         gamma = 0.45 if vmax > vmin else 1.0
#         norm = mcolors.PowerNorm(gamma=gamma, vmin=vmin, vmax=vmax)
        
#         sm = ScalarMappable(norm=norm, cmap=cmap)
#         sm.set_array([])
#         cbar = fig.colorbar(sm, ax=ax, orientation="vertical", fraction=0.02, pad=0.015, shrink=0.7)
#         cbar.outline.set_edgecolor("#AAB7B0")
#         cbar.ax.yaxis.set_major_formatter(FuncFormatter(_format_tick))
#         cbar.ax.tick_params(labelsize=8, colors=COLOR_MUTED, length=0)
#         cbar.set_label("Остатки, шт", fontsize=9, color=COLOR_TEXT, labelpad=8)
#     else:
#         vmin, vmax = 0, 1
#         norm = mcolors.PowerNorm(gamma=0.45, vmin=vmin, vmax=vmax)
    
#     # Закрашиваем российские регионы
#     colored_russia = russia_with_data[russia_with_data["итого"] > 0].copy()
#     if not colored_russia.empty:
#         colored_russia.plot(ax=ax, column="итого", cmap=cmap, norm=norm,
#                            edgecolor="#FFFFFF", linewidth=1.35, zorder=3)
    
#     # Закрашиваем страны
#     if countries_geoms is not None and not countries_geoms.empty and not countries_stats.empty:
#         countries_with_data = countries_geoms.merge(
#             countries_stats[["регион", "на_складе", "в_пути", "складов", "итого"]],
#             how="left",
#             left_on="name_ru",
#             right_on="регион",
#         )
#         countries_with_data["итого"] = countries_with_data["итого"].fillna(0)
#         countries_with_data["на_складе"] = countries_with_data["на_складе"].fillna(0)
#         countries_with_data["в_пути"] = countries_with_data["в_пути"].fillna(0)
#         countries_with_data["складов"] = countries_with_data["складов"].fillna(0).astype(int)
        
#         colored_countries = countries_with_data[countries_with_data["итого"] > 0].copy()
#         if not colored_countries.empty:
#             colored_countries.plot(ax=ax, column="итого", cmap=cmap, norm=norm,
#                                    edgecolor="#FFFFFF", linewidth=1.2, zorder=4)
    
#     # Подписи для российских регионов
#     for _, row in russia_with_data.iterrows():
#         district = row["district"]
#         qty = float(row["итого"])
#         in_transit = float(row["в_пути"])
#         warehouses = int(row["складов"])
        
#         x, y = LABEL_POINTS.get(district, (None, None))
#         if x is None:
#             try:
#                 point = row.geometry.representative_point()
#                 x, y = point.x, point.y
#             except:
#                 continue
        
#         main_text, sub_text = _format_label_text(qty, in_transit, warehouses, district, qty > 0)
        
#         if qty > 0:
#             ax.text(x, y + 0.7, main_text, ha="center", va="center", fontsize=9,
#                     color=COLOR_TEXT, fontweight=600, zorder=5,
#                     bbox=dict(boxstyle="round,pad=0.34", facecolor="#FAFAF8",
#                              edgecolor="#B6C4BD", linewidth=0.8, alpha=0.96))
#             ax.text(x, y - 0.9, sub_text, ha="center", va="center", fontsize=7,
#                     color=COLOR_MUTED, zorder=5, alpha=0.9)
#         else:
#             ax.text(x, y, district, ha="center", va="center", fontsize=9,
#                     color=COLOR_MUTED, zorder=5,
#                     bbox=dict(boxstyle="round,pad=0.34", facecolor="#FAFAF8",
#                              edgecolor="#D0D8D3", linewidth=0.6, alpha=0.85))
    
#     # Подписи для стран
#     for _, row in countries_stats.iterrows():
#         country_name = row["регион"]
#         qty = float(row["итого"])
#         in_transit = float(row["в_пути"])
#         warehouses = int(row["складов"])
        
#         if country_name in COUNTRIES_CONFIG:
#             x, y = COUNTRIES_CONFIG[country_name]["center"]
#             main_text, sub_text = _format_label_text(qty, in_transit, warehouses, country_name, qty > 0)
            
#             if qty > 0:
#                 ax.text(x, y + 1.0, main_text, ha="center", va="center", fontsize=9,
#                         color=COLOR_TEXT, fontweight=600, zorder=5,
#                         bbox=dict(boxstyle="round,pad=0.34", facecolor="#FAFAF8",
#                                  edgecolor="#B6C4BD", linewidth=0.8, alpha=0.96))
#                 ax.text(x, y - 0.8, sub_text, ha="center", va="center", fontsize=7,
#                         color=COLOR_MUTED, zorder=5, alpha=0.9)
#             else:
#                 ax.text(x, y, f"{country_name}\nнет данных", ha="center", va="center",
#                         fontsize=8.5, color=COLOR_MUTED, zorder=5, alpha=0.7)
    
#     # Настройки карты
#     ax.set_xlim(20, 180)
#     ax.set_ylim(40, 76)
#     ax.set_title(f"География остатков товаров\nна {report_date}",
#                  fontsize=17, fontweight="bold", color=COLOR_TEXT, pad=18)
    
#     # Легенда
#     legend_text = ""
#     if not unmapped_stats.empty:
#         unmapped_total = float(unmapped_stats["итого"].sum())
#         legend_text += f"\n\n Не распределено: {format_number(unmapped_total)}"
    
#     ax.text(0.02, 0.02, legend_text, transform=ax.transAxes, ha="left", va="bottom",
#             fontsize=8, color=COLOR_MUTED,
#             bbox=dict(boxstyle="round,pad=0.3", facecolor="#FAFAF8",
#                      edgecolor="#B6C4BD", linewidth=0.5, alpha=0.88))
    
#     ax.set_xticks([])
#     ax.set_yticks([])
#     ax.grid(False)
#     for spine in ax.spines.values():
#         spine.set_visible(False)
    
#     plt.tight_layout(pad=0.4)
    
#     buffer = io.BytesIO()
#     fig.savefig(buffer, format="png", dpi=180, bbox_inches="tight", facecolor=COLOR_BG)
#     plt.close(fig)
#     buffer.seek(0)
    
#     return buffer


# build_regions_stock_map_png = build_russia_regions_map




# inventories/reporting/map/russia_regions_map.py
from __future__ import annotations

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
    """
    Ручные позиции подписей, чтобы мелкие страны не накладывались друг на друга.
    """
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


def build_russia_regions_map(region_stats: pd.DataFrame, report_date: str) -> io.BytesIO:
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

        # Внешняя обводка окрашенных регионов
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

    ax.set_title(
        f"География остатков товаров\nна {report_date}",
        fontsize=18,
        fontweight="bold",
        color=COLOR_TEXT,
        pad=18,
        linespacing=1.05,
    )

    # Важно: обрезаем лишний низ и делаем карту крупнее.
    # Раньше ylim начинался с 40, из-за этого Таджикистан был почти на границе,
    # а ниже оставалось пустое поле. Теперь диапазон аккуратнее.
    ax.set_xlim(20, 178)
    ax.set_ylim(37.2, 75.8)

    # Блок "не распределено" показываем только если есть сумма
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

    plt.subplots_adjust(left=0.015, right=0.965, top=0.88, bottom=0.035)

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