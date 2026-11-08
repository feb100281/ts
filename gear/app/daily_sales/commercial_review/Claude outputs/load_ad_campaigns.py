from __future__ import annotations

import json
import os
import time
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv


load_dotenv()


# ============================================================
# НАСТРОЙКИ
#
# Тот же токен, что и у остального парсинга (WB_SUPER_TOKEN) --
# но у него должен быть включён доступ к категории "Продвижение"
# в личном кабинете WB (Настройки -> Доступ к API). Если доступа
# нет, запросы ниже упадут с HTTP 401/403.
#
# Хост рекламного API -- ОТДЕЛЬНЫЙ от marketplace-api, которым
# пользуется load_fbs_orders.py: advert-api, а не marketplace-api.
#
# Пути ниже сверены 23.09.2026 по актуальному Swagger WB
# (https://dev.wildberries.ru/en/swagger/promotion) -- Даша
# прислала скриншоты, т.к. сам этот домен недоступен из моей
# песочницы. WB успел один раз переехать на новые пути уже после
# того, как я написал первую версию скрипта (adverts: было
# POST /adv/v1/promotion/adverts -> стало GET /api/advert/v2/adverts;
# fullstats: было POST /adv/v2/fullstats -> стало GET /adv/v3/fullstats).
# Если WB переедет ещё раз -- проверяй здесь в первую очередь.
# ============================================================

token = os.getenv("WB_SUPER_TOKEN")
parquet_path = os.getenv("PARQUET_PATH")

BASE_URL = "https://advert-api.wildberries.ru"

COUNT_URL = (
    f"{BASE_URL}"
    f"/adv/v1/promotion/count"
)

ADVERTS_URL = (
    f"{BASE_URL}"
    f"/api/advert/v2/adverts"
)

FULLSTATS_URL = (
    f"{BASE_URL}"
    f"/adv/v3/fullstats"
)

BALANCE_URL = (
    f"{BASE_URL}"
    f"/adv/v1/balance"
)


# ------------------------------------------------------------
# СКОЛЬКО ДНЕЙ НАЗАД ТЯНЕМ СТАТИСТИКУ
#
# Не только "вчера": у WB статистика по рекламе может донабираться
# и уточняться ещё день-два после самого дня показов (как и с
# расходами в sales.sales_long). Поэтому каждый день перезапрашиваем
# скользящее окно назад, а не только последний день -- поздние
# уточнения сами перезапишут более раннюю (менее точную) версию того
# же дня при сборке в DuckDB (тот же приём, что и с fbs-заказами --
# берём самый свежий снимок на дату).
#
# У /adv/v3/fullstats максимум 31 день в одном запросе -- если
# захочешь когда-нибудь увеличить окно больше 31 дня, придётся
# разбивать на несколько запросов по датам, не только по кампаниям.
# ------------------------------------------------------------

STATS_WINDOW_DAYS = 30


# ------------------------------------------------------------
# СКОЛЬКО КАМПАНИЙ ЗА ОДИН ЗАПРОС
#
# У обоих методов (adverts и fullstats) лимит -- максимум 50 ID
# за запрос, это в Swagger написано явно, беру по максимуму.
#
# У /adv/v3/fullstats жёсткий лимит на скорость -- фактически не
# чаще 1 запроса в 20 секунд на большинстве типов токенов (в
# Swagger: "3 requests / 1 min, интервал между burst -- 20s").
# Если токен окажется более редкого типа "Base" -- там лимит вообще
# 1 запрос в час, тогда весь прогон растянется на много часов; если
# увидишь в консоли много "HTTP 429" подряд даже после ожидания --
# напиши, будем считать кампании реже, а не каждый день.
# ------------------------------------------------------------

ADVERTS_BATCH_SIZE = 50
FULLSTATS_BATCH_SIZE = 50
FULLSTATS_SLEEP_SECONDS = 20

# /adv/v3/fullstats считает статистику только для кампаний в этих
# статусах (написано прямо в Swagger) -- остальные (черновик,
# отклонена, удаляется) смысла запрашивать нет, будет либо пусто,
# либо ошибка.
STATS_ELIGIBLE_STATUSES = {7, 9, 11}

