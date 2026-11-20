"""План разноски Армении: контрагенты, счета, договоры и правила статей. Без --apply только показывает."""
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.db.models import Q

from contracts.models import CfItemAuto, Contracts, ContractsTitle
from corporate.models import COA, CfItems, Owners
from counterparties.models import Counterparty
from treasury.models import CfData, CounterpartyAccount
from utils.bsparsers.am.loader import auto_assign, unassigned

OWNER_TAX = "00532316"
OWN = ["11817103567800", "1570016863008700", "1570016863000146", "1570016863000158", "1570016863000101",
       "1150011484654604", "2470003205871007", "2470003205871052", "2470003205871025", "2470003205871070",
       "2470003205871061", "2470003205871034", "16062007242300", "16062007242301", "1570016863000110"]


def K(title, regex=None, st=None, bs=None, sbs=None, pl=None, spl=None, cf=None, cur="AMD"):
    """Договор: тип, RegEx карточки, счета (коды), статья CF для Дт и Кт."""
    return dict(title=title, regex=regex, st=st, bs=bs, sbs=sbs, pl=pl, spl=spl, cf=cf, cur=cur)


ACQ = dict(st="799100", cf="111300")                                   # поступления розницы
FEE = dict(st="720001", pl="610000", spl="540204", cf="123992")        # комиссия эквайринга
RKO = dict(st="720001", pl="610000", spl="540203", cf="123100")        # комиссии банка
GOODS = dict(st="720001", bs="130001", sbs="610101", cf="121100")      # закуп товара
LOGIST = dict(st="720001", pl="520000", spl="520302", cf="121200")     # логистика закупа

CERT = dict(st="720001", pl="520000", spl="520304", cf="121440")    # маркировка, сертификация
CUSTOMS_SRV = dict(st="720001", pl="520000", spl="520303", cf="121400")  # брокер, таможенный склад
STORAGE = dict(st="720001", pl="610000", spl="540302", cf="123500")  # склад
RENT = dict(st="720001", pl="610000", spl="540306", cf="123500")     # аренда торговых помещений
NET = dict(st="720001", pl="610000", spl="540406", cf="123700")      # интернет и связь
LABELS = dict(st="720001", pl="610000", spl="540501", cf="123930")   # ценники, стикеры
ADS = dict(st="720001", pl="610000", spl="540110", cf="123900")      # типография, реклама
CONTENT = dict(st="720001", pl="610000", spl="540109", cf="123900")  # фото, видео, UGC
OFFICE = dict(st="720001", pl="620000", spl="540601", cf="123930")   # канцелярия, хознужды
EQUIP = dict(st="720001", pl="610000", spl="540503", cf="123920")    # торговое оборудование
PACK = dict(st="720001", pl="610000", spl="540502", cf="121300")     # пакеты, упаковка
REPAIR = dict(st="720001", pl="620000", spl="540602", cf="123970")   # мелкий ремонт магазина
SECRETARY = dict(st="720001", pl="620000", spl="580103", cf="123930")  # переводы документов

