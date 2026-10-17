import pandas as pd
from conns import ENGINE

# наши данные


def get_our_data():
    q = """
    select t.*,
        t.sale_dt::date as sale_date,
        t.order_dt::date as order_date,
        son.name as son,
        dt.name as doc_type,
        pp.name as pmt_processing,
        nms.name as nm_name


        from wb_dwh.realization_kv t
        left join wb_dwh.dim_supplier_oper as son on son.id=t.son_id
        left join wb_dwh.payment_processing as pp on t.pmt_processing_id = pp.id
        left join wb_dwh.dim_doc_type as dt on dt.id = t.dtn_id
        left join public.sales_nms as nms on t.nm_id = nms.nm_id

        where t.rr_dt >='2026-02-20' and t.rr_dt < '2026-02-21'        
        and quantity <> 2 
        
        
    """
    return pd.read_sql(q, ENGINE)


def get_wb_fact(file="/Users/pavelustenko/Downloads/feb21.xlsx"):
    return pd.read_excel(file)




wb_cols = [
    "№",
    "Номер поставки",
    "Предмет",
    "Код номенклатуры",
    "Бренд",
    "Артикул поставщика",
    "Название",
    "Размер",
    "Баркод",
    "Тип документа",
    "Обоснование для оплаты",
    "Дата заказа покупателем",
    "Дата продажи",
    "Кол-во",
    "Цена розничная",
    "Вайлдберриз реализовал Товар (Пр)",
    "Согласованный продуктовый дисконт, %",
    "Промокод, %",
    "Итоговая согласованная скидка, %",
    "Цена розничная с учетом согласованной скидки",
    "Размер снижения кВВ из-за рейтинга, %",
    "Размер изменения кВВ из-за акции, %",
    "Скидка постоянного Покупателя (СПП), %",
    "Размер кВВ, %",
    "Размер кВВ без НДС, % Базовый",
    "Итоговый кВВ без НДС, %",
    "Вознаграждение с продаж до вычета услуг поверенного, без НДС",
    "Возмещение за выдачу и возврат товаров на ПВЗ",
    "Эквайринг/Комиссии за организацию платежей",
    "Размер комиссии за эквайринг/Комиссии за организацию платежей, %",
    "Тип платежа за Эквайринг/Комиссии за организацию платежей",
    "Вознаграждение Вайлдберриз (ВВ), без НДС",
    "НДС с Вознаграждения Вайлдберриз",
    "К перечислению Продавцу за реализованный Товар",
    "Количество доставок",
    "Количество возврата",
    "Услуги по доставке товара покупателю",
    "Дата начала действия фиксации",
    "Дата конца действия фиксации",
    "Признак услуги платной доставки",
    "Общая сумма штрафов",
    "Корректировка Вознаграждения Вайлдберриз (ВВ)",
    "Виды логистики, штрафов и корректировок ВВ",
    "Стикер МП",
    "Наименование банка-эквайера",
    "Номер офиса",
    "Наименование офиса доставки",
    "ИНН партнера",
    "Партнер",
    "Склад",
    "Страна",
    "Тип коробов",
    "Номер таможенной декларации",
    "Номер сборочного задания",
    "Код маркировки",
    "ШК",
    "Srid",
    "Возмещение издержек по перевозке/по складским операциям с товаром",
    "Организатор перевозки",
    "Хранение",
    "Удержания",
    "Операции на приемке",
    "Фиксированный коэффициент склада по поставке",
    "Признак продажи юридическому лицу",
    "Номер короба для обработки товара",
    "Скидка по программе софинансирования",
    "Скидка Wibes, %",
    "Компенсация скидки по программе лояльности",
    "Стоимость участия в программе лояльности",
    "Сумма удержанная за начисленные баллы программы лояльности",
    "Id корзины заказа",
    "Разовое изменение срока перечисления денежных средств",
    "Id собственной акции продавца с дополнительной скидкой",
    "Размер дополнительной скидки по собственной акции продавца, %",
    "Способы продажи и тип товара",
    "Уникальный идентификатор скидки лояльности от продавца",
    "Размер скидки лояльности от продавца,%",
    "Id промокода",
    "Скидка за промокод, %",
]

ren = {
    "Дата продажи":"sale_date",
    "Код номенклатуры":"nm_id",
    "Кол-во":"quantity",
    "Удержания":"deduction",
    "Вайлдберриз реализовал Товар (Пр)":"retail_amount",
    "К перечислению Продавцу за реализованный Товар":"ppvz_for_pay",
    "Тип документа":"doc_type",
    "Srid":"srid"
}




