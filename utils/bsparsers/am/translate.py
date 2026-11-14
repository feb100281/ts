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
