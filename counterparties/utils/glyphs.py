from pathlib import Path
import re

from django.conf import settings
from counterparties.models import Glyph  

HEX_RE = re.compile(r"^[0-9A-F]{3,6}$", re.IGNORECASE)


def normalize_code(code: str) -> str | None:
    if not code:
        return None
    c = str(code).strip()

    c = c.replace("U+", "").replace("u+", "")
    c = c.replace("0x", "").replace("0X", "")
    c = c.replace("\\u", "").replace("\\U", "")
    c = c.lstrip("\\").strip()

    if c.lower().startswith("u") and len(c) > 1:
        c = c[1:]

    if not HEX_RE.match(c):
        return None

    return c.upper()


def generate_glyph_map_css() -> tuple[Path, int, int]:
    """
    Generates static/fonts/glyph-map.css
    Returns: (path, rules_count, skipped_count)
    """
    out_file = Path(settings.BASE_DIR) / "static" / "fonts" / "glyph-map.css"
    out_file.parent.mkdir(parents=True, exist_ok=True)

    rules = []
    skipped = 0

    for g in Glyph.objects.all().only("code").order_by("code"):
        norm = normalize_code(g.code)
        if not norm:
            skipped += 1
            continue
        rules.append(
            f'.tenant-glyph-preview[data-glyph="{norm}"]::before {{ content: "\\{norm.lower()}"; }}'
        )

    out_file.write_text("\n".join(rules) + "\n", encoding="utf-8")
    return out_file, len(rules), skipped