# ------------------------------------------------------------
# КАКИЕ КАМПАНИИ ТЯНЕМ КАЖДЫЙ ДЕНЬ
#
# У Даши на 3 064 кампании реально "живых" (которые вообще могут
# измениться -- статус, бюджет, показы) всего ~48: Активна (9) +
# На паузе (11). Остальные ~3 016 -- Завершена (7), в основном
# старые одноразовые аукционные ставки; их данные по определению
# больше не меняются, а тянуть детали+статистику по каждой из них
# заново КАЖДЫЙ день -- это и есть та самая "супер долгая" работа
# скрипта (десятки минут из-за жёсткого рейт-лимита WB на
# /adv/v3/fullstats, не чаще ~1 запроса в 20 секунд).
#
# Поэтому по умолчанию завершённые кампании в ежедневный прогон НЕ
# попадают -- их незачем перезапрашивать. Чтобы один раз (или
# изредка) сделать полную историческую выгрузку по вообще всем
# кампаниям, включая завершённые, запусти:
#
#   AD_CAMPAIGNS_INCLUDE_COMPLETED=1 python utils/load_ad_campaigns.py
#
# Такой прогон будет медленным (десятки минут) -- это ожидаемо и
# нормально, зато его достаточно сделать один раз (плюс изредка
# повторять, если появятся новые завершённые кампании, по которым
# ещё нет ни одного снимка).
# ------------------------------------------------------------

LIVE_STATUSES = {9, 11}

INCLUDE_COMPLETED_CAMPAIGNS = (
    os.getenv(
        "AD_CAMPAIGNS_INCLUDE_COMPLETED",
        "0",
    )
    == "1"
)


# ------------------------------------------------------------
# СПРАВОЧНИКИ ТИПОВ/СТАТУСОВ КАМПАНИЙ
#
# Статусы -- сверены Дашей по официальному Swagger 23.09.2026,
# ими же промаркирован /api/advert/v2/adverts, так что эти коды
# точно актуальны (не только "устоявшиеся", как я предполагал
# раньше).
#
# Типы (4-9) -- пока НЕ из свежей документации, а из моих старых
# знаний, но их подтвердил реальный первый запуск: /adv/v1/promotion/count
# на 3 064 боевых кампаниях Даши вернул только коды 5, 6, 7, 9 --
# и все они корректно разложились по этому словарю (заглушка "—" ни
# разу не сработала). Так что этот справочник можно считать
# практически подтверждённым.
# ------------------------------------------------------------

ADVERT_TYPE_NAMES = {
    4: "В каталоге",
    5: "В карточке товара",
    6: "В поиске",
    7: "На главной странице",
    8: "Автоматическая кампания",
    9: "Аукцион",
}

ADVERT_STATUS_NAMES = {
    -1: "Идёт проверка",
    4: "Готова к запуску",
    7: "Завершена",
    8: "Отклонена",
    9: "Активна",
    11: "На паузе",
}

# appType в /adv/v3/fullstats (days[].apps[].appType) -- в реальном
# ответе встречаются коды 1, 32, 64, но их точное значение (поиск /
# карточка товара / рекомендации и т.п.) я нигде не смог свежо
# подтвердить -- ни в официальной документации (недоступна из моей
# песочницы), ни в открытых источниках. Поэтому пока не расшифровываю,
# храню сырой код как есть в колонке app_type -- если WB
# когда-нибудь подтвердит расшифровку (или мы угадаем её по
# косвенным признакам в данных), легко добавить словарь по аналогии
# с ADVERT_TYPE_NAMES.
APP_TYPE_NAMES: dict[int, str] = {}


if not token:
    raise RuntimeError(
        "WB_SUPER_TOKEN is not set"
    )


if not parquet_path:
    raise RuntimeError(
        "PARQUET_PATH is not set"
    )


headers = {
    "Authorization": token,
    "Content-Type": "application/json",
}


# ============================================================
# ПАПКА
# ============================================================

output_dir = (
    Path(parquet_path)
    / "ad_campaigns"
)

output_dir.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# ВСПОМОГАТЕЛЬНЫЕ ФУНКЦИИ
# ============================================================

