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
# ============================================================

token = os.getenv("WB_SUPER_TOKEN")
parquet_path = os.getenv("PARQUET_PATH")

BASE_URL = "https://marketplace-api.wildberries.ru"

ORDERS_URL = (
    f"{BASE_URL}"
    f"/api/v3/orders"
)

ORDERS_STATUS_URL = (
    f"{BASE_URL}"
    f"/api/v3/orders/status"
)

SUPPLIES_URL = (
    f"{BASE_URL}"
    f"/api/v3/supplies"
)


# ------------------------------------------------------------
# СПРАВОЧНИКИ СКЛАДОВ
#
# В заказах лежат только warehouse_id (наш склад отправления)
# и destination_office_id (склад WB, куда едет поставка) —
# голые числа. Названия отдают две отдельные ручки.
# ------------------------------------------------------------

WAREHOUSES_URL = (
    f"{BASE_URL}"
    f"/api/v3/warehouses"
)

OFFICES_URL = (
    f"{BASE_URL}"
    f"/api/v3/offices"
)


CARGO_TYPE_NAMES = {
    1: "Обычный",
    2: "СГТ (сверхгабарит)",
    3: "КГТ (крупногабарит)",
}


DELIVERY_TYPE_NAMES = {
    1: "На склад WB",
    2: "Силами продавца",
    3: "Курьером WB",
}


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
    / "fbs_orders"
)

output_dir.mkdir(
    parents=True,
    exist_ok=True,
)


# ============================================================
# ОБЩАЯ ФУНКЦИЯ GET
# ============================================================

