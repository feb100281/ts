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
             "LLC": "ООО", "LLP": "ТОО", "CJSC": "ЗАО", "OJSC": "ОАО", "JSC": "АО",
             "OOO": "ООО", "ZAO": "ЗАО", "AO": "АО", "PAO": "ПАО", "IP": "ИП"}
_ARM = re.compile(r"[Ա-և]")


# госорганы и служебные «контрагенты» банков — переводим, а не транслитерируем (проверяются по порядку)
NAME_PHRASES = [
    ("Առողջության համընդհանուր ապահովագրության ապահովագրավճարներ", "ВЗНОСЫ НА ВСЕОБЩЕЕ МЕДСТРАХОВАНИЕ"),
    ("ՀՀ պետական եկամուտների կոմիտե", "КГД РА"),
    ("Հարկերի միասնական հաշիվ", "ЕДИНЫЙ НАЛОГОВЫЙ СЧЁТ"),
    ("Այլ միջնորդավճարներ ֆինանսական կազ", "ПРОЧИЕ КОМИССИИ ФИНОРГАНИЗАЦИЙ"),
    ("տարանցիկ հաշիվ", "ТРАНЗИТНЫЙ СЧЁТ"),
    ("Փոխհաշվարկ ՊՔ-ի և տերմինալ.միջև", "РАСЧЁТЫ МЕЖДУ ПК И ТЕРМИНАЛОМ"),
    ("Փոխհաշվարկ ՊՔ-ի — տերմինալ.միջ—", "РАСЧЁТЫ МЕЖДУ ПК И ТЕРМИНАЛОМ"),
    ("Արտաքին տնտեսական կոդ", "ВНЕШНЕЭКОНОМИЧЕСКИЙ КОД"),
    ("համագործակց. եկամուտ", "ДОХОД ОТ СОТРУДНИЧЕСТВА"),
    ("համագործակց. եկամու", "ДОХОД ОТ СОТРУДНИЧЕСТВА"),
    ("սպասարկումից եկամուտ", "ДОХОД ОТ ОБСЛУЖИВАНИЯ"),
    ("պարզաբանվող", "ДО ВЫЯСНЕНИЯ"),
]
# целиком по началу или ключевым словам — длинные названия госреестров и налогов
NAME_STARTS = [
    ("Պետական ռեգիստր", "ГОСРЕГИСТР ЮРЛИЦ"),
    ("բնապահպանական հարկ", "ЭКОЛОГИЧЕСКИЙ НАЛОГ НА ИМПОРТ"),
]


def _translit_word(word: str) -> str:
    low = word.lower().replace("յու", "ю").replace("ու", "у").replace("յա", "я").replace("յե", "е")
    out = []
    for i, ch in enumerate(low):
        if ch == "ե" and i == 0:
            out.append("е")
        elif ch == "ո" and i == 0:
            out.append("во")
        else:
            out.append(_HY_RU.get(ch, ch))
    return "".join(out)


def _swift_name(s: str) -> str:
    """«1/Имя 1/продолжение 2/адрес 3/страна» → имя; строки 1/ склеиваются (SWIFT режет по 35 знаков)."""
    parts = re.split(r"(?:^|\s)(\d)/", " " + s)
    name = ""
    for i in range(1, len(parts) - 1, 2):
        if parts[i] == "1":
            name += parts[i + 1].strip() if not name else parts[i + 1].rstrip()
    return name.strip() or s


def cp_name_ru(name: str) -> str:
    """Название контрагента по-русски, заглавными, форма в конце: «ԻԴՐԱՄ ՍՊԸ» → «ИДРАМ ООО»."""
    s = " ".join((name or "").replace("*", " ").split())
    if not s:
        return ""
    if re.search(r"(?:^|\s)1/", s):
        s = _swift_name(s)
    s = re.sub(r"^INN\d+(?:\.KPP\d+)?\s*", "", s)                # ИНН/КПП из платежей РФ
    s = re.split(r"\s*//|\s+\d{6},|,\s*UL\.", s)[0]                  # адрес после //, индекса или «UL.»
    s = re.sub(r"\s+\d+/\S*", "", s).strip(" ,")
    for hy, ru in NAME_STARTS:
        if hy.lower() in s.lower():
            return ru
    for hy, ru in NAME_PHRASES:
        s = s.replace(hy, ru)
    form, words = "", []
    for w in re.findall(r"[^\s«»\"']+", s):
        key = w.strip(".,").upper()
        if key in ORG_FORMS and not form:
            form = ORG_FORMS[key]
            break                                                    # после формы — адрес
        if key == "ՀՀ":
            w = "РА"
        elif _ARM.search(w):
            w = _translit_word(w)
        words.append(w)
    body = re.sub(r"\s+,", ",", " ".join(words)).strip(" ,").upper()
    return f"{body} {form}".strip() if body else form
