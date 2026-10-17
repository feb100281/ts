import os, json, requests
from datetime import date
from dotenv import load_dotenv
from sqlalchemy import text
from conns import ENGINE

load_dotenv()
TOKEN = os.getenv("WB_TOKEN")  # лучше WB_FIN_TOKEN
URL = "https://finance-api.wildberries.ru/api/v1/account/balance"

r = requests.get(URL, headers={"Authorization": TOKEN}, timeout=30)
r.raise_for_status()
payload = r.json()

print(json.dumps(payload, ensure_ascii=False))