def dig(d, *keys, default=None):
    """Безопасно достаём вложенное значение из словаря: dig(x, "a", "b")
    эквивалентно x.get("a", {}).get("b"), но не падает, если "a"
    отсутствует, равно None или вообще не словарь."""

    current = d

    for key in keys:

        if not isinstance(current, dict):
            return default

        current = current.get(key)

    return (
        current
        if current is not None
        else default
    )


def wb_get(
    url: str,
    params: dict | None = None,
    allow_rate_limit_retry: bool = False,
) -> dict | list:

    try:

        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=60,
        )

    except requests.RequestException as e:

        raise RuntimeError(
            f"Ошибка запроса WB API: {e}"
        )


    if (
        response.status_code == 429
        and allow_rate_limit_retry
    ):

        print(
            "HTTP 429 (слишком много запросов) -- "
            "ждём 60 секунд и пробуем ещё раз"
        )

        time.sleep(
            60
        )

        response = requests.get(
            url,
            headers=headers,
            params=params,
            timeout=60,
        )


    if response.status_code != 200:

        print()
        print(
            f"GET {url}"
        )

        print(
            f"params: {params}"
        )

        print(
            f"HTTP: {response.status_code}"
        )

        print(
            response.text
        )

        raise RuntimeError(
            "WB API GET error"
        )


    return response.json()


def chunked(items, size):

    for start in range(
        0,
        len(items),
        size,
    ):

        yield items[
            start:
            start + size
        ]


# ============================================================
# 1. СПИСОК ВСЕХ КАМПАНИЙ (ID + ТИП + СТАТУС)
#
# /adv/v1/promotion/count отдаёт кампании, сгруппированные по
# (type, status) -- в т.ч. завершённые/отклонённые, не только
# активные: историю рекламы хотим видеть всю, как и с заказами.
# ============================================================

print()
print(
    "=" * 70
)

print(
    "1. Получаем список рекламных кампаний"
)

print(
    "=" * 70
)


count_data = wb_get(
    COUNT_URL
)


advert_groups = count_data.get(
    "adverts",
    [],
)


campaign_type_status = {}


for group in advert_groups:

    group_type = group.get(
        "type"
    )

    group_status = group.get(
        "status"
    )

    for item in group.get(
        "advert_list",
        [],
    ):

        advert_id = item.get(
            "advertId"
        )

        if advert_id is None:
            continue

        campaign_type_status[
            int(advert_id)
        ] = {
            "type": group_type,
            "status": group_status,
        }


all_advert_ids = list(
    campaign_type_status.keys()
)

target_statuses = set(
    LIVE_STATUSES
)

if INCLUDE_COMPLETED_CAMPAIGNS:

    target_statuses |= STATS_ELIGIBLE_STATUSES


# кампании, для которых сегодня тянем детали + статистику --
# по умолчанию только "живые" (активна/на паузе), см. пояснение
# выше про INCLUDE_COMPLETED_CAMPAIGNS.
target_advert_ids = [
    advert_id
    for advert_id, info in campaign_type_status.items()
    if info["status"] in target_statuses
]

# из target_advert_ids дополнительно исключаем статусы, для которых
# WB вообще не считает статистику (сейчас target_statuses и так
# подмножество STATS_ELIGIBLE_STATUSES, но проверяем явно на случай
# будущих изменений).
stats_eligible_ids = [
    advert_id
    for advert_id in target_advert_ids
    if campaign_type_status[advert_id]["status"] in STATS_ELIGIBLE_STATUSES
]


print(
    f"Всего кампаний: "
    f"{len(all_advert_ids):,} "
    f"(по данным {count_data.get('all', '?')})"
)

print(
    f"Обрабатываем сегодня (статусы {sorted(target_statuses)}"
    f"{', включая завершённые' if INCLUDE_COMPLETED_CAMPAIGNS else ''}): "
    f"{len(target_advert_ids):,}"
)

if not INCLUDE_COMPLETED_CAMPAIGNS:

    skipped = len(all_advert_ids) - len(target_advert_ids)

    print(
        f"Пропускаем завершённые кампании (их данные больше не "
        f"меняются): {skipped:,}. Чтобы один раз выгрузить и их "
        f"тоже -- запусти с AD_CAMPAIGNS_INCLUDE_COMPLETED=1."
    )


