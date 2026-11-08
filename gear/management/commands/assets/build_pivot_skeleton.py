# -*- coding: utf-8 -*-
"""Пересборка листа «Сводная CF» в assets/pivot_skeleton.xlsx.

ВАЖНО: скелет собирается этим скриптом, а не руками в Excel.
Если открыть pivot_skeleton.xlsx в Excel и сохранить, Excel перепишет
описание сводной по-своему и потеряет группировку дат (год -> месяц ->
день), шрифт Helvetica Light, стиль ManpackPivotGreen и флаги
свёрнутости уровней. Восстанавливается одной командой:

    python3 gear/management/commands/assets/build_pivot_skeleton.py
    mv gear/management/commands/assets/pivot_skeleton.xlsx.new \
       gear/management/commands/assets/pivot_skeleton.xlsx

Что делает скрипт:
  * кладёт в кэш сводной настоящие справочники значений — иначе Excel при
    обновлении создаёт элементы заново и теряет состояние свёрнутости;
  * добавляет служебные поля группировки дат Months / Quarters / Years;
  * строит шесть уровней строк: вид деятельности -> операция -> статья ->
    подстатья -> контрагент -> договор, свёрнутых до второго;
  * колонки: год -> месяц -> день, свёрнуты до года;
  * прописывает стиль ManpackPivotGreen и делает его стилем по умолчанию.
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


import os, re, sys, zipfile

HERE = os.path.dirname(os.path.abspath(__file__))
SRC = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, "pivot_skeleton.xlsx")
DST = sys.argv[2] if len(sys.argv) > 2 else SRC + ".new"

NAVY, TOTAL_ROW, STRIPE = "FF2F6656", "FFE7F1ED", "FFF6F6F6"
SUB1, SUB2, SUB3 = "FFE7F1ED", "FFEDF5F1", "FFF3F8F6"
RULE = "FFE6E6E6"        # светло-серые разделители колонок
GRID, TEXT = "FFD4DDD9", "FF1F1F1F"
ANCHOR_DATE = "2026-03-17T00:00:00"


def esc(s):
    return (s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
             .replace('"', "&quot;"))


# --------------------------------------------------------------- кэш сводной
def shared(values):
    return ('<sharedItems count="%d">%s</sharedItems>'
            % (len(values), "".join('<s v="%s"/>' % esc(v) for v in values)))


PLAIN = '<sharedItems containsNonDate="0" containsString="0" containsBlank="1"/>'


# ------------------------------------------------- группировка дат Excel
#  Год → месяц → день: три служебных поля группировки, которые Excel
#  создаёт сам при команде «Сгруппировать» на поле даты. Мы описываем их
#  ровно в том же виде, поэтому Excel принимает их как свои.
G_START, G_END = "2023-09-22T00:00:00", "2026-03-18T00:00:00"
MON = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
DAYS_IN = [31,29,31,30,31,30,31,31,30,31,30,31]

DAY_ITEMS = (["&lt;" + G_START[:10]]
             + ["%02d-%s" % (d, MON[m]) for m in range(12)
                for d in range(1, DAYS_IN[m] + 1)]
             + ["&gt;" + G_END[:10]])
MONTH_ITEMS = ["&lt;" + G_START[:10]] + MON + ["&gt;" + G_END[:10]]
YEAR_ITEMS = ["&lt;" + G_START[:10], "2023", "2024", "2025", "2026",
              "&gt;" + G_END[:10]]


def group_items(vals):
    return ('<groupItems count="%d">%s</groupItems>'
            % (len(vals), "".join('<s v="%s"/>' % v for v in vals)))


def range_pr(by):
    return ('<rangePr autoStart="1" autoEnd="1" groupBy="%s" startDate="%s"'
            ' endDate="%s" groupInterval="1"/>' % (by, G_START, G_END))


DAY_GROUP = ('<fieldGroup par="17" base="0">%s%s</fieldGroup>'
             % (range_pr("days"), group_items(DAY_ITEMS)))


def group_field(name, by, vals):
    return ('<cacheField name="%s" numFmtId="0" databaseField="0">'
            '<fieldGroup base="0">%s%s</fieldGroup></cacheField>'
            % (name, range_pr(by), group_items(vals)))


GROUP_FIELDS = (group_field("Months", "months", MONTH_ITEMS)
                + group_field("Quarters", "quarters", ["&lt;" + G_START[:10],
                    "Qtr1", "Qtr2", "Qtr3", "Qtr4", "&gt;" + G_END[:10]])
                + group_field("Years", "years", YEAR_ITEMS))



CACHE_FIELDS = [
    ("date_from", "165",
     '<sharedItems count="1" containsSemiMixedTypes="0" containsNonDate="0"'
     ' containsDate="1" containsString="0" minDate="%s" maxDate="%s">'
     '<d v="%s"/></sharedItems>' % (ANCHOR_DATE, ANCHOR_DATE, ANCHOR_DATE)
     + DAY_GROUP),
    ("acc_id", "0", PLAIN),
    ("subconto_id", "0", PLAIN),
    ("contract_id", "0", PLAIN),
    ("contract_name", "0", shared(CONTRACT)),
    ("cp_name", "0", shared(CP_NAME)),
    ("account_name", "0", PLAIN),
    ("activity", "0", shared(ACTIVITY)),
    ("operation", "0", shared(OPERATION)),
    ("item", "0", shared(ITEM)),
    ("subitem", "0", shared(SUBITEM)),
    ("description", "0", PLAIN),
    ("dt", "0", PLAIN),
    ("cr", "0", PLAIN),
    ("amount", "0", PLAIN),
]

CACHE = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<pivotCacheDefinition'
    ' xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
    ' xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships"'
    ' saveData="0" refreshOnLoad="1" missingItemsLimit="0" createdVersion="8"'
    ' refreshedVersion="8" minRefreshableVersion="3" recordCount="0">'
    '<cacheSource type="worksheet"><worksheetSource name="raw_cf"/></cacheSource>'
    '<cacheFields count="%d">%s%s</cacheFields>'
    '</pivotCacheDefinition>'
    % (len(CACHE_FIELDS) + 3,
       "".join('<cacheField name="%s" numFmtId="%s">%s</cacheField>'
               % (esc(n), nf, si) for n, nf, si in CACHE_FIELDS),
       GROUP_FIELDS))


# ------------------------------------------------------------ сама сводная
def items(n, collapsed):
    """Элементы поля. collapsed=True → уровень открывается по кнопке «+»."""
    sd = ' sd="0"' if collapsed else ""
    body = "".join('<item%s x="%d"/>' % (sd, i) for i in range(n))
    return '<items count="%d">%s<item t="default"%s/></items>' % (n + 1, body, sd)


ROW = 'axis="axisRow" showAll="0"'
PF = [
    '<pivotField axis="axisCol" numFmtId="165" showAll="0">%s</pivotField>'
    % items(len(DAY_ITEMS), True),
    '<pivotField showAll="0"/>',                                   # acc_id
    '<pivotField showAll="0"/>',                                   # subconto_id
    '<pivotField showAll="0"/>',                                   # contract_id
    '<pivotField %s>%s</pivotField>' % (ROW, items(len(CONTRACT), False)),
    '<pivotField %s>%s</pivotField>' % (ROW, items(len(CP_NAME), True)),
    '<pivotField showAll="0"/>',                                   # account_name
    '<pivotField %s>%s</pivotField>' % (ROW, items(len(ACTIVITY), False)),
    '<pivotField %s>%s</pivotField>' % (ROW, items(len(OPERATION), True)),
    '<pivotField %s>%s</pivotField>' % (ROW, items(len(ITEM), True)),
    '<pivotField %s>%s</pivotField>' % (ROW, items(len(SUBITEM), True)),
    '<pivotField showAll="0"/>',                                   # description
    '<pivotField showAll="0"/>',                                   # dt
    '<pivotField showAll="0"/>',                                   # cr
    '<pivotField dataField="1" showAll="0"/>',                     # amount
    '<pivotField axis="axisCol" showAll="0">%s</pivotField>'        # Months
    % items(len(MONTH_ITEMS), True),
    '<pivotField showAll="0"/>',                                   # Quarters
    '<pivotField axis="axisCol" showAll="0">%s</pivotField>'        # Years
    % items(len(YEAR_ITEMS), True),
]

# исходная раскладка: первый уровень раскрыт, второй свёрнут
# держим её минимальной — ровно под те ячейки, что уже лежат на листе;
# полную таблицу Excel строит сам при открытии (refreshOnLoad)
TREE = [(0, [0])]
row_items, nrows = [], 0
for a, ops in TREE:
    row_items.append('<i><x v="%d"/></i>' % a)
    nrows += 1
    for o in ops:
        row_items.append('<i r="1"><x v="%d"/></i>' % o)
        nrows += 1
row_items.append('<i t="grand"><x/></i>')
nrows += 1

last_row = 3 + 1 + nrows                       # строка 3 — подпись, 4 — шапка
PIVOT = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<pivotTableDefinition'
    ' xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"'
    ' name="PivotTable5" cacheId="534" applyNumberFormats="1"'
    ' applyBorderFormats="0" applyFontFormats="0" applyPatternFormats="0"'
    ' applyAlignmentFormats="0" applyWidthHeightFormats="1"'
    ' dataCaption="Values" updatedVersion="8" minRefreshableVersion="3"'
    ' useAutoFormatting="1" itemPrintTitles="1" createdVersion="8" indent="0"'
    ' showHeaders="0" outline="1" outlineData="1" multipleFieldFilters="0"'
    ' grandTotalCaption="ИТОГО">'
    '<location ref="A3:C%d" firstHeaderRow="1" firstDataRow="2" firstDataCol="1"/>'
    '<pivotFields count="%d">%s</pivotFields>'
    '<rowFields count="6">'
    '<field x="7"/><field x="8"/><field x="9"/><field x="10"/>'
    '<field x="5"/><field x="4"/>'
    '</rowFields>'
    '<rowItems count="%d">%s</rowItems>'
    '<colFields count="3">'
    '<field x="17"/><field x="15"/><field x="0"/>'
    '</colFields>'
    '<colItems count="2"><i><x v="1"/></i><i t="grand"><x/></i></colItems>'
    '<dataFields count="1">'
    '<dataField name="в российских рублях (RUB)" fld="14" baseField="0"'
    ' baseItem="0" numFmtId="171"/>'
    '</dataFields>'
    '<pivotTableStyleInfo name="ManpackPivotGreen" showRowHeaders="1"'
    ' showColHeaders="1" showRowStripes="1" showColStripes="0"'
    ' showLastColumn="1"/>'
    '</pivotTableDefinition>')


# ------------------------------------------------------------------ стили
def dxf(font=None, numfmt=None, fill=None, border=None):
    out = "<dxf>"
    if font:
        out += font
    if numfmt:
        out += numfmt
    if fill:
        out += ('<fill><patternFill patternType="solid">'
                '<fgColor rgb="%s"/><bgColor rgb="%s"/>'
                '</patternFill></fill>' % (fill, fill))
    if border:
        out += border
    return out + "</dxf>"


def edges(spec):
    return ("<border>"
            + "".join('<%s style="%s"><color rgb="%s"/></%s>' % (s, st, c, s)
                      for s, st, c in spec)
            + "</border>")


D_WHOLE = dxf(font='<font><sz val="10"/><name val="Helvetica Light"/></font>',
              border=edges([("left", "thin", RULE), ("right", "thin", RULE)]))
D_HEADER = dxf(font='<font><b/><sz val="10"/><color rgb="FFFFFFFF"/>'
                    '<name val="Helvetica Light"/></font>',
               fill=NAVY,
               border=edges([("left", "thin", GRID), ("right", "thin", GRID),
                             ("top", "thin", GRID), ("bottom", "thin", GRID)]))
D_TOTAL = dxf(font='<font><b/><sz val="10"/><color rgb="%s"/>'
                   '<name val="Helvetica Light"/></font>' % TEXT,
              fill=TOTAL_ROW,
              border=edges([("top", "medium", NAVY),
                            ("bottom", "double", NAVY),
                            ("left", "thin", RULE), ("right", "thin", RULE)]))
D_SUB1 = dxf(font='<font><b/><sz val="10"/><color rgb="%s"/>'
                  '<name val="Helvetica Light"/></font>' % TEXT,
             fill=SUB1,
             border=edges([("left", "thin", RULE), ("right", "thin", RULE)]))
D_SUB2 = dxf(font='<font><b/><sz val="10"/><color rgb="%s"/>'
                  '<name val="Helvetica Light"/></font>' % TEXT,
             fill=SUB2,
             border=edges([("left", "thin", RULE), ("right", "thin", RULE)]))
D_SUB3 = dxf(font='<font><sz val="10"/><color rgb="%s"/>'
                  '<name val="Helvetica Light"/></font>' % TEXT,
             fill=SUB3,
             border=edges([("left", "thin", RULE), ("right", "thin", RULE)]))
D_STRIPE = dxf(fill=STRIPE)


def patch_styles(xml):
    # шрифт листа сводной — Helvetica Light 10
    xml = xml.replace('<sz val="11"/><color theme="1"/>'
                      '<name val="Roboto Condensed Light"/>',
                      '<sz val="10"/><color theme="1"/>'
                      '<name val="Helvetica Light"/>')
    xml = xml.replace('<u/><sz val="11"/><color theme="10"/>'
                      '<name val="Roboto Condensed Light"/>',
                      '<u/><sz val="10"/><color theme="10"/>'
                      '<name val="Helvetica Light"/>')
    xml = xml.replace('<b/><sz val="18"/><color theme="1"/>'
                      '<name val="Roboto Condensed Light"/>',
                      '<b/><sz val="18"/><color theme="1"/>'
                      '<name val="Helvetica Light"/>')

    # формат «в скобках» для отрицательных
    if 'numFmtId="171"' not in xml:
        xml = re.sub(
            r'<numFmts count="(\d+)">',
            lambda m: '<numFmts count="%d">' % (int(m.group(1)) + 1)
                      + '<numFmt numFmtId="171" '
                        'formatCode="#,##0;(#,##0);&quot;–&quot;"/>',
            xml, count=1)

    # ячейки листа сводной считают тем же форматом
    m = re.search(r'<cellXfs count="\d+">.*?</cellXfs>', xml, re.S)
    xml = (xml[:m.start()]
           + m.group(0).replace('numFmtId="164"', 'numFmtId="171"')
           + xml[m.end():])

    m = re.search(r'<dxfs count="(\d+)">(.*?)</dxfs>', xml, re.S)
    body, base = m.group(2), int(m.group(1))
    order = ["whole", "header", "total", "stripe", "sub1", "sub2", "sub3"]
    idx = {k: base + i for i, k in enumerate(order)}
    body += D_WHOLE + D_HEADER + D_TOTAL + D_STRIPE + D_SUB1 + D_SUB2 + D_SUB3
    xml = (xml[:m.start()]
           + '<dxfs count="%d">%s</dxfs>' % (base + len(order), body)
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
    xml = re.sub(r'<tableStyles.*?</tableStyles>|<tableStyles[^>]*/>',
                 style, xml, count=1, flags=re.S)
    return xml, idx["whole"]


# ------------------------------------------------------------------ сборка
src = zipfile.ZipFile(SRC)
styles, date_dxf = patch_styles(src.read("xl/styles.xml").decode("utf-8"))
pivot = PIVOT % (last_row, len(PF), "".join(PF), len(row_items),
                 "".join(row_items))

repl = {
    "xl/pivotCache/pivotCacheDefinition1.xml": CACHE,
    "xl/pivotTables/pivotTable1.xml": pivot,
    "xl/styles.xml": styles,
}

out = zipfile.ZipFile(DST, "w", zipfile.ZIP_DEFLATED)
for info in src.infolist():
    data = repl.get(info.filename)
    out.writestr(info.filename,
                 data.encode("utf-8") if data else src.read(info.filename))
out.close()
src.close()

print("готово:", DST)
print("строк в исходной раскладке:", nrows, "→ location A3:C%d" % last_row)
print("колонки: Years -> Months -> дни, элементов дней:", len(DAY_ITEMS))
