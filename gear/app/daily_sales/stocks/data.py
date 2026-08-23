# gear/app/daily_sales/stocks/data.py
from datetime import date, timedelta

from conns import get_duckdb_conn_with_opt


# =============================================================================
# СЕБЕСТОИМОСТЬ ЗА ЕДИНИЦУ — ЕДИНАЯ МЕТОДИКА ДЛЯ ВСЕХ ОТЧЁТОВ ПО ОСТАТКАМ
#
# Раньше каждый отчёт независимо считал себестоимость как
# MAX(pre_wo.adjust_wo[-1]) — последний элемент массива СПИСАНИЙ.
# Такой массив заполнен ТОЛЬКО у товаров, по которым уже были продажи:
# непроданный товар получал NULL -> 0 и попадал в отчёт с нулевой
# стоимостью остатка. Для оценки ущерба (пожар) это критично —
# сгорает весь остаток, включая ни разу не проданный.
#
# Основной источник теперь — приходные УПД (inventories.upd_income),
# тот же, что в costs_control:
#
#     upd_price_vatless  — бухгалтерская цена за единицу
#     man_cost_per_unit  — управленческая цена за единицу
#
# ЕДИНИЦЫ. upd_income хранит РУБЛИ, pre_wo — КОПЕЙКИ. Наружу этот
# блок отдаёт КОПЕЙКИ (цена из УПД умножается на 100), чтобы не
# трогать перевод в рубли, который выполняется ниже по течению
# (excel.py, снимок происшествия в dashboard_data.py).
#
# ДАТА. Берётся последний приход НЕ ПОЗЖЕ $report_date. Приход из
# будущего в историческую дату не попадает. ARG_MAX в DuckDB
# пропускает NULL, поэтому если в самом свежем УПД управленческая
# цена не заполнена, подставится последняя заполненная.
#
# pre_wo остаётся РЕЗЕРВОМ: если приходов по УПД до даты отчёта нет
# (например, товар пришёл не по УПД), используется последняя
# себестоимость списания — прежнее поведение.
#
# ТРЕБОВАНИЯ К ЗАПРОСУ, КУДА ВСТАВЛЯЕТСЯ БЛОК:
#   1. выше должен быть определён CTE nm_usk (nm_id, usk);
#   2. в запросе должен быть параметр $report_date;
#   3. блок НЕ заканчивается запятой — её ставит место вставки.
#
# Итоговый CTE называется costs и отдаёт колонки:
#   nm_id, last_costs, last_man_costs   (копейки)
# =============================================================================

COSTS_CTES_SQL = """
            /*
            ============================================================
            РЕЗЕРВ: ПОСЛЕДНЯЯ СЕБЕСТОИМОСТЬ СПИСАНИЯ (копейки)

            Если у nm_id несколько USK, берём максимальную
            последнюю известную стоимость среди связанных USK.
            ============================================================
            */
            wo_costs AS (
                SELECT
                    nu.nm_id,

                    MAX(
                        w.adjust_wo[-1]
                    ) AS last_costs,

                    MAX(
                        w.adjust_man_wo[-1]
                    ) AS last_man_costs

                FROM nm_usk nu

                LEFT JOIN inventories.pre_wo w
                    ON w.usk = nu.usk

                GROUP BY
                    nu.nm_id
            ),


            /*
            ============================================================
            ОСНОВНОЙ ИСТОЧНИК: ПРИХОДНЫЕ УПД

            Последний приход не позже даты отчёта.
            Рубли переводим в копейки (* 100).
            ============================================================
            */
            upd_costs AS (
                SELECT
                    t.nm_id,

                    ARG_MAX(
                        t.upd_price_vatless,
                        u.date
                    ) * 100 AS last_costs,

                    ARG_MAX(
                        t.man_cost_per_unit,
                        u.date
                    ) * 100 AS last_man_costs

                FROM inventories.upd_income t

                LEFT JOIN inventories.upd_documents u
                    ON u.id = t.upd_document_id

                WHERE
                    t.nm_id IS NOT NULL
                    AND u.date::DATE <= $report_date::DATE

                GROUP BY
                    t.nm_id
            ),


            /*
            ============================================================
            ИТОГОВАЯ СЕБЕСТОИМОСТЬ: УПД, ПРИ ОТСУТСТВИИ — СПИСАНИЕ

            FULL OUTER JOIN, потому что nm_id может быть только
            в УПД (нет связи с USK) или только в pre_wo
            (пришёл не по УПД).

            NULLIF(..., 0) — незаполненная цена в УПД хранится
            как 0 и должна уступать место резерву.
            ============================================================
            */
            costs AS (
                SELECT
                    COALESCE(
                        uc.nm_id,
                        wc.nm_id
                    ) AS nm_id,

                    COALESCE(
                        NULLIF(
                            uc.last_costs,
                            0
                        ),
                        wc.last_costs
                    ) AS last_costs,

                    COALESCE(
                        NULLIF(
                            uc.last_man_costs,
                            0
                        ),
                        wc.last_man_costs
                    ) AS last_man_costs

                FROM upd_costs uc

                FULL OUTER JOIN wo_costs wc
                    ON wc.nm_id = uc.nm_id
            )"""


def get_default_stocks_date():
    return date.today() - timedelta(days=1)