# поставщики по реестру расходов коллег: (название, счёт, шаблон)
SUPPLIERS = [
    ("ЭСЭЛЭС СЕНТР ООО (SLS CENTER)", "1510064545585400", CERT),
    ("ФИВИ ЗАО", "1570026516910100", GOODS),
    ("ФИВИ ЗАО", "11500460450604", GOODS),
    ("ВАН ТАЙМ ООО", "1570031975380100", GOODS),
    ("ЭКО ТРЕЙД ООО", "16062007258900", GOODS),
    ("СЦИЛЛА КОРПОРЕЙШН ООО", "1570082476010100", CUSTOMS_SRV),
    ("БРОКУС ООО", "1570015126050200", CUSTOMS_SRV),
    ("МЕТЭКСИМ ТЕРМИНАЛ ООО", "2050022751591001", CUSTOMS_SRV),
    ("САТИ ЗАО", "1510035850650100", LOGIST),
    ("САРОЯН АРА ИП", "1570022455930100", LOGIST),
    ("АЙКОН-ИКС ЗАО", "2052122213571001", LOGIST),
    ("АЙК ЗАО (ТЕРМИНАЛ)", "163068058383", LOGIST),
    ("ТРАНСИМПЭКС ООО", "1570014738160200", LOGIST),
    ("НАИРИ ИНШУРАНС ООО", "1570001164651200", LOGIST),
    ("ЮМАКС ООО", "1570012802110100", STORAGE),
    ("АРМАН ЭНД ПАРТНЕРС ООО", "1570014178961400", STORAGE),
    ("ХАНКАШАР ООО", "11500857737700", RENT),
    ("ЮКОМ ЗАО", "2470054651060010", NET),
    ("АЙСПОРТ ООО", "11817076207400", NET),
    ("ТОЧ-МАСТЕР ООО", "19300641417400", FEE),
    ("СКАН СЕРВИС ООО", "2052022213341001", LABELS),
    ("РЕНРАН ООО", "2051722067031001", ADS),
    ("МЕЛОЯН ШУШАН ИП", "1570098908960100", CONTENT),
    ("МОЛЛИ МЕЙД ИТ ООО", "2050022731961001", CONTENT),
    ("МЕЦ ЦИАЦАН ООО", "1570017805580100", OFFICE),
    ("ВОСКЕ КНИК ООО", "2140006742640100", OFFICE),
    ("МХИТАРЯН ВААГН ИП", "163688005590", EQUIP),
    ("ЭКО ПАК ООО", "2500011275890100", PACK),
    ("ГАЛСТЯН ВАХЕ ИП", "2052832599061001", EQUIP),          # сенсоры для магазина
    ("ЮНИТЕК ООО", "2050822021721001", EQUIP),               # сканеры для кассы
    ("АЛАВЕРДЯН ОВАННЕС ИП", "16600178930300", LOGIST),      # перевозка до склада
    ("ГРИГОРЯН ДИАНА", "2050081954927002", CONTENT),         # UGC Instagram
    ("ГРИГОРЯН АСМИК", "220163911195000", CONTENT),          # модель для съёмки
    ("АГАБЕКЯН ГАГИК ИП", "163003050024", OFFICE),           # ароматизация магазина
    ("ПОЛИГЛОТ ЛАБ ООО", "220493332328000", SECRETARY),       # перевод документов
    ("БИ СОФТ ООО", "11808010064700", EQUIP),                # сканеры для кассы
    ("КЕЧЕЧЯН КАРЕН ИП", "1570096103280100", EQUIP),         # оборудование для магазина
    ("САН ПРИНТ ООО", "220453331062000", EQUIP),             # оборудование для магазина
    ("СОГАКЯН КАРЕН", "11800336798400", REPAIR),             # мелкий ремонт магазина
    ("АСРЯН НАРЕК", "1930097138048800", CONTENT),            # договор услуг: контент
    ("МАЧКАЛЯН ЭРИКА", "2050565564057001", CONTENT),         # договор услуг: контент
    # ответы коллег на «Уточнить платежи» (18.11.2026)
    ("ФЕЕРИЛЕНД ГРУП ООО", "1570025903110100", LOGIST),      # перевозка
    ("СПЛЕШ УОТЕР ООО", "11500184049140", OFFICE),           # вода для кулера
    ("СТЕПАНЯН АРУСИК", "2050091457931001", ADS),            # блогер, реклама
    ("МАКАРЯН МАНАНА ИП", "11820010818100", ADS),            # блогер, реклама
    ("АБРОСИН СЕРГЕЙ ИП", "1660078217040100", ADS),          # блогер, реклама
]

RKO_ARDSHIN = ("սպասարկման|միջնորդավճար|ինկասաց|SWIFT|INVOICE|PEREVOD|"
               "spasarkman|vtchari|mijnordavchar|inkasac")

