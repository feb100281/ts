# gear/app/daily_sales/stocks/incident_compensation.py
"""
Расчёт компенсации ущерба продавцу WB по формуле п. 11.3.5-11.3.6
оферты "О реализации товара на сайте Wildberries" (действует
с 01.09.2026), на которую прямо ссылается Постановление
Правительства РФ от 25.08.2026 N 1074 "О мерах поддержки лиц,
пострадавших в результате атак БПЛА на объекты группы "РВБ"
(п. 3 Постановления: расчётная сумма ущерба определяется "в
порядке, аналогичном порядку определения размера компенсации,
предусмотренному пунктами 11.3.5 и 11.3.6 оферты").

ФОРМУЛА (п. 11.3.5 Оферты):

    Св = Ц - НДС - К - (Ц - НДС - К) * Нац%

    где:
        Ц    — Потенциальная цена (см. п. 11.3.6 Оферты и
               stocks/data.py::get_incident_potential_prices);
        НДС  — Ц * НДС% / (100% + НДС%), НДС% зависит от товара
               и от того, является ли продавец плательщиком НДС
               на дату выплаты компенсации;
        К    — комиссия Вайлдберриз по категории товара,
               К = Ц * К%;
        Нац% — наценка (надбавка к себестоимости) по категории
               товара, справочник WB.

СПРАВОЧНИКИ (получены от продавца, WB публикует их сама):

    stocks/reference/wb_commission_by_subject.csv
        Комиссия WB по каждому "Предмету" (справочник продавца,
        выгрузка с seller.wildberries.ru/dynamic-product-
        categories/commission). Используется колонка комиссии
        "Склад WB (FBW), %" — потому что происшествия на складах
        (пожары/атаки БПЛА) затрагивают именно физический остаток,
        хранящийся на складе WB, то есть способ продажи "Склад WB"
        (FBW).

    stocks/reference/wb_markup_by_category.csv
        "Размер наценки" по 79 укрупнённым категориям
        (Razmer_nacenki_20260203.pdf, официальный файл WB).

ИЗВЕСТНОЕ ОГРАНИЧЕНИЕ. Таксономия "Категория" в комиссионном
справочнике (97 значений) не совпадает 1:1 со старым списком
79 категорий в файле наценок — часть "Предметов" (например,
подкатегории автотоваров, "Электрика", "Готовая еда" и т.п.)
не находит наценку автоматически. Для таких позиций markup_pct
возвращается None, а в итоговой таблице соответствующая ячейка
остаётся жёлтой/пустой для ручного заполнения — как в
пользовательском образце. Считать наценку "по умолчанию" не
делаем: занижение/завышение ущерба — деньги господдержки.

Также НЕ реализовано ограничение Ц "Максимальной ценой по
Предмету" (п. 11.3.6, абз. 3) — оно требует розничных цен
ВСЕХ продавцов WB по Предмету, таких данных у нас нет.
"""

from __future__ import annotations

import csv
from pathlib import Path


_REFERENCE_DIR = Path(__file__).resolve().parent / "reference"

_COMMISSION_CSV = _REFERENCE_DIR / "wb_commission_by_subject.csv"
_MARKUP_CSV = _REFERENCE_DIR / "wb_markup_by_category.csv"


# Известные расхождения в написании категории между двумя
# справочниками WB (разных дат выгрузки). Пополнять по мере
# обнаружения новых расхождений.
_CATEGORY_ALIASES = {
    "Смартфоны и гаджеты": "Смартфоны и аксессуары",
    "Фото и Видеотехника": "Фото- и видеотехника",
    "Садовые инструменты и полив": "Садовые инструменты",
}


_commission_by_subject: dict[str, dict] | None = None
_markup_by_category: dict[str, float] | None = None