def wb_get(
    url: str,
    params: dict | None = None,
) -> dict:

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


    if response.status_code != 200:

        print()
        print(
            f"GET {url}"
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


# ============================================================
# ОБЩАЯ ФУНКЦИЯ POST
# ============================================================

def wb_post(
    url: str,
    payload: dict,
) -> dict:

    try:

        response = requests.post(
            url,
            headers=headers,
            json=payload,
            timeout=60,
        )

    except requests.RequestException as e:

        raise RuntimeError(
            f"Ошибка запроса WB API: {e}"
        )


    if response.status_code != 200:

        print()
        print(
            f"POST {url}"
        )

        print(
            f"HTTP: {response.status_code}"
        )

        print(
            response.text
        )

        raise RuntimeError(
            "WB API POST error"
        )


    return response.json()


# ============================================================
# 1. ПОЛУЧАЕМ ВСЕ ДОСТУПНЫЕ FBS-ЗАКАЗЫ
# ============================================================

print()
print(
    "=" * 70
)

print(
    "1. Получаем FBS-заказы"
)

print(
    "=" * 70
)


all_orders = []

next_value = 0


while True:

    orders_data = wb_get(
        ORDERS_URL,
        params={
            "next": next_value,
            "limit": 1000,
        },
    )


    orders = orders_data.get(
        "orders",
        [],
    )


    all_orders.extend(
        orders
    )


    new_next = orders_data.get(
        "next"
    )


    print(
        f"Получено заказов: "
        f"{len(orders):,} "
        f"| всего: "
        f"{len(all_orders):,} "
        f"| next: "
        f"{new_next}"
    )


    if not orders:
        break


    if not new_next:
        break


    if new_next == next_value:
        break


    next_value = new_next


    time.sleep(
        0.2
    )


print()
print(
    f"Всего FBS-заказов: "
    f"{len(all_orders):,}"
)


# ============================================================
# 2. ПОЛУЧАЕМ СТАТУСЫ ЗАКАЗОВ
#
# Отправляем ID батчами.
# ============================================================

statuses = []


if all_orders:

    order_ids = [
        order["id"]
        for order in all_orders
        if order.get("id") is not None
    ]


    print()
    print(
        "=" * 70
    )

    print(
        "2. Получаем статусы заказов"
    )

    print(
        "=" * 70
    )


    STATUS_BATCH_SIZE = 1000


    for start in range(
        0,
        len(order_ids),
        STATUS_BATCH_SIZE,
    ):

        batch = order_ids[
            start:
            start + STATUS_BATCH_SIZE
        ]


        status_data = wb_post(
            ORDERS_STATUS_URL,
            {
                "orders": batch
            },
        )


        batch_statuses = (
            status_data.get(
                "orders",
                [],
            )
        )


        statuses.extend(
            batch_statuses
        )


        print(
            f"Статусы: "
            f"{min(start + len(batch), len(order_ids)):,}/"
            f"{len(order_ids):,}"
        )


        time.sleep(
            0.2
        )


    print()
    print(
        f"Получено статусов: "
        f"{len(statuses):,}"
    )


else:

    print()
    print(
        "FBS-заказов нет."
    )


# ============================================================
# СЛОВАРЬ СТАТУСОВ
# ============================================================

status_by_order_id = {
    row.get("id"): row
    for row in statuses
    if row.get("id") is not None
}


# ============================================================
# 3. ПОЛУЧАЕМ ВСЕ ПОСТАВКИ FBS
# ============================================================

print()
print(
    "=" * 70
)

print(
    "3. Получаем FBS-поставки"
)

print(
    "=" * 70
)


all_supplies = []

next_value = 0


while True:

    supply_data = wb_get(
        SUPPLIES_URL,
        params={
            "next": next_value,
            "limit": 1000,
        },
    )


    supplies = supply_data.get(
        "supplies",
        [],
    )


    all_supplies.extend(
        supplies
    )


    new_next = supply_data.get(
        "next"
    )


    print(
        f"Получено поставок: "
        f"{len(supplies):,} "
        f"| всего: "
        f"{len(all_supplies):,} "
        f"| next: "
        f"{new_next}"
    )


    if not supplies:
        break


    if not new_next:
        break


    if new_next == next_value:
        break


    next_value = new_next


    time.sleep(
        0.2
    )


print()
print(
    f"Всего поставок: "
    f"{len(all_supplies):,}"
)


# ============================================================
# 4. ПОЛУЧАЕМ ID ЗАКАЗОВ В КАЖДОЙ ПОСТАВКЕ
# ============================================================

print()
print(
    "=" * 70
)

print(
    "4. Получаем состав поставок"
)

print(
    "=" * 70
)


order_to_supply = {}


for number, supply in enumerate(
    all_supplies,
    start=1,
):

    supply_id = supply.get(
        "id"
    )


    if not supply_id:
        continue


    url = (
        f"{BASE_URL}"
        f"/api/marketplace/v3/"
        f"supplies/"
        f"{supply_id}/"
        f"order-ids"
    )


    try:

        data = wb_get(
            url
        )

    except RuntimeError:

        print(
            f"Не удалось получить "
            f"заказы поставки "
            f"{supply_id}"
        )

        continue


    order_ids = (
        data.get("orderIds")
        or data.get("orders")
        or []
    )


    for order_id in order_ids:

        if isinstance(
            order_id,
            dict,
        ):

            current_order_id = (
                order_id.get("id")
                or order_id.get("orderId")
            )

        else:

            current_order_id = (
                order_id
            )


        if current_order_id is None:
            continue


        order_to_supply[
            int(current_order_id)
        ] = supply_id


    print(
        f"{number:>3}/"
        f"{len(all_supplies)} "
        f"| {supply_id} "
        f"| заказов: "
        f"{len(order_ids):,}"
    )


    time.sleep(
        0.1
    )


print()
print(
    f"Заказов связано "
    f"с поставками: "
    f"{len(order_to_supply):,}"
)


# ============================================================
# СЛОВАРЬ ПОСТАВОК
# ============================================================

supply_by_id = {
    supply.get("id"): supply
    for supply in all_supplies
    if supply.get("id")
}


# ============================================================
# 5. СОБИРАЕМ ДАННЫЕ ПО FBS-ЗАКАЗАМ
# ============================================================

print()
print(
    "=" * 70
)

print(
    "5. Формируем таблицу"
)

print(
    "=" * 70
)


rows = []


loaded_at = pd.Timestamp.now(
    tz="UTC"
)


for order in all_orders:

    order_id = order.get(
        "id"
    )


    status = status_by_order_id.get(
        order_id,
        {},
    )


    supply_id = order_to_supply.get(
        order_id
    )


    supply = supply_by_id.get(
        supply_id,
        {},
    )


    rows.append({

        # ----------------------------------------------------
        # ЗАКАЗ
        # ----------------------------------------------------

        "order_id":
            order_id,

        "order_uid":
            order.get(
                "orderUid"
            ),

        "rid":
            order.get(
                "rid"
            ),

        "created_at":
            order.get(
                "createdAt"
            ),

        "delivery_type":
            order.get(
                "deliveryType"
            ),

        # ----------------------------------------------------
        # ТОВАР
        # ----------------------------------------------------

        "nm_id":
            order.get(
                "nmId"
            ),

        "chrt_id":
            order.get(
                "chrtId"
            ),

        "article":
            order.get(
                "article"
            ),

        "sku":
            (
                order.get(
                    "skus",
                    [None],
                )[0]
                if order.get("skus")
                else None
            ),

        # ----------------------------------------------------
        # СКЛАД ПРОДАВЦА
        # ----------------------------------------------------

        "warehouse_id":
            order.get(
                "warehouseId"
            ),

        # ----------------------------------------------------
        # ЦЕНЫ
        # ----------------------------------------------------

        "price":
            order.get(
                "price"
            ),

        "sale_price":
            order.get(
                "salePrice"
            ),

        "final_price":
            order.get(
                "finalPrice"
            ),

        "converted_price":
            order.get(
                "convertedPrice"
            ),

        "converted_final_price":
            order.get(
                "convertedFinalPrice"
            ),

        # ----------------------------------------------------
        # СТАТУС
        # ----------------------------------------------------

        "supplier_status":
            status.get(
                "supplierStatus"
            ),

        "wb_status":
            status.get(
                "wbStatus"
            ),

        "is_cancellable":
            status.get(
                "isCancellable"
            ),

        # ----------------------------------------------------
        # ПОСТАВКА
        # ----------------------------------------------------

        "supply_id":
            supply_id,

        "supply_name":
            supply.get(
                "name"
            ),

        "supply_created_at":
            supply.get(
                "createdAt"
            ),

        "supply_closed_at":
            supply.get(
                "closedAt"
            ),

        "supply_scan_dt":
            supply.get(
                "scanDt"
            ),

        "supply_reject_dt":
            supply.get(
                "rejectDt"
            ),

        "supply_done":
            supply.get(
                "done"
            ),

        "destination_office_id":
            supply.get(
                "destinationOfficeId"
            ),

        # ----------------------------------------------------
        # ДОПОЛНИТЕЛЬНО
        # ----------------------------------------------------

        "office_id":
            order.get(
                "officeId"
            ),

        "offices":
            json.dumps(
                order.get(
                    "offices",
                    [],
                ),
                ensure_ascii=False,
            ),

        "required_meta":
            json.dumps(
                order.get(
                    "requiredMeta",
                    [],
                ),
                ensure_ascii=False,
            ),

        "optional_meta":
            json.dumps(
                order.get(
                    "optionalMeta",
                    [],
                ),
                ensure_ascii=False,
            ),

        "is_zero_order":
            order.get(
                "isZeroOrder"
            ),

        # ----------------------------------------------------
        # ТЕХНИЧЕСКОЕ
        # ----------------------------------------------------

        "_loaded_at":
            loaded_at,

        "payload":
            json.dumps(
                order,
                ensure_ascii=False,
            ),
    })


# ============================================================
# 6. DATAFRAME
# ============================================================

df = pd.DataFrame(
    rows
)


print()
print(
    f"Строк в таблице: "
    f"{len(df):,}"
)


# ============================================================
# ТИПЫ ДАТ
# ============================================================

date_columns = [
    "created_at",
    "supply_created_at",
    "supply_closed_at",
    "supply_scan_dt",
    "supply_reject_dt",
]


for column in date_columns:

    if column in df.columns:

        df[column] = pd.to_datetime(
            df[column],
            utc=True,
            errors="coerce",
        )


# ============================================================
# ЧИСЛОВЫЕ ID
# ============================================================

id_columns = [
    "order_id",
    "nm_id",
    "chrt_id",
    "warehouse_id",
    "office_id",
    "destination_office_id",
]


for column in id_columns:

    if column in df.columns:

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        ).astype(
            "Int64"
        )