# (контрагент, ИНН-заглушка, [счета], [договоры])
PLAN = [
    ("ЭКВАЙРИНГ АРДШИНБАНК", "AM-ACQ-ARDSHIN",
     ["2470010211270000", "2470000332300010", "2470036366410000", "36910000002145", "2470050477480000"],
     [K("Эквайринг", **ACQ)]),
    ("АРДШИНБАНК", "AM-ARDSHINBANK",
     ["SELF:2470003205871007", "2470030575170000", "2470036329880000", "2470036329700000", "62111090001850",
      "2470001038351000"],
     [K("Комиссия эквайринг", "Գործարք ԱԿ-ում|Gortsarq AK-um", **FEE),
      K("Бизнес карта", "Անկանխիկ վճարում|Ankankhik vcharum", st="720001", pl="620000", spl="580101", cf="123940"),
      K("Договор РКО", RKO_ARDSHIN, **RKO)]),
    ("ЭКВАЙРИНГ ВТБ-АРМЕНИЯ", "AM-ACQ-VTB", ["29190480000419", "62010000000053"],
     [K("Эквайринг", "Բանկի POS-ից", **ACQ)]),
    ("ВТБ-АРМЕНИЯ", "AM-VTB", ["SELF:16062007242300"], [K("Комиссия эквайринг", **FEE)]),
    ("ЭКВАЙРИНГ АКБА БАНК", "AM-ACQ-ACBA", ["220008609657000", "220008609350000"], [K("Эквайринг", **ACQ)]),
    ("АРАРАТ ИНКАССАЦИЯ ЗАО", "AM-ARARAT-INKAS", ["2470032194060000"], [K("Договор", **ACQ)]),
    # оплаты покупателей через кошелёк Idram
    ("ИДРАМ ООО (ОПЛАТЫ ПОКУПАТЕЛЕЙ)", "AM-IDRAM",
     ["1930028248480100", "1930028248480400", "1510024803180100", "1150005284850100"], [K("Эквайринг", **ACQ)]),
    # возвраты покупателям, купившим в кредит Айди Банка (RL): гашение их кредита
    ("ВОЗВРАТЫ ПОКУПАТЕЛЯМ — КРЕДИТЫ RL АЙДИ БАНКА", "AM-RL-REFUND", [], [K("Договор", "RL gortsarq", **ACQ)]),
    # проценты банков на остаток по счетам
    ("ПРОЦЕНТЫ БАНКОВ НА ОСТАТОК", "AM-BANK-INTEREST", ["1150005473033022", "33140620025325", "33140620025358"],
     [K("Договор", st="771001", pl="420000", spl="590301", cf="313100")]),
    # оплата услуг инкассации — отдельный счёт Арарата
    ("АРАРАТ ИНКАССАЦИЯ ЗАО — УСЛУГИ ИНКАССАЦИИ", "AM-ARARAT-INKAS-FEE", ["163288601434"], [K("Договор", **RKO)]),
    ("ТРЕНДСЕТТЕР ЗАО (АРМЕНИЯ) — СОБСТВЕННЫЕ СЧЕТА", "AM-OWN-" + OWNER_TAX, OWN,
     [K("Внутригрупповые расчеты", "տեղափոխ|միջև|Սեփական|teghapokh|mijev|sepakan|հանձնարարագիր|/RTN/|собственных средс", st="790001", cf="410101"),
      K("Внутригрупповые расчеты", "փոխանակում|փոխարկում|pokhanakum|pokharkum|արժույթի|arjuyti|Currency Exchange|Obmen", st="790003", cf="410201")]),
    ("ГОСБЮДЖЕТ РА", "AM-STATE-BUDGET",
     ["900005010120", "900005000618", "900005001699", "900005003703", "900005001186", "900005160719",
      "900008000490", "900005017109"],
     [K("Без договора", "ԱՎԵԼԱՑՎԱԾ", st="730006", cf="125400"),
      K("Без договора", "ՄԱՔՍԱ", st="720001", bs="130001", sbs="610102", cf="121400"),
      K("Без договора", "Ապահովագրավճար|Դրոշմանիշ", st="750002", cf="125100"),    # удержания из зарплаты
      K("Без договора", "գրանցման", st="750004", pl="620000", spl="560103", cf="123010"),
      K("Без договора", "Բնապահպան", st="750000", pl="610000", spl="540701", cf="125710")]),
    ("KRASSULA LLP", "AM-KRASSULA", ["KZ566017131000002662"], [K("Договор поставки", "KRASSULA", **GOODS, cur="KZT")]),
    ("OVS SPA", "AM-OVS", ["IT67W0200809440000030020014"], [K("Договор поставки", **GOODS, cur="EUR")]),
    ("SAS JSC", "AM-SASJSC", ["FR7611306000304815431801425"], [K("Договор поставки", **GOODS, cur="EUR")]),
    ("MEXX FASHION B.V.", "AM-MEXX", ["NL88ABNA0254216188"], [K("Договор поставки", **GOODS, cur="EUR")]),
    ("TAKE OFF LIMITED", "AM-TAKEOFF", ["MT66VALL22013000000040023185412"], [K("Договор поставки", **GOODS, cur="EUR")]),
    ("FASHION TRADING DMCC", "AM-FASHIONTRADING", ["AE880351031326767523003"],
     [K("Договор поставки", **GOODS, cur="EUR")]),
    ("GAS MILANO 1984 S.P.A.", "AM-GASMILANO", ["IT95I0200812011000106350105"],
     [K("Договор поставки", **GOODS, cur="EUR")]),
    ("LLP (ОБУВЬ, КАЗАХСТАН) KZ22821ZKXEW10000004", "AM-KZ22821ZKXEW", ["KZ22821ZKXEW10000004"],
     [K("Договор поставки", **GOODS, cur="USD")]),
    ("JIAXING J AND Y TRADING CO LTD", "AM-JIAXING", ["9550880211317900435"],
     [K("Договор поставки", **GOODS, cur="USD")]),
    ("BMJ GMBH INTERNATIONAL LOGISTICS", "AM-BMJ", ["GB37MOLU00992889665412"], [K("Договор", **LOGIST, cur="EUR")]),
    ("PROLOG SAS", "AM-PROLOG", ["FR7610096185650009317160185"], [K("Договор", **LOGIST, cur="EUR")]),
    ("LAM SHIPPING AGENCIES GEORGIA", "AM-LAMSHIPPING", ["GE14BG0000000162590600"],
     [K("Договор", st="720001", pl="520000", spl="520303", cf="121400", cur="USD")]),
    ("ФЕШН ИНВЕСТ ЗАО", "AM-FASHIONINVEST", ["1150008526466410"],
     [K("Договор займа", st="770001", pl="630000", spl="590403", cf="321100")]),
    ("ТАЙМВЕБ.КЛАУД ООО", "7810945525", ["40702810555000083723"],
     [K("Лицензионный договор", st="720001", pl="610000", spl="540401", cf="123700", cur="RUB")]),
    ("СТЕП ООО", "6715012502", ["40702810210500000852"],
     [K("Договор", st="720001", pl="520000", spl="520304", cf="121440", cur="RUB")]),   # декларации ТР ЕАЭС
    ("DANIEL SOUKHAREV", "AM-GE92TB7587245063400001", ["GE92TB7587245063400001"],
     [K("Договор", st="720001", bs="143000", cf="202030", cur="USD")]),    # покупка доли (SPA 19.05.2026)
    ("КРЕСТОН АРМЕНИА ЗАО", "AM-KRESTON", ["1150010706776773"],
     [K("Договор", st="720001", pl="620000", spl="560101", cf="123200")]),             # бухгалтерские услуги
    ("СЕРКОНС ООО", "7737517770", ["40702810700010002338"],
     [K("Договор", st="720001", pl="520000", spl="520304", cf="121440", cur="RUB")]),   # сертификация
    ("ЭЛЕКТРОЭНЕРГИЯ — ПОЛУЧАТЕЛЬ 1570038410027500", "AM-ELECTRICITY-1570038410027500", ["1570038410027500"],
     [K("Договор", st="720001", pl="610000", spl="540606", cf="123982")]),
    ("РЕЕСТР АКЦИОНЕРОВ И РЕГИСТРАЦИЯ", "AM-REGISTRY",
     ["11500056665966", "1150062112015200", "1150063110010600", "1150040210080300"],
     [K("Без договора", st="720001", pl="620000", spl="560103", cf="123010")]),
]

