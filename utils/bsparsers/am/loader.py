"""
Загрузка армянских выписок в treasury (BankStatements / CfData).

Отличия от загрузки выписок РФ:
  * операции не удаляются: повторная загрузка добавляет только новые (по row_key);
  * договоры, контрагенты и статьи подбираются только для новых строк и только среди договоров этой компании;
  * выписка с нарушенным сальдо не загружается.
"""

from __future__ import annotations

from collections import Counter
from datetime import timedelta
from pathlib import Path

from django.core.files import File
from django.db import connection, transaction
from django.db import models
from django.db.models import F, Q

from corporate.models import Bank, BankAccount, Owners
from treasury.models import BankStatements, CfData, CounterpartyAccount, CpName, HintRule, TextTranslation

from .parser import Statement, StatementError, parse_statement
from .translate import cp_name_ru, fill, key_of, template

DOC_TYPE = "Банковская операция"
SEED = Path(__file__).with_name("translations_hy_ru.json")

NEW_OWNER = {
    "country": "AM", "currency": "AMD", "report_group": "Армения", "in_reports": True,
}


def sniff(path) -> bool:
    """Быстрая проверка: армянская выписка или нет (для BankStatements.save и am_load)."""
    import zipfile

    path = Path(path)
    marks = ["Տեղեկանք".encode(), "Ժամանակահատված".encode(), b"AccountStatementReport",
             "î»Õ»Ï³Ýù".encode(),                       # Տեղեկանք в ArmSCII-8, сохранённый как текст
             b"\xee\xbb\xd5\xbb\xcf\xb3\xdd\xf9"]          # то же в однобайтовой кодировке
    for ru in ("Начала периода", "Номер документа", "Банк-Клиент"):      # русские версии банков
        marks += [ru.encode(), ru.encode("cp1251")]
    try:
        if path.suffix.lower() in (".xlsx", ".xlsm"):
            with zipfile.ZipFile(path) as z:            # текст внутри xlsx сжат — читаем части книги
                names = [n for n in z.namelist() if n in ("xl/workbook.xml", "xl/sharedStrings.xml")
                         or n.startswith("xl/worksheets/sheet1")]
                head = b"".join(z.read(n)[:400_000] for n in names)
        else:
            head = path.read_bytes()[:400_000]
            if b"<Workbook" not in head:
                return False
    except (OSError, zipfile.BadZipFile):
        return False
    return any(m in head for m in marks)


# ============================================================
# Справочники
# ============================================================

def get_owner(st: Statement, log) -> Owners:
    owner = Owners.objects.filter(inn=st.owner_tax_id).first() if st.owner_tax_id else None
    if owner:
        return owner
    if not st.owner_tax_id:
        # русская версия «Банк-клиента» без ИНН: компания по этому счёту или по счетам того же клиента банка
        ba = BankAccount.objects.filter(account=st.account).select_related("corporate").first()
        if ba is None and len(st.account) > 10:
            ba = (BankAccount.objects.filter(account__startswith=st.account[:-2])
                  .exclude(corporate__country="RU").select_related("corporate").first())
        if ba is not None:
            return ba.corporate
        raise StatementError("в выписке нет ИНН (ՀՎՀՀ) владельца счёта, и счёт не найден среди счетов компаний")
    owner = Owners.objects.create(name=f"{cp_name_ru(st.owner_name) or 'КОМПАНИЯ'} (АРМЕНИЯ)", inn=st.owner_tax_id, **NEW_OWNER)
    log(f"  + новая компания: {owner.name}, ИНН {owner.inn} — проверьте карточку")
    return owner


def get_account(st: Statement, owner: Owners, log) -> BankAccount:
    ba = BankAccount.objects.select_related("corporate").filter(account=st.account).first()
    if ba:
        if ba.corporate_id != owner.id:
            raise StatementError(f"счёт {st.account} заведён на другую компанию: {ba.corporate}")
        return ba
    code = st.account[:3]
    bank = Bank.objects.filter(code=code, country="AM").first()
    if bank is None:
        bank = Bank.objects.create(name=st.bank or f"Банк {code}", code=code, country="AM")
        log(f"  + новый банк: {bank.name} (код {code})")
    ba = BankAccount.objects.create(corporate=owner, bank=bank, account=st.account,
                                    currency=st.currency or "AMD", is_active=True)
    log(f"  + новый счёт: {ba}")
    ensure_bs_acc(ba, log)
    return ba