# ============================================================
# ЦЕНЫ WB
#
# WB отдаёт значения в копейках.
# Оставляем исходное значение
# и создаём отдельное поле в рублях.
# ============================================================

price_columns = [
    "price",
    "sale_price",
    "final_price",
    "converted_price",
    "converted_final_price",
]


for column in price_columns:

    if column in df.columns:

        df[column] = pd.to_numeric(
            df[column],
            errors="coerce",
        )


        df[
            f"{column}_rub"
        ] = (
            df[column]
            / 100
        )


# ============================================================
# 7. РАСЧЁТ ВРЕМЕНИ
#
# Пока считаем два варианта:
#
# заказ -> закрытие поставки
# заказ -> сканирование поставки
#
# Позже определим, какой показатель
# соответствует расчётам WB.
# ============================================================

if not df.empty:

    df[
        "hours_to_supply_close"
    ] = (
        (
            df["supply_closed_at"]
            - df["created_at"]
        )
        .dt.total_seconds()
        / 3600
    )


    df[
        "hours_to_supply_scan"
    ] = (
        (
            df["supply_scan_dt"]
            - df["created_at"]
        )
        .dt.total_seconds()
        / 3600
    )


# ============================================================
# 8. ДОПОЛНИТЕЛЬНЫЕ СЧЁТЧИКИ
# ============================================================