def get_stocks_export_data(report_date):
    """
    Детальная выгрузка остатков для Excel.

    Добавлено:
    - последняя наша розничная цена;
    - продажи за последние 7 дней;
    - оборачиваемость в днях;
    - дата последнего прихода;
    - возраст товара.

    ЛОГИКА ОБОРАЧИВАЕМОСТИ
    ----------------------

    Оборачиваемость рассчитывается НА УРОВНЕ NM_ID.

    Причина:
    остатки в stocks.unpacked_stocks находятся в том числе
    на уровне размера / chrt_id, а продажи в inventories.inv_gl_final
    находятся на уровне USK.

    Поэтому нельзя брать:
        остаток одного chrt_id
        /
        продажи всего USK

    Это давало неправильную оборачиваемость.

    Теперь:

    1. Остатки сначала агрегируются по nm_id + chrt_id.
    2. Отдельно считается общий фактический остаток по nm_id.
    3. Продажи inv_gl_final переводятся USK -> nm_id.
    4. Продажи агрегируются по nm_id.
    5. Оборачиваемость:

        общий остаток nm_id
        /
        (чистые продажи nm_id за 7 дней / 7)

    Формула:

        stock_qty_nm_id * 7 / sales_qty_7d

    Продажи:
        cr_rev > 0 -> +1
        cr_rev < 0 -> -1

    ВАЖНО:
    - в оборачиваемость входит только фактический остаток quantity;
    - товары в пути не входят;
    - оборачиваемость одинаковая для всех размеров одного nm_id;
    - если чистые продажи за 7 дней <= 0,
      оборачиваемость не рассчитывается;
    - себестоимость приходит в копейках;
    - в рубли себестоимость переводим уже в excel.py;
    - retail_price переводим в рубли здесь;
    - NM ID и Chrt ID в Excel переносятся в конец.
    """

    with get_duckdb_conn_with_opt() as con:
        df = con.execute(
            """
            WITH

            /*
            ============================================================
            КАРТА USK -> NM_ID

            Делаем отдельную дедуплицированную таблицу.

            Это важно, потому что прямой JOIN inventories.usk
            к остаткам по card_id может размножить строки,
            если в inventories.usk есть несколько записей
            для одного card_id.
            ============================================================
            */
            usk_to_nm AS (
                SELECT
                    usk,
                    MAX(card_id) AS nm_id

                FROM inventories.usk

                WHERE
                    usk IS NOT NULL
                    AND card_id IS NOT NULL

                GROUP BY
                    usk
            ),


            /*
            ============================================================
            ОСТАТКИ

            Здесь НЕ присоединяем inventories.usk.

            Одна строка:
                дата + nm_id + chrt_id

            Это защищает остатки от размножения.
            ============================================================
            */
/*
============================================================
ОСТАТКИ WB
============================================================
*/
wb_stocks AS (
    SELECT
        t.date_from::DATE AS date_from,
        t.nm_id,
        t.chrt_id,

        SUM(
            COALESCE(
                t.quantity,
                0
            )
        ) AS wb_quantity,

        SUM(
            COALESCE(
                t.in_way_from_client,
                0
            )
        ) AS in_way_from_client,

        SUM(
            COALESCE(
                t.in_way_to_client,
                0
            )
        ) AS in_way_to_client

    FROM stocks.unpacked_stocks t

    WHERE
        t.date_from::DATE = $report_date::DATE

    GROUP BY
        t.date_from::DATE,
        t.nm_id,
        t.chrt_id
),


/*
============================================================
ОСТАТКИ FBS
============================================================
*/
fbs_stocks AS (
    SELECT
        t.date_from::DATE AS date_from,
        t.nm_id,
        t.chrt_id,

        SUM(
            COALESCE(
                t.quantity,
                0
            )
        ) AS fbs_quantity

    FROM stocks.unpacked_fbs_stocks t

    WHERE
        t.date_from::DATE = $report_date::DATE

    GROUP BY
        t.date_from::DATE,
        t.nm_id,
        t.chrt_id
),


/*
============================================================
WB + FBS

FULL OUTER JOIN нужен обязательно:
товар может быть только на WB или только на FBS.
============================================================
*/
    stocks AS (
        SELECT
            COALESCE(
                wb.date_from,
                fbs.date_from
            ) AS date_from,

            COALESCE(
                wb.nm_id,
                fbs.nm_id
            ) AS nm_id,

            COALESCE(
                wb.chrt_id,
                fbs.chrt_id
            ) AS chrt_id,

            COALESCE(
                wb.wb_quantity,
                0
            ) AS quantity_on_hand,

            COALESCE(
                fbs.fbs_quantity,
                0
            ) AS fbs_quantity,

            COALESCE(
                wb.in_way_from_client,
                0
            ) AS in_way_from_client,

            COALESCE(
                wb.in_way_to_client,
                0
            ) AS in_way_to_client,

            (
                COALESCE(
                    wb.wb_quantity,
                    0
                )
                +
                COALESCE(
                    fbs.fbs_quantity,
                    0
                )
            ) AS physical_quantity,

            (
                COALESCE(
                    wb.wb_quantity,
                    0
                )
                +
                COALESCE(
                    fbs.fbs_quantity,
                    0
                )
                +
                COALESCE(
                    wb.in_way_from_client,
                    0
                )
                +
                COALESCE(
                    wb.in_way_to_client,
                    0
                )
            ) AS total_quantity

        FROM wb_stocks wb

        FULL OUTER JOIN fbs_stocks fbs
                ON wb.date_from = fbs.date_from
                AND wb.chrt_id = fbs.chrt_id
    ),


            /*
            ============================================================
            ОБЩИЙ ОСТАТОК ПО NM_ID

            Именно этот остаток используется для оборачиваемости.

            Если у товара:

                S = 10 шт.
                M = 20 шт.
                L = 30 шт.

            stock_qty_nm = 60 шт.
            ============================================================
            */
stocks_by_nm AS (
    SELECT
        nm_id,

        SUM(
            physical_quantity
        ) AS total_quantity_nm

    FROM stocks

    GROUP BY
        nm_id
),

            /*
            ============================================================
            КАРТА NM_ID -> USK ДЛЯ СЕБЕСТОИМОСТИ

            Нам нужна последняя себестоимость из pre_wo.

            Сначала получаем список связей без размножения
            основной таблицы остатков.
            ============================================================
            */
            nm_usk AS (
                SELECT
                    card_id AS nm_id,
                    usk

                FROM inventories.usk

                WHERE
                    card_id IS NOT NULL
                    AND usk IS NOT NULL

                GROUP BY
                    card_id,
                    usk
            ),


            """
            + COSTS_CTES_SQL
            + """,


            /*
            ============================================================
            БРЕНД
            ============================================================
            */
            brands AS (
                SELECT
                    nm_id,

                    COALESCE(
                        MAX(brand),
                        'Бренд не указан'
                    ) AS brand

                FROM cards.unpacked_cards

                GROUP BY
                    nm_id
            ),


            /*
            ============================================================
            ПОСЛЕДНЯЯ НАША РОЗНИЧНАЯ ЦЕНА

            Берём последнюю известную retail_price
            на дату отчёта или раньше.

            Цена из будущего в историческую дату
            не попадает.
            ============================================================
            */
            prices AS (
                SELECT
                    nm_id,

                    LIST(
                        val
                        ORDER BY date_from
                    )[-1] AS last_price

                FROM sales.sales_long

                WHERE
                    field = 'retail_price'
                    AND oper = 'dt'
                    AND date_from::DATE <= $report_date::DATE

                GROUP BY
                    nm_id
            ),


            /*
            ============================================================
            ПОСЛЕДНИЙ ПРИХОД

            inventories.upd_income
                ->
            inventories.upd_documents

            Последний приход = максимальная дата УПД
            на дату отчёта или раньше.
            ============================================================
            */
            last_income AS (
                SELECT
                    ui.nm_id,

                    MAX(
                        ud.date
                    )::DATE AS last_income_date

                FROM inventories.upd_income ui

                INNER JOIN inventories.upd_documents ud
                    ON ud.id = ui.upd_document_id

                WHERE
                    ui.nm_id IS NOT NULL

                    AND ud.date::DATE
                        <= $report_date::DATE

                GROUP BY
                    ui.nm_id
            ),


            /*
            ============================================================
            ПРОДАЖИ ЗА 7 ДНЕЙ НА УРОВНЕ USK

            Источник:
                inventories.inv_gl_final

            Чистые продажи:
                cr_rev > 0 -> +1
                cr_rev < 0 -> -1

            Период:
                report_date - 6 дней
                ...
                report_date

            То есть ровно 7 календарных дней.
            ============================================================
            */
            sales_7d_by_usk AS (
                SELECT
                    t.usk,

                    SUM(
                        CASE

                            WHEN COALESCE(
                                t.cr_rev,
                                0
                            ) > 0
                            THEN 1

                            WHEN COALESCE(
                                t.cr_rev,
                                0
                            ) < 0
                            THEN -1

                            ELSE 0

                        END
                    ) AS sales_qty_7d

                FROM inventories.inv_gl_final t

                WHERE
                    COALESCE(
                        t.cr_rev,
                        0
                    ) <> 0

                    AND t.date_from::DATE
                        BETWEEN
                        (
                            $report_date::DATE
                            - INTERVAL 6 DAY
                        )
                        AND $report_date::DATE

                GROUP BY
                    t.usk
            ),


            /*
            ============================================================
            ПРОДАЖИ ЗА 7 ДНЕЙ НА УРОВНЕ NM_ID

            Переводим:
                USK -> NM_ID

            Затем суммируем все продажи всех USK,
            относящихся к одному nm_id.

            Теперь уровень продаж совпадает
            с уровнем остатка для оборачиваемости.
            ============================================================
            */
            sales_7d AS (
                SELECT
                    m.nm_id,

                    SUM(
                        s.sales_qty_7d
                    ) AS sales_qty_7d

                FROM sales_7d_by_usk s

                INNER JOIN usk_to_nm m
                    ON m.usk = s.usk

                WHERE
                    m.nm_id IS NOT NULL

                GROUP BY
                    m.nm_id
            )


            /*
            ============================================================
            ИТОГОВАЯ ВЫГРУЗКА
            ============================================================
            */
            SELECT
                s.date_from
                    AS "Дата",


                /*
                --------------------------------------------------------
                USK

                Поскольку итоговая строка находится на уровне
                nm_id + chrt_id, а у nm_id потенциально может
                быть несколько USK, выбираем один представитель.

                USK здесь информационное поле и НЕ используется
                для расчёта оборачиваемости.
                --------------------------------------------------------
                */
                (
                    SELECT
                        MIN(nu.usk)

                    FROM nm_usk nu

                    WHERE
                        nu.nm_id = s.nm_id
                ) AS "USK",


                /*
                --------------------------------------------------------
                Карточка товара
                --------------------------------------------------------
                */
                COALESCE(
                    b.brand,
                    'Бренд не указан'
                ) AS "Бренд",

                COALESCE(
                    p.subject_name,
                    'Категория не указана'
                ) AS "Категория",

                COALESCE(
                    p.gender,
                    'Пол не указан'
                ) AS "Пол",

                COALESCE(
                    p.sa_name,
                    ''
                ) AS "Артикул",

                COALESCE(
                    p.title,
                    ''
                ) AS "Наименование",

                COALESCE(
                    sz.tech_size,
                    ''
                ) AS "Размер",


                /*
                --------------------------------------------------------
                Остатки конкретного размера / chrt_id
                --------------------------------------------------------
                */
               s.total_quantity
                    AS "Итого количество",

                s.quantity_on_hand
                    AS "Остаток на складе",

                s.fbs_quantity
                    AS "Остаток FBS",

                s.in_way_from_client
                    AS "В пути от клиента",

                s.in_way_to_client
                    AS "В пути к клиенту",


                /*
                --------------------------------------------------------
                Последняя наша розничная цена

                retail_price хранится в копейках,
                поэтому переводим в рубли.
                --------------------------------------------------------
                */
                ROUND(
                    COALESCE(
                        lp.last_price,
                        0
                    ) / 100.0,
                    2
                ) AS "Последняя наша розничная цена",


                /*
                --------------------------------------------------------
                Чистые продажи NM_ID за последние 7 дней

                В каждой строке размера одного nm_id
                будет одинаковое значение.

                Это правильно, потому что продажи считаются
                на уровне всего товара nm_id.
                --------------------------------------------------------
                */
                COALESCE(
                    sl7.sales_qty_7d,
                    0
                ) AS "Продажи за 7 дней",


                /*
                --------------------------------------------------------
                Оборачиваемость в днях

                ОБОРАЧИВАЕМОСТЬ СЧИТАЕТСЯ НА УРОВНЕ NM_ID.

                Формула:

                    общий фактический остаток nm_id
                    --------------------------------
                    продажи nm_id за 7 дней / 7

                Или:

                    stock_nm_id * 7
                    ----------------
                    sales_qty_7d

                Товары в пути НЕ входят.

                Для всех размеров одного nm_id значение
                оборачиваемости будет одинаковым.
                --------------------------------------------------------
                */
                CASE

                    WHEN COALESCE(
                        sl7.sales_qty_7d,
                        0
                    ) > 0

                    THEN ROUND(
    COALESCE(
        sn.total_quantity_nm,
        0
    )
    * 7.0
    /
    sl7.sales_qty_7d,
    2
)

                    ELSE NULL

                END AS "Оборачиваемость 7 дней",


                /*
                --------------------------------------------------------
                Последний приход
                --------------------------------------------------------
                */
                li.last_income_date
                    AS "Дата последнего прихода",


                /*
                --------------------------------------------------------
                Возраст товара

                Дата отчёта
                минус
                дата последнего прихода.
                --------------------------------------------------------
                */
                CASE

                    WHEN li.last_income_date
                        IS NOT NULL

                    THEN DATE_DIFF(
                        'day',
                        li.last_income_date,
                        $report_date::DATE
                    )

                    ELSE NULL

                END AS "Возраст товара, дней",


                /*
                --------------------------------------------------------
                Себестоимость за единицу
                --------------------------------------------------------
                */
                c.last_costs
                    AS "Бух. с/с за ед.",

                c.last_man_costs
                    AS "Упр. с/с за ед.",


                /*
                --------------------------------------------------------
                Общая стоимость остатка

                Здесь сохраняем прежнюю логику:
                стоимость считается по ИТОГО количеству,
                включая товары в пути.
                --------------------------------------------------------
                */
                s.total_quantity
                * COALESCE(
                    c.last_costs,
                    0
                ) AS "Бух. с/с всего",

                s.total_quantity
                * COALESCE(
                    c.last_man_costs,
                    0
                ) AS "Упр. с/с всего",


                /*
                --------------------------------------------------------
                Технические ID
                --------------------------------------------------------
                */
                s.nm_id
                    AS "NM ID",

                s.chrt_id
                    AS "Chrt ID"


            FROM stocks s


            LEFT JOIN stocks_by_nm sn
                ON sn.nm_id = s.nm_id


            LEFT JOIN cards.product p
                ON p.nm_id = s.nm_id


            LEFT JOIN brands b
                ON b.nm_id = s.nm_id


            LEFT JOIN cards.sizes sz
                ON sz.chrt_id = s.chrt_id


            LEFT JOIN prices lp
                ON lp.nm_id = s.nm_id


            LEFT JOIN last_income li
                ON li.nm_id = s.nm_id


            LEFT JOIN sales_7d sl7
                ON sl7.nm_id = s.nm_id


            LEFT JOIN costs c
                ON c.nm_id = s.nm_id


            WHERE
                s.total_quantity > 0


            ORDER BY
                COALESCE(
                    b.brand,
                    'Бренд не указан'
                ),

                COALESCE(
                    p.subject_name,
                    'Категория не указана'
                ),

                COALESCE(
                    p.title,
                    ''
                ),

                COALESCE(
                    sz.tech_size,
                    ''
                )
            """,
            {
                "report_date": report_date,
            },
        ).df()

    return df


