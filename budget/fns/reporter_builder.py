# budget/fns/reporter_builder.py

from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional
from datetime import datetime


# =========================
# Классы для параграфов
# =========================
class P(Enum):
    NORMAL = ""
    SMALL = "p-small"
    COMMENT = "p-comment"
    STRONG = "p-strong"
    LEAD = "p-lead"
    MUTED = "p-muted"


# =========================
# Классы для таблиц
# =========================
class T(Enum):
    NORMAL = "table-normal"
    COMPACT = "table-compact"
    BORDERED = "table-bordered"
    STRIPED = "table-striped"
    NO_BORDER = "table-no-border"


# =========================
# Раздел отчета
# =========================
class Section:
    def __init__(self, order, name: str):
        self.order = order
        self.name = name
        self.blocks = []

    def paragraph(self, text: str, style: P = P.NORMAL):
        self.blocks.append({
            "type": "paragraph",
            "text": text,
            "class": style.value
        })
        return self

    def list(self, items, ordered: bool = False, title: Optional[str] = None, css_class: str = ""):
        self.blocks.append({
            "type": "list",
            "ordered": ordered,
            "items": items,
            "title": title,
            "class": css_class
        })
        return self

    def table(self, columns, rows, title: Optional[str] = None, style: T = T.NORMAL):
        self.blocks.append({
            "type": "table",
            "columns": columns,
            "rows": rows,
            "title": title,
            "class": style.value
        })
        return self

    def svg(self, content: str, title: Optional[str] = None, css_class: str = ""):
        self.blocks.append({
            "type": "svg",
            "content": content,
            "title": title,
            "class": css_class
        })
        return self

    def dict(self, d: dict, title: Optional[str] = None):
        items = [f"{k}: {v}" for k, v in d.items()]
        return self.list(items, ordered=False, title=title)

    def page_break(self):
        self.blocks.append({
            "type": "page_break"
        })
        return self


# =========================
# Финальный отчет
# =========================
@dataclass
class Report:
    title: str
    subtitle: Optional[str] = None
    company: Optional[str] = None
    period: Optional[str] = None
    author: Optional[str] = None
    theme: str = "executive"
    cover_title: Optional[str] = None
    cover_subtitle: Optional[str] = None
    created_at: Optional[str] = None
    show_cover: bool = True
    sections: List[Section] = field(default_factory=list)
    cover_type: Optional[str] = None
    cover_system: Optional[str] = None
    report_type: Optional[str] = None
    confidential: bool = True

    def add(self, section: Section):
        self.sections.append(section)
        return self

    def build(self):
        blocks = []

        for s in sorted(self.sections, key=lambda x: x.order):
            if s.name:
                blocks.append({
                    "type": "heading",
                    "level": 2,
                    "text": s.name
                })
            blocks.extend(s.blocks)

        created_at = self.created_at or datetime.now().strftime("%d.%m.%Y")

        return {
            "title": self.title,
            "subtitle": self.subtitle,
            "company": self.company,
            "period": self.period,
            "author": self.author,
            "theme": self.theme,
            "cover_title": self.cover_title or self.title,
            "cover_subtitle": self.cover_subtitle or self.subtitle,
            "created_at": created_at,
            "show_cover": self.show_cover,
            "cover_type": self.cover_type,
            "cover_system": self.cover_system,
            "report_type": self.report_type,
            "confidential": self.confidential,
            "meta": {
                "title": self.title,
                "subtitle": self.subtitle,
                "company": self.company,
                "period": self.period,
                "author": self.author,
                "theme": self.theme,
                "created_at": created_at,
                "cover_type": self.cover_type,
                "cover_system": self.cover_system,
                "report_type": self.report_type,
                "confidential": self.confidential,
            },
            "blocks": blocks
        }