for group in advert_groups:

    type_name = ADVERT_TYPE_NAMES.get(
        group.get("type"),
        "—",
    )

    status_name = ADVERT_STATUS_NAMES.get(
        group.get("status"),
        "—",
    )

    print(
        f"  тип {group.get('type')} ({type_name}) / "
        f"статус {group.get('status')} ({status_name}) "
        f"-- {group.get('count', 0):,}"
    )


# ============================================================
# 2. ДЕТАЛИ КАЖДОЙ КАМПАНИИ (НАЗВАНИЕ, СПОСОБ ОПЛАТЫ, РАЗМЕЩЕНИЕ,
#    ДАТЫ, ТОВАРЫ В КАМПАНИИ)
#
# GET /api/advert/v2/adverts принимает пачку ID через query-параметр
# ids (через запятую) и отдаёт по ним подробности. Батчами по
# ADVERTS_BATCH_SIZE (максимум 50 за раз по документации).
# ============================================================

print()
print(
    "=" * 70
)

print(
    "2. Получаем детали кампаний"
)

print(
    "=" * 70
)


campaign_details = []


if target_advert_ids:

    for number, batch in enumerate(
        chunked(
            target_advert_ids,
            ADVERTS_BATCH_SIZE,
        ),
        start=1,
    ):

        response_data = wb_get(
            ADVERTS_URL,
            params={
                "ids": ",".join(
                    str(advert_id)
                    for advert_id in batch
                ),
            },
            allow_rate_limit_retry=True,
        )

        batch_details = (
            response_data.get(
                "adverts",
                [],
            )
            if isinstance(response_data, dict)
            else []
        )


        campaign_details.extend(
            batch_details
        )


        print(
            f"Пачка {number} "
            f"-- кампаний: {len(batch)} "
            f"-- получено деталей: "
            f"{len(batch_details)}"
        )


        time.sleep(
            0.3
        )


else:

    print(
        "Кампаний нет -- пропускаем."
    )


print()
print(
    f"Деталей получено: "
    f"{len(campaign_details):,}"
)


# ============================================================
# 3. СТАТИСТИКА ПО ДНЯМ (fullstats)
#
# По каждой кампании (в подходящем статусе) -- окно
# STATS_WINDOW_DAYS дней назад от сегодня. GET-запрос с
# query-параметрами ids/beginDate/endDate, батчами по
# FULLSTATS_BATCH_SIZE с паузой между ними -- это самая
# "тяжёлая" и медленная ручка рекламного API.
#
# Ответ -- по каждой кампании: набор дней (days[]), а в каждом дне --
# разбивка по площадке размещения (apps[], поле appType) и внутри
# неё -- по конкретному товару (nms[], поле nmId). Это позволяет
# увидеть расход/заказы не только по кампании в целом, но и по
# конкретной карточке товара внутри кампании -- разложил это в
# отдельную таблицу stats_by_nm ниже, ей ещё нет аналога в старых
# отчётах, но именно она свяжет рекламу с конкретными карточками.
# ============================================================

print()
print(
    "=" * 70
)

print(
    "3. Получаем статистику показов/кликов/расходов"
)

print(
    "=" * 70
)


today = pd.Timestamp.now(
    tz="UTC"
).date()

window_start = (
    today
    - pd.Timedelta(
        days=STATS_WINDOW_DAYS
    )
)


stats_rows = []
stats_by_nm_rows = []

loaded_at = pd.Timestamp.now(
    tz="UTC"
)