# def get_stocks_summary_stats(report_date):
#     with get_duckdb_conn_with_opt() as con:
#         warehouse_row = con.execute(
#             """
#             SELECT
#                 COUNT(
#                     DISTINCT warehouse_name
#                 ) AS total_warehouses,

#                 SUM(
#                     COALESCE(
#                         quantity,
#                         0
#                     )
#                 ) AS total_on_hand,

#                 SUM(
#                     COALESCE(
#                         in_way_to_client,
#                         0
#                     )
#                     +
#                     COALESCE(
#                         in_way_from_client,
#                         0
#                     )
#                 ) AS total_in_transit,

#                 SUM(
#                     COALESCE(
#                         quantity,
#                         0
#                     )
#                     +
#                     COALESCE(
#                         in_way_to_client,
#                         0
#                     )
#                     +
#                     COALESCE(
#                         in_way_from_client,
#                         0
#                     )
#                 ) AS total_quantity

#             FROM stocks.unpacked_stocks

#             WHERE
#                 date_from::DATE
#                     = $report_date::DATE
#             """,
#             {
#                 "report_date": report_date,
#             },
#         ).fetchone()


#         product_row = con.execute(
#             """
#             WITH stocks AS (
#                 SELECT
#                     t.nm_id,
#                     t.chrt_id,

#                     SUM(
#                         COALESCE(
#                             t.quantity,
#                             0
#                         )
#                         +
#                         COALESCE(
#                             t.in_way_to_client,
#                             0
#                         )
#                         +
#                         COALESCE(
#                             t.in_way_from_client,
#                             0
#                         )
#                     ) AS qty

#                 FROM stocks.unpacked_stocks t

#                 WHERE
#                     t.date_from::DATE
#                         = $report_date::DATE

#                 GROUP BY
#                     t.nm_id,
#                     t.chrt_id
#             ),


#             brands AS (
#                 SELECT
#                     nm_id,

#                     COALESCE(
#                         MAX(brand),
#                         'Бренд не указан'
#                     ) AS brand

#                 FROM cards.unpacked_cards

#                 GROUP BY
#                     nm_id
#             )


#             SELECT
#                 COUNT(
#                     DISTINCT s.nm_id
#                 ) AS total_products,

#                 COUNT(
#                     DISTINCT b.brand
#                 ) AS total_brands,

#                 COUNT(*)
#                     AS total_positions,

#                 COUNT(
#                     DISTINCT p.subject_name
#                 ) AS total_categories


#             FROM stocks s


#             LEFT JOIN cards.product p
#                 ON p.nm_id = s.nm_id


#             LEFT JOIN brands b
#                 ON b.nm_id = s.nm_id


#             WHERE
#                 s.qty > 0
#             """,
#             {
#                 "report_date": report_date,
#             },
#         ).fetchone()


#     return {
#         "total_warehouses": (
#             warehouse_row[0]
#             or 0
#         ),

#         "total_on_hand": (
#             warehouse_row[1]
#             or 0
#         ),

#         "total_in_transit": (
#             warehouse_row[2]
#             or 0
#         ),

#         "total_quantity": (
#             warehouse_row[3]
#             or 0
#         ),

#         "total_products": (
#             product_row[0]
#             or 0
#         ),

#         "total_brands": (
#             product_row[1]
#             or 0
#         ),

#         "total_positions": (
#             product_row[2]
#             or 0
#         ),

#         "total_categories": (
#             product_row[3]
#             or 0
#         ),

