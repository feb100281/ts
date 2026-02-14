# import os, json, requests
# from dotenv import load_dotenv

# load_dotenv()
# TOKEN = os.getenv("WB_TOKEN")
# if not TOKEN:
#     raise RuntimeError("WB_TOKEN not found")

# URL = "https://content-api.wildberries.ru/content/v2/get/cards/list"
# HEADERS = {"Authorization": TOKEN}

# payload = {
#     "settings": {
#         "filter": {
#             "nmIDs": [172429871]
#         },
#         "cursor": {
#             "limit": 1
#         }
#     }
# }

# r = requests.post(URL, headers=HEADERS, json=payload, timeout=60)
# r.raise_for_status()

# j = r.json()

# print("STATUS OK")
# print(json.dumps(j, ensure_ascii=False, indent=2))


# import os, json, requests
# from dotenv import load_dotenv
# load_dotenv()

# TOKEN = os.getenv("WB_TOKEN")
# URL = "https://content-api.wildberries.ru/content/v2/get/cards/list"
# HEADERS = {"Authorization": TOKEN, "Content-Type": "application/json"}

# def test(nm_id: int):
#     payload = {"settings": {"filter": {"nmIDs": [nm_id]}, "cursor": {"limit": 1}}}
#     r = requests.post(URL, headers=HEADERS, json=payload, timeout=60)
#     print("HTTP", r.status_code)
#     j = r.json()
#     cards = j.get("cards") or []
#     got = cards[0].get("nmID") if cards else None
#     print("REQ:", nm_id, "GOT:", got, "cards:", len(cards))
#     print("cursor:", j.get("cursor"))
#     print("raw_head:", json.dumps(j, ensure_ascii=False)[:400])

# test(230034207)
# test(172429868)
# test(235869727)

# import os, requests, json
# from dotenv import load_dotenv

# load_dotenv()
# TOKEN = os.getenv("WB_TOKEN")
# HEADERS = {"Authorization": TOKEN}

# subject_id = 1853
# URL = f"https://content-api.wildberries.ru/content/v2/object/charcs/{subject_id}"

# r = requests.get(URL, headers=HEADERS, timeout=60)
# print("HTTP", r.status_code)
# r.raise_for_status()
# j = r.json()

# # WB обычно оборачивает в {"data":..., "error":...}
# data = j.get("data", j)

# hits = [x for x in data if "ндс" in str(x.get("name","")).lower() or "vat" in str(x.get("name","")).lower()]
# print("FOUND:", len(hits))
# print(json.dumps(hits[:50], ensure_ascii=False, indent=2))

# import os, requests, json
# from dotenv import load_dotenv

# load_dotenv()
# TOKEN = os.getenv("WB_TOKEN")
# HEADERS = {"Authorization": TOKEN}

# CHARC_ID = 15001405
# URL = f"https://content-api.wildberries.ru/content/v2/object/charcs/{CHARC_ID}/values"

# r = requests.get(URL, headers=HEADERS, timeout=60)
# print("HTTP", r.status_code)
# print(r.text[:2000])
# r.raise_for_status()

# j = r.json()
# print(json.dumps(j, ensure_ascii=False, indent=2)[:4000])

# import os, requests, json
# from dotenv import load_dotenv

# load_dotenv()
# TOKEN = os.getenv("WB_TOKEN")
# HEADERS = {"Authorization": TOKEN}

# nm_id = 230034207
# URL = "https://content-api.wildberries.ru/content/v2/get/cards/list"
# payload = {"settings": {"filter": {"nmIDs": [nm_id]}, "cursor": {"limit": 1}}}

# r = requests.post(URL, headers=HEADERS, json=payload, timeout=60)
# print("HTTP", r.status_code)
# r.raise_for_status()
# j = r.json()

# card = j["cards"][0]
# # вытащим именно характеристику ставки НДС по charcID
# vat = None
# for ch in card.get("characteristics", []):
#     if ch.get("id") == 15001405 or ch.get("charcID") == 15001405 or ch.get("name") == "Ставка НДС":
#         vat = ch.get("value")
#         break

# print("VAT VALUE RAW:", vat)
# print(json.dumps(card.get("characteristics", []), ensure_ascii=False, indent=2)[:4000])

from conns import ENGINE
import pandas as pd

file = '/Users/pavelustenko/Downloads/fin_report_1.xlsx'

df = pd.read_excel(file)

df.to_sql('wb_raw.tmp',con=ENGINE,index=False,if_exists='replace')