_sup = {}
for _n, _a, _t in SUPPLIERS:                                  # один контрагент — все его счета
    _sup.setdefault(_n, ([], _t))[0].append(_a)
PLAN += [(n, "AM-" + accs[0], accs, [K("Договор", **t)]) for n, (accs, t) in _sup.items()]

# правки RegEx договоров из плана: (ИНН контрагента, было, стало)
REGEX_FIX_CP = [("AM-ARDSHINBANK", "սպասարկման|միջնորդավճար|ինկասաց",
                 "սպասարկման|միջնորդավճար|ինկասաց|SWIFT|INVOICE|PEREVOD"),
                # русские версии выписок: назначение транслитом
                ("AM-ARDSHINBANK", "սպասարկման|միջնորդավճար|ինկասաց|SWIFT|INVOICE|PEREVOD", RKO_ARDSHIN),
                ("AM-ARDSHINBANK", "Գործարք ԱԿ-ում", "Գործարք ԱԿ-ում|Gortsarq AK-um"),
                ("AM-ARDSHINBANK", "Անկանխիկ վճարում", "Անկանխիկ վճարում|Ankankhik vcharum"),
                ("AM-OWN-" + OWNER_TAX, "տեղափոխ|միջև|Սեփական", "տեղափոխ|միջև|Սեփական|teghapokh|mijev|sepakan"),
                ("AM-OWN-" + OWNER_TAX, "փոխանակում|փոխարկում", "փոխանակում|փոխարկում|pokhanakum|pokharkum"),
                # обмен валюты и переводы между своими счетами без ключевых слов
                ("AM-OWN-" + OWNER_TAX, "տեղափոխ|միջև|Սեփական|teghapokh|mijev|sepakan", "տեղափոխ|միջև|Սեփական|teghapokh|mijev|sepakan|հանձնարարագիր|/RTN/"),
                ("AM-OWN-" + OWNER_TAX, "տեղափոխ|միջև|Սեփական|teghapokh|mijev|sepakan|հանձնարարագիր|/RTN/", "տեղափոխ|միջև|Սեփական|teghapokh|mijev|sepakan|հանձնարարագիր|/RTN/|собственных средс"),
                ("AM-OWN-" + OWNER_TAX, "փոխանակում|փոխարկում|pokhanakum|pokharkum", "փոխանակում|փոխարկում|pokhanakum|pokharkum|արժույթի|arjuyti|Currency Exchange|Obmen")]