#         "report_date": report_date,
#     }



def get_stocks_summary_stats(report_date):
    with get_duckdb_conn_with_opt() as con:

        # ============================================================
        # WB + ТОВАРЫ В ПУТИ
        # ============================================================

        warehouse_row = con.execute(
            """
            SELECT
                COUNT(
                    DISTINCT warehouse_name
                ) AS total_warehouses,

                SUM(
                    COALESCE(
                        quantity,
                        0
                    )
                ) AS total_on_hand,

                SUM(
                    COALESCE(
                        in_way_to_client,
                        0
                    )
                    +
                    COALESCE(
                        in_way_from_client,
                        0
                    )
                ) AS total_in_transit

            FROM stocks.unpacked_stocks

            WHERE
                date_from::DATE
                    = $report_date::DATE
            """,
            {
                "report_date": report_date,
            },
        ).fetchone()


        # ============================================================
        # FBS — НАШ СКЛАД
        # ============================================================

        fbs_row = con.execute(
            """
            SELECT
                SUM(
                    COALESCE(
                        quantity,
                        0
                    )
                ) AS total_fbs

            FROM stocks.unpacked_fbs_stocks

            WHERE
                date_from::DATE
                    = $report_date::DATE
            """,
            {
                "report_date": report_date,
            },
        ).fetchone()


        # ============================================================
        # ПОКАЗАТЕЛИ WB
        # ============================================================

        total_warehouses = (
            warehouse_row[0]
            or 0
        )

        total_on_hand = (
            warehouse_row[1]
            or 0
        )

        total_in_transit = (
            warehouse_row[2]
            or 0
        )


        # ============================================================
        # FBS
        # ============================================================

        total_fbs = (
            fbs_row[0]
            or 0
        )


        # ============================================================
        # ИТОГО
        #
        # WB
        # + FBS
        # + в пути к клиенту
        # + в пути от клиента
        # ============================================================

        total_quantity = (
            total_on_hand
            +
            total_fbs
            +
            total_in_transit
        )


        # ============================================================
        # КОЛИЧЕСТВО ТОВАРОВ / БРЕНДОВ / КАТЕГОРИЙ
        #
        # Здесь тоже объединяем WB + FBS,
        # чтобы товары только на FBS не потерялись.
        # ============================================================

        product_row = con.execute(
            """
            WITH

            wb AS (
                SELECT
                    nm_id,
                    chrt_id,

                    SUM(
                        COALESCE(
                            quantity,
                            0
                        )
                        +
                        COALESCE(
                            in_way_to_client,
                            0
                        )
                        +
                        COALESCE(
                            in_way_from_client,
                            0
                        )
                    ) AS qty

                FROM stocks.unpacked_stocks

                WHERE
                    date_from::DATE
                        = $report_date::DATE

                GROUP BY
                    nm_id,
                    chrt_id
            ),


            fbs AS (
                SELECT
                    nm_id,
                    chrt_id,

                    SUM(
                        COALESCE(
                            quantity,
                            0
                        )
                    ) AS qty

                FROM stocks.unpacked_fbs_stocks

                WHERE
                    date_from::DATE
                        = $report_date::DATE

                GROUP BY
                    nm_id,
                    chrt_id
            ),


            stocks AS (
                SELECT
                    COALESCE(
                        wb.nm_id,
                        fbs.nm_id
                    ) AS nm_id,

                    COALESCE(
                        wb.chrt_id,
                        fbs.chrt_id
                    ) AS chrt_id,

                    COALESCE(
                        wb.qty,
                        0
                    )
                    +
                    COALESCE(
                        fbs.qty,
                        0
                    ) AS qty

                FROM wb

                FULL OUTER JOIN fbs
                    ON wb.chrt_id = fbs.chrt_id
            ),


            brands AS (
                SELECT
                    nm_id,

                    COALESCE(
                        MAX(brand),
                        'Бренд не указан'
                    ) AS brand

                FROM cards.unpacked_cards

                GROUP BY
                    nm_id
            )


            SELECT
                COUNT(
                    DISTINCT s.nm_id
                ) AS total_products,

                COUNT(
                    DISTINCT b.brand
                ) AS total_brands,

                COUNT(*)
                    AS total_positions,

                COUNT(
                    DISTINCT p.subject_name
                ) AS total_categories


            FROM stocks s

            LEFT JOIN cards.product p
                ON p.nm_id = s.nm_id

            LEFT JOIN brands b
                ON b.nm_id = s.nm_id

            WHERE
                s.qty > 0
            """,
            {
                "report_date": report_date,
            },
        ).fetchone()


    return {
        "total_warehouses": total_warehouses,

        "total_on_hand": total_on_hand,

        "total_fbs": total_fbs,

        "total_in_transit": total_in_transit,

        "total_quantity": total_quantity,

        "total_products": (
            product_row[0]
            or 0
        ),

        "total_brands": (
            product_row[1]
            or 0
        ),

        "total_positions": (
            product_row[2]
            or 0
        ),

        "total_categories": (
            product_row[3]
            or 0
        ),

        "report_date": report_date,
    }


def get_stocks_by_warehouse_extended(report_date):
    with get_duckdb_conn_with_opt() as con:
        df = con.execute(
            """
            SELECT
                COALESCE(
                    region_name,
                    'Регион не указан'
                ) AS "регион",

                COUNT(
                    DISTINCT warehouse_name
                ) AS "складов",

                SUM(
                    COALESCE(
                        quantity,
                        0
                    )
                ) AS "на_складе",

                SUM(
                    COALESCE(
                        in_way_to_client,
                        0
                    )
                    +
                    COALESCE(
                        in_way_from_client,
                        0
                    )
                ) AS "в_пути",

                SUM(
                    COALESCE(
                        quantity,
                        0
                    )
                    +
                    COALESCE(
                        in_way_to_client,
                        0
                    )
                    +
                    COALESCE(
                        in_way_from_client,
                        0
                    )
                ) AS "итого"

            FROM stocks.unpacked_stocks

            WHERE
                date_from::DATE
                    = $report_date::DATE

            GROUP BY
                COALESCE(
                    region_name,
                    'Регион не указан'
                )

            ORDER BY
                "итого" DESC
            """,
            {
                "report_date": report_date,
            },
        ).df()

    return df




# def get_stocks_by_warehouse_products(report_date):
#     """
#     Детальные остатки в разрезе:

#         регион
#         -> склад
#         -> nm_id
#         -> chrt_id / размер

#     В лист попадает только физический остаток quantity.

#     Товары в пути не включаются, поскольку задача листа —
#     показать, какая номенклатура фактически находится
#     на конкретном складе и на какую сумму.

#     Себестоимость в запросе остаётся в копейках.
#     Перевод в рубли выполняется в excel.py.
#     """

#     with get_duckdb_conn_with_opt() as con:
#         df = con.execute(
#             """
#             WITH

#             /*
#             ============================================================
#             ОСТАТКИ ПО СКЛАДАМ И НОМЕНКЛАТУРЕ

#             Одна строка:
#                 регион
#                 + склад
#                 + nm_id
#                 + chrt_id

#             Суммируем строки заранее, чтобы последующие JOIN
#             не размножали количество.
#             ============================================================
#             */
#             warehouse_stocks AS (
#                 SELECT
#                     COALESCE(
#                         NULLIF(
#                             TRIM(t.region_name),
#                             ''
#                         ),
#                         'Регион не указан'
#                     ) AS region_name,

#                     COALESCE(
#                         NULLIF(
#                             TRIM(t.warehouse_name),
#                             ''
#                         ),
#                         'Склад не указан'
#                     ) AS warehouse_name,

#                     t.nm_id,
#                     t.chrt_id,

#                     SUM(
#                         COALESCE(
#                             t.quantity,
#                             0
#                         )
#                     ) AS quantity_on_hand

#                 FROM stocks.unpacked_stocks t

#                 WHERE
#                     t.date_from::DATE = $report_date::DATE

#                 GROUP BY
#                     COALESCE(
#                         NULLIF(
#                             TRIM(t.region_name),
#                             ''
#                         ),
#                         'Регион не указан'
#                     ),

#                     COALESCE(
#                         NULLIF(
#                             TRIM(t.warehouse_name),
#                             ''
#                         ),
#                         'Склад не указан'
#                     ),