orders_with_supply = 0
orders_without_supply = 0

orders_with_closed_at = 0
orders_with_scan_dt = 0


if not df.empty:

    orders_with_supply = (
        df["supply_id"]
        .notna()
        .sum()
    )


    orders_without_supply = (
        df["supply_id"]
        .isna()
        .sum()
    )


    orders_with_closed_at = (
        df["supply_closed_at"]
        .notna()
        .sum()
    )


    orders_with_scan_dt = (
        df["supply_scan_dt"]
        .notna()
        .sum()
    )


# ============================================================
# 9. СОХРАНЯЕМ PARQUET
#
# Один файл на одну дату.
#
# Повторный запуск в этот же день
# перезапишет файл.
# ============================================================

file_date = loaded_at.strftime(
    "%Y-%m-%d"
)


file_name = (
    output_dir
    / f"fbs_orders_{file_date}.parquet"
)


df.to_parquet(
    file_name,
    index=False,
)


# ============================================================
# 10. СОХРАНЯЕМ ПОСТАВКИ
# ============================================================

supplies_df = pd.DataFrame(
    all_supplies
)


if not supplies_df.empty:

    for column in [
        "createdAt",
        "closedAt",
        "scanDt",
        "rejectDt",
    ]:

        if column in supplies_df.columns:

            supplies_df[column] = (
                pd.to_datetime(
                    supplies_df[column],
                    utc=True,
                    errors="coerce",
                )
            )


supplies_file = (
    output_dir
    / f"fbs_supplies_{file_date}.parquet"
)


supplies_df.to_parquet(
    supplies_file,
    index=False,
)


# ============================================================
# 11. СПРАВОЧНИКИ СКЛАДОВ
#
# GET /api/v3/warehouses — наши склады отправления:
#   id, name, officeId, cargoType, deliveryType
#
# GET /api/v3/offices — склады WB, куда отгружаем:
#   id, name, address, city, cargoType, deliveryType
#
# Справочники маленькие и меняются редко, поэтому храним
# по одному файлу без даты — каждый запуск перезаписывает.
#
# Блок стоит В КОНЦЕ и обёрнут в try: заказы и поставки
# уже сохранены выше, и если ручка справочников отвалится
# или у токена не окажется на неё прав, дневная загрузка
# всё равно останется на диске.
# ============================================================

print()
print(
    "=" * 70
)

print(
    "11. Справочники складов"
)

print(
    "=" * 70
)


warehouses_df = pd.DataFrame()
offices_df = pd.DataFrame()

warehouses_file = (
    output_dir
    / "fbs_warehouses.parquet"
)

offices_file = (
    output_dir
    / "fbs_offices.parquet"
)