def _load_commission_by_subject() -> dict[str, dict]:
    global _commission_by_subject

    if _commission_by_subject is not None:
        return _commission_by_subject

    data = {}

    if _COMMISSION_CSV.exists():
        with open(_COMMISSION_CSV, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row in reader:
                subject = (row.get("subject") or "").strip()

                if not subject:
                    continue

                try:
                    fbw_pct = float(row.get("commission_fbw_pct"))
                except (TypeError, ValueError):
                    fbw_pct = None

                data[subject] = {
                    "category": (row.get("category") or "").strip(),
                    "commission_fbw_pct": fbw_pct,
                }

    _commission_by_subject = data

    return data


def _load_markup_by_category() -> dict[str, float]:
    global _markup_by_category

    if _markup_by_category is not None:
        return _markup_by_category

    data = {}

    if _MARKUP_CSV.exists():
        with open(_MARKUP_CSV, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)

            for row in reader:
                category = (row.get("category") or "").strip()

                if not category:
                    continue

                try:
                    markup_pct = float(row.get("markup_pct"))
                except (TypeError, ValueError):
                    continue

                data[category] = markup_pct

    _markup_by_category = data

    return data


def lookup_subject_reference(subject_name: str | None) -> dict:
    """
    По "Предмету" (subject_name, он же "Категория" в выгрузках
    остатков этого приложения) возвращает комиссию WB (К%, по
    складской продаже FBW) и наценку (Нац%, по укрупнённой
    категории). Любое из значений может быть None, если
    справочники не содержат такой "Предмет"/категорию — тогда
    поле нужно заполнить вручную в выгруженной таблице.
    """

    commission_map = _load_commission_by_subject()
    markup_map = _load_markup_by_category()

    subject_name = (subject_name or "").strip()

    commission_entry = commission_map.get(subject_name)

    category = (
        commission_entry["category"]
        if commission_entry
        else None
    )
    commission_pct = (
        commission_entry["commission_fbw_pct"]
        if commission_entry
        else None
    )

    markup_pct = None

    if category:
        markup_pct = markup_map.get(category)

        if markup_pct is None:
            aliased = _CATEGORY_ALIASES.get(category)

            if aliased:
                markup_pct = markup_map.get(aliased)

    return {
        "category": category,
        "commission_pct": commission_pct,
        "markup_pct": markup_pct,
    }


def compute_item_compensation(
    *,
    qty: float,
    potential_price: float | None,
    commission_pct: float | None,
    markup_pct: float | None,
    is_vat_payer: bool,
    vat_rate_pct: float | None,
) -> dict:
    """
    Считает компенсацию по одной позиции по формуле п. 11.3.5
    Оферты:

        Св = Ц - НДС - К - (Ц - НДС - К) * Нац%

    Если каких-то входных данных не хватает (Ц, К% или Нац%),
    возвращает частично заполненный результат с
    "is_complete": False и "compensation_total": None — такая
    строка в Excel остаётся для ручного заполнения, автосумма
    её не учитывает (и НЕ считает эту позицию нулевым ущербом).
    """

    qty = float(qty or 0)

    nds_pct = (
        float(vat_rate_pct)
        if (is_vat_payer and vat_rate_pct is not None)
        else 0.0
    )

    missing = (
        potential_price is None
        or commission_pct is None
        or markup_pct is None
    )

    if missing:
        return {
            "is_complete": False,
            "potential_price": potential_price,
            "commission_pct": commission_pct,
            "markup_pct": markup_pct,
            "vat_rate_pct": vat_rate_pct if is_vat_payer else 0.0,
            "nds_rub": None,
            "commission_rub": None,
            "compensation_per_unit": None,
            "compensation_total": None,
        }

    potential_price = float(potential_price)
    commission_pct = float(commission_pct)
    markup_pct = float(markup_pct)

    nds_rub = (
        potential_price * nds_pct / (100.0 + nds_pct)
        if nds_pct > 0
        else 0.0
    )

    commission_rub = potential_price * commission_pct / 100.0

    base = potential_price - nds_rub - commission_rub

    markup_rub = base * markup_pct / 100.0

    compensation_per_unit = base - markup_rub

    # Отрицательный ущерб не имеет смысла (комиссия/наценка не
    # должны "съедать" сверх цены) — на практике при корректных
    # входных данных этого не происходит, но подстраховываемся.
    compensation_per_unit = max(compensation_per_unit, 0.0)

    return {
        "is_complete": True,
        "potential_price": potential_price,
        "commission_pct": commission_pct,
        "markup_pct": markup_pct,
        "vat_rate_pct": nds_pct,
        "nds_rub": nds_rub,
        "commission_rub": commission_rub,
        "compensation_per_unit": compensation_per_unit,
        "compensation_total": compensation_per_unit * qty,
    }
