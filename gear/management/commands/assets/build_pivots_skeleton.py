# -*- coding: utf-8 -*-
"""Пересборка assets/pivots_skeleton.xlsx — книги со сводными.

ВАЖНО: скелет собирается этим скриптом, а не руками в Excel. Если открыть
pivots_skeleton.xlsx в Excel и сохранить, Excel перепишет описание сводных
по-своему и потеряет группировку дат, шрифт, стиль и флаги свёрнутости.

Что делает скрипт:
  * кладёт в кэш обеих сводных справочники значений, отсортированные по
    коду — иначе разделы идут в случайном порядке;
  * добавляет служебные поля группировки дат Months / Quarters / Years;
  * строит шесть уровней строк до договора:
      CF  — вид деятельности -> операция -> статья -> подстатья ->
            контрагент -> договор;
      P&L — группа счетов -> счёт -> группа статей -> статья ->
            контрагент -> договор;
    первые два уровня открыты, глубже — по кнопке «+»;
  * колонки: год -> месяц -> день, свёрнуты до года;
  * прописывает стиль ManpackPivotGreen и делает его стилем по умолчанию;
  * ставит листы в порядке: обе сводные, затем источники.

Справочники в скелете — только заготовка. При сборке пакета команда
перезаписывает их фактическими значениями из витрин (mp.py,
sync_pivot_items), иначе новая статья или контрагент после обновления
показывались бы раскрытыми.

Рядом должны лежать два служебных файла, снятые с reporting/excel/template.xlsx:
  _pivots_base.xlsx           — четыре листа (две сводные + два источника);
  _pivots_cache_fields.json   — справочники значений из кэшей шаблона.
"""

