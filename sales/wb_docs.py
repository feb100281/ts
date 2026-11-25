import os
import base64
import requests
from dotenv import load_dotenv

# загружаем .env если он есть (тихо, без ошибки)
load_dotenv(override=False)

WB_DOCS_DOWNLOAD_URL = "https://documents-api.wildberries.ru/api/v1/documents/download"


class WBDownloadError(RuntimeError):
    pass


def download_wb_document(service_name: str, extension: str) -> tuple[str, bytes]:
    """
    Возвращает (filename, content_bytes)
    """

    token = os.getenv("WB_DOCS_TOKEN") or os.getenv("WB_TOKEN")
    if not token:
        raise WBDownloadError("WB_DOCS_TOKEN or WB_TOKEN is not set")

    headers = {"Authorization": token}
    params = {"serviceName": service_name, "extension": extension}

    try:
        r = requests.get(
            WB_DOCS_DOWNLOAD_URL,
            headers=headers,
            params=params,
            timeout=120,
        )
        r.raise_for_status()
    except requests.RequestException as e:
        raise WBDownloadError(f"WB request failed: {e}") from e

    payload = r.json()
    data = payload.get("data") or {}

    b64 = data.get("document")
    if not b64:
        raise WBDownloadError(
            f"No document in response for {service_name}.{extension}"
        )

    filename = data.get("fileName") or f"{service_name}.{extension}"

    try:
        content = base64.b64decode(b64)
    except Exception as e:
        raise WBDownloadError(f"Base64 decode failed: {e}") from e

    return filename, content