if stats_eligible_ids:

    for number, batch in enumerate(
        chunked(
            stats_eligible_ids,
            FULLSTATS_BATCH_SIZE,
        ),
        start=1,
    ):

        params = {
            "ids": ",".join(
                str(advert_id)
                for advert_id in batch
            ),
            "beginDate": str(
                window_start
            ),
            "endDate": str(
                today
            ),
        }


        try:

            batch_stats = wb_get(
                FULLSTATS_URL,
                params=params,
                allow_rate_limit_retry=True,
            )

        except RuntimeError as e:

            print(
                f"Пачка {number} "
                f"({len(batch)} кампаний) "
                f"-- ошибка, пропускаем: {e}"
            )

            time.sleep(
                FULLSTATS_SLEEP_SECONDS
            )

            continue


        if not isinstance(
            batch_stats,
            list,
        ):

            batch_stats = []


        for campaign_stat in batch_stats:

            advert_id = campaign_stat.get(
                "advertId"
            )

            currency = campaign_stat.get(
                "currency"
            )

            for day in campaign_stat.get(
                "days",
                [],
            ):

                stats_rows.append({

                    "advert_id":
                        advert_id,

                    "date":
                        day.get("date"),

                    "views":
                        day.get("views"),

                    "clicks":
                        day.get("clicks"),

                    "ctr":
                        day.get("ctr"),

                    "cpc":
                        day.get("cpc"),

                    "sum":
                        day.get("sum"),

                    "atbs":
                        day.get("atbs"),

                    "orders":
                        day.get("orders"),

                    "cr":
                        day.get("cr"),

                    "shks":
                        day.get("shks"),

                    "sum_price":
                        day.get("sum_price"),

                    "canceled":
                        day.get("canceled"),

                    "currency":
                        currency,

                    "loaded_at":
                        loaded_at,

                    # сырой день целиком (в т.ч. разбивка apps/nms) --
                    # ничего не теряем, даже то, что мы здесь не
                    # разложили по колонкам.
                    "payload":
                        json.dumps(
                            day,
                            ensure_ascii=False,
                        ),
                })


                for app in (
                    day.get("apps", [])
                    or []
                ):

                    app_type = app.get(
                        "appType"
                    )

                    for nm in (
                        app.get("nms", [])
                        or []
                    ):

                        stats_by_nm_rows.append({

                            "advert_id":
                                advert_id,

                            "date":
                                day.get("date"),

                            "app_type":
                                app_type,

                            "app_type_name":
                                APP_TYPE_NAMES.get(
                                    app_type,
                                    "—",
                                ),

                            "nm_id":
                                nm.get("nmId"),

                            "title":
                                nm.get("name"),

                            "views":
                                nm.get("views"),

                            "clicks":
                                nm.get("clicks"),

                            "ctr":
                                nm.get("ctr"),

                            "cpc":
                                nm.get("cpc"),

                            "sum":
                                nm.get("sum"),

                            "atbs":
                                nm.get("atbs"),

                            "orders":
                                nm.get("orders"),

                            "cr":
                                nm.get("cr"),

                            "shks":
                                nm.get("shks"),

                            "sum_price":
                                nm.get("sum_price"),

                            "canceled":
                                nm.get("canceled"),

                            "loaded_at":
                                loaded_at,
                        })


        print(
            f"Пачка {number} "
            f"-- кампаний: {len(batch)} "
            f"-- дней статистики получено: "
            f"{sum(len(c.get('days', [])) for c in batch_stats):,}"
        )


        time.sleep(
            FULLSTATS_SLEEP_SECONDS
        )


else:

    print(
        "Нет кампаний в статусах, подходящих для статистики -- "
        "пропускаем."
    )


print()
print(
    f"Строк статистики (кампания x день): "
    f"{len(stats_rows):,}"
)

print(
    f"Строк статистики по товарам (кампания x день x товар): "
    f"{len(stats_by_nm_rows):,}"
)


# ============================================================
# 4. СОБИРАЕМ ТАБЛИЦУ КАМПАНИЙ (+ ТОВАРЫ ВНУТРИ КАМПАНИЙ)
# ============================================================

campaign_rows = []
nm_settings_rows = []