def ensure_bs_acc(ba: BankAccount, log=print):
    """Балансовый счёт в плане счетов для банковского счёта: в той же группе, что счета РФ."""
    from corporate.models import COA
    if ba.bs_acc_id:
        return ba.bs_acc
    from collections import Counter
    used = Counter(x for x in BankAccount.objects.filter(bs_acc__isnull=False).exclude(pk=ba.pk)
                   .values_list("bs_acc__parent_id", flat=True) if x)
    if not used:
        raise StatementError("в плане счетов нет группы банковских счетов")
    parent = COA.objects.get(pk=used.most_common(1)[0][0])
    codes = [int(c) for c in COA.objects.filter(parent=parent).values_list("code", flat=True) if c.isdigit()]
    code = max(codes) + 1 if codes else int(parent.code) * 10 + 1
    while COA.objects.filter(code=f"{code:06d}").exists():
        code += 1
    bank = ba.bank.name if ba.bank else ""
    acc = COA.objects.create(code=f"{code:06d}", parent=parent, name=f"{bank} {ba.currency} {ba.account}".strip())
    BankAccount.objects.filter(pk=ba.pk).update(bs_acc=acc)
    ba.bs_acc = acc
    log(f"  + балансовый счёт {acc}")
    return acc


_seed = None


def seed() -> dict[str, str]:
    """Начальный словарь переводов (шаблон → перевод)."""
    global _seed
    if _seed is None:
        import json
        _seed = json.loads(SEED.read_text(encoding="utf-8")) if SEED.exists() else {}
    return _seed


def cp_names(names: list[str]) -> dict[str, str]:
    """Русские названия контрагентов по справочнику; новые добавляются с автоматическим переводом."""
    uniq = {n for n in names if n}
    have = dict(CpName.objects.filter(source__in=uniq).values_list("source", "name_ru"))
    new = [CpName(source=n, name_ru=cp_name_ru(n)) for n in uniq if n not in have]
    CpName.objects.bulk_create(new, ignore_conflicts=True)
    have.update({x.source: x.name_ru for x in new})
    return have


def translations(texts: list[str]) -> dict[str, str | None]:
    """Перевод для каждого текста; новые шаблоны добавляются в словарь без перевода."""
    tpls = {t: template(t) for t in set(texts)}
    keys = {t: key_of(tpl) for t, (tpl, _) in tpls.items()}
    known = {x.key: x for x in TextTranslation.objects.filter(key__in=set(keys.values()))}
    hits = Counter(keys[t] for t in texts)
    new = {}
    for t, (tpl, _) in tpls.items():
        k = keys[t]
        if k not in known and k not in new:
            new[k] = TextTranslation(key=k, source=tpl, hits=0, translation=seed().get(tpl))
    TextTranslation.objects.bulk_create(new.values(), ignore_conflicts=True)
    known = {x.key: x for x in TextTranslation.objects.filter(key__in=set(keys.values()))}
    for k, n in hits.items():
        if k in known:
            known[k].hits += n
    TextTranslation.objects.bulk_update(known.values(), ["hits"], batch_size=500)
    out = {}
    for t, (tpl, nums) in tpls.items():
        tr = known[keys[t]].translation
        out[t] = fill(tr, nums) if tr else None
    return out


# ============================================================
# Авторазноска новых строк
# ============================================================

# транзитные счета банков: рублёвые переводы в РФ идут через них, получатель — только в названии (ИНН)
TRANSIT_ACCOUNTS = ("16000001146200",      # ВТБ-Армения
                    "2470059669470000")    # Ардшинбанк
TRANSIT_SQL = "(" + ", ".join(f"'{a}'" for a in TRANSIT_ACCOUNTS) + ")"


def is_transit(account: str) -> bool:
    import re as _re
    return account in TRANSIT_ACCOUNTS or bool(_re.fullmatch(r"30[12]\d{17}", account or ""))


