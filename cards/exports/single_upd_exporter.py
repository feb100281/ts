# cards/exports/single_upd_exporter.py

import io
import zipfile
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Border, Side, Alignment, numbers
from django.http import HttpResponse


# Цвета
COLORS = {
    "dark_green": "2F6656",
    "light_green": "E7F1ED", 
    "total_green": "DCECE6",
    "light_gray": "F7F7F7",
    "summary_fill": "FBFBFB",
    "border_gray": "D9D9D9",
    "text_gray": "666666",
    "white": "FFFFFF",
    "black": "1F1F1F",
    "back_text_green": "1F5E4E",
}

# Заливки
FILLS = {
    "header": PatternFill("solid", fgColor=COLORS["dark_green"]),
    "section": PatternFill("solid", fgColor=COLORS["light_green"]),
    "alt": PatternFill("solid", fgColor=COLORS["light_gray"]),
    "total": PatternFill("solid", fgColor=COLORS["total_green"]),
    "summary": PatternFill("solid", fgColor=COLORS["summary_fill"]),
}

# Шрифты
FONTS = {
    "title": Font(name="Helvetica Light", size=14, bold=False, color=COLORS["white"]),
    "subtitle": Font(name="Helvetica Light", size=10, color=COLORS["text_gray"]),
    "label": Font(name="Helvetica Light", size=10, color=COLORS["black"]),
    "header": Font(name="Helvetica Light", size=10, color=COLORS["white"]),
    "bold": Font(name="Helvetica Light", size=10, color=COLORS["black"]),
    "normal": Font(name="Helvetica", size=10, color=COLORS["black"]),
    "total": Font(name="Helvetica Light", size=11, bold=True, color=COLORS["black"]),
    "id": Font(name="Helvetica Light", size=10, bold=True, color=COLORS["dark_green"]),
    "mono": Font(name="Helvetica Light", size=10, color=COLORS["black"]),
    "link": Font(name="Helvetica Light", size=10, color=COLORS["dark_green"], underline="single"),
    "empty": Font(name="Helvetica Light", size=10, color="C62828"),
}

# Границы
thin = Side(style="thin", color=COLORS["border_gray"])
medium = Side(style="medium", color=COLORS["dark_green"])

BORDERS = {
    "thin": Border(left=thin, right=thin, top=thin, bottom=thin),
    "bottom_medium": Border(bottom=medium),
    "total": Border(left=medium, right=medium, top=medium, bottom=medium),
}

# Выравнивание
ALIGNMENTS = {
    "left": Alignment(horizontal="left", vertical="center"),
    "center": Alignment(horizontal="center", vertical="center"),
    "right": Alignment(horizontal="right", vertical="center"),
    "center_wrap": Alignment(horizontal="center", vertical="center", wrap_text=True),
    "left_wrap": Alignment(horizontal="left", vertical="top", wrap_text=True),
}