for detail in campaign_details:

    advert_id = detail.get(
        "id"
    )

    known = campaign_type_status.get(
        int(advert_id)
        if advert_id is not None
        else None,
        {},
    )

    campaign_type = known.get(
        "type"
    )

    campaign_status = (
        detail.get("status")
        if detail.get("status") is not None
        else known.get("status")
    )

    campaign_rows.append({

        "advert_id":
            advert_id,

        "name":
            dig(detail, "settings", "name"),

        "type":
            campaign_type,

        "type_name":
            ADVERT_TYPE_NAMES.get(
                campaign_type,
                "—",
            ),

        "status":
            campaign_status,

        "status_name":
            ADVERT_STATUS_NAMES.get(
                campaign_status,
                "—",
            ),

        "payment_type":
            dig(detail, "settings", "payment_type"),

        "placement_search":
            dig(detail, "settings", "placements", "search"),

        "placement_recommendations":
            dig(detail, "settings", "placements", "recommendations"),

        "bid_type":
            detail.get("bid_type"),

        "currency":
            detail.get("currency"),

        "can_change_nms":
            dig(detail, "restrictions", "can_change_nms"),

        "create_time":
            dig(detail, "timestamps", "created"),

        "start_time":
            dig(detail, "timestamps", "started"),

        "change_time":
            dig(detail, "timestamps", "updated"),

        # у WB "не удалена" кодируется далёкой датой-заглушкой
        # (2100-01-01) -- разбираемся с этим ниже, после сборки
        # DataFrame.
        "end_time":
            dig(detail, "timestamps", "deleted"),

        "_loaded_at":
            loaded_at,

        # сырая карточка кампании целиком -- ничего не теряем, даже
        # то, что мы здесь не разложили по колонкам (например,
        # boosterStats из fullstats сюда не относится, но любые
        # будущие новые поля adverts -- останутся здесь).
        "payload":
            json.dumps(
                detail,
                ensure_ascii=False,
            ),
    })


    for nm in (
        detail.get("nm_settings", [])
        or []
    ):

        nm_settings_rows.append({

            "advert_id":
                advert_id,

            "nm_id":
                nm.get("nm_id"),

            "subject_id":
                dig(nm, "subject", "id"),

            "subject_name":
                dig(nm, "subject", "name"),

            "bid_search_kopecks":
                dig(nm, "bids_kopecks", "search"),

            "bid_recommendations_kopecks":
                dig(nm, "bids_kopecks", "recommendations"),

            "_loaded_at":
                loaded_at,
        })


campaigns_df = pd.DataFrame(
    campaign_rows
)

stats_df = pd.DataFrame(
    stats_rows
)

stats_by_nm_df = pd.DataFrame(
    stats_by_nm_rows
)

nm_settings_df = pd.DataFrame(
    nm_settings_rows
)


print()
print(
    f"Строк в таблице кампаний: "
    f"{len(campaigns_df):,}"
)

print(
    f"Строк в таблице статистики: "
    f"{len(stats_df):,}"
)

print(
    f"Строк в таблице статистики по товарам: "
    f"{len(stats_by_nm_df):,}"
)

print(
    f"Строк в таблице товаров внутри кампаний: "
    f"{len(nm_settings_df):,}"
)


# ============================================================
# ТИПЫ ДАТ / ЧИСЕЛ / БУЛЕВЫХ
# ============================================================

for column in (
    "create_time",
    "change_time",
    "start_time",
    "end_time",
):

    if column in campaigns_df.columns:

        campaigns_df[column] = pd.to_datetime(
            campaigns_df[column],
            utc=True,
            errors="coerce",
        )


if (
    "end_time" in campaigns_df.columns
    and not campaigns_df.empty
):

    # заглушка WB для "кампания не удалена" -- дата 2100-01-01 в
    # часовом поясе МСК (+03:00); после перевода в UTC это уже
    # 2099-12-31 21:00, поэтому сравниваем с запасом (2050), а не
    # ровно с 2100 -- ни одна настоящая дата удаления кампании
    # реалистично не окажется в этом диапазоне.
    far_future = (
        campaigns_df["end_time"].dt.year >= 2050
    )

    campaigns_df.loc[
        far_future,
        "end_time",
    ] = pd.NaT


if "advert_id" in campaigns_df.columns:

    campaigns_df["advert_id"] = pd.to_numeric(
        campaigns_df["advert_id"],
        errors="coerce",
    ).astype(
        "Int64"
    )


for column in (
    "placement_search",
    "placement_recommendations",
    "can_change_nms",
):

    if column in campaigns_df.columns:

        campaigns_df[column] = campaigns_df[column].astype(
            "boolean"
        )