#                     t.nm_id,
#                     t.chrt_id
#             ),


#             /*
#             ============================================================
#             КАРТА NM_ID -> USK

#             Дедуплицируем связь, чтобы не размножить остатки.
#             ============================================================
#             */
#             nm_usk AS (
#                 SELECT
#                     card_id AS nm_id,
#                     usk

#                 FROM inventories.usk

#                 WHERE
#                     card_id IS NOT NULL
#                     AND usk IS NOT NULL

#                 GROUP BY
#                     card_id,
#                     usk
#             ),


#             /*
#             ============================================================
#             ПОСЛЕДНЯЯ СЕБЕСТОИМОСТЬ ПО NM_ID

#             Повторяем логику основной выгрузки:
#             берём последнюю известную бухгалтерскую
#             и управленческую себестоимость.
#             ============================================================
#             */
#             costs AS (
#                 SELECT
#                     nu.nm_id,

#                     MAX(
#                         w.adjust_wo[-1]
#                     ) AS last_costs,

#                     MAX(
#                         w.adjust_man_wo[-1]
#                     ) AS last_man_costs

#                 FROM nm_usk nu

#                 LEFT JOIN inventories.pre_wo w
#                     ON w.usk = nu.usk

#                 GROUP BY
#                     nu.nm_id
#             ),


#             /*
#             ============================================================
#             БРЕНД

#             Отдельно агрегируем карточки по nm_id,
#             чтобы не размножить складские остатки.
#             ============================================================
#             */
#             brands AS (
#                 SELECT
#                     nm_id,

#                     COALESCE(
#                         MAX(brand),
#                         'Бренд не указан'
#                     ) AS brand

#                 FROM cards.unpacked_cards

#                 GROUP BY
#                     nm_id
#             )


#             SELECT
#                 ws.region_name
#                     AS "Регион",

#                 ws.warehouse_name
#                     AS "Склад",

#                 COALESCE(
#                     b.brand,
#                     'Бренд не указан'
#                 ) AS "Бренд",

#                 COALESCE(
#                     p.subject_name,
#                     'Категория не указана'
#                 ) AS "Категория",

#                 COALESCE(
#                     p.gender,
#                     'Пол не указан'
#                 ) AS "Пол",

#                 COALESCE(
#                     p.sa_name,
#                     ''
#                 ) AS "Артикул",

#                 COALESCE(
#                     p.title,
#                     ''
#                 ) AS "Наименование",

#                 COALESCE(
#                     sz.tech_size,
#                     ''
#                 ) AS "Размер",

#                 ws.quantity_on_hand
#                     AS "Остаток на складе",

#                 c.last_costs
#                     AS "Бух. с/с за ед.",

#                 c.last_man_costs
#                     AS "Упр. с/с за ед.",

#                 ws.quantity_on_hand
#                 * COALESCE(
#                     c.last_costs,
#                     0
#                 ) AS "Бух. стоимость остатка",

#                 ws.quantity_on_hand
#                 * COALESCE(
#                     c.last_man_costs,
#                     0
#                 ) AS "Упр. стоимость остатка",

#                 ws.nm_id
#                     AS "NM ID",

#                 ws.chrt_id
#                     AS "Chrt ID"

#             FROM warehouse_stocks ws

#             LEFT JOIN cards.product p
#                 ON p.nm_id = ws.nm_id

#             LEFT JOIN brands b
#                 ON b.nm_id = ws.nm_id

#             LEFT JOIN cards.sizes sz
#                 ON sz.chrt_id = ws.chrt_id

#             LEFT JOIN costs c
#                 ON c.nm_id = ws.nm_id

#             WHERE
#                 ws.quantity_on_hand > 0

#             ORDER BY
#                 ws.region_name,
#                 ws.warehouse_name,

#                 COALESCE(
#                     b.brand,
#                     'Бренд не указан'
#                 ),

#                 COALESCE(
#                     p.subject_name,
#                     'Категория не указана'
#                 ),

#                 COALESCE(
#                     p.title,
#                     ''
#                 ),

#                 COALESCE(
#                     sz.tech_size,
#                     ''
#                 )
#             """,
#             {
#                 "report_date": report_date,
#             },
#         ).df()

#     return df



def get_stocks_by_warehouse_products(report_date):
    """
    Детальные остатки в разрезе:

        регион
        -> склад
        -> nm_id
        -> chrt_id / размер

    В выгрузку включаются:

    - физический остаток на складе;
    - товары в пути от клиента;
    - товары в пути к клиенту;
    - итоговое количество.

    Одна строка соответствует:

        регион
        + склад
        + nm_id
        + chrt_id

    Себестоимость в запросе остаётся в копейках.
    Перевод в рубли выполняется в excel.py.

    Стоимость остатка рассчитывается по итоговому количеству,
    включая товары в пути — аналогично основному листу
    "Все товары".
    """

    with get_duckdb_conn_with_opt() as con:
        df = con.execute(
            """
            WITH

            /*
            ============================================================
            ОСТАТКИ ПО СКЛАДАМ И НОМЕНКЛАТУРЕ

            Одна строка:
                регион
                + склад
                + nm_id
                + chrt_id

            Суммируем данные до присоединения справочников,
            чтобы последующие JOIN не размножали количество.
            ============================================================
            */
            warehouse_stocks AS (
                SELECT
                    COALESCE(
                        NULLIF(
                            TRIM(t.region_name),
                            ''
                        ),
                        'Регион не указан'
                    ) AS region_name,

                    COALESCE(
                        NULLIF(
                            TRIM(t.warehouse_name),
                            ''
                        ),
                        'Склад не указан'
                    ) AS warehouse_name,

                    t.nm_id,
                    t.chrt_id,

                    SUM(
                        COALESCE(
                            t.quantity,
                            0
                        )
                    ) AS quantity_on_hand,

                    SUM(
                        COALESCE(
                            t.in_way_from_client,
                            0
                        )
                    ) AS in_way_from_client,

                    SUM(
                        COALESCE(
                            t.in_way_to_client,
                            0
                        )
                    ) AS in_way_to_client,

                    SUM(
                        COALESCE(
                            t.quantity,
                            0
                        )
                        +
                        COALESCE(
                            t.in_way_from_client,
                            0
                        )
                        +
                        COALESCE(
                            t.in_way_to_client,
                            0
                        )
                    ) AS total_quantity

                FROM stocks.unpacked_stocks t

                WHERE
                    t.date_from::DATE = $report_date::DATE

                GROUP BY
                    COALESCE(
                        NULLIF(
                            TRIM(t.region_name),
                            ''
                        ),
                        'Регион не указан'
                    ),

                    COALESCE(
                        NULLIF(
                            TRIM(t.warehouse_name),
                            ''
                        ),
                        'Склад не указан'
                    ),

                    t.nm_id,
                    t.chrt_id
            ),


            /*
            ============================================================
            КАРТА NM_ID -> USK

            Дедуплицируем связь, чтобы присоединение себестоимости
            не размножало складские остатки.
            ============================================================
            */
            nm_usk AS (
                SELECT
                    card_id AS nm_id,
                    usk

                FROM inventories.usk

                WHERE
                    card_id IS NOT NULL
                    AND usk IS NOT NULL

                GROUP BY
                    card_id,
                    usk
            ),


            """
            + COSTS_CTES_SQL
            + """,


            /*
            ============================================================
            БРЕНД

            Агрегируем карточки отдельно по nm_id,
            чтобы не размножить складские строки.
            ============================================================
            */
            brands AS (
                SELECT
                    nm_id,

                    COALESCE(
                        MAX(brand),
                        'Бренд не указан'
                    ) AS brand

                FROM cards.unpacked_cards

                GROUP BY
                    nm_id
            )


            /*
            ============================================================
            ИТОГОВАЯ ВЫГРУЗКА
            ============================================================
            */
            SELECT
                ws.region_name
                    AS "Регион",

                ws.warehouse_name
                    AS "Склад",

                COALESCE(
                    b.brand,
                    'Бренд не указан'
                ) AS "Бренд",

                COALESCE(
                    p.subject_name,
                    'Категория не указана'
                ) AS "Категория",

                COALESCE(
                    p.gender,
                    'Пол не указан'
                ) AS "Пол",

                COALESCE(
                    p.sa_name,
                    ''
                ) AS "Артикул",

                COALESCE(
                    p.title,
                    ''
                ) AS "Наименование",

                COALESCE(
                    sz.tech_size,
                    ''
                ) AS "Размер",


                /*
                --------------------------------------------------------
                КОЛИЧЕСТВО
                --------------------------------------------------------
                */
                ws.total_quantity
                    AS "Итого количество",

                ws.quantity_on_hand
                    AS "Остаток на складе",

                ws.in_way_from_client
                    AS "В пути от клиента",

                ws.in_way_to_client
                    AS "В пути к клиенту",


                /*
                --------------------------------------------------------
                СЕБЕСТОИМОСТЬ ЗА ЕДИНИЦУ
                --------------------------------------------------------
                */
                c.last_costs
                    AS "Бух. с/с за ед.",

                c.last_man_costs
                    AS "Упр. с/с за ед.",


                /*
                --------------------------------------------------------
                ОБЩАЯ СТОИМОСТЬ

                Считаем по итоговому количеству,
                включая товары в пути.
                --------------------------------------------------------
                */
                ws.total_quantity
                * COALESCE(
                    c.last_costs,
                    0
                ) AS "Бух. стоимость остатка",

                ws.total_quantity
                * COALESCE(
                    c.last_man_costs,
                    0
                ) AS "Упр. стоимость остатка",


                /*
                --------------------------------------------------------
                ТЕХНИЧЕСКИЕ ID
                --------------------------------------------------------
                */
                ws.nm_id
                    AS "NM ID",

                ws.chrt_id
                    AS "Chrt ID"

            FROM warehouse_stocks ws

            LEFT JOIN cards.product p
                ON p.nm_id = ws.nm_id

            LEFT JOIN brands b
                ON b.nm_id = ws.nm_id

            LEFT JOIN cards.sizes sz
                ON sz.chrt_id = ws.chrt_id

            LEFT JOIN costs c
                ON c.nm_id = ws.nm_id

            WHERE
                ws.total_quantity > 0

            ORDER BY
                ws.region_name,
                ws.warehouse_name,

                COALESCE(
                    b.brand,
                    'Бренд не указан'
                ),

                COALESCE(
                    p.subject_name,
                    'Категория не указана'
                ),

                COALESCE(
                    p.title,
                    ''
                ),

                COALESCE(
                    sz.tech_size,
                    ''
                )
            """,
            {
                "report_date": report_date,
            },
        ).df()

    return df