cols_list = [
    "date_from",
    "date_to",
    "rr_dt",
    "sale_dt",
    "order_dt",
    "create_dt",
    "rrd_id",
    "nm_id",
    "realizationreport_id",
    "sa_name",
    "shk_id",
    "report_type",
    "barcode",
    "srid",
    "ts_name",
    "currency_name",
    "bonus_type_name",
    "quantity",
    "is_legal_entity",
    "ppvz_kvw_prc",
    "ppvz_spp_prc",
    "sale_percent",
    "acquiring_percent",
    "ppvz_kvw_prc_base",
    "commission_percent",
    "country_id",
    "son_id",
    "dtn_id",
    "pmt_processing_id",
    "loaded_at",
    "son",
    "doc_type",
    "pmt_processing",
    "nm_name",
    #  'field', 'value',
]





df = get_our_data()
wide = (
    df.set_index(["rrd_id", "field"])["value"]
      .unstack("field")      
)



df_noms = df[["rrd_id", "nm_id","quantity","dtn_id","son_id","sale_date","doc_type",'srid']].drop_duplicates()

fin_our_df = wide.merge(df_noms, on="rrd_id", how="left").fillna(0)

comp_cols = [#'rrd_id',
             'nm_id',
            'quantity',
            'deduction',
            'retail_amount',
            'ppvz_for_pay',
            'doc_type',
            'sale_date',
            'srid']

df_wb = get_wb_fact()

df_wb = df_wb[df_wb['Кол-во']!=2].fillna(0)

print(len(wide))
print(len(df_wb))


# df_wb = df_wb.rename(columns=ren)
# our_df = fin_our_df[comp_cols].copy()
# wb_df  = df_wb[comp_cols].copy()

# our_df_filterd = our_df[our_df['doc_type']=='Продажа']
# wb_df_filterd = wb_df[wb_df['doc_type']=='Продажа']

# # our_df_filterd['nm_id'] =  our_df_filterd['nm_id'].astype(str)

# our_df_filterd['df_type'] = 'our'

# wb_df_filterd['df_type'] = 'wb'

# df_join = pd.concat([our_df_filterd,wb_df_filterd],ignore_index=True) 

# df_pivot = df_join.pivot_table(
#     index='nm_id',
#     columns='df_type',
#     values='retail_amount',
#     aggfunc='count'
# )

# df_pivot['our'] = df_pivot['our']
# df_pivot['diff'] = df_pivot['our'] - df_pivot['wb']


# df_diff = df_pivot[df_pivot['diff'].isna()]

# print(df_diff.index.to_list())
# print(df_diff)

# def make_set(df, cols):
#     s = set()
#     for _, r in df.iterrows():
#         key = "|".join(
#             str(r[c]).strip() if pd.notna(r[c]) else ""
#             for c in cols
#         )
#         s.add(key)
#     return s

# our_set = make_set(our_df, comp_cols)
# wb_set  = make_set(wb_df, comp_cols)

# missing = our_set - wb_set

# print("Строк нет в WB:", len(missing))

# # если надо обратно в df
# missing_df = pd.DataFrame(
#     [x.split("|") for x in missing],
#     columns=comp_cols
# )

# print(missing_df.head(20))

# fin_our_df = fin_our_df[fin_our_df['quantity']!=2]

# print(len(fin_our_df))
# print(len(df_wb))

# our_counts = (
#     fin_our_df.groupby("nm_id")
#       .size()
#       .reset_index(name="count_our")
# )

# # 2️⃣ WB: Код номенклатуры → количество строк
# wb_counts = (
#     df_wb.groupby("Код номенклатуры")
#          .size()
#          .reset_index(name="count_wb")
#          .rename(columns={"Код номенклатуры": "nm_id"})
# )


# # 3️⃣ Приводим типы
# our_counts["nm_id"] = our_counts["nm_id"].astype(str)
# wb_counts["nm_id"] = wb_counts["nm_id"].astype(str)

# # 4️⃣ Merge
# recon = our_counts.merge(wb_counts, on="nm_id", how="outer")

# # 5️⃣ Заполняем NaN нулями
# recon[["count_our", "count_wb"]] = recon[["count_our", "count_wb"]].fillna(0)

# recon[["count_our", "count_wb"]] = recon[["count_our", "count_wb"]].fillna(0)

# # 6️⃣ Разница
# recon["diff"] = recon["count_our"] - recon["count_wb"]

# df_dif = recon.loc[recon["diff"].ne(0)].sort_values("diff", ascending=False)

# print(df_dif)