ACTIVITY = [
 "100000 Операционная деятельность",
 "200000 Инвестиционная деятельность",
 "300000 Финансовая деятельность",
 "400000 Внутрегрупповые трансакции",
]
OPERATION = [
 "110000 Поступления от операционной деятельности",
 "120000 Платежи по операционной деятельности",
 "202000 Платежи по инвестиционной деятельности",
 "310000 Поступления от финансовой деятельности",
 "320000 Отток от финансовой деятельности",
 "410000 Перевод между счетами",
]
ITEM = [
 "111000 Выручка от продажи товаров",
 "121000 Оплаты товаров для перепродажи",
 "122000 Зачет расходов на реализацию WB",
 "123000 Накладные и корпоративные расходы",
 "124000 Затраты на персонал",
 "125000 Оплаты налогов и сборов",
 "202010 Инвестиции в нематериальные активы",
 "202020 Приобретение основных средств",
 "312000 Привлечение заемных средств",
 "313000 Проценты по депозитам / займам",
 "314000 Возврат размещённых средств",
 "321000 Погашение кредитов и займов",
 "322000 Размещение денежных средств",
 "410100 Перевод собственных средств",
 "410200 Валютные операции",
]
SUBITEM = [
 "111100 Продажи через маркетплейсы",
 "111200 Выкуп товара маркетплэйсом",
 "121200 Логистика и доставка товара",
 "122101 Комиссия маркетплэйса с продаж",
 "122102 Комиссия маркетплэйса с выкупа",
 "122201 Логистика с продаж",
 "122202 Логистика с выкупов",
 "122300 Хранение с продаж",
 "122401 Приемка товара с продаж",
 "122501 Удержания с продаж",
 "122601 Штрафы с продаж",
 "122701 Корректировки с прожаж",
 "122801 Участие в программе лояльности с продаж",
 "122901 Измеение срока перечисления с продаж",
 "122910 Балы по программе лояльности с продаж",
 "123100 Комисии банков",
 "123200 Бухгалтерские услуги",
 "123700 Цифровые сервисы",
 "123940 Операции по корпоративной карте",
 "124100 Заработная плата",
 "124200 Обучение и развитие персонала",
 "125300 Соц взносы",
 "125400 НДС",
 "202011 Разработка собственного ПО",
 "202021 Серверы и IT-инфраструктура",
 "312100 Кредиты и займы",
 "313100 Начисленные проценты по депозитам",
 "314100 Возврат тела депозита",
 "321100 Погашение тела кредитов и займов",
 "321200 Оплата процентов по кредитам и займам",
 "322100 Депозиты",
 "410101 Перевод собственных средств",
 "410201 Валютная конвертация",
 "410202 Отражение курсовых разниц",
]
CP_NAME = [
 "АЛЬФА-БАНК АО","БАНК БЖФ АО","БАНК КАЗАНИ ООО","БЕЙОНД ТЭЙЛОР ООО",
 "БЕРДНИКОВ СЕРГЕЙ АЛЕКСЕЕВИЧ","ВАЙЛДБЕРРИЗ БАНК ООО","ГАВШИН БОГДАН СЕРГЕЕВИЧ",
 "ИФНС","КБ ХЛЫНОВ АО","КОТОВСКАЯ КАРИНА ВЛАДИМИРОВНА","КУЗИН МАКСИМ ЕВГЕНЬЕВИЧ",
 "МАЛАЙ МАКСИМ АЛЕКСАНДРОВИЧ","МИНАСЯН МАКСИМ ВАДИМОВИЧ","МОРСКОЙ БАНК АО",
 "МУРАДЯН КАРИНЭ АРТЮНОВНА","НЬЮ РИВЕР ООО","ОПЕРАТОР-ЦРПТ ООО",
 "ПЕРЕВЕРЗЕВ ДМИТРИЙ ВЛАДИМИРОВИЧ","РВБ ООО","РЕПОРТ СИСТЕМС ЗАО","С-ЛОГИСТИК ООО",
 "СИДОРОВА КСЕНИЯ ДМИТРИЕВНА","СОВКОМБАНК ПАО","ТАЛИПОВА ГАЛИЯ ГАЯНОВНА ИП",
 "ТКС ООО","ТРЕНДСЕТТЕР OOO","ЭКСПОБАНК АО",
]
CONTRACT = [
 "Без договора № б/н от б/д",
 "Бизнес карта № б/н от б/д",
 "Договор РКО № б/н от 2024-12-13",
 "Договор РКО № б/н от б/д",
 "Договор займа № б/н от 2024-07-24",
 "Договор комиссионера № б/н от б/д",
 "Договор на депозит № 56252/25-ДБОЮЛ от 2025-09-12",
 "Договор на депозит № 56774/25-ДБОЮЛ от 2025-09-17",
 "Договор на депозит № 57788/25-ДБОЮЛ от 2025-09-26",
 "Договор на депозит № БВ-Ю-810/1100-90618308/1-24 от 2024-03-07",
 "Договор на депозит № БВ-Ю-810/1100-90618308/2-24 от 2024-03-15",
 "Договор на депозит № б/н от 2023-10-26",
 "Договор № 1763420 от б/д",
 "Договор № 31052024-1 от 2024-05-31",
 "Договор № 64 от 2023-09-25",
 "Договор № TC/PC-0124 от 2024-08-07",
 "Договор № TC/PC-2024 от 2024-12-25",
 "Договор № БТ-21-03/2025 от 2025-09-17",
 "Договор № б/н от б/д",
 "Кредитный договор № 16/25-КЛ/з от 2025-04-22",
 "Кредитный договор № 16/25-КЛ/з-02 от 2025-04-29",
 "Кредитный договор № 236-2025Ю00 от 2025-06-25",
 "Трудовой договор № б/н от б/д",
]


import json, os, re, sys, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "_pivots_base.xlsx")
DST = sys.argv[2] if len(sys.argv) > 2 else os.path.join(HERE, "pivots_skeleton.xlsx")
FIELDS = json.load(open(os.path.join(HERE, "_pivots_cache_fields.json"), encoding="utf-8"))

NAVY, TOTAL_ROW, STRIPE = "FF2F6656", "FFE7F1ED", "FFE9E9E9"
SUB1, SUB2, SUB3 = "FFE7F1ED", "FFEDF5F1", "FFF3F8F6"
GRID, RULE, TEXT = "FFD4DDD9", "FFE6E6E6", "FF1F1F1F"

PIVOT_FONT = "Roboto"

G_START, G_END = "2023-09-22T00:00:00", "2026-03-18T00:00:00"
MON = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
DAYS_IN = [31,29,31,30,31,30,31,31,30,31,30,31]
DAY_ITEMS = (["&lt;" + G_START[:10]]
             + ["%02d-%s" % (d, MON[m]) for m in range(12)
                for d in range(1, DAYS_IN[m] + 1)]
             + ["&gt;" + G_END[:10]])