# def get_stock_dimension_distributions(
#     report_date,
#     brand_list=None,
#     cat_list=None,
#     gender_list=None,
# ):
#     """
#     Быстрая агрегированная аналитика остатков для dashboard-вкладок.

#     Возвращает два DataFrame:
#         brands, categories

#     Производительность:
#     - stocks.unpacked_stocks читается один раз;
#     - нет цикла по складам;
#     - карточки товара заранее дедуплицируются по nm_id;
#     - фильтры применяются внутри SQL;
#     - результат сразу агрегирован до уровня бренда / категории.

#     Показатели:
#     - on_hand: физический остаток;
#     - in_transit: в пути от клиента + к клиенту;
#     - total_qty: физический остаток + в пути;
#     - warehouses: количество складов присутствия;
#     - products: количество уникальных NM ID;
#     - share_pct: доля физического остатка;
#     - cumulative_share_pct: накопленная доля физического остатка;
#     - rank: место по физическому остатку.
#     """

#     def clean_filter(values):
#         return [
#             str(value).strip()
#             for value in (values or [])
#             if value is not None
#             and str(value).strip()
#         ]

#     brand_list = clean_filter(brand_list)
#     cat_list = clean_filter(cat_list)
#     gender_list = clean_filter(gender_list)

#     params = {
#         "report_date": report_date,
#     }
#     filters = []

#     def add_in_filter(column, values, prefix):
#         if not values:
#             return

#         placeholders = []
#         for index, value in enumerate(values):
#             key = f"{prefix}_{index}"
#             params[key] = value
#             placeholders.append(f"${key}")

#         filters.append(
#             f"{column} IN ({', '.join(placeholders)})"
#         )

#     add_in_filter(
#         "e.brand",
#         brand_list,
#         "brand",
#     )
#     add_in_filter(
#         "e.category",
#         cat_list,
#         "category",
#     )
#     add_in_filter(
#         "e.gender",
#         gender_list,
#         "gender",
#     )

#     filter_sql = (
#         " AND " + " AND ".join(filters)
#         if filters
#         else ""
#     )

#     query = f"""
#         WITH

#         /*
#         ================================================================
#         ОСТАТКИ ДО УРОВНЯ СКЛАД + NM_ID

#         Размеры предварительно суммируются, поэтому последующие JOIN
#         не размножают складские количества.
#         ================================================================
#         */
#         stock_by_warehouse_nm AS (
#             SELECT
#                 COALESCE(
#                     NULLIF(TRIM(t.warehouse_name), ''),
#                     'Склад не указан'
#                 ) AS warehouse,

#                 t.nm_id,

#                 SUM(
#                     COALESCE(t.quantity, 0)
#                 ) AS on_hand,

#                 SUM(
#                     COALESCE(t.in_way_from_client, 0)
#                     + COALESCE(t.in_way_to_client, 0)
#                 ) AS in_transit

#             FROM stocks.unpacked_stocks t

#             WHERE
#                 t.date_from::DATE = $report_date::DATE
#                 AND t.nm_id IS NOT NULL

#             GROUP BY
#                 COALESCE(
#                     NULLIF(TRIM(t.warehouse_name), ''),
#                     'Склад не указан'
#                 ),
#                 t.nm_id
#         ),

#         /*
#         ================================================================
#         БРЕНД: строго одна строка на NM_ID
#         ================================================================
#         */
#         brands AS (
#             SELECT
#                 nm_id,
#                 COALESCE(
#                     NULLIF(TRIM(MAX(brand)), ''),
#                     'Бренд не указан'
#                 ) AS brand

#             FROM cards.unpacked_cards

#             WHERE nm_id IS NOT NULL

#             GROUP BY nm_id
#         ),

#         /*
#         ================================================================
#         КАРТОЧКА: строго одна строка на NM_ID

#         MAX используется намеренно как защита от возможных дублей
#         справочника cards.product.
#         ================================================================
#         */
#         products AS (
#             SELECT
#                 nm_id,

#                 COALESCE(
#                     NULLIF(TRIM(MAX(subject_name)), ''),
#                     'Категория не указана'
#                 ) AS category,

#                 COALESCE(
#                     NULLIF(TRIM(MAX(gender)), ''),
#                     'Пол не указан'
#                 ) AS gender

#             FROM cards.product

#             WHERE nm_id IS NOT NULL

#             GROUP BY nm_id
#         ),

#         /*
#         ================================================================
#         ОБОГАЩЁННЫЕ СКЛАДСКИЕ ОСТАТКИ
#         ================================================================
#         */
#         enriched AS (
#             SELECT
#                 s.warehouse,
#                 s.nm_id,

#                 COALESCE(
#                     b.brand,
#                     'Бренд не указан'
#                 ) AS brand,

#                 COALESCE(
#                     p.category,
#                     'Категория не указана'
#                 ) AS category,

#                 COALESCE(
#                     p.gender,
#                     'Пол не указан'
#                 ) AS gender,

#                 s.on_hand,
#                 s.in_transit,
#                 s.on_hand + s.in_transit AS total_qty

#             FROM stock_by_warehouse_nm s

#             LEFT JOIN brands b
#                 ON b.nm_id = s.nm_id

#             LEFT JOIN products p
#                 ON p.nm_id = s.nm_id
#         ),

#         /*
#         ================================================================
#         БРЕНДЫ
#         ================================================================
#         */
#         brand_distribution AS (
#             SELECT
#                 'brand' AS dimension,
#                 e.brand AS name,

#                 SUM(e.on_hand) AS on_hand,
#                 SUM(e.in_transit) AS in_transit,
#                 SUM(e.total_qty) AS total_qty,

#                 COUNT(
#                     DISTINCT CASE
#                         WHEN e.total_qty > 0
#                         THEN e.warehouse
#                     END
#                 ) AS warehouses,

#                 COUNT(
#                     DISTINCT CASE
#                         WHEN e.total_qty > 0
#                         THEN e.nm_id
#                     END
#                 ) AS products