# # sum_return = df_wb[df_wb['Тип документа'] == 'Возврат']
# # r = sum_return['Вайлдберриз реализовал Товар (Пр)'].sum()

# # sum_sale = df_wb[df_wb['Тип документа'] == 'Продажа']
# # s = sum_sale['Вайлдберриз реализовал Товар (Пр)'].sum()

# # wb_sale = sum_sale - sum_return
# # print('wb_sale', wb_sale)

# sum_return = df_wb[df_wb['Тип документа'] == 'Возврат']
# sum_return['К перечислению Продавцу за реализованный Товар'].sum()


# sum_sale = df_wb[df_wb['Тип документа'] == 'Продажа']
# sum_sale['К перечислению Продавцу за реализованный Товар'].sum()


# wb_sale = sum_sale - sum_return
# print('for pay', wb_sale)


# sum_return = df_wb[df_wb['Тип документа'] == 'Возврат']
# print(sum_return['Компенсация скидки по программе лояльности'].sum())

# sum_sale = df_wb[df_wb['Тип документа'] == 'Продажа']
# print(sum_sale['Компенсация скидки по программе лояльности'].sum())

# print(df_wb["Удержания"].sum())

# sum_return = df_wb[df_wb['Тип документа'] == 'Возврат']
# print(sum_return['Стоимость участия в программе лояльности'].sum())

# sum_sale = df_wb[df_wb['Тип документа'] == 'Продажа']
# print(sum_sale['Стоимость участия в программе лояльности'].sum())


# sum_return = df_wb[df_wb['Тип документа'] == 'Возврат']
# print(sum_return['Сумма удержанная за начисленные баллы программы лояльности'].sum())

# sum_sale = df_wb[df_wb['Тип документа'] == 'Продажа']
# print(sum_sale['Сумма удержанная за начисленные баллы программы лояльности'].sum())

print('+++++ OUR +++++++')


sum_return = fin_our_df[fin_our_df['dtn_id'] == 1]
r = sum_return['retail_amount'].sum()
sum_sale = fin_our_df[fin_our_df['dtn_id'] == 2]
s = sum_sale['retail_amount'].sum()

print('our_sale', s-r )

sum_return = fin_our_df[fin_our_df['dtn_id'] == 1]
r = sum_return['ppvz_for_pay'].sum()
sum_sale = fin_our_df[fin_our_df['dtn_id'] == 2]
s = sum_sale['ppvz_for_pay'].sum()

print('our_for_pay', s-r )

l = fin_our_df['delivery_rub'].sum()
d = fin_our_df['deduction'].sum()
p = fin_our_df['penalty'].sum()
a = fin_our_df['additional_payment'].sum()

print(l)
print(d)
print(p)
print(a)



# sum_sale = df_wb[df_wb['Тип документа'] == 'Продажа']
# print(sum_sale['Вайлдберриз реализовал Товар (Пр)'].sum())

# sum_return = df_wb[df_wb['Тип документа'] == 'Возврат']
# print(sum_return['К перечислению Продавцу за реализованный Товар'].sum())

# sum_sale = df_wb[df_wb['Тип документа'] == 'Продажа']
# print(sum_sale['К перечислению Продавцу за реализованный Товар'].sum())

# sum_return = df_wb[df_wb['Тип документа'] == 'Возврат']
# print(sum_return['Компенсация скидки по программе лояльности'].sum())

# sum_sale = df_wb[df_wb['Тип документа'] == 'Продажа']
# print(sum_sale['Компенсация скидки по программе лояльности'].sum())

# print(df_wb["Удержания"].sum())

# sum_return = df_wb[df_wb['Тип документа'] == 'Возврат']
# print(sum_return['Стоимость участия в программе лояльности'].sum())

# sum_sale = df_wb[df_wb['Тип документа'] == 'Продажа']
# print(sum_sale['Стоимость участия в программе лояльности'].sum())


# sum_return = df_wb[df_wb['Тип документа'] == 'Возврат']
# print(sum_return['Сумма удержанная за начисленные баллы программы лояльности'].sum())

# sum_sale = df_wb[df_wb['Тип документа'] == 'Продажа']
# print(sum_sale['Сумма удержанная за начисленные баллы программы лояльности'].sum())


# print(df_wb["Стоимость участия в программе лояльности"].sum())

# print(df_wb["Сумма удержанная за начисленные баллы программы лояльности"].sum())