# RegEx проверяется и по оригиналу назначения, и по переводу
AUTO_SQL = [
    ("контрагенты по счёту", """
        UPDATE treasury_cfdata d SET cp_id = a.cp_id
        FROM treasury_counterpartyaccount a, corporate_bankaccount b
        WHERE d.id = ANY(%(ids)s) AND b.id = d.ba_id
          -- пустой контрагент, или договора ещё нет, а счёт привязан к другому контрагенту
          AND (d.cp_id IS NULL OR (d.contract_id IS NULL AND d.cp_id <> a.cp_id))
          -- корр. счёт равен своему счёту выписки (удержания банка) — привязка «SELF:<счёт>»
          AND a.account = CASE WHEN (CASE WHEN d.dt > 0 THEN d.payer_account ELSE d.reciver_account END) = b.account
                               THEN 'SELF:' || b.account
                               ELSE (CASE WHEN d.dt > 0 THEN d.payer_account ELSE d.reciver_account END) END
          -- транзитные и корр. счета банков — общие для многих получателей, контрагента не определяют
          AND a.account NOT IN """ + TRANSIT_SQL + """ AND a.account !~ '^30[12][0-9]{17}$'
    """),
    ("договоры по счёту", """
        -- счёт привязан к конкретному договору (эквайринг, инкассация) — договор по счёту, до RegEx
        UPDATE treasury_cfdata d SET contract_id = a.contract_id
        FROM treasury_counterpartyaccount a, corporate_bankaccount b, contracts_contracts c
        WHERE d.id = ANY(%(ids)s) AND d.contract_id IS NULL AND b.id = d.ba_id
          AND c.id = a.contract_id AND c.owner_id = d.owner_id
          AND a.account = CASE WHEN (CASE WHEN d.dt > 0 THEN d.payer_account ELSE d.reciver_account END) = b.account
                               THEN 'SELF:' || b.account
                               ELSE (CASE WHEN d.dt > 0 THEN d.payer_account ELSE d.reciver_account END) END
    """),
    ("контрагенты по ИНН в названии", """
        UPDATE treasury_cfdata d SET cp_id = c.id
        FROM counterparties_counterparty c
        WHERE d.id = ANY(%(ids)s) AND d.cp_id IS NULL
          AND c.tax_id = substring(d.cp_bs_name from '(?:INN|ИНН)[ .:]*([0-9]{10,12})')
    """),
    ("договоры по назначению", """
        WITH m AS (
            SELECT DISTINCT ON (d.id) d.id AS cf_id, c.id AS contract_id
            FROM treasury_cfdata d
            JOIN contracts_contracts c
              ON c.owner_id = d.owner_id AND c.regex IS NOT NULL AND c.regex <> ''
              AND (d.temp ~* c.regex OR coalesce(d.temp_ru, '') ~* c.regex)
              -- договор, привязанный к счетам, подбирается только по счёту
              AND NOT EXISTS (SELECT 1 FROM treasury_counterpartyaccount ba WHERE ba.contract_id = c.id)
            WHERE d.id = ANY(%(ids)s) AND d.contract_id IS NULL
              AND (d.cp_id IS NULL OR c.cp_id = d.cp_id)        -- контрагент известен: только его договоры
              -- контрагент не найден, но в названии есть ИНН — чужой договор по RegEx не ставим
              AND (d.cp_id IS NOT NULL OR coalesce(d.cp_bs_name, '') !~* '(INN|ИНН)[ .:]*[0-9]{10}')
            ORDER BY d.id, length(c.regex) DESC, c.id
        )
        UPDATE treasury_cfdata d SET contract_id = m.contract_id FROM m WHERE d.id = m.cf_id
    """),
    ("договоры по контрагенту", """
        UPDATE treasury_cfdata d SET contract_id = r.contract_id
        FROM treasury_contractsrexex r
        JOIN contracts_contracts c ON c.id = r.contract_id
        WHERE d.id = ANY(%(ids)s) AND d.contract_id IS NULL AND d.cp_id = r.cp_id
          AND c.owner_id = d.owner_id AND (d.temp ~* r.regex OR coalesce(d.temp_ru, '') ~* r.regex)
    """),
    ("единственный договор контрагента", """
        WITH one AS (
            SELECT owner_id, cp_id, min(id) AS contract_id
            FROM contracts_contracts
            GROUP BY owner_id, cp_id
            HAVING count(*) = 1
        )
        UPDATE treasury_cfdata d SET contract_id = one.contract_id
        FROM one
        WHERE d.id = ANY(%(ids)s) AND d.contract_id IS NULL
          AND one.owner_id = d.owner_id AND one.cp_id = d.cp_id
    """),
    ("контрагент по договору", """
        UPDATE treasury_cfdata d SET cp_final_id = c.cp_id
        FROM contracts_contracts c
        WHERE d.id = ANY(%(ids)s) AND d.contract_id = c.id AND d.cp_final_id IS NULL
    """),
    ("статьи", """
        WITH m AS (
            SELECT DISTINCT ON (d.id) d.id AS cf_id,
                   CASE WHEN d.dt = 0 THEN t.defaultcfcr_id ELSE t.defaultcfdt_id END AS cf_item
            FROM treasury_cfdata d
            JOIN contracts_cfitemauto t ON t.contract_id = d.contract_id
             -- пустой RegEx автоматизации — статья для любого назначения; более точный RegEx важнее
             AND (coalesce(t.regex, '') = '' OR d.temp ~* t.regex OR coalesce(d.temp_ru, '') ~* t.regex)
            WHERE d.id = ANY(%(ids)s) AND d.cfitem_id IS NULL
              -- только правила, где статья для этого направления заполнена
              AND (CASE WHEN d.dt = 0 THEN t.defaultcfcr_id ELSE t.defaultcfdt_id END) IS NOT NULL
            ORDER BY d.id, length(coalesce(t.regex, '')) DESC, t.id
        )
        UPDATE treasury_cfdata d SET cfitem_id = m.cf_item FROM m WHERE d.id = m.cf_id AND m.cf_item IS NOT NULL
    """),
    ("валютная конвертация — не внутригрупповая", """
        UPDATE treasury_cfdata d SET intercompany = FALSE
        FROM corporate_cfitems i
        WHERE d.id = ANY(%(ids)s) AND d.intercompany AND i.id = d.cfitem_id AND i.code = '410201'
    """),
    ("разметка по похожим операциям", """
        WITH stat AS (
            SELECT owner_id, op_type, (dt > 0) AS incoming, hint, count(*) AS n
            FROM treasury_cfdata
            WHERE owner_id = %(owner)s AND hint <> '' AND NOT hint_auto AND op_type IS NOT NULL
            GROUP BY 1, 2, 3, 4
        ), best AS (
            SELECT *, sum(n) OVER w AS total, row_number() OVER (w ORDER BY n DESC) AS rn
            FROM stat WINDOW w AS (PARTITION BY owner_id, op_type, incoming)
        )
        UPDATE treasury_cfdata d SET hint = b.hint, hint_auto = TRUE
        FROM best b
        WHERE d.id = ANY(%(ids)s) AND coalesce(d.hint, '') = ''
          AND b.owner_id = d.owner_id AND b.op_type = d.op_type AND b.incoming = (d.dt > 0)
          AND b.rn = 1 AND b.n >= 3 AND b.n >= 0.9 * b.total
    """),
    ("статьи по разметке", """
        UPDATE treasury_cfdata d
        SET cfitem_id = CASE WHEN d.dt > 0 THEN r.cfitem_dt_id ELSE r.cfitem_cr_id END
        FROM treasury_hintrule r
        WHERE d.id = ANY(%(ids)s) AND d.cfitem_id IS NULL AND d.hint = r.hint
          AND (CASE WHEN d.dt > 0 THEN r.cfitem_dt_id ELSE r.cfitem_cr_id END) IS NOT NULL
    """),
]