MONTH_ITEMS = ["&lt;" + G_START[:10]] + MON + ["&gt;" + G_END[:10]]
QTR_ITEMS = ["&lt;" + G_START[:10], "Qtr1", "Qtr2", "Qtr3", "Qtr4",
             "&gt;" + G_END[:10]]
YEAR_ITEMS = ["&lt;" + G_START[:10], "2023", "2024", "2025", "2026",
              "&gt;" + G_END[:10]]


def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;"))


def shared(values):
    # сортируем: коды стоят в начале подписи, значит порядок по коду
    values = sorted(values)
    return ('<sharedItems count="%d">%s</sharedItems>'
            % (len(values), "".join('<s v="%s"/>' % esc(v) for v in values)))


PLAIN = '<sharedItems containsNonDate="0" containsString="0" containsBlank="1"/>'
DATE_ITEMS = ('<sharedItems count="1" containsSemiMixedTypes="0"'
              ' containsNonDate="0" containsDate="1" containsString="0"'
              ' minDate="%s" maxDate="%s"><d v="%s"/></sharedItems>'
              % (G_END, G_END, G_END))


def group_items(vals):
    return ('<groupItems count="%d">%s</groupItems>'
            % (len(vals), "".join('<s v="%s"/>' % v for v in vals)))


def range_pr(by):
    return ('<rangePr autoStart="1" autoEnd="1" groupBy="%s" startDate="%s"'
            ' endDate="%s" groupInterval="1"/>' % (by, G_START, G_END))


def group_field(name, by, vals):
    return ('<cacheField name="%s" numFmtId="0" databaseField="0">'
            '<fieldGroup base="0">%s%s</fieldGroup></cacheField>'
            % (name, range_pr(by), group_items(vals)))


def items(n, collapsed):
    sd = ' sd="0"' if collapsed else ""
    body = "".join('<item%s x="%d"/>' % (sd, i) for i in range(n))
    return '<items count="%d">%s<item t="default"%s/></items>' % (n + 1, body, sd)


# ------------------------------------------------------------- конфигурация
CF_VALUES = {}
for i, f in enumerate(FIELDS["cf"]):
    if f["values"] and f["name"] not in ("date_from",):
        CF_VALUES[i] = [v for v in f["values"] if v]
CF_VALUES[4] = CONTRACT          # contract_name — в шаблоне не использовался
CF_VALUES[5] = CP_NAME           # cp_name — тоже

PL_VALUES = {}
for i, f in enumerate(FIELDS["pl"]):
    if f["values"] and f["name"] not in ("date_from",):
        PL_VALUES[i] = [v for v in f["values"] if v]

PIVOTS = {
    "cf": {
        "cache": "xl/pivotCache/pivotCacheDefinition1.xml",
        "table": "xl/pivotTables/pivotTable1.xml",
        "source": "raw_cf",
        "cacheId": "538",
        "base": [f["name"] for f in FIELDS["cf"]
                 if f["name"] not in ("Months", "Quarters", "Years")],
        "values": CF_VALUES,
        "rows": [7, 8, 9, 10, 5, 4],       # вид → операция → статья →
                                           # подстатья → контрагент → договор
        "amount": 14,
    },
    "pl": {
        "cache": "xl/pivotCache/pivotCacheDefinition2.xml",
        "table": "xl/pivotTables/pivotTable2.xml",
        "source": "raw_pl",
        "cacheId": "531",
        "base": [f["name"] for f in FIELDS["pl"]
                 if f["name"] not in ("Months", "Quarters", "Years")],
        "values": PL_VALUES,
        "rows": [6, 7, 8, 9, 11, 10],      # группа счетов → счёт → группа
                                           # статей → статья → контрагент →
                                           # договор
        "amount": 14,
    },
}


