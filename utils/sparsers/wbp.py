from __future__ import annotations

import json
import time
from typing import Iterable, Optional

import pandas as pd
import requests

from historical import ENGINE
from sqlalchemy import text
import re
import time

from typing import Optional, Union, Tuple, Dict, Any

from sqlalchemy import text, bindparam
from sqlalchemy.dialects.postgresql import JSONB


def wb_card_json_df(
    nm_ids: Iterable[int],
    *,
    max_basket: int = 99,
    timeout: int = 10,
    sleep_sec: float = 0.15,
    session: Optional[requests.Session] = None,
):
    """
    Возвращает DataFrame с колонками:
      - nm_id: артикул WB (int)
      - card_json: JSON-строка (text) — удобно хранить в PostgreSQL (jsonb тоже ок)

    Примечания:
    - Использует схему, которая у тебя сработала: vol = nm_id // 100_000, part = nm_id // 1_000
    - Подбирает basket-XX перебором и кэширует найденный basket для артикула
    - Если не удалось получить json — кладёт None в card_json
    """
    headers = {"User-Agent": "Mozilla/5.0"}
    s = session or requests.Session()

    basket_cache: dict[int, int] = {}
    rows = []

    def _find_basket(nm_id: int) -> int:
        if nm_id in basket_cache:
            return basket_cache[nm_id]

        vol = nm_id // 100_000
        part = nm_id // 1_000

        # HEAD иногда режут/неправильно настроены; если будет 405/403 — попробуем GET
        for b in range(1, max_basket + 1):
            url = (
                f"https://basket-{b:02d}.wbbasket.ru/"
                f"vol{vol}/part{part}/{nm_id}/info/ru/card.json"
            )
            try:
                r = s.head(url, headers=headers, timeout=timeout, allow_redirects=True)
                if r.status_code == 200:
                    basket_cache[nm_id] = b
                    return b
                if r.status_code in (403, 405):  # fallback на GET
                    r2 = s.get(url, headers=headers, timeout=timeout)
                    if r2.status_code == 200:
                        basket_cache[nm_id] = b
                        return b
            except requests.RequestException:
                pass

        raise RuntimeError("basket не найден")

    def _fetch_card_json(nm_id: int) -> dict:
        vol = nm_id // 100_000
        part = nm_id // 1_000
        b = _find_basket(nm_id)
        url = (
            f"https://basket-{b:02d}.wbbasket.ru/"
            f"vol{vol}/part{part}/{nm_id}/info/ru/card.json"
        )
        r = s.get(url, headers=headers, timeout=timeout)
        r.raise_for_status()
        return r.json()

    for nm_id in nm_ids:
        nm_id_int = int(nm_id)
        try:
            card = _fetch_card_json(nm_id_int)
            card_json_str = json.dumps(card, ensure_ascii=False)  # под хранение в text/jsonb
        except Exception:
            card_json_str = None

        rows.append({"nm_id": nm_id_int, "card_json": card_json_str})
        if sleep_sec:
            time.sleep(sleep_sec)

    return pd.DataFrame(rows)



def wb_fetch_card_json_one(
    nm_id: int,
    *,
    max_basket: int = 99,
    timeout: int = 10,
    session: Optional[requests.Session] = None,
) -> Union[bool, Tuple[Dict[str, Any], str]]:
    """
    Возвращает:
      - False, если card.json не найден/не скачался
      - (card_dict, basket_str) если найден

    Логика парсера сохранена:
      vol = nm_id // 100_000
      part = nm_id // 1_000
      перебор basket 1..max_basket
      HEAD -> если 200 то basket найден
      если 403/405 -> пробуем GET и если 200 то basket найден
      после нахождения basket делаем GET и возвращаем json
    """
    nm_id = int(nm_id)
    headers = {"User-Agent": "Mozilla/5.0"}
    s = session or requests.Session()

    vol = nm_id // 100_000
    part = nm_id // 1_000

    def url_for(b: int) -> str:
        return (
            f"https://basket-{b:02d}.wbbasket.ru/"
            f"vol{vol}/part{part}/{nm_id}/info/ru/card.json"
        )

    # 1) найти basket
    basket: Optional[int] = None
    for b in range(1, max_basket + 1):
        url = url_for(b)
        try:
            r = s.head(url, headers=headers, timeout=timeout, allow_redirects=True)
            if r.status_code == 200:
                basket = b
                break
            if r.status_code in (403, 405):
                r2 = s.get(url, headers=headers, timeout=timeout)
                if r2.status_code == 200:
                    basket = b
                    break
        except requests.RequestException:
            pass

    if basket is None:
        return False, "WB buscket not found"

    # 2) скачать json
    try:
        r = s.get(url_for(basket), headers=headers, timeout=timeout)
        r.raise_for_status()
        return r.json(), f"{basket:02d}"
    except Exception:
        return False, "JSON not found"
    