class SingleUpdExporter:
    """Класс для выгрузки отдельных УПД в Excel"""

    @staticmethod
    def filename(upd_document) -> str:
        """«Контрагент УПД номер от дата.xlsx» без символов, недопустимых в имени файла."""
        import re
        cp = str(upd_document.counterparty or "").split(" (ИНН:")[0]
        cp = re.sub(r'[«»"\'“”]', "", cp).strip()
        name = f"{cp} УПД {upd_document.number} от {upd_document.date:%d.%m.%Y}".strip()
        return re.sub(r'[\\/:*?<>|]+', "_", name) + ".xlsx"

    @staticmethod
    def _disposition(name: str) -> str:
        from urllib.parse import quote
        return f"attachment; filename*=UTF-8''{quote(name)}"

    @classmethod
    def generate_response(cls, upd_document):
        """Генерация HTTP-ответа для одной УПД"""
        excel_buffer = cls._generate_excel_buffer(upd_document)
        response = HttpResponse(
            excel_buffer.getvalue(),
            content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )
        response['Content-Disposition'] = cls._disposition(cls.filename(upd_document))
        return response

    @classmethod
    def generate_zip_response(cls, upd_documents):
        """Генерация ZIP-архива для нескольких УПД"""
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, 'w', zipfile.ZIP_DEFLATED) as zip_file:
            for upd_document in upd_documents:
                excel_buffer = cls._generate_excel_buffer(upd_document)
                zip_file.writestr(cls.filename(upd_document), excel_buffer.getvalue())
        
        zip_buffer.seek(0)
        response = HttpResponse(zip_buffer, content_type='application/zip')
        response['Content-Disposition'] = cls._disposition(f"УПД пакет {upd_documents.count()} шт.zip")
        return response

    @classmethod
    def _generate_excel_buffer(cls, upd_document):
        """Шаблон для управленческой себестоимости: свод по каналам, строки, итоги на формулах."""
        from openpyxl.utils import get_column_letter as L
        from openpyxl.worksheet.datavalidation import DataValidation  # noqa: F401
        from cards.models import CHANNELS

        names = dict(CHANNELS)
        default = upd_document.default_channel or "wb"
        lines = list(upd_document.income_lines.select_related("nm").order_by("upd_pos"))

        cols = [  # (заголовок, ширина, выравнивание)
            # ширины D–J рассчитаны и на свод по каналам над таблицей
            ("ID", 11, "center"), ("Позиция", 10, "center"), ("Канал", 18, "center"),
            ("Артикул поставщика", 30, "left"), ("Наименование товара", 30, "left"),
            ("Размер", 16, "center"), ("Ставка НДС, %", 20, "center"), ("Ед. изм.", 20, "center"),
            ("Кол-во", 16, "right"), ("Цена без НДС", 18, "right"), ("Сумма без НДС", 18, "right"),
            ("Сумма с НДС", 18, "right"), ("Себестоимость за ед.", 18, "right"),
            ("Себестоимость, сумма", 20, "right"), ("Наценка к УПД, %", 14, "right"),
            ("Валюта", 9, "center"), ("Карточка WB", 15, "center"),
        ]
        n = len(cols)
        C = {h: i + 1 for i, (h, _, _) in enumerate(cols)}
        money, pct = '#,##0.00', '0.0%'

        wb = Workbook()
        ws = wb.active
        ws.title = "УПД"
        ws.sheet_view.showGridLines = False

        def band(row, c1, c2, value, font, height=None):
            ws.merge_cells(start_row=row, start_column=c1, end_row=row, end_column=c2)
            cell = ws.cell(row=row, column=c1, value=value)
            cell.font, cell.alignment = font, ALIGNMENTS["center"]
            for c in range(c1, c2 + 1):
                ws.cell(row=row, column=c).fill = FILLS["header"]
            if height:
                ws.row_dimensions[row].height = height

        band(1, 1, n, f"УПД № {upd_document.number}", FONTS["title"], 30)
        band(2, 1, 6, f"от {upd_document.date:%d.%m.%Y}",
             Font(name="Helvetica Light", size=11, bold=True, color=COLORS["white"]), 24)
        band(2, 7, n, f"Поставщик: {upd_document.counterparty or 'не указан'}",
             Font(name="Helvetica Light", size=11, bold=True, color=COLORS["white"]))

        ws.cell(row=3, column=1, value="Заполните жёлтую колонку «Себестоимость за ед.» и, если известно, «Канал» (ВБ / Розница). "
                "Суммы и наценка считаются автоматически. Колонки ID и Позиция не меняйте."
                ).font = FONTS["subtitle"]

        # строки таблицы и свода
        present = [k for k, _ in CHANNELS if any((l.channel or default) == k for l in lines)] or [default]
        top = 5
        head = top + len(present) + 3          # шапка таблицы
        first, last = head + 1, head + len(lines)
        rng = lambda h: f"${L(C[h])}${first}:${L(C[h])}${max(last, first)}"

        # --- свод по каналам ---
        sh = ["Канал", "Строк", "Кол-во", "Сумма без НДС", "Себестоимость", "Наценка, %", "Не заполнено, строк"]
        for j, h in enumerate(sh):
            c = ws.cell(row=top, column=4 + j, value=h)
            c.font, c.fill, c.alignment, c.border = FONTS["header"], FILLS["header"], ALIGNMENTS["center_wrap"], BORDERS["thin"]
        ws.row_dimensions[top].height = 32
        for k, ch in enumerate(present + ["__total"]):
            r = top + 1 + k
            total = ch == "__total"
            crit = "" if total else f',{rng("Канал")},"{names[ch]}"'
            f = (lambda col: f"=SUM({rng(col)})") if total else (lambda col: f"=SUMIFS({rng(col)}{crit})")
            vals = [
                "Итого" if total else names[ch],
                f"=COUNTA({rng('ID')})" if total else f"=COUNTIFS({rng('Канал')},\"{names[ch]}\")",
                f("Кол-во"), f("Сумма без НДС"), f("Себестоимость, сумма"),
                # наценка только по строкам с заполненной себестоимостью
                (f"=IFERROR({L(8)}{r}/SUMIFS({rng('Сумма без НДС')}{crit},"
                 f"{rng('Себестоимость за ед.')},\"<>\")-1,\"\")"),
                (f"=COUNTIFS({rng('Себестоимость за ед.')},\"\")" if total else
                 f"=COUNTIFS({rng('Канал')},\"{names[ch]}\",{rng('Себестоимость за ед.')},\"\")"),
            ]
            for j, v in enumerate(vals):
                c = ws.cell(row=r, column=4 + j, value=v)
                c.border = BORDERS["thin"]
                c.font = FONTS["total"] if total else FONTS["normal"]
                c.alignment = ALIGNMENTS["right"] if j else ALIGNMENTS["left"]
                if total:
                    c.fill = FILLS["total"]
                c.number_format = {2: '#,##0', 3: money, 4: money, 5: pct}.get(j, 'General')

        # --- шапка таблицы ---
        for j, (h, w, _) in enumerate(cols, start=1):
            c = ws.cell(row=head, column=j, value=h)
            c.font, c.fill, c.alignment, c.border = FONTS["header"], FILLS["header"], ALIGNMENTS["center_wrap"], BORDERS["thin"]
            ws.column_dimensions[L(j)].width = w
        ws.row_dimensions[head].height = 32
        ws.cell(row=head, column=C["Себестоимость за ед."]).fill = PatternFill("solid", fgColor="B8860B")

        yellow = PatternFill("solid", fgColor="FFF4CC")
        for idx, l in enumerate(lines):
            r = first + idx
            q, cost = f"{L(C['Кол-во'])}{r}", f"{L(C['Себестоимость за ед.'])}{r}"
            row = {
                "ID": l.id, "Позиция": l.upd_pos, "Канал": names.get(l.channel or default, ""),
                "Артикул поставщика": l.upd_sa_name or "", "Наименование товара": l.upd_title or "",
                "Размер": l.upd_size or "",
                "Ставка НДС, %": float(l.upd_vat_rate) if l.upd_vat_rate is not None else 0,
                "Ед. изм.": l.upd_unit or "", "Кол-во": float(l.upd_qty or 0),
                "Цена без НДС": float(l.upd_price_vatless or 0),
                "Сумма без НДС": float(l.upd_amount_vatless or 0),
                "Сумма с НДС": float(l.upd_amount_vatadd or 0),
                "Себестоимость за ед.": float(l.man_cost_per_unit) if l.man_cost_per_unit is not None else None,
                # как в базе: цена за ед. хранится с 2 знаками
                "Себестоимость, сумма": f'=IF({cost}="","",{q}*ROUND({cost},2))',
                "Наценка к УПД, %": f'=IF(OR({cost}="",{L(C["Цена без НДС"])}{r}=0),"",'
                                     f'ROUND({cost},2)/{L(C["Цена без НДС"])}{r}-1)',
                "Валюта": l.currency_code or "RUB",
                "Карточка WB": str(l.nm_id) if l.nm_id else "—",
            }
            for h, w, al in cols:
                c = ws.cell(row=r, column=C[h], value=row[h])
                c.border, c.alignment = BORDERS["thin"], ALIGNMENTS[al]
                c.font = FONTS["id"] if h == "ID" else FONTS["normal"]
                if h in ("Кол-во", "Цена без НДС", "Сумма без НДС", "Сумма с НДС",
                         "Себестоимость за ед.", "Себестоимость, сумма"):
                    c.number_format = money
                if h == "Наценка к УПД, %":
                    c.number_format = pct
                if idx % 2:
                    c.fill = FILLS["alt"]
            ws.cell(row=r, column=C["Себестоимость за ед."]).fill = yellow
            if l.nm_id:
                c = ws.cell(row=r, column=C["Карточка WB"])
                c.hyperlink = f"https://www.wildberries.ru/catalog/{l.nm_id}/detail.aspx"
                c.font = FONTS["link"]

        # --- итоги по видимым строкам (учитывают фильтр) ---
        tr = last + 1
        for j in range(1, n + 1):
            c = ws.cell(row=tr, column=j)
            c.fill, c.border, c.font = FILLS["total"], BORDERS["total"], FONTS["total"]
        ws.cell(row=tr, column=1, value="ИТОГО (по фильтру)").alignment = ALIGNMENTS["left"]
        for h in ("Кол-во", "Сумма без НДС", "Сумма с НДС", "Себестоимость, сумма"):
            c = ws.cell(row=tr, column=C[h], value=f"=SUBTOTAL(9,{rng(h)})")
            c.number_format, c.alignment = money, ALIGNMENTS["right"]
        c = ws.cell(row=tr, column=C["Наценка к УПД, %"],
                    value=(f'=IFERROR({L(C["Себестоимость, сумма"])}{tr}/SUMPRODUCT('
                           f'SUBTOTAL(109,OFFSET({L(C["Сумма без НДС"])}{first},'
                           f'ROW({rng("Сумма без НДС")})-{first},0)),'
                           f'--({rng("Себестоимость за ед.")}<>""))-1,"")'))
        c.number_format, c.alignment = pct, ALIGNMENTS["right"]

        if lines:
            from openpyxl.worksheet.datavalidation import DataValidation
            dv = DataValidation(type="list", formula1='"ВБ,Розница,Не распределено"', allow_blank=True)
            dv.add(f"{L(C['Канал'])}{first}:{L(C['Канал'])}{last}")
            ws.add_data_validation(dv)

        ws.auto_filter.ref = f"A{head}:{L(n)}{max(last, head)}"
        ws.freeze_panes = ws.cell(row=first, column=C["Наименование товара"])

        excel_buffer = io.BytesIO()
        wb.save(excel_buffer)
        excel_buffer.seek(0)
        return excel_buffer