def build_cache(cfg):
    n = len(cfg["base"])
    months_i, years_i = n, n + 2
    parts = []
    for i, name in enumerate(cfg["base"]):
        if i == 0:
            body = DATE_ITEMS + (
                '<fieldGroup par="%d" base="0">%s%s</fieldGroup>'
                % (years_i, range_pr("days"), group_items(DAY_ITEMS)))
            parts.append('<cacheField name="%s" numFmtId="165">%s</cacheField>'
                         % (esc(name), body))
        elif i in cfg["values"]:
            parts.append('<cacheField name="%s" numFmtId="0">%s</cacheField>'
                         % (esc(name), shared(cfg["values"][i])))
        else:
            parts.append('<cacheField name="%s" numFmtId="0">%s</cacheField>'
                         % (esc(name), PLAIN))
    parts.append(group_field("Months", "months", MONTH_ITEMS))
    parts.append(group_field("Quarters", "quarters", QTR_ITEMS))
    parts.append(group_field("Years", "years", YEAR_ITEMS))

    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<pivotCacheDefinition'
            ' xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
            ' xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
            ' saveData="0" refreshOnLoad="1" missingItemsLimit="0"'
            ' createdVersion="8" refreshedVersion="8"'
            ' minRefreshableVersion="3" recordCount="0">'
            '<cacheSource type="worksheet">'
            '<worksheetSource name="%s"/></cacheSource>'
            '<cacheFields count="%d">%s</cacheFields>'
            '</pivotCacheDefinition>'
            % (cfg["source"], n + 3, "".join(parts)))


def build_table(cfg, dxf_date=None):
    n = len(cfg["base"])
    months_i, years_i = n, n + 2
    rows = cfg["rows"]
    open_levels = set(rows[:2])

    pf = []
    for i in range(n + 3):
        if i == 0:
            pf.append('<pivotField axis="axisCol" numFmtId="165" showAll="0">'
                      '%s</pivotField>' % items(len(DAY_ITEMS), True))
        elif i == months_i:
            pf.append('<pivotField axis="axisCol" showAll="0">%s</pivotField>'
                      % items(len(MONTH_ITEMS), True))
        elif i == years_i:
            pf.append('<pivotField axis="axisCol" showAll="0">%s</pivotField>'
                      % items(len(YEAR_ITEMS), True))
        elif i in rows:
            cnt = len(cfg["values"].get(i, [""]))
            # открыты первые два уровня, глубже — по кнопке «+»
            pf.append('<pivotField axis="axisRow" showAll="0"'
                      ' sortType="ascending">%s</pivotField>'
                      % items(cnt, i not in open_levels))
        elif i == cfg["amount"]:
            pf.append('<pivotField dataField="1" showAll="0"/>')
        else:
            pf.append('<pivotField showAll="0"/>')

    row_fields = "".join('<field x="%d"/>' % i for i in rows)

    return ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
            '<pivotTableDefinition'
            ' xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
            ' name="Pivot_%s" cacheId="%s" applyNumberFormats="0"'
            ' applyBorderFormats="0" applyFontFormats="0"'
            ' applyPatternFormats="0" applyAlignmentFormats="0"'
            ' applyWidthHeightFormats="1" dataCaption="Values"'
            ' updatedVersion="8" minRefreshableVersion="3"'
            ' useAutoFormatting="1" itemPrintTitles="1" createdVersion="8"'
            ' indent="0" showHeaders="0" outline="1" outlineData="1"'
            ' multipleFieldFilters="0" grandTotalCaption="ИТОГО">'
            '<location ref="A3:C7" firstHeaderRow="1" firstDataRow="2"'
            ' firstDataCol="1"/>'
            '<pivotFields count="%d">%s</pivotFields>'
            '<rowFields count="%d">%s</rowFields>'
            '<rowItems count="3"><i><x/></i><i r="1"><x/></i>'
            '<i t="grand"><x/></i></rowItems>'
            '<colFields count="3">'
            '<field x="%d"/><field x="%d"/><field x="0"/></colFields>'
            '<colItems count="2"><i><x v="1"/></i><i t="grand"><x/></i>'
            '</colItems>'
            '<dataFields count="1">'
            '<dataField name="в российских рублях (RUB)" fld="%d"'
            ' baseField="0" baseItem="0" numFmtId="171"/></dataFields>'
            '<pivotTableStyleInfo name="ManpackPivotGreen" showRowHeaders="1"'
            ' showColHeaders="1" showRowStripes="1" showColStripes="0"'
            ' showLastColumn="1"/>'
            '</pivotTableDefinition>'
            % (cfg["source"], cfg["cacheId"], n + 3, "".join(pf),
               len(rows), row_fields, years_i, months_i, cfg["amount"]))


