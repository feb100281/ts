# import os
# import json
# import time
# import requests
# from dotenv import load_dotenv
# from pprint import pprint
# # --------------------
# # CONFIG
# # --------------------
# load_dotenv()

# TOKEN = os.getenv("WB_TOKEN") or os.getenv("WB_TOKEN")
# if not TOKEN:
#     raise RuntimeError("WB_TOKEN (preferred) or WB_TOKEN not found in .env")

# URL = "https://documents-api.wildberries.ru/api/v1/documents/list"
# HEADERS = {"Authorization": TOKEN}

# BEGIN_DATE = "2024-02-18"
# END_DATE   = "2024-02-20"

# LIMIT = 50
# OFFSET = 0

# all_docs = []

# # --------------------
# # FETCH
# # --------------------
# while True:
#     params = {
#         "locale": "ru",
#         "beginTime": BEGIN_DATE,
#         "endTime": END_DATE,
#         "limit": LIMIT,
#         "offset": OFFSET,
#         "sort": "date",
#         "order": "asc",
#     }

#     r = requests.get(URL, headers=HEADERS, params=params, timeout=60)

#     if not r.ok:
#         raise RuntimeError(f"WB HTTP {r.status_code}: {r.text}")

#     payload = r.json()
#     docs = (payload.get("data") or {}).get("documents") or []

#     if not docs:
#         break

#     all_docs.extend(docs)
#     print(f"Fetched {len(docs)} docs (offset={OFFSET})")

#     OFFSET += LIMIT
#     time.sleep(11)  # у documents api жёсткий лимит

# print(f"\nTOTAL DOCUMENTS: {len(all_docs)}\n")

# pprint(all_docs)





import os
import base64
import requests
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv("WB_DOCS_TOKEN") or os.getenv("WB_TOKEN")
if not TOKEN:
    raise RuntimeError("WB_DOCS_TOKEN or WB_TOKEN not found in .env")

HEADERS = {"Authorization": TOKEN}
URL = "https://documents-api.wildberries.ru/api/v1/documents/download"

SERVICE_NAME = "weekly-implementation-report-594269641"
EXTENSION = "zip"   # из твоего списка extensions

def main():
    params = {"serviceName": SERVICE_NAME, "extension": EXTENSION}
    r = requests.get(URL, headers=HEADERS, params=params, timeout=120)
    r.raise_for_status()

    payload = r.json()
    data = payload.get("data") or {}
    fname = data.get("fileName") or f"{SERVICE_NAME}.{EXTENSION}"
    b64 = data.get("document")
    if not b64:
        raise RuntimeError(f"No document in response: {payload}")

    content = base64.b64decode(b64)
    with open(fname, "wb") as f:
        f.write(content)

    print("Saved:", fname)

if __name__ == "__main__":
    main()

# import os
# import json
# import base64
# import requests
# from dotenv import load_dotenv

# load_dotenv()

# TOKEN = os.getenv("WB_DOCS_TOKEN") or os.getenv("WB_TOKEN")
# if not TOKEN:
#     raise RuntimeError("WB_DOCS_TOKEN or WB_TOKEN not found in .env")

# HEADERS = {"Authorization": TOKEN}
# URL = "https://documents-api.wildberries.ru/api/v1/documents/download/all"

# DOCS_FILE = "/Users/pavelustenko/ts/wb_documents_2025-11-09_to_2025-11-16.json"  # <-- сюда положи твой JSON
# TIMEOUT = 180


# def pick_extension(d: dict) -> str:
#     exts = d.get("extensions") or []
#     if not exts:
#         raise ValueError(f"No extensions for {d.get('serviceName')}")
#     return "zip" if "zip" in exts else exts[0]


# def chunked(seq, n):
#     for i in range(0, len(seq), n):
#         yield seq[i:i + n]


# def load_docs(path: str):
#     with open(path, "r", encoding="utf-8") as f:
#         docs = json.load(f)
#     if not isinstance(docs, list):
#         raise ValueError("docs.json must be a JSON array (list of objects)")
#     return docs


# def download_batch(docs_batch, batch_idx: int):
#     params_list = [
#         {"serviceName": d["serviceName"], "extension": pick_extension(d)}
#         for d in docs_batch
#     ]

#     body = {"params": params_list}

#     r = requests.post(URL, headers=HEADERS, json=body, timeout=TIMEOUT)
#     r.raise_for_status()

#     payload = r.json()
#     data = payload.get("data") or {}

