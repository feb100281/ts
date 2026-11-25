"""
Отправка разложенных файлов Армении на сервер ts.

Отправляются только новые и изменённые файлы (учёт — в скрытом .am_uploaded.json в каждой папке).
Адрес и ключ — из .env проекта: AM_UPLOAD_URL, AM_UPLOAD_TOKEN.

    python am_upload.py --statements <папка> --sales <папка> --env <путь к .env>
"""

from __future__ import annotations

import argparse
import hashlib
import json
import mimetypes
import ssl
import sys
import urllib.error
import urllib.request
import uuid
from pathlib import Path

DEFAULT_URL = "https://ts-bias.ru/api/am/upload/"
STATE = ".am_uploaded.json"


def read_env(path: Path) -> dict[str, str]:
    env = {}
    if path.exists():
        for line in path.read_text(encoding="utf-8").splitlines():
            if "=" in line and not line.lstrip().startswith("#"):
                k, v = line.split("=", 1)
                env[k.strip()] = v.strip().strip('"').strip("'")
    return env


def sha1(path: Path) -> str:
    return hashlib.sha1(path.read_bytes()).hexdigest()


def files_to_send(root: Path) -> list[Path]:
    out = []
    for p in sorted(root.rglob("*")):
        rel = p.relative_to(root)
        if not p.is_file() or p.name.startswith((".", "~$")):
            continue
        if any(part.startswith("_") for part in rel.parts):
            continue                                    # служебные папки и журнал
        out.append(p)
    return out


def post(url: str, token: str, kind: str, path: Path, rel: str) -> tuple[int, dict]:
    boundary = uuid.uuid4().hex
    ctype = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    parts = []
    for name, value in (("kind", kind), ("path", rel)):
        parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n\r\n{value}\r\n'.encode())
    parts.append(f'--{boundary}\r\nContent-Disposition: form-data; name="file"; filename="{path.name}"\r\n'
                 f"Content-Type: {ctype}\r\n\r\n".encode() + path.read_bytes() + b"\r\n")
    parts.append(f"--{boundary}--\r\n".encode())
    req = urllib.request.Request(url, data=b"".join(parts), method="POST", headers={
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "Authorization": f"Bearer {token}",
    })
    try:
        with urllib.request.urlopen(req, timeout=300, context=ssl.create_default_context()) as resp:
            return resp.status, json.loads(resp.read() or b"{}")
    except urllib.error.HTTPError as exc:
        try:
            return exc.code, json.loads(exc.read() or b"{}")
        except ValueError:
            return exc.code, {"error": exc.reason}


def send_folder(root: Path, kind: str, url: str, token: str) -> bool:
    state_path = root / STATE
    state = json.loads(state_path.read_text(encoding="utf-8")) if state_path.exists() else {}
    ok = True
    sent = 0
    for p in files_to_send(root):
        rel = p.relative_to(root).as_posix()
        digest = sha1(p)
        if state.get(rel) == digest:
            continue
        try:
            code, data = post(url, token, kind, p, rel)
        except (urllib.error.URLError, OSError) as exc:
            print(f"  ✗ {rel}: нет связи с сервером ({exc})")
            return False
        if code == 200 and data.get("ok"):
            state[rel] = digest
            sent += 1
            extra = f"новых операций {data['new']}, уже были {data['existing']}" if "new" in data else data.get("message", "")
            print(f"  ✓ {rel}: {extra}")
            for w in data.get("warnings", []):
                print(f"      ! {w}")
        else:
            ok = False
            print(f"  ✗ {rel}: {data.get('error') or code}")
        state_path.write_text(json.dumps(state, ensure_ascii=False, indent=1), encoding="utf-8")
    if sent == 0 and ok:
        print("  новых файлов нет")
    return ok


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--statements", type=Path)
    ap.add_argument("--sales", type=Path)
    ap.add_argument("--env", type=Path, required=True)
    args = ap.parse_args(argv)
    env = read_env(args.env)
    token = env.get("AM_UPLOAD_TOKEN", "")
    url = env.get("AM_UPLOAD_URL", DEFAULT_URL)
    if not token:
        print(f"В {args.env} нет AM_UPLOAD_TOKEN — отправка пропущена")
        return 1
    ok = True
    for kind, folder, title in (("statement", args.statements, "ВЫПИСКИ"), ("sales", args.sales, "ПРОДАЖИ")):
        if folder and folder.is_dir():
            print("=" * 60)
            print(f"Отправка: {title}")
            ok = send_folder(folder, kind, url, token) and ok
    print("=" * 60)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