# ------------------------------------------------------------------- стили
def dxf(font=None, fill=None, border=None):
    out = "<dxf>"
    if font:
        out += font
    if fill:
        out += ('<fill><patternFill patternType="solid">'
                '<fgColor rgb="%s"/><bgColor rgb="%s"/>'
                '</patternFill></fill>' % (fill, fill))
    if border:
        out += border
    return out + "</dxf>"


def edges(spec):
    return ("<border>" + "".join(
        '<%s style="%s"><color rgb="%s"/></%s>' % (s, st, c, s)
        for s, st, c in spec) + "</border>")


FONT10 = '<sz val="10"/><name val="%s"/>' % PIVOT_FONT
FONT_B = '<b/>' + FONT10

D_WHOLE = dxf(font="<font>%s</font>" % FONT10,
              border=edges([("left", "thin", RULE), ("right", "thin", RULE)]))
D_HEADER = dxf(font='<font>%s<color rgb="FFFFFFFF"/></font>' % FONT_B,
               fill=NAVY,
               border=edges([("left", "thin", GRID), ("right", "thin", GRID),
                             ("top", "thin", GRID), ("bottom", "thin", GRID)]))
D_TOTAL = dxf(font='<font>%s<color rgb="%s"/></font>' % (FONT_B, TEXT),
              fill=TOTAL_ROW,
              border=edges([("top", "medium", NAVY), ("bottom", "double", NAVY),
                            ("left", "thin", RULE), ("right", "thin", RULE)]))
D_STRIPE = dxf(fill=STRIPE)
D_SUB1 = dxf(font='<font>%s<color rgb="%s"/></font>' % (FONT_B, TEXT), fill=SUB1)
D_SUB2 = dxf(font='<font>%s<color rgb="%s"/></font>' % (FONT_B, TEXT), fill=SUB2)
D_SUB3 = dxf(font='<font>%s<color rgb="%s"/></font>' % (FONT10, TEXT), fill=SUB3)


def patch_styles(xml):
    # шрифт всей книги: стиль сводной задаёт свой, но подписи, которые
    # Excel рисует сам, берут шрифт из общих настроек книги
    xml = re.sub(r'<name val="[^"]*"/>', '<name val="%s"/>' % PIVOT_FONT, xml)

    if 'numFmtId="171"' not in xml:
        if "<numFmts" in xml:
            xml = re.sub(
                r'<numFmts count="(\d+)">',
                lambda m: '<numFmts count="%d">' % (int(m.group(1)) + 1)
                          + '<numFmt numFmtId="171" '
                            'formatCode="#,##0;(#,##0);&quot;–&quot;"/>',
                xml, count=1)
        else:
            xml = xml.replace(
                "<fonts", '<numFmts count="1"><numFmt numFmtId="171" '
                          'formatCode="#,##0;(#,##0);&quot;–&quot;"/>'
                          "</numFmts><fonts", 1)

    m = re.search(r'<dxfs count="(\d+)"\s*/>|<dxfs count="(\d+)">(.*?)</dxfs>',
                  xml, re.S)
    base = int(m.group(1) or m.group(2))
    body = m.group(3) or ""
    order = ["whole", "header", "total", "stripe", "sub1", "sub2", "sub3"]
    idx = {k: base + i for i, k in enumerate(order)}
    body += D_WHOLE + D_HEADER + D_TOTAL + D_STRIPE + D_SUB1 + D_SUB2 + D_SUB3
    xml = (xml[:m.start()] + '<dxfs count="%d">%s</dxfs>' % (base + 7, body)
           + xml[m.end():])

    style = ('<tableStyles count="1" defaultTableStyle="TableStyleMedium2"'
             ' defaultPivotStyle="ManpackPivotGreen">'
             '<tableStyle name="ManpackPivotGreen" pivot="1" count="7">'
             '<tableStyleElement type="wholeTable" dxfId="%d"/>'
             '<tableStyleElement type="headerRow" dxfId="%d"/>'
             '<tableStyleElement type="totalRow" dxfId="%d"/>'
             '<tableStyleElement type="firstRowStripe" size="1" dxfId="%d"/>'
             '<tableStyleElement type="firstSubtotalRow" size="1" dxfId="%d"/>'
             '<tableStyleElement type="secondSubtotalRow" size="1" dxfId="%d"/>'
             '<tableStyleElement type="thirdSubtotalRow" size="1" dxfId="%d"/>'
             '</tableStyle></tableStyles>'
             % (idx["whole"], idx["header"], idx["total"], idx["stripe"],
                idx["sub1"], idx["sub2"], idx["sub3"]))
    if "<tableStyles" in xml:
        xml = re.sub(r'<tableStyles.*?</tableStyles>|<tableStyles[^>]*/>',
                     style, xml, count=1, flags=re.S)
    else:
        xml = xml.replace("</styleSheet>", style + "</styleSheet>", 1)
    return xml


