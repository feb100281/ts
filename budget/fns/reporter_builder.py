from enum import Enum

# Классы для параграфов
class P(Enum):
    NORMAL = ""
    SMALL = "p-small"
    COMMENT = "p-comment"
    HIGHLIGHT = "fw-bold"

# Классы для таблиц
class T(Enum):
    NORMAL = ""
    COMPACT = "table table-sm"
    BORDERED = "table table-bordered"
    STRIPED = "table table-striped"


#Разделы отчета
class Section:
    def __init__(self, order, name):
        self.order = order
        self.name = name
        self.blocks = []

    def paragraph(self, text, style: P = P.NORMAL):
        self.blocks.append({
            "type": "paragraph",
            "text": text,
            "class": style.value
        })
        return self

    def list(self, items, ordered=False):
        self.blocks.append({
            "type": "list",
            "ordered": ordered,
            "items": items
        })
        return self

    def svg(self, content, title=None):
        block = {
            "type": "svg",
            "content": content
        }
        if title:
            block["title"] = title

        self.blocks.append(block)
        return self

    def table(self, columns, rows, title=None):
        block = {
            "type": "table",
            "columns": columns,
            "rows": rows
        }
        if title:
            block["title"] = title

        self.blocks.append(block)
        return self

    def dict(self, d):
        self.list([f"{k}: {v}" for k, v in d.items()])
        return self

#Финальный репорт который собирает JSON
class Report:
    def __init__(self, title):
        self.title = title
        self.sections = []

    def add(self, section):
        self.sections.append(section)
        return self

    def build(self):
        blocks = []

        for s in sorted(self.sections, key=lambda x: x.order):
            blocks.append({
                "type": "heading",
                "level": 2,
                "text": s.name
            })
            blocks += s.blocks

        return {
            "title": self.title,
            "blocks": blocks
        }
    