def get_missing_items(limit=100)->dict:
    q = text("""
        SELECT id, wb_article
        FROM sales_product
        WHERE id NOT IN (
            SELECT id FROM sales_productdata
        )
        LIMIT :limit
    """)
    with ENGINE.begin() as conn:
        result = conn.execute(q, {"limit": limit})
        return {row.id: row.wb_article for row in result}
    
def fill_table(limit):
    
    d = get_missing_items(limit)      
    
    res_dict = []
    for id,value in d.items():
        s = requests.Session()
        j_son, buscket = wb_fetch_card_json_one(nm_id=int(value),session=s)
        q = text("""
        insert into sales_productdata(wb_article_id,data,status,basket)
        values(:wb_article_id, :data, :status, :basket)        
        """).bindparams(bindparam("data", type_=JSONB))              
        status = 1 if j_son else 0
        data = j_son if j_son else None
        bascket = buscket if j_son else None
        with ENGINE.begin() as conn:
            conn.execute(q, {"wb_article_id": id,"data":data, "status":status, "basket":bascket })
        res_dict.append({"wb_article_id": id,"data":data, "status":status, "basket":bascket })
    
    return res_dict

start = time.perf_counter()
fill_table(4000)
end = time.perf_counter()

print(f"Elapsed: {end - start:.3f} sec")


# s = requests.Session()

# res = wb_fetch_card_json_one(177979910, session=s)
# if res is False:
#     print("not found")
# else:
#     card, basket = res
#     print("basket:", basket)
#     print("name:", card.get("imt_name"))



nm_list = ['177979910',
      "210344925",
"186709523",
"523404737",
"482941712",
"241127898",
"188026617",
"311043439",]

# df = wb_card_json_df(nm_list)

# df.to_sql('wb_parse',if_exists='replace',index=False,con=ENGINE)
###### REFRESH MATERIALIZED VIEW CONCURRENTLY mv_sales_productdata; !!!!!!!!!!!!!

def get_missing_products(engine, limit=None):
    sql = """
    select p.id as product_id, p.wb_article
    from sales_product p
    left join sales_productdata pd on pd.wb_article_id = p.id
    where pd.id is null and p.wb_article in ('177979910','210344925','186709523','482941712')
    order by p.id
    """
    if limit:
        sql += " limit :limit"

    with engine.begin() as conn:
        rows = conn.execute(text(sql), {"limit": limit} if limit else {}).mappings().all()
    # rows: list[{"product_id":..., "wb_article":...}]
    return rows

CARD_PAGE = "https://www.wildberries.ru/catalog/{nm}/detail.aspx"
HEADERS = {"User-Agent": "Mozilla/5.0"}

RE_BASKET = re.compile(r"https://basket-(\d{2})\.wbbasket\.ru/")

def find_basket_by_html(nm_id: int, session: requests.Session, timeout=20) -> str:
    r = session.get(CARD_PAGE.format(nm=nm_id), headers=HEADERS, timeout=timeout)
    r.raise_for_status()
    m = RE_BASKET.search(r.text)
    if not m:
        raise RuntimeError("basket not found in html")
    return m.group(1)  # "12"


def insert_productdata_rows(engine, rows):
    """
    rows: list[{"wb_article_id": int, "basket": str}]
    """
    if not rows:
        return

    # Минимальный insert. Если у тебя есть другие NOT NULL поля — добавь сюда.
    sql = """
    insert into sales_productdata (wb_article_id, basket)
    values (:wb_article_id, :basket)
    on conflict (wb_article_id) do nothing
    """
    with engine.begin() as conn:
        conn.execute(text(sql), rows)
        

def load_baskets_into_db(engine, *, limit=None, batch_size=500, sleep_sec=0.1):
    missing = get_missing_products(engine, limit=limit)

    s = requests.Session()

    buf = []
    ok = 0
    fail = 0

    for row in missing:
        product_id = int(row["product_id"])
        nm_id = int(row["wb_article"])

        try:
            basket = find_basket_by_html(nm_id, s)
            buf.append({"wb_article_id": product_id, "basket": basket})
            ok += 1
        except Exception as e:
            # можно логировать отдельно
            fail += 1

        if len(buf) >= batch_size:
            insert_productdata_rows(engine, buf)
            buf.clear()
            time.sleep(0.2)  # микропаузa между батчами

        if sleep_sec:
            time.sleep(sleep_sec)

    if buf:
        insert_productdata_rows(engine, buf)

    return {"ok": ok, "fail": fail, "total": len(missing)}