if not stats_df.empty:

    stats_df["date"] = pd.to_datetime(
        stats_df["date"],
        errors="coerce",
    ).dt.date

    stats_df["advert_id"] = pd.to_numeric(
        stats_df["advert_id"],
        errors="coerce",
    ).astype(
        "Int64"
    )

    for column in (
        "views",
        "clicks",
        "ctr",
        "cpc",
        "sum",
        "atbs",
        "orders",
        "cr",
        "shks",
        "sum_price",
        "canceled",
    ):

        stats_df[column] = pd.to_numeric(
            stats_df[column],
            errors="coerce",
        )


if not stats_by_nm_df.empty:

    stats_by_nm_df["date"] = pd.to_datetime(
        stats_by_nm_df["date"],
        errors="coerce",
    ).dt.date

    stats_by_nm_df["advert_id"] = pd.to_numeric(
        stats_by_nm_df["advert_id"],
        errors="coerce",
    ).astype(
        "Int64"
    )

    stats_by_nm_df["nm_id"] = pd.to_numeric(
        stats_by_nm_df["nm_id"],
        errors="coerce",
    ).astype(
        "Int64"
    )

    for column in (
        "views",
        "clicks",
        "ctr",
        "cpc",
        "sum",
        "atbs",
        "orders",
        "cr",
        "shks",
        "sum_price",
        "canceled",
    ):

        stats_by_nm_df[column] = pd.to_numeric(
            stats_by_nm_df[column],
            errors="coerce",
        )


if not nm_settings_df.empty:

    nm_settings_df["advert_id"] = pd.to_numeric(
        nm_settings_df["advert_id"],
        errors="coerce",
    ).astype(
        "Int64"
    )

    nm_settings_df["nm_id"] = pd.to_numeric(
        nm_settings_df["nm_id"],
        errors="coerce",
    ).astype(
        "Int64"
    )


# ============================================================
# 5. СОХРАНЯЕМ PARQUET
#
# Один файл на дату -- та же схема, что и у fbs_orders/fbs_supplies:
# повторный запуск в тот же день перезаписывает файл этого дня,
# а окно в 30 дней в fullstats выше сам исправит более ранние дни,
# если WB их ещё раз пересчитал.
# ============================================================

file_date = loaded_at.strftime(
    "%Y-%m-%d"
)


campaigns_file = (
    output_dir
    / f"ad_campaigns_info_{file_date}.parquet"
)

stats_file = (
    output_dir
    / f"ad_campaigns_stats_{file_date}.parquet"
)

stats_by_nm_file = (
    output_dir
    / f"ad_campaigns_stats_by_nm_{file_date}.parquet"
)

nm_settings_file = (
    output_dir
    / f"ad_campaigns_nm_settings_{file_date}.parquet"
)


campaigns_df.to_parquet(
    campaigns_file,
    index=False,
)

stats_df.to_parquet(
    stats_file,
    index=False,
)

stats_by_nm_df.to_parquet(
    stats_by_nm_file,
    index=False,
)

nm_settings_df.to_parquet(
    nm_settings_file,
    index=False,
)


# ============================================================
# 6. БАЛАНС РЕКЛАМНОГО КАБИНЕТА
#
# Маленький бонус-блок в конце и в try/except -- как справочники
# складов в load_fbs_orders.py: если ручка недоступна токену,
# кампании и статистика к этому моменту уже сохранены на диск.
# ============================================================

print()
print(
    "=" * 70
)

print(
    "6. Баланс рекламного кабинета"
)

print(
    "=" * 70
)


balance_file = (
    output_dir
    / "ad_campaigns_balance.parquet"
)

balance_df = pd.DataFrame()