#     b64 = data.get("document")
#     if not b64:
#         raise RuntimeError(f"No document in response: {payload}")

#     # fileName от WB; если нет — делаем свой
#     fname = data.get("fileName") or f"documents_batch_{batch_idx:03d}.zip"

#     content = base64.b64decode(b64)
#     with open(fname, "wb") as f:
#         f.write(content)

#     print(f"Saved: {fname} (docs: {len(params_list)})")


# def main():
#     docs = load_docs(DOCS_FILE)

#     # скачиваем пакетами по 50 (ограничение API)
#     for idx, batch in enumerate(chunked(docs, 50), start=1):
#         download_batch(batch, idx)


# if __name__ == "__main__":
#     main()



# import os
# import time
# import requests
# from dotenv import load_dotenv

# import psycopg


# # --------------------
# # CONFIG
# # --------------------
# load_dotenv()

# WB_TOKEN = os.getenv("WB_TOKEN")
# if not WB_TOKEN:
#     raise RuntimeError("WB_TOKEN not found in .env")

# PG_HOST = os.getenv("DB_HOST", "127.0.0.1")
# PG_PORT = int(os.getenv("DB_PORT", "5432"))
# PG_DB   = os.getenv("DB_NAME", "ts_db")
# PG_USER = os.getenv("DB_USER", "ts_user")
# PG_PASS = os.getenv("DB_PASSWORD")
# if not PG_PASS:
#     raise RuntimeError("DB_PASSWORD not found in env/.env")

# URL = "https://documents-api.wildberries.ru/api/v1/documents/list"
# HEADERS = {"Authorization": WB_TOKEN}

# BEGIN_DATE = "2026-02-10"
# END_DATE   = "2026-02-20"

# LIMIT = 50
# OFFSET = 0
# SLEEP_SECONDS = 11


# UPSERT_SQL = """
# INSERT INTO wb_raw.wb_documents
#     (service_name, category, name, creation_time, extensions, viewed, fetched_at)
# VALUES
#     (%s, %s, %s, %s, %s, %s, NOW())
# ON CONFLICT (service_name, name, creation_time)
# DO UPDATE SET
#     category   = EXCLUDED.category,
#     extensions = EXCLUDED.extensions,
#     viewed     = EXCLUDED.viewed,
#     fetched_at = NOW();
# """


# def ext_to_str(ext) -> str:
#     # WB: ["xml"] / ["zip"] / ... -> "xml" / "zip" / "xml,zip"
#     if not ext:
#         return ""
#     if isinstance(ext, list):
#         return ",".join(str(x) for x in ext if x is not None)
#     return str(ext)


# def fetch_page(offset: int):
#     params = {
#         "locale": "ru",
#         "beginTime": BEGIN_DATE,
#         "endTime": END_DATE,
#         "limit": LIMIT,
#         "offset": offset,
#         "sort": "date",
#         "order": "asc",
#     }
#     r = requests.get(URL, headers=HEADERS, params=params, timeout=60)
#     if not r.ok:
#         raise RuntimeError(f"WB HTTP {r.status_code}: {r.text}")
#     payload = r.json()
#     return (payload.get("data") or {}).get("documents") or []


# def main():
#     dsn = (
#         f"host={PG_HOST} port={PG_PORT} dbname={PG_DB} "
#         f"user={PG_USER} password={PG_PASS}"
#     )

#     total = 0
#     offset = OFFSET

#     # autocommit=False по умолчанию; будем коммитить по странице
#     with psycopg.connect(dsn) as conn:
#         with conn.cursor() as cur:
#             while True:
#                 docs = fetch_page(offset)
#                 if not docs:
#                     break

#                 rows = [
#                     (
#                         d.get("serviceName"),
#                         d.get("category"),
#                         d.get("name"),
#                         d.get("creationTime"),          # ISO -> timestamptz
#                         ext_to_str(d.get("extensions")),
#                         bool(d.get("viewed", False)),
#                     )
#                     for d in docs
#                 ]

#                 # Быстро для 50 строк/страница: executemany достаточно
#                 cur.executemany(UPSERT_SQL, rows)
#                 conn.commit()

#                 total += len(rows)
#                 print(f"Fetched {len(rows)} docs + upserted (offset={offset})")

#                 offset += LIMIT
#                 time.sleep(SLEEP_SECONDS)

#     print(f"\nTOTAL UPSERTED (processed): {total}\n")


# if __name__ == "__main__":
#     main()