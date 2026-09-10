import os
import json
import requests
import pandas as pd
from dotenv import load_dotenv

load_dotenv()

token = os.getenv("WB_SUPER_TOKEN")

url = "https://seller-analytics-api.wildberries.ru/api/analytics/v1/stocks-report/wb-warehouses"

headers = {
    "Authorization": token,
    "Content-Type": "application/json",
}

payload = {
    "limit": 250000,
    "offset": 0,
}

r = requests.post(url, headers=headers, json=payload)

print("Status code:", r.status_code)

if r.status_code != 200:
    print(r.text)
    raise SystemExit("WB API error")

response = r.json()

rows = response["data"]["items"]

df = pd.DataFrame({
    "nm_id": [row["nmId"] for row in rows],
    "payload": [json.dumps(row, ensure_ascii=False) for row in rows],
})

file_name = "wb_stocks_raw.parquet"
df.to_parquet(file_name, index=False)

print(f"Saved: {file_name}")
print("Rows:", len(df))
print(df.head())