#             FROM enriched e

#             WHERE
#                 e.total_qty > 0
#                 {filter_sql}

#             GROUP BY e.brand
#         ),

#         /*
#         ================================================================
#         КАТЕГОРИИ
#         ================================================================
#         */
#         category_distribution AS (
#             SELECT
#                 'category' AS dimension,
#                 e.category AS name,

#                 SUM(e.on_hand) AS on_hand,
#                 SUM(e.in_transit) AS in_transit,
#                 SUM(e.total_qty) AS total_qty,

#                 COUNT(
#                     DISTINCT CASE
#                         WHEN e.total_qty > 0
#                         THEN e.warehouse
#                     END
#                 ) AS warehouses,

#                 COUNT(
#                     DISTINCT CASE
#                         WHEN e.total_qty > 0
#                         THEN e.nm_id
#                     END
#                 ) AS products

#             FROM enriched e

#             WHERE
#                 e.total_qty > 0
#                 {filter_sql}

#             GROUP BY e.category
#         )

#         SELECT *
#         FROM brand_distribution

#         UNION ALL

#         SELECT *
#         FROM category_distribution

#         ORDER BY
#             dimension,
#             on_hand DESC,
#             name
#     """

#     with get_duckdb_conn_with_opt() as con:
#         result = con.execute(
#             query,
#             params,
#         ).df()

#     empty_columns = [
#         "name",
#         "on_hand",
#         "in_transit",
#         "total_qty",
#         "warehouses",
#         "products",
#         "share_pct",
#         "cumulative_share_pct",
#         "rank",
#     ]

#     if result.empty:
#         import pandas as pd

#         empty = pd.DataFrame(
#             columns=empty_columns
#         )
#         return empty.copy(), empty.copy()

#     def prepare_dimension(dimension):
#         frame = (
#             result[
#                 result["dimension"] == dimension
#             ]
#             .drop(
#                 columns=["dimension"]
#             )
#             .copy()
#         )

#         numeric_columns = [
#             "on_hand",
#             "in_transit",
#             "total_qty",
#             "warehouses",
#             "products",
#         ]

#         for column in numeric_columns:
#             frame[column] = frame[column].fillna(0)

#         frame = (
#             frame[
#                 frame["total_qty"] > 0
#             ]
#             .sort_values(
#                 ["on_hand", "total_qty", "name"],
#                 ascending=[False, False, True],
#             )
#             .reset_index(drop=True)
#         )

#         physical_total = float(
#             frame["on_hand"].sum()
#         )

#         frame["share_pct"] = (
#             frame["on_hand"]
#             / physical_total
#             * 100
#             if physical_total > 0
#             else 0.0
#         )

#         frame["cumulative_share_pct"] = (
#             frame["share_pct"].cumsum()
#         )

#         frame["rank"] = frame.index + 1

#         return frame[empty_columns]

#     return (
#         prepare_dimension("brand"),
#         prepare_dimension("category"),
#     )



def get_stock_dimension_distributions(
    report_date,
    brand_list=None,
    cat_list=None,
    gender_list=None,
):
    """
    Быстрая агрегированная аналитика остатков для dashboard-вкладок.

    Возвращает:
        brands, categories

    Логика показателей:
    - on_hand:
        физический остаток на складах;

    - in_transit:
        в пути от клиента + в пути к клиенту;

    - total_qty:
        физический остаток + весь товар в пути;

    - warehouses:
        количество складов присутствия;

    - products:
        количество уникальных NM ID;

    - share_pct:
        доля бренда / категории в общем количестве total_qty;

    - cumulative_share_pct:
        накопленная доля total_qty;

    - rank:
        место по total_qty.

    Производительность:
    - stocks.unpacked_stocks читается один раз;
    - нет цикла по складам;
    - данные сначала агрегируются до склад + nm_id;
    - справочники дедуплицируются до одной строки на nm_id;
    - фильтры применяются внутри SQL;
    - результат сразу агрегируется по брендам и категориям.
    """

    import pandas as pd

    def clean_filter(values):
        return [
            str(value).strip()
            for value in (values or [])
            if value is not None
            and str(value).strip()
        ]

    brand_list = clean_filter(
        brand_list
    )
    cat_list = clean_filter(
        cat_list
    )
    gender_list = clean_filter(
        gender_list
    )

    params = {
        "report_date": report_date,
    }

    filters = []

    def add_in_filter(
        column,
        values,
        prefix,
    ):
        if not values:
            return

        placeholders = []

        for index, value in enumerate(values):
            key = f"{prefix}_{index}"

            params[key] = value

            placeholders.append(
                f"${key}"
            )

        filters.append(
            f"{column} IN "
            f"({', '.join(placeholders)})"
        )

    add_in_filter(
        column="e.brand",
        values=brand_list,
        prefix="brand",
    )

    add_in_filter(
        column="e.category",
        values=cat_list,
        prefix="category",
    )

    add_in_filter(
        column="e.gender",
        values=gender_list,
        prefix="gender",
    )

    filter_sql = (
        " AND " + " AND ".join(filters)
        if filters
        else ""
    )

    query = f"""
        WITH

        /*
        ================================================================
        ОСТАТКИ НА УРОВНЕ:

            СКЛАД + NM_ID

        Все размеры одного NM ID на одном складе предварительно
        суммируются. Поэтому последующие JOIN не размножают остатки.
        ================================================================
        */
        stock_by_warehouse_nm AS (
            SELECT
                COALESCE(
                    NULLIF(
                        TRIM(t.warehouse_name),
                        ''
                    ),
                    'Склад не указан'
                ) AS warehouse,

                t.nm_id,

                SUM(
                    COALESCE(
                        t.quantity,
                        0
                    )
                ) AS on_hand,

                SUM(
                    COALESCE(
                        t.in_way_from_client,
                        0
                    )
                    +
                    COALESCE(
                        t.in_way_to_client,
                        0
                    )
                ) AS in_transit,

                SUM(
                    COALESCE(
                        t.quantity,
                        0
                    )
                    +
                    COALESCE(
                        t.in_way_from_client,
                        0
                    )
                    +
                    COALESCE(
                        t.in_way_to_client,
                        0
                    )
                ) AS total_qty

            FROM stocks.unpacked_stocks t

            WHERE
                t.date_from::DATE
                    = $report_date::DATE

                AND t.nm_id IS NOT NULL

            GROUP BY
                COALESCE(
                    NULLIF(
                        TRIM(t.warehouse_name),
                        ''
                    ),
                    'Склад не указан'
                ),

                t.nm_id
        ),


        /*
        ================================================================
        БРЕНД

        Строго одна строка на NM ID.
        ================================================================
        */
        brands AS (
            SELECT
                nm_id,

                COALESCE(
                    NULLIF(
                        TRIM(
                            MAX(brand)
                        ),
                        ''
                    ),
                    'Бренд не указан'
                ) AS brand

            FROM cards.unpacked_cards

            WHERE
                nm_id IS NOT NULL

            GROUP BY
                nm_id
        ),


        /*
        ================================================================
        КАТЕГОРИЯ И ПОЛ

        Строго одна строка на NM ID.
        ================================================================
        */
        products AS (
            SELECT
                nm_id,

                COALESCE(
                    NULLIF(
                        TRIM(
                            MAX(subject_name)
                        ),
                        ''
                    ),
                    'Категория не указана'
                ) AS category,

                COALESCE(
                    NULLIF(
                        TRIM(
                            MAX(gender)
                        ),
                        ''
                    ),
                    'Пол не указан'
                ) AS gender

            FROM cards.product

            WHERE
                nm_id IS NOT NULL

            GROUP BY
                nm_id
        ),


        /*
        ================================================================
        ОБОГАЩЁННЫЕ ОСТАТКИ
        ================================================================
        */
        enriched AS (
            SELECT
                s.warehouse,
                s.nm_id,

                COALESCE(
                    b.brand,
                    'Бренд не указан'
                ) AS brand,

                COALESCE(
                    p.category,
                    'Категория не указана'
                ) AS category,

                COALESCE(
                    p.gender,
                    'Пол не указан'
                ) AS gender,

                s.on_hand,
                s.in_transit,
                s.total_qty

            FROM stock_by_warehouse_nm s

            LEFT JOIN brands b
                ON b.nm_id = s.nm_id

            LEFT JOIN products p
                ON p.nm_id = s.nm_id
        ),


        /*
        ================================================================
        РАСПРЕДЕЛЕНИЕ ПО БРЕНДАМ
        ================================================================
        */
        brand_distribution AS (
            SELECT
                'brand' AS dimension,

                e.brand AS name,

                SUM(
                    e.on_hand
                ) AS on_hand,

                SUM(
                    e.in_transit
                ) AS in_transit,

                SUM(
                    e.total_qty
                ) AS total_qty,

                COUNT(
                    DISTINCT CASE
                        WHEN e.total_qty > 0
                        THEN e.warehouse
                    END
                ) AS warehouses,

                COUNT(
                    DISTINCT CASE
                        WHEN e.total_qty > 0
                        THEN e.nm_id
                    END
                ) AS products

            FROM enriched e

            WHERE
                e.total_qty > 0
                {filter_sql}

            GROUP BY
                e.brand
        ),


        /*
        ================================================================
        РАСПРЕДЕЛЕНИЕ ПО КАТЕГОРИЯМ
        ================================================================
        */
        category_distribution AS (
            SELECT
                'category' AS dimension,

                e.category AS name,

                SUM(
                    e.on_hand
                ) AS on_hand,

                SUM(
                    e.in_transit
                ) AS in_transit,

                SUM(
                    e.total_qty
                ) AS total_qty,

                COUNT(
                    DISTINCT CASE
                        WHEN e.total_qty > 0
                        THEN e.warehouse
                    END
                ) AS warehouses,

                COUNT(
                    DISTINCT CASE
                        WHEN e.total_qty > 0
                        THEN e.nm_id
                    END
                ) AS products

            FROM enriched e

            WHERE
                e.total_qty > 0
                {filter_sql}

            GROUP BY
                e.category
        )


        SELECT
            dimension,
            name,
            on_hand,
            in_transit,
            total_qty,
            warehouses,
            products

        FROM brand_distribution


        UNION ALL


        SELECT
            dimension,
            name,
            on_hand,
            in_transit,
            total_qty,
            warehouses,
            products

        FROM category_distribution


        ORDER BY
            dimension,
            total_qty DESC,
            name
    """

    with get_duckdb_conn_with_opt() as con:
        result = con.execute(
            query,
            params,
        ).df()

    output_columns = [
        "name",
        "on_hand",
        "in_transit",
        "total_qty",
        "warehouses",
        "products",
        "share_pct",
        "cumulative_share_pct",
        "rank",
    ]

    if result.empty:
        empty = pd.DataFrame(
            columns=output_columns
        )

        return (
            empty.copy(),
            empty.copy(),
        )

    def prepare_dimension(
        dimension,
    ):
        frame = (
            result[
                result["dimension"] == dimension
            ]
            .drop(
                columns=[
                    "dimension",
                ]
            )
            .copy()
        )

        numeric_columns = [
            "on_hand",
            "in_transit",
            "total_qty",
            "warehouses",
            "products",
        ]

        for column in numeric_columns:
            frame[column] = pd.to_numeric(
                frame[column],
                errors="coerce",
            ).fillna(0)

        frame["name"] = (
            frame["name"]
            .fillna("Не указано")
            .astype(str)
            .str.strip()
            .replace(
                "",
                "Не указано",
            )
        )

        frame = (
            frame[
                frame["total_qty"] > 0
            ]
            .sort_values(
                by=[
                    "total_qty",
                    "on_hand",
                    "name",
                ],
                ascending=[
                    False,
                    False,
                    True,
                ],
            )
            .reset_index(
                drop=True
            )
        )

        total_quantity = float(
            frame["total_qty"].sum()
        )

        if total_quantity > 0:
            frame["share_pct"] = (
                frame["total_qty"]
                / total_quantity
                * 100
            )
        else:
            frame["share_pct"] = 0.0

        frame["cumulative_share_pct"] = (
            frame["share_pct"]
            .cumsum()
        )

        frame["rank"] = (
            frame.index + 1
        )

        return frame[
            output_columns
        ]

    brands = prepare_dimension(
        "brand"
    )

    categories = prepare_dimension(
        "category"
    )

    return (
        brands,
        categories,
    )