# ------------------------------------------------------------------ сборка
src = zipfile.ZipFile(SRC)
repl = {"xl/styles.xml": patch_styles(src.read("xl/styles.xml").decode("utf-8"))}
for key, cfg in PIVOTS.items():
    repl[cfg["cache"]] = build_cache(cfg)
    repl[cfg["table"]] = build_table(cfg)

# порядок листов: сначала обе сводные, источники — в конец
def reorder_sheets(xml):
    import re as _re
    block = _re.search(r"<sheets>(.*?)</sheets>", xml, _re.S)
    tags = _re.findall(r"<sheet [^>]*/>", block.group(1))
    order = ["Сводная CF", "Сводная P&amp;L", "raw_cf", "raw_pl"]
    by_name = {}
    for t in tags:
        by_name[_re.search(r'name="([^"]*)"', t).group(1)] = t
    ordered = [by_name[n] for n in order if n in by_name]
    ordered += [t for n, t in by_name.items() if n not in order]
    return xml[:block.start(1)] + "".join(ordered) + xml[block.end(1):]


repl["xl/workbook.xml"] = reorder_sheets(
    src.read("xl/workbook.xml").decode("utf-8"))


# Закрепление строк. Шапка сводной занимает три строки: год, месяц и день,
# поэтому закреплять надо по строку 6 включительно — иначе строка с датой
# уезжает вверх при прокрутке.
PIVOT_VIEW = ('<sheetViews><sheetView showGridLines="0" workbookViewId="0">'
              '<pane xSplit="1" ySplit="6" topLeftCell="B7"'
              ' activePane="bottomRight" state="frozen"/>'
              '<selection pane="bottomRight" activeCell="B7" sqref="B7"/>'
              '</sheetView></sheetViews>')

RAW_VIEW = ('<sheetViews><sheetView workbookViewId="0">'
            '<pane ySplit="1" topLeftCell="A2" activePane="bottomLeft"'
            ' state="frozen"/>'
            '<selection pane="bottomLeft" activeCell="A2" sqref="A2"/>'
            '</sheetView></sheetViews>')


def set_view(xml, view):
    import re as _re
    return _re.sub(r"<sheetViews>.*?</sheetViews>", view, xml, count=1,
                   flags=_re.S)


SHEET_VIEWS = {
    "xl/worksheets/sheet1.xml": PIVOT_VIEW,   # Сводная CF
    "xl/worksheets/sheet4.xml": PIVOT_VIEW,   # Сводная P&L
    "xl/worksheets/sheet2.xml": RAW_VIEW,     # raw_cf
    "xl/worksheets/sheet3.xml": RAW_VIEW,     # raw_pl
}

for part, view in SHEET_VIEWS.items():
    if part in src.namelist():
        repl[part] = set_view(src.read(part).decode("utf-8"), view)

out = zipfile.ZipFile(DST, "w", zipfile.ZIP_DEFLATED)
for info in src.infolist():
    data = repl.get(info.filename)
    out.writestr(info.filename,
                 data.encode("utf-8") if data else src.read(info.filename))
out.close()
src.close()
print("готово:", DST)
for key, cfg in PIVOTS.items():
    print(" ", key, "полей:", len(cfg["base"]) + 3,
          "| строки:", cfg["rows"],
          "| справочники:", {i: len(v) for i, v in sorted(cfg["values"].items())})
