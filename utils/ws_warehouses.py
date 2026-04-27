import os
import json
import requests
from dotenv import load_dotenv

load_dotenv()


token = os.getenv("WB_TOKEN")


headers = {
    "Authorization": token,
    "Content-Type": "application/json",
}

wb_office_id = 507  # например Коледино, если есть в списке

url = f"https://marketplace-api.wildberries.ru/api/v3/stocks/{wb_office_id}"

payload = {
    "skus": []  # или chrtIds/skus по документации твоего метода
}

r = requests.post(url, headers=headers, json=payload)

print(r.status_code)
print(r.text)