try:

    balance_data = wb_get(
        BALANCE_URL
    )

    # печатаем сырой ответ целиком -- баланс один раз уже показал
    # 0/None там, где по документации ожидались ненулевые числа,
    # так что здесь лучше не гадать по паре распечатанных полей, а
    # видеть весь ответ WB как есть.
    print(
        f"Сырой ответ WB: {balance_data}"
    )

    if isinstance(
        balance_data,
        dict,
    ):

        cashbacks = (
            balance_data.get("cashbacks")
            or []
        )

        cashbacks_total = sum(
            (c.get("sum") or 0)
            for c in cashbacks
        )

        balance_df = pd.DataFrame([{
            "balance":
                balance_data.get("balance"),

            "net":
                balance_data.get("net"),

            "bonus":
                balance_data.get("bonus"),

            "currency":
                balance_data.get("currency"),

            "cashbacks_total":
                cashbacks_total,

            "payload":
                json.dumps(
                    balance_data,
                    ensure_ascii=False,
                ),

            "loaded_at":
                loaded_at,
        }])

        balance_df.to_parquet(
            balance_file,
            index=False,
        )

        print(
            f"Чистый доступный бюджет (net): "
            f"{balance_data.get('net')} "
            f"{balance_data.get('currency', '')}"
        )

        print(
            f"Баланс (balance, отдельно от net): "
            f"{balance_data.get('balance')} "
            f"{balance_data.get('currency', '')} "
            f"(бонусы: "
            f"{balance_data.get('bonus')}, "
            f"сгорающий кэшбэк: "
            f"{cashbacks_total})"
        )

    else:

        print(
            "Неожиданный формат ответа -- пропускаем."
        )


except Exception as e:

    print()
    print(
        f"Баланс не загрузился: {e}"
    )

    print(
        "Кампании и статистика это не затрагивает -- "
        "они уже сохранены выше."
    )


# ============================================================
# 7. ИТОГ
# ============================================================

print()
print(
    "=" * 70
)

print(
    "AD CAMPAIGNS LOADED"
)

print(
    "-" * 70
)

print(
    f"Кампаний: "
    f"{len(campaigns_df):,}"
)

print(
    f"Строк статистики: "
    f"{len(stats_df):,}"
)

print(
    f"Строк статистики по товарам: "
    f"{len(stats_by_nm_df):,}"
)

print(
    f"Окно статистики: "
    f"{window_start} .. {today} "
    f"({STATS_WINDOW_DAYS} дн.)"
)

print()

print(
    "Campaigns:"
)

print(
    campaigns_file
)

print()

print(
    "Stats:"
)

print(
    stats_file
)

print()

print(
    "Stats by nm:"
)

print(
    stats_by_nm_file
)

print()

print(
    f"Loaded at: "
    f"{loaded_at}"
)

print(
    "=" * 70
)


# ============================================================
# 8. КРАТКИЙ ПРОСМОТР
# ============================================================

if not campaigns_df.empty:

    preview_columns = [
        column
        for column in [
            "advert_id",
            "name",
            "type_name",
            "status_name",
            "payment_type",
            "placement_search",
            "placement_recommendations",
            "start_time",
        ]
        if column in campaigns_df.columns
    ]

    print()
    print(
        "Кампании:"
    )

    print(
        campaigns_df[
            preview_columns
        ]
        .head(30)
        .to_string(
            index=False
        )
    )


if not stats_df.empty:

    latest_date = stats_df["date"].max()

    preview = (
        stats_df[
            stats_df["date"] == latest_date
        ]
        .sort_values(
            "sum",
            ascending=False,
        )
        .head(15)
    )

    print()
    print(
        f"Статистика за {latest_date} "
        f"(топ-15 по расходу):"
    )

    print(
        preview[
            [
                "advert_id", "views", "clicks",
                "ctr", "cpc", "sum", "orders", "cr",
            ]
        ]
        .to_string(
            index=False
        )
    )


if not stats_by_nm_df.empty:

    latest_date_nm = stats_by_nm_df["date"].max()

    preview_nm = (
        stats_by_nm_df[
            stats_by_nm_df["date"] == latest_date_nm
        ]
        .sort_values(
            "sum",
            ascending=False,
        )
        .head(15)
    )

    print()
    print(
        f"Статистика по товарам за {latest_date_nm} "
        f"(топ-15 по расходу):"
    )

    print(
        preview_nm[
            [
                "advert_id", "nm_id", "title",
                "views", "clicks", "sum", "orders",
            ]
        ]
        .to_string(
            index=False
        )
    )