# правки RegEx существующих договоров: {id: (было, стало)}
REGEX_FIX = {
    535: ("գործ|վերադարձ|վճարահաշվարկ", "գործ|վերադարձ|վճարահաշվարկ|POS անբավարար"),
    536: ("Commission|փոխանցումից", "Commission|փոխանցումից|միջնորդավճար"),
    548: (None, "Sarkisova|Սարկիսովա"),          # удержания по исполнительному листу (ДАХК) — в её зарплату
}
EXTRA_ACCOUNTS = {"1570062112451000": 536}       # абонплата Америабанка → контрагент договора РКО 536
# разовые операции: (дата, расход, ИНН контрагента договора, ST договора, статья CF)
OP_FIX = [("2026-10-19", "3630000.00", "AM-STATE-BUDGET", "750002", "125100")]   # налоги с ФОТ за сентябрь
STAFF_AUTO = (("Зарплата|Аванс|Отпускные", "Зарплата|Аванс|Отпускные|Пособие|Հիվանդության",
               "Зарплата|Аванс|Отпускные|Пособие|Հիվանդության|Преми|Պարգև",
               "Зарплата|Аванс|Отпускные|Пособие|Հիվանդության|Преми|Պարգև|Доплат|Հավելավճար|"
               "Окончательн|վերջնահաշվարկ"),
              "Зарплата|Аванс|Отпускные|Пособие|Հիվանդության|Преми|Պարգև|Доплат|Հավելավճար|"
              "Окончательн|վերջնահաշվարկ|Перерасч|վերահաշվարկ|Աշխատավարձ|Արձակուրդ|ԴԱՀԿ|DAHK|Oroshum")