wb_cols = [
    "№",
    "Номер поставки",
    "Предмет",
    "Код номенклатуры",
    "Бренд",
    "Артикул поставщика",
    "Название",
    "Размер",
    "Баркод",
    "Тип документа",
    "Обоснование для оплаты",
    "Дата заказа покупателем",
    "Дата продажи",
    "Кол-во",
    "Цена розничная",
    "Вайлдберриз реализовал Товар (Пр)",
    "Согласованный продуктовый дисконт, %",
    "Промокод, %",
    "Итоговая согласованная скидка, %",
    "Цена розничная с учетом согласованной скидки",
    "Размер снижения кВВ из-за рейтинга, %",
    "Размер изменения кВВ из-за акции, %",
    "Скидка постоянного Покупателя (СПП), %",
    "Размер кВВ, %",
    "Размер кВВ без НДС, % Базовый",
    "Итоговый кВВ без НДС, %",
    "Вознаграждение с продаж до вычета услуг поверенного, без НДС",
    "Возмещение за выдачу и возврат товаров на ПВЗ",
    "Эквайринг/Комиссии за организацию платежей",
    "Размер комиссии за эквайринг/Комиссии за организацию платежей, %",
    "Тип платежа за Эквайринг/Комиссии за организацию платежей",
    "Вознаграждение Вайлдберриз (ВВ), без НДС",
    "НДС с Вознаграждения Вайлдберриз",
    "К перечислению Продавцу за реализованный Товар",
    "Количество доставок",
    "Количество возврата",
    "Услуги по доставке товара покупателю",
    "Дата начала действия фиксации",
    "Дата конца действия фиксации",
    "Признак услуги платной доставки",
    "Общая сумма штрафов",
    "Корректировка Вознаграждения Вайлдберриз (ВВ)",
    "Виды логистики, штрафов и корректировок ВВ",
    "Стикер МП",
    "Наименование банка-эквайера",
    "Номер офиса",
    "Наименование офиса доставки",
    "ИНН партнера",
    "Партнер",
    "Склад",
    "Страна",
    "Тип коробов",
    "Номер таможенной декларации",
    "Номер сборочного задания",
    "Код маркировки",
    "ШК",
    "Srid",
    "Возмещение издержек по перевозке/по складским операциям с товаром",
    "Организатор перевозки",
    "Хранение",
    "Удержания",
    "Операции на приемке",
    "Фиксированный коэффициент склада по поставке",
    "Признак продажи юридическому лицу",
    "Номер короба для обработки товара",
    "Скидка по программе софинансирования",
    "Скидка Wibes, %",
    "Компенсация скидки по программе лояльности",
    "Стоимость участия в программе лояльности",
    "Сумма удержанная за начисленные баллы программы лояльности",
    "Id корзины заказа",
    "Разовое изменение срока перечисления денежных средств",
    "Id собственной акции продавца с дополнительной скидкой",
    "Размер дополнительной скидки по собственной акции продавца, %",
    "Способы продажи и тип товара",
    "Уникальный идентификатор скидки лояльности от продавца",
    "Размер скидки лояльности от продавца,%",
    "Id промокода",
    "Скидка за промокод, %",
]

cols_list = [
    "date_from",
    "date_to",
    "rr_dt",
    "sale_dt",
    "order_dt",
    "create_dt",
    "rrd_id",
    "nm_id",
    "realizationreport_id",
    "sa_name",
    "shk_id",
    "report_type",
    "barcode",
    "srid",
    "ts_name",
    "currency_name",
    "bonus_type_name",
    "quantity",
    "is_legal_entity",
    "ppvz_kvw_prc",
    "ppvz_spp_prc",
    "sale_percent",
    "acquiring_percent",
    "ppvz_kvw_prc_base",
    "commission_percent",
    "country_id",
    "son_id",
    "dtn_id",
    "pmt_processing_id",
    "loaded_at",
    "son",
    "doc_type",
    "pmt_processing",
    "name",
    #  'field', 'value',
]


# pivot_fact = df.pivot_table(
#     index=["rrd_id"],
#     columns="field",
#     values="value",
#     aggfunc="first",
#     observed=True      # иногда ускоряет/чище с категориальными
# )

# wide = (
#     df.set_index(["rrd_id", "field"])["value"]
#       .unstack("field")
# )
# print(len(wide))
# print(pivot_fact)
# print(len(pivot_fact.index))
# print(len(df_wb))


# with ENGINE.connect() as c:
#     row = c.exec_driver_sql("""
#         select
#           current_user,
#           current_database(),
#           inet_server_addr(),
#           inet_server_port(),
#           current_setting('search_path')
#     """).fetchone()
#     print(row)

# print(ENGINE.url)