def auto_assign(ids: list[int], owner_id: int, log):
    if not ids:
        return
    with connection.cursor() as cur:
        for title, sql in AUTO_SQL:
            cur.execute(sql, {"ids": ids, "owner": owner_id})
            log(f"  {title}: {cur.rowcount}")


def retranslate(log=print) -> None:
    """Перевод всех операций вне РФ по текущему словарю; счётчики словаря — заново; неиспользуемые непроверенные шаблоны — удалить."""
    rows = list(CfData.objects.exclude(owner__country="RU").filter(owner__isnull=False)
                .values_list("id", "temp", "temp_ru", "cp_bs_name", "cp_name_ru"))
    with transaction.atomic():
        TextTranslation.objects.update(hits=0)
        empty = [x for x in TextTranslation.objects.filter(is_checked=False)
                 .filter(Q(translation__isnull=True) | Q(translation__contains="текст в выписке повреждён"))
                 if x.source in seed() and x.translation != seed()[x.source]]   # пустые и прежние заглушки
        for x in empty:
            x.translation = seed()[x.source]
        TextTranslation.objects.bulk_update(empty, ["translation"], batch_size=500)
        tr = translations([t for _, t, _, _, _ in rows if t])
        counts = Counter(n for _, _, _, n, _ in rows if n)
        cps = list(CpName.objects.all())
        for x in cps:                                                   # автоназвания — по текущим правилам
            if not x.is_checked:
                x.name_ru = cp_name_ru(x.source)
            x.hits = counts.get(x.source, 0)
        CpName.objects.bulk_update(cps, ["name_ru", "hits"], batch_size=500)
        names = cp_names([n for _, _, _, n, _ in rows])
        changed = [CfData(id=i, temp_ru=tr.get(t) if t else None, cp_name_ru=names.get(n) or None)
                   for i, t, old_t, n, old_n in rows
                   if (tr.get(t) if t else None) != old_t or (names.get(n) or None) != old_n]
        CfData.objects.bulk_update(changed, ["temp_ru", "cp_name_ru"], batch_size=1000)
        dropped, _ = TextTranslation.objects.filter(hits=0, is_checked=False).delete()
    log(f"Переводы и названия: операций {len(rows)}, обновлено {len(changed)}, лишних шаблонов удалено {dropped}")