def get_warehouse_incident_stock_items(warehouse_name, report_date):
    """
    Постатейная детализация ФИЗИЧЕСКОГО остатка одного склада на дату —
    для оценки товарного ущерба при происшествии (пожаре).

    Использует тот же источник, что и общая выгрузка по складам
    (get_stocks_by_warehouse_products), но:

    - фильтрует строго по одному складу;
    - берёт только физический остаток ("Остаток на складе"),
      БЕЗ товаров в пути;
    - переводит себестоимость из копеек в рубли (в этой выгрузке
      она остаётся в копейках, см. docstring get_stocks_export_data).

    ВАЖНО про себестоимость: она считается единой методикой
    COSTS_CTES_SQL (основной источник — приходные УПД, тот же,
    что в costs_control; резерв — последнее списание из pre_wo).
    Подробности и причина отказа от pre_wo как основного
    источника — в комментарии к константе в начале файла.

    Единицы: SQL отдаёт копейки, наружу функция отдаёт РУБЛИ.

    0 и "данных нет" здесь по-прежнему считаются ОДНИМ И ТЕМ ЖЕ
    ("нет с/с"): incident_loss_export.py помечает такие позиции
    в колонке "Без с/с" по значению 0. После перехода на УПД
    туда должны попадать только товары вообще без приходов.

    Возвращает список словарей — пригоден для передачи как
    event["items"] в incident_loss_export.build_incident_loss_excel:

        {
            "nm_id": ...,
            "name": ...,
            "brand": ...,
            "size": ...,
            "qty": ...,                     # физический остаток, шт
            "accounting_unit_cost": ...,    # ₽ за единицу (0, если нет данных)
            "management_unit_cost": ...,    # ₽ за единицу (0, если нет данных)
            #   ^ рубли, НЕ копейки
        }
    """

    import pandas as pd

    def _safe_str(value, default=""):
        if value is None:
            return default
        try:
            if pd.isna(value):
                return default
        except (TypeError, ValueError):
            pass
        return str(value)

    def _safe_float(value, default=0.0):
        if value is None:
            return default
        try:
            if pd.isna(value):
                return default
        except (TypeError, ValueError):
            pass
        try:
            return float(value)
        except (TypeError, ValueError):
            return default

    def _safe_scalar(value):
        if value is None:
            return None
        try:
            if pd.isna(value):
                return None
        except (TypeError, ValueError):
            pass
        return value

    df = get_stocks_by_warehouse_products(report_date)

    if df is None or df.empty:
        return []

    target = str(warehouse_name or "").strip()

    # pd.to_numeric(...).fillna(0) — чтобы сравнение "> 0" не споткнулось
    # о NA внутри булевой маски (прямое df[col] > 0 на nullable Int64
    # с пропусками кидает "Cannot mask with non-boolean array
    # containing NA / NaN values").
    on_hand_numeric = pd.to_numeric(
        df["Остаток на складе"],
        errors="coerce",
    ).fillna(0)

    mask = (
        df["Склад"].astype(str).str.strip() == target
    ) & (
        on_hand_numeric > 0
    )

    df = df.loc[mask].copy()

    if df.empty:
        return []

    items = []

    for _, row in df.iterrows():
        # Себестоимость уже посчитана в SQL по единой методике
        # (COSTS_CTES_SQL: приходные УПД, резерв — списания)
        # и приходит в копейках — здесь только перевод в рубли.
        acc_kopecks = _safe_float(row.get("Бух. с/с за ед."))
        mgmt_kopecks = _safe_float(row.get("Упр. с/с за ед."))

        acc_unit = acc_kopecks / 100.0
        mgmt_unit = mgmt_kopecks / 100.0

        items.append(
            {
                "nm_id": _safe_scalar(row.get("NM ID")),
                "name": _safe_str(row.get("Наименование")),
                "brand": _safe_str(row.get("Бренд")),
                "size": _safe_str(row.get("Размер")),
                "qty": _safe_float(row.get("Остаток на складе")),
                "accounting_unit_cost": acc_unit,
                "management_unit_cost": mgmt_unit,
            }
        )

    return items