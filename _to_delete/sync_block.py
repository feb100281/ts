PIVOT_LAYOUT = {
    "xl/pivotTables/pivotTable1.xml": {
        "cache": "xl/pivotCache/pivotCacheDefinition1.xml",
        "source": "raw_cf",
        "rows": ["activity", "operation", "item", "subitem",
                 "cp_name", "contract_name"],
    },
    "xl/pivotTables/pivotTable2.xml": {
        "cache": "xl/pivotCache/pivotCacheDefinition2.xml",
        "source": "raw_pl",
        "rows": ["parent_account_name", "account_name", "cost_item_group",
                 "cost_item", "cp_name", "contract_name"],
    },
}

# сколько верхних уровней открыто при открытии файла
PIVOT_OPEN_LEVELS = 2


def sync_pivot_items(path, data):
    """Переписывает справочники значений сводных под фактические данные.

    Зачем. Уровень сводной свёрнут, если у КАЖДОГО его элемента стоит
    признак «не раскрывать». Признак живёт у конкретного значения, а не у
    поля целиком, поэтому значение, которого не было в справочнике,
    Excel после обновления показывает раскрытым. Появилась новая статья
    или контрагент — и ветка открывается сама.

    Поэтому перед выдачей файла складываем в справочники ровно те
    значения, которые лежат в источнике, и всем уровням ниже
    PIVOT_OPEN_LEVELS проставляем «свёрнуто».
    """
    import xml.etree.ElementTree as ET
    import shutil
    import tempfile
    import zipfile

    ns = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
    ET.register_namespace("", ns)
    tag = lambda name: "{%s}%s" % (ns, name)

    def distinct(columns, rows, name):
        if name not in columns:
            return [], False
        i = columns.index(name)
        seen, blank = set(), False
        for row in rows:
            value = row[i]
            text = "" if value is None else str(value).strip()
            if text:
                seen.add(text)
            else:
                blank = True
        return sorted(seen), blank

    src = zipfile.ZipFile(path)
    parts = {}

    for table_part, cfg in PIVOT_LAYOUT.items():
        if table_part not in src.namelist() or cfg["source"] not in data:
            continue

        columns, rows = data[cfg["source"]]
        cache = ET.fromstring(src.read(cfg["cache"]))
        table = ET.fromstring(src.read(table_part))

        cache_fields = list(cache.find(tag("cacheFields")))
        pivot_fields = list(table.find(tag("pivotFields")))
        names = [f.get("name") for f in cache_fields]

        for level, name in enumerate(cfg["rows"]):
            if name not in names:
                continue
            index = names.index(name)
            values, blank = distinct(columns, rows, name)
            if not values and not blank:
                continue

            collapsed = level >= PIVOT_OPEN_LEVELS

            shared = ET.SubElement(cache_fields[index], tag("sharedItems"))
            cache_fields[index].remove(shared)
            shared = ET.Element(tag("sharedItems"))
            shared.set("count", str(len(values) + (1 if blank else 0)))
            if blank:
                shared.set("containsBlank", "1")
            for value in values:
                ET.SubElement(shared, tag("s")).set("v", value)
            if blank:
                ET.SubElement(shared, tag("m"))

            old = cache_fields[index].find(tag("sharedItems"))
            if old is not None:
                cache_fields[index].remove(old)
            cache_fields[index].insert(0, shared)

            items = ET.Element(tag("items"))
            total = len(values) + (1 if blank else 0)
            items.set("count", str(total + 1))
            for i in range(total):
                item = ET.SubElement(items, tag("item"))
                item.set("x", str(i))
                if collapsed:
                    item.set("sd", "0")
            default = ET.SubElement(items, tag("item"))
            default.set("t", "default")
            if collapsed:
                default.set("sd", "0")

            old = pivot_fields[index].find(tag("items"))
            if old is not None:
                pivot_fields[index].remove(old)
            pivot_fields[index].append(items)

        parts[cfg["cache"]] = ET.tostring(cache, encoding="UTF-8",
                                          xml_declaration=True)
        parts[table_part] = ET.tostring(table, encoding="UTF-8",
                                        xml_declaration=True)

    if not parts:
        src.close()
        return 0

    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".xlsx")
    tmp.close()

    out = zipfile.ZipFile(tmp.name, "w", zipfile.ZIP_DEFLATED)
    for info in src.infolist():
        out.writestr(info, parts.get(info.filename) or src.read(info.filename))
    out.close()
    src.close()

    shutil.move(tmp.name, path)
    return len(parts) // 2