def unassigned(qs):
    """Операции, где не заполнено хотя бы одно поле разноски."""
    return qs.filter(models.Q(cfitem__isnull=True) | models.Q(contract__isnull=True) | models.Q(hint__isnull=True)
                     | models.Q(hint="") | models.Q(cp__isnull=True) | models.Q(cp_final__isnull=True))


def reassign(owner_id: int, log=print) -> None:
    """Повторная авторазноска по всем операциям компании, где что-то не заполнено. Заполненное не меняется."""
    ids = list(CfData.objects.filter(owner_id=owner_id)
               .filter(models.Q(cfitem__isnull=True) | models.Q(contract__isnull=True) | models.Q(hint__isnull=True)
                       | models.Q(hint="") | models.Q(cp__isnull=True) | models.Q(cp_final__isnull=True))
               .values_list("id", flat=True))
    log(f"Повторная разноска незаполненных операций: {len(ids)}")
    with transaction.atomic():
        auto_assign(ids, owner_id, log)


# ============================================================
# Загрузка
# ============================================================

def check_chain(ba: BankAccount, st: Statement, log) -> list[str]:
    """Сверка с соседними выписками по счёту: остатки и разрывы."""
    warns = []
    prev = (BankStatements.objects.filter(ba=ba, finish__lt=st.start)
            .exclude(start=st.start, finish=st.finish).order_by("-finish").first())
    if prev:
        if prev.finish != st.start - timedelta(days=1):
            warns.append(f"разрыв: нет выписок с {prev.finish + timedelta(days=1)} по {st.start - timedelta(days=1)}")
        elif prev.eb is not None and prev.eb != st.bb:
            warns.append(f"вход {st.bb:,} ≠ исход предыдущей выписки {prev.eb:,} (разница {st.bb - prev.eb:,})")
    nxt = (BankStatements.objects.filter(ba=ba, start=st.finish + timedelta(days=1)).first())
    if nxt and nxt.bb is not None and nxt.bb != st.eb:
        warns.append(f"исход {st.eb:,} ≠ вход следующей выписки {nxt.bb:,}")
    for w in warns:
        log(f"  ! {w}")
    return warns