class Command(BaseCommand):
    help = "План разноски Армении; без --apply только проверка и список"

    @staticmethod
    def _sync(owner, coa, items):
        """Единственный договор контрагента из плана — привести счета и статью к плану; статью в операциях тоже."""
        n = 0
        for name, tax, accs, ks in PLAN:
            if len(ks) != 1:
                continue
            k = ks[0]
            cs = list(Contracts.objects.filter(owner=owner, cp__tax_id=tax))
            if len(cs) != 1:
                continue
            c = cs[0]
            want = dict(bs=coa[k["st"]], st=coa.get(k["bs"]) if k["bs"] else None,
                        subconto_bs=items.get(k["sbs"]) if k["sbs"] else None,
                        pl=coa.get(k["pl"]) if k["pl"] else None,
                        subconto_pl=items.get(k["spl"]) if k["spl"] else None)
            if any(getattr(c, f) != v for f, v in want.items()):
                Contracts.objects.filter(pk=c.pk).update(**want)
                n += 1
            cf = items[k["cf"]]
            old = set(CfItemAuto.objects.filter(contract=c).exclude(defaultcfcr=cf)
                      .values_list("defaultcfcr_id", flat=True)) - {None}
            CfItemAuto.objects.filter(contract=c, regex=".").update(defaultcfdt=cf, defaultcfcr=cf)
            if old:
                CfData.objects.filter(contract=c, cfitem_id__in=old).update(cfitem=cf)
        return n

    def add_arguments(self, p):
        p.add_argument("--apply", action="store_true")

    def handle(self, apply, **_):
        owner = Owners.objects.exclude(country="RU").filter(name__icontains="АРМЕН").first()
        if owner is None:
            raise CommandError("нет компании со страной Армения")
        coa = {c.code: c for c in COA.objects.all()}
        items = {c.code: c for c in CfItems.objects.all()}
        titles = {t.title: t for t in ContractsTitle.objects.all()}

        missing = set()
        for _, _, _, ks in PLAN:
            for k in ks:
                for f in ("st", "bs", "pl"):
                    if k[f] and k[f] not in coa:
                        missing.add(f"счёт {k[f]}")
                for f in ("sbs", "spl", "cf"):
                    if k[f] and k[f] not in items:
                        missing.add(f"статья {k[f]}")
                if k["title"] not in titles:
                    missing.add(f"тип договора «{k['title']}»")
        if missing:
            raise CommandError("Нет в справочниках (новые не создаю): " + ", ".join(sorted(missing)))

        taken = dict(CounterpartyAccount.objects.values_list("account", "cp__name"))
        self.stdout.write(f"Компания: {owner}")
        for name, tax, accs, ks in PLAN:
            cp = Counterparty.objects.filter(tax_id=tax).first()
            self.stdout.write(f"\n● {name} [{tax}]{' — уже есть' if cp else ''}")
            for a in accs:
                busy = taken.get(a)
                self.stdout.write(f"    счёт {a}" + (f"  (уже привязан к «{busy}» — пропуск)" if busy else ""))
            for k in ks:
                parts = [f"ST {k['st']}"] + [f"{lbl} {k[f]}" for lbl, f in
                                              (("BS", "bs"), ("субк.BS", "sbs"), ("PL", "pl"), ("субк.PL", "spl")) if k[f]]
                self.stdout.write(f"    договор «{k['title']}» {k['cur']} | {' | '.join(parts)} | RegEx {k['regex'] or '—'} "
                                  f"| статья {k['cf']} {items[k['cf']].name}")
        for cid, (old, new) in REGEX_FIX.items():
            self.stdout.write(f"\nДоговор {cid}: RegEx «{old}» → «{new}»")
        for a, cid in EXTRA_ACCOUNTS.items():
            self.stdout.write(f"Счёт {a} → контрагент договора {cid}")
        self.stdout.write(f"Трудовые договоры: правило статьи → «{STAFF_AUTO[1]}»")

        if not apply:
            self.stdout.write("\nПроверка без записи. Для создания добавьте --apply.")
            return

        made = 0
        with transaction.atomic():
            for tax, old, new in REGEX_FIX_CP:                 # до создания — чтобы не задвоить договор
                Contracts.objects.filter(owner=owner, cp__tax_id=tax, regex=old).update(regex=new)
            for name, tax, accs, ks in PLAN:
                cp, _ = Counterparty.objects.get_or_create(tax_id=tax, defaults={"name": name, "country": "AM"})
                for a in accs:
                    if a not in taken:
                        CounterpartyAccount.objects.create(account=a, cp=cp)
                        taken[a] = cp.name
                for k in ks:
                    if Contracts.objects.filter(owner=owner, cp=cp, regex=k["regex"], bs=coa[k["st"]]).exists():
                        continue
                    c = Contracts.objects.create(
                        owner=owner, cp=cp, title=titles[k["title"]], currency=k["cur"], regex=k["regex"],
                        bs=coa[k["st"]], st=coa.get(k["bs"]) if k["bs"] else None,
                        subconto_bs=items.get(k["sbs"]) if k["sbs"] else None,
                        pl=coa.get(k["pl"]) if k["pl"] else None,
                        subconto_pl=items.get(k["spl"]) if k["spl"] else None)
                    CfItemAuto.objects.create(contract=c, regex=".", defaultcfdt=items[k["cf"]],
                                              defaultcfcr=items[k["cf"]])
                    made += 1
            for cid, (old, new) in REGEX_FIX.items():
                was = Q(regex__isnull=True) | Q(regex="") if old is None else Q(regex=old)
                Contracts.objects.filter(was, pk=cid, owner=owner).update(regex=new)
            for a, cid in EXTRA_ACCOUNTS.items():
                c = Contracts.objects.filter(pk=cid, owner=owner).first()
                if c:
                    CounterpartyAccount.objects.update_or_create(account=a, defaults={"cp": c.cp})
            CfItemAuto.objects.filter(contract__owner=owner, contract__title__title="Трудовой договор",
                                      regex__in=STAFF_AUTO[0]).update(regex=STAFF_AUTO[1])
            synced = self._sync(owner, coa, items)
            for d, amount, tax, st, cf in OP_FIX:
                c = Contracts.objects.filter(owner=owner, cp__tax_id=tax, bs__code=st).first()
                if c:
                    CfData.objects.filter(owner=owner, date=d, cr=amount, contract__isnull=True).update(
                        contract=c, cp_final=c.cp, cfitem=items[cf])
            ids = list(unassigned(CfData.objects.filter(owner=owner)).values_list("id", flat=True))
            lines = []
            auto_assign(ids, owner.id, lines.append)
        left = unassigned(CfData.objects.filter(owner=owner)).filter(contract__isnull=True).count()
        self.stdout.write(f"\nДоговоров с обновлёнными настройками: {synced}.")
        self.stdout.write(f"Новых договоров: {made}. Проверено операций: {len(ids)}; без договора осталось: {left}")
        for x in lines:
            self.stdout.write(x)
