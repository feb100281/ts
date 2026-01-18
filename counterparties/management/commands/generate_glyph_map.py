from pathlib import Path
import re

from django.conf import settings
from django.core.management.base import BaseCommand

from counterparties.models import Glyph


HEX_RE = re.compile(r"^[0-9A-F]{3,6}$", re.IGNORECASE)


def normalize_code(code: str) -> str | None:
    r"""
    Accepts: E001, \E001, uE001, U+E001, 0xE001, \uE001, \UE001
    Returns: E001 (upper) or None if invalid
    """
    if not code:
        return None

    c = code.strip()

    # remove common prefixes/forms
    c = c.replace("U+", "").replace("u+", "")
    c = c.replace("0x", "").replace("0X", "")

    # IMPORTANT: support "\uE001" / "\UE001"
    c = c.replace("\\u", "").replace("\\U", "")

    # support "\E001"
    c = c.lstrip("\\").strip()

    # support "uE001" (no backslash)
    if c.lower().startswith("u") and len(c) > 1:
        c = c[1:]

    if not HEX_RE.match(c):
        return None

    return c.upper()


class Command(BaseCommand):
    help = "Generate static/fonts/glyph-map.css from Glyph table"

    def add_arguments(self, parser):
        parser.add_argument(
            "--out",
            default="static/fonts/glyph-map.css",
            help="Output path relative to BASE_DIR (default: static/fonts/glyph-map.css)",
        )

    def handle(self, *args, **opts):
        out_rel = opts["out"]
        out_file = Path(settings.BASE_DIR) / out_rel
        out_file.parent.mkdir(parents=True, exist_ok=True)

        glyphs = Glyph.objects.all().only("code").order_by("code")

        rules: list[str] = []
        skipped = 0

        for g in glyphs:
            norm = normalize_code(g.code)
            if not norm:
                skipped += 1
                continue

            # CSS expects \e001 format
            rules.append(
                f'.tenant-glyph-preview[data-glyph="{norm}"]::before {{ content: "\\{norm.lower()}"; }}'
            )

        out_file.write_text("\n".join(rules) + "\n", encoding="utf-8")

        self.stdout.write(
            self.style.SUCCESS(
                f"glyph-map.css generated: {out_file} | rules={len(rules)} | skipped={skipped}"
            )
        )