def file_sha1(path) -> str:
    import hashlib
    return hashlib.sha1(Path(path).read_bytes()).hexdigest()


def load_statement(path, log=print, bs: BankStatements | None = None, force: bool = False) -> dict:
    path = Path(path)
    digest = file_sha1(path)
    if not force and bs is None:
        same = BankStatements.objects.filter(file_sha1=digest).select_related("ba").first()
        if same is not None:                               # этот же файл уже загружен
            return {"bs_id": same.pk, "owner_id": same.owner_id, "new": 0, "existing": None,
                    "warnings": [], "account": same.ba.account if same.ba else "", "skipped": True,
                    "period": (same.start, same.finish)}
    st = parse_statement(path)
    log(f"{st.bank} {st.currency} {st.account}: {st.start:%d.%m.%Y}–{st.finish:%d.%m.%Y}, строк {len(st.rows)}")
    if st.balance_gap:
        raise StatementError(f"сальдо не сходится: вход {st.bb:,} + приход {st.total_dt:,} − расход "
                             f"{st.total_cr:,} ≠ исход {st.eb:,} (разница {st.balance_gap:,}) — выписка не загружена")

    with transaction.atomic():
        owner = get_owner(st, log)
        ba = get_account(st, owner, log)
        warns = check_chain(ba, st, log)

        covered = list(BankStatements.objects.filter(ba=ba, start__lte=st.finish, finish__gte=st.start)
                       .exclude(pk=getattr(bs, "pk", None)).values_list("start", "finish"))
        if bs is None:
            bs = BankStatements.objects.filter(ba=ba, start=st.start, finish=st.finish).first()
        if bs is None:
            bs = BankStatements(owner=owner, ba=ba, start=st.start, finish=st.finish, bb=st.bb, eb=st.eb,
                                file_sha1=digest)
            with path.open("rb") as f:
                bs.file.save(path.name, File(f), save=False)
            bs.save()
        else:
            BankStatements.objects.filter(pk=bs.pk).update(owner=owner, ba=ba, start=st.start, finish=st.finish,
                                                           bb=st.bb, eb=st.eb, file_sha1=digest)

        keys = [r.key for r in st.rows]
        have = set(CfData.objects.filter(ba=ba, row_key__in=keys).values_list("row_key", flat=True))
        new_rows = [r for r in st.rows if r.key not in have]
        # та же операция в другой версии выписки (русская/армянская, транслит назначения) —
        # совпадение по дате, сумме и номеру документа считается уже загруженной
        loose = Counter(
            (d, dt or 0, cr or 0, (doc or "").split("/")[0].lstrip("0"))
            for d, dt, cr, doc in CfData.objects.filter(ba=ba, date__gte=st.start, date__lte=st.finish)
            .values_list("date", "dt", "cr", "doc_numner"))
        for r in st.rows:                                   # уже совпавшие по ключу из счёта не вычитать дважды
            if r.key in have:
                loose[(r.date, r.dt, r.cr, r.doc_number.lstrip("0"))] -= 1
        kept = []
        for r in new_rows:
            k = (r.date, r.dt, r.cr, r.doc_number.lstrip("0"))
            if loose[k] > 0:
                loose[k] -= 1
                have.add(r.key)
                continue
            kept.append(r)
        new_rows = kept

        ours = set(BankAccount.objects.values_list("account", flat=True))
        cp_map = dict(CounterpartyAccount.objects.filter(
            account__in={r.cp_account for r in new_rows}).values_list("account", "cp_id"))
        tr = translations([r.purpose for r in new_rows])
        names = cp_names([r.cp_name for r in new_rows])
        used = set(CfData.objects.filter(bs=bs).values_list("doc_numner", "date", "dt", "cr"))

        objs = []
        for r in new_rows:
            doc = r.doc_number or "б/н"
            n = 1
            while (doc, r.date, r.dt, r.cr) in used:          # уникальность в пределах выписки
                n += 1
                doc = f"{r.doc_number}/{n}"
            used.add((doc, r.date, r.dt, r.cr))
            incoming = r.dt > 0
            objs.append(CfData(
                bs=bs, owner=owner, ba=ba, doc_type=DOC_TYPE, doc_numner=doc,
                doc_date=r.date.strftime("%d.%m.%Y"), date=r.date, dt=r.dt, cr=r.cr,
                source_dt=r.dt, source_cr=r.cr, dt_eq=r.dt_eq, cr_eq=r.cr_eq,
                temp=r.purpose, temp_ru=tr.get(r.purpose), op_type=r.op_type, cp_bs_name=r.cp_name,
                payer_account=r.cp_account if incoming else st.account,
                reciver_account=st.account if incoming else r.cp_account,
                intercompany=r.cp_account in ours and r.cp_account != st.account, cp_id=cp_map.get(r.cp_account), row_key=r.key,
                hint=r.hint or None, cp_name_ru=names.get(r.cp_name) or None,
            ))
        HintRule.objects.bulk_create([HintRule(hint=h) for h in {o.hint for o in objs if o.hint}],
                                     ignore_conflicts=True)            # новые метки — в справочник
        created = CfData.objects.bulk_create(objs, batch_size=500)
        ids = [o.pk for o in created if o.pk]
        if len(ids) != len(created):
            ids = list(CfData.objects.filter(ba=ba, row_key__in=[o.row_key for o in objs]).values_list("id", flat=True))
        auto_assign(ids, owner.id, log)

    suspects = [o for o in objs if any(s <= o.date <= f for s, f in covered if s and f)]
    if suspects:                                            # дни уже были загружены, а строки «новые»
        w = (f"{len(suspects)} новых операций приходятся на уже загруженные дни — "
             f"проверьте на дубли (банк мог изменить текст назначения)")
        warns.append(w)
        log(f"  ! {w}")
    no_tr = sum(1 for o in objs if not o.temp_ru)
    log(f"  новых операций: {len(objs)}, уже были: {len(have)}, без перевода: {no_tr}")
    return {"bs_id": bs.pk, "owner_id": owner.id, "new": len(objs), "existing": len(have), "warnings": warns,
            "account": st.account, "period": (st.start, st.finish)}


