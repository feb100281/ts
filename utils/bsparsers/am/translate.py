"""
Перевод назначений по словарю шаблонов.

В шаблоне числа и коды с цифрами заменены на #, названия месяцев — на @.
Перевод хранится один раз на шаблон. При подстановке # получают исходные числа,
@ — месяц по-русски; если в переводе нет @, месяц опускается («Зарплата»).
"""

import hashlib
import re

NUM = r"[A-Za-z0-9]*\d[A-Za-z0-9]*(?:[.,]\d+)*"          # 5443XXXX0036, 8BY4, 1,250.00
MONTHS_HY = ["հունվար", "փետրվար", "մարտ", "ապրիլ", "մայիս", "հունիս", "հուլիս",
             "օգոստոս", "սեպտեմբեր", "հոկտեմբեր", "նոյեմբեր", "դեկտեմբեր"]
MONTHS_RU = ["январь", "февраль", "март", "апрель", "май", "июнь", "июль",
             "август", "сентябрь", "октябрь", "ноябрь", "декабрь"]
MONTHS_RU_GEN = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля",
                 "августа", "сентября", "октября", "ноября", "декабря"]
MONTH = r"\b(?:" + "|".join(MONTHS_HY) + r")(?:ի)?\b"
TOKEN = re.compile(f"(?P<num>{NUM})|(?P<month>{MONTH})", re.I)


def _month_ru(word: str) -> str:
    w = word.lower()
    genitive = w.endswith("ի") and w[:-1] in MONTHS_HY
    i = MONTHS_HY.index(w[:-1] if genitive else w)
    return MONTHS_RU_GEN[i] if genitive else MONTHS_RU[i]


def template(text: str) -> tuple[str, list[tuple[str, str]]]:
    """Шаблон и значения по порядку: ('#', число) или ('@', месяц по-русски)."""
    values = []

    def sub(m):
        if m.group("num"):
            values.append(("#", m.group("num")))
            return "#"
        values.append(("@", _month_ru(m.group("month"))))
        return "@"

    return TOKEN.sub(sub, text or ""), values


def key_of(tpl: str) -> str:
    return hashlib.sha1(tpl.encode("utf-8")).hexdigest()


def fill(translation: str, values: list[tuple[str, str]]) -> str:
    """Подставить значения по порядку. Если число # не совпадает — перевод без подстановки."""
    nums = [v for k, v in values if k == "#"]
    months = [v for k, v in values if k == "@"]
    if translation.count("#") != len(nums):
        return translation
    it_n, it_m = iter(nums), iter(months)
    out = re.sub("#", lambda _: next(it_n), translation)
    return re.sub("@", lambda _: next(it_m, ""), out)


# ============================================================
# Названия контрагентов по-русски
# ============================================================

_HY_RU = {
    "ա": "а", "բ": "б", "գ": "г", "դ": "д", "ե": "е", "զ": "з", "է": "э", "ը": "ы", "թ": "т", "ժ": "ж",
    "ի": "и", "լ": "л", "խ": "х", "ծ": "ц", "կ": "к", "հ": "х", "ձ": "дз", "ղ": "г", "ճ": "ч", "մ": "м",
    "յ": "й", "ն": "н", "շ": "ш", "ո": "о", "չ": "ч", "պ": "п", "ջ": "дж", "ռ": "р", "ս": "с", "վ": "в",
    "տ": "т", "ր": "р", "ց": "ц", "ւ": "в", "փ": "п", "ք": "к", "և": "ев", "օ": "о", "ֆ": "ф",
}
ORG_FORMS = {"ՍՊԸ": "ООО", "ՓԲԸ": "ЗАО", "ԲԲԸ": "ОАО", "ԱՁ": "ИП", "ՀԿ": "ОО", "ՊՈԱԿ": "ГНКО", "ՀՈԱԿ": "ОНКО",
             "LLC": "ООО", "LLP": "ТОО", "CJSC": "ЗАО", "OJSC": "ОАО", "JSC": "АО"}
_ARM = re.compile(r"[Ա-և]")


# служебные «контрагенты» банков — переводим, а не транслитерируем
NAME_PHRASES = [
    ("տարանցիկ հաշիվ", "транзитный счёт"),
    ("Փոխհաշվարկ ՊՔ-ի և տերմինալ.միջև", "Расчёты между ПК и терминалом"),
    ("Փոխհաշվարկ ՊՔ-ի — տերմինալ.միջ—", "Расчёты между ПК и терминалом"),
    ("Արտաքին տնտեսական կոդ", "Внешнеэкономический код"),
    ("համագործակց. եկամուտ", "доход от сотрудничества"),
    ("սպասարկումից եկամուտ", "доход от обслуживания"),
    ("պարզաբանվող", "до выяснения"),
]


def _translit_word(word: str) -> str:
    low = word.lower().replace("ու", "у").replace("յու", "ю").replace("յա", "я").replace("յե", "е")
    low = low.replace("յу", "ю")
    out = []
    for i, ch in enumerate(low):
        if ch == "ե" and i == 0:
            out.append("е")
        elif ch == "ո" and i == 0:
            out.append("во")
        else:
            out.append(_HY_RU.get(ch, ch))
    res = "".join(out)
    return res[:1].upper() + res[1:] if word[:1].isupper() else res


def cp_name_ru(name: str) -> str:
    """«ԻԴՐԱՄ ՍՊԸ» → «ООО «Идрам»», «Արամյան Անահիտ Հայկի» → «Арамян Анахит Хайки». Латиница — как есть."""
    s = " ".join((name or "").replace("*", " ").split())
    m = re.search(r"1/\s*(.+?)(?:\s+\d/|$)", s)                # Ардшин: «1/ имя 2/ИНН 8/адрес»
    if m:
        s = m.group(1)
    s = re.sub(r"\s+\d+/\S*", "", s).strip(" ,")             # хвосты вида «2/02588245»
    if not s:
        return ""
    for hy, ru in NAME_PHRASES:
        s = s.replace(hy, ru)
    form = ""
    words = []
    for w in re.findall(r"[^\s«»\"']+", s):
        key = w.strip(".,").upper()
        if key in ORG_FORMS and not form:
            form = ORG_FORMS[key]
            continue
        if _ARM.search(w):
            w = _translit_word(w.capitalize() if w.isupper() or not w[:1].isupper() else w)
        words.append(w)
    body = " ".join(words)
    return f"{form} «{body}»" if form and body else (body or form)