try:

    # --------------------------------------------------------
    # НАШИ СКЛАДЫ
    # --------------------------------------------------------

    warehouses = wb_get(
        WAREHOUSES_URL
    )


    if not isinstance(
        warehouses,
        list,
    ):

        raise RuntimeError(
            "Ожидался список складов продавца, "
            f"пришло: {type(warehouses).__name__}"
        )


    warehouses_df = pd.DataFrame([
        {
            "warehouse_id":
                item.get("id"),

            "warehouse_name":
                item.get("name"),

            "office_id":
                item.get("officeId"),

            "cargo_type":
                item.get("cargoType"),

            "cargo_type_name":
                CARGO_TYPE_NAMES.get(
                    item.get("cargoType"),
                    "—",
                ),

            "delivery_type":
                item.get("deliveryType"),

            "delivery_type_name":
                DELIVERY_TYPE_NAMES.get(
                    item.get("deliveryType"),
                    "—",
                ),

            "loaded_at":
                loaded_at,
        }
        for item in warehouses
    ])


    warehouses_df.to_parquet(
        warehouses_file,
        index=False,
    )


    print(
        f"Складов продавца: "
        f"{len(warehouses_df):,}"
    )


    time.sleep(
        0.3
    )


    # --------------------------------------------------------
    # СКЛАДЫ WB
    # --------------------------------------------------------

    offices = wb_get(
        OFFICES_URL
    )


    if not isinstance(
        offices,
        list,
    ):

        raise RuntimeError(
            "Ожидался список складов WB, "
            f"пришло: {type(offices).__name__}"
        )


    offices_df = pd.DataFrame([
        {
            "office_id":
                item.get("id"),

            "office_name":
                item.get("name"),

            "address":
                item.get("address"),

            "city":
                item.get("city"),

            "cargo_type":
                item.get("cargoType"),

            "cargo_type_name":
                CARGO_TYPE_NAMES.get(
                    item.get("cargoType"),
                    "—",
                ),

            "delivery_type":
                item.get("deliveryType"),

            "delivery_type_name":
                DELIVERY_TYPE_NAMES.get(
                    item.get("deliveryType"),
                    "—",
                ),

            "loaded_at":
                loaded_at,
        }
        for item in offices
    ])


    offices_df.to_parquet(
        offices_file,
        index=False,
    )


    print(
        f"Складов WB: "
        f"{len(offices_df):,}"
    )


    # --------------------------------------------------------
    # ПОКРЫТИЕ
    #
    # Сразу видно, все ли склады из заказов
    # получится назвать по имени.
    # --------------------------------------------------------

    if (
        not df.empty
        and not warehouses_df.empty
        and "warehouse_id" in df.columns
    ):

        order_warehouses = set(
            df["warehouse_id"]
            .dropna()
            .astype(int)
            .unique()
        )


        known_warehouses = set(
            warehouses_df["warehouse_id"]
            .dropna()
            .astype(int)
            .unique()
        )


        unknown = (
            order_warehouses
            - known_warehouses
        )


        print(
            f"Складов в заказах: "
            f"{len(order_warehouses):,} "
            f"| с названием: "
            f"{len(order_warehouses & known_warehouses):,}"
        )


        if unknown:

            print(
                f"Без названия: "
                f"{sorted(unknown)} "
                f"— эти склады удалены "
                f"или больше не ваши"
            )


except Exception as e:

    print()
    print(
        f"Справочники складов не загрузились: {e}"
    )

    print(
        "Заказы и поставки это не затрагивает — "
        "они уже сохранены выше."
    )


# ============================================================
# 12. ИТОГ
# ============================================================

print()
print(
    "=" * 70
)

print(
    "FBS ORDERS LOADED"
)

print(
    "-" * 70
)

print(
    f"FBS-заказов: "
    f"{len(all_orders):,}"
)

print(
    f"Статусов: "
    f"{len(statuses):,}"
)

print(
    f"Поставок: "
    f"{len(all_supplies):,}"
)

print(
    f"Связей заказ -> поставка: "
    f"{len(order_to_supply):,}"
)

print(
    f"Заказов с supply_id: "
    f"{orders_with_supply:,}"
)

print(
    f"Заказов без supply_id: "
    f"{orders_without_supply:,}"
)

print(
    f"Заказов с closedAt: "
    f"{orders_with_closed_at:,}"
)

print(
    f"Заказов с scanDt: "
    f"{orders_with_scan_dt:,}"
)

print(
    f"Строк parquet: "
    f"{len(df):,}"
)

print(
    f"Складов продавца: "
    f"{len(warehouses_df):,}"
)

print(
    f"Складов WB: "
    f"{len(offices_df):,}"
)

print()

print(
    "Orders:"
)

print(
    file_name
)

print()

print(
    "Supplies:"
)

print(
    supplies_file
)

print()

print(
    "Warehouses:"
)

print(
    warehouses_file
)

print()

print(
    "Offices:"
)

print(
    offices_file
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
# 13. КРАТКИЙ ПРОСМОТР
# ============================================================

if not df.empty:

    preview_columns = [
        column
        for column in [
            "order_id",
            "article",
            "nm_id",
            "created_at",
            "supplier_status",
            "wb_status",
            "supply_id",
            "supply_name",
            "supply_closed_at",
            "supply_scan_dt",
            "hours_to_supply_close",
            "hours_to_supply_scan",
        ]
        if column in df.columns
    ]


    print()
    print(
        df[
            preview_columns
        ]
        .head(30)
        .to_string(
            index=False
        )
    )