def regroup_contract(contract, log=print) -> int:
    """Операции контрагента, подходящие под RegEx договора, — на этот договор.

    Переносятся только операции без договора или стоящие на договоре этого контрагента без RegEx
    (подставленном как единственный); выбранные по своему RegEx и сплиты не трогаются.
    Статья — заново, по автоматизации договора.
    """
    rx = (contract.regex or "").strip()
    owner = getattr(contract, "owner", None)
    if not rx or owner is None or (owner.country or "RU") == "RU":
        return 0
    if CounterpartyAccount.objects.filter(contract=contract).exists():   # договор по счёту — RegEx не применяется
        return 0
    with transaction.atomic(), connection.cursor() as cur:
        cur.execute("""
            UPDATE treasury_cfdata d
            SET contract_id = %(c)s, cfitem_id = NULL, cp_final_id = %(cp)s
            WHERE d.owner_id = %(owner)s
              AND (d.cp_id = %(cp)s OR d.cp_final_id = %(cp)s)
              AND (d.temp ~* %(rx)s OR coalesce(d.temp_ru, '') ~* %(rx)s)
              AND d.contract_id IS DISTINCT FROM %(c)s
              AND (d.contract_id IS NULL OR EXISTS (
                    SELECT 1 FROM contracts_contracts o
                    WHERE o.id = d.contract_id AND o.cp_id = %(cp)s AND coalesce(o.regex, '') = ''
                      -- договор, привязанный к счёту (эквайринг), выбран по счёту — не трогаем
                      AND NOT EXISTS (SELECT 1 FROM treasury_counterpartyaccount ba WHERE ba.contract_id = o.id)))
              AND NOT EXISTS (SELECT 1 FROM treasury_cfsplits s WHERE s.transaction_id = d.id)
            RETURNING d.id
        """, {"c": contract.pk, "cp": contract.cp_id, "owner": owner.pk, "rx": rx})
        ids = [r[0] for r in cur.fetchall()]
        if ids:
            auto_assign(ids, owner.pk, log)
    return len(ids